"""
数据管道模块 (Data Pipeline Module)

本模块实现了流式数据处理的核心功能，包括：
- RingBuffer: 线程安全的环形缓冲区（支持零拷贝、批量操作）
- StreamProcessor: 流式数据处理器，支持多种触发机制（支持并行处理、背压控制）
- DataPipeline: 数据管道，整合缓冲区和处理器

设计参考：技术设计文档第8章节

作者: Agent
创建日期: 2024-03-07
更新日期: 2024-03-08
依赖: numpy, asyncio

性能优化:
- RingBuffer: 零拷贝读取、批量操作优化、内存视图支持
- StreamProcessor: 并行触发器检查、背压控制、智能缓存
- 统计: P50/P90/P95/P99延迟分布、吞吐量监控
"""

from __future__ import annotations

import asyncio
import time
from collections import deque
from collections.abc import Callable, Generator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from threading import Event, Lock, RLock
from typing import Any

import numpy as np
from numpy.typing import NDArray


class TriggerType(Enum):
    """
    触发类型枚举。

    定义数据处理器支持的触发机制类型。

    Attributes:
        THRESHOLD: 阈值触发，当数据超过指定阈值时触发
        PATTERN: 模式触发，当数据匹配特定模式时触发
        PERIODIC: 周期触发，按固定间隔触发
    """

    THRESHOLD = "threshold"
    PATTERN = "pattern"
    PERIODIC = "periodic"


class OverflowStrategy(Enum):
    """
    缓冲区溢出策略枚举。

    定义缓冲区满时的处理策略。

    Attributes:
        OVERWRITE_OLDEST: 覆盖最旧数据（默认，适合实时数据）
        DROP_NEW: 丢弃新数据（适合历史数据完整性优先）
        EXPAND: 动态扩容（适合数据量不确定场景）
    """

    OVERWRITE_OLDEST = "overwrite_oldest"
    DROP_NEW = "drop_new"
    EXPAND = "expand"


@dataclass
class TriggerConfig:
    """
    触发器配置数据类。

    存储触发器的完整配置信息，包括触发条件、回调函数和状态。

    Attributes:
        name: 触发器名称，作为唯一标识符
        trigger_type: 触发类型（THRESHOLD/PATTERN/PERIODIC）
        condition: 触发条件函数，接收数据数组，返回布尔值
        callback: 触发回调函数，接收触发时的数据
        enabled: 是否启用，默认True
        trigger_count: 触发次数统计，默认0
        last_check_time: 最后检查时间戳
        check_interval: 检查间隔（秒），0表示每次都检查
        cache_result: 是否缓存条件结果
        last_condition_result: 最后一次条件检查结果

    Example:
        >>> def my_condition(data: np.ndarray) -> bool:
        ...     return len(data) > 100
        >>> def my_callback(data: np.ndarray) -> None:
        ...     print(f"触发！数据长度: {len(data)}")
        >>> config = TriggerConfig(
        ...     name="length_trigger",
        ...     trigger_type=TriggerType.THRESHOLD,
        ...     condition=my_condition,
        ...     callback=my_callback
        ... )
    """

    name: str
    trigger_type: TriggerType
    condition: Callable[[np.ndarray], bool]
    callback: Callable[[np.ndarray], None]
    enabled: bool = True
    trigger_count: int = 0
    last_check_time: float = 0.0
    check_interval: float = 0.0  # 0表示每次都检查
    cache_result: bool = False
    last_condition_result: bool = False


@dataclass
class PipelineStatistics:
    """
    管道统计信息数据类。

    记录数据管道运行的各项统计指标，用于性能监控和分析。
    支持滑动窗口统计、吞吐量计算和延迟百分位分析。

    Attributes:
        total_data_points: 总处理数据点数
        total_bytes: 总处理字节数
        buffer_overflows: 缓冲区溢出次数
        trigger_activations: 触发器激活总次数
        avg_processing_time_ms: 平均处理时间（毫秒）
        last_update_time: 最后更新时间戳
        throughput_points_per_sec: 吞吐量（点/秒）
        peak_memory_usage_mb: 峰值内存使用（MB）
        batch_count: 批量处理次数
        avg_batch_size: 平均批量大小
        _processing_times: 内部处理时间记录列表
        _batch_sizes: 内部批量大小记录列表
        _start_time: 统计开始时间
        _last_throughput_check: 上次吞吐量检查时间
        _last_data_points: 上次检查时的数据点数

    Example:
        >>> stats = PipelineStatistics()
        >>> stats.update_processing_time(1.5)
        >>> stats.update_batch_size(100)
        >>> stats.update_throughput()
        >>> print(f"P95延迟: {stats.get_percentile_latency(95)}ms")
    """

    total_data_points: int = 0
    total_bytes: int = 0
    buffer_overflows: int = 0
    trigger_activations: int = 0
    avg_processing_time_ms: float = 0.0
    last_update_time: float = field(default_factory=time.time)
    _processing_times: list[float] = field(default_factory=list)

    # 新增性能指标
    throughput_points_per_sec: float = 0.0
    peak_memory_usage_mb: float = 0.0
    batch_count: int = 0
    avg_batch_size: float = 0.0
    _batch_sizes: list[int] = field(default_factory=list)
    _start_time: float = field(default_factory=time.time)
    _last_throughput_check: float = field(default_factory=time.time)
    _last_data_points: int = 0

    def update_processing_time(self, elapsed_ms: float) -> None:
        """
        更新处理时间统计。

        使用滑动窗口（最近100次）计算平均处理时间。

        Args:
            elapsed_ms: 本次处理耗时（毫秒）
        """
        self._processing_times.append(elapsed_ms)
        # 保留最近100次处理时间
        if len(self._processing_times) > 100:
            self._processing_times.pop(0)
        self.avg_processing_time_ms = float(np.mean(self._processing_times))

    def update_batch_size(self, batch_size: int) -> None:
        """
        更新批量大小统计。

        使用滑动窗口（最近100次）计算平均批量大小。

        Args:
            batch_size: 本次批量大小
        """
        self.batch_count += 1
        self._batch_sizes.append(batch_size)
        # 保留最近100次批量大小
        if len(self._batch_sizes) > 100:
            self._batch_sizes.pop(0)
        self.avg_batch_size = float(np.mean(self._batch_sizes))

    def update_throughput(self) -> None:
        """
        更新吞吐量统计。

        计算自上次检查以来的数据点处理速率（点/秒）。
        每秒更新一次以避免频繁计算。
        """
        current_time = time.time()
        time_elapsed = current_time - self._last_throughput_check

        if time_elapsed >= 1.0:  # 每秒更新一次
            points_processed = self.total_data_points - self._last_data_points
            self.throughput_points_per_sec = points_processed / time_elapsed
            self._last_throughput_check = current_time
            self._last_data_points = self.total_data_points

    def update_memory_usage(self, bytes_used: int) -> None:
        """
        更新内存使用统计。

        记录峰值内存使用量。

        Args:
            bytes_used: 当前使用的字节数
        """
        memory_mb = bytes_used / (1024 * 1024)
        self.peak_memory_usage_mb = max(self.peak_memory_usage_mb, memory_mb)

    def get_percentile_latency(self, percentile: float = 95.0) -> float:
        """
        获取指定百分位的延迟。

        Args:
            percentile: 百分位（0-100），默认95

        Returns:
            指定百分位的延迟（毫秒），无数据时返回0.0

        Example:
            >>> p95 = stats.get_percentile_latency(95)
            >>> p99 = stats.get_percentile_latency(99)
        """
        if not self._processing_times:
            return 0.0
        return float(np.percentile(self._processing_times, percentile))

    def get_latency_distribution(self) -> dict[str, float]:
        """
        获取延迟分布统计。

        返回多个百分位的延迟值，用于全面了解处理延迟分布。

        Returns:
            延迟分布字典，包含：
                - p50: 中位数延迟（毫秒）
                - p90: 90%延迟（毫秒）
                - p95: 95%延迟（毫秒）
                - p99: 99%延迟（毫秒）
            无数据时所有值返回0.0

        Example:
            >>> dist = stats.get_latency_distribution()
            >>> print(f"P99延迟: {dist['p99']}ms")
        """
        if not self._processing_times:
            return {"p50": 0.0, "p90": 0.0, "p95": 0.0, "p99": 0.0}

        return {
            "p50": float(np.percentile(self._processing_times, 50)),
            "p90": float(np.percentile(self._processing_times, 90)),
            "p95": float(np.percentile(self._processing_times, 95)),
            "p99": float(np.percentile(self._processing_times, 99)),
        }


