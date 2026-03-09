"""
文件名: error_recovery.py
路径: backend/core/
功能: 智能错误恢复系统，实现设备连接重试、WebSocket自动重连、实验状态保存恢复
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: asyncio, logging, dataclasses, typing
"""

import asyncio
import json
import logging
import os
import time
import traceback
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Type, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class RecoveryStrategy(Enum):
    """恢复策略枚举。

    Attributes:
        EXPONENTIAL_BACKOFF: 指数退避重试
        LINEAR_BACKOFF: 线性退避重试
        FIXED_INTERVAL: 固定间隔重试
        IMMEDIATE: 立即重试
    """

    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_INTERVAL = "fixed_interval"
    IMMEDIATE = "immediate"


class RecoveryState(Enum):
    """恢复状态枚举。

    Attributes:
        IDLE: 空闲状态
        RECOVERING: 恢复中
        RECOVERED: 已恢复
        FAILED: 恢复失败
        EXHAUSTED: 重试次数耗尽
    """

    IDLE = "idle"
    RECOVERING = "recovering"
    RECOVERED = "recovered"
    FAILED = "failed"
    EXHAUSTED = "exhausted"


@dataclass
class RetryConfig:
    """重试配置类。

    Attributes:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_factor: 退避因子
        strategy: 恢复策略
        jitter: 是否添加随机抖动
        retryable_exceptions: 可重试的异常类型列表
    """

    max_retries: int = 3
    initial_delay: float = 1.0
    max_delay: float = 60.0
    backoff_factor: float = 2.0
    strategy: RecoveryStrategy = RecoveryStrategy.EXPONENTIAL_BACKOFF
    jitter: bool = True
    retryable_exceptions: List[Type[Exception]] = field(default_factory=list)

    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟时间。

        Args:
            attempt: 当前重试次数（从1开始）

        Returns:
            float: 延迟时间（秒）
        """
        import random

        if self.strategy == RecoveryStrategy.IMMEDIATE:
            return 0.0

        if self.strategy == RecoveryStrategy.FIXED_INTERVAL:
            delay = self.initial_delay

        elif self.strategy == RecoveryStrategy.LINEAR_BACKOFF:
            delay = self.initial_delay * attempt

        elif self.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.initial_delay * (self.backoff_factor ** (attempt - 1))

        else:
            delay = self.initial_delay

        # 限制最大延迟
        delay = min(delay, self.max_delay)

        # 添加随机抖动（防止惊群效应）
        if self.jitter:
            jitter_range = delay * 0.1
            delay += random.uniform(-jitter_range, jitter_range)

        return max(0.0, delay)

    def should_retry(self, exception: Exception) -> bool:
        """判断是否应该重试。

        Args:
            exception: 发生的异常

        Returns:
            bool: 是否应该重试
        """
        if not self.retryable_exceptions:
            # 如果未指定可重试异常，默认重试所有异常
            return True

        return any(
            isinstance(exception, exc_type) for exc_type in self.retryable_exceptions
        )


@dataclass
class RetryResult:
    """重试结果类。

    Attributes:
        success: 是否成功
        attempts: 尝试次数
        last_exception: 最后一次异常
        total_time: 总耗时（秒）
        result: 成功时的结果
    """

    success: bool = False
    attempts: int = 0
    last_exception: Optional[Exception] = None
    total_time: float = 0.0
    result: Any = None


class RetryExecutor:
    """重试执行器。

    提供统一的异步重试机制，支持多种重试策略。

    Example:
        >>> config = RetryConfig(max_retries=3, strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF)
        >>> executor = RetryExecutor(config)
        >>> result = await executor.execute(some_async_function, arg1, arg2)
    """

    def __init__(self, config: Optional[RetryConfig] = None):
        """初始化重试执行器。

        Args:
            config: 重试配置，为None时使用默认配置
        """
        self.config = config or RetryConfig()
        self._attempt_count = 0

    async def execute(
        self,
        func: Callable[..., T],
        *args: Any,
        **kwargs: Any,
    ) -> RetryResult:
        """执行带重试的异步函数。

        Args:
            func: 要执行的异步函数
            *args: 位置参数
            **kwargs: 关键字参数

        Returns:
            RetryResult: 重试结果
        """
        start_time = time.time()
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.config.max_retries + 1):
            self._attempt_count = attempt

            try:
                if asyncio.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)

                return RetryResult(
                    success=True,
                    attempts=attempt,
                    total_time=time.time() - start_time,
                    result=result,
                )

            except Exception as e:
                last_exception = e
                logger.warning(
                    f"执行失败 (尝试 {attempt}/{self.config.max_retries}): {e}"
                )

                # 检查是否应该重试
                if not self.config.should_retry(e):
                    logger.error(f"异常不可重试: {type(e).__name__}")
                    break

                # 检查是否还有重试机会
                if attempt >= self.config.max_retries:
                    logger.error(f"已达到最大重试次数: {self.config.max_retries}")
                    break

                # 计算延迟并等待
                delay = self.config.calculate_delay(attempt)
                logger.info(f"等待 {delay:.2f} 秒后重试...")
                await asyncio.sleep(delay)

        return RetryResult(
            success=False,
            attempts=self._attempt_count,
            last_exception=last_exception,
            total_time=time.time() - start_time,
        )


@dataclass
class DeviceConnectionState:
    """设备连接状态类。

    Attributes:
        device_id: 设备ID
        connected: 是否已连接
        last_connected_time: 最后连接时间
        last_error: 最后错误信息
        reconnect_count: 重连次数
        state: 恢复状态
    """

    device_id: str
    connected: bool = False
    last_connected_time: Optional[float] = None
    last_error: Optional[str] = None
    reconnect_count: int = 0
    state: RecoveryState = RecoveryState.IDLE

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            Dict[str, Any]: 状态字典
        """
        return {
            "device_id": self.device_id,
            "connected": self.connected,
            "last_connected_time": self.last_connected_time,
            "last_error": self.last_error,
            "reconnect_count": self.reconnect_count,
            "state": self.state.value,
        }


