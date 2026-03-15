"""
文件名: driver_manager.py
路径: backend/core/
功能: 驱动进程管理器，实现驱动进程生命周期管理、IPC通信、健康监控和自动重启
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: multiprocessing, threading, logging, typing
参考: 技术文档v3.0第14.1.1节插件化架构设计
"""

import asyncio
import logging
import multiprocessing as mp
import signal
import threading
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from multiprocessing.queues import Queue as MPQueue
from typing import Any, TypeVar

from ..abstract import AbstractDevice

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=AbstractDevice)


class DriverProcessStatus(Enum):
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
    """IPC消息类型枚举。"""

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
    source: str = "driver_manager"
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
    """驱动进程配置类。

    Attributes:
        driver_id: 驱动唯一标识
        driver_class: 驱动类
        config: 驱动配置字典
        auto_restart: 是否自动重启
        max_restart_count: 最大重启次数
        restart_delay: 重启延迟（秒）
        heartbeat_interval: 心跳间隔（秒）
        heartbeat_timeout: 心跳超时（秒）
    """

    driver_id: str
    driver_class: type[AbstractDevice]
    config: dict[str, Any] = field(default_factory=dict)
    auto_restart: bool = True
    max_restart_count: int = 3
    restart_delay: float = 5.0
    heartbeat_interval: float = 10.0
    heartbeat_timeout: float = 30.0


@dataclass
class DriverProcessInfo:
    """驱动进程信息类。

    Attributes:
        driver_id: 驱动ID
        status: 进程状态
        pid: 进程ID
        start_time: 启动时间
        restart_count: 重启次数
        last_heartbeat: 最后心跳时间
        last_error: 最后错误信息
    """

    driver_id: str
    status: DriverProcessStatus = DriverProcessStatus.STOPPED
    pid: int | None = None
    start_time: float | None = None
    restart_count: int = 0
    last_heartbeat: float | None = None
    last_error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """序列化为字典。

        Returns:
            Dict[str, Any]: 序列化后的字典
        """
        return {
            "driver_id": self.driver_id,
            "status": self.status.value,
            "pid": self.pid,
            "start_time": self.start_time,
            "restart_count": self.restart_count,
            "last_heartbeat": self.last_heartbeat,
            "last_error": self.last_error,
        }


