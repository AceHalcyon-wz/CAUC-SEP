"""
WebSocket 背压控制模块。

实现消息队列背压控制，防止客户端处理缓慢时服务器内存溢出。
当队列使用率超过阈值时，自动丢弃新消息并通知客户端降速。

文件路径: backend/api/websocket_backpressure.py
功能: 背压控制器、队列管理、流量调节
作者: Agent
创建日期: 2026-03-16
依赖: asyncio
"""

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from collections.abc import Callable

logger = logging.getLogger(__name__)

# 默认配置常量
DEFAULT_MAX_QUEUE_SIZE: int = 100
DEFAULT_THRESHOLD: float = 0.8
DEFAULT_LOW_WATER_MARK: float = 0.5
DEFAULT_TIMEOUT: float = 1.0


@dataclass
class BackpressureStats:
    """
    背压统计数据。

    记录消息队列的使用情况和性能指标。

    Attributes:
        queue_size: 当前队列大小
        max_queue_size: 最大队列大小
        dropped_messages: 已丢弃消息数
        total_messages: 总消息数
        avg_send_time_ms: 平均发送时间（毫秒）
        backpressure_events: 背压事件次数
        last_backpressure_time: 上次背压事件时间戳

    Example:
        >>> stats = BackpressureStats(max_queue_size=100)
        >>> print(f"队列使用率: {stats.queue_usage:.1%}")
    """

    queue_size: int = 0
    max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE
    dropped_messages: int = 0
    total_messages: int = 0
    avg_send_time_ms: float = 0.0
    backpressure_events: int = 0
    last_backpressure_time: float = 0.0

    @property
    def queue_usage(self) -> float:
        """
        计算队列使用率。

        Returns:
            float: 队列使用率（0.0-1.0）
        """
        if self.max_queue_size <= 0:
            return 0.0
        return self.queue_size / self.max_queue_size

    @property
    def drop_rate(self) -> float:
        """
        计算消息丢弃率。

        Returns:
            float: 消息丢弃率（0.0-1.0）
        """
        if self.total_messages <= 0:
            return 0.0
        return self.dropped_messages / self.total_messages

    def to_dict(self) -> dict[str, int | float]:
        """
        转换为字典格式。

        Returns:
            dict[str, int | float]: 统计数据的字典表示
        """
        return {
            "queue_size": self.queue_size,
            "max_queue_size": self.max_queue_size,
            "queue_usage": round(self.queue_usage, 3),
            "dropped_messages": self.dropped_messages,
            "total_messages": self.total_messages,
            "drop_rate": round(self.drop_rate, 3),
            "avg_send_time_ms": round(self.avg_send_time_ms, 2),
            "backpressure_events": self.backpressure_events,
        }


