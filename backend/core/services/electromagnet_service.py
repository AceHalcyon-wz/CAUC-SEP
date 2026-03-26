"""
文件名: electromagnet_service.py
路径: backend/core/services/electromagnet_service.py
功能: 电磁铁控制业务逻辑服务，封装电流控制、安全保护等业务规则
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+, backend.drivers.base, backend.core.utils

安全约束:
- 所有电流控制必须包含过流保护校验
- 异常时必须触发安全断电逻辑
- 高危操作必须包含二次校验、日志审计逻辑
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from backend.core.services.base_service import (
    BaseDeviceService,
    ServiceResult,
)
from backend.core.utils.exception_utils import (
    DeviceException,
    DeviceCommunicationError,
    DeviceParameterError,
    DeviceNotConnectedError,
)
from backend.core.utils.validation_utils import (
    validate_range,
    validate_device_id,
    validate_current_value,
)

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 默认电流参数
DEFAULT_CURRENT_A = 0.0
DEFAULT_MAX_CURRENT_A = 10.0

# 电流范围
MIN_CURRENT_A = 0.0
MAX_CURRENT_A = 10.0


class ElectromagnetStatus(str, Enum):
    """
    电磁铁状态枚举。

    Attributes:
        OFF: 断电状态
        ON: 通电状态
        RAMPING: 电流爬升中
        ERROR: 错误状态
    """

    OFF = "off"
    ON = "on"
    RAMPING = "ramping"
    ERROR = "error"


@dataclass
class ElectromagnetState:
    """
    电磁铁状态数据类。

    Attributes:
        current_a: 当前电流（A）
        target_current_a: 目标电流（A）
        voltage_v: 当前电压（V）
        status: 电磁铁状态
        is_enabled: 是否使能
    """

    current_a: float = 0.0
    target_current_a: float = 0.0
    voltage_v: float = 0.0
    status: ElectromagnetStatus = ElectromagnetStatus.OFF
    is_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典。"""
        return {
            "current_a": self.current_a,
            "target_current_a": self.target_current_a,
            "voltage_v": self.voltage_v,
            "status": self.status.value,
            "is_enabled": self.is_enabled,
        }