def driver_process_entry(
    driver_id: str,
    driver_class: type[AbstractDevice],
    config: dict[str, Any],
    command_queue: MPQueue,
    response_queue: MPQueue,
    heartbeat_interval: float,
) -> None:
    """驱动进程入口函数。

    在独立进程中运行，管理单个驱动实例的生命周期。

    Args:
        driver_id: 驱动ID
        driver_class: 驱动类
        config: 驱动配置
        command_queue: 命令队列（从主进程接收命令）
        response_queue: 响应队列（向主进程发送响应）
        heartbeat_interval: 心跳间隔

    Note:
        此函数在子进程中执行，不应直接调用。
    """
    # 设置子进程日志
    logging.basicConfig(
        level=logging.INFO,
        format=f"[Driver:{driver_id}] %(asctime)s - %(levelname)s - %(message)s",
    )
    process_logger = logging.getLogger(f"driver_process.{driver_id}")

    process_logger.info(f"驱动进程启动，PID: {mp.current_process().pid}")

    # 创建驱动实例
    driver: AbstractDevice | None = None
    running = True
    loop: asyncio.AbstractEventLoop | None = None

    def handle_signal(signum, frame):
        """处理终止信号。"""
        nonlocal running
        process_logger.info(f"收到信号 {signum}，准备退出")
        running = False

    # 注册信号处理
    signal.signal(signal.SIGTERM, handle_signal)
    signal.signal(signal.SIGINT, handle_signal)

    async def initialize_driver():
        """异步初始化驱动。"""
        nonlocal driver
        try:
            driver = driver_class(driver_id, config)
            success = await driver.connect()
            if success:
                process_logger.info(f"驱动 {driver_id} 初始化成功")
                response_queue.put(
                    IPCMessage(
                        msg_type=IPCMessageType.STATUS,
                        payload={"status": "initialized", "driver_id": driver_id},
                        source=driver_id,
                    )
                )
                return True
            else:
                process_logger.error(f"驱动 {driver_id} 连接失败")
                return False
        except Exception as e:
            process_logger.error(f"驱动初始化异常: {e}\n{traceback.format_exc()}")
            response_queue.put(
                IPCMessage(
                    msg_type=IPCMessageType.ERROR,
                    payload={"error": str(e), "driver_id": driver_id},
                    source=driver_id,
                )
            )
            return False

    async def cleanup_driver():
        """异步清理驱动。"""
        nonlocal driver
        if driver:
            try:
                await driver.disconnect()
                process_logger.info(f"驱动 {driver_id} 已断开连接")
            except Exception as e:
                process_logger.error(f"驱动断开连接异常: {e}")
            finally:
                driver = None

    async def process_command(msg: IPCMessage) -> IPCMessage | None:
        """处理命令消息。

        Args:
            msg: IPC消息

        Returns:
            Optional[IPCMessage]: 响应消息
        """
        nonlocal running

        if msg.msg_type == IPCMessageType.STOP:
            process_logger.info("收到停止命令")
            running = False
            return IPCMessage(
                msg_type=IPCMessageType.RESPONSE,
                payload={"success": True, "action": "stop"},
                source=driver_id,
                request_id=msg.request_id,
            )

        elif msg.msg_type == IPCMessageType.PING:
            return IPCMessage(
                msg_type=IPCMessageType.RESPONSE,
                payload={"pong": True, "driver_status": driver.status.value if driver else "none"},
                source=driver_id,
                request_id=msg.request_id,
            )

        elif msg.msg_type == IPCMessageType.COMMAND:
            # 执行驱动命令
            if driver is None:
                return IPCMessage(
                    msg_type=IPCMessageType.ERROR,
                    payload={"error": "驱动未初始化"},
                    source=driver_id,
                    request_id=msg.request_id,
                )

            command = msg.payload.get("command")
            params = msg.payload.get("params", {})

            try:
                # 动态调用驱动方法
                if hasattr(driver, command):
                    method = getattr(driver, command)
                    if asyncio.iscoroutinefunction(method):
                        result = await method(**params)
                    else:
                        result = method(**params)

                    return IPCMessage(
                        msg_type=IPCMessageType.RESPONSE,
                        payload={"success": True, "result": result},
                        source=driver_id,
                        request_id=msg.request_id,
                    )
                else:
                    return IPCMessage(
                        msg_type=IPCMessageType.ERROR,
                        payload={"error": f"未知命令: {command}"},
                        source=driver_id,
                        request_id=msg.request_id,
                    )
            except Exception as e:
                process_logger.error(f"命令执行失败: {command}, 错误: {e}")
                return IPCMessage(
                    msg_type=IPCMessageType.ERROR,
                    payload={"error": str(e), "command": command},
                    source=driver_id,
                    request_id=msg.request_id,
                )

        return None

    async def send_heartbeat():
        """发送心跳消息。"""
        response_queue.put(
            IPCMessage(
                msg_type=IPCMessageType.HEARTBEAT,
                payload={
                    "driver_id": driver_id,
                    "status": driver.status.value if driver else "none",
                    "timestamp": time.time(),
                },
                source=driver_id,
            )
        )

    async def main_loop():
        """主事件循环。"""
        nonlocal running

        # 初始化驱动
        if not await initialize_driver():
            return

        last_heartbeat = time.time()

        while running:
            try:
                # 检查命令队列（非阻塞）
                try:
                    if not command_queue.empty():
                        msg = command_queue.get_nowait()
                        if isinstance(msg, dict):
                            msg = IPCMessage.from_dict(msg)

                        response = await process_command(msg)
                        if response:
                            response_queue.put(response)
                except Exception as e:
                    process_logger.error(f"处理命令异常: {e}")

                # 发送心跳
                if time.time() - last_heartbeat >= heartbeat_interval:
                    await send_heartbeat()
                    last_heartbeat = time.time()

                # 短暂休眠，避免CPU占用过高
                await asyncio.sleep(0.1)

            except Exception as e:
                process_logger.error(f"主循环异常: {e}\n{traceback.format_exc()}")
                response_queue.put(
                    IPCMessage(
                        msg_type=IPCMessageType.ERROR,
                        payload={"error": str(e), "driver_id": driver_id},
                        source=driver_id,
                    )
                )

        # 清理
        await cleanup_driver()

    # 运行事件循环
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(main_loop())
    except Exception as e:
        process_logger.error(f"事件循环异常: {e}\n{traceback.format_exc()}")
    finally:
        if loop:
            loop.close()
        process_logger.info(f"驱动进程 {driver_id} 已退出")


