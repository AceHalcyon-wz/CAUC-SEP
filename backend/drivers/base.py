"""
文件名: base.py
路径: backend/drivers/
功能: 驱动进程基类，提供进程化驱动的基础框架
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: multiprocessing, asyncio, logging, typing
"""

import asyncio
import logging
import multiprocessing as mp
import signal
import sys
import time
import traceback
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from multiprocessing.queues import Queue as MPQueue
from typing import Any, TypeVar

# 设置Windows多进程支持
if sys.platform == "win32":
    mp.set_start_method("spawn", force=True)

logger = logging.getLogger(__name__)

T = TypeVar("T")


class DriverProcessState(Enum):
    """驱动进程状态枚举。

    状态机说明：
        STOPPED → STARTING → RUNNING → STOPPING → STOPPED
        任何状态都可能转变为 ERROR
    """

    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
    RESTARTING = "restarting"


class IPCMessageType(Enum):
    """IPC消息类型枚举。

    定义进程间通信的消息类型，用于区分不同类型的消息处理逻辑。

    Attributes:
        COMMAND: 控制命令，携带具体操作指令
        STOP: 停止命令，通知驱动进程停止运行
        RESTART: 重启命令，通知驱动进程重启
        PING: 心跳检测命令，用于检测进程存活状态
        STATUS: 状态报告，驱动进程主动上报状态
        HEARTBEAT: 心跳消息，定时发送以维持连接
        ERROR: 错误消息，报告异常情况
        LOG: 日志消息，传递日志记录
        DATA: 数据消息，传输业务数据
        RESPONSE: 响应消息，对命令的响应
    """

    # 控制命令
    COMMAND = "command"
    STOP = "stop"
    RESTART = "restart"
    PING = "ping"

    # 状态报告
    STATUS = "status"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    LOG = "log"

    # 数据传输
    DATA = "data"
    RESPONSE = "response"


