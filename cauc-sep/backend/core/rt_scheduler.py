"""
文件名: rt_scheduler.py
路径: backend/core/
功能: Windows高精度定时器和实时调度功能实现
作者: Backend Engineer Agent
创建日期: 2024-03-07
更新日期: 2024-03-08
依赖: ctypes, logging
平台: Windows only

性能优化与稳定性增强:
- 添加调度器性能监控（执行时间统计、精度偏差监控）
- 完善异常处理和资源释放
- 实现优雅退出机制
- 添加性能报告生成功能
"""

from __future__ import annotations

import ctypes
import ctypes.wintypes as wintypes
import logging
import threading
import time
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from types import TracebackType
from typing import Any, Optional

# 配置日志
logger = logging.getLogger(__name__)

# Windows API 常量定义
# 线程优先级常量
THREAD_PRIORITY_IDLE = -15
THREAD_PRIORITY_LOWEST = -2
THREAD_PRIORITY_BELOW_NORMAL = -1
THREAD_PRIORITY_NORMAL = 0
THREAD_PRIORITY_ABOVE_NORMAL = 1
THREAD_PRIORITY_HIGHEST = 2
THREAD_PRIORITY_TIME_CRITICAL = 15

# 进程优先级类常量
PROCESS_PRIORITY_CLASS_NORMAL = 0x20
PROCESS_PRIORITY_CLASS_HIGH = 0x80
PROCESS_PRIORITY_CLASS_REALTIME = 0x100


@dataclass
class SchedulerPerformanceMetrics:
    """
    调度器性能指标数据类。

    记录调度器的各项性能指标，用于监控和优化。

    Attributes:
        total_executions: 总执行次数
        total_execution_time_ms: 总执行时间（毫秒）
        avg_execution_time_ms: 平均执行时间（毫秒）
        max_execution_time_ms: 最大执行时间（毫秒）
        min_execution_time_ms: 最小执行时间（毫秒）
        precision_errors: 精度偏差列表（毫秒）
        avg_precision_error_ms: 平均精度偏差（毫秒）
        max_precision_error_ms: 最大精度偏差（毫秒）
        missed_deadlines: 错过截止时间次数
        context_switches: 上下文切换次数
    """

    total_executions: int = 0
    total_execution_time_ms: float = 0.0
    avg_execution_time_ms: float = 0.0
    max_execution_time_ms: float = 0.0
    min_execution_time_ms: float = float("inf")
    _execution_times: deque = field(default_factory=lambda: deque(maxlen=1000))
    precision_errors: deque = field(default_factory=lambda: deque(maxlen=1000))
    avg_precision_error_ms: float = 0.0
    max_precision_error_ms: float = 0.0
    missed_deadlines: int = 0
    context_switches: int = 0
    _start_time: float = field(default_factory=time.time)

    def update_execution_time(self, elapsed_ms: float) -> None:
        """
        更新执行时间统计。

        Args:
            elapsed_ms: 本次执行耗时（毫秒）
        """
        self.total_executions += 1
        self.total_execution_time_ms += elapsed_ms
        self._execution_times.append(elapsed_ms)

        self.max_execution_time_ms = max(self.max_execution_time_ms, elapsed_ms)
        self.min_execution_time_ms = min(self.min_execution_time_ms, elapsed_ms)
        self.avg_execution_time_ms = self.total_execution_time_ms / self.total_executions

    def update_precision_error(self, error_ms: float) -> None:
        """
        更新精度偏差统计。

        Args:
            error_ms: 精度偏差（毫秒）
        """
        self.precision_errors.append(abs(error_ms))
        self.max_precision_error_ms = max(self.max_precision_error_ms, abs(error_ms))
        if self.precision_errors:
            self.avg_precision_error_ms = sum(self.precision_errors) / len(self.precision_errors)

    def get_percentile_latency(self, percentile: float = 95.0) -> float:
        """
        获取指定百分位的延迟。

        Args:
            percentile: 百分位（0-100），默认95

        Returns:
            指定百分位的延迟（毫秒）
        """
        if not self._execution_times:
            return 0.0
        import numpy as np

        return float(np.percentile(list(self._execution_times), percentile))

    def get_report(self) -> dict[str, Any]:
        """
        生成性能报告。

        Returns:
            性能报告字典
        """
        import numpy as np

        uptime_seconds = time.time() - self._start_time

        return {
            "uptime_seconds": uptime_seconds,
            "total_executions": self.total_executions,
            "executions_per_second": (
                self.total_executions / uptime_seconds if uptime_seconds > 0 else 0
            ),
            "execution_time": {
                "avg_ms": round(self.avg_execution_time_ms, 3),
                "max_ms": round(self.max_execution_time_ms, 3),
                "min_ms": (
                    round(self.min_execution_time_ms, 3)
                    if self.min_execution_time_ms != float("inf")
                    else 0
                ),
                "p50_ms": round(self.get_percentile_latency(50), 3),
                "p95_ms": round(self.get_percentile_latency(95), 3),
                "p99_ms": round(self.get_percentile_latency(99), 3),
            },
            "precision": {
                "avg_error_ms": round(self.avg_precision_error_ms, 3),
                "max_error_ms": round(self.max_precision_error_ms, 3),
                "error_count": len(self.precision_errors),
            },
            "reliability": {
                "missed_deadlines": self.missed_deadlines,
                "miss_rate": (
                    self.missed_deadlines / self.total_executions
                    if self.total_executions > 0
                    else 0
                ),
                "context_switches": self.context_switches,
            },
        }


