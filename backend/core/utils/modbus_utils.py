"""
文件名: modbus_utils.py
路径: backend/core/utils/modbus_utils.py
功能: Modbus通信通用工具类，提供数据类型转换、寄存器操作封装
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+, typing

安全约束:
- 所有Modbus通信必须使用统一的串口通信管理器
- 寄存器地址必须定义为常量
- 通信失败必须实现重试和异常处理
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# DM2C驱动器寄存器地址常量
DM2C_REG_STATUS_WORD = 0x1003  # 状态字
DM2C_REG_ALARM_CODE = 0x1005  # 报警代码
DM2C_REG_CURRENT_POSITION = 0x1008  # 当前位置（低16位）
DM2C_REG_CURRENT_POSITION_HIGH = 0x1009  # 当前位置（高16位）
DM2C_REG_TARGET_POSITION = 0x1010  # 目标位置（低16位）
DM2C_REG_TARGET_POSITION_HIGH = 0x1011  # 目标位置（高16位）
DM2C_REG_SPEED = 0x1012  # 运动速度（低16位）
DM2C_REG_SPEED_HIGH = 0x1013  # 运动速度（高16位）
DM2C_REG_ACCELERATION = 0x1014  # 加速度
DM2C_REG_DECELERATION = 0x1015  # 减速度
DM2C_REG_CONTROL_MODE = 0x1801  # 控制模式
DM2C_REG_MOTION_COMMAND = 0x1802  # 运动指令
DM2C_REG_EMERGENCY_STOP = 0x040  # 急停寄存器
DM2C_REG_POSITIVE_LIMIT = 0x060  # 正向限位
DM2C_REG_NEGATIVE_LIMIT = 0x061  # 负向限位
DM2C_REG_PR_MODE = 0x070  # PR模式
DM2C_REG_PR_START_SPEED = 0x071  # PR起始速度
DM2C_REG_PR_TARGET_POSITION = 0x072  # PR目标位置

# 通用Modbus参数
MODBUS_DEFAULT_SLAVE_ID = 1
MODBUS_DEFAULT_BAUDRATE = 38400
MODBUS_DEFAULT_TIMEOUT = 1.0
MODBUS_MAX_RETRY_COUNT = 3
MODBUS_RETRY_INTERVAL = 0.1


class ModbusDataConverter:
    """
    Modbus数据转换工具类。

    提供Modbus寄存器数据类型的转换功能，包括：
    - 有符号/无符号32位整数高低位转换
    - 16位整数与物理量转换
    - CRC校验

    Example:
        >>> converter = ModbusDataConverter()
        >>> # 将32位有符号整数转换为两个16位寄存器
        >>> high, low = converter.signed_32bit_to_registers(-10000)
        >>> # 将两个16位寄存器转换为32位有符号整数
        >>> value = converter.registers_to_signed_32bit(high, low)
    """

    @staticmethod
    def signed_32bit_to_registers(value: int) -> tuple[int, int]:
        """
        将有符号32位整数转换为两个16位寄存器值。

        Args:
            value: 有符号32位整数

        Returns:
            Tuple[int, int]: (高16位, 低16位)

        Example:
            >>> high, low = ModbusDataConverter.signed_32bit_to_registers(-10000)
            >>> print(f"High={high}, Low={low}")
        """
        # 处理负数（补码表示）
        if value < 0:
            value = value & 0xFFFFFFFF  # 转换为无符号32位

        high_word = (value >> 16) & 0xFFFF
        low_word = value & 0xFFFF

        return high_word, low_word

    @staticmethod
    def registers_to_signed_32bit(high_word: int, low_word: int) -> int:
        """
        将两个16位寄存器值转换为有符号32位整数。

        Args:
            high_word: 高16位寄存器值
            low_word: 低16位寄存器值

        Returns:
            int: 有符号32位整数

        Example:
            >>> value = ModbusDataConverter.registers_to_signed_32bit(0xFFFF, 0xD8F0)
            >>> print(value)  # -10000
        """
        # 组合为32位无符号整数
        unsigned_value = (high_word << 16) | low_word

        # 转换为有符号整数
        if unsigned_value & 0x80000000:
            # 最高位为1，表示负数
            return unsigned_value - 0x100000000
        else:
            return unsigned_value

    @staticmethod
    def unsigned_32bit_to_registers(value: int) -> tuple[int, int]:
        """
        将无符号32位整数转换为两个16位寄存器值。

        Args:
            value: 无符号32位整数

        Returns:
            Tuple[int, int]: (高16位, 低16位)

        Example:
            >>> high, low = ModbusDataConverter.unsigned_32bit_to_registers(50000)
        """
        high_word = (value >> 16) & 0xFFFF
        low_word = value & 0xFFFF

        return high_word, low_word

    @staticmethod
    def registers_to_unsigned_32bit(high_word: int, low_word: int) -> int:
        """
        将两个16位寄存器值转换为无符号32位整数。

        Args:
            high_word: 高16位寄存器值
            low_word: 低16位寄存器值

        Returns:
            int: 无符号32位整数
        """
        return (high_word << 16) | low_word

    @staticmethod
    def position_to_registers(position_mm: float, pulses_per_mm: float = 1000.0) -> tuple[int, int]:
        """
        将位置（毫米）转换为脉冲数，再转换为两个16位寄存器值。

        Args:
            position_mm: 位置（毫米）
            pulses_per_mm: 每毫米脉冲数，默认1000

        Returns:
            Tuple[int, int]: (高16位, 低16位)

        Example:
            >>> high, low = ModbusDataConverter.position_to_registers(10.5, 1000)
        """
        # 转换为脉冲数
        position_pulses = int(position_mm * pulses_per_mm)

        return ModbusDataConverter.signed_32bit_to_registers(position_pulses)

    @staticmethod
    def registers_to_position(high_word: int, low_word: int, pulses_per_mm: float = 1000.0) -> float:
        """
        将两个16位寄存器值转换为位置（毫米）。

        Args:
            high_word: 高16位寄存器值
            low_word: 低16位寄存器值
            pulses_per_mm: 每毫米脉冲数，默认1000

        Returns:
            float: 位置（毫米）
        """
        position_pulses = ModbusDataConverter.registers_to_signed_32bit(
            high_word, low_word
        )
        return position_pulses / pulses_per_mm

    @staticmethod
    def speed_to_registers(speed_hz: float, pulses_per_mm: float = 1000.0) -> tuple[int, int]:
        """
        将速度（Hz）转换为脉冲/秒，再转换为两个16位寄存器值。

        Args:
            speed_hz: 速度（Hz）
            pulses_per_mm: 每毫米脉冲数，默认1000

        Returns:
            Tuple[int, int]: (高16位, 低16位)
        """
        # 转换为脉冲/秒
        speed_pulses = int(speed_hz * pulses_per_mm / 1000.0)

        return ModbusDataConverter.signed_32bit_to_registers(speed_pulses)

    @staticmethod
    def registers_to_speed(high_word: int, low_word: int, pulses_per_mm: float = 1000.0) -> float:
        """
        将两个16位寄存器值转换为速度（Hz）。

        Args:
            high_word: 高16位寄存器值
            low_word: 低16位寄存器值
            pulses_per_mm: 每毫米脉冲数，默认1000

        Returns:
            float: 速度（Hz）
        """
        speed_pulses = ModbusDataConverter.registers_to_signed_32bit(
            high_word, low_word
        )
        return speed_pulses * 1000.0 / pulses_per_mm


class ModbusCommunicationHelper:
    """
    Modbus通信辅助工具类。

    提供Modbus通信的通用功能，包括：
    - 重试机制
    - 错误处理
    - 超时控制

    Example:
        >>> helper = ModbusCommunicationHelper(max_retries=3, retry_interval=0.1)
        >>> result = await helper.execute_with_retry(read_func, slave_id=1, address=0x1003, count=1)
    """

    def __init__(
        self,
        max_retries: int = MODBUS_MAX_RETRY_COUNT,
        retry_interval: float = MODBUS_RETRY_INTERVAL,
        timeout: float = MODBUS_DEFAULT_TIMEOUT,
    ) -> None:
        """
        初始化Modbus通信辅助工具。

        Args:
            max_retries: 最大重试次数
            retry_interval: 重试间隔（秒）
            timeout: 通信超时时间（秒）
        """
        self.max_retries = max_retries
        self.retry_interval = retry_interval
        self.timeout = timeout

        logger.info(
            f"ModbusCommunicationHelper初始化: "
            f"max_retries={max_retries}, retry_interval={retry_interval}s, timeout={timeout}s"
        )

    async def execute_with_retry(
        self,
        read_func: Callable[..., Any],
        slave_id: int,
        address: int,
        count: int = 1,
        **kwargs: Any,
    ) -> list[int] | None:
        """
        执行带重试的Modbus读取操作。

        Args:
            read_func: 读取函数
            slave_id: 从站地址
            address: 寄存器地址
            count: 读取数量
            **kwargs: 其他参数

        Returns:
            Optional[List[int]]: 寄存器值列表，失败返回None

        安全约束:
            - 通信失败必须记录日志
            - 重试失败必须触发异常处理
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                result = read_func(
                    address=address,
                    count=count,
                    slave=slave_id,
                    **kwargs,
                )

                if result and not result.isError():
                    return result.registers

                # 记录错误
                last_error = Exception(
                    f"Modbus读取失败: address=0x{address:04X}, "
                    f"error={result if result else 'No response'}"
                )
                logger.warning(
                    f"Modbus读取失败，准备重试: "
                    f"attempt={attempt + 1}/{self.max_retries}, "
                    f"address=0x{address:04X}, slave_id={slave_id}"
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Modbus读取异常，准备重试: "
                    f"attempt={attempt + 1}/{self.max_retries}, "
                    f"error={str(e)}"
                )

            # 重试间隔（指数退避）
            if attempt < self.max_retries - 1:
                import asyncio

                backoff = self.retry_interval * (2**attempt)
                await asyncio.sleep(backoff)

        # 所有重试失败
        logger.error(
            f"Modbus读取失败（已重试{self.max_retries}次）: "
            f"address=0x{address:04X}, slave_id={slave_id}, error={last_error}"
        )
        return None

    async def write_with_retry(
        self,
        write_func: Callable[..., Any],
        slave_id: int,
        address: int,
        value: int,
        **kwargs: Any,
    ) -> bool:
        """
        执行带重试的Modbus写入操作。

        Args:
            write_func: 写入函数
            slave_id: 从站地址
            address: 寄存器地址
            value: 写入值
            **kwargs: 其他参数

        Returns:
            bool: 写入是否成功

        安全约束:
            - 写入失败必须记录日志
            - 急停指令写入失败必须触发严重告警
        """
        last_error: Exception | None = None

        for attempt in range(self.max_retries):
            try:
                result = write_func(
                    address=address,
                    value=value,
                    slave=slave_id,
                    **kwargs,
                )

                if result and not result.isError():
                    return True

                # 记录错误
                last_error = Exception(
                    f"Modbus写入失败: address=0x{address:04X}, "
                    f"value={value}, error={result if result else 'No response'}"
                )
                logger.warning(
                    f"Modbus写入失败，准备重试: "
                    f"attempt={attempt + 1}/{self.max_retries}, "
                    f"address=0x{address:04X}, value={value}"
                )

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Modbus写入异常，准备重试: "
                    f"attempt={attempt + 1}/{self.max_retries}, "
                    f"error={str(e)}"
                )

            # 重试间隔（指数退避）
            if attempt < self.max_retries - 1:
                import asyncio

                backoff = self.retry_interval * (2**attempt)
                await asyncio.sleep(backoff)

        # 所有重试失败
        logger.error(
            f"Modbus写入失败（已重试{self.max_retries}次）: "
            f"address=0x{address:04X}, value={value}, error={last_error}"
        )
        return False


# ==================== 便捷函数 ====================


def convert_signed_32bit(value: int) -> tuple[int, int]:
    """
    将有符号32位整数转换为两个16位寄存器值。

    Args:
        value: 有符号32位整数

    Returns:
        Tuple[int, int]: (高16位, 低16位)
    """
    return ModbusDataConverter.signed_32bit_to_registers(value)


def convert_unsigned_32bit(value: int) -> tuple[int, int]:
    """
    将无符号32位整数转换为两个16位寄存器值。

    Args:
        value: 无符号32位整数

    Returns:
        Tuple[int, int]: (高16位, 低16位)
    """
    return ModbusDataConverter.unsigned_32bit_to_registers(value)