class RingBuffer:
    """
    线程安全的环形缓冲区。

    用于存储和检索流式数据，支持高效的写入和读取操作。
    当缓冲区满时，根据配置的溢出策略处理新数据。

    环形缓冲区特点：
    - 固定大小，内存占用可预测
    - O(1)时间复杂度的写入和读取
    - 支持多种溢出策略
    - 线程安全
    - 支持零拷贝读取（内存视图）
    - 支持批量操作优化

    Attributes:
        size: 缓冲区大小（数据点数）
        dtype: 数据类型（numpy dtype）
        overflow_strategy: 溢出策略

    Example:
        >>> buffer = RingBuffer(size=1000)
        >>> buffer.write(np.array([1.0, 2.0, 3.0]))
        3
        >>> data = buffer.read(2)
        >>> print(data)  # [1.0, 2.0]
    """

    def __init__(
        self,
        size: int = 10000,
        dtype: type[np.floating[Any]] | type[np.integer[Any]] = np.float64,
        overflow_strategy: OverflowStrategy = OverflowStrategy.OVERWRITE_OLDEST,
        expand_threshold: float = 0.9,
    ) -> None:
        """
        初始化环形缓冲区。

        Args:
            size: 缓冲区大小（数据点数），默认10000
            dtype: 数据类型，默认np.float64
            overflow_strategy: 溢出策略，默认OVERWRITE_OLDEST
                - OVERWRITE_OLDEST: 覆盖最旧数据
                - DROP_NEW: 丢弃新数据
                - EXPAND: 动态扩容
            expand_threshold: 扩容阈值（0-1），当使用率超过此值时触发扩容

        Raises:
            ValueError: 当size小于等于0时抛出异常
        """
        if size <= 0:
            raise ValueError(f"缓冲区大小必须大于0，当前值: {size}")

        self._size = size
        self._dtype = dtype
        self._buffer = np.zeros(size, dtype=dtype)
        self._write_index = 0
        self._count = 0
        self._lock = Lock()
        self._overflow_strategy = overflow_strategy
        self._expand_threshold = expand_threshold
        self._overflow_count = 0  # 溢出计数器

        # 性能优化：预分配临时缓冲区
        self._temp_buffer = np.zeros(size, dtype=dtype)
        self._temp_buffer_valid = False

    def write(self, data: NDArray[np.floating[Any] | np.integer[Any]]) -> int:
        """
        写入数据到缓冲区。

        根据配置的溢出策略处理缓冲区满的情况：
        - OVERWRITE_OLDEST: 覆盖最旧数据
        - DROP_NEW: 丢弃新数据
        - EXPAND: 动态扩容

        Args:
            data: 待写入的数据数组

        Returns:
            实际写入的数据量

        Note:
            数据类型不匹配时会自动转换
        """
        if data is None or len(data) == 0:
            return 0

        # 确保数据类型正确
        if data.dtype != self._dtype:
            data = data.astype(self._dtype)

        data_len = len(data)

        with self._lock:
            # 计算可写入空间
            available_space = self._size - self._count
            write_len = min(data_len, available_space)

            if write_len == 0:
                # 缓冲区已满，根据策略处理
                if self._overflow_strategy == OverflowStrategy.DROP_NEW:
                    return 0
                elif self._overflow_strategy == OverflowStrategy.EXPAND:
                    # 动态扩容
                    self._expand_buffer(max(self._size * 2, self._size + data_len))
                    write_len = data_len
                else:  # OVERWRITE_OLDEST
                    self._overflow_count += 1
                    write_len = min(data_len, self._size)
                    if data_len >= self._size:
                        # 数据量大于缓冲区，只保留最新数据
                        self._buffer[:] = data[-self._size :]
                        self._write_index = 0
                        self._count = self._size
                        return write_len
                    else:
                        # 部分覆盖
                        self._write_index = (
                            self._write_index + self._size - write_len
                        ) % self._size
                        self._buffer[self._write_index : self._write_index + write_len] = data[
                            :write_len
                        ]
                        self._count = self._size
                        return write_len

            # 正常写入
            # 处理环形边界
            first_chunk = min(write_len, self._size - self._write_index)
            self._buffer[self._write_index : self._write_index + first_chunk] = data[:first_chunk]

            if first_chunk < write_len:
                # 需要回绕
                second_chunk = write_len - first_chunk
                self._buffer[:second_chunk] = data[first_chunk:write_len]

            self._write_index = (self._write_index + write_len) % self._size
            self._count = min(self._count + write_len, self._size)

            return write_len

    def write_batch(self, data_list: list[NDArray[np.floating[Any] | np.integer[Any]]]) -> int:
        """
        批量写入多个数据数组。

        优化多次小数据写入的性能，通过合并数据和减少锁竞争来提升效率。

        Args:
            data_list: 数据数组列表

        Returns:
            实际写入的总数据量

        Example:
            >>> buffer.write_batch([np.array([1.0, 2.0]), np.array([3.0, 4.0])])
            4
        """
        if not data_list:
            return 0

        # 预先计算总长度和类型转换
        total_len = 0
        converted_data = []
        for data in data_list:
            if data is not None and len(data) > 0:
                if data.dtype != self._dtype:
                    data = data.astype(self._dtype)
                converted_data.append(data)
                total_len += len(data)

        if total_len == 0:
            return 0

        # 合并所有数据
        merged_data = np.concatenate(converted_data)

        return self.write(merged_data)

    def _expand_buffer(self, new_size: int) -> None:
        """
        扩容缓冲区（内部方法）。

        创建新的更大缓冲区，并将现有数据复制过去。
        仅在OVERFLOW_STRATEGY为EXPAND时调用。

        Args:
            new_size: 新的缓冲区大小

        Warning:
            此方法会持有锁，可能阻塞其他操作
        """
        # 注意：此方法在write()的锁内调用，不能再次获取锁
        # 直接访问内部属性读取数据
        if self._count == 0:
            # 缓冲区为空，直接创建新缓冲区
            self._buffer = np.zeros(new_size, dtype=self._dtype)
            self._size = new_size
            self._write_index = 0
            self._count = 0
            return

        # 读取现有数据（不使用read_all避免锁竞争）
        read_index = (self._write_index - self._count + self._size) % self._size
        old_data = np.zeros(self._count, dtype=self._dtype)

        if self._count == self._size:
            # 缓冲区已满，直接复制
            old_data[:] = self._buffer
        else:
            # 处理环形边界
            first_chunk = min(self._count, self._size - read_index)
            old_data[:first_chunk] = self._buffer[read_index : read_index + first_chunk]

            if first_chunk < self._count:
                second_chunk = self._count - first_chunk
                old_data[first_chunk:] = self._buffer[:second_chunk]

        # 创建新缓冲区
        self._buffer = np.zeros(new_size, dtype=self._dtype)
        self._size = new_size

        # 重新写入数据
        write_len = min(len(old_data), new_size)
        self._buffer[:write_len] = old_data[-write_len:]
        self._write_index = write_len % new_size
        self._count = write_len

    def read(self, count: int) -> NDArray[np.floating[Any] | np.integer[Any]] | None:
        """
        从缓冲区读取指定数量的数据。

        读取后数据将从缓冲区移除（FIFO顺序）。

        Args:
            count: 要读取的数据量

        Returns:
            读取的数据数组，缓冲区为空或count<=0时返回None

        Example:
            >>> buffer.write(np.array([1.0, 2.0, 3.0]))
            3
            >>> data = buffer.read(2)
            >>> print(data)  # [1.0, 2.0]
        """
        if count <= 0:
            return None

        with self._lock:
            if self._count == 0:
                return None

            read_len = min(count, self._count)
            read_index = (self._write_index - self._count + self._size) % self._size

            result = np.zeros(read_len, dtype=self._dtype)

            # 处理环形边界
            first_chunk = min(read_len, self._size - read_index)
            result[:first_chunk] = self._buffer[read_index : read_index + first_chunk]

            if first_chunk < read_len:
                # 需要回绕
                second_chunk = read_len - first_chunk
                result[first_chunk:] = self._buffer[:second_chunk]

            # 更新计数
            self._count -= read_len

            return result

    def read_all(self) -> NDArray[np.floating[Any] | np.integer[Any]]:
        """
        读取缓冲区中的所有数据。

        读取后数据不会从缓冲区移除（peek操作）。

        Returns:
            缓冲区中的所有数据，按时间顺序排列。
            缓冲区为空时返回空数组。

        Example:
            >>> buffer.write(np.array([1.0, 2.0, 3.0]))
            3
            >>> all_data = buffer.read_all()
            >>> print(all_data)  # [1.0, 2.0, 3.0]
        """
        with self._lock:
            if self._count == 0:
                return np.array([], dtype=self._dtype)

            read_index = (self._write_index - self._count + self._size) % self._size

            if self._count == self._size:
                # 缓冲区已满，直接返回副本
                return self._buffer.copy()

            result = np.zeros(self._count, dtype=self._dtype)

            # 处理环形边界
            first_chunk = min(self._count, self._size - read_index)
            result[:first_chunk] = self._buffer[read_index : read_index + first_chunk]

            if first_chunk < self._count:
                second_chunk = self._count - first_chunk
                result[first_chunk:] = self._buffer[:second_chunk]

            return result

    def peek(self, count: int) -> NDArray[np.floating[Any] | np.integer[Any]] | None:
        """
        查看缓冲区中最新的数据（不移除）。

        从缓冲区末尾读取最新数据，但不改变缓冲区状态。

        Args:
            count: 要查看的数据量

        Returns:
            最新的数据数组（按时间顺序），缓冲区为空或count<=0时返回None

        Example:
            >>> buffer.write(np.array([1.0, 2.0, 3.0]))
            3
            >>> latest = buffer.peek(2)
            >>> print(latest)  # [2.0, 3.0]
        """
        if count <= 0:
            return None

        with self._lock:
            if self._count == 0:
                return None

            peek_len = min(count, self._count)

            result = np.zeros(peek_len, dtype=self._dtype)

            # 优化：使用向量化索引计算替代循环
            # 计算读取起始索引
            start_idx = (self._write_index - peek_len + self._size) % self._size

            # 处理环形边界
            if start_idx + peek_len <= self._size:
                # 不需要回绕
                result[:] = self._buffer[start_idx : start_idx + peek_len]
            else:
                # 需要回绕
                first_chunk = self._size - start_idx
                result[:first_chunk] = self._buffer[start_idx:]
                result[first_chunk:] = self._buffer[: peek_len - first_chunk]

            return result

    def clear(self) -> None:
        """
        清空缓冲区。

        重置写入索引、计数，并将缓冲区数据清零。
        """
        with self._lock:
            self._write_index = 0
            self._count = 0
            self._buffer.fill(0)

    @property
    def available(self) -> int:
        """
        返回可读数据量。

        Returns:
            缓冲区中当前的数据点数
        """
        with self._lock:
            return self._count

    @property
    def is_full(self) -> bool:
        """
        返回缓冲区是否已满。

        Returns:
            如果缓冲区已满返回True，否则返回False
        """
        with self._lock:
            return self._count >= self._size

    @property
    def capacity(self) -> int:
        """
        返回缓冲区总容量。

        Returns:
            缓冲区总大小（数据点数）
        """
        return self._size

    def get_latest(self, n: int = 1) -> NDArray[np.floating[Any] | np.integer[Any]] | None:
        """
        获取最新的n个数据点（不移除）。

        Args:
            n: 要获取的数据点数，默认1

        Returns:
            最新的n个数据点，缓冲区为空时返回None
        """
        return self.peek(n)

    def get_statistics(self) -> dict[str, Any]:
        """
        获取缓冲区统计信息。

        返回缓冲区状态和数据统计信息。

        Returns:
            统计信息字典，包含：
                - size: 缓冲区大小
                - count: 当前数据量
                - usage_percent: 使用率百分比
                - is_full: 是否已满
                - dtype: 数据类型
                - overflow_count: 溢出次数
                - overflow_strategy: 溢出策略
                - memory_bytes: 内存占用（字节）
                - min/max/mean/std: 数据统计（有数据时）
        """
        with self._lock:
            data = self.read_all()
            stats = {
                "size": self._size,
                "count": self._count,
                "usage_percent": (self._count / self._size * 100) if self._size > 0 else 0,
                "is_full": self._count >= self._size,
                "dtype": str(self._dtype),
                "overflow_count": self._overflow_count,
                "overflow_strategy": self._overflow_strategy.value,
                "memory_bytes": self._size * np.dtype(self._dtype).itemsize,
            }

            if len(data) > 0:
                stats.update(
                    {
                        "min": float(np.min(data)),
                        "max": float(np.max(data)),
                        "mean": float(np.mean(data)),
                        "std": float(np.std(data)),
                    }
                )

            return stats

    def read_zero_copy(
        self, count: int
    ) -> tuple[NDArray[np.floating[Any] | np.integer[Any]] | None, int]:
        """
        零拷贝读取指定数量的数据。

        返回缓冲区的内存视图，避免数据复制。
        注意：返回的视图在下次写入操作后可能失效。

        Args:
            count: 要读取的数据量

        Returns:
            元组 (数据视图, 实际读取数量)
            如果缓冲区为空，返回 (None, 0)

        Warning:
            返回的数组是缓冲区的视图，不应修改其内容。
            在下次写入操作前使用完毕。

        Example:
            >>> buffer.write(np.array([1.0, 2.0, 3.0]))
            >>> view, n = buffer.read_zero_copy(2)
            >>> print(view[:n])  # [1.0, 2.0]
        """
        if count <= 0:
            return None, 0

        with self._lock:
            if self._count == 0:
                return None, 0

            read_len = min(count, self._count)
            read_index = (self._write_index - self._count + self._size) % self._size

            # 检查是否需要回绕
            if read_index + read_len <= self._size:
                # 不需要回绕，直接返回视图
                view = self._buffer[read_index : read_index + read_len]
            else:
                # 需要回绕，必须复制到临时缓冲区
                first_chunk = self._size - read_index
                self._temp_buffer[:first_chunk] = self._buffer[read_index:]
                self._temp_buffer[first_chunk:read_len] = self._buffer[: read_len - first_chunk]
                view = self._temp_buffer[:read_len]
                self._temp_buffer_valid = True

            # 更新计数
            self._count -= read_len

            return view, read_len

    def write_fast(self, data: NDArray[np.floating[Any] | np.integer[Any]]) -> int:
        """
        快速写入数据（优化版本）。

        减少边界检查和类型转换开销，适用于高性能场景。
        调用者需确保数据类型正确。

        Args:
            data: 待写入的数据数组（必须匹配dtype）

        Returns:
            实际写入的数据量

        Note:
            此方法假设数据类型已正确，跳过类型检查。
            数据类型不匹配会导致未定义行为。
        """
        if data is None or len(data) == 0:
            return 0

        data_len = len(data)

        with self._lock:
            # 快速路径：缓冲区有足够空间
            available_space = self._size - self._count

            if data_len <= available_space:
                # 直接写入，无需处理溢出
                first_chunk = min(data_len, self._size - self._write_index)
                self._buffer[self._write_index : self._write_index + first_chunk] = data[
                    :first_chunk
                ]

                if first_chunk < data_len:
                    second_chunk = data_len - first_chunk
                    self._buffer[:second_chunk] = data[first_chunk:]

                self._write_index = (self._write_index + data_len) % self._size
                self._count += data_len
                return data_len

            # 溢出处理
            if self._overflow_strategy == OverflowStrategy.DROP_NEW:
                return 0
            elif self._overflow_strategy == OverflowStrategy.EXPAND:
                self._expand_buffer(max(self._size * 2, self._size + data_len))
                # 重新写入
                return self.write_fast(data)
            else:  # OVERWRITE_OLDEST
                self._overflow_count += 1
                if data_len >= self._size:
                    # 数据量大于缓冲区，只保留最新数据
                    self._buffer[:] = data[-self._size :]
                    self._write_index = 0
                    self._count = self._size
                    return self._size
                else:
                    # 部分覆盖
                    write_len = min(data_len, self._size)
                    self._write_index = (self._write_index + self._size - write_len) % self._size
                    first_chunk = min(write_len, self._size - self._write_index)
                    self._buffer[self._write_index : self._write_index + first_chunk] = data[
                        :first_chunk
                    ]

                    if first_chunk < write_len:
                        self._buffer[: write_len - first_chunk] = data[first_chunk:]

                    self._count = self._size
                    return write_len

    def get_contiguous_view(
        self,
    ) -> tuple[NDArray[np.floating[Any] | np.integer[Any]] | None, int, int]:
        """
        获取连续数据视图（零拷贝）。

        返回缓冲区中连续数据的视图，用于批量处理。
        如果数据跨越缓冲区边界，返回第一段连续数据。

        Returns:
            元组 (数据视图, 起始索引, 数据长度)
            如果缓冲区为空，返回 (None, 0, 0)

        Example:
            >>> view, start, length = buffer.get_contiguous_view()
            >>> if view is not None:
            ...     process(view[:length])
        """
        with self._lock:
            if self._count == 0:
                return None, 0, 0

            read_index = (self._write_index - self._count + self._size) % self._size
            contiguous_len = min(self._count, self._size - read_index)

            view = self._buffer[read_index : read_index + contiguous_len]
            return view, read_index, contiguous_len