class WindowsAPIError(Exception):
    """
    Windows API调用异常。

    当Windows API调用失败时抛出此异常。

    Attributes:
        message: 错误信息描述

    Example:
        >>> raise WindowsAPIError("无法加载winmm.dll")
    """

    def __init__(self, message: str) -> None:
        """
        初始化异常。

        Args:
            message: 错误信息描述
        """
        super().__init__(message)
        self.message = message


class WinMMWrapper:
    """
    Windows多媒体定时器API封装。

    通过winmm.dll实现毫秒级精度的定时器控制。
    提供系统定时器精度的设置和查询功能。

    Attributes:
        _winmm: winmm.dll库句柄
        _TIMECAPS: TIMECAPS结构体类型
        _initialized: 初始化状态标志

    Example:
        >>> winmm = WinMMWrapper()
        >>> winmm.time_begin_period(1)  # 设置1ms精度
        True
        >>> winmm.get_min_resolution()
        1
        >>> winmm.time_end_period(1)  # 恢复默认精度
        True
    """

    def __init__(self) -> None:
        """
        初始化winmm.dll库。

        加载winmm.dll并设置函数签名，包括：
        - timeBeginPeriod: 设置定时器精度
        - timeEndPeriod: 恢复定时器精度
        - timeGetDevCaps: 获取定时器能力

        Raises:
            WindowsAPIError: 无法加载winmm.dll时抛出
        """
        try:
            self._winmm = ctypes.windll.winmm
            # 设置函数签名
            self._winmm.timeBeginPeriod.argtypes = [wintypes.UINT]
            self._winmm.timeBeginPeriod.restype = wintypes.UINT

            self._winmm.timeEndPeriod.argtypes = [wintypes.UINT]
            self._winmm.timeEndPeriod.restype = wintypes.UINT

            # TIMECAPS结构体定义（正确版本）
            class TIMECAPS(ctypes.Structure):
                _fields_ = [
                    ("wPeriodMin", wintypes.UINT),
                    ("wPeriodMax", wintypes.UINT),
                ]

            self._TIMECAPS = TIMECAPS
            self._winmm.timeGetDevCaps.argtypes = [ctypes.POINTER(TIMECAPS), wintypes.UINT]
            self._winmm.timeGetDevCaps.restype = wintypes.UINT

            self._initialized = True
            logger.debug("WinMM库初始化成功")
        except Exception as e:
            self._initialized = False
            logger.error(f"WinMM库初始化失败: {e}")
            raise WindowsAPIError(f"无法加载winmm.dll: {e}")

    def time_begin_period(self, period_ms: int) -> bool:
        """
        设置系统定时器精度。

        Args:
            period_ms: 请求的定时器精度（毫秒），通常为1-5ms

        Returns:
            bool: 设置成功返回True

        Raises:
            WindowsAPIError: API调用失败时抛出
        """
        if not self._initialized:
            raise WindowsAPIError("WinMM库未初始化")

        result = self._winmm.timeBeginPeriod(wintypes.UINT(period_ms))
        if result != 0:
            logger.warning(f"timeBeginPeriod({period_ms})返回错误码: {result}")
            return False

        logger.debug(f"系统定时器精度设置为 {period_ms}ms")
        return True

    def time_end_period(self, period_ms: int) -> bool:
        """
        恢复系统定时器精度。

        Args:
            period_ms: 之前设置的定时器精度（毫秒）

        Returns:
            bool: 恢复成功返回True
        """
        if not self._initialized:
            return True

        result = self._winmm.timeEndPeriod(wintypes.UINT(period_ms))
        if result != 0:
            logger.warning(f"timeEndPeriod({period_ms})返回错误码: {result}")
            return False

        logger.debug(f"系统定时器精度已恢复")
        return True

    def get_min_resolution(self) -> int:
        """
        获取系统支持的最小定时器精度。

        Returns:
            最小精度（毫秒），失败返回1
        """
        # 使用初始化时定义的TIMECAPS结构体
        caps = self._TIMECAPS()
        result = self._winmm.timeGetDevCaps(ctypes.byref(caps), wintypes.UINT(ctypes.sizeof(caps)))

        if result != 0:
            logger.warning("获取定时器能力失败，使用默认值1ms")
            return 1

        logger.debug(f"定时器精度范围: {caps.wPeriodMin}-{caps.wPeriodMax}ms")
        return int(caps.wPeriodMin)