class DeviceConnectionRecovery:
    """设备连接自动恢复管理器。

    实现设备连接的自动重试和恢复机制。

    Example:
        >>> recovery = DeviceConnectionRecovery()
        >>> recovery.register_device("motor_1", connect_func, disconnect_func)
        >>> await recovery.start_recovery("motor_1")
    """

    def __init__(
        self,
        default_config: Optional[RetryConfig] = None,
        state_file: Optional[str] = None,
    ):
        """初始化设备连接恢复管理器。

        Args:
            default_config: 默认重试配置
            state_file: 状态持久化文件路径
        """
        self.default_config = default_config or RetryConfig(
            max_retries=5,
            initial_delay=2.0,
            max_delay=120.0,
            backoff_factor=2.0,
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
        )
        self.state_file = state_file or "device_states.json"

        # 设备连接函数映射
        self._connect_funcs: Dict[str, Callable] = {}
        self._disconnect_funcs: Dict[str, Callable] = {}
        self._health_check_funcs: Dict[str, Callable] = {}

        # 设备状态
        self._device_states: Dict[str, DeviceConnectionState] = {}

        # 设备特定配置
        self._device_configs: Dict[str, RetryConfig] = {}

        # 恢复任务
        self._recovery_tasks: Dict[str, asyncio.Task] = {}

        # 运行标志
        self._running = False

        # 加载持久化状态
        self._load_states()

        logger.info("DeviceConnectionRecovery 初始化完成")

    def register_device(
        self,
        device_id: str,
        connect_func: Callable,
        disconnect_func: Optional[Callable] = None,
        health_check_func: Optional[Callable] = None,
        config: Optional[RetryConfig] = None,
    ) -> None:
        """注册设备。

        Args:
            device_id: 设备ID
            connect_func: 连接函数（异步）
            disconnect_func: 断开连接函数（异步，可选）
            health_check_func: 健康检查函数（异步，可选）
            config: 设备特定的重试配置
        """
        self._connect_funcs[device_id] = connect_func

        if disconnect_func:
            self._disconnect_funcs[device_id] = disconnect_func

        if health_check_func:
            self._health_check_funcs[device_id] = health_check_func

        if config:
            self._device_configs[device_id] = config

        # 初始化设备状态
        if device_id not in self._device_states:
            self._device_states[device_id] = DeviceConnectionState(device_id=device_id)

        logger.info(f"设备 '{device_id}' 已注册")

    def unregister_device(self, device_id: str) -> None:
        """注销设备。

        Args:
            device_id: 设备ID
        """
        # 取消恢复任务
        if device_id in self._recovery_tasks:
            self._recovery_tasks[device_id].cancel()
            del self._recovery_tasks[device_id]

        # 清理状态
        self._connect_funcs.pop(device_id, None)
        self._disconnect_funcs.pop(device_id, None)
        self._health_check_funcs.pop(device_id, None)
        self._device_configs.pop(device_id, None)
        self._device_states.pop(device_id, None)

        logger.info(f"设备 '{device_id}' 已注销")

    async def connect_device(self, device_id: str) -> bool:
        """连接设备（带自动重试）。

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否连接成功
        """
        if device_id not in self._connect_funcs:
            logger.error(f"设备 '{device_id}' 未注册")
            return False

        state = self._device_states.get(device_id)
        if not state:
            state = DeviceConnectionState(device_id=device_id)
            self._device_states[device_id] = state

        config = self._device_configs.get(device_id, self.default_config)
        executor = RetryExecutor(config)

        state.state = RecoveryState.RECOVERING

        result = await executor.execute(self._connect_funcs[device_id])

        if result.success:
            state.connected = True
            state.last_connected_time = time.time()
            state.last_error = None
            state.state = RecoveryState.RECOVERED
            logger.info(f"设备 '{device_id}' 连接成功")
            self._save_states()
            return True
        else:
            state.connected = False
            state.last_error = str(result.last_exception)
            state.state = RecoveryState.FAILED if result.attempts < config.max_retries else RecoveryState.EXHAUSTED
            logger.error(f"设备 '{device_id}' 连接失败: {state.last_error}")
            return False

    async def disconnect_device(self, device_id: str) -> bool:
        """断开设备连接。

        Args:
            device_id: 设备ID

        Returns:
            bool: 是否断开成功
        """
        state = self._device_states.get(device_id)
        if not state:
            return True

        # 取消恢复任务
        if device_id in self._recovery_tasks:
            self._recovery_tasks[device_id].cancel()
            del self._recovery_tasks[device_id]

        disconnect_func = self._disconnect_funcs.get(device_id)
        if disconnect_func:
            try:
                if asyncio.iscoroutinefunction(disconnect_func):
                    await disconnect_func()
                else:
                    disconnect_func()
            except Exception as e:
                logger.error(f"断开设备 '{device_id}' 失败: {e}")

        state.connected = False
        state.state = RecoveryState.IDLE
        self._save_states()

        logger.info(f"设备 '{device_id}' 已断开")
        return True

    async def start_recovery(self, device_id: str) -> None:
        """启动设备恢复任务。

        Args:
            device_id: 设备ID
        """
        if device_id in self._recovery_tasks:
            logger.warning(f"设备 '{device_id}' 恢复任务已在运行")
            return

        self._recovery_tasks[device_id] = asyncio.create_task(
            self._recovery_loop(device_id)
        )
        logger.info(f"设备 '{device_id}' 恢复任务已启动")

    async def stop_recovery(self, device_id: str) -> None:
        """停止设备恢复任务。

        Args:
            device_id: 设备ID
        """
        if device_id in self._recovery_tasks:
            self._recovery_tasks[device_id].cancel()
            del self._recovery_tasks[device_id]
            logger.info(f"设备 '{device_id}' 恢复任务已停止")

    async def _recovery_loop(self, device_id: str) -> None:
        """恢复循环。

        Args:
            device_id: 设备ID
        """
        state = self._device_states.get(device_id)
        config = self._device_configs.get(device_id, self.default_config)

        while True:
            try:
                # 检查设备连接状态
                if not state.connected:
                    logger.info(f"设备 '{device_id}' 未连接，尝试恢复...")
                    success = await self.connect_device(device_id)

                    if success:
                        state.reconnect_count += 1
                        self._save_states()
                    else:
                        # 等待后重试
                        delay = config.calculate_delay(state.reconnect_count + 1)
                        await asyncio.sleep(delay)
                        continue

                # 健康检查
                health_check = self._health_check_funcs.get(device_id)
                if health_check:
                    try:
                        is_healthy = await health_check() if asyncio.iscoroutinefunction(health_check) else health_check()
                        if not is_healthy:
                            logger.warning(f"设备 '{device_id}' 健康检查失败")
                            state.connected = False
                            state.last_error = "健康检查失败"
                            continue
                    except Exception as e:
                        logger.error(f"设备 '{device_id}' 健康检查异常: {e}")
                        state.connected = False
                        state.last_error = str(e)
                        continue

                # 正常检查间隔
                await asyncio.sleep(30.0)

            except asyncio.CancelledError:
                logger.info(f"设备 '{device_id}' 恢复循环已取消")
                break
            except Exception as e:
                logger.error(f"设备 '{device_id}' 恢复循环异常: {e}")
                await asyncio.sleep(10.0)

    def get_device_state(self, device_id: str) -> Optional[Dict[str, Any]]:
        """获取设备状态。

        Args:
            device_id: 设备ID

        Returns:
            Optional[Dict[str, Any]]: 设备状态字典
        """
        state = self._device_states.get(device_id)
        return state.to_dict() if state else None

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有设备状态。

        Returns:
            Dict[str, Dict[str, Any]]: 所有设备状态
        """
        return {
            device_id: state.to_dict()
            for device_id, state in self._device_states.items()
        }

    def _save_states(self) -> None:
        """保存状态到文件。"""
        try:
            states_data = {
                device_id: state.to_dict()
                for device_id, state in self._device_states.items()
            }
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(states_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存设备状态失败: {e}")

    def _load_states(self) -> None:
        """从文件加载状态。"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, "r", encoding="utf-8") as f:
                    states_data = json.load(f)

                for device_id, data in states_data.items():
                    self._device_states[device_id] = DeviceConnectionState(
                        device_id=device_id,
                        connected=data.get("connected", False),
                        last_connected_time=data.get("last_connected_time"),
                        last_error=data.get("last_error"),
                        reconnect_count=data.get("reconnect_count", 0),
                        state=RecoveryState(data.get("state", "idle")),
                    )

                logger.info(f"已加载 {len(states_data)} 个设备状态")
        except Exception as e:
            logger.warning(f"加载设备状态失败: {e}")