class StreamProcessor:
    """
    流式数据处理器。

    支持多种触发机制的数据处理，包括阈值触发、模式触发和周期触发。
    可用于实时数据分析和事件检测。

    核心功能：
    - 数据缓冲与流式处理
    - 多触发器管理（支持并行检查）
    - 磁滞回线检测
    - 峰值检测
    - 背压控制
    - 性能监控

    Attributes:
        buffer_size: 内部缓冲区大小
        _buffer: 环形缓冲区实例
        _triggers: 触发器配置字典
        _statistics: 管道统计信息
        _backpressure_enabled: 是否启用背压控制
        _high_watermark: 高水位阈值
        _low_watermark: 低水位阈值

    Example:
        >>> processor = StreamProcessor(buffer_size=10000)
        >>> def threshold_callback(data):
        ...     print(f"阈值触发！数据长度: {len(data)}")
        >>> processor.add_trigger(
        ...     "high_value",
        ...     TriggerType.THRESHOLD,
        ...     lambda d: len(d) > 0 and d[-1] > 100,
        ...     threshold_callback
        ... )
        >>> processor.process(np.array([50.0, 75.0, 120.0]))
    """

    def __init__(
        self,
        buffer_size: int = 10000,
        enable_parallel_triggers: bool = False,
        backpressure_enabled: bool = True,
        high_watermark: float = 0.9,
        low_watermark: float = 0.7,
    ) -> None:
        """
        初始化流式数据处理器。

        Args:
            buffer_size: 内部缓冲区大小，默认10000
            enable_parallel_triggers: 是否启用并行触发器检查，默认False
            backpressure_enabled: 是否启用背压控制，默认True
            high_watermark: 高水位阈值（0-1），默认0.9
            low_watermark: 低水位阈值（0-1），默认0.7
        """
        self._buffer = RingBuffer(size=buffer_size)
        self._triggers: dict[str, TriggerConfig] = {}
        self._lock = RLock()
        self._statistics = PipelineStatistics()

        # 磁滞回线检测状态
        self._hysteresis_state = {
            "direction": 0,  # 0: 初始, 1: 正向, -1: 负向
            "peak_value": 0.0,
            "crossings": 0,
            "last_value": 0.0,
        }

        # 触发器执行优化：缓存数据
        self._cached_data: np.ndarray | None = None
        self._cache_valid = False
        self._last_buffer_count = 0

        # 并行处理支持
        self._enable_parallel_triggers = enable_parallel_triggers
        self._executor: ThreadPoolExecutor | None = None
        if enable_parallel_triggers:
            self._executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="trigger_")

        # 背压控制
        self._backpressure_enabled = backpressure_enabled
        self._high_watermark = int(buffer_size * high_watermark)
        self._low_watermark = int(buffer_size * low_watermark)
        self._backpressure_active = False
        self._backpressure_event = Event()
        self._backpressure_event.set()  # 初始状态：允许写入

        # 性能监控
        self._trigger_check_times: deque[float] = deque(maxlen=100)
        self._process_times: deque[float] = deque(maxlen=100)

    def add_trigger(
        self,
        name: str,
        trigger_type: TriggerType,
        condition: Callable[[np.ndarray], bool],
        callback: Callable[[np.ndarray], None],
        check_interval: float = 0.0,
        cache_result: bool = False,
    ) -> None:
        """
        添加触发器。

        创建并注册一个新的触发器，当条件满足时调用回调函数。

        Args:
            name: 触发器名称（唯一标识），用于后续管理和移除
            trigger_type: 触发类型（THRESHOLD/PATTERN/PERIODIC）
            condition: 触发条件函数，接收数据数组，返回布尔值
            callback: 触发回调函数，接收触发时的数据
            check_interval: 检查间隔（秒），0表示每次都检查，默认0
            cache_result: 是否缓存条件结果，默认False

        Raises:
            ValueError: 当触发器名称已存在时抛出异常

        Example:
            >>> processor.add_trigger(
            ...     "peak_detector",
            ...     TriggerType.THRESHOLD,
            ...     lambda d: len(d) > 0 and np.max(d) > 100,
            ...     lambda d: print(f"检测到峰值: {np.max(d)}")
            ... )
        """
        with self._lock:
            if name in self._triggers:
                raise ValueError(f"触发器 '{name}' 已存在")

            self._triggers[name] = TriggerConfig(
                name=name,
                trigger_type=trigger_type,
                condition=condition,
                callback=callback,
                check_interval=check_interval,
                cache_result=cache_result,
            )

    def remove_trigger(self, name: str) -> bool:
        """
        移除触发器。

        根据名称删除已注册的触发器。

        Args:
            name: 触发器名称

        Returns:
            成功移除返回True，触发器不存在返回False
        """
        with self._lock:
            if name in self._triggers:
                del self._triggers[name]
                return True
            return False

    def enable_trigger(self, name: str, enabled: bool = True) -> bool:
        """
        启用或禁用触发器。

        临时禁用触发器而不删除，便于后续重新启用。

        Args:
            name: 触发器名称
            enabled: 是否启用，True启用，False禁用

        Returns:
            操作成功返回True，触发器不存在返回False
        """
        with self._lock:
            if name in self._triggers:
                self._triggers[name].enabled = enabled
                return True
            return False

    def process(self, data: NDArray[np.floating[Any] | np.integer[Any]]) -> dict[str, Any]:
        """
        处理数据并检查触发条件。

        将数据写入缓冲区，并检查所有启用的触发器。
        触发器条件满足时会自动调用对应的回调函数。

        Args:
            data: 输入数据数组

        Returns:
            处理结果字典，包含：
                - written_count: 写入的数据点数
                - triggered: 触发的触发器名称列表
                - buffer_stats: 缓冲区统计信息
                - backpressure_active: 背压是否激活

        Example:
            >>> result = processor.process(np.array([1.0, 2.0, 3.0]))
            >>> print(f"写入: {result['written_count']}, 触发: {result['triggered']}")
        """
        start_time = time.time()

        if data is None or len(data) == 0:
            return {
                "written_count": 0,
                "triggered": [],
                "buffer_stats": self._buffer.get_statistics(),
                "backpressure_active": self._backpressure_active,
            }

        # 背压控制：等待缓冲区水位下降
        if self._backpressure_enabled and self._backpressure_active:
            # 阻塞等待，直到水位降至低水位以下
            self._backpressure_event.wait(timeout=1.0)

        # 写入缓冲区
        written_count = self._buffer.write(data)

        triggered: list[str] = []

        # 检查触发器
        trigger_start = time.time()
        with self._lock:
            # 缓存数据优化：避免多次读取
            current_buffer_count = self._buffer.available
            if (
                self._cached_data is None
                or not self._cache_valid
                or self._last_buffer_count != current_buffer_count
            ):
                self._cached_data = self._buffer.read_all()
                self._cache_valid = True
                self._last_buffer_count = current_buffer_count

            check_data = self._cached_data
            current_time = time.time()

            # 并行或串行检查触发器
            if self._enable_parallel_triggers and len(self._triggers) > 1:
                triggered = self._check_triggers_parallel(check_data, current_time)
            else:
                triggered = self._check_triggers_serial(check_data, current_time)

        # 记录触发器检查时间
        trigger_elapsed = (time.time() - trigger_start) * 1000
        self._trigger_check_times.append(trigger_elapsed)

        # 更新背压状态
        if self._backpressure_enabled:
            self._update_backpressure_state()

        # 更新统计信息
        elapsed_ms = (time.time() - start_time) * 1000
        self._process_times.append(elapsed_ms)
        self._statistics.update_processing_time(elapsed_ms)
        self._statistics.total_data_points += written_count
        self._statistics.total_bytes += written_count * np.dtype(self._buffer._dtype).itemsize
        self._statistics.last_update_time = time.time()
        self._statistics.update_throughput()
        self._statistics.update_memory_usage(self._statistics.total_bytes)

        return {
            "written_count": written_count,
            "triggered": triggered,
            "buffer_stats": self._buffer.get_statistics(),
            "backpressure_active": self._backpressure_active,
        }

    def _check_triggers_serial(self, check_data: np.ndarray, current_time: float) -> list[str]:
        """
        串行检查触发器。

        Args:
            check_data: 待检查的数据
            current_time: 当前时间戳

        Returns:
            触发的触发器名称列表
        """
        triggered: list[str] = []

        for name, trigger in self._triggers.items():
            if not trigger.enabled:
                continue

            try:
                # 检查时间间隔
                if trigger.check_interval > 0:
                    if current_time - trigger.last_check_time < trigger.check_interval:
                        continue

                trigger.last_check_time = current_time

                # 检查缓存结果
                if trigger.cache_result and trigger.last_condition_result:
                    should_trigger = trigger.last_condition_result
                else:
                    should_trigger = trigger.condition(check_data)
                    trigger.last_condition_result = should_trigger

                if should_trigger:
                    trigger.callback(check_data)
                    trigger.trigger_count += 1
                    triggered.append(name)
                    self._statistics.trigger_activations += 1

                    if trigger.cache_result:
                        trigger.last_condition_result = False
            except Exception as e:
                import warnings

                warnings.warn(f"触发器 '{name}' 执行错误: {e}")

        return triggered

    def _check_triggers_parallel(self, check_data: np.ndarray, current_time: float) -> list[str]:
        """
        并行检查触发器。

        使用线程池并行执行触发器检查，提高多触发器场景的性能。

        Args:
            check_data: 待检查的数据
            current_time: 当前时间戳

        Returns:
            触发的触发器名称列表
        """
        import concurrent.futures

        triggered: list[str] = []
        futures: list[tuple[str, concurrent.futures.Future]] = []

        for name, trigger in self._triggers.items():
            if not trigger.enabled:
                continue

            # 检查时间间隔
            if trigger.check_interval > 0:
                if current_time - trigger.last_check_time < trigger.check_interval:
                    continue

            trigger.last_check_time = current_time

            # 提交到线程池
            if self._executor:
                future = self._executor.submit(
                    self._check_single_trigger, name, trigger, check_data
                )
                futures.append((name, future))

        # 收集结果
        for name, future in futures:
            try:
                if future.result(timeout=1.0):  # 1秒超时
                    triggered.append(name)
                    self._statistics.trigger_activations += 1
            except Exception as e:
                import warnings

                warnings.warn(f"触发器 '{name}' 并行检查错误: {e}")

        return triggered

    def _check_single_trigger(
        self, name: str, trigger: TriggerConfig, check_data: np.ndarray
    ) -> bool:
        """
        检查单个触发器（用于并行执行）。

        Args:
            name: 触发器名称
            trigger: 触发器配置
            check_data: 待检查的数据

        Returns:
            是否触发
        """
        try:
            if trigger.cache_result and trigger.last_condition_result:
                should_trigger = trigger.last_condition_result
            else:
                should_trigger = trigger.condition(check_data)
                trigger.last_condition_result = should_trigger

            if should_trigger:
                trigger.callback(check_data)
                trigger.trigger_count += 1

                if trigger.cache_result:
                    trigger.last_condition_result = False

                return True
        except Exception as e:
            import warnings

            warnings.warn(f"触发器 '{name}' 执行错误: {e}")

        return False

    def _update_backpressure_state(self) -> None:
        """
        更新背压状态。

        根据缓冲区水位自动激活或解除背压。
        """
        current_count = self._buffer.available

        if current_count >= self._high_watermark and not self._backpressure_active:
            # 激活背压
            self._backpressure_active = True
            self._backpressure_event.clear()
        elif current_count <= self._low_watermark and self._backpressure_active:
            # 解除背压
            self._backpressure_active = False
            self._backpressure_event.set()

    def get_backpressure_status(self) -> dict[str, Any]:
        """
        获取背压状态信息。

        Returns:
            背压状态字典，包含：
                - enabled: 是否启用背压控制
                - active: 当前是否激活
                - high_watermark: 高水位阈值
                - low_watermark: 低水位阈值
                - current_level: 当前缓冲区水位
        """
        return {
            "enabled": self._backpressure_enabled,
            "active": self._backpressure_active,
            "high_watermark": self._high_watermark,
            "low_watermark": self._low_watermark,
            "current_level": self._buffer.available,
        }

    def get_performance_metrics(self) -> dict[str, Any]:
        """
        获取性能指标。

        Returns:
            性能指标字典，包含：
                - avg_trigger_check_time_ms: 平均触发器检查时间
                - avg_process_time_ms: 平均处理时间
                - trigger_check_p95_ms: 触发器检查P95延迟
                - process_p95_ms: 处理P95延迟
        """

        def get_percentile(data: deque, percentile: float) -> float:
            if not data:
                return 0.0
            return float(np.percentile(list(data), percentile))

        return {
            "avg_trigger_check_time_ms": (
                float(np.mean(list(self._trigger_check_times)))
                if self._trigger_check_times
                else 0.0
            ),
            "avg_process_time_ms": (
                float(np.mean(list(self._process_times))) if self._process_times else 0.0
            ),
            "trigger_check_p95_ms": get_percentile(self._trigger_check_times, 95),
            "process_p95_ms": get_percentile(self._process_times, 95),
        }

    def process_batch(
        self, data_list: list[NDArray[np.floating[Any] | np.integer[Any]]]
    ) -> dict[str, Any]:
        """
        批量处理多个数据数组。

        优化多次小数据处理的性能，通过合并写入和减少锁竞争来提升效率。
        触发器检查只在批量写入完成后执行一次。

        Args:
            data_list: 数据数组列表

        Returns:
            处理结果字典，包含：
                - written_count: 写入的总数据点数
                - triggered: 触发的触发器名称列表（去重）
                - buffer_stats: 缓冲区统计信息

        Example:
            >>> result = processor.process_batch([
            ...     np.array([1.0, 2.0]),
            ...     np.array([3.0, 4.0])
            ... ])
            >>> print(f"总写入: {result['written_count']}")
        """
        if not data_list:
            return {
                "written_count": 0,
                "triggered": [],
                "buffer_stats": self._buffer.get_statistics(),
            }

        start_time = time.time()

        # 批量写入
        written_count = self._buffer.write_batch(data_list)

        # 更新批量统计
        self._statistics.update_batch_size(len(data_list))

        triggered: list[str] = []
        triggered_set: set[str] = set()

        # 检查触发器（只检查一次）
        with self._lock:
            check_data = self._buffer.read_all()
            current_time = time.time()

            for name, trigger in self._triggers.items():
                if not trigger.enabled:
                    continue

                try:
                    # 检查时间间隔
                    if trigger.check_interval > 0:
                        if current_time - trigger.last_check_time < trigger.check_interval:
                            continue

                    trigger.last_check_time = current_time

                    if trigger.condition(check_data):
                        trigger.callback(check_data)
                        trigger.trigger_count += 1
                        triggered_set.add(name)
                        self._statistics.trigger_activations += 1
                except Exception as e:
                    import warnings

                    warnings.warn(f"触发器 '{name}' 执行错误: {e}")

        triggered = list(triggered_set)

        # 更新统计信息
        elapsed_ms = (time.time() - start_time) * 1000
        self._statistics.update_processing_time(elapsed_ms)
        self._statistics.total_data_points += written_count
        self._statistics.total_bytes += written_count * np.dtype(self._buffer._dtype).itemsize
        self._statistics.last_update_time = time.time()
        self._statistics.update_throughput()
        self._statistics.update_memory_usage(self._statistics.total_bytes)

        return {
            "written_count": written_count,
            "triggered": triggered,
            "buffer_stats": self._buffer.get_statistics(),
        }

    def detect_hysteresis_loop(
        self,
        x_data: NDArray[np.floating[Any] | np.integer[Any]],
        y_data: NDArray[np.floating[Any] | np.integer[Any]],
        threshold: float = 0.1,
    ) -> bool:
        """
        检测磁滞回线完成。

        通过监测数据的方向变化和峰值穿越来判断磁滞回线是否完成一个周期。
        适用于磁性材料测量等场景。

        Args:
            x_data: X轴数据（如磁场强度）
            y_data: Y轴数据（如磁矩）
            threshold: 变化阈值，用于判断方向变化，默认0.1

        Returns:
            是否检测到完整的磁滞回线周期

        Note:
            判断条件：
            1. X方向至少变化2次（正向和负向扫描）
            2. Y值至少穿越零点2次
            3. 数据量至少10个点

        Example:
            >>> x = np.linspace(-1, 1, 100)
            >>> y = np.sin(x * np.pi)
            >>> is_complete = processor.detect_hysteresis_loop(x, y)
        """
        if len(x_data) < 3 or len(y_data) < 3:
            return False

        # 计算数据变化方向
        x_diff = np.diff(x_data)
        y_diff = np.diff(y_data)

        # 检测X方向变化（磁场扫描方向）
        if len(x_diff) == 0:
            return False

        # 判断当前扫描方向
        current_direction = 1 if x_diff[-1] > 0 else -1

        # 检测方向变化次数
        direction_changes = 0
        prev_direction = 0

        for diff in x_diff:
            if diff > threshold:
                new_direction = 1
            elif diff < -threshold:
                new_direction = -1
            else:
                continue

            if prev_direction != 0 and new_direction != prev_direction:
                direction_changes += 1
            prev_direction = new_direction

        # 检测Y值穿越零点的次数
        zero_crossings = np.sum(np.diff(np.sign(y_data)) != 0)

        # 判断条件：
        # 1. X方向至少变化2次（正向和负向扫描）
        # 2. Y值至少穿越零点2次
        # 3. 数据量足够
        is_complete = direction_changes >= 2 and zero_crossings >= 2 and len(x_data) >= 10

        return is_complete

    def detect_peak(
        self, data: NDArray[np.floating[Any] | np.integer[Any]], threshold: float | None = None
    ) -> dict[str, Any]:
        """
        检测数据峰值。

        使用局部最大值检测算法识别数据中的峰值点。

        Args:
            data: 输入数据数组
            threshold: 峰值阈值，默认为数据标准差的2倍

        Returns:
            峰值检测结果字典，包含：
                - peak_indices: 峰值索引列表
                - peak_values: 峰值列表
                - peak_count: 峰值数量

        Example:
            >>> data = np.array([1.0, 5.0, 2.0, 8.0, 3.0])
            >>> result = processor.detect_peak(data)
            >>> print(f"检测到 {result['peak_count']} 个峰值")
        """
        if data is None or len(data) < 3:
            return {"peak_indices": [], "peak_values": [], "peak_count": 0}

        if threshold is None:
            threshold = 2 * np.std(data)

        # 使用简单的局部最大值检测
        peak_indices = []
        peak_values = []

        for i in range(1, len(data) - 1):
            if data[i] > data[i - 1] and data[i] > data[i + 1]:
                if data[i] > threshold:
                    peak_indices.append(i)
                    peak_values.append(float(data[i]))

        return {
            "peak_indices": peak_indices,
            "peak_values": peak_values,
            "peak_count": len(peak_indices),
        }

    def get_buffer_data(self) -> NDArray[np.floating[Any] | np.integer[Any]]:
        """
        获取缓冲区中的所有数据。

        Returns:
            缓冲区数据数组（副本）
        """
        return self._buffer.read_all()

    def clear_buffer(self) -> None:
        """
        清空缓冲区。

        重置缓冲区状态，清除所有数据。
        """
        self._buffer.clear()

    def get_statistics(self) -> dict[str, Any]:
        """
        获取处理器统计信息。

        Returns:
            统计信息字典，包含：
                - total_data_points: 总数据点数
                - total_bytes: 总字节数
                - trigger_activations: 触发器激活次数
                - avg_processing_time_ms: 平均处理时间
                - last_update_time: 最后更新时间
                - buffer_stats: 缓冲区统计
                - trigger_count: 触发器数量
        """
        return {
            "total_data_points": self._statistics.total_data_points,
            "total_bytes": self._statistics.total_bytes,
            "trigger_activations": self._statistics.trigger_activations,
            "avg_processing_time_ms": self._statistics.avg_processing_time_ms,
            "last_update_time": self._statistics.last_update_time,
            "buffer_stats": self._buffer.get_statistics(),
            "trigger_count": len(self._triggers),
            # 新增性能指标
            "throughput_points_per_sec": self._statistics.throughput_points_per_sec,
            "peak_memory_usage_mb": self._statistics.peak_memory_usage_mb,
            "batch_count": self._statistics.batch_count,
            "avg_batch_size": self._statistics.avg_batch_size,
            "latency_distribution": self._statistics.get_latency_distribution(),
        }