class ThreadPriorityManager:
    """
    线程优先级管理器。

    提供线程优先级和进程优先级的设置功能。
    通过kernel32.dll实现对Windows调度器的控制。

    Attributes:
        _kernel32: kernel32.dll库句柄
        _initialized: 初始化状态标志

    Example:
        >>> manager = ThreadPriorityManager()
        >>> manager.set_thread_priority(THREAD_PRIORITY_HIGHEST)
        True
        >>> manager.get_thread_priority()
        2
    """

    def __init__(self) -> None:
        """
        初始化Windows API。

        加载kernel32.dll并设置函数签名，包括：
        - GetCurrentThread/GetCurrentProcess: 获取句柄
        - SetThreadPriority/GetThreadPriority: 线程优先级操作
        - SetPriorityClass/GetPriorityClass: 进程优先级操作

        Raises:
            WindowsAPIError: 无法加载kernel32.dll时抛出
        """
        try:
            self._kernel32 = ctypes.windll.kernel32

            # 设置函数签名
            self._kernel32.GetCurrentThread.restype = wintypes.HANDLE
            self._kernel32.GetCurrentProcess.restype = wintypes.HANDLE

            self._kernel32.SetThreadPriority.argtypes = [wintypes.HANDLE, wintypes.INT]
            self._kernel32.SetThreadPriority.restype = wintypes.BOOL

            self._kernel32.GetThreadPriority.argtypes = [wintypes.HANDLE]
            self._kernel32.GetThreadPriority.restype = wintypes.INT

            self._kernel32.SetPriorityClass.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            self._kernel32.SetPriorityClass.restype = wintypes.BOOL

            self._kernel32.GetPriorityClass.argtypes = [wintypes.HANDLE]
            self._kernel32.GetPriorityClass.restype = wintypes.DWORD

            self._initialized = True
            logger.debug("Kernel32库初始化成功")
        except Exception as e:
            self._initialized = False
            logger.error(f"Kernel32库初始化失败: {e}")
            raise WindowsAPIError(f"无法加载kernel32.dll: {e}")

    def set_thread_priority(self, priority: int) -> bool:
        """
        设置当前线程优先级。

        Args:
            priority: 优先级值，推荐使用以下常量：
                - THREAD_PRIORITY_IDLE (-15): 空闲优先级
                - THREAD_PRIORITY_LOWEST (-2): 最低优先级
                - THREAD_PRIORITY_BELOW_NORMAL (-1): 低于正常
                - THREAD_PRIORITY_NORMAL (0): 正常优先级
                - THREAD_PRIORITY_ABOVE_NORMAL (1): 高于正常
                - THREAD_PRIORITY_HIGHEST (2): 最高优先级
                - THREAD_PRIORITY_TIME_CRITICAL (15): 实时优先级

        Returns:
            设置成功返回True，失败返回False

        Raises:
            WindowsAPIError: Kernel32库未初始化时抛出

        Example:
            >>> manager.set_thread_priority(THREAD_PRIORITY_HIGHEST)
            True
        """
        if not self._initialized:
            raise WindowsAPIError("Kernel32库未初始化")

        thread_handle = self._kernel32.GetCurrentThread()
        result = self._kernel32.SetThreadPriority(thread_handle, priority)

        if not result:
            error = ctypes.get_last_error()
            logger.error(f"设置线程优先级失败，错误码: {error}")
            return False

        logger.debug(f"线程优先级设置为: {priority}")
        return True

    def get_thread_priority(self) -> int:
        """
        获取当前线程优先级。

        Returns:
            当前线程优先级值，未初始化时返回THREAD_PRIORITY_NORMAL

        Example:
            >>> priority = manager.get_thread_priority()
            >>> print(f"当前优先级: {priority}")
        """
        if not self._initialized:
            return THREAD_PRIORITY_NORMAL

        thread_handle = self._kernel32.GetCurrentThread()
        return int(self._kernel32.GetThreadPriority(thread_handle))

    def set_process_priority_class(self, priority_class: int) -> bool:
        """
        设置进程优先级类。

        Args:
            priority_class: 优先级类，推荐使用以下常量：
                - PROCESS_PRIORITY_CLASS_NORMAL (0x20): 正常优先级
                - PROCESS_PRIORITY_CLASS_HIGH (0x80): 高优先级
                - PROCESS_PRIORITY_CLASS_REALTIME (0x100): 实时优先级

        Returns:
            设置成功返回True，失败返回False

        Raises:
            WindowsAPIError: Kernel32库未初始化时抛出

        Warning:
            设置实时优先级可能导致系统不稳定，需要管理员权限

        Example:
            >>> manager.set_process_priority_class(PROCESS_PRIORITY_CLASS_HIGH)
            True
        """
        if not self._initialized:
            raise WindowsAPIError("Kernel32库未初始化")

        process_handle = self._kernel32.GetCurrentProcess()
        result = self._kernel32.SetPriorityClass(process_handle, priority_class)

        if not result:
            error = ctypes.get_last_error()
            logger.error(f"设置进程优先级失败，错误码: {error}")
            return False

        logger.debug(f"进程优先级类设置为: {priority_class}")
        return True

    def get_process_priority_class(self) -> int:
        """
        获取当前进程优先级类。

        Returns:
            当前进程优先级类值，未初始化时返回PROCESS_PRIORITY_CLASS_NORMAL

        Example:
            >>> priority_class = manager.get_process_priority_class()
            >>> print(f"当前进程优先级类: 0x{priority_class:X}")
        """
        if not self._initialized:
            return PROCESS_PRIORITY_CLASS_NORMAL

        process_handle = self._kernel32.GetCurrentProcess()
        return int(self._kernel32.GetPriorityClass(process_handle))