@dataclass
class WebSocketReconnectionState:
    """WebSocket重连状态类。

    Attributes:
        connection_id: 连接ID
        endpoint: 端点路径
        connected: 是否已连接
        reconnect_count: 重连次数
        last_connected_time: 最后连接时间
        last_error: 最后错误信息
        state: 恢复状态
    """

    connection_id: str
    endpoint: str = ""
    connected: bool = False
    reconnect_count: int = 0
    last_connected_time: Optional[float] = None
    last_error: Optional[str] = None
    state: RecoveryState = RecoveryState.IDLE

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            Dict[str, Any]: 状态字典
        """
        return {
            "connection_id": self.connection_id,
            "endpoint": self.endpoint,
            "connected": self.connected,
            "reconnect_count": self.reconnect_count,
            "last_connected_time": self.last_connected_time,
            "last_error": self.last_error,
            "state": self.state.value,
        }


class WebSocketReconnectionManager:
    """WebSocket自动重连管理器。

    实现WebSocket连接的自动重连和恢复机制。

    Example:
        >>> manager = WebSocketReconnectionManager()
        >>> manager.register_connection("ws_1", connect_func, on_message_func)
        >>> await manager.start_reconnection("ws_1")
    """

    def __init__(
        self,
        default_config: Optional[RetryConfig] = None,
        heartbeat_interval: float = 30.0,
        heartbeat_timeout: float = 90.0,
    ):
        """初始化WebSocket重连管理器。

        Args:
            default_config: 默认重试配置
            heartbeat_interval: 心跳间隔（秒）
            heartbeat_timeout: 心跳超时（秒）
        """
        self.default_config = default_config or RetryConfig(
            max_retries=10,
            initial_delay=1.0,
            max_delay=60.0,
            backoff_factor=1.5,
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
        )
        self.heartbeat_interval = heartbeat_interval
        self.heartbeat_timeout = heartbeat_timeout

        # 连接函数映射
        self._connect_funcs: Dict[str, Callable] = {}
        self._disconnect_funcs: Dict[str, Callable] = {}
        self._on_message_funcs: Dict[str, Callable] = {}
        self._on_reconnect_funcs: Dict[str, Callable] = {}

        # 连接状态
        self._connection_states: Dict[str, WebSocketReconnectionState] = {}

        # 连接特定配置
        self._connection_configs: Dict[str, RetryConfig] = {}

        # 重连任务
        self._reconnection_tasks: Dict[str, asyncio.Task] = {}

        # 心跳任务
        self._heartbeat_tasks: Dict[str, asyncio.Task] = {}

        # WebSocket对象
        self._websockets: Dict[str, Any] = {}

        logger.info("WebSocketReconnectionManager 初始化完成")

    def register_connection(
        self,
        connection_id: str,
        connect_func: Callable,
        on_message_func: Optional[Callable] = None,
        on_reconnect_func: Optional[Callable] = None,
        disconnect_func: Optional[Callable] = None,
        config: Optional[RetryConfig] = None,
        endpoint: str = "",
    ) -> None:
        """注册WebSocket连接。

        Args:
            connection_id: 连接ID
            connect_func: 连接函数（异步）
            on_message_func: 消息处理函数（异步，可选）
            on_reconnect_func: 重连回调函数（异步，可选）
            disconnect_func: 断开连接函数（异步，可选）
            config: 连接特定的重试配置
            endpoint: 端点路径
        """
        self._connect_funcs[connection_id] = connect_func

        if on_message_func:
            self._on_message_funcs[connection_id] = on_message_func

        if on_reconnect_func:
            self._on_reconnect_funcs[connection_id] = on_reconnect_func

        if disconnect_func:
            self._disconnect_funcs[connection_id] = disconnect_func

        if config:
            self._connection_configs[connection_id] = config

        # 初始化连接状态
        if connection_id not in self._connection_states:
            self._connection_states[connection_id] = WebSocketReconnectionState(
                connection_id=connection_id,
                endpoint=endpoint,
            )

        logger.info(f"WebSocket连接 '{connection_id}' 已注册")

    def unregister_connection(self, connection_id: str) -> None:
        """注销WebSocket连接。

        Args:
            connection_id: 连接ID
        """
        # 取消任务
        if connection_id in self._reconnection_tasks:
            self._reconnection_tasks[connection_id].cancel()
            del self._reconnection_tasks[connection_id]

        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
            del self._heartbeat_tasks[connection_id]

        # 清理状态
        self._connect_funcs.pop(connection_id, None)
        self._disconnect_funcs.pop(connection_id, None)
        self._on_message_funcs.pop(connection_id, None)
        self._on_reconnect_funcs.pop(connection_id, None)
        self._connection_configs.pop(connection_id, None)
        self._connection_states.pop(connection_id, None)
        self._websockets.pop(connection_id, None)

        logger.info(f"WebSocket连接 '{connection_id}' 已注销")

    async def connect(self, connection_id: str) -> bool:
        """连接WebSocket（带自动重试）。

        Args:
            connection_id: 连接ID

        Returns:
            bool: 是否连接成功
        """
        if connection_id not in self._connect_funcs:
            logger.error(f"WebSocket连接 '{connection_id}' 未注册")
            return False

        state = self._connection_states.get(connection_id)
        if not state:
            state = WebSocketReconnectionState(connection_id=connection_id)
            self._connection_states[connection_id] = state

        config = self._connection_configs.get(connection_id, self.default_config)
        executor = RetryExecutor(config)

        state.state = RecoveryState.RECOVERING

        result = await executor.execute(self._connect_funcs[connection_id])

        if result.success:
            state.connected = True
            state.last_connected_time = time.time()
            state.last_error = None
            state.state = RecoveryState.RECOVERED
            self._websockets[connection_id] = result.result

            # 启动心跳任务
            self._heartbeat_tasks[connection_id] = asyncio.create_task(
                self._heartbeat_loop(connection_id)
            )

            logger.info(f"WebSocket连接 '{connection_id}' 连接成功")

            # 调用重连回调
            if state.reconnect_count > 0:
                on_reconnect = self._on_reconnect_funcs.get(connection_id)
                if on_reconnect:
                    try:
                        if asyncio.iscoroutinefunction(on_reconnect):
                            await on_reconnect()
                        else:
                            on_reconnect()
                    except Exception as e:
                        logger.error(f"重连回调执行失败: {e}")

            return True
        else:
            state.connected = False
            state.last_error = str(result.last_exception)
            state.state = RecoveryState.FAILED if result.attempts < config.max_retries else RecoveryState.EXHAUSTED
            logger.error(f"WebSocket连接 '{connection_id}' 连接失败: {state.last_error}")
            return False

    async def disconnect(self, connection_id: str) -> bool:
        """断开WebSocket连接。

        Args:
            connection_id: 连接ID

        Returns:
            bool: 是否断开成功
        """
        state = self._connection_states.get(connection_id)
        if not state:
            return True

        # 取消任务
        if connection_id in self._reconnection_tasks:
            self._reconnection_tasks[connection_id].cancel()
            del self._reconnection_tasks[connection_id]

        if connection_id in self._heartbeat_tasks:
            self._heartbeat_tasks[connection_id].cancel()
            del self._heartbeat_tasks[connection_id]

        disconnect_func = self._disconnect_funcs.get(connection_id)
        if disconnect_func:
            try:
                if asyncio.iscoroutinefunction(disconnect_func):
                    await disconnect_func()
                else:
                    disconnect_func()
            except Exception as e:
                logger.error(f"断开WebSocket连接 '{connection_id}' 失败: {e}")

        state.connected = False
        state.state = RecoveryState.IDLE
        self._websockets.pop(connection_id, None)

        logger.info(f"WebSocket连接 '{connection_id}' 已断开")
        return True

    async def start_reconnection(self, connection_id: str) -> None:
        """启动WebSocket重连任务。

        Args:
            connection_id: 连接ID
        """
        if connection_id in self._reconnection_tasks:
            logger.warning(f"WebSocket连接 '{connection_id}' 重连任务已在运行")
            return

        self._reconnection_tasks[connection_id] = asyncio.create_task(
            self._reconnection_loop(connection_id)
        )
        logger.info(f"WebSocket连接 '{connection_id}' 重连任务已启动")

    async def stop_reconnection(self, connection_id: str) -> None:
        """停止WebSocket重连任务。

        Args:
            connection_id: 连接ID
        """
        if connection_id in self._reconnection_tasks:
            self._reconnection_tasks[connection_id].cancel()
            del self._reconnection_tasks[connection_id]
            logger.info(f"WebSocket连接 '{connection_id}' 重连任务已停止")

    async def _heartbeat_loop(self, connection_id: str) -> None:
        """心跳循环。

        Args:
            connection_id: 连接ID
        """
        state = self._connection_states.get(connection_id)
        if not state:
            return

        last_pong_time = time.time()

        while True:
            try:
                await asyncio.sleep(self.heartbeat_interval)

                # 检查心跳超时
                if time.time() - last_pong_time > self.heartbeat_timeout:
                    logger.warning(
                        f"WebSocket连接 '{connection_id}' 心跳超时，"
                        f"准备重连..."
                    )
                    state.connected = False
                    state.last_error = "心跳超时"

                    # 取消当前心跳任务，触发重连
                    break

                # 发送心跳
                ws = self._websockets.get(connection_id)
                if ws:
                    try:
                        # 发送ping消息
                        if hasattr(ws, "ping"):
                            await ws.ping()
                        elif hasattr(ws, "send"):
                            await ws.send(json.dumps({"type": "ping"}))
                    except Exception as e:
                        logger.error(f"发送心跳失败: {e}")
                        state.connected = False
                        break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"心跳循环异常: {e}")
                break

    async def _reconnection_loop(self, connection_id: str) -> None:
        """重连循环。

        Args:
            connection_id: 连接ID
        """
        state = self._connection_states.get(connection_id)
        config = self._connection_configs.get(connection_id, self.default_config)

        while True:
            try:
                # 检查连接状态
                if not state.connected:
                    logger.info(f"WebSocket连接 '{connection_id}' 未连接，尝试重连...")
                    success = await self.connect(connection_id)

                    if success:
                        state.reconnect_count += 1
                    else:
                        # 等待后重试
                        delay = config.calculate_delay(state.reconnect_count + 1)
                        await asyncio.sleep(delay)
                        continue

                # 正常检查间隔
                await asyncio.sleep(10.0)

            except asyncio.CancelledError:
                logger.info(f"WebSocket连接 '{connection_id}' 重连循环已取消")
                break
            except Exception as e:
                logger.error(f"WebSocket连接 '{connection_id}' 重连循环异常: {e}")
                await asyncio.sleep(5.0)

    def get_connection_state(self, connection_id: str) -> Optional[Dict[str, Any]]:
        """获取连接状态。

        Args:
            connection_id: 连接ID

        Returns:
            Optional[Dict[str, Any]]: 连接状态字典
        """
        state = self._connection_states.get(connection_id)
        return state.to_dict() if state else None

    def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        """获取所有连接状态。

        Returns:
            Dict[str, Dict[str, Any]]: 所有连接状态
        """
        return {
            connection_id: state.to_dict()
            for connection_id, state in self._connection_states.items()
        }


@dataclass
class ExperimentCheckpoint:
    """实验检查点数据类。

    Attributes:
        experiment_id: 实验ID
        experiment_name: 实验名称
        status: 实验状态
        current_step: 当前步骤
        total_steps: 总步骤数
        progress: 进度（0-1）
        start_time: 开始时间
        checkpoint_time: 检查点时间
        data: 实验数据
        metadata: 元数据
    """

    experiment_id: int
    experiment_name: str
    status: str
    current_step: int
    total_steps: int
    progress: float
    start_time: float
    checkpoint_time: float = field(default_factory=time.time)
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典。

        Returns:
            Dict[str, Any]: 检查点字典
        """
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "status": self.status,
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "progress": self.progress,
            "start_time": self.start_time,
            "checkpoint_time": self.checkpoint_time,
            "data": self.data,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExperimentCheckpoint":
        """从字典创建检查点。

        Args:
            data: 字典数据

        Returns:
            ExperimentCheckpoint: 检查点实例
        """
        return cls(
            experiment_id=data["experiment_id"],
            experiment_name=data["experiment_name"],
            status=data["status"],
            current_step=data["current_step"],
            total_steps=data["total_steps"],
            progress=data["progress"],
            start_time=data["start_time"],
            checkpoint_time=data.get("checkpoint_time", time.time()),
            data=data.get("data", {}),
            metadata=data.get("metadata", {}),
        )