class BackpressureController:
    """
    背压控制器。

    管理消息队列，在高负载时自动丢弃消息并通知客户端。
    使用高水位线/低水位线机制实现平滑的流量控制。

    Attributes:
        stats: 背压统计数据
        is_backpressured: 是否处于背压状态

    Example:
        >>> controller = BackpressureController(
        ...     max_queue_size=100,
        ...     threshold=0.8,
        ...     on_backpressure=lambda usage: print(f"背压警告: {usage:.1%}")
        ... )
        >>> await controller.enqueue(message_data)
        >>> msg = await controller.dequeue()
    """

    def __init__(
        self,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
        threshold: float = DEFAULT_THRESHOLD,
        low_water_mark: float = DEFAULT_LOW_WATER_MARK,
        on_backpressure: Callable[[float], None] | None = None,
        on_recover: Callable[[], None] | None = None,
    ) -> None:
        """
        初始化背压控制器。

        Args:
            max_queue_size: 最大队列大小
            threshold: 高水位线阈值（触发背压）
            low_water_mark: 低水位线阈值（解除背压）
            on_backpressure: 背压触发回调函数
            on_recover: 背压解除回调函数
        """
        self._queue: deque[bytes] = deque(maxlen=max_queue_size)
        self._max_queue_size = max_queue_size
        self._threshold = threshold
        self._low_water_mark = low_water_mark
        self._on_backpressure = on_backpressure
        self._on_recover = on_recover
        self._stats = BackpressureStats(max_queue_size=max_queue_size)
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()
        self._event.set()  # 初始状态：可发送
        self._is_backpressured = False
        self._send_times: deque[float] = deque(maxlen=100)  # 用于计算平均发送时间

    @property
    def stats(self) -> BackpressureStats:
        """
        获取统计信息。

        Returns:
            BackpressureStats: 背压统计数据
        """
        return self._stats

    @property
    def is_backpressured(self) -> bool:
        """
        检查是否处于背压状态。

        Returns:
            bool: 是否处于背压状态
        """
        return self._is_backpressured

    @property
    def queue_size(self) -> int:
        """
        获取当前队列大小。

        Returns:
            int: 队列中的消息数量
        """
        return len(self._queue)

    async def enqueue(self, message: bytes) -> bool:
        """
        将消息加入队列。

        当队列使用率超过高水位线阈值时，丢弃消息并触发背压回调。
        消息丢弃策略：丢弃新消息（保护旧消息的完整性）。

        Args:
            message: 要加入队列的消息数据（已序列化）

        Returns:
            bool: 是否成功加入队列

        Example:
            >>> success = await controller.enqueue(msgpack_data)
            >>> if not success:
            ...     print("消息被丢弃，客户端应降低发送频率")
        """
        async with self._lock:
            self._stats.total_messages += 1
            current_usage = self._stats.queue_usage

            # 检查是否超过高水位线
            if current_usage >= self._threshold:
                self._stats.dropped_messages += 1

                # 触发背压状态
                if not self._is_backpressured:
                    self._is_backpressured = True
                    self._stats.backpressure_events += 1
                    self._stats.last_backpressure_time = time.time()
                    logger.warning(
                        f"Backpressure triggered: queue={self._stats.queue_size}, "
                        f"usage={current_usage:.1%}, threshold={self._threshold:.1%}"
                    )
                    if self._on_backpressure:
                        try:
                            self._on_backpressure(current_usage)
                        except Exception as e:
                            logger.error(f"Backpressure callback error: {e}")

                logger.debug(
                    f"Dropping message: queue={self._stats.queue_size}, "
                    f"dropped={self._stats.dropped_messages}"
                )
                return False

            # 加入队列
            self._queue.append(message)
            self._stats.queue_size = len(self._queue)
            self._event.set()  # 通知有新消息

            # 检查是否从背压状态恢复
            if self._is_backpressured and current_usage <= self._low_water_mark:
                self._is_backpressured = False
                logger.info(
                    f"Backpressure recovered: queue={self._stats.queue_size}, "
                    f"usage={current_usage:.1%}"
                )
                if self._on_recover:
                    try:
                        self._on_recover()
                    except Exception as e:
                        logger.error(f"Recover callback error: {e}")

            return True

    async def dequeue(self, timeout: float = DEFAULT_TIMEOUT) -> bytes | None:
        """
        从队列取出消息。

        如果队列为空，等待直到有新消息或超时。

        Args:
            timeout: 超时时间（秒）

        Returns:
            bytes | None: 消息数据，超时或队列为空时返回 None

        Example:
            >>> message = await controller.dequeue(timeout=1.0)
            >>> if message:
            ...     await websocket.send_bytes(message)
        """
        try:
            await asyncio.wait_for(self._event.wait(), timeout=timeout)
        except TimeoutError:
            return None

        async with self._lock:
            if not self._queue:
                self._event.clear()
                return None

            message = self._queue.popleft()
            self._stats.queue_size = len(self._queue)

            # 记录发送时间用于计算平均值
            self._send_times.append(time.time())
            self._update_avg_send_time()

            if not self._queue:
                self._event.clear()

            return message

    def _update_avg_send_time(self) -> None:
        """更新平均发送时间。"""
        if len(self._send_times) >= 2:
            # 计算最近发送间隔的平均值
            intervals = []
            times_list = list(self._send_times)
            for i in range(1, len(times_list)):
                intervals.append(times_list[i] - times_list[i - 1])
            if intervals:
                self._stats.avg_send_time_ms = (sum(intervals) / len(intervals)) * 1000

    def clear(self) -> None:
        """
        清空队列。

        重置所有状态，用于连接关闭或重置场景。
        """
        self._queue.clear()
        self._stats.queue_size = 0
        self._is_backpressured = False
        self._event.clear()
        self._send_times.clear()
        logger.debug("Queue cleared")

    def reset_stats(self) -> None:
        """
        重置统计数据。

        保留队列内容，仅重置计数器。
        """
        self._stats.dropped_messages = 0
        self._stats.total_messages = 0
        self._stats.backpressure_events = 0
        self._stats.avg_send_time_ms = 0.0
        self._send_times.clear()

    async def get_status(self) -> dict[str, int | float | bool]:
        """
        获取控制器状态。

        Returns:
            dict[str, int | float | bool]: 包含统计信息和状态
        """
        async with self._lock:
            return {
                **self._stats.to_dict(),
                "is_backpressured": self._is_backpressured,
                "threshold": self._threshold,
                "low_water_mark": self._low_water_mark,
            }