class CPUAffinityManager:
    """
    CPU亲和性管理器。

    提供线程绑定到指定CPU核心的功能。
    通过设置CPU亲和性掩码，可以将线程限制在特定核心上运行，
    从而减少缓存失效和核心切换开销。

    Attributes:
        _kernel32: kernel32.dll库句柄
        _SYSTEM_INFO: SYSTEM_INFO结构体类型
        _initialized: 初始化状态标志

    Example:
        >>> manager = CPUAffinityManager()
        >>> manager.get_cpu_count()
        8
        >>> manager.set_thread_affinity([0, 1])  # 绑定到核心0和1
        True
        >>> manager.get_available_cores()
        [0, 1, 2, 3, 4, 5, 6, 7]
    """

    def __init__(self) -> None:
        """
        初始化Windows API。

        加载kernel32.dll并设置函数签名，包括：
        - GetProcessAffinityMask: 获取进程亲和性掩码
        - SetThreadAffinityMask: 设置线程亲和性掩码
        - GetSystemInfo: 获取系统信息

        Raises:
            WindowsAPIError: 无法初始化CPU亲和性API时抛出
        """
        try:
            self._kernel32 = ctypes.windll.kernel32

            # 设置函数签名
            self._kernel32.GetCurrentProcess.restype = wintypes.HANDLE
            self._kernel32.GetCurrentThread.restype = wintypes.HANDLE

            self._kernel32.GetProcessAffinityMask.argtypes = [
                wintypes.HANDLE,
                ctypes.POINTER(wintypes.DWORD),
                ctypes.POINTER(wintypes.DWORD),
            ]
            self._kernel32.GetProcessAffinityMask.restype = wintypes.BOOL

            self._kernel32.SetThreadAffinityMask.argtypes = [wintypes.HANDLE, wintypes.DWORD]
            self._kernel32.SetThreadAffinityMask.restype = wintypes.DWORD

            # 定义正确的SYSTEM_INFO结构体（兼容32位和64位）
            # 在64位系统上，DWORD_PTR是8字节，在32位系统上是4字节
            DWORD_PTR = ctypes.c_size_t  # 自动适配平台位数

            class SYSTEM_INFO(ctypes.Structure):
                _fields_ = [
                    ("wProcessorArchitecture", wintypes.WORD),
                    ("wReserved", wintypes.WORD),
                    ("dwPageSize", wintypes.DWORD),
                    ("lpMinimumApplicationAddress", DWORD_PTR),
                    ("lpMaximumApplicationAddress", DWORD_PTR),
                    ("dwActiveProcessorMask", DWORD_PTR),
                    ("dwNumberOfProcessors", wintypes.DWORD),
                    ("dwProcessorType", wintypes.DWORD),
                    ("dwAllocationGranularity", wintypes.DWORD),
                    ("wProcessorLevel", wintypes.WORD),
                    ("wProcessorRevision", wintypes.WORD),
                ]

            self._SYSTEM_INFO = SYSTEM_INFO

            self._kernel32.GetSystemInfo.restype = None
            self._kernel32.GetSystemInfo.argtypes = [ctypes.POINTER(SYSTEM_INFO)]

            self._initialized = True
            logger.debug("CPU亲和性管理器初始化成功")
        except Exception as e:
            self._initialized = False
            logger.error(f"CPU亲和性管理器初始化失败: {e}")
            raise WindowsAPIError(f"无法初始化CPU亲和性API: {e}")

    def get_cpu_count(self) -> int:
        """
        获取系统CPU核心数量。

        Returns:
            系统逻辑CPU核心数（包含超线程核心）

        Example:
            >>> count = manager.get_cpu_count()
            >>> print(f"系统有 {count} 个逻辑核心")
        """
        # 使用初始化时定义的SYSTEM_INFO结构体
        sys_info = self._SYSTEM_INFO()
        self._kernel32.GetSystemInfo(ctypes.byref(sys_info))

        cpu_count = sys_info.dwNumberOfProcessors
        logger.debug(f"系统CPU核心数: {cpu_count}")
        return int(cpu_count)

    def set_thread_affinity(self, core_ids: list[int]) -> bool:
        """
        将当前线程绑定到指定CPU核心。

        通过设置亲和性掩码，限制线程只能在指定核心上运行。
        这对于实时任务非常重要，可以减少缓存失效和核心迁移开销。

        Args:
            core_ids: CPU核心ID列表，如[0, 1]表示绑定到核心0和1。
                核心ID从0开始，最大值为CPU核心数-1。

        Returns:
            设置成功返回True，失败返回False

        Raises:
            WindowsAPIError: CPU亲和性管理器未初始化时抛出

        Example:
            >>> manager.set_thread_affinity([0])  # 绑定到核心0
            True
            >>> manager.set_thread_affinity([0, 2, 4])  # 绑定到核心0、2、4
            True
        """
        if not self._initialized:
            raise WindowsAPIError("CPU亲和性管理器未初始化")

        cpu_count = self.get_cpu_count()

        # 验证核心ID有效性
        for core_id in core_ids:
            if core_id < 0 or core_id >= cpu_count:
                logger.error(f"无效的CPU核心ID: {core_id}，有效范围: 0-{cpu_count-1}")
                return False

        # 计算亲和性掩码
        affinity_mask = 0
        for core_id in core_ids:
            affinity_mask |= 1 << core_id

        thread_handle = self._kernel32.GetCurrentThread()
        old_mask = self._kernel32.SetThreadAffinityMask(
            thread_handle, wintypes.DWORD(affinity_mask)
        )

        if old_mask == 0:
            error = ctypes.get_last_error()
            logger.error(f"设置CPU亲和性失败，错误码: {error}")
            return False

        logger.debug(f"线程CPU亲和性设置为: 核心{core_ids} (掩码: 0x{affinity_mask:X})")
        return True

    def get_process_affinity_mask(self) -> tuple[int, int]:
        """
        获取进程的CPU亲和性掩码。

        Returns:
            元组 (进程掩码, 系统掩码)：
                - 进程掩码: 当前进程可使用的CPU核心位掩码
                - 系统掩码: 系统所有可用CPU核心位掩码
            未初始化时返回 (0, 0)

        Example:
            >>> process_mask, system_mask = manager.get_process_affinity_mask()
            >>> print(f"进程掩码: 0b{process_mask:b}, 系统掩码: 0b{system_mask:b}")
        """
        if not self._initialized:
            return (0, 0)

        process_mask = wintypes.DWORD()
        system_mask = wintypes.DWORD()

        process_handle = self._kernel32.GetCurrentProcess()
        result = self._kernel32.GetProcessAffinityMask(
            process_handle, ctypes.byref(process_mask), ctypes.byref(system_mask)
        )

        if not result:
            logger.warning("获取进程亲和性掩码失败")
            return (0, 0)

        return (process_mask.value, system_mask.value)

    def get_available_cores(self) -> list[int]:
        """
        获取可用的CPU核心列表。

        解析进程亲和性掩码，返回当前进程可使用的CPU核心ID列表。

        Returns:
            可用核心ID列表，如[0, 1, 2, 3]

        Example:
            >>> cores = manager.get_available_cores()
            >>> print(f"可用核心: {cores}")
        """
        process_mask, _ = self.get_process_affinity_mask()

        if process_mask == 0:
            # 如果获取失败，返回所有核心
            return list(range(self.get_cpu_count()))

        cores = []
        bit = 1
        core_id = 0
        while bit <= process_mask:
            if process_mask & bit:
                cores.append(core_id)
            bit <<= 1
            core_id += 1

        return cores


