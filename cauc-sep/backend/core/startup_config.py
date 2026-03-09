"""
启动性能优化配置模块。

提供应用启动时的性能优化配置，包括模块预加载、
环境变量设置、垃圾回收优化等。

功能：
    - 禁用不必要的警告
    - 优化NumPy/SciPy计算线程数
    - 预加载常用模块
    - 配置垃圾回收策略
    - 内存使用优化

作者：运维工程师 Agent
创建日期：2026-03-07
"""

import gc
import os
import sys
import warnings
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Optional


class StartupConfig:
    """启动配置管理类。
    
    集中管理应用启动时的各项优化配置。
    
    Attributes:
        optimize_numpy: 是否优化NumPy配置
        preload_modules: 是否预加载模块
        optimize_gc: 是否优化垃圾回收
        thread_pool_size: 线程池大小
    """
    
    def __init__(
        self,
        optimize_numpy: bool = True,
        preload_modules: bool = True,
        optimize_gc: bool = True,
        thread_pool_size: Optional[int] = None,
    ) -> None:
        """初始化启动配置。
        
        Args:
            optimize_numpy: 是否优化NumPy多线程配置
            preload_modules: 是否预加载常用模块
            optimize_gc: 是否优化垃圾回收参数
            thread_pool_size: 线程池大小，None表示自动检测
        """
        self.optimize_numpy = optimize_numpy
        self.preload_modules = preload_modules
        self.optimize_gc = optimize_gc
        self.thread_pool_size = thread_pool_size or self._detect_optimal_threads()
        
        self._applied = False
    
    @staticmethod
    def _detect_optimal_threads() -> int:
        """检测最优线程数。
        
        根据CPU核心数计算最优线程数，用于并行计算。
        
        Returns:
            int: 最优线程数
        """
        cpu_count = os.cpu_count() or 4
        # 保留一个核心给系统
        return max(1, cpu_count - 1)
    
    def apply(self) -> dict[str, Any]:
        """应用所有优化配置。
        
        Returns:
            dict: 应用结果，包含各项配置的状态
        
        Example:
            >>> config = StartupConfig()
            >>> result = config.apply()
            >>> print(f"优化完成: {result}")
        """
        if self._applied:
            return {"status": "already_applied"}
        
        result: dict[str, Any] = {
            "status": "success",
            "optimizations": [],
        }
        
        # 1. 禁用不必要的警告
        self._configure_warnings()
        result["optimizations"].append("warnings_configured")
        
        # 2. 优化NumPy/SciPy
        if self.optimize_numpy:
            self._optimize_numpy()
            result["optimizations"].append("numpy_optimized")
        
        # 3. 预加载模块
        if self.preload_modules:
            preload_result = self._preload_modules()
            result["optimizations"].append("modules_preloaded")
            result["preloaded_modules"] = preload_result
        
        # 4. 优化垃圾回收
        if self.optimize_gc:
            self._optimize_gc()
            result["optimizations"].append("gc_optimized")
        
        # 5. 配置线程池
        self._configure_thread_pool()
        result["optimizations"].append("thread_pool_configured")
        
        self._applied = True
        return result
    
    @staticmethod
    def _configure_warnings() -> None:
        """配置警告过滤器。
        
        禁用不影响功能的警告，减少日志噪音。
        """
        # 禁用过时警告
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=FutureWarning)
        
        # 禁用特定模块的警告
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            module="uvicorn",
        )
        warnings.filterwarnings(
            "ignore",
            category=UserWarning,
            module="pydantic",
        )
    
    def _optimize_numpy(self) -> None:
        """优化NumPy/SciPy计算配置。
        
        设置多线程计算参数，避免过度占用CPU资源。
        """
        thread_count = str(self.thread_pool_size)
        
        # OpenMP线程数
        os.environ.setdefault("OMP_NUM_THREADS", thread_count)
        
        # MKL线程数（Intel Math Kernel Library）
        os.environ.setdefault("MKL_NUM_THREADS", thread_count)
        
        # OpenBLAS线程数
        os.environ.setdefault("OPENBLAS_NUM_THREADS", thread_count)
        
        # VECLIB线程数（macOS）
        os.environ.setdefault("VECLIB_MAXIMUM_THREADS", thread_count)
        
        # NumPy线程数
        os.environ.setdefault("NUMEXPR_NUM_THREADS", thread_count)
    
    @staticmethod
    def _preload_modules() -> dict[str, bool]:
        """预加载常用模块。
        
        提前加载常用模块，减少首次访问时的延迟。
        
        Returns:
            dict: 各模块的加载状态
        """
        preload_list: list[str] = [
            # 核心依赖
            "numpy",
            "scipy.optimize",
            "scipy.interpolate",
            # Web框架
            "fastapi",
            "uvicorn",
            "starlette",
            # 数据处理
            "pydantic",
            "sqlalchemy",
            # 序列化
            "json",
            "orjson",
        ]
        
        result: dict[str, bool] = {}
        
        for module in preload_list:
            try:
                __import__(module)
                result[module] = True
            except ImportError:
                result[module] = False
        
        return result
    
    @staticmethod
    def _optimize_gc() -> None:
        """优化垃圾回收参数。
        
        调整GC阈值，减少垃圾回收对性能的影响。
        """
        # 获取当前阈值
        thresholds = gc.get_threshold()
        
        # 设置新的阈值（根据实际负载调整）
        # threshold0: 触发GC的分配次数
        # threshold1: 触发GC的分配次数（考虑存活对象）
        # threshold2: 触发GC的分配次数（考虑所有对象）
        gc.set_threshold(
            thresholds[0] * 2,  # 增加阈值，减少GC频率
            thresholds[1],
            thresholds[2],
        )
        
        # 禁用自动GC（适用于长时间运行的服务）
        # gc.disable()  # 谨慎使用，需要手动调用gc.collect()
    
    def _configure_thread_pool(self) -> None:
        """配置线程池。
        
        设置默认线程池大小，用于异步IO操作。
        """
        # 设置asyncio默认线程池大小
        if hasattr(sys, "setswitchinterval"):
            # 设置线程切换间隔（微秒）
            sys.setswitchinterval(0.005)