class DataPipeline:
    """
    数据管道，整合缓冲区和处理器。

    提供完整的流式数据处理管道，支持异步数据消费、
    触发器管理和分析回调。是多通道数据流处理的核心组件。

    核心功能：
    - 异步数据消费（支持硬件数据流）
    - 多通道数据管理
    - 触发器机制
    - 分析回调注册
    - 性能统计

    Attributes:
        buffer_size: 缓冲区大小
        _processor: 流式数据处理器
        _analysis_callbacks: 分析回调列表
        _channel_buffers: 多通道缓冲区字典
        _statistics: 管道统计信息
        _is_running: 运行状态标志

    Example:
        >>> pipeline = DataPipeline(buffer_size=10000)
        >>>
        >>> # 注册分析回调
        >>> def my_callback(data):
        ...     print(f"收到数据: {data['channel']}")
        >>> pipeline.register_analysis_callback(my_callback)
        >>>
        >>> # 添加触发器
        >>> pipeline.add_trigger(
        ...     "threshold",
        ...     TriggerType.THRESHOLD,
        ...     lambda d: len(d) > 0 and d[-1] > 100,
        ...     lambda d: print("超过阈值！")
        ... )
        >>>
        >>> # 启动管道
        >>> pipeline.start()
    """

    def __init__(self, buffer_size: int = 10000) -> None:
        """
        初始化数据管道。

        Args:
            buffer_size: 缓冲区大小，默认10000
        """
        self._processor = StreamProcessor(buffer_size=buffer_size)
        self._analysis_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._lock = RLock()
        self._statistics = PipelineStatistics()
        self._is_running = False

        # 数据缓存（用于多通道数据）
        self._channel_buffers: dict[str, RingBuffer] = {}
        self._channel_lock = Lock()

    async def consume_hardware_stream(self, data: dict[str, Any]) -> None:
        """
        消费硬件数据流。

        异步处理来自硬件的数据流，支持多通道数据。
        数据将被写入缓冲区、检查触发器并调用分析回调。

        Args:
            data: 数据字典，包含：
                - channel: 通道名称（可选，默认"default"）
                - values: 数据值数组（必需）
                - timestamp: 时间戳（可选）
                - metadata: 元数据（可选）

        Example:
            >>> await pipeline.consume_hardware_stream({
            ...     "channel": "sensor_1",
            ...     "values": np.array([1.0, 2.0, 3.0]),
            ...     "timestamp": time.time()
            ... })
        """
        start_time = time.time()

        if not data:
            return

        channel = data.get("channel", "default")
        values = data.get("values")

        if values is None:
            return

        # 转换为numpy数组
        if not isinstance(values, np.ndarray):
            values = np.array(values, dtype=np.float64)

        # 处理主数据流
        result = self._processor.process(values)

        # 处理多通道数据
        with self._channel_lock:
            if channel not in self._channel_buffers:
                self._channel_buffers[channel] = RingBuffer(size=10000)
            self._channel_buffers[channel].write(values)

        # 调用分析回调
        analysis_data = {
            "channel": channel,
            "values": values,
            "timestamp": data.get("timestamp", time.time()),
            "metadata": data.get("metadata", {}),
            "processing_result": result,
        }

        with self._lock:
            for callback in self._analysis_callbacks:
                try:
                    callback(analysis_data)
                except Exception as e:
                    import warnings

                    warnings.warn(f"分析回调执行错误: {e}")

        # 更新统计信息
        elapsed_ms = (time.time() - start_time) * 1000
        self._statistics.update_processing_time(elapsed_ms)
        self._statistics.total_data_points += len(values)
        self._statistics.last_update_time = time.time()
        self._statistics.update_throughput()
        self._statistics.update_memory_usage(self._statistics.total_bytes)

    async def consume_hardware_stream_batch(self, data_list: list[dict[str, Any]]) -> None:
        """
        批量消费硬件数据流。

        优化多次小数据处理的性能，通过合并处理减少开销。
        数据按通道分组后批量处理。

        Args:
            data_list: 数据字典列表，每个字典格式同consume_hardware_stream

        Example:
            >>> await pipeline.consume_hardware_stream_batch([
            ...     {"channel": "sensor_1", "values": np.array([1.0, 2.0])},
            ...     {"channel": "sensor_2", "values": np.array([3.0, 4.0])}
            ... ])
        """
        if not data_list:
            return

        start_time = time.time()

        # 按通道分组数据
        channel_data: dict[str, list[np.ndarray]] = {}
        all_values: list[np.ndarray] = []

        for data in data_list:
            if not data:
                continue

            channel = data.get("channel", "default")
            values = data.get("values")

            if values is None:
                continue

            # 转换为numpy数组
            if not isinstance(values, np.ndarray):
                values = np.array(values, dtype=np.float64)

            all_values.append(values)

            if channel not in channel_data:
                channel_data[channel] = []
            channel_data[channel].append(values)

        # 批量处理主数据流
        if all_values:
            result = self._processor.process_batch(all_values)
            self._statistics.update_batch_size(len(all_values))

        # 批量处理多通道数据
        with self._channel_lock:
            for channel, values_list in channel_data.items():
                if channel not in self._channel_buffers:
                    self._channel_buffers[channel] = RingBuffer(size=10000)
                self._channel_buffers[channel].write_batch(values_list)

        # 更新统计信息
        elapsed_ms = (time.time() - start_time) * 1000
        total_points = sum(len(v) for v in all_values)
        self._statistics.update_processing_time(elapsed_ms)
        self._statistics.total_data_points += total_points
        self._statistics.last_update_time = time.time()
        self._statistics.update_throughput()
        self._statistics.update_memory_usage(self._statistics.total_bytes)

    def register_analysis_callback(self, callback: Callable[[dict[str, Any]], None]) -> None:
        """
        注册分析回调函数。

        回调函数将在每次数据处理完成后被调用，可用于实时分析。

        Args:
            callback: 回调函数，接收分析数据字典，包含：
                - channel: 通道名称
                - values: 数据值
                - timestamp: 时间戳
                - metadata: 元数据
                - processing_result: 处理结果

        Example:
            >>> def my_analyzer(data):
            ...     print(f"通道 {data['channel']}: {len(data['values'])} 个数据点")
            >>> pipeline.register_analysis_callback(my_analyzer)
        """
        with self._lock:
            if callback not in self._analysis_callbacks:
                self._analysis_callbacks.append(callback)

    def unregister_analysis_callback(self, callback: Callable[[dict[str, Any]], None]) -> bool:
        """
        注销分析回调函数。

        Args:
            callback: 要注销的回调函数

        Returns:
            成功注销返回True，回调不存在返回False
        """
        with self._lock:
            if callback in self._analysis_callbacks:
                self._analysis_callbacks.remove(callback)
                return True
            return False

    def add_trigger(
        self,
        name: str,
        trigger_type: TriggerType,
        condition: Callable[[np.ndarray], bool],
        callback: Callable[[np.ndarray], None],
        check_interval: float = 0.0,
        cache_result: bool = False,
    ) -> None:
        """
        添加触发器。

        委托给内部StreamProcessor处理。

        Args:
            name: 触发器名称
            trigger_type: 触发类型
            condition: 触发条件函数
            callback: 触发回调函数
            check_interval: 检查间隔（秒），0表示每次都检查
            cache_result: 是否缓存条件结果
        """
        self._processor.add_trigger(
            name, trigger_type, condition, callback, check_interval, cache_result
        )

    def remove_trigger(self, name: str) -> bool:
        """
        移除触发器。

        Args:
            name: 触发器名称

        Returns:
            成功移除返回True，触发器不存在返回False
        """
        return self._processor.remove_trigger(name)

    def get_channel_data(
        self, channel: str = "default"
    ) -> NDArray[np.floating[Any] | np.integer[Any]]:
        """
        获取指定通道的数据。

        Args:
            channel: 通道名称，默认"default"

        Returns:
            通道数据数组，通道不存在时返回空数组
        """
        with self._channel_lock:
            if channel in self._channel_buffers:
                return self._channel_buffers[channel].read_all()
            return np.array([], dtype=np.float64)

    def get_all_channels(self) -> list[str]:
        """
        获取所有通道名称。

        Returns:
            通道名称列表
        """
        with self._channel_lock:
            return list(self._channel_buffers.keys())

    def clear_channel(self, channel: str = "default") -> bool:
        """
        清空指定通道数据。

        Args:
            channel: 通道名称

        Returns:
            成功清空返回True，通道不存在返回False
        """
        with self._channel_lock:
            if channel in self._channel_buffers:
                self._channel_buffers[channel].clear()
                return True
            return False

    def clear_all_channels(self) -> None:
        """
        清空所有通道数据。

        保留通道结构，仅清除数据。
        """
        with self._channel_lock:
            for buffer in self._channel_buffers.values():
                buffer.clear()

    def get_statistics(self) -> dict[str, Any]:
        """
        获取管道统计信息。

        Returns:
            统计信息字典，包含：
                - total_data_points: 总数据点数
                - total_bytes: 总字节数
                - avg_processing_time_ms: 平均处理时间
                - last_update_time: 最后更新时间
                - channel_count: 通道数量
                - channels: 各通道统计信息
                - throughput_points_per_sec: 吞吐量（点/秒）
                - peak_memory_usage_mb: 峰值内存使用（MB）
                - batch_count: 批量处理次数
                - avg_batch_size: 平均批量大小
                - latency_distribution: 延迟分布
        """
        channel_stats = {}
        with self._channel_lock:
            for name, buffer in self._channel_buffers.items():
                channel_stats[name] = buffer.get_statistics()

        return {
            "total_data_points": self._statistics.total_data_points,
            "total_bytes": self._statistics.total_bytes,
            "avg_processing_time_ms": self._statistics.avg_processing_time_ms,
            "last_update_time": self._statistics.last_update_time,
            "channel_count": len(self._channel_buffers),
            "channels": channel_stats,
            "processor_stats": self._processor.get_statistics(),
            # 新增性能指标
            "throughput_points_per_sec": self._statistics.throughput_points_per_sec,
            "peak_memory_usage_mb": self._statistics.peak_memory_usage_mb,
            "batch_count": self._statistics.batch_count,
            "avg_batch_size": self._statistics.avg_batch_size,
            "latency_distribution": self._statistics.get_latency_distribution(),
        }

    def start(self) -> None:
        """
        启动数据管道。

        设置运行状态标志，允许数据处理。
        """
        self._is_running = True

    def stop(self) -> None:
        """
        停止数据管道。

        清除运行状态标志，停止数据处理。
        """
        self._is_running = False

    @property
    def is_running(self) -> bool:
        """
        返回管道是否正在运行。

        Returns:
            运行中返回True，否则返回False
        """
        return self._is_running

    def reset(self) -> None:
        """
        重置管道状态。

        清空所有缓冲区和统计信息，恢复到初始状态。
        """
        self._processor.clear_buffer()
        self.clear_all_channels()
        self._statistics = PipelineStatistics()


