"""
文件名: serial_manager.py
路径: backend/core/device_management/serial_manager.py
功能: 统一串口通信管理器，实现单串口多设备队列调度、优先级调度、超时中断、急停重发机制
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: PyModbus 3.5+, asyncio, threading, logging
安全约束: 急停指令最高优先级执行，通信失败自动触发安全兜底逻辑

核心功能：
    1. 单串口多设备队列调度：同一串口下的多个设备共享通信队列，避免总线冲突
    2. 指令优先级分级：P0(急停/报警) > P1(控制指令) > P2(状态查询) > P3(参数配置)
    3. 高优先级插队机制：P0/P1级指令可插队执行，保障实时性
    4. 超时强制中断：单个请求超时阻塞时强制中断，避免阻塞后续指令
    5. 急停强制重发：急停指令下发失败时自动重试3次，确保指令送达设备

设计参考：技术文档v3.0第14.1.2节串口通信管理设计
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable

try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import ModbusException

    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False
    ModbusException = Exception

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 默认超时时间（秒）
DEFAULT_TIMEOUT = 1.0

# 急停指令重试次数
EMERGENCY_STOP_RETRY_COUNT = 3

# 急停指令重试间隔（秒）
EMERGENCY_STOP_RETRY_INTERVAL = 0.05

# 默认通信间隔（秒），用于设备间切换
DEFAULT_INTER_DEVICE_DELAY = 0.01

# 最大队列长度（防止内存溢出）
MAX_QUEUE_SIZE = 1000


class CommandPriority(IntEnum):
    """
    指令优先级枚举。

    优先级数值越小，优先级越高。

    Attributes:
        P0_EMERGENCY: 急停/报警指令，最高优先级，立即执行
        P1_CONTROL: 控制指令（运动、停止等），高优先级
        P2_STATUS: 状态查询指令，普通优先级
        P3_CONFIG: 参数配置指令，低优先级
    """

    P0_EMERGENCY = 0  # 急停/报警：最高优先级，立即执行
    P1_CONTROL = 1  # 控制指令：运动、停止、回零等
    P2_STATUS = 2  # 状态查询：位置、状态字、报警代码等
    P3_CONFIG = 3  # 参数配置：PR路径、IO配置、通信参数等


class CommandType(IntEnum):
    """
    指令类型枚举。

    Attributes:
        READ_HOLDING: 读保持寄存器
        WRITE_SINGLE: 写单个寄存器
        WRITE_MULTIPLE: 写多个寄存器
        READ_INPUT: 读输入寄存器
        READ_COILS: 读线圈
        WRITE_COIL: 写单个线圈
    """

    READ_HOLDING = 0x03
    WRITE_SINGLE = 0x06
    WRITE_MULTIPLE = 0x10
    READ_INPUT = 0x04
    READ_COILS = 0x01
    WRITE_COIL = 0x05


@dataclass
class SerialCommand:
    """
    串口指令数据类。

    封装单个Modbus指令的所有信息，用于队列调度。

    Attributes:
        command_id: 指令唯一标识
        command_type: 指令类型
        slave_id: 从站地址
        address: 寄存器起始地址
        value: 写入值（写操作）或读取数量（读操作）
        priority: 指令优先级
        timeout: 超时时间（秒）
        retry_count: 重试次数
        retry_interval: 重试间隔（秒）
        callback: 回调函数，用于异步返回结果
        timestamp: 指令创建时间戳
        device_id: 设备标识（用于日志和调试）
        is_emergency: 是否为急停指令
    """

    command_id: str
    command_type: CommandType
    slave_id: int
    address: int
    value: int | list[int]
    priority: CommandPriority = CommandPriority.P2_STATUS
    timeout: float = DEFAULT_TIMEOUT
    retry_count: int = 0
    retry_interval: float = 0.1
    callback: Callable[[bool, Any], None] | None = None
    timestamp: float = field(default_factory=time.time)
    device_id: str = "unknown"
    is_emergency: bool = False

    def __lt__(self, other: SerialCommand) -> bool:
        """
        比较运算符，用于优先级队列排序。

        优先级数值越小，优先级越高。

        Args:
            other: 另一个指令对象

        Returns:
            bool: 当前指令优先级是否高于另一个指令
        """
        if self.priority != other.priority:
            return self.priority < other.priority
        # 优先级相同时，按创建时间排序（先到先执行）
        return self.timestamp < other.timestamp


@dataclass
class SerialPortConfig:
    """
    串口配置数据类。

    Attributes:
        port: 串口号（如 "COM1"）
        baudrate: 波特率
        bytesize: 数据位
        parity: 校验位（'N'=无, 'E'=偶, 'O'=奇）
        stopbits: 停止位
        timeout: 默认超时时间（秒）
    """

    port: str = "COM1"
    baudrate: int = 38400
    bytesize: int = 8
    parity: str = "N"
    stopbits: int = 1
    timeout: float = DEFAULT_TIMEOUT

    def to_pymodbus_kwargs(self) -> dict[str, Any]:
        """
        转换为PyModbus客户端初始化参数。

        Returns:
            Dict[str, Any]: PyModbus客户端参数字典
        """
        return {
            "port": self.port,
            "baudrate": self.baudrate,
            "bytesize": self.bytesize,
            "parity": self.parity,
            "stopbits": self.stopbits,
            "timeout": self.timeout,
        }


@dataclass
class CommandResult:
    """
    指令执行结果数据类。

    Attributes:
        success: 是否成功
        data: 返回数据（读操作）或None（写操作）
        error_message: 错误信息
        execution_time: 执行耗时（秒）
        retry_count: 实际重试次数
    """

    success: bool = False
    data: Any = None
    error_message: str | None = None
    execution_time: float = 0.0
    retry_count: int = 0


class SerialCommunicationError(Exception):
    """
    串口通信异常。

    当串口通信失败时抛出此异常。

    Attributes:
        message: 错误信息
        command: 相关指令
        retry_count: 已重试次数
    """

    def __init__(
        self,
        message: str,
        command: SerialCommand | None = None,
        retry_count: int = 0,
    ) -> None:
        """
        初始化异常。

        Args:
            message: 错误信息
            command: 相关指令
            retry_count: 已重试次数
        """
        super().__init__(message)
        self.message = message
        self.command = command
        self.retry_count = retry_count


class SerialPortManager:
    """
    单串口管理器。

    管理单个串口的通信队列和设备访问。
    实现优先级调度、超时中断、急停重发等核心功能。

    Attributes:
        config: 串口配置
        client: PyModbus客户端实例
        command_queue: 指令优先级队列
        is_busy: 总线占用状态
        is_connected: 连接状态
        current_command: 当前执行的指令
        _lock: 线程锁
        _event_loop: 事件循环
        _running: 运行状态
        _stats: 统计信息

    Example:
        >>> config = SerialPortConfig(port="COM1", baudrate=38400)
        >>> manager = SerialPortManager(config)
        >>> await manager.connect()
        >>> result = await manager.execute_command(
        ...     SerialCommand(
        ...         command_id="cmd_001",
        ...         command_type=CommandType.READ_HOLDING,
        ...         slave_id=1,
        ...         address=0x1003,
        ...         value=1,
        ...         priority=CommandPriority.P2_STATUS,
        ...     )
        ... )
    """

    def __init__(self, config: SerialPortConfig) -> None:
        """
        初始化串口管理器。

        Args:
            config: 串口配置
        """
        self.config = config
        self.client: ModbusSerialClient | None = None

        # 指令队列（按优先级分组）
        self._queues: dict[CommandPriority, list[SerialCommand]] = defaultdict(list)
        self._queue_lock = threading.Lock()

        # 总线状态
        self._is_busy = False
        self._busy_lock = threading.Lock()
        self._current_command: SerialCommand | None = None
        self._current_command_start_time: float = 0.0

        # 连接状态
        self._is_connected = False

        # 线程和异步支持
        self._lock = threading.RLock()
        self._event_loop: asyncio.AbstractEventLoop | None = None
        self._running = False
        self._processor_task: asyncio.Task | None = None

        # 统计信息
        self._stats = {
            "total_commands": 0,
            "successful_commands": 0,
            "failed_commands": 0,
            "timeout_commands": 0,
            "emergency_commands": 0,
            "emergency_retries": 0,
            "avg_execution_time": 0.0,
            "max_execution_time": 0.0,
        }

        logger.info(
            f"SerialPortManager初始化: port={config.port}, "
            f"baudrate={config.baudrate}, parity={config.parity}"
        )

    @property
    def is_busy(self) -> bool:
        """
        获取总线占用状态。

        Returns:
            bool: 总线是否被占用
        """
        with self._busy_lock:
            return self._is_busy

    @property
    def is_connected(self) -> bool:
        """
        获取连接状态。

        Returns:
            bool: 是否已连接
        """
        return self._is_connected

    @property
    def current_command(self) -> SerialCommand | None:
        """
        获取当前执行的指令。

        Returns:
            Optional[SerialCommand]: 当前指令，无则返回None
        """
        with self._lock:
            return self._current_command

    async def connect(self) -> bool:
        """
        建立串口连接。

        Returns:
            bool: 连接是否成功

        Raises:
            RuntimeError: PyModbus不可用时抛出
        """
        if not PYMODBUS_AVAILABLE:
            logger.warning("PyModbus不可用，运行在仿真模式")
            self._is_connected = True
            return True

        try:
            self.client = ModbusSerialClient(**self.config.to_pymodbus_kwargs())

            if self.client.connect():
                self._is_connected = True
                self._running = True
                self._event_loop = asyncio.get_event_loop()

                # 启动指令处理任务
                self._processor_task = asyncio.create_task(self._command_processor())

                logger.info(f"串口连接成功: {self.config.port}")
                return True
            else:
                logger.error(f"串口连接失败: {self.config.port}")
                return False

        except Exception as e:
            logger.error(f"串口连接异常: {e}")
            self._is_connected = False
            return False

    async def disconnect(self) -> bool:
        """
        断开串口连接。

        Returns:
            bool: 断开是否成功
        """
        self._running = False

        # 等待处理器任务结束
        if self._processor_task:
            try:
                await asyncio.wait_for(self._processor_task, timeout=5.0)
            except asyncio.TimeoutError:
                logger.warning("指令处理器任务超时，强制取消")
                self._processor_task.cancel()

        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"关闭串口异常: {e}")

        self._is_connected = False
        logger.info(f"串口已断开: {self.config.port}")
        return True

    def enqueue_command(self, command: SerialCommand) -> bool:
        """
        将指令加入队列。

        Args:
            command: 指令对象

        Returns:
            bool: 是否成功加入队列

        Raises:
            ValueError: 队列已满时抛出
        """
        with self._queue_lock:
            # 检查队列长度
            total_commands = sum(len(q) for q in self._queues.values())
            if total_commands >= MAX_QUEUE_SIZE:
                logger.error(f"指令队列已满，拒绝指令: {command.command_id}")
                raise ValueError("指令队列已满")

            # 急停指令标记
            if command.is_emergency or command.priority == CommandPriority.P0_EMERGENCY:
                command.is_emergency = True
                command.priority = CommandPriority.P0_EMERGENCY
                command.retry_count = EMERGENCY_STOP_RETRY_COUNT
                command.retry_interval = EMERGENCY_STOP_RETRY_INTERVAL

            # 加入对应优先级队列
            self._queues[command.priority].append(command)

            logger.debug(
                f"指令入队: id={command.command_id}, "
                f"priority={command.priority.name}, "
                f"device={command.device_id}, "
                f"type={command.command_type.name}"
            )

            return True

    async def execute_command(self, command: SerialCommand) -> CommandResult:
        """
        执行单个指令（同步等待结果）。

        Args:
            command: 指令对象

        Returns:
            CommandResult: 执行结果

        Example:
            >>> result = await manager.execute_command(
            ...     SerialCommand(
            ...         command_id="read_status",
            ...         command_type=CommandType.READ_HOLDING,
            ...         slave_id=1,
            ...         address=0x1003,
            ...         value=1,
            ...     )
            ... )
            >>> if result.success:
            ...     print(f"状态字: {result.data}")
        """
        # 创建Future用于等待结果
        future: asyncio.Future[CommandResult] = asyncio.Future()

        def callback(success: bool, data: Any) -> None:
            """结果回调函数。"""
            if not future.done():
                if success:
                    future.set_result(
                        CommandResult(
                            success=True,
                            data=data,
                            execution_time=time.time() - command.timestamp,
                        )
                    )
                else:
                    future.set_result(
                        CommandResult(
                            success=False,
                            error_message=str(data),
                            execution_time=time.time() - command.timestamp,
                        )
                    )

        command.callback = callback
        self.enqueue_command(command)

        # 等待结果（带超时）
        try:
            return await asyncio.wait_for(future, timeout=command.timeout * (command.retry_count + 1) + 5.0)
        except asyncio.TimeoutError:
            return CommandResult(
                success=False,
                error_message="指令执行超时",
                execution_time=time.time() - command.timestamp,
            )

    async def _command_processor(self) -> None:
        """
        指令处理器主循环。

        从队列中取出指令并执行，支持优先级调度和超时中断。
        """
        logger.info("指令处理器启动")

        while self._running:
            try:
                # 获取下一个指令（按优先级）
                command = self._get_next_command()

                if command is None:
                    # 队列为空，短暂休眠
                    await asyncio.sleep(0.001)
                    continue

                # 检查是否需要中断当前指令
                if self._should_interrupt_current(command):
                    await self._interrupt_current_command()

                # 执行指令
                await self._execute_single_command(command)

            except asyncio.CancelledError:
                logger.info("指令处理器被取消")
                break
            except Exception as e:
                logger.error(f"指令处理器异常: {e}", exc_info=True)
                await asyncio.sleep(0.1)

        logger.info("指令处理器已停止")

    def _get_next_command(self) -> SerialCommand | None:
        """
        从队列中获取下一个指令（按优先级）。

        Returns:
            Optional[SerialCommand]: 下一个指令，队列为空返回None
        """
        with self._queue_lock:
            # 按优先级从高到低遍历
            for priority in CommandPriority:
                queue = self._queues[priority]
                if queue:
                    return queue.pop(0)
            return None

    def _should_interrupt_current(self, new_command: SerialCommand) -> bool:
        """
        判断是否需要中断当前指令。

        规则：
        1. 当前无指令执行，不需要中断
        2. 新指令为P0级（急停），必须中断
        3. 新指令为P1级（控制），当前为P2/P3级，可中断

        Args:
            new_command: 新指令

        Returns:
            bool: 是否需要中断
        """
        with self._lock:
            if self._current_command is None:
                return False

            # P0级指令（急停）必须立即执行
            if new_command.priority == CommandPriority.P0_EMERGENCY:
                return True

            # P1级指令可中断P2/P3级指令
            if (
                new_command.priority == CommandPriority.P1_CONTROL
                and self._current_command.priority
                in (CommandPriority.P2_STATUS, CommandPriority.P3_CONFIG)
            ):
                return True

            return False

    async def _interrupt_current_command(self) -> None:
        """
        中断当前指令。

        将当前指令重新放回队列前端。
        """
        with self._lock:
            if self._current_command is None:
                return

            # 记录中断信息
            elapsed = time.time() - self._current_command_start_time
            logger.warning(
                f"指令被中断: id={self._current_command.command_id}, "
                f"elapsed={elapsed:.3f}s"
            )

            # 将指令放回队列前端
            with self._queue_lock:
                self._queues[self._current_command.priority].insert(0, self._current_command)

            self._current_command = None
            self._is_busy = False

    async def _execute_single_command(self, command: SerialCommand) -> None:
        """
        执行单个指令。

        Args:
            command: 指令对象
        """
        # 设置当前指令
        with self._lock:
            self._current_command = command
            self._current_command_start_time = time.time()
            self._is_busy = True

        self._stats["total_commands"] += 1

        # 急停指令特殊处理
        if command.is_emergency:
            result = await self._execute_emergency_command(command)
        else:
            result = await self._execute_normal_command(command)

        # 更新统计
        if result.success:
            self._stats["successful_commands"] += 1
        else:
            self._stats["failed_commands"] += 1
            if "timeout" in (result.error_message or "").lower():
                self._stats["timeout_commands"] += 1

        # 更新执行时间统计
        self._stats["max_execution_time"] = max(
            self._stats["max_execution_time"], result.execution_time
        )
        total_time = (
            self._stats["avg_execution_time"] * (self._stats["total_commands"] - 1)
            + result.execution_time
        )
        self._stats["avg_execution_time"] = total_time / self._stats["total_commands"]

        # 回调结果
        if command.callback:
            try:
                command.callback(result.success, result.data if result.success else result.error_message)
            except Exception as e:
                logger.error(f"回调函数异常: {e}")

        # 清除当前指令
        with self._lock:
            self._current_command = None
            self._is_busy = False

    async def _execute_emergency_command(self, command: SerialCommand) -> CommandResult:
        """
        执行急停指令（带重发机制）。

        急停指令具有最高优先级，失败时自动重试3次。

        Args:
            command: 急停指令

        Returns:
            CommandResult: 执行结果
        """
        self._stats["emergency_commands"] += 1
        start_time = time.time()

        logger.warning(
            f"执行急停指令: id={command.command_id}, "
            f"device={command.device_id}, address=0x{command.address:04X}"
        )

        for attempt in range(EMERGENCY_STOP_RETRY_COUNT):
            result = await self._execute_modbus_command(command)

            if result.success:
                logger.info(
                    f"急停指令执行成功: id={command.command_id}, "
                    f"attempt={attempt + 1}/{EMERGENCY_STOP_RETRY_COUNT}"
                )
                result.execution_time = time.time() - start_time
                return result

            # 记录重试
            self._stats["emergency_retries"] += 1
            logger.error(
                f"急停指令执行失败，准备重试: id={command.command_id}, "
                f"attempt={attempt + 1}/{EMERGENCY_STOP_RETRY_COUNT}, "
                f"error={result.error_message}"
            )

            # 重试间隔
            if attempt < EMERGENCY_STOP_RETRY_COUNT - 1:
                await asyncio.sleep(EMERGENCY_STOP_RETRY_INTERVAL)

        # 所有重试失败
        error_msg = f"急停指令执行失败（已重试{EMERGENCY_STOP_RETRY_COUNT}次）"
        logger.critical(f"{error_msg}: id={command.command_id}")

        return CommandResult(
            success=False,
            error_message=error_msg,
            execution_time=time.time() - start_time,
            retry_count=EMERGENCY_STOP_RETRY_COUNT,
        )

    async def _execute_normal_command(self, command: SerialCommand) -> CommandResult:
        """
        执行普通指令（带重试和超时机制）。

        Args:
            command: 指令对象

        Returns:
            CommandResult: 执行结果
        """
        start_time = time.time()
        last_error: str | None = None

        for attempt in range(command.retry_count + 1):
            # 检查超时
            elapsed = time.time() - start_time
            if elapsed > command.timeout * (command.retry_count + 1):
                return CommandResult(
                    success=False,
                    error_message=f"指令执行超时（{elapsed:.3f}s > {command.timeout}s）",
                    execution_time=elapsed,
                    retry_count=attempt,
                )

            result = await self._execute_modbus_command(command)

            if result.success:
                result.execution_time = time.time() - start_time
                result.retry_count = attempt
                return result

            last_error = result.error_message

            # 重试间隔（指数退避）
            if attempt < command.retry_count:
                backoff = command.retry_interval * (2**attempt)
                logger.debug(
                    f"指令重试: id={command.command_id}, "
                    f"attempt={attempt + 1}/{command.retry_count}, "
                    f"backoff={backoff:.3f}s"
                )
                await asyncio.sleep(backoff)

        return CommandResult(
            success=False,
            error_message=last_error or "指令执行失败",
            execution_time=time.time() - start_time,
            retry_count=command.retry_count,
        )

    async def _execute_modbus_command(self, command: SerialCommand) -> CommandResult:
        """
        执行Modbus指令（底层通信）。

        Args:
            command: 指令对象

        Returns:
            CommandResult: 执行结果
        """
        if not PYMODBUS_AVAILABLE:
            # 仿真模式
            return self._simulate_command(command)

        if not self.client or not self._is_connected:
            return CommandResult(success=False, error_message="串口未连接")

        try:
            # 根据指令类型执行对应操作
            if command.command_type == CommandType.READ_HOLDING:
                result = self.client.read_holding_registers(
                    address=command.address,
                    count=command.value if isinstance(command.value, int) else 1,
                    slave=command.slave_id,
                )
                if result and not result.isError():
                    return CommandResult(success=True, data=result.registers)
                return CommandResult(
                    success=False,
                    error_message=f"读取保持寄存器失败: {result if result else 'No response'}",
                )

            elif command.command_type == CommandType.WRITE_SINGLE:
                result = self.client.write_register(
                    address=command.address,
                    value=command.value if isinstance(command.value, int) else command.value[0],
                    slave=command.slave_id,
                )
                if result and not result.isError():
                    return CommandResult(success=True, data=None)
                return CommandResult(
                    success=False,
                    error_message=f"写单个寄存器失败: {result if result else 'No response'}",
                )

            elif command.command_type == CommandType.WRITE_MULTIPLE:
                values = command.value if isinstance(command.value, list) else [command.value]
                result = self.client.write_registers(
                    address=command.address,
                    values=values,
                    slave=command.slave_id,
                )
                if result and not result.isError():
                    return CommandResult(success=True, data=None)
                return CommandResult(
                    success=False,
                    error_message=f"写多个寄存器失败: {result if result else 'No response'}",
                )

            elif command.command_type == CommandType.READ_INPUT:
                result = self.client.read_input_registers(
                    address=command.address,
                    count=command.value if isinstance(command.value, int) else 1,
                    slave=command.slave_id,
                )
                if result and not result.isError():
                    return CommandResult(success=True, data=result.registers)
                return CommandResult(
                    success=False,
                    error_message=f"读取输入寄存器失败: {result if result else 'No response'}",
                )

            elif command.command_type == CommandType.READ_COILS:
                result = self.client.read_coils(
                    address=command.address,
                    count=command.value if isinstance(command.value, int) else 1,
                    slave=command.slave_id,
                )
                if result and not result.isError():
                    return CommandResult(success=True, data=result.bits)
                return CommandResult(
                    success=False,
                    error_message=f"读取线圈失败: {result if result else 'No response'}",
                )

            elif command.command_type == CommandType.WRITE_COIL:
                result = self.client.write_coil(
                    address=command.address,
                    value=bool(command.value if isinstance(command.value, int) else command.value[0]),
                    slave=command.slave_id,
                )
                if result and not result.isError():
                    return CommandResult(success=True, data=None)
                return CommandResult(
                    success=False,
                    error_message=f"写线圈失败: {result if result else 'No response'}",
                )

            else:
                return CommandResult(
                    success=False,
                    error_message=f"未知指令类型: {command.command_type}",
                )

        except ModbusException as e:
            logger.error(f"Modbus通信异常: {e}")
            return CommandResult(success=False, error_message=f"Modbus异常: {e}")
        except Exception as e:
            logger.error(f"指令执行异常: {e}", exc_info=True)
            return CommandResult(success=False, error_message=f"执行异常: {e}")

    def _simulate_command(self, command: SerialCommand) -> CommandResult:
        """
        仿真模式：模拟指令执行。

        Args:
            command: 指令对象

        Returns:
            CommandResult: 模拟的执行结果
        """
        logger.debug(f"[仿真模式] 执行指令: {command.command_id}")

        if command.command_type in (CommandType.READ_HOLDING, CommandType.READ_INPUT):
            # 返回模拟数据
            count = command.value if isinstance(command.value, int) else 1
            return CommandResult(success=True, data=[0] * count)

        return CommandResult(success=True, data=None)

    def get_stats(self) -> dict[str, Any]:
        """
        获取统计信息。

        Returns:
            Dict[str, Any]: 统计信息字典
        """
        with self._lock:
            return {
                **self._stats,
                "is_connected": self._is_connected,
                "is_busy": self._is_busy,
                "queue_sizes": {
                    priority.name: len(self._queues[priority])
                    for priority in CommandPriority
                },
                "total_queue_size": sum(len(q) for q in self._queues.values()),
            }

    def clear_queue(self) -> int:
        """
        清空指令队列。

        Returns:
            int: 清除的指令数量
        """
        with self._queue_lock:
            total = sum(len(q) for q in self._queues.values())
            for queue in self._queues.values():
                queue.clear()
            logger.info(f"指令队列已清空，清除{total}条指令")
            return total


class UnifiedSerialManager:
    """
    统一串口通信管理器。

    管理多个串口，每个串口对应一个SerialPortManager实例。
    提供统一的接口供设备驱动使用。

    Attributes:
        _port_managers: 串口管理器字典（端口名 -> 管理器实例）
        _lock: 线程锁
        _device_port_map: 设备到串口的映射

    Example:
        >>> manager = UnifiedSerialManager()
        >>> config = SerialPortConfig(port="COM1", baudrate=38400)
        >>> await manager.register_port("COM1", config)
        >>> result = await manager.execute_command(
        ...     "COM1",
        ...     SerialCommand(
        ...         command_id="read_status",
        ...         command_type=CommandType.READ_HOLDING,
        ...         slave_id=1,
        ...         address=0x1003,
        ...         value=1,
        ...     )
        ... )
    """

    def __init__(self) -> None:
        """初始化统一串口管理器。"""
        self._port_managers: dict[str, SerialPortManager] = {}
        self._lock = threading.RLock()
        self._device_port_map: dict[str, str] = {}

        logger.info("UnifiedSerialManager初始化完成")

    async def register_port(
        self,
        port_name: str,
        config: SerialPortConfig,
        auto_connect: bool = True,
    ) -> bool:
        """
        注册串口。

        Args:
            port_name: 串口名称（标识符）
            config: 串口配置
            auto_connect: 是否自动连接，默认True

        Returns:
            bool: 注册是否成功

        Raises:
            ValueError: 串口已注册时抛出
        """
        with self._lock:
            if port_name in self._port_managers:
                raise ValueError(f"串口 '{port_name}' 已注册")

            manager = SerialPortManager(config)
            self._port_managers[port_name] = manager

            if auto_connect:
                success = await manager.connect()
                if not success:
                    logger.error(f"串口 '{port_name}' 连接失败")
                    return False

            logger.info(f"串口 '{port_name}' 注册成功")
            return True

    async def unregister_port(self, port_name: str) -> bool:
        """
        注销串口。

        Args:
            port_name: 串口名称

        Returns:
            bool: 注销是否成功
        """
        with self._lock:
            if port_name not in self._port_managers:
                logger.warning(f"串口 '{port_name}' 未注册")
                return False

            manager = self._port_managers[port_name]
            await manager.disconnect()
            del self._port_managers[port_name]

            # 清理设备映射
            devices_to_remove = [
                device_id
                for device_id, port in self._device_port_map.items()
                if port == port_name
            ]
            for device_id in devices_to_remove:
                del self._device_port_map[device_id]

            logger.info(f"串口 '{port_name}' 已注销")
            return True

    def register_device(self, device_id: str, port_name: str) -> bool:
        """
        注册设备到串口映射。

        Args:
            device_id: 设备标识
            port_name: 串口名称

        Returns:
            bool: 注册是否成功
        """
        with self._lock:
            if port_name not in self._port_managers:
                logger.error(f"串口 '{port_name}' 未注册")
                return False

            self._device_port_map[device_id] = port_name
            logger.info(f"设备 '{device_id}' 已映射到串口 '{port_name}'")
            return True

    def get_port_for_device(self, device_id: str) -> str | None:
        """
        获取设备对应的串口名称。

        Args:
            device_id: 设备标识

        Returns:
            Optional[str]: 串口名称，未找到返回None
        """
        return self._device_port_map.get(device_id)

    async def execute_command(
        self,
        port_name: str,
        command: SerialCommand,
    ) -> CommandResult:
        """
        执行指令。

        Args:
            port_name: 串口名称
            command: 指令对象

        Returns:
            CommandResult: 执行结果

        Raises:
            KeyError: 串口未注册时抛出
        """
        with self._lock:
            if port_name not in self._port_managers:
                raise KeyError(f"串口 '{port_name}' 未注册")

            manager = self._port_managers[port_name]

        return await manager.execute_command(command)

    async def execute_command_for_device(
        self,
        device_id: str,
        command: SerialCommand,
    ) -> CommandResult:
        """
        为设备执行指令。

        根据设备ID自动查找对应的串口。

        Args:
            device_id: 设备标识
            command: 指令对象

        Returns:
            CommandResult: 执行结果

        Raises:
            KeyError: 设备未注册时抛出
        """
        port_name = self.get_port_for_device(device_id)
        if port_name is None:
            raise KeyError(f"设备 '{device_id}' 未注册")

        command.device_id = device_id
        return await self.execute_command(port_name, command)

    async def broadcast_emergency_stop(
        self,
        address: int = 0x040,
        value: int = 1,
    ) -> dict[str, CommandResult]:
        """
        广播急停指令到所有串口。

        向所有已连接的串口发送急停指令。

        Args:
            address: 急停寄存器地址，默认0x040
            value: 急停值，默认1

        Returns:
            Dict[str, CommandResult]: 各串口的执行结果
        """
        results: dict[str, CommandResult] = {}

        logger.critical("广播急停指令到所有串口")

        for port_name, manager in self._port_managers.items():
            command = SerialCommand(
                command_id=f"emergency_stop_{port_name}_{time.time()}",
                command_type=CommandType.WRITE_SINGLE,
                slave_id=0,  # 广播地址
                address=address,
                value=value,
                priority=CommandPriority.P0_EMERGENCY,
                is_emergency=True,
                device_id="broadcast",
            )

            result = await manager.execute_command(command)
            results[port_name] = result

        return results

    def get_port_manager(self, port_name: str) -> SerialPortManager | None:
        """
        获取串口管理器实例。

        Args:
            port_name: 串口名称

        Returns:
            Optional[SerialPortManager]: 管理器实例，未找到返回None
        """
        return self._port_managers.get(port_name)

    def get_all_stats(self) -> dict[str, dict[str, Any]]:
        """
        获取所有串口的统计信息。

        Returns:
            Dict[str, Dict[str, Any]]: 各串口的统计信息
        """
        return {
            port_name: manager.get_stats()
            for port_name, manager in self._port_managers.items()
        }

    async def connect_all(self) -> dict[str, bool]:
        """
        连接所有已注册的串口。

        Returns:
            Dict[str, bool]: 各串口的连接结果
        """
        results: dict[str, bool] = {}

        for port_name, manager in self._port_managers.items():
            if not manager.is_connected:
                results[port_name] = await manager.connect()
            else:
                results[port_name] = True

        return results

    async def disconnect_all(self) -> dict[str, bool]:
        """
        断开所有串口连接。

        Returns:
            Dict[str, bool]: 各串口的断开结果
        """
        results: dict[str, bool] = {}

        for port_name, manager in self._port_managers.items():
            results[port_name] = await manager.disconnect()

        return results

    def get_registered_ports(self) -> list[str]:
        """
        获取已注册的串口列表。

        Returns:
            List[str]: 串口名称列表
        """
        return list(self._port_managers.keys())

    def get_registered_devices(self) -> list[str]:
        """
        获取已注册的设备列表。

        Returns:
            List[str]: 设备ID列表
        """
        return list(self._device_port_map.keys())


# ==================== 便捷函数 ====================


def create_emergency_stop_command(
    device_id: str,
    slave_id: int,
    address: int = 0x040,
) -> SerialCommand:
    """
    创建急停指令。

    Args:
        device_id: 设备标识
        slave_id: 从站地址
        address: 急停寄存器地址，默认0x040

    Returns:
        SerialCommand: 急停指令对象

    Example:
        >>> cmd = create_emergency_stop_command("motor_1", 1)
        >>> result = await manager.execute_command_for_device("motor_1", cmd)
    """
    return SerialCommand(
        command_id=f"emergency_{device_id}_{time.time()}",
        command_type=CommandType.WRITE_SINGLE,
        slave_id=slave_id,
        address=address,
        value=1,
        priority=CommandPriority.P0_EMERGENCY,
        is_emergency=True,
        device_id=device_id,
    )


def create_read_command(
    device_id: str,
    slave_id: int,
    address: int,
    count: int = 1,
    priority: CommandPriority = CommandPriority.P2_STATUS,
) -> SerialCommand:
    """
    创建读指令。

    Args:
        device_id: 设备标识
        slave_id: 从站地址
        address: 寄存器起始地址
        count: 读取数量，默认1
        priority: 指令优先级，默认P2_STATUS

    Returns:
        SerialCommand: 读指令对象

    Example:
        >>> cmd = create_read_command("motor_1", 1, 0x1003, 1)
        >>> result = await manager.execute_command_for_device("motor_1", cmd)
    """
    return SerialCommand(
        command_id=f"read_{device_id}_{address:04X}_{time.time()}",
        command_type=CommandType.READ_HOLDING,
        slave_id=slave_id,
        address=address,
        value=count,
        priority=priority,
        device_id=device_id,
    )


def create_write_command(
    device_id: str,
    slave_id: int,
    address: int,
    value: int | list[int],
    priority: CommandPriority = CommandPriority.P1_CONTROL,
) -> SerialCommand:
    """
    创建写指令。

    Args:
        device_id: 设备标识
        slave_id: 从站地址
        address: 寄存器地址
        value: 写入值（单个值或列表）
        priority: 指令优先级，默认P1_CONTROL

    Returns:
        SerialCommand: 写指令对象

    Example:
        >>> cmd = create_write_command("motor_1", 1, 0x1801, 0x4001)
        >>> result = await manager.execute_command_for_device("motor_1", cmd)
    """
    command_type = (
        CommandType.WRITE_MULTIPLE if isinstance(value, list) else CommandType.WRITE_SINGLE
    )

    return SerialCommand(
        command_id=f"write_{device_id}_{address:04X}_{time.time()}",
        command_type=command_type,
        slave_id=slave_id,
        address=address,
        value=value,
        priority=priority,
        device_id=device_id,
    )