class DriverProcessManager:
    """驱动进程管理器。

    管理多个驱动进程的生命周期，提供IPC通信、健康监控和自动重启功能。

    Features:
        - 驱动进程生命周期管理（启动、停止、重启）
        - 进程间通信（IPC）机制，使用multiprocessing.Queue
        - 驱动进程健康监控和自动重启机制
        - 进程状态追踪和错误处理

    Example:
        >>> manager = DriverProcessManager()
        >>> manager.register_driver("motor_1", LeadshineDM2C, {"port": "COM1"})
        >>> await manager.start_driver("motor_1")
        >>> result = await manager.send_command("motor_1", "move_abs", {"position": 100})
        >>> await manager.stop_driver("motor_1")
    """

    def __init__(self) -> None:
        """初始化驱动进程管理器。"""
        self._drivers: dict[str, DriverProcessConfig] = {}
        self._processes: dict[str, mp.Process] = {}
        self._process_info: dict[str, DriverProcessInfo] = {}
        self._command_queues: dict[str, MPQueue] = {}
        self._response_queues: dict[str, MPQueue] = {}
        self._monitor_thread: threading.Thread | None = None
        self._running = False
        self._lock = threading.RLock()

        logger.info("DriverProcessManager 初始化完成")

    def register_driver(
        self,
        driver_id: str,
        driver_class: type[AbstractDevice],
        config: dict[str, Any] | None = None,
        auto_restart: bool = True,
        max_restart_count: int = 3,
        restart_delay: float = 5.0,
        heartbeat_interval: float = 10.0,
        heartbeat_timeout: float = 30.0,
    ) -> bool:
        """注册驱动。

        Args:
            driver_id: 驱动唯一标识
            driver_class: 驱动类（必须继承自AbstractDevice）
            config: 驱动配置字典
            auto_restart: 是否自动重启
            max_restart_count: 最大重启次数
            restart_delay: 重启延迟（秒）
            heartbeat_interval: 心跳间隔（秒）
            heartbeat_timeout: 心跳超时（秒）

        Returns:
            bool: 注册成功返回True

        Raises:
            ValueError: 驱动ID已存在或驱动类无效
        """
        with self._lock:
            if driver_id in self._drivers:
                raise ValueError(f"驱动ID '{driver_id}' 已存在")

            if not issubclass(driver_class, AbstractDevice):
                raise ValueError(f"驱动类 {driver_class.__name__} 必须继承自 AbstractDevice")

            driver_config = DriverProcessConfig(
                driver_id=driver_id,
                driver_class=driver_class,
                config=config or {},
                auto_restart=auto_restart,
                max_restart_count=max_restart_count,
                restart_delay=restart_delay,
                heartbeat_interval=heartbeat_interval,
                heartbeat_timeout=heartbeat_timeout,
            )

            self._drivers[driver_id] = driver_config
            self._process_info[driver_id] = DriverProcessInfo(driver_id=driver_id)

            logger.info(f"驱动 '{driver_id}' 注册成功")
            return True

    def unregister_driver(self, driver_id: str) -> bool:
        """注销驱动。

        Args:
            driver_id: 驱动唯一标识

        Returns:
            bool: 注销成功返回True

        Raises:
            KeyError: 驱动不存在
        """
        with self._lock:
            if driver_id not in self._drivers:
                raise KeyError(f"驱动 '{driver_id}' 不存在")

            # 如果进程正在运行，先停止
            if self._process_info[driver_id].status == DriverProcessStatus.RUNNING:
                logger.warning(f"驱动 '{driver_id}' 正在运行，请先停止")
                return False

            del self._drivers[driver_id]
            del self._process_info[driver_id]

            # 清理队列
            if driver_id in self._command_queues:
                del self._command_queues[driver_id]
            if driver_id in self._response_queues:
                del self._response_queues[driver_id]

            logger.info(f"驱动 '{driver_id}' 注销成功")
            return True

    def start_driver(self, driver_id: str) -> bool:
        """启动驱动进程。

        Args:
            driver_id: 驱动唯一标识

        Returns:
            bool: 启动成功返回True

        Raises:
            KeyError: 驱动不存在
        """
        with self._lock:
            if driver_id not in self._drivers:
                raise KeyError(f"驱动 '{driver_id}' 不存在")

            config = self._drivers[driver_id]
            info = self._process_info[driver_id]

            # 检查进程状态
            if info.status == DriverProcessStatus.RUNNING:
                logger.warning(f"驱动 '{driver_id}' 已在运行")
                return True

            # 更新状态
            info.status = DriverProcessStatus.STARTING

            # 创建IPC队列
            self._command_queues[driver_id] = mp.Queue()
            self._response_queues[driver_id] = mp.Queue()

            # 创建并启动进程
            process = mp.Process(
                target=driver_process_entry,
                args=(
                    driver_id,
                    config.driver_class,
                    config.config,
                    self._command_queues[driver_id],
                    self._response_queues[driver_id],
                    config.heartbeat_interval,
                ),
                name=f"Driver-{driver_id}",
                daemon=True,
            )

            process.start()

            self._processes[driver_id] = process
            info.pid = process.pid
            info.start_time = time.time()
            info.status = DriverProcessStatus.RUNNING
            info.last_heartbeat = time.time()

            logger.info(f"驱动 '{driver_id}' 进程已启动，PID: {process.pid}")

            # 启动监控线程（如果尚未启动）
            self._start_monitor_thread()

            return True

    def stop_driver(self, driver_id: str, timeout: float = 10.0) -> bool:
        """停止驱动进程。

        Args:
            driver_id: 驱动唯一标识
            timeout: 等待超时时间（秒）

        Returns:
            bool: 停止成功返回True
        """
        with self._lock:
            if driver_id not in self._drivers:
                raise KeyError(f"驱动 '{driver_id}' 不存在")

            info = self._process_info[driver_id]

            if info.status != DriverProcessStatus.RUNNING:
                logger.warning(f"驱动 '{driver_id}' 未在运行")
                return True

            info.status = DriverProcessStatus.STOPPING

            # 发送停止命令
            command_queue = self._command_queues.get(driver_id)
            if command_queue:
                try:
                    command_queue.put(
                        IPCMessage(
                            msg_type=IPCMessageType.STOP,
                            source="driver_manager",
                        )
                    )
                except Exception as e:
                    logger.error(f"发送停止命令失败: {e}")

            # 等待进程结束
            process = self._processes.get(driver_id)
            if process:
                process.join(timeout=timeout)

                if process.is_alive():
                    logger.warning(f"驱动 '{driver_id}' 进程未响应，强制终止")
                    process.terminate()
                    process.join(timeout=2.0)

                    if process.is_alive():
                        process.kill()
                        process.join()

            # 清理
            info.status = DriverProcessStatus.STOPPED
            info.pid = None

            if driver_id in self._processes:
                del self._processes[driver_id]

            logger.info(f"驱动 '{driver_id}' 已停止")
            return True

    def restart_driver(self, driver_id: str, delay: float = 0.0) -> bool:
        """重启驱动进程。

        Args:
            driver_id: 驱动唯一标识
            delay: 重启延迟（秒）

        Returns:
            bool: 重启成功返回True
        """
        with self._lock:
            if driver_id not in self._drivers:
                raise KeyError(f"驱动 '{driver_id}' 不存在")

            info = self._process_info[driver_id]
            config = self._drivers[driver_id]

            info.status = DriverProcessStatus.RESTARTING

            # 先停止
            self.stop_driver(driver_id)

            # 延迟重启
            if delay > 0:
                time.sleep(delay)

            # 重新启动
            success = self.start_driver(driver_id)

            if success:
                info.restart_count += 1
                logger.info(
                    f"驱动 '{driver_id}' 重启成功，"
                    f"累计重启次数: {info.restart_count}/{config.max_restart_count}"
                )
            else:
                info.status = DriverProcessStatus.ERROR
                logger.error(f"驱动 '{driver_id}' 重启失败")

            return success

    async def send_command(
        self,
        driver_id: str,
        command: str,
        params: dict[str, Any] | None = None,
        timeout: float = 30.0,
    ) -> dict[str, Any]:
        """向驱动发送命令。

        Args:
            driver_id: 驱动唯一标识
            command: 命令名称
            params: 命令参数
            timeout: 超时时间（秒）

        Returns:
            Dict[str, Any]: 命令执行结果

        Raises:
            KeyError: 驱动不存在
            RuntimeError: 驱动未运行或通信失败
        """
        if driver_id not in self._drivers:
            raise KeyError(f"驱动 '{driver_id}' 不存在")

        info = self._process_info[driver_id]

        if info.status != DriverProcessStatus.RUNNING:
            raise RuntimeError(f"驱动 '{driver_id}' 未运行，当前状态: {info.status.value}")

        command_queue = self._command_queues.get(driver_id)
        response_queue = self._response_queues.get(driver_id)

        if not command_queue or not response_queue:
            raise RuntimeError(f"驱动 '{driver_id}' 通信队列不可用")

        # 生成请求ID
        request_id = f"{driver_id}_{command}_{time.time()}"

        # 发送命令
        msg = IPCMessage(
            msg_type=IPCMessageType.COMMAND,
            payload={"command": command, "params": params or {}},
            source="driver_manager",
            request_id=request_id,
        )

        try:
            command_queue.put(msg)
        except Exception as e:
            raise RuntimeError(f"发送命令失败: {e}")

        # 等待响应
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                if not response_queue.empty():
                    response = response_queue.get_nowait()
                    if isinstance(response, dict):
                        response = IPCMessage.from_dict(response)

                    if response.request_id == request_id:
                        if response.msg_type == IPCMessageType.ERROR:
                            raise RuntimeError(
                                f"命令执行失败: {response.payload.get('error', 'Unknown error')}"
                            )
                        return response.payload
            except Exception as e:
                if isinstance(e, RuntimeError):
                    raise
                logger.error(f"读取响应失败: {e}")

            await asyncio.sleep(0.1)

        raise RuntimeError(f"命令 '{command}' 执行超时")

    def get_driver_info(self, driver_id: str) -> dict[str, Any]:
        """获取驱动信息。

        Args:
            driver_id: 驱动唯一标识

        Returns:
            Dict[str, Any]: 驱动信息
        """
        if driver_id not in self._drivers:
            raise KeyError(f"驱动 '{driver_id}' 不存在")

        info = self._process_info[driver_id]
        config = self._drivers[driver_id]

        return {
            **info.to_dict(),
            "config": {
                "auto_restart": config.auto_restart,
                "max_restart_count": config.max_restart_count,
                "restart_delay": config.restart_delay,
                "heartbeat_interval": config.heartbeat_interval,
                "heartbeat_timeout": config.heartbeat_timeout,
            },
        }

    def get_all_drivers_info(self) -> dict[str, dict[str, Any]]:
        """获取所有驱动信息。

        Returns:
            Dict[str, Dict[str, Any]]: 所有驱动信息
        """
        return {driver_id: self.get_driver_info(driver_id) for driver_id in self._drivers}

    def _start_monitor_thread(self) -> None:
        """启动监控线程。"""
        if self._monitor_thread and self._monitor_thread.is_alive():
            return

        self._running = True
        self._monitor_thread = threading.Thread(
            target=self._monitor_loop,
            name="DriverMonitor",
            daemon=True,
        )
        self._monitor_thread.start()
        logger.info("驱动监控线程已启动")

    def _monitor_loop(self) -> None:
        """监控循环。

        检查驱动进程健康状态，处理自动重启。
        """
        logger.info("监控循环开始运行")

        while self._running:
            try:
                # 处理响应队列中的消息
                self._process_responses()

                # 检查进程健康状态
                self._check_process_health()

                # 短暂休眠
                time.sleep(1.0)

            except Exception as e:
                logger.error(f"监控循环异常: {e}")

        logger.info("监控循环已退出")

    def _process_responses(self) -> None:
        """处理响应队列中的消息。"""
        for driver_id, response_queue in self._response_queues.items():
            try:
                while not response_queue.empty():
                    msg = response_queue.get_nowait()
                    if isinstance(msg, dict):
                        msg = IPCMessage.from_dict(msg)

                    self._handle_response(driver_id, msg)
            except Exception as e:
                logger.error(f"处理响应失败 [{driver_id}]: {e}")

    def _handle_response(self, driver_id: str, msg: IPCMessage) -> None:
        """处理响应消息。

        Args:
            driver_id: 驱动ID
            msg: IPC消息
        """
        info = self._process_info.get(driver_id)
        if not info:
            return

        if msg.msg_type == IPCMessageType.HEARTBEAT:
            info.last_heartbeat = time.time()
            logger.debug(f"收到心跳 [{driver_id}]")

        elif msg.msg_type == IPCMessageType.ERROR:
            error_info = msg.payload
            info.last_error = error_info.get("error", "Unknown error")
            logger.error(f"驱动错误 [{driver_id}]: {info.last_error}")

        elif msg.msg_type == IPCMessageType.STATUS:
            logger.debug(f"状态更新 [{driver_id}]: {msg.payload}")

    def _check_process_health(self) -> None:
        """检查进程健康状态。"""
        current_time = time.time()

        for driver_id, config in list(self._drivers.items()):
            info = self._process_info.get(driver_id)
            if not info:
                continue

            # 检查进程是否存活
            process = self._processes.get(driver_id)
            if process and not process.is_alive():
                logger.warning(f"驱动进程 [{driver_id}] 已终止")
                info.status = DriverProcessStatus.ERROR
                info.last_error = "进程异常终止"

                # 自动重启
                if config.auto_restart and info.restart_count < config.max_restart_count:
                    logger.info(
                        f"准备自动重启驱动 [{driver_id}]，" f"延迟 {config.restart_delay} 秒"
                    )
                    threading.Timer(
                        config.restart_delay,
                        self.restart_driver,
                        args=[driver_id],
                    ).start()
                continue

            # 检查心跳超时
            if (
                info.status == DriverProcessStatus.RUNNING
                and info.last_heartbeat
                and current_time - info.last_heartbeat > config.heartbeat_timeout
            ):
                logger.warning(
                    f"驱动 [{driver_id}] 心跳超时，"
                    f"上次心跳: {current_time - info.last_heartbeat:.1f} 秒前"
                )
                info.last_error = "心跳超时"

                # 自动重启
                if config.auto_restart and info.restart_count < config.max_restart_count:
                    logger.info(f"准备重启心跳超时的驱动 [{driver_id}]")
                    self.restart_driver(driver_id, delay=config.restart_delay)

    def start_all(self) -> dict[str, bool]:
        """启动所有已注册的驱动。

        Returns:
            Dict[str, bool]: 各驱动的启动结果
        """
        results = {}
        for driver_id in self._drivers:
            try:
                results[driver_id] = self.start_driver(driver_id)
            except Exception as e:
                logger.error(f"启动驱动 '{driver_id}' 失败: {e}")
                results[driver_id] = False
        return results

    def stop_all(self, timeout: float = 10.0) -> dict[str, bool]:
        """停止所有驱动进程。

        Args:
            timeout: 等待超时时间（秒）

        Returns:
            Dict[str, bool]: 各驱动的停止结果
        """
        results = {}
        for driver_id in list(self._drivers.keys()):
            try:
                results[driver_id] = self.stop_driver(driver_id, timeout)
            except Exception as e:
                logger.error(f"停止驱动 '{driver_id}' 失败: {e}")
                results[driver_id] = False
        return results

    def shutdown(self) -> None:
        """关闭管理器，停止所有驱动进程。"""
        logger.info("正在关闭 DriverProcessManager")
        self._running = False

        # 停止所有驱动
        self.stop_all()

        # 等待监控线程结束
        if self._monitor_thread and self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=5.0)

        logger.info("DriverProcessManager 已关闭")

    def __enter__(self) -> "DriverProcessManager":
        """上下文管理器入口。"""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """上下文管理器退出。"""
        self.shutdown()


# 便捷函数
def create_driver_manager() -> DriverProcessManager:
    """创建驱动进程管理器实例。

    Returns:
        DriverProcessManager: 管理器实例
    """
    return DriverProcessManager()