# ==================== 便捷函数 ====================


def create_threshold_trigger(
    threshold: float,
    callback: Callable[[np.ndarray], None],
    comparison: str = "greater",
) -> tuple[TriggerType, Callable[[np.ndarray], bool], Callable[[np.ndarray], None]]:
    """
    创建阈值触发器的便捷函数。

    快速创建一个基于阈值的触发器配置。

    Args:
        threshold: 阈值
        callback: 触发回调函数
        comparison: 比较方式，可选：
            - "greater": 大于阈值触发（默认）
            - "less": 小于阈值触发
            - "equal": 等于阈值触发

    Returns:
        元组：(触发类型, 条件函数, 回调函数)

    Example:
        >>> trigger_type, condition, callback = create_threshold_trigger(
        ...     threshold=100.0,
        ...     callback=lambda d: print("超过100！"),
        ...     comparison="greater"
        ... )
        >>> processor.add_trigger("high_value", trigger_type, condition, callback)
    """

    def condition(data: np.ndarray) -> bool:
        if len(data) == 0:
            return False
        latest = data[-1]
        if comparison == "greater":
            return latest > threshold
        elif comparison == "less":
            return latest < threshold
        else:
            return abs(latest - threshold) < 1e-6

    return TriggerType.THRESHOLD, condition, callback


