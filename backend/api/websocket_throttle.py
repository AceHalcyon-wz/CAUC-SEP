"""
WebSocket 数据节流模块。

实现数据推送频率控制，避免高频数据推送导致的网络拥塞和客户端过载。
支持批量发送、动态间隔调整和优先级队列。

文件路径: backend/api/websocket_throttle.py
功能: 数据节流器、批量发送、频率控制
作者: Agent
创建日期: 2026-03-16
依赖: asyncio
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar
from collections.abc import Callable

logger = logging.getLogger(__name__)

# 默认配置常量
DEFAULT_MIN_INTERVAL: float = 0.1  # 10 Hz
DEFAULT_MAX_BATCH_SIZE: int = 10
DEFAULT_MAX_BUFFER_SIZE: int = 1000

T = TypeVar("T")


@dataclass
class ThrottleConfig:
    """
    节流配置。

    定义数据节流器的行为参数。

    Attributes:
        min_interval: 最小推送间隔（秒），默认 0.1 秒（10 Hz）
        max_batch_size: 单次最大批量发送数量
        enable_batching: 是否启用批量发送
        max_buffer_size: 最大缓冲区大小，超过时丢弃旧数据
        adaptive: 是否启用自适应间隔调整

    Example:
        >>> config = ThrottleConfig(
        ...     min_interval=0.05,  # 20 Hz
        ...     max_batch_size=20,
        ...     enable_batching=True
        ... )
    """

    min_interval: float = DEFAULT_MIN_INTERVAL
    max_batch_size: int = DEFAULT_MAX_BATCH_SIZE
    enable_batching: bool = True
    max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE
    adaptive: bool = False


@dataclass
class ThrottleStats:
    """
    节流统计数据。

    记录节流器的运行状态和性能指标。

    Attributes:
        total_pushed: 总推送数据量
        total_sent: 实际发送次数
        total_dropped: 丢弃数据量
        current_buffer_size: 当前缓冲区大小
        last_send_time: 上次发送时间戳
        avg_batch_size: 平均批量大小
    """

    total_pushed: int = 0
    total_sent: int = 0
    total_dropped: int = 0
    current_buffer_size: int = 0
    last_send_time: float = 0.0
    avg_batch_size: float = 0.0

    @property
    def drop_rate(self) -> float:
        """
        计算数据丢弃率。

        Returns:
            float: 丢弃率（0.0-1.0）
        """
        if self.total_pushed <= 0:
            return 0.0
        return self.total_dropped / self.total_pushed

    def to_dict(self) -> dict[str, int | float]:
        """
        转换为字典格式。

        Returns:
            dict[str, int | float]: 统计数据的字典表示
        """
        return {
            "total_pushed": self.total_pushed,
            "total_sent": self.total_sent,
            "total_dropped": self.total_dropped,
            "drop_rate": round(self.drop_rate, 3),
            "current_buffer_size": self.current_buffer_size,
            "avg_batch_size": round(self.avg_batch_size, 2),
        }


class DataThrottler(Generic[T]):
    """
    数据节流器。

    缓冲高频数据，按配置的间隔批量发送，避免网络拥塞。

    Attributes:
        config: 节流配置
        stats: 节流统计数据

    Example:
        >>> config = ThrottleConfig(min_interval=0.1, max_batch_size=10)
        >>> throttler = DataThrottler(
        ...     config=config,
        ...     on_send=lambda batch: websocket.send_json(batch)
        ... )
        >>> await throttler.start()
        >>> await throttler.push(data)
        >>> await throttler.stop()
    """

    def __init__(
        self,
        config: ThrottleConfig,
        on_send: Callable[[list[T]], None] | Callable[[list[T]], Any],
    ) -> None:
        """
        初始化数据节流器。

        Args:
            config: 节流配置
            on_send: 发送回调函数，接收批量数据列表
        """
        self._config = config
        self._on_send = on_send
        self._buffer: deque[T] = deque(maxlen=config.max_buffer_size)
        self._last_send_time: float = 0.0
        self._lock = asyncio.Lock()
        self._task: asyncio.Task[None] | None = None
        self._running = False
        self._stats = ThrottleStats()
        self._batch_sizes: deque[int] = deque(maxlen=100)  # 用于计算平均批量大小

    @property
    def config(self) -> ThrottleConfig:
        """
        获取节流配置。

        Returns:
            ThrottleConfig: 当前配置
        """
        return self._config

    @property
    def stats(self) -> ThrottleStats:
        """
        获取统计数据。

        Returns:
            ThrottleStats: 节流统计数据
        """
        return self._stats

    @property
    def is_running(self) -> bool:
        """
        检查节流器是否正在运行。

        Returns:
            bool: 是否正在运行
        """
        return self._running

    @property
    def buffer_size(self) -> int:
        """
        获取当前缓冲区大小。

        Returns:
            int: 缓冲区中的数据数量
        """
        return len(self._buffer)

    async def start(self) -> None:
        """
        启动节流器。

        创建后台发送任务，开始处理缓冲数据。
        """
        if self._running:
            logger.warning("Throttler is already running")
            return

        self._running = True
        self._task = asyncio.create_task(self._send_loop())
        logger.info(
            f"Throttler started: interval={self._config.min_interval}s, "
            f"batch_size={self._config.max_batch_size}"
        )

    async def stop(self) -> None:
        """
        停止节流器。

        取消后台任务，发送剩余缓冲数据。
        """
        if not self._running:
            return

        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        # 发送剩余数据
        await self._flush()

        logger.info("Throttler stopped")

    async def push(self, data: T) -> bool:
        """
        推送数据到缓冲区。

        数据会被缓冲，按配置的间隔批量发送。
        如果缓冲区已满，丢弃最旧的数据。

        Args:
            data: 要推送的数据

        Returns:
            bool: 是否成功加入缓冲区（非满时返回 True）

        Example:
            >>> success = await throttler.push({"position": 100.0})
            >>> if not success:
            ...     print("缓冲区已满，旧数据被丢弃")
        """
        async with self._lock:
            self._stats.total_pushed += 1

            # 检查缓冲区是否已满
            if len(self._buffer) >= self._config.max_buffer_size:
                # 丢弃最旧的数据
                self._buffer.popleft()
                self._stats.total_dropped += 1
                logger.debug(
                    f"Buffer full, dropped oldest data. "
                    f"buffer_size={self._config.max_buffer_size}"
                )

            self._buffer.append(data)
            self._stats.current_buffer_size = len(self._buffer)

            # 如果不启用批量，且达到最小间隔，立即发送
            if not self._config.enable_batching:
                current_time = time.time()
                if current_time - self._last_send_time >= self._config.min_interval:
                    await self._flush()

            return True

    async def push_batch(self, data_list: list[T]) -> int:
        """
        批量推送数据到缓冲区。

        Args:
            data_list: 要推送的数据列表

        Returns:
            int: 成功加入缓冲区的数据数量
        """
        success_count = 0
        for data in data_list:
            if await self.push(data):
                success_count += 1
        return success_count

    async def _send_loop(self) -> None:
        """
        发送循环。

        按配置的间隔定期发送缓冲数据。
        """
        while self._running:
            try:
                await asyncio.sleep(self._config.min_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in send loop: {e}")
                await asyncio.sleep(0.1)  # 错误后短暂等待

    async def _flush(self) -> None:
        """
        刷新缓冲区。

        取出缓冲数据并调用发送回调。
        """
        async with self._lock:
            if not self._buffer:
                return

            # 取出数据
            batch: list[T] = []
            while self._buffer and len(batch) < self._config.max_batch_size:
                batch.append(self._buffer.popleft())

            if batch:
                self._last_send_time = time.time()
                self._stats.total_sent += 1
                self._stats.current_buffer_size = len(self._buffer)

                # 更新平均批量大小
                self._batch_sizes.append(len(batch))
                self._update_avg_batch_size()

                # 调用发送回调
                try:
                    result = self._on_send(batch)
                    # 支持异步回调
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error in send callback: {e}")
                    # 将数据放回缓冲区（如果可能）
                    for item in reversed(batch):
                        self._buffer.appendleft(item)
                    self._stats.current_buffer_size = len(self._buffer)

    def _update_avg_batch_size(self) -> None:
        """更新平均批量大小。"""
        if self._batch_sizes:
            self._stats.avg_batch_size = sum(self._batch_sizes) / len(self._batch_sizes)

    async def flush_now(self) -> None:
        """
        立即刷新缓冲区。

        忽略间隔限制，立即发送所有缓冲数据。
        """
        await self._flush()

    def clear(self) -> None:
        """
        清空缓冲区。

        丢弃所有缓冲数据。
        """
        self._buffer.clear()
        self._stats.current_buffer_size = 0
        self._batch_sizes.clear()

    def update_config(self, **kwargs: Any) -> None:
        """
        更新节流配置。

        Args:
            **kwargs: 要更新的配置参数

        Example:
            >>> throttler.update_config(min_interval=0.05, max_batch_size=20)
        """
        if "min_interval" in kwargs:
            self._config.min_interval = kwargs["min_interval"]
        if "max_batch_size" in kwargs:
            self._config.max_batch_size = kwargs["max_batch_size"]
        if "enable_batching" in kwargs:
            self._config.enable_batching = kwargs["enable_batching"]
        if "max_buffer_size" in kwargs:
            new_size = kwargs["max_buffer_size"]
            # 创建新的 deque 并复制数据
            old_buffer = list(self._buffer)
            self._buffer = deque(old_buffer[-new_size:], maxlen=new_size)
            self._config.max_buffer_size = new_size
            self._stats.current_buffer_size = len(self._buffer)


class PriorityDataThrottler(DataThrottler[T]):
    """
    优先级数据节流器。

    支持按优先级处理数据，高优先级数据优先发送。

    Example:
        >>> throttler = PriorityDataThrottler(
        ...     config=config,
        ...     on_send=send_callback,
        ...     priority_levels=3
        ... )
        >>> await throttler.push(data, priority=2)  # 高优先级
    """

    def __init__(
        self,
        config: ThrottleConfig,
        on_send: Callable[[list[T]], None] | Callable[[list[T]], Any],
        priority_levels: int = 3,
    ) -> None:
        """
        初始化优先级数据节流器。

        Args:
            config: 节流配置
            on_send: 发送回调函数
            priority_levels: 优先级数量（0 为最低）
        """
        super().__init__(config, on_send)
        self._priority_levels = priority_levels
        # 创建多个优先级队列
        self._priority_buffers: list[deque[T]] = [
            deque(maxlen=config.max_buffer_size // priority_levels)
            for _ in range(priority_levels)
        ]

    async def push(self, data: T, priority: int = 0) -> bool:
        """
        推送数据到指定优先级的缓冲区。

        Args:
            data: 要推送的数据
            priority: 优先级（0 为最低，priority_levels-1 为最高）

        Returns:
            bool: 是否成功加入缓冲区
        """
        if priority < 0:
            priority = 0
        elif priority >= self._priority_levels:
            priority = self._priority_levels - 1

        async with self._lock:
            self._stats.total_pushed += 1

            buffer = self._priority_buffers[priority]
            if len(buffer) >= buffer.maxlen:
                self._stats.total_dropped += 1
                buffer.popleft()

            buffer.append(data)
            self._stats.current_buffer_size = sum(
                len(b) for b in self._priority_buffers
            )
            return True

    async def _flush(self) -> None:
        """刷新缓冲区，按优先级顺序发送数据。"""
        async with self._lock:
            batch: list[T] = []

            # 按优先级从高到低取数据
            for priority in range(self._priority_levels - 1, -1, -1):
                buffer = self._priority_buffers[priority]
                while buffer and len(batch) < self._config.max_batch_size:
                    batch.append(buffer.popleft())

            if batch:
                self._last_send_time = time.time()
                self._stats.total_sent += 1
                self._stats.current_buffer_size = sum(
                    len(b) for b in self._priority_buffers
                )

                self._batch_sizes.append(len(batch))
                self._update_avg_batch_size()

                try:
                    result = self._on_send(batch)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error in send callback: {e}")

    def clear(self) -> None:
        """清空所有优先级缓冲区。"""
        for buffer in self._priority_buffers:
            buffer.clear()
        self._stats.current_buffer_size = 0
        self._batch_sizes.clear()


class AdaptiveThrottler(DataThrottler[T]):
    """
    自适应节流器。

    根据网络状况和客户端处理能力动态调整发送间隔。

    Example:
        >>> throttler = AdaptiveThrottler(
        ...     config=config,
        ...     on_send=send_callback,
        ...     min_interval=0.01,
        ...     max_interval=1.0
        ... )
        >>> throttler.report_latency(0.05)  # 报告延迟
    """

    def __init__(
        self,
        config: ThrottleConfig,
        on_send: Callable[[list[T]], None] | Callable[[list[T]], Any],
        min_interval: float = 0.01,
        max_interval: float = 1.0,
        target_latency: float = 0.05,
    ) -> None:
        """
        初始化自适应节流器。

        Args:
            config: 节流配置
            on_send: 发送回调函数
            min_interval: 最小间隔（最快发送频率）
            max_interval: 最大间隔（最慢发送频率）
            target_latency: 目标延迟（秒）
        """
        super().__init__(config, on_send)
        self._min_interval = min_interval
        self._max_interval = max_interval
        self._target_latency = target_latency
        self._current_interval = config.min_interval
        self._latency_samples: deque[float] = deque(maxlen=10)

    @property
    def current_interval(self) -> float:
        """
        获取当前发送间隔。

        Returns:
            float: 当前间隔（秒）
        """
        return self._current_interval

    def report_latency(self, latency: float) -> None:
        """
        报告网络延迟。

        用于自适应调整发送间隔。

        Args:
            latency: 延迟时间（秒）
        """
        self._latency_samples.append(latency)
        self._adjust_interval()

    def _adjust_interval(self) -> None:
        """根据延迟样本调整发送间隔。"""
        if not self._latency_samples:
            return

        avg_latency = sum(self._latency_samples) / len(self._latency_samples)

        if avg_latency > self._target_latency * 1.5:
            # 延迟过高，增加间隔
            self._current_interval = min(
                self._current_interval * 1.2, self._max_interval
            )
        elif avg_latency < self._target_latency * 0.5:
            # 延迟较低，减少间隔
            self._current_interval = max(
                self._current_interval * 0.8, self._min_interval
            )

        logger.debug(
            f"Adjusted interval: {self._current_interval:.3f}s "
            f"(avg_latency={avg_latency:.3f}s)"
        )

    async def _send_loop(self) -> None:
        """发送循环，使用自适应间隔。"""
        while self._running:
            try:
                await asyncio.sleep(self._current_interval)
                await self._flush()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in send loop: {e}")
                await asyncio.sleep(0.1)