class WindowsRTScheduler:
    """
    Windows实时调度器。

    提供高精度定时、线程优先级设置和CPU亲和性绑定的综合管理。
    支持上下文管理器模式，确保资源正确释放。

    该类整合了以下功能：
    - WinMMWrapper: 高精度定时器控制
    - ThreadPriorityManager: 线程/进程优先级管理
    - CPUAffinityManager: CPU亲和性管理
    - SchedulerPerformanceMetrics: 性能监控

    Attributes:
        _interval_ms: 定时器精度（毫秒）
        _winmm: WinMM封装实例
        _priority_manager: 优先级管理器实例
        _affinity_manager: CPU亲和性管理器实例
        _original_priority: 原始线程优先级
        _original_priority_class: 原始进程优先级类
        _original_affinity: 原始CPU亲和性掩码
        _active: 调度器激活状态
        _performance_metrics: 性能指标实例
        _shutdown_requested: 是否请求关闭
        _lock: 线程锁

    Example:
        >>> with WindowsRTScheduler(interval_ms=5) as scheduler:
        ...     scheduler.set_thread_priority(THREAD_PRIORITY_HIGHEST)
        ...     scheduler.set_cpu_affinity([0])
        ...     # 执行实时任务
        ...     pass
    """

    def __init__(self, interval_ms: int = 5) -> None:
        """
        初始化调度器。

        Args:
            interval_ms: 定时器精度（毫秒），默认5ms。
                建议范围1-10ms，过小可能增加系统开销。
        """
        self._interval_ms = interval_ms
        self._winmm: Optional[WinMMWrapper] = None
        self._priority_manager: Optional[ThreadPriorityManager] = None
        self._affinity_manager: Optional[CPUAffinityManager] = None
        self._original_priority: Optional[int] = None
        self._original_priority_class: Optional[int] = None
        self._original_affinity: Optional[int] = None
        self._active = False

        # 性能监控
        self._performance_metrics = SchedulerPerformanceMetrics()

        # 优雅退出
        self._shutdown_requested = False
        self._lock = threading.Lock()

        logger.info(f"WindowsRTScheduler初始化，精度: {interval_ms}ms")

    def _initialize_managers(self) -> None:
        """
        初始化各管理器实例。

        创建WinMMWrapper、ThreadPriorityManager和CPUAffinityManager实例。

        Raises:
            WindowsAPIError: 任一管理器初始化失败时抛出
        """
        try:
            self._winmm = WinMMWrapper()
            self._priority_manager = ThreadPriorityManager()
            self._affinity_manager = CPUAffinityManager()
        except WindowsAPIError as e:
            logger.error(f"管理器初始化失败: {e}")
            raise

    def __enter__(self) -> WindowsRTScheduler:
        """
        进入上下文，设置高精度定时。

        执行以下操作：
        1. 初始化所有管理器
        2. 保存原始系统设置
        3. 设置高精度定时器

        Returns:
            调度器实例

        Raises:
            WindowsAPIError: 管理器初始化失败时抛出
        """
        try:
            self._initialize_managers()

            # 保存原始设置
            self._original_priority = self._priority_manager.get_thread_priority()
            self._original_priority_class = self._priority_manager.get_process_priority_class()
            process_mask, _ = self._affinity_manager.get_process_affinity_mask()
            self._original_affinity = process_mask

            # 设置高精度定时器
            if not self._winmm.time_begin_period(self._interval_ms):
                logger.warning(f"设置定时器精度 {self._interval_ms}ms 失败")

            self._active = True
            self._shutdown_requested = False

            logger.info("进入实时调度上下文")
            return self
        except Exception as e:
            # 初始化失败时清理已分配的资源
            self._cleanup_resources()
            logger.error(f"进入实时调度上下文失败: {e}")
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        退出上下文，恢复系统设置。

        执行以下操作：
        1. 恢复线程优先级
        2. 恢复进程优先级
        3. 恢复CPU亲和性
        4. 恢复定时器精度
        5. 记录异常信息（如有）

        Args:
            exc_type: 异常类型（如有异常）
            exc_val: 异常值（如有异常）
            exc_tb: 异常回溯（如有异常）
        """
        if not self._active:
            return

        # 记录异常信息
        if exc_type is not None:
            logger.error(f"实时调度上下文异常退出: {exc_type.__name__}: {exc_val}")
            self._performance_metrics.missed_deadlines += 1

        # 执行清理
        self._cleanup_resources()

        # 记录性能报告
        self._log_performance_summary()

        logger.info("退出实时调度上下文，已恢复原始设置")

    def _cleanup_resources(self) -> None:
        """
        清理资源并恢复系统设置。

        确保所有资源正确释放，即使发生异常。
        """
        errors: list[str] = []

        # 恢复线程优先级
        if self._priority_manager and self._original_priority is not None:
            try:
                self._priority_manager.set_thread_priority(self._original_priority)
            except Exception as e:
                errors.append(f"恢复线程优先级失败: {e}")

        # 恢复进程优先级
        if self._priority_manager and self._original_priority_class is not None:
            try:
                self._priority_manager.set_process_priority_class(self._original_priority_class)
            except Exception as e:
                errors.append(f"恢复进程优先级失败: {e}")

        # 恢复CPU亲和性
        if (
            self._affinity_manager
            and self._original_affinity is not None
            and self._original_affinity > 0
        ):
            try:
                self._affinity_manager.set_thread_affinity(
                    self._mask_to_core_ids(self._original_affinity)
                )
            except Exception as e:
                errors.append(f"恢复CPU亲和性失败: {e}")

        # 恢复定时器精度
        if self._winmm:
            try:
                self._winmm.time_end_period(self._interval_ms)
            except Exception as e:
                errors.append(f"恢复定时器精度失败: {e}")

        self._active = False

        if errors:
            for error in errors:
                logger.warning(error)

    def _log_performance_summary(self) -> None:
        """
        记录性能摘要。
        """
        report = self._performance_metrics.get_report()
        logger.info(
            f"调度器性能摘要: "
            f"执行次数={report['total_executions']}, "
            f"平均延迟={report['execution_time']['avg_ms']}ms, "
            f"P95延迟={report['execution_time']['p95_ms']}ms, "
            f"平均精度偏差={report['precision']['avg_error_ms']}ms"
        )

    def request_shutdown(self) -> None:
        """
        请求优雅关闭。

        设置关闭标志，通知调度器准备退出。
        """
        with self._lock:
            self._shutdown_requested = True
            logger.info("已请求调度器关闭")

    def is_shutdown_requested(self) -> bool:
        """
        检查是否请求关闭。

        Returns:
            是否已请求关闭
        """
        with self._lock:
            return self._shutdown_requested

    def _mask_to_core_ids(self, mask: int) -> list[int]:
        """
        将CPU亲和性掩码转换为核心ID列表。

        Args:
            mask: CPU亲和性位掩码

        Returns:
            核心ID列表，如掩码0b1011返回[0, 1, 3]

        Example:
            >>> self._mask_to_core_ids(0b1011)
            [0, 1, 3]
        """
        cores: list[int] = []
        bit = 1
        core_id = 0
        while bit <= mask:
            if mask & bit:
                cores.append(core_id)
            bit <<= 1
            core_id += 1
        return cores

    def set_thread_priority(self, priority: int) -> bool:
        """
        设置线程优先级。

        Args:
            priority: 优先级值，推荐使用:
                - THREAD_PRIORITY_ABOVE_NORMAL: 高于正常
                - THREAD_PRIORITY_HIGHEST: 最高
                - THREAD_PRIORITY_TIME_CRITICAL: 实时（需管理员权限）

        Returns:
            设置成功返回True，调度器未激活或设置失败返回False

        Example:
            >>> scheduler.set_thread_priority(THREAD_PRIORITY_HIGHEST)
            True
        """
        if not self._active:
            logger.warning("调度器未激活，请使用上下文管理器")
            return False

        return self._priority_manager.set_thread_priority(priority)

    def set_process_priority_high(self) -> bool:
        """
        设置进程为高优先级。

        将进程优先级类设置为PROCESS_PRIORITY_CLASS_HIGH。
        这会影响进程内所有线程的调度优先级。

        Returns:
            设置成功返回True，调度器未激活或设置失败返回False

        Example:
            >>> scheduler.set_process_priority_high()
            True
        """
        if not self._active:
            logger.warning("调度器未激活，请使用上下文管理器")
            return False

        return self._priority_manager.set_process_priority_class(PROCESS_PRIORITY_CLASS_HIGH)

    def set_process_priority_realtime(self) -> bool:
        """
        设置进程为实时优先级。

        将进程优先级类设置为PROCESS_PRIORITY_CLASS_REALTIME。
        这是最高优先级，可能抢占系统关键任务。

        Warning:
            - 需要管理员权限
            - 可能导致系统不稳定，甚至死锁
            - 仅在极端实时需求场景使用

        Returns:
            设置成功返回True，调度器未激活或设置失败返回False

        Example:
            >>> # 谨慎使用！
            >>> scheduler.set_process_priority_realtime()
            True
        """
        if not self._active:
            logger.warning("调度器未激活，请使用上下文管理器")
            return False

        logger.warning("设置实时优先级可能导致系统不稳定，请谨慎使用")
        return self._priority_manager.set_process_priority_class(PROCESS_PRIORITY_CLASS_REALTIME)

    def set_cpu_affinity(self, core_ids: list[int]) -> bool:
        """
        设置CPU亲和性，将线程绑定到指定核心。

        Args:
            core_ids: CPU核心ID列表，如[0]绑定到核心0，
                [0, 2, 4]绑定到核心0、2、4

        Returns:
            设置成功返回True，调度器未激活或设置失败返回False

        Example:
            >>> scheduler.set_cpu_affinity([0])  # 绑定到核心0
            True
        """
        if not self._active:
            logger.warning("调度器未激活，请使用上下文管理器")
            return False

        return self._affinity_manager.set_thread_affinity(core_ids)

    def get_cpu_count(self) -> int:
        """
        获取CPU核心数。

        Returns:
            系统逻辑CPU核心数

        Example:
            >>> count = scheduler.get_cpu_count()
            >>> print(f"系统有 {count} 个逻辑核心")
        """
        if self._affinity_manager:
            return self._affinity_manager.get_cpu_count()

        # 如果管理器未初始化，临时创建
        temp_manager = CPUAffinityManager()
        return temp_manager.get_cpu_count()

    def get_available_cores(self) -> list[int]:
        """
        获取可用的CPU核心列表。

        Returns:
            可用核心ID列表，调度器未激活时返回空列表

        Example:
            >>> cores = scheduler.get_available_cores()
            >>> print(f"可用核心: {cores}")
        """
        if not self._active:
            logger.warning("调度器未激活，请使用上下文管理器")
            return []

        return self._affinity_manager.get_available_cores()

    def get_min_timer_resolution(self) -> int:
        """
        获取系统支持的最小定时器精度。

        Returns:
            最小精度（毫秒），通常为1ms
        """
        if self._winmm:
            return self._winmm.get_min_resolution()
        return 1

    def record_execution(self, elapsed_ms: float, expected_ms: float) -> None:
        """
        记录执行时间和精度偏差。

        Args:
            elapsed_ms: 实际执行时间（毫秒）
            expected_ms: 预期执行时间（毫秒）
        """
        self._performance_metrics.update_execution_time(elapsed_ms)
        precision_error = elapsed_ms - expected_ms
        self._performance_metrics.update_precision_error(precision_error)

        # 检测是否错过截止时间（超过预期时间的50%）
        if abs(precision_error) > expected_ms * 0.5:
            self._performance_metrics.missed_deadlines += 1

    def get_performance_report(self) -> dict[str, Any]:
        """
        获取性能报告。

        Returns:
            性能报告字典，包含执行时间统计、精度偏差、可靠性指标等
        """
        report = self._performance_metrics.get_report()
        report.update(
            {
                "interval_ms": self._interval_ms,
                "active": self._active,
                "shutdown_requested": self._shutdown_requested,
            }
        )
        return report

    def reset_performance_metrics(self) -> None:
        """
        重置性能指标。

        清除所有统计数据，重新开始记录。
        """
        self._performance_metrics = SchedulerPerformanceMetrics()
        logger.info("性能指标已重置")

    @contextmanager
    def measure_execution(self, expected_ms: float = 0.0):
        """
        执行时间测量上下文管理器。

        自动记录代码块的执行时间和精度偏差。

        Args:
            expected_ms: 预期执行时间（毫秒），默认0表示不计算精度偏差

        Yields:
            None

        Example:
            >>> with scheduler.measure_execution(expected_ms=10.0):
            ...     # 执行需要测量的代码
            ...     time.sleep(0.01)
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            elapsed_ms = (time.perf_counter() - start_time) * 1000
            self.record_execution(elapsed_ms, expected_ms)