class ExperimentStateRecovery:
    """实验状态自动保存和恢复管理器。

    实现实验状态的自动保存和恢复机制。

    Example:
        >>> recovery = ExperimentStateRecovery(checkpoint_dir="checkpoints")
        >>> recovery.save_checkpoint(experiment_id, experiment_data)
        >>> checkpoint = recovery.load_checkpoint(experiment_id)
    """

    def __init__(
        self,
        checkpoint_dir: str = "checkpoints",
        auto_save_interval: float = 60.0,
        max_checkpoints: int = 10,
    ):
        """初始化实验状态恢复管理器。

        Args:
            checkpoint_dir: 检查点目录
            auto_save_interval: 自动保存间隔（秒）
            max_checkpoints: 最大检查点数量
        """
        self.checkpoint_dir = Path(checkpoint_dir)
        self.auto_save_interval = auto_save_interval
        self.max_checkpoints = max_checkpoints

        # 创建检查点目录
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

        # 活跃实验
        self._active_experiments: Dict[int, ExperimentCheckpoint] = {}

        # 自动保存任务
        self._auto_save_tasks: Dict[int, asyncio.Task] = {}

        # 状态变更回调
        self._on_state_change_callbacks: List[Callable] = []

        logger.info(f"ExperimentStateRecovery 初始化完成，检查点目录: {checkpoint_dir}")

    def register_experiment(
        self,
        experiment_id: int,
        experiment_name: str,
        total_steps: int,
        metadata: Optional[Dict[str, Any]] = None,
        auto_save: bool = True,
    ) -> None:
        """注册实验。

        Args:
            experiment_id: 实验ID
            experiment_name: 实验名称
            total_steps: 总步骤数
            metadata: 元数据
            auto_save: 是否启用自动保存
        """
        checkpoint = ExperimentCheckpoint(
            experiment_id=experiment_id,
            experiment_name=experiment_name,
            status="running",
            current_step=0,
            total_steps=total_steps,
            progress=0.0,
            start_time=time.time(),
            metadata=metadata or {},
        )

        self._active_experiments[experiment_id] = checkpoint

        # 启动自动保存任务（仅在事件循环运行时）
        if auto_save:
            self._start_auto_save_task(experiment_id)

        logger.info(f"实验 '{experiment_name}' (ID: {experiment_id}) 已注册")

    def _start_auto_save_task(self, experiment_id: int) -> None:
        """启动自动保存任务。

        Args:
            experiment_id: 实验ID
        """
        try:
            loop = asyncio.get_running_loop()
            self._auto_save_tasks[experiment_id] = asyncio.create_task(
                self._auto_save_loop(experiment_id)
            )
        except RuntimeError:
            # 没有运行的事件循环，延迟创建
            logger.debug(f"无运行事件循环，自动保存任务将在首次访问时创建")

    def unregister_experiment(self, experiment_id: int) -> None:
        """注销实验。

        Args:
            experiment_id: 实验ID
        """
        # 取消自动保存任务
        if experiment_id in self._auto_save_tasks:
            self._auto_save_tasks[experiment_id].cancel()
            del self._auto_save_tasks[experiment_id]

        # 移除活跃实验
        self._active_experiments.pop(experiment_id, None)

        logger.info(f"实验 ID {experiment_id} 已注销")

    def update_progress(
        self,
        experiment_id: int,
        current_step: int,
        status: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """更新实验进度。

        Args:
            experiment_id: 实验ID
            current_step: 当前步骤
            status: 状态（可选）
            data: 数据（可选）
        """
        checkpoint = self._active_experiments.get(experiment_id)
        if not checkpoint:
            logger.warning(f"实验 ID {experiment_id} 未注册")
            return

        checkpoint.current_step = current_step
        checkpoint.progress = current_step / checkpoint.total_steps if checkpoint.total_steps > 0 else 0.0

        if status:
            checkpoint.status = status

        if data:
            checkpoint.data.update(data)

        # 触发状态变更回调
        for callback in self._on_state_change_callbacks:
            try:
                callback(checkpoint)
            except Exception as e:
                logger.error(f"状态变更回调执行失败: {e}")

    def save_checkpoint(
        self,
        experiment_id: int,
        force: bool = False,
    ) -> bool:
        """保存检查点。

        Args:
            experiment_id: 实验ID
            force: 是否强制保存

        Returns:
            bool: 是否保存成功
        """
        checkpoint = self._active_experiments.get(experiment_id)
        if not checkpoint:
            logger.warning(f"实验 ID {experiment_id} 未注册")
            return False

        checkpoint.checkpoint_time = time.time()

        # 保存到文件
        checkpoint_file = self.checkpoint_dir / f"experiment_{experiment_id}_checkpoint.json"

        try:
            with open(checkpoint_file, "w", encoding="utf-8") as f:
                json.dump(checkpoint.to_dict(), f, ensure_ascii=False, indent=2)

            logger.info(
                f"实验 '{checkpoint.experiment_name}' (ID: {experiment_id}) "
                f"检查点已保存，进度: {checkpoint.progress:.2%}"
            )
            return True

        except Exception as e:
            logger.error(f"保存检查点失败: {e}")
            return False

    def load_checkpoint(self, experiment_id: int) -> Optional[ExperimentCheckpoint]:
        """加载检查点。

        Args:
            experiment_id: 实验ID

        Returns:
            Optional[ExperimentCheckpoint]: 检查点数据，不存在时返回None
        """
        checkpoint_file = self.checkpoint_dir / f"experiment_{experiment_id}_checkpoint.json"

        if not checkpoint_file.exists():
            logger.info(f"实验 ID {experiment_id} 检查点不存在")
            return None

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            checkpoint = ExperimentCheckpoint.from_dict(data)
            logger.info(
                f"实验 '{checkpoint.experiment_name}' (ID: {experiment_id}) "
                f"检查点已加载，进度: {checkpoint.progress:.2%}"
            )
            return checkpoint

        except Exception as e:
            logger.error(f"加载检查点失败: {e}")
            return None

    def delete_checkpoint(self, experiment_id: int) -> bool:
        """删除检查点。

        Args:
            experiment_id: 实验ID

        Returns:
            bool: 是否删除成功
        """
        checkpoint_file = self.checkpoint_dir / f"experiment_{experiment_id}_checkpoint.json"

        if not checkpoint_file.exists():
            return True

        try:
            checkpoint_file.unlink()
            logger.info(f"实验 ID {experiment_id} 检查点已删除")
            return True
        except Exception as e:
            logger.error(f"删除检查点失败: {e}")
            return False

    def list_checkpoints(self) -> List[Dict[str, Any]]:
        """列出所有检查点。

        Returns:
            List[Dict[str, Any]]: 检查点列表
        """
        checkpoints = []

        for checkpoint_file in self.checkpoint_dir.glob("experiment_*_checkpoint.json"):
            try:
                with open(checkpoint_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                checkpoints.append(data)
            except Exception as e:
                logger.error(f"读取检查点文件失败: {checkpoint_file}, 错误: {e}")

        # 按检查点时间排序
        checkpoints.sort(key=lambda x: x.get("checkpoint_time", 0), reverse=True)

        return checkpoints

    def cleanup_old_checkpoints(self) -> int:
        """清理旧检查点。

        Returns:
            int: 清理的检查点数量
        """
        checkpoints = self.list_checkpoints()

        if len(checkpoints) <= self.max_checkpoints:
            return 0

        # 删除超出数量的旧检查点
        to_delete = checkpoints[self.max_checkpoints :]
        deleted_count = 0

        for checkpoint in to_delete:
            experiment_id = checkpoint["experiment_id"]
            if self.delete_checkpoint(experiment_id):
                deleted_count += 1

        logger.info(f"已清理 {deleted_count} 个旧检查点")
        return deleted_count

    async def _auto_save_loop(self, experiment_id: int) -> None:
        """自动保存循环。

        Args:
            experiment_id: 实验ID
        """
        while True:
            try:
                await asyncio.sleep(self.auto_save_interval)
                self.save_checkpoint(experiment_id)
            except asyncio.CancelledError:
                # 退出前保存一次
                self.save_checkpoint(experiment_id)
                break
            except Exception as e:
                logger.error(f"自动保存失败: {e}")

    def add_state_change_callback(self, callback: Callable) -> None:
        """添加状态变更回调。

        Args:
            callback: 回调函数
        """
        self._on_state_change_callbacks.append(callback)

    def remove_state_change_callback(self, callback: Callable) -> None:
        """移除状态变更回调。

        Args:
            callback: 回调函数
        """
        if callback in self._on_state_change_callbacks:
            self._on_state_change_callbacks.remove(callback)

    def get_experiment_state(self, experiment_id: int) -> Optional[Dict[str, Any]]:
        """获取实验状态。

        Args:
            experiment_id: 实验ID

        Returns:
            Optional[Dict[str, Any]]: 实验状态字典
        """
        checkpoint = self._active_experiments.get(experiment_id)
        return checkpoint.to_dict() if checkpoint else None

    def get_all_states(self) -> Dict[int, Dict[str, Any]]:
        """获取所有实验状态。

        Returns:
            Dict[int, Dict[str, Any]]: 所有实验状态
        """
        return {
            exp_id: checkpoint.to_dict()
            for exp_id, checkpoint in self._active_experiments.items()
        }


class ErrorRecoveryManager:
    """错误恢复管理器。

    统一管理设备连接恢复、WebSocket重连和实验状态恢复。

    Example:
        >>> manager = ErrorRecoveryManager()
        >>> await manager.initialize()
        >>> manager.register_device("motor_1", connect_func)
        >>> manager.register_websocket("ws_1", connect_func)
        >>> manager.register_experiment(1, "实验1", 10)
    """

    def __init__(
        self,
        checkpoint_dir: str = "checkpoints",
        device_state_file: str = "device_states.json",
    ):
        """初始化错误恢复管理器。

        Args:
            checkpoint_dir: 检查点目录
            device_state_file: 设备状态文件
        """
        self.device_recovery = DeviceConnectionRecovery(state_file=device_state_file)
        self.websocket_recovery = WebSocketReconnectionManager()
        self.experiment_recovery = ExperimentStateRecovery(checkpoint_dir=checkpoint_dir)

        self._initialized = False

        logger.info("ErrorRecoveryManager 初始化完成")

    async def initialize(self) -> None:
        """初始化管理器。"""
        if self._initialized:
            return

        # 恢复未完成的实验
        checkpoints = self.experiment_recovery.list_checkpoints()
        for checkpoint_data in checkpoints:
            if checkpoint_data.get("status") == "running":
                logger.info(
                    f"发现未完成的实验: {checkpoint_data['experiment_name']} "
                    f"(ID: {checkpoint_data['experiment_id']})"
                )

        self._initialized = True
        logger.info("ErrorRecoveryManager 已初始化")

    async def shutdown(self) -> None:
        """关闭管理器。"""
        # 保存所有活跃实验
        for experiment_id in list(self.experiment_recovery._active_experiments.keys()):
            self.experiment_recovery.save_checkpoint(experiment_id)

        # 停止所有恢复任务
        for device_id in list(self.device_recovery._recovery_tasks.keys()):
            await self.device_recovery.stop_recovery(device_id)

        for connection_id in list(self.websocket_recovery._reconnection_tasks.keys()):
            await self.websocket_recovery.stop_reconnection(connection_id)

        logger.info("ErrorRecoveryManager 已关闭")

    # 设备相关方法
    def register_device(
        self,
        device_id: str,
        connect_func: Callable,
        disconnect_func: Optional[Callable] = None,
        health_check_func: Optional[Callable] = None,
        config: Optional[RetryConfig] = None,
    ) -> None:
        """注册设备。"""
        self.device_recovery.register_device(
            device_id, connect_func, disconnect_func, health_check_func, config
        )

    async def connect_device(self, device_id: str) -> bool:
        """连接设备。"""
        return await self.device_recovery.connect_device(device_id)

    async def disconnect_device(self, device_id: str) -> bool:
        """断开设备。"""
        return await self.device_recovery.disconnect_device(device_id)

    # WebSocket相关方法
    def register_websocket(
        self,
        connection_id: str,
        connect_func: Callable,
        on_message_func: Optional[Callable] = None,
        on_reconnect_func: Optional[Callable] = None,
        config: Optional[RetryConfig] = None,
    ) -> None:
        """注册WebSocket连接。"""
        self.websocket_recovery.register_connection(
            connection_id, connect_func, on_message_func, on_reconnect_func, config=config
        )

    async def connect_websocket(self, connection_id: str) -> bool:
        """连接WebSocket。"""
        return await self.websocket_recovery.connect(connection_id)

    async def disconnect_websocket(self, connection_id: str) -> bool:
        """断开WebSocket。"""
        return await self.websocket_recovery.disconnect(connection_id)

    # 实验相关方法
    def register_experiment(
        self,
        experiment_id: int,
        experiment_name: str,
        total_steps: int,
        metadata: Optional[Dict[str, Any]] = None,
        auto_save: bool = True,
    ) -> None:
        """注册实验。"""
        self.experiment_recovery.register_experiment(
            experiment_id, experiment_name, total_steps, metadata, auto_save
        )

    def update_experiment_progress(
        self,
        experiment_id: int,
        current_step: int,
        status: Optional[str] = None,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """更新实验进度。"""
        self.experiment_recovery.update_progress(experiment_id, current_step, status, data)

    def save_experiment_checkpoint(self, experiment_id: int) -> bool:
        """保存实验检查点。"""
        return self.experiment_recovery.save_checkpoint(experiment_id)

    def load_experiment_checkpoint(self, experiment_id: int) -> Optional[ExperimentCheckpoint]:
        """加载实验检查点。"""
        return self.experiment_recovery.load_checkpoint(experiment_id)

    def get_recovery_stats(self) -> Dict[str, Any]:
        """获取恢复统计信息。

        Returns:
            Dict[str, Any]: 恢复统计信息
        """
        return {
            "devices": self.device_recovery.get_all_states(),
            "websockets": self.websocket_recovery.get_all_states(),
            "experiments": self.experiment_recovery.get_all_states(),
            "checkpoints": self.experiment_recovery.list_checkpoints(),
        }


# 全局错误恢复管理器实例
error_recovery_manager = ErrorRecoveryManager()
