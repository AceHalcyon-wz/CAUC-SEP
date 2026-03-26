"""
设备基类模块（已废弃）

功能：
- 定义所有设备驱动的抽象基类
- 提供统一的设备状态管理
- 定义设备生命周期接口

作者：Backend Engineer Agent
创建日期：2026-03-14
最后更新：2026-03-26

⚠️ 废弃警告：
本模块已废弃，请使用统一的设备抽象基类：
- backend.core.hardware.BaseDevice
- backend.core.hardware.DeviceStatus
- backend.core.hardware.DeviceConfig

迁移指南：backend.core.hardware.migration_guide

废弃时间：2026-03-26
移除时间：2026-05-26
"""

import warnings
from enum import Enum
from typing import Any

# 发出废弃警告
warnings.warn(
    "backend.devices.base 模块已废弃，请使用 backend.core.hardware 模块。"
    "迁移指南：backend.core.hardware.migration_guide",
    DeprecationWarning,
    stacklevel=2
)


class DeviceStatus(str, Enum):
    """
    设备状态枚举（已废弃）。
    
    ⚠️ 请使用 backend.core.hardware.DeviceStatus
    
    废弃时间：2026-03-26
    移除时间：2026-05-26
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    MAINTENANCE = "maintenance"


class AbstractDevice:
    """
    设备抽象基类

    所有设备驱动必须继承此类并实现其抽象方法。
    提供统一的设备生命周期管理和状态监控。

    Attributes:
        device_id: 设备唯一标识符
        config: 设备配置字典
        status: 当前设备状态
        simulation: 是否为仿真模式
    """

    def __init__(self, device_id: str, config: dict[str, Any]):
        """
        初始化设备基类。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典
        """
        self.device_id = device_id
        self.config = config
        self.status = DeviceStatus.DISCONNECTED
        self.simulation = config.get("simulation", False)
        self._error_message: str | None = None

    async def connect(self) -> bool:
        """
        连接设备。

        Returns:
            bool: 连接是否成功

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("Subclasses must implement connect()")

    async def disconnect(self) -> bool:
        """
        断开设备连接。

        Returns:
            bool: 断开是否成功

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("Subclasses must implement disconnect()")

    async def read_status(self) -> dict[str, Any]:
        """
        读取设备状态。

        Returns:
            dict: 设备状态信息

        Raises:
            NotImplementedError: 子类必须实现此方法
        """
        raise NotImplementedError("Subclasses must implement read_status()")

    async def reset_error(self) -> bool:
        """
        重置设备错误状态。

        Returns:
            bool: 重置是否成功
        """
        self._error_message = None
        return True

    def get_error_message(self) -> str | None:
        """
        获取错误消息。

        Returns:
            str | None: 错误消息，无错误时返回 None
        """
        return self._error_message

    def set_error(self, message: str) -> None:
        """
        设置错误消息和状态。

        Args:
            message: 错误消息
        """
        self._error_message = message
        self.status = DeviceStatus.ERROR

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__}(id='{self.device_id}', status='{self.status.value}')>"
