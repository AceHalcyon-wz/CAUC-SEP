"""
文件名: motor_service.py
路径: backend/core/services/motor_service.py
功能: 步进电机控制业务逻辑服务，封装运动控制、PR路径、限位校验等业务规则
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+, backend.drivers.base, backend.core.utils

安全约束:
- 所有运动指令必须先执行软件限位预校验
- 异常时必须触发安全停机逻辑
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
    OperationLog,
)
from backend.core.utils.exception_utils import (
    DeviceException,
    DeviceCommunicationError,
    DeviceParameterError,
    DeviceAlarmError,
    DeviceNotConnectedError,
    DeviceLimitError,
    handle_device_exception,
)
from backend.core.utils.validation_utils import (
    validate_range,
    validate_device_id,
    validate_position_value,
    validate_speed_value,
)
from backend.services.limit_protection_service import (
    LimitProtectionService,
    get_limit_protection_service,
)

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 默认运动参数
DEFAULT_SPEED_HZ = 500.0
DEFAULT_ACCELERATION_MS = 100
DEFAULT_DECELERATION_MS = 100

# 运动参数范围
MIN_SPEED_HZ = 100.0
MAX_SPEED_HZ = 5000.0
MIN_ACCELERATION_MS = 10
MAX_ACCELERATION_MS = 10000


class MotionStatus(str, Enum):
    """
    运动状态枚举。

    Attributes:
        IDLE: 空闲
        MOVING: 运动中
        STOPPING: 停止中
        ALARM: 报警
        EMERGENCY_STOP: 急停
    """

    IDLE = "idle"
    MOVING = "moving"
    STOPPING = "stopping"
    ALARM = "alarm"
    EMERGENCY_STOP = "emergency_stop"


class JogDirection(str, Enum):
    """
    JOG方向枚举。

    Attributes:
        POSITIVE: 正向（+）
        NEGATIVE: 负向（-）
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"


@dataclass
class MotorState:
    """
    电机状态数据类。

    Attributes:
        position_mm: 当前位置（mm）
        target_position_mm: 目标位置（mm）
        speed_hz: 当前速度（Hz）
        motion_status: 运动状态
        is_alarm: 是否报警
        alarm_code: 报警代码
        is_moving: 是否运动中
    """

    position_mm: float = 0.0
    target_position_mm: float = 0.0
    speed_hz: float = 0.0
    motion_status: MotionStatus = MotionStatus.IDLE
    is_alarm: bool = False
    alarm_code: int = 0
    is_moving: bool = False


    def to_dict(self) -> dict[str, Any]:
        """转换为字典。 """
        return {
            "position_mm": self.position_mm,
            "target_position_mm": self.target_position_mm,
            "speed_hz": self.speed_hz,
            "motion_status": self.motion_status.value,
            "is_alarm": self.is_alarm,
            "alarm_code": self.alarm_code,
            "is_moving": self.is_moving,
        }


