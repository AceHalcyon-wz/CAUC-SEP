"""
文件名: base_device.py
路径: backend/core/hardware/base_device.py
功能: 统一的设备抽象基类，整合现有3套基类的核心功能
作者: Backend Engineer Agent
创建日期: 2026-03-26
依赖: Python 3.11+, abc, logging, typing

安全约束:
- 所有设备驱动必须继承此抽象基类
- 必须实现connect、disconnect、get_status、emergency_stop、reset_alarm通用方法
- 急停相关代码必须保障最高执行优先级
- 高危操作必须包含二次校验、日志审计逻辑

设计参考：
- backend/devices/base.py - AbstractDevice
- backend/core/abstract.py - AbstractDevice (ABC)
- backend/drivers/base.py - BaseDevice (ABC, Generic)
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from typing import Any, Callable, Generic, TypeVar

from backend.core.hardware.device_types import (
    DeviceAlarm,
    DeviceConfig,
    DeviceInfo,
    DeviceStatus,
)
from backend.core.hardware.software_limit import SoftwareLimitConfig

logger = logging.getLogger(__name__)

# 类型变量，用于泛型设备状态
DeviceStateType = TypeVar("DeviceStateType")


class BaseDevice(ABC, Generic[DeviceStateType]):
    """
    统一的设备抽象基类。

    整合现有3套基类的核心功能，提供统一的设备接口规范。
    所有设备驱动必须继承此基类，并实现所有抽象方法。

    Attributes:
        device_id: 设备唯一标识
        config: 设备配置
        status: 设备状态
        info: 设备信息
        _last_error: 最后一次错误信息
        _alarms: 报警列表
        _status_callback: 状态变化回调函数
        _alarm_callback: 报警回调函数
        _limit_config: 软件限位配置

    安全约束:
        - 所有设备控制相关代码必须包含异常兜底逻辑、参数合法性校验
        - 急停相关代码必须保障最高执行优先级
        - 高危操作必须包含二次校验、日志审计逻辑

    Example:
        >>> class MotorDevice(BaseDevice[MotorState]):
        ...     async def connect(self) -> bool:
        ...         self._set_status(DeviceStatus.CONNECTING)
        ...         # 连接逻辑...
        ...         self._set_status(DeviceStatus.READY)
        ...         return True
        ...
        ...     async def emergency_stop(self) -> bool:
        ...         # 急停逻辑（最高优先级）
        ...         self._set_status(DeviceStatus.EMERGENCY_STOP)
        ...         return True
    """

    def __init__(self, device_id: str, config: DeviceConfig | dict[str, Any]) -> None:
        """
        初始化设备驱动。

        Args:
            device_id: 设备唯一标识
            config: 设备配置，可以是DeviceConfig对象或字典
        """
        self.device_id = device_id

        # 处理配置参数
        if isinstance(config, DeviceConfig):
            self.config = config
        else:
            self.config = DeviceConfig(device_id=device_id, **config)

        # 设备状态
        self._status = DeviceStatus.DISCONNECTED
        self._state: DeviceStateType | None = None

        # 设备信息
        self.info = DeviceInfo(device_id=device_id)

        # 错误和报警
        self._last_error: str | None = None
        self._alarms: list[DeviceAlarm] = []

        # 回调函数
        self._status_callback: Callable[[dict[str, Any]], None] | None = None
        self._alarm_callback: Callable[[DeviceAlarm], None] | None = None

        # 软件限位配置
        self._limit_config = SoftwareLimitConfig()

        # 连接时间戳
        self._connected_at: float | None = None
        self._last_activity: float = time.time()

        logger.info(f"BaseDevice初始化: device_id={device_id}")

    # ==================== 抽象方法（必须实现） ====================

    @abstractmethod
    async def connect(self) -> bool:
        """
        建立与设备的连接。

        Returns:
            bool: 连接是否成功

        安全约束:
            - 连接开始时应设置状态为 CONNECTING
            - 连接成功时应设置状态为 READY
            - 连接失败时应设置状态为 ERROR 并记录错误信息
            - 必须包含异常兜底逻辑

        Example:
            >>> async def connect(self) -> bool:
            ...     self._set_status(DeviceStatus.CONNECTING)
            ...     try:
            ...         # 连接逻辑...
            ...         self._set_status(DeviceStatus.READY)
            ...         return True
            ...     except Exception as e:
            ...         self._set_error(f"连接失败: {e}")
            ...         return False
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        断开与设备的连接。

        Returns:
            bool: 断开是否成功

        安全约束:
            - 断开前应停止所有正在执行的操作
            - 必须释放所有占用的资源
            - 断开成功后应设置状态为 DISCONNECTED
        """
        pass

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """
        获取设备完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典

        安全约束:
            - 状态获取失败时必须返回包含错误信息的字典
            - 不得抛出异常
        """
        pass

    @abstractmethod
    async def emergency_stop(self) -> bool:
        """
        执行紧急停止。

        立即停止设备所有操作，进入安全状态。

        Returns:
            bool: 急停是否成功

        安全约束:
            - 急停指令必须具有最高执行优先级
            - 急停失败时必须记录严重错误日志
            - 必须包含异常兜底逻辑
            - 必须设置设备状态为 EMERGENCY_STOP

        Example:
            >>> async def emergency_stop(self) -> bool:
            ...     try:
            ...         # 急停逻辑（最高优先级）
            ...         self._set_status(DeviceStatus.EMERGENCY_STOP)
            ...         logger.critical(f"设备急停: device_id={self.device_id}")
            ...         return True
            ...     except Exception as e:
            ...         logger.error(f"急停失败: {e}", exc_info=True)
            ...         return False
        """
        pass

    @abstractmethod
    async def reset_alarm(self) -> bool:
        """
        复位设备报警状态。

        Returns:
            bool: 复位是否成功

        安全约束:
            - 复位前应检查设备状态，确保安全
            - 必须清除所有活动报警
            - 复位成功后应设置状态为 READY
        """
        pass

    # ==================== 可选方法（建议实现） ====================

    async def initialize(self) -> bool:
        """
        初始化设备。

        执行设备初始化流程，如回零、参数加载等。

        Returns:
            bool: 初始化是否成功
        """
        logger.info(f"设备初始化: device_id={self.device_id}")
        self._set_status(DeviceStatus.INITIALIZING)
        try:
            # 子类可重写此方法实现具体的初始化逻辑
            self._set_status(DeviceStatus.READY)
            return True
        except Exception as e:
            self._set_error(f"初始化失败: {e}")
            logger.error(f"设备初始化失败: device_id={self.device_id}, error={e}")
            return False

    async def reset(self) -> bool:
        """
        复位设备。

        将设备恢复到初始状态。

        Returns:
            bool: 复位是否成功
        """
        logger.info(f"设备复位: device_id={self.device_id}")
        try:
            # 清除报警
            self._alarms.clear()
            self._last_error = None

            # 子类可重写此方法实现具体的复位逻辑
            if self._status == DeviceStatus.ERROR:
                self._set_status(DeviceStatus.READY)

            return True
        except Exception as e:
            self._set_error(str(e))
            logger.error(f"设备复位失败: device_id={self.device_id}, error={e}")
            return False

    async def self_test(self) -> dict[str, Any]:
        """
        执行设备自检。

        Returns:
            Dict[str, Any]: 自检结果，包含各项测试结果
        """
        logger.info(f"设备自检: device_id={self.device_id}")
        return {
            "device_id": self.device_id,
            "status": self._status.value,
            "connected": self.is_connected,
            "alarms_count": len(self._alarms),
            "last_error": self._last_error,
            "test_result": "pass" if self.is_connected else "not_connected",
        }

    # ==================== 属性访问器 ====================

    @property
    def status(self) -> DeviceStatus:
        """
        获取设备当前状态。

        Returns:
            DeviceStatus: 当前设备状态
        """
        return self._status

    @property
    def is_connected(self) -> bool:
        """
        检查设备是否已连接。

        Returns:
            bool: 是否已连接
        """
        return self._status not in (
            DeviceStatus.DISCONNECTED,
            DeviceStatus.CONNECTING,
        )

    @property
    def is_ready(self) -> bool:
        """
        检查设备是否就绪。

        Returns:
            bool: 是否就绪（可接收指令）
        """
        return self._status == DeviceStatus.READY

    @property
    def is_busy(self) -> bool:
        """
        检查设备是否忙碌。

        Returns:
            bool: 是否正在执行指令
        """
        return self._status == DeviceStatus.BUSY

    @property
    def is_error(self) -> bool:
        """
        检查设备是否处于错误状态。

        Returns:
            bool: 是否处于错误状态
        """
        return self._status == DeviceStatus.ERROR

    @property
    def is_emergency_stop(self) -> bool:
        """
        检查设备是否处于急停状态。

        Returns:
            bool: 是否处于急停状态
        """
        return self._status == DeviceStatus.EMERGENCY_STOP

    @property
    def is_alarm(self) -> bool:
        """
        检查设备是否处于报警状态。

        Returns:
            bool: 是否处于报警状态
        """
        return self._status == DeviceStatus.ALARM or len(self._alarms) > 0

    @property
    def last_error(self) -> str | None:
        """
        获取最后一次错误信息。

        Returns:
            Optional[str]: 错误信息，无错误返回None
        """
        return self._last_error

    @property
    def state(self) -> DeviceStateType | None:
        """
        获取设备状态对象。

        Returns:
            Optional[DeviceStateType]: 设备状态对象
        """
        return self._state

    @property
    def limit_config(self) -> SoftwareLimitConfig:
        """
        获取软件限位配置。

        Returns:
            SoftwareLimitConfig: 软件限位配置实例
        """
        return self._limit_config

    @limit_config.setter
    def limit_config(self, value: SoftwareLimitConfig) -> None:
        """
        设置软件限位配置。

        Args:
            value: 软件限位配置实例

        Raises:
            ValueError: 当配置无效时抛出
        """
        if not isinstance(value, SoftwareLimitConfig):
            raise ValueError(f"limit_config必须是SoftwareLimitConfig类型，当前类型: {type(value)}")
        self._limit_config = value

    # ==================== 回调函数设置 ====================

    def set_status_callback(
        self, callback: Callable[[dict[str, Any]], None] | None
    ) -> None:
        """
        设置状态变化回调函数。

        Args:
            callback: 回调函数，接收状态字典
        """
        self._status_callback = callback

    def set_alarm_callback(
        self, callback: Callable[[DeviceAlarm], None] | None
    ) -> None:
        """
        设置报警回调函数。

        Args:
            callback: 回调函数，接收报警对象
        """
        self._alarm_callback = callback

    # ==================== 内部方法 ====================

    def _set_status(self, status: DeviceStatus, strict: bool = False) -> None:
        """
        设置设备状态并触发回调。

        Args:
            status: 新状态
            strict: 是否启用严格模式（非法转换抛出异常），默认False

        Raises:
            ValueError: 当strict=True且状态转换不合法时抛出
        """
        old_status = self._status

        # 状态转换验证
        if strict and not old_status.can_transition_to(status):
            raise ValueError(
                f"非法状态转换: {old_status.value} -> {status.value} "
                f"(设备: {self.device_id})"
            )
        elif not old_status.can_transition_to(status):
            logger.warning(
                f"非标准状态转换: {old_status.value} -> {status.value} "
                f"(设备: {self.device_id})"
            )

        self._status = status
        self._last_activity = time.time()

        if old_status != status:
            logger.debug(
                f"设备状态变化: device_id={self.device_id}, "
                f"old={old_status.value}, new={status.value}"
            )
            self._notify_status_change()

    def _add_alarm(self, alarm: DeviceAlarm) -> None:
        """
        添加报警。

        Args:
            alarm: 报警对象
        """
        self._alarms.append(alarm)
        logger.warning(
            f"设备报警: device_id={self.device_id}, "
            f"code={alarm.alarm_code}, message={alarm.alarm_message}"
        )

        if self._alarm_callback:
            try:
                self._alarm_callback(alarm)
            except Exception as e:
                logger.error(f"报警回调函数异常: {e}")

    def _set_error(self, error: str) -> None:
        """
        设置错误信息。

        Args:
            error: 错误信息
        """
        self._last_error = error
        self._status = DeviceStatus.ERROR
        logger.error(f"设备错误: device_id={self.device_id}, error={error}")

    def _notify_status_change(self) -> None:
        """
        通知状态变化。
        """
        if self._status_callback:
            try:
                status_data = self._get_base_status()
                self._status_callback(status_data)
            except Exception as e:
                logger.error(f"状态回调函数异常: {e}")

    def _get_base_status(self) -> dict[str, Any]:
        """
        获取基础状态信息。

        Returns:
            Dict[str, Any]: 基础状态字典
        """
        return {
            "device_id": self.device_id,
            "status": self._status.value,
            "is_connected": self.is_connected,
            "is_ready": self.is_ready,
            "is_busy": self.is_busy,
            "is_error": self.is_error,
            "is_emergency_stop": self.is_emergency_stop,
            "is_alarm": self.is_alarm,
            "last_error": self._last_error,
            "alarms_count": len(self._alarms),
            "connected_at": self._connected_at,
            "last_activity": self._last_activity,
        }

    def __repr__(self) -> str:
        """
        返回设备对象的字符串表示。

        Returns:
            str: 字符串表示
        """
        return (
            f"{self.__class__.__name__}("
            f"device_id='{self.device_id}', "
            f"status={self._status.value}, "
            f"connected={self.is_connected})"
        )
