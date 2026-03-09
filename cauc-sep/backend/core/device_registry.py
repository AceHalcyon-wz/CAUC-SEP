"""
设备注册表模块

功能：
- 统一管理所有设备实例
- 提供设备注册、注销、查询接口
- 单例模式确保全局唯一实例

作者：Backend Engineer Agent
创建日期：2026-03-07
依赖：typing
"""

from typing import Any, Dict


class DeviceRegistry:
    """
    设备注册表类（单例模式）。

    用于统一管理所有设备实例，提供全局访问点。
    使用类变量实现单例模式，避免多实例导致的状态不一致问题。

    Attributes:
        _instance: 单例实例
        _devices: 设备字典，key为设备ID，value为设备实例

    Example:
        >>> registry = DeviceRegistry()
        >>> registry.register("motor_1", motor_instance)
        >>> motor = registry.get_device("motor_1")
    """

    _instance = None
    _devices: Dict[str, Any] = {}

    def __new__(cls) -> "DeviceRegistry":
        """
        实现单例模式。

        Returns:
            DeviceRegistry: 全局唯一的注册表实例
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """
        私有化初始化方法。

        单例模式下，初始化仅在首次创建时执行。
        """
        # 单例模式下避免重复初始化
        pass

    @classmethod
    def register(cls, device_id: str, device: Any) -> bool:
        """
        注册设备实例。

        Args:
            device_id: 设备唯一标识符
            device: 设备实例对象

        Returns:
            bool: 注册成功返回True

        Raises:
            ValueError: 设备ID已存在时抛出

        Example:
            >>> DeviceRegistry.register("motor_main", dm2c_driver)
            True
        """
        if device_id in cls._devices:
            raise ValueError(
                f"设备ID '{device_id}' 已存在，无法重复注册。"
                f"请使用 unregister() 先注销现有设备。"
            )

        cls._devices[device_id] = device
        return True

    @classmethod
    def unregister(cls, device_id: str) -> bool:
        """
        注销设备实例。

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 注销成功返回True

        Raises:
            KeyError: 设备不存在时抛出

        Example:
            >>> DeviceRegistry.unregister("motor_main")
            True
        """
        if device_id not in cls._devices:
            raise KeyError(
                f"设备ID '{device_id}' 不存在。"
                f"当前已注册设备: {list(cls._devices.keys())}"
            )

        del cls._devices[device_id]
        return True

    @classmethod
    def get_device(cls, device_id: str) -> Any:
        """
        获取设备实例。

        Args:
            device_id: 设备唯一标识符

        Returns:
            Any: 设备实例对象

        Raises:
            KeyError: 设备不存在时抛出

        Example:
            >>> motor = DeviceRegistry.get_device("motor_main")
            >>> await motor.connect()
        """
        if device_id not in cls._devices:
            raise KeyError(
                f"设备ID '{device_id}' 不存在。"
                f"当前已注册设备: {list(cls._devices.keys())}"
            )

        return cls._devices[device_id]

    @classmethod
    def get_all_devices(cls) -> Dict[str, Any]:
        """
        获取所有已注册设备。

        Returns:
            Dict[str, Any]: 设备字典，key为设备ID，value为设备实例

        Example:
            >>> devices = DeviceRegistry.get_all_devices()
            >>> for device_id, device in devices.items():
            ...     print(f"{device_id}: {device.status}")
        """
        return cls._devices.copy()

    @classmethod
    def has_device(cls, device_id: str) -> bool:
        """
        检查设备是否存在。

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 设备存在返回True，否则返回False

        Example:
            >>> if DeviceRegistry.has_device("motor_main"):
            ...     motor = DeviceRegistry.get_device("motor_main")
        """
        return device_id in cls._devices

    @classmethod
    def clear(cls) -> None:
        """
        清空所有已注册设备。

        警告：此操作将移除所有设备实例，通常仅在系统关闭时调用。

        Example:
            >>> DeviceRegistry.clear()
            >>> DeviceRegistry.get_all_devices()
            {}
        """
        cls._devices.clear()

    @classmethod
    def get_device_count(cls) -> int:
        """
        获取已注册设备数量。

        Returns:
            int: 设备数量

        Example:
            >>> count = DeviceRegistry.get_device_count()
            >>> print(f"已注册 {count} 个设备")
        """
        return len(cls._devices)

    @classmethod
    def get_device_ids(cls) -> list[str]:
        """
        获取所有设备ID列表。

        Returns:
            list[str]: 设备ID列表

        Example:
            >>> ids = DeviceRegistry.get_device_ids()
            >>> print(f"设备列表: {ids}")
        """
        return list(cls._devices.keys())