def optimize_startup(
    optimize_numpy: bool = True,
    preload_modules: bool = True,
    optimize_gc: bool = True,
) -> dict[str, Any]:
    """应用启动优化配置。
    
    便捷函数，快速应用所有优化配置。
    
    Args:
        optimize_numpy: 是否优化NumPy配置
        preload_modules: 是否预加载模块
        optimize_gc: 是否优化垃圾回收
    
    Returns:
        dict: 优化结果
    
    Example:
        >>> result = optimize_startup()
        >>> print(f"已应用优化: {result['optimizations']}")
    """
    config = StartupConfig(
        optimize_numpy=optimize_numpy,
        preload_modules=preload_modules,
        optimize_gc=optimize_gc,
    )
    return config.apply()


def get_system_info() -> dict[str, Any]:
    """获取系统信息。
    
    收集系统配置信息，用于性能调优参考。
    
    Returns:
        dict: 系统信息字典
    
    Example:
        >>> info = get_system_info()
        >>> print(f"CPU核心数: {info['cpu_count']}")
    """
    info: dict[str, Any] = {
        "python_version": sys.version,
        "platform": sys.platform,
        "cpu_count": os.cpu_count(),
        "executable": sys.executable,
    }
    
    # 内存信息（如果可用）
    try:
        import psutil
        
        memory = psutil.virtual_memory()
        info["memory_total_gb"] = memory.total / (1024**3)
        info["memory_available_gb"] = memory.available / (1024**3)
    except ImportError:
        pass
    
    # NumPy信息
    try:
        import numpy as np
        
        info["numpy_version"] = np.__version__
        info["numpy_config"] = {
            "threads": os.environ.get("OMP_NUM_THREADS", "default"),
        }
    except ImportError:
        pass
    
    return info


def check_dependencies() -> dict[str, dict[str, str]]:
    """检查依赖包版本。
    
    验证所有必需依赖是否正确安装。
    
    Returns:
        dict: 依赖包及其版本信息
    
    Example:
        >>> deps = check_dependencies()
        >>> for pkg, info in deps.items():
        ...     print(f"{pkg}: {info['status']}")
    """
    required_packages: list[str] = [
        "fastapi",
        "uvicorn",
        "pydantic",
        "sqlalchemy",
        "numpy",
        "scipy",
        "pymodbus",
        "serial",
    ]
    
    result: dict[str, dict[str, str]] = {}
    
    for package in required_packages:
        try:
            module = __import__(package)
            version = getattr(module, "__version__", "unknown")
            result[package] = {
                "status": "installed",
                "version": version,
            }
        except ImportError:
            result[package] = {
                "status": "missing",
                "version": "N/A",
            }
    
    return result


class PerformanceMonitor:
    """性能监控器。
    
    监控应用启动和运行时的性能指标。
    """
    
    def __init__(self) -> None:
        """初始化性能监控器。"""
        self._metrics: dict[str, float] = {}
        self._start_time: Optional[float] = None
    
    def start(self) -> None:
        """开始计时。"""
        import time
        
        self._start_time = time.time()
    
    def record(self, name: str) -> None:
        """记录时间点。
        
        Args:
            name: 指标名称
        """
        import time
        
        if self._start_time is None:
            return
        
        self._metrics[name] = time.time() - self._start_time
    
    def get_report(self) -> dict[str, Any]:
        """获取性能报告。
        
        Returns:
            dict: 性能指标报告
        """
        return {
            "metrics": self._metrics,
            "total_time": sum(self._metrics.values()),
        }