class MultiClientBackpressureManager:
    """
    多客户端背压管理器。

    为多个 WebSocket 连接提供独立的背压控制。

    Example:
        >>> manager = MultiClientBackpressureManager()
        >>> client_id = "client-001"
        >>> controller = manager.get_or_create(client_id)
        >>> await controller.enqueue(message)
    """

    def __init__(
        self,
        max_queue_size: int = DEFAULT_MAX_QUEUE_SIZE,
        threshold: float = DEFAULT_THRESHOLD,
        low_water_mark: float = DEFAULT_LOW_WATER_MARK,
    ) -> None:
        """
        初始化多客户端背压管理器。

        Args:
            max_queue_size: 每个客户端的最大队列大小
            threshold: 高水位线阈值
            low_water_mark: 低水位线阈值
        """
        self._max_queue_size = max_queue_size
        self._threshold = threshold
        self._low_water_mark = low_water_mark
        self._controllers: dict[str, BackpressureController] = {}
        self._lock = asyncio.Lock()

    def get_or_create(
        self,
        client_id: str,
        on_backpressure: Callable[[float], None] | None = None,
        on_recover: Callable[[], None] | None = None,
    ) -> BackpressureController:
        """
        获取或创建客户端的背压控制器。

        Args:
            client_id: 客户端标识
            on_backpressure: 背压触发回调
            on_recover: 背压解除回调

        Returns:
            BackpressureController: 客户端的背压控制器
        """
        if client_id not in self._controllers:
            self._controllers[client_id] = BackpressureController(
                max_queue_size=self._max_queue_size,
                threshold=self._threshold,
                low_water_mark=self._low_water_mark,
                on_backpressure=on_backpressure,
                on_recover=on_recover,
            )
        return self._controllers[client_id]

    def remove(self, client_id: str) -> None:
        """
        移除客户端的背压控制器。

        Args:
            client_id: 客户端标识
        """
        if client_id in self._controllers:
            self._controllers[client_id].clear()
            del self._controllers[client_id]

    async def get_all_stats(self) -> dict[str, dict[str, int | float | bool]]:
        """
        获取所有客户端的统计数据。

        Returns:
            dict[str, dict]: 客户端ID到统计数据的映射
        """
        result = {}
        for client_id, controller in self._controllers.items():
            result[client_id] = await controller.get_status()
        return result

    @property
    def client_count(self) -> int:
        """
        获取当前管理的客户端数量。

        Returns:
            int: 客户端数量
        """
        return len(self._controllers)