def create_pattern_trigger(
    pattern: np.ndarray,
    callback: Callable[[np.ndarray], None],
    tolerance: float = 0.1,
) -> tuple[TriggerType, Callable[[np.ndarray], bool], Callable[[np.ndarray], None]]:
    """创建模式触发器的便捷函数。

    Args:
        pattern: 目标模式数组
        callback: 触发回调函数
        tolerance: 匹配容差

    Returns:
        元组：(触发类型, 条件函数, 回调函数)
    """

    def condition(data: np.ndarray) -> bool:
        if len(data) < len(pattern):
            return False
        latest = data[-len(pattern) :]
        # 使用归一化相关系数进行模式匹配
        if np.std(latest) == 0 or np.std(pattern) == 0:
            return False
        correlation = np.corrcoef(latest, pattern)[0, 1]
        return correlation > (1 - tolerance)

    return TriggerType.PATTERN, condition, callback


def create_periodic_trigger(
    interval_points: int,
    callback: Callable[[np.ndarray], None],
) -> tuple[TriggerType, Callable[[np.ndarray], bool], Callable[[np.ndarray], None]]:
    """创建周期触发器的便捷函数。

    Args:
        interval_points: 触发间隔（数据点数）
        callback: 触发回调函数

    Returns:
        元组：(触发类型, 条件函数, 回调函数)
    """
    counter = [0]  # 使用列表存储可变计数器

    def condition(data: np.ndarray) -> bool:
        counter[0] += 1
        if counter[0] >= interval_points:
            counter[0] = 0
            return True
        return False

    return TriggerType.PERIODIC, condition, callback