class ElectromagnetControlService(BaseDeviceService[Any]):
    """
    电磁铁控制业务逻辑服务。

    提供电磁铁电流控制、安全保护能力。
    所有方法均集成过流保护校验、异常兜底断电逻辑。

    Attributes:
        _electromagnet_drivers: 电磁铁驱动映射
        _electromagnet_states: 电磁铁状态映射
        _max_current_limits: 最大电流限制映射

    安全约束:
        - 所有电流控制必须包含过流保护校验
        - 异常时必须触发安全断电逻辑
        - 高危操作必须包含二次校验、日志审计逻辑
    """

    def __init__(self) -> None:
        """初始化电磁铁控制服务。"""
        super().__init__("ElectromagnetControlService")

        self._electromagnet_drivers: dict[str, Any] = {}
        self._electromagnet_states: dict[str, ElectromagnetState] = {}
        self._max_current_limits: dict[str, float] = {}

        logger.info("ElectromagnetControlService初始化完成")

    # ==================== 驱动管理 ====================

    def register_driver(
        self, device_id: str, driver: Any, max_current_a: float = DEFAULT_MAX_CURRENT_A
    ) -> None:
        """
        注册电磁铁驱动。

        Args:
            device_id: 设备ID
            driver: 驱动实例
            max_current_a: 最大电流限制（A）
        """
        self._electromagnet_drivers[device_id] = driver
        self._electromagnet_states[device_id] = ElectromagnetState()
        self._max_current_limits[device_id] = max_current_a
        logger.info(f"注册电磁铁驱动: device_id={device_id}, max_current={max_current_a}A")

    def unregister_driver(self, device_id: str) -> None:
        """
        注销电磁铁驱动。

        Args:
            device_id: 设备ID
        """
        self._electromagnet_drivers.pop(device_id, None)
        self._electromagnet_states.pop(device_id, None)
        self._max_current_limits.pop(device_id, None)
        logger.info(f"注销电磁铁驱动: device_id={device_id}")

    def get_driver(self, device_id: str) -> Any | None:
        """
        获取电磁铁驱动。

        Args:
            device_id: 设备ID

        Returns:
            Optional[Any]: 驱动实例，不存在返回None
        """
        return self._electromagnet_drivers.get(device_id)

    # ==================== 抽象方法实现 ====================

    async def get_device_status(self, device_id: str) -> ServiceResult:
        """
        获取设备状态。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        start_time = time.time()

        try:
            # 校验设备ID
            result = validate_device_id(device_id)
            if not result:
                return ServiceResult(
                    success=False,
                    message=result.error_message,
                    error_code=result.error_code,
                )

            # 获取驱动
            driver = self.get_driver(device_id)
            if driver is None:
                return ServiceResult(
                    success=False,
                    message=f"设备 {device_id} 未注册",
                    error_code=1001,
                )

            # 获取状态
            status = await driver.get_status()

            # 更新本地状态缓存
            if device_id in self._electromagnet_states:
                state = self._electromagnet_states[device_id]
                state.current_a = status.get("current_a", 0.0)
                state.voltage_v = status.get("voltage_v", 0.0)
                state.is_enabled = status.get("is_enabled", False)

            execution_time = (time.time() - start_time) * 1000

            return ServiceResult(
                success=True,
                data=status,
                message=f"设备 {device_id} 状态获取成功",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            return self.handle_exception(e, device_id, "get_device_status")

    async def execute_command(
        self,
        device_id: str,
        command: str,
        params: dict[str, Any],
    ) -> ServiceResult:
        """
        执行设备命令。

        Args:
            device_id: 设备ID
            command: 命令名称
            params: 命令参数

        Returns:
            ServiceResult: 服务操作结果
        """
        start_time = time.time()

        # 命令处理器映射
        command_handlers = {
            "set_current": self._handle_set_current,
            "enable": self._handle_enable,
            "disable": self._handle_disable,
            "ramp_current": self._handle_ramp_current,
        }

        handler = command_handlers.get(command)
        if handler is None:
            return ServiceResult(
                success=False,
                message=f"未知命令: {command}",
                error_code=1002,
            )

        try:
            result = await handler(device_id, params)
            execution_time = (time.time() - start_time) * 1000

            # 记录操作日志
            self.log_operation(
                operation=command,
                device_id=device_id,
                parameters=params,
                result="success" if result.success else "failed",
                execution_time_ms=execution_time,
            )

            result.execution_time_ms = execution_time
            return result

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            # 记录失败日志
            self.log_operation(
                operation=command,
                device_id=device_id,
                parameters=params,
                result=f"failed: {str(e)}",
                execution_time_ms=execution_time,
            )

            return self.handle_exception(e, device_id, command)

    async def emergency_stop(self, device_id: str) -> ServiceResult:
        """
        执行紧急停止（断电）。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        start_time = time.time()

        logger.critical(f"[EMERGENCY_STOP] 执行急停（断电）: device_id={device_id}")

        try:
            driver = self.get_driver(device_id)
            if driver is None:
                return ServiceResult(
                    success=False,
                    message=f"设备 {device_id} 未注册",
                    error_code=1001,
                )

            # 执行断电
            success = await driver.disable()

            # 更新状态
            if device_id in self._electromagnet_states:
                self._electromagnet_states[device_id].is_enabled = False
                self._electromagnet_states[device_id].status = ElectromagnetStatus.OFF
                self._electromagnet_states[device_id].target_current_a = 0.0

            execution_time = (time.time() - start_time) * 1000

            # 记录急停日志
            self.log_operation(
                operation="emergency_stop",
                device_id=device_id,
                parameters={},
                result="success" if success else "failed",
                execution_time_ms=execution_time,
            )

            return ServiceResult(
                success=success,
                message=f"设备 {device_id} 急停（断电）{'成功' if success else '失败'}",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            logger.critical(
                f"[EMERGENCY_STOP] 急停执行失败: device_id={device_id}, error={e}"
            )

            return self.handle_exception(e, device_id, "emergency_stop")

    # ==================== 电流控制方法 ====================

    async def set_current(
        self,
        device_id: str,
        current_a: float,
    ) -> ServiceResult:
        """
        设置电流。

        Args:
            device_id: 设备ID
            current_a: 目标电流（A）

        Returns:
            ServiceResult: 服务操作结果

        安全约束:
            - 电流值必须在校验范围内
            - 超过最大电流限制必须拦截
        """
        return await self.execute_command(
            device_id,
            "set_current",
            {"current_a": current_a},
        )

    async def enable(self, device_id: str) -> ServiceResult:
        """
        使能电磁铁。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(device_id, "enable", {})

    async def disable(self, device_id: str) -> ServiceResult:
        """
        断电电磁铁。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(device_id, "disable", {})

    async def ramp_current(
        self,
        device_id: str,
        target_current_a: float,
        ramp_time_s: float = 1.0,
    ) -> ServiceResult:
        """
        爬升电流。

        Args:
            device_id: 设备ID
            target_current_a: 目标电流（A）
            ramp_time_s: 爬升时间（秒）

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(
            device_id,
            "ramp_current",
            {
                "target_current_a": target_current_a,
                "ramp_time_s": ramp_time_s,
            },
        )

    # ==================== 命令处理器 ====================

    async def _handle_set_current(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理设置电流命令。
        """
        current_a = params.get("current_a")

        # 参数校验
        if current_a is None:
            return ServiceResult(
                success=False,
                message="缺少必填参数: current_a",
                error_code=1003,
            )

        # 获取驱动
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        # 检查设备状态
        if not driver.is_connected:
            raise DeviceNotConnectedError(device_id=device_id)

        # 过流保护校验
        max_current = self._max_current_limits.get(device_id, DEFAULT_MAX_CURRENT_A)
        validation_result = validate_current_value(
            current_a,
            min_current=MIN_CURRENT_A,
            max_current=max_current,
            device_id=device_id,
        )

        if not validation_result:
            return ServiceResult(
                success=False,
                message=validation_result.error_message,
                error_code=validation_result.error_code,
            )

        # 执行电流设置
        success = await driver.set_current(current_a)

        # 更新状态
        if device_id in self._electromagnet_states:
            self._electromagnet_states[device_id].target_current_a = current_a
            if success:
                self._electromagnet_states[device_id].status = ElectromagnetStatus.ON

        return ServiceResult(
            success=success,
            message=f"电流设置{'成功' if success else '失败'}",
        )

    async def _handle_enable(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理使能命令。
        """
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        # 检查设备状态
        if not driver.is_connected:
            raise DeviceNotConnectedError(device_id=device_id)

        # 执行使能
        success = await driver.enable()

        # 更新状态
        if device_id in self._electromagnet_states:
            self._electromagnet_states[device_id].is_enabled = True
            self._electromagnet_states[device_id].status = ElectromagnetStatus.ON

        return ServiceResult(
            success=success,
            message=f"使能{'成功' if success else '失败'}",
        )

    async def _handle_disable(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理断电命令。
        """
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        # 执行断电
        success = await driver.disable()

        # 更新状态
        if device_id in self._electromagnet_states:
            self._electromagnet_states[device_id].is_enabled = False
            self._electromagnet_states[device_id].status = ElectromagnetStatus.OFF
            self._electromagnet_states[device_id].target_current_a = 0.0

        return ServiceResult(
            success=success,
            message=f"断电{'成功' if success else '失败'}",
        )

    async def _handle_ramp_current(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理电流爬升命令。
        """
        target_current_a = params.get("target_current_a")
        ramp_time_s = params.get("ramp_time_s", 1.0)

        # 参数校验
        if target_current_a is None:
            return ServiceResult(
                success=False,
                message="缺少必填参数: target_current_a",
                error_code=1003,
            )

        # 获取驱动
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        # 检查设备状态
        if not driver.is_connected:
            raise DeviceNotConnectedError(device_id=device_id)

        # 过流保护校验
        max_current = self._max_current_limits.get(device_id, DEFAULT_MAX_CURRENT_A)
        validation_result = validate_current_value(
            target_current_a,
            min_current=MIN_CURRENT_A,
            max_current=max_current,
            device_id=device_id,
        )

        if not validation_result:
            return ServiceResult(
                success=False,
                message=validation_result.error_message,
                error_code=validation_result.error_code,
            )

        # 执行电流爬升
        success = await driver.ramp_current(target_current_a, ramp_time_s)

        # 更新状态
        if device_id in self._electromagnet_states:
            self._electromagnet_states[device_id].target_current_a = target_current_a
            if success:
                self._electromagnet_states[device_id].status = ElectromagnetStatus.ON

        return ServiceResult(
            success=success,
            message=f"电流爬升{'成功' if success else '失败'}",
        )


# ==================== 全局服务实例 ====================

_electromagnet_control_service: ElectromagnetControlService | None = None


def get_electromagnet_control_service() -> ElectromagnetControlService:
    """
    获取全局电磁铁控制服务实例。

    Returns:
        ElectromagnetControlService: 电磁铁控制服务实例
    """
    global _electromagnet_control_service
    if _electromagnet_control_service is None:
        _electromagnet_control_service = ElectromagnetControlService()
    return _electromagnet_control_service