class MotorControlService(BaseDeviceService[Any]):
    """
    步进电机控制业务逻辑服务。

    提供电机运动控制、PR路径编程、限位校验能力。
    所有方法均集成软件限位二次校验、异常兜底停机逻辑。

    Attributes:
        _limit_service: 限位防护服务
        _motor_drivers: 电机驱动映射
        _motor_states: 电机状态映射

    安全约束:
        - 所有运动指令必须先执行软件限位预校验
        - 异常时必须触发安全停机逻辑
        - 高危操作必须包含二次校验、日志审计逻辑
    """

    def __init__(self) -> None:
        """初始化电机控制服务。 """
        super().__init__("MotorControlService")

        self._limit_service: LimitProtectionService = get_limit_protection_service()
        self._motor_drivers: dict[str, Any] = {}
        self._motor_states: dict[str, MotorState] = {}

        # 默认运动参数
        self._default_speed = DEFAULT_SPEED_HZ
        self._default_acceleration = DEFAULT_ACCELERATION_MS

        logger.info("MotorControlService初始化完成")

    # ==================== 驱动管理 ====================

    def register_driver(self, device_id: str, driver: Any) -> None:
        """
        注册电机驱动。

        Args:
            device_id: 设备ID
            driver: 驱动实例
        """
        self._motor_drivers[device_id] = driver
        self._motor_states[device_id] = MotorState()
        logger.info(f"注册电机驱动: device_id={device_id}")

    def unregister_driver(self, device_id: str) -> None:
        """
        注销电机驱动。

        Args:
            device_id: 设备ID
        """
        self._motor_drivers.pop(device_id, None)
        self._motor_states.pop(device_id, None)
        logger.info(f"注销电机驱动: device_id={device_id}")

    def get_driver(self, device_id: str) -> Any | None:
        """
        获取电机驱动。

        Args:
            device_id: 设备ID

        Returns:
            Optional[Any]: 驱动实例，不存在返回None
        """
        return self._motor_drivers.get(device_id)

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
            if device_id in self._motor_states:
                state = self._motor_states[device_id]
                state.position_mm = status.get("position_mm", 0.0)
                state.speed_hz = status.get("speed_hz", 0.0)
                state.is_alarm = status.get("is_alarm", False)
                state.alarm_code = status.get("alarm_code", 0)
                state.is_moving = status.get("is_moving", False)

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
            "absolute_move": self._handle_absolute_move,
            "relative_move": self._handle_relative_move,
            "jog_start": self._handle_jog_start,
            "jog_stop": self._handle_jog_stop,
            "stop": self._handle_stop,
            "home": self._handle_home,
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
        执行紧急停止。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        start_time = time.time()

        logger.critical(f"[EMERGENCY_STOP] 执行急停: device_id={device_id}")

        try:
            driver = self.get_driver(device_id)
            if driver is None:
                return ServiceResult(
                    success=False,
                    message=f"设备 {device_id} 未注册",
                    error_code=1001,
                )

            # 执行急停
            success = await driver.emergency_stop()

            # 更新状态
            if device_id in self._motor_states:
                self._motor_states[device_id].motion_status = MotionStatus.EMERGENCY_STOP
                self._motor_states[device_id].is_moving = False

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
                message=f"设备 {device_id} 急停{'成功' if success else '失败'}",
                execution_time_ms=execution_time,
            )

        except Exception as e:
            execution_time = (time.time() - start_time) * 1000

            logger.critical(
                f"[EMERGENCY_STOP] 急停执行失败: device_id={device_id}, error={e}"
            )

            return self.handle_exception(e, device_id, "emergency_stop")

    # ==================== 运动控制方法 ====================

    async def absolute_move(
        self,
        device_id: str,
        target_position_mm: float,
        speed_hz: float | None = None,
        acceleration_ms: float | None = None,
    ) -> ServiceResult:
        """
        执行绝对定位运动。

        Args:
            device_id: 设备ID
            target_position_mm: 目标位置（mm）
            speed_hz: 运动速度（Hz），None使用默认值
            acceleration_ms: 加速度（ms），None使用默认值

        Returns:
            ServiceResult: 服务操作结果

        安全约束:
            - 运动指令下发前必须执行目标位置预校验，超出限位直接拦截
            - 驱动器处于报警状态时，禁止下发任何运动指令
        """
        return await self.execute_command(
            device_id,
            "absolute_move",
            {
                "target_position_mm": target_position_mm,
                "speed_hz": speed_hz or self._default_speed,
                "acceleration_ms": acceleration_ms or self._default_acceleration,
            },
        )

    async def relative_move(
        self,
        device_id: str,
        distance_mm: float,
        speed_hz: float | None = None,
    ) -> ServiceResult:
        """
        执行相对定位运动。

        Args:
            device_id: 设备ID
            distance_mm: 移动距离（mm）
            speed_hz: 运动速度（Hz），None使用默认值

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(
            device_id,
            "relative_move",
            {
                "distance_mm": distance_mm,
                "speed_hz": speed_hz or self._default_speed,
            },
        )

    async def jog_start(
        self,
        device_id: str,
        direction: JogDirection,
        speed_hz: float | None = None,
    ) -> ServiceResult:
        """
        启动JOG点动。

        Args:
            device_id: 设备ID
            direction: JOG方向
            speed_hz: 运动速度（Hz），None使用默认值

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(
            device_id,
            "jog_start",
            {
                "direction": direction.value,
                "speed_hz": speed_hz or self._default_speed,
            },
        )

    async def jog_stop(self, device_id: str) -> ServiceResult:
        """
        停止JOG点动。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(device_id, "jog_stop", {})

    async def stop(self, device_id: str) -> ServiceResult:
        """
        停止运动。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(device_id, "stop", {})

    async def home(self, device_id: str) -> ServiceResult:
        """
        执行回零操作。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        return await self.execute_command(device_id, "home", {})

    # ==================== 命令处理器 ====================

    async def _handle_absolute_move(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理绝对定位命令。
        """
        target_position_mm = params.get("target_position_mm")
        speed_hz = params.get("speed_hz", self._default_speed)
        acceleration_ms = params.get("acceleration_ms", self._default_acceleration)

        # 参数校验
        if target_position_mm is None:
            return ServiceResult(
                success=False,
                message="缺少必填参数: target_position_mm",
                error_code=1003,
            )

        # 获取驱动
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        # 检查设备状态
        if not driver.is_connected:
            raise DeviceNotConnectedError(device_id=device_id)

        if driver.is_alarm:
            raise DeviceAlarmError(
                message="驱动器处于报警状态，禁止运动",
                device_id=device_id,
            )

        # 软件限位预校验
        current_state = self._motor_states.get(device_id, MotorState())
        is_valid, error_msg = self._limit_service.pre_validate_position(
            device_id=device_id,
            target_position_mm=target_position_mm,
            current_position_mm=current_state.position_mm,
        )

        if not is_valid:
            raise DeviceLimitError(
                message=error_msg or "目标位置超出软件限位范围",
                device_id=device_id,
            )

        # 执行绝对定位
        success = await driver.absolute_move(target_position_mm, speed_hz, acceleration_ms)

        # 更新状态
        if device_id in self._motor_states:
            self._motor_states[device_id].target_position_mm = target_position_mm
            self._motor_states[device_id].speed_hz = speed_hz
            self._motor_states[device_id].motion_status = MotionStatus.MOVING if success else MotionStatus.IDLE

        return ServiceResult(
            success=success,
            message=f"绝对定位{'成功' if success else '失败'}",
        )

    async def _handle_relative_move(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理相对定位命令。
        """
        distance_mm = params.get("distance_mm")
        speed_hz = params.get("speed_hz", self._default_speed)

        # 参数校验
        if distance_mm is None:
            return ServiceResult(
                    success=False,
                    message="缺少必填参数: distance_mm",
                    error_code=1003,
                )

        # 获取驱动
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        # 计算目标位置
        current_state = self._motor_states.get(device_id, MotorState())
        target_position_mm = current_state.position_mm + distance_mm

        # 软件限位预校验
        is_valid, error_msg = self._limit_service.pre_validate_position(
            device_id=device_id,
            target_position_mm=target_position_mm,
            current_position_mm=current_state.position_mm,
        )

        if not is_valid:
            raise DeviceLimitError(
                message=error_msg or "目标位置超出软件限位范围",
                device_id=device_id,
            )

        # 执行相对定位
        success = await driver.relative_move(distance_mm, speed_hz)

        return ServiceResult(
            success=success,
            message=f"相对定位{'成功' if success else '失败'}",
        )

    async def _handle_jog_start(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理JOG启动命令。
        """
        direction = params.get("direction", "positive")
        speed_hz = params.get("speed_hz", self._default_speed)

        # 获取驱动
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        # 检查设备状态
        if not driver.is_connected:
            raise DeviceNotConnectedError(device_id=device_id)

        if driver.is_alarm:
            raise DeviceAlarmError(
                message="驱动器处于报警状态，禁止运动",
                device_id=device_id,
            )

        # JOG限位预校验
        current_state = self._motor_states.get(device_id, MotorState())
        jog_direction_int = 1 if direction == "positive" else -1
        is_valid, error_msg = self._limit_service.pre_validate_jog(
            device_id=device_id,
            direction=jog_direction_int,
            current_position_mm=current_state.position_mm,
        )

        if not is_valid:
            raise DeviceLimitError(
                message=error_msg or "JOG运动被限位阻止",
                device_id=device_id,
            )

        # 执行JOG
        success = await driver.start_jog(direction, speed_hz)

        # 更新状态
        if device_id in self._motor_states:
            self._motor_states[device_id].motion_status = MotionStatus.MOVING if success else MotionStatus.IDLE

        return ServiceResult(
            success=success,
            message=f"JOG启动{'成功' if success else '失败'}",
        )

    async def _handle_jog_stop(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理JOG停止命令。
        """
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        success = await driver.stop_jog()

        # 更新状态
        if device_id in self._motor_states:
            self._motor_states[device_id].motion_status = MotionStatus.IDLE

        return ServiceResult(
            success=success,
            message=f"JOG停止{'成功' if success else '失败'}",
        )

    async def _handle_stop(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理停止命令。
        """
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        success = await driver.stop()

        # 更新状态
        if device_id in self._motor_states:
            self._motor_states[device_id].motion_status = MotionStatus.IDLE

        return ServiceResult(
            success=success,
            message=f"运动停止{'成功' if success else '失败'}",
        )

    async def _handle_home(
        self, device_id: str, params: dict[str, Any]
    ) -> ServiceResult:
        """
        处理回零命令。
        """
        driver = self.get_driver(device_id)
        if driver is None:
            raise DeviceNotConnectedError(device_id=device_id)

        success = await driver.home()

        # 更新状态
        if device_id in self._motor_states:
            self._motor_states[device_id].position_mm = 0.0
            self._motor_states[device_id].motion_status = MotionStatus.IDLE

        return ServiceResult(
            success=success,
            message=f"回零{'成功' if success else '失败'}",
        )


# ==================== 全局服务实例 ====================

_motor_control_service: MotorControlService | None = None


def get_motor_control_service() -> MotorControlService:
    """
    获取全局电机控制服务实例。

    Returns:
        MotorControlService: 电机控制服务实例
    """
    global _motor_control_service
    if _motor_control_service is None:
        _motor_control_service = MotorControlService()
    return _motor_control_service