class RealtimeContext:
    """
    实时执行上下文管理器。

    提供简化的实时任务配置接口，自动管理高精度定时、
    线程优先级和CPU亲和性。适用于需要快速配置实时环境的场景。

    Attributes:
        _priority: 线程优先级
        _cpu_cores: CPU核心列表
        _interval_ms: 定时器精度
        _high_process_priority: 是否设置进程高优先级
        _scheduler: WindowsRTScheduler实例

    Example:
        >>> # 使用默认设置（高优先级，不绑定核心）
        >>> with RealtimeContext():
        ...     # 执行实时任务
        ...     pass

        >>> # 自定义设置
        >>> with RealtimeContext(
        ...     priority=THREAD_PRIORITY_HIGHEST,
        ...     cpu_cores=[0, 1]
        ... ):
        ...     # 执行实时任务
        ...     pass
    """

    def __init__(
        self,
        priority: int | None = None,
        cpu_cores: list[int] | None = None,
        interval_ms: int = 5,
        high_process_priority: bool = True,
    ) -> None:
        """
        初始化实时上下文。

        Args:
            priority: 线程优先级，None表示使用默认值THREAD_PRIORITY_ABOVE_NORMAL
            cpu_cores: CPU核心列表，None表示不绑定特定核心
            interval_ms: 定时器精度（毫秒），默认5ms
            high_process_priority: 是否设置进程高优先级，默认True
        """
        self._priority = priority if priority is not None else THREAD_PRIORITY_ABOVE_NORMAL
        self._cpu_cores = cpu_cores
        self._interval_ms = interval_ms
        self._high_process_priority = high_process_priority
        self._scheduler: Optional[WindowsRTScheduler] = None

        logger.debug(
            f"RealtimeContext初始化: priority={self._priority}, "
            f"cores={self._cpu_cores}, interval={self._interval_ms}ms"
        )

    def __enter__(self) -> RealtimeContext:
        """
        进入实时上下文。

        执行以下操作：
        1. 创建并初始化WindowsRTScheduler
        2. 设置进程优先级（如配置）
        3. 设置线程优先级
        4. 设置CPU亲和性（如配置）

        Returns:
            上下文实例
        """
        self._scheduler = WindowsRTScheduler(self._interval_ms)
        self._scheduler.__enter__()

        # 设置进程优先级
        if self._high_process_priority:
            self._scheduler.set_process_priority_high()

        # 设置线程优先级
        self._scheduler.set_thread_priority(self._priority)

        # 设置CPU亲和性
        if self._cpu_cores:
            self._scheduler.set_cpu_affinity(self._cpu_cores)

        logger.info("实时上下文已激活")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        """
        退出实时上下文。

        自动恢复所有系统设置到进入前的状态。

        Args:
            exc_type: 异常类型（如有异常）
            exc_val: 异常值（如有异常）
            exc_tb: 异常回溯（如有异常）
        """
        if self._scheduler:
            self._scheduler.__exit__(exc_type, exc_val, exc_tb)
            self._scheduler = None

        logger.info("实时上下文已退出")


