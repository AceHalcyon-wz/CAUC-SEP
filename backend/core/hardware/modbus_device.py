"""
文件名: modbus_device.py
路径: backend/core/hardware/modbus_device.py
功能: Modbus设备驱动抽象基类，提供Modbus通信相关的通用功能
作者: Backend Engineer Agent
创建日期: 2026-03-26
依赖: Python 3.11+, logging

安全约束:
- 所有Modbus设备驱动必须继承此基类
- Modbus通信必须使用统一的串口通信管理器
- 必须实现指令优先级调度、超时重传、错误帧过滤
- 急停指令必须跳过通信队列，优先执行
"""

from __future__ import annotations

import logging
from typing import Any

from backend.core.hardware.base_device import BaseDevice, DeviceStateType
from backend.core.hardware.device_types import ConnectionType, DeviceConfig

logger = logging.getLogger(__name__)


class ModbusDeviceBase(BaseDevice[DeviceStateType]):
    """
    Modbus设备驱动抽象基类。

    继承自BaseDevice，提供Modbus通信相关的通用功能。
    所有Modbus设备驱动应继承此基类。

    Attributes:
        slave_id: Modbus从站地址
        port: 串口号
        baudrate: 波特率

    安全约束:
        - Modbus通信必须使用统一的串口通信管理器
        - 必须实现指令优先级调度、超时重传、错误帧过滤
        - 急停指令必须跳过通信队列，优先执行

    Example:
        >>> class DM2CMotorDevice(ModbusDeviceBase[MotorState]):
        ...     async def connect(self) -> bool:
        ...         self._set_status(DeviceStatus.CONNECTING)
        ...         try:
        ...             # 初始化Modbus连接
        ...             self._set_status(DeviceStatus.READY)
        ...             return True
        ...         except Exception as e:
        ...             self._set_error(f"连接失败: {e}")
        ...             return False
    """

    def __init__(
        self,
        device_id: str,
        config: DeviceConfig | dict[str, Any],
        slave_id: int = 1,
    ) -> None:
        """
        初始化Modbus设备驱动。

        Args:
            device_id: 设备唯一标识
            config: 设备配置
            slave_id: Modbus从站地址，默认1

        Raises:
            ValueError: 当slave_id无效时抛出
        """
        super().__init__(device_id, config)

        # 验证slave_id
        if not isinstance(slave_id, int) or slave_id < 1 or slave_id > 247:
            raise ValueError(f"slave_id必须在1-247范围内，当前值: {slave_id}")

        # Modbus参数
        self.slave_id = slave_id
        self.port = self.config.connection_params.get("port", "COM1")
        self.baudrate = self.config.connection_params.get("baudrate", 38400)

        # 更新设备信息
        self.info.connection_type = ConnectionType.SERIAL

        logger.info(
            f"ModbusDeviceBase初始化: device_id={device_id}, "
            f"slave_id={slave_id}, port={self.port}, baudrate={self.baudrate}"
        )

    # ==================== Modbus通信抽象方法 ====================

    async def read_holding_registers(
        self, address: int, count: int = 1, priority: int = 5
    ) -> list[int] | None:
        """
        读取保持寄存器。

        Args:
            address: 起始地址
            count: 读取数量，默认1
            priority: 指令优先级（0=最高，9=最低），默认5

        Returns:
            Optional[List[int]]: 寄存器值列表，失败返回None

        安全约束:
            - 必须实现超时重传机制
            - 必须实现错误帧过滤
            - 急停相关寄存器读取必须使用最高优先级

        Example:
            >>> # 读取电机当前位置（地址0x1000，32位，需读2个寄存器）
            >>> position_regs = await device.read_holding_registers(0x1000, 2)
            >>> if position_regs:
            ...     position = (position_regs[0] << 16) | position_regs[1]
        """
        # 子类应重写此方法实现具体的Modbus读取逻辑
        raise NotImplementedError("read_holding_registers未实现")

    async def write_single_register(
        self, address: int, value: int, priority: int = 5
    ) -> bool:
        """
        写入单个寄存器。

        Args:
            address: 寄存器地址
            value: 写入值（16位无符号整数，0-65535）
            priority: 指令优先级（0=最高，9=最低），默认5

        Returns:
            bool: 写入是否成功

        安全约束:
            - 必须实现超时重传机制
            - 急停指令必须使用priority=0，跳过通信队列
            - 必须验证参数合法性（地址、值范围）

        Example:
            >>> # 写入急停指令（最高优先级）
            >>> success = await device.write_single_register(0x0200, 1, priority=0)
        """
        # 子类应重写此方法实现具体的Modbus写入逻辑
        raise NotImplementedError("write_single_register未实现")

    async def write_multiple_registers(
        self, address: int, values: list[int], priority: int = 5
    ) -> bool:
        """
        写入多个寄存器。

        Args:
            address: 起始地址
            values: 写入值列表（每个值为16位无符号整数）
            priority: 指令优先级（0=最高，9=最低），默认5

        Returns:
            bool: 写入是否成功

        安全约束:
            - 必须实现超时重传机制
            - 急停相关指令必须使用最高优先级
            - 必须验证参数合法性（地址、值范围、列表长度）
        """
        # 子类应重写此方法实现具体的Modbus写入逻辑
        raise NotImplementedError("write_multiple_registers未实现")

    async def read_input_registers(
        self, address: int, count: int = 1, priority: int = 5
    ) -> list[int] | None:
        """
        读取输入寄存器。

        Args:
            address: 起始地址
            count: 读取数量，默认1
            priority: 指令优先级（0=最高，9=最低），默认5

        Returns:
            Optional[List[int]]: 寄存器值列表，失败返回None
        """
        # 子类应重写此方法实现具体的Modbus读取逻辑
        raise NotImplementedError("read_input_registers未实现")

    async def read_coils(self, address: int, count: int = 1, priority: int = 5) -> list[bool] | None:
        """
        读取线圈状态。

        Args:
            address: 起始地址
            count: 读取数量，默认1
            priority: 指令优先级（0=最高，9=最低），默认5

        Returns:
            Optional[List[bool]]: 线圈状态列表，失败返回None
        """
        # 子类应重写此方法实现具体的Modbus读取逻辑
        raise NotImplementedError("read_coils未实现")

    async def write_single_coil(self, address: int, value: bool, priority: int = 5) -> bool:
        """
        写入单个线圈。

        Args:
            address: 线圈地址
            value: 写入值（True/False）
            priority: 指令优先级（0=最高，9=最低），默认5

        Returns:
            bool: 写入是否成功
        """
        # 子类应重写此方法实现具体的Modbus写入逻辑
        raise NotImplementedError("write_single_coil未实现")

    # ==================== 辅助方法 ====================

    @staticmethod
    def _convert_signed_32bit(high: int, low: int) -> int:
        """
        将两个16位寄存器值转换为有符号32位整数。

        Args:
            high: 高16位寄存器值
            low: 低16位寄存器值

        Returns:
            int: 有符号32位整数

        Example:
            >>> # 读取电机当前位置（32位有符号整数）
            >>> regs = await device.read_holding_registers(0x1000, 2)
            >>> if regs:
            ...     position = device._convert_signed_32bit(regs[0], regs[1])
        """
        value = (high << 16) | low
        if value & 0x80000000:
            value -= 0x100000000
        return value

    @staticmethod
    def _convert_unsigned_32bit(high: int, low: int) -> int:
        """
        将两个16位寄存器值转换为无符号32位整数。

        Args:
            high: 高16位寄存器值
            low: 低16位寄存器值

        Returns:
            int: 无符号32位整数
        """
        return (high << 16) | low

    @staticmethod
    def _split_32bit_to_registers(value: int) -> tuple[int, int]:
        """
        将32位整数拆分为两个16位寄存器值。

        Args:
            value: 32位整数

        Returns:
            Tuple[int, int]: (高16位, 低16位)

        Example:
            >>> # 写入目标位置（32位整数）
            >>> high, low = device._split_32bit_to_registers(10000)
            >>> await device.write_multiple_registers(0x1000, [high, low])
        """
        high = (value >> 16) & 0xFFFF
        low = value & 0xFFFF
        return high, low