@dataclass
class IPCMessage:
    """IPC消息数据类。

    用于进程间通信的消息封装。

    Attributes:
        msg_type: 消息类型
        payload: 消息负载
        timestamp: 时间戳
        source: 消息来源
        request_id: 请求ID（用于请求-响应模式）
    """

    msg_type: IPCMessageType
    payload: Any = None
    timestamp: float = field(default_factory=time.time)
    source: str = "driver_process"
    request_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。

        Returns:
            Dict[str, Any]: 序列化后的字典
        """
        return {
            "msg_type": self.msg_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "source": self.source,
            "request_id": self.request_id,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IPCMessage":
        """从字典反序列化。

        Args:
            data: 字典数据

        Returns:
            IPCMessage: 消息实例
        """
        return cls(
            msg_type=IPCMessageType(data["msg_type"]),
            payload=data.get("payload"),
            timestamp=data.get("timestamp", time.time()),
            source=data.get("source", "unknown"),
            request_id=data.get("request_id"),
        )


@dataclass
class DriverProcessConfig:
    """驱动进程配置数据类。

    封装驱动进程的所有配置参数，用于进程创建和生命周期管理。

    Attributes:
        driver_id: 驱动唯一标识符，用于日志和消息路由
        driver_name: 驱动名称，用于人类可读的标识
        config: 驱动配置字典，包含设备端口、参数等具体配置
        auto_restart: 是否在异常退出时自动重启，默认True
        max_restart_count: 最大重启次数，超过后不再重启，默认3次
        restart_delay: 重启延迟时间（秒），避免频繁重启，默认5.0秒
        heartbeat_interval: 心跳发送间隔（秒），默认10.0秒
        heartbeat_timeout: 心跳超时时间（秒），超时判定进程异常，默认30.0秒

    Example:
        >>> config = DriverProcessConfig(
        ...     driver_id="motor_1",
        ...     driver_name="DM2C步进电机",
        ...     config={"port": "COM1", "slave_id": 1},
        ...     auto_restart=True,
        ...     max_restart_count=5,
        ... )
    """

    driver_id: str
    driver_name: str
    config: dict[str, Any] = field(default_factory=dict)
    auto_restart: bool = True
    max_restart_count: int = 3
    restart_delay: float = 5.0
    heartbeat_interval: float = 10.0
    heartbeat_timeout: float = 30.0


class DriverProcessBase(ABC):
    """驱动进程基类。

    提供进程化驱动的基础框架，包括：
    - 进程生命周期管理
    - IPC通信机制
    - 心跳监控
    - 错误处理和自动重启

    子类需要实现：
    - initialize(): 初始化驱动实例
    - cleanup(): 清理驱动资源
    - handle_command(): 处理自定义命令

    Example:
        >>> class MyDriverProcess(DriverProcessBase):
        ...     async def initialize(self) -> bool:
        ...         self.driver = MyDriver(self.config)
        ...         return await self.driver.connect()
        ...
        ...     async def cleanup(self) -> None:
        ...         if self.driver:
        ...             await self.driver.disconnect()
        ...
        ...     async def handle_command(self, command: str, params: Dict) -> Any:
        ...         if command == "do_something":
        ...             return await self.driver.do_something(**params)
        ...         return None
    """

    def __init__(
        self,
        driver_id: str,
        config: dict[str, Any],
        command_queue: MPQueue,
        response_queue: MPQueue,
        heartbeat_interval: float = 10.0,
    ):
        """初始化驱动进程基类。

        Args:
            driver_id: 驱动ID
            config: 驱动配置
            command_queue: 命令队列（从主进程接收命令）
            response_queue: 响应队列（向主进程发送响应）
            heartbeat_interval: 心跳间隔（秒）
        """
        self.driver_id = driver_id
        self.config = config
        self.command_queue = command_queue
        self.response_queue = response_queue
        self.heartbeat_interval = heartbeat_interval

        # 状态
        self._running = False
        self._state = DriverProcessState.STOPPED
        self._last_error: str | None = None
        self._driver: Any = None

        # 设置日志
        self._setup_logging()

    def _setup_logging(self) -> None:
        """设置子进程日志配置。

        配置子进程独立的日志记录器，包含驱动ID前缀以便区分不同驱动进程的日志。
        日志格式: [Driver:{driver_id}] 时间 - 级别 - 消息
        """
        logging.basicConfig(
            level=logging.INFO,
            format=f"[Driver:{self.driver_id}] %(asctime)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(f"driver_process.{self.driver_id}")

    def run(self) -> None:
        """进程入口点。

        此方法由multiprocessing.Process调用，不应直接调用。
        """
        self.logger.info(f"驱动进程启动，PID: {mp.current_process().pid}")

        # 注册信号处理
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

        # 运行事件循环
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self._main_loop())
        except Exception as e:
            self.logger.error(f"事件循环异常: {e}\n{traceback.format_exc()}")
            self._send_error(str(e))
        finally:
            loop.close()
            self.logger.info(f"驱动进程 {self.driver_id} 已退出")

    def _handle_signal(self, signum: int, frame) -> None:
        """处理终止信号。

        接收到SIGTERM或SIGINT信号时，设置运行标志为False，触发优雅退出流程。

        Args:
            signum: 信号编号
            frame: 当前栈帧
        """
        self.logger.info(f"收到信号 {signum}，准备退出")
        self._running = False

    async def _main_loop(self) -> None:
        """主事件循环。

        驱动进程的核心运行循环，执行以下操作：
        1. 调用initialize()初始化驱动
        2. 循环处理命令队列消息
        3. 定期发送心跳
        4. 执行周期性任务
        5. 退出时调用cleanup()清理资源

        状态转换:
            STOPPED → STARTING → RUNNING → STOPPING → STOPPED
        """
        self._running = True
        self._state = DriverProcessState.STARTING

        # 初始化驱动
        if not await self.initialize():
            self._state = DriverProcessState.ERROR
            return

        self._state = DriverProcessState.RUNNING
        self._send_status("initialized")

        last_heartbeat = time.time()

        while self._running:
            try:
                # 处理命令队列
                await self._process_commands()

                # 发送心跳
                if time.time() - last_heartbeat >= self.heartbeat_interval:
                    await self._send_heartbeat()
                    last_heartbeat = time.time()

                # 执行周期性任务
                await self.periodic_task()

                # 短暂休眠
                await asyncio.sleep(0.1)

            except Exception as e:
                self.logger.error(f"主循环异常: {e}\n{traceback.format_exc()}")
                self._send_error(str(e))

        # 清理资源
        await self.cleanup()
        self._state = DriverProcessState.STOPPED

    async def _process_commands(self) -> None:
        """处理命令队列中的消息。

        非阻塞地从命令队列获取消息，解析并处理，将响应放入响应队列。
        使用get_nowait()避免阻塞事件循环。
        """
        try:
            if not self.command_queue.empty():
                msg = self.command_queue.get_nowait()
                if isinstance(msg, dict):
                    msg = IPCMessage.from_dict(msg)

                response = await self._handle_message(msg)
                if response:
                    self.response_queue.put(response)
        except Exception as e:
            self.logger.error(f"处理命令异常: {e}")

    async def _handle_message(self, msg: IPCMessage) -> IPCMessage | None:
        """处理IPC消息。

        Args:
            msg: IPC消息

        Returns:
            Optional[IPCMessage]: 响应消息
        """
        if msg.msg_type == IPCMessageType.STOP:
            self.logger.info("收到停止命令")
            self._running = False
            return IPCMessage(
                msg_type=IPCMessageType.RESPONSE,
                payload={"success": True, "action": "stop"},
                source=self.driver_id,
                request_id=msg.request_id,
            )

        elif msg.msg_type == IPCMessageType.PING:
            return IPCMessage(
                msg_type=IPCMessageType.RESPONSE,
                payload={"pong": True, "state": self._state.value},
                source=self.driver_id,
                request_id=msg.request_id,
            )

        elif msg.msg_type == IPCMessageType.COMMAND:
            command = msg.payload.get("command")
            params = msg.payload.get("params", {})

            try:
                result = await self.handle_command(command, params)
                return IPCMessage(
                    msg_type=IPCMessageType.RESPONSE,
                    payload={"success": True, "result": result},
                    source=self.driver_id,
                    request_id=msg.request_id,
                )
            except Exception as e:
                self.logger.error(f"命令执行失败: {command}, 错误: {e}")
                return IPCMessage(
                    msg_type=IPCMessageType.ERROR,
                    payload={"error": str(e), "command": command},
                    source=self.driver_id,
                    request_id=msg.request_id,
                )

        return None

    async def _send_heartbeat(self) -> None:
        """发送心跳消息。

        向主进程发送心跳消息，包含驱动ID、当前状态和时间戳。
        主进程通过心跳消息监控驱动进程的存活状态。
        """
        self.response_queue.put(
            IPCMessage(
                msg_type=IPCMessageType.HEARTBEAT,
                payload={
                    "driver_id": self.driver_id,
                    "state": self._state.value,
                    "timestamp": time.time(),
                },
                source=self.driver_id,
            )
        )

    def _send_status(self, status: str) -> None:
        """发送状态消息。

        向主进程发送状态更新消息。

        Args:
            status: 状态描述字符串
        """
        self.response_queue.put(
            IPCMessage(
                msg_type=IPCMessageType.STATUS,
                payload={"status": status, "driver_id": self.driver_id},
                source=self.driver_id,
            )
        )

    def _send_error(self, error: str) -> None:
        """发送错误消息。

        向主进程发送错误报告消息。

        Args:
            error: 错误描述字符串
        """
        self.response_queue.put(
            IPCMessage(
                msg_type=IPCMessageType.ERROR,
                payload={"error": error, "driver_id": self.driver_id},
                source=self.driver_id,
            )
        )

    # ==================== 抽象方法 ====================

    @abstractmethod
    async def initialize(self) -> bool:
        """初始化驱动实例。

        Returns:
            bool: 初始化是否成功
        """
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """清理驱动资源。"""
        pass

    @abstractmethod
    async def handle_command(self, command: str, params: dict[str, Any]) -> Any:
        """处理自定义命令。

        Args:
            command: 命令名称
            params: 命令参数

        Returns:
            Any: 命令执行结果
        """
        pass

    # ==================== 可选方法 ====================

    async def periodic_task(self) -> None:
        """周期性任务。

        子类可重写此方法实现周期性任务，如数据采集、状态更新等。
        """
        pass


def create_driver_process(
    driver_process_class: type[DriverProcessBase],
    driver_id: str,
    config: dict[str, Any],
    command_queue: MPQueue,
    response_queue: MPQueue,
    heartbeat_interval: float = 10.0,
) -> mp.Process:
    """创建驱动进程。

    Args:
        driver_process_class: 驱动进程类
        driver_id: 驱动ID
        config: 驱动配置
        command_queue: 命令队列
        response_queue: 响应队列
        heartbeat_interval: 心跳间隔

    Returns:
        mp.Process: 进程对象

    Example:
        >>> process = create_driver_process(
        ...     DM2CDriverProcess,
        ...     "motor_1",
        ...     {"port": "COM1", "slave_id": 1},
        ...     command_queue,
        ...     response_queue,
        ... )
        >>> process.start()
    """
    # 创建驱动进程实例
    driver_instance = driver_process_class(
        driver_id=driver_id,
        config=config,
        command_queue=command_queue,
        response_queue=response_queue,
        heartbeat_interval=heartbeat_interval,
    )

    # 创建进程
    process = mp.Process(
        target=driver_instance.run,
        name=f"Driver-{driver_id}",
        daemon=True,
    )

    return process