@contextmanager
def high_precision_timer(interval_ms: int = 1):
    """
    高精度定时器上下文管理器。

    简化的定时器精度设置接口，仅设置定时器精度，
    不修改线程优先级或CPU亲和性。适用于仅需要高精度定时的场景。

    Args:
        interval_ms: 定时器精度（毫秒），默认1ms

    Yields:
        None

    Example:
        >>> with high_precision_timer(1):
        ...     # 执行需要高精度定时的代码
        ...     import time
        ...     time.sleep(0.001)  # 更精确的1ms延迟
    """
    winmm = WinMMWrapper()
    winmm.time_begin_period(interval_ms)
    try:
        yield
    finally:
        winmm.time_end_period(interval_ms)


def check_realtime_capability() -> dict[str, Any]:
    """
    检查系统实时能力。

    收集并返回系统实时调度的相关信息，包括CPU核心数、
    定时器精度、可用核心和管理员权限状态。

    Returns:
        包含系统实时能力信息的字典：
            - platform: 平台名称
            - cpu_count: CPU核心数
            - min_timer_resolution_ms: 最小定时器精度
            - available_cores: 可用核心列表
            - admin_privilege: 是否有管理员权限
            - errors: 错误信息列表

    Example:
        >>> info = check_realtime_capability()
        >>> print(f"CPU核心数: {info['cpu_count']}")
        >>> print(f"最小定时器精度: {info['min_timer_resolution_ms']}ms")
    """
    result: dict[str, Any] = {
        "platform": "Windows",
        "cpu_count": 0,
        "min_timer_resolution_ms": 1,
        "available_cores": [],
        "admin_privilege": False,
        "errors": [],
    }

    try:
        affinity_manager = CPUAffinityManager()
        result["cpu_count"] = affinity_manager.get_cpu_count()
        result["available_cores"] = affinity_manager.get_available_cores()
    except Exception as e:
        result["errors"].append(f"CPU亲和性检测失败: {e}")

    try:
        winmm = WinMMWrapper()
        result["min_timer_resolution_ms"] = winmm.get_min_resolution()
    except Exception as e:
        result["errors"].append(f"定时器检测失败: {e}")

    # 检查管理员权限
    try:
        import ctypes

        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        result["admin_privilege"] = bool(is_admin)
    except Exception:
        result["admin_privilege"] = False

    return result


# 模块级便捷函数
def set_realtime_priority() -> bool:
    """
    设置当前线程为实时优先级。

    快捷函数，直接将当前线程设置为THREAD_PRIORITY_TIME_CRITICAL优先级。

    Warning:
        - 需要管理员权限
        - 可能导致系统不稳定
        - 建议使用RealtimeContext上下文管理器替代

    Returns:
        设置成功返回True，失败返回False

    Example:
        >>> if set_realtime_priority():
        ...     print("实时优先级设置成功")
        ... else:
        ...     print("设置失败，请以管理员身份运行")
    """
    try:
        manager = ThreadPriorityManager()
        return manager.set_thread_priority(THREAD_PRIORITY_TIME_CRITICAL)
    except Exception as e:
        logger.error(f"设置实时优先级失败: {e}")
        return False


def bind_to_cpu_core(core_id: int) -> bool:
    """
    将当前线程绑定到指定CPU核心。

    快捷函数，将当前线程绑定到单个CPU核心。

    Args:
        core_id: CPU核心ID，从0开始

    Returns:
        设置成功返回True，失败返回False

    Example:
        >>> if bind_to_cpu_core(0):
        ...     print("已绑定到核心0")

    Note:
        如需绑定多个核心，请使用CPUAffinityManager.set_thread_affinity()
    """
    try:
        manager = CPUAffinityManager()
        return manager.set_thread_affinity([core_id])
    except Exception as e:
        logger.error(f"绑定CPU核心失败: {e}")
        return False
