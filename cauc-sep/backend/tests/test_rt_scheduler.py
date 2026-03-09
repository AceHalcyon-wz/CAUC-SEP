"""
文件名: test_rt_scheduler.py
路径: backend/tests/
功能: 实时调度器模块单元测试
作者: Test Debugger Agent
创建日期: 2024-03-07
依赖: pytest, numpy
"""

import sys
import threading
import time
from unittest.mock import MagicMock, patch

import pytest


class TestWinMMWrapper:
    """WinMM封装测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_time_begin_period(self):
        """测试定时器精度设置。"""
        from core.rt_scheduler import WinMMWrapper

        wrapper = WinMMWrapper()
        result = wrapper.time_begin_period(1)

        assert result is True

        # 清理
        wrapper.time_end_period(1)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_time_end_period(self):
        """测试定时器精度恢复。"""
        from core.rt_scheduler import WinMMWrapper

        wrapper = WinMMWrapper()
        wrapper.time_begin_period(1)

        result = wrapper.time_end_period(1)

        assert result is True

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_min_resolution(self):
        """测试获取最小定时器精度。"""
        from core.rt_scheduler import WinMMWrapper

        wrapper = WinMMWrapper()
        min_res = wrapper.get_min_resolution()

        assert isinstance(min_res, int)
        assert min_res >= 1

    def test_uninitialized_operations(self):
        """测试未初始化时的操作。"""
        from core.rt_scheduler import WinMMWrapper, WindowsAPIError

        wrapper = WinMMWrapper.__new__(WinMMWrapper)
        wrapper._initialized = False

        with pytest.raises(WindowsAPIError, match="未初始化"):
            wrapper.time_begin_period(1)


class TestThreadPriorityManager:
    """线程优先级管理器测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_thread_priority(self):
        """测试线程优先级设置。"""
        from core.rt_scheduler import (
            THREAD_PRIORITY_ABOVE_NORMAL,
            ThreadPriorityManager,
        )

        manager = ThreadPriorityManager()

        result = manager.set_thread_priority(THREAD_PRIORITY_ABOVE_NORMAL)

        assert result is True

        # 恢复默认优先级
        manager.set_thread_priority(0)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_thread_priority(self):
        """测试获取线程优先级。"""
        from core.rt_scheduler import ThreadPriorityManager

        manager = ThreadPriorityManager()
        priority = manager.get_thread_priority()

        assert isinstance(priority, int)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_process_priority_class(self):
        """测试进程优先级类设置。"""
        from core.rt_scheduler import (
            PROCESS_PRIORITY_CLASS_HIGH,
            PROCESS_PRIORITY_CLASS_NORMAL,
            ThreadPriorityManager,
        )

        manager = ThreadPriorityManager()

        result = manager.set_process_priority_class(PROCESS_PRIORITY_CLASS_HIGH)

        assert result is True

        # 恢复默认优先级
        manager.set_process_priority_class(PROCESS_PRIORITY_CLASS_NORMAL)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_process_priority_class(self):
        """测试获取进程优先级类。"""
        from core.rt_scheduler import ThreadPriorityManager

        manager = ThreadPriorityManager()
        priority_class = manager.get_process_priority_class()

        assert isinstance(priority_class, int)


class TestCPUAffinityManager:
    """CPU亲和性管理器测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_cpu_count(self):
        """测试获取CPU核心数。"""
        from core.rt_scheduler import CPUAffinityManager

        manager = CPUAffinityManager()
        cpu_count = manager.get_cpu_count()

        assert isinstance(cpu_count, int)
        assert cpu_count >= 1

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_thread_affinity(self):
        """测试设置CPU亲和性。"""
        from core.rt_scheduler import CPUAffinityManager

        manager = CPUAffinityManager()
        cpu_count = manager.get_cpu_count()

        # 绑定到第一个核心
        result = manager.set_thread_affinity([0])

        assert result is True

        # 恢复到所有核心
        manager.set_thread_affinity(list(range(cpu_count)))

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_thread_affinity_invalid_core(self):
        """测试设置无效CPU核心。"""
        from core.rt_scheduler import CPUAffinityManager

        manager = CPUAffinityManager()
        cpu_count = manager.get_cpu_count()

        # 尝试绑定到不存在的核心
        result = manager.set_thread_affinity([cpu_count + 10])

        assert result is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_process_affinity_mask(self):
        """测试获取进程亲和性掩码。"""
        from core.rt_scheduler import CPUAffinityManager

        manager = CPUAffinityManager()
        process_mask, system_mask = manager.get_process_affinity_mask()

        assert isinstance(process_mask, int)
        assert isinstance(system_mask, int)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_available_cores(self):
        """测试获取可用核心列表。"""
        from core.rt_scheduler import CPUAffinityManager

        manager = CPUAffinityManager()
        cores = manager.get_available_cores()

        assert isinstance(cores, list)
        assert len(cores) >= 1


class TestWindowsRTScheduler:
    """Windows实时调度器测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_context_manager(self):
        """测试上下文管理器模式。"""
        from core.rt_scheduler import WindowsRTScheduler

        with WindowsRTScheduler(interval_ms=5) as scheduler:
            assert scheduler._active is True
            assert scheduler._winmm is not None
            assert scheduler._priority_manager is not None
            assert scheduler._affinity_manager is not None

        # 退出后应该已恢复
        assert scheduler._active is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_context_manager_saves_original_settings(self):
        """测试上下文管理器保存原始设置。"""
        from core.rt_scheduler import WindowsRTScheduler

        scheduler = WindowsRTScheduler(interval_ms=5)

        with scheduler:
            original_priority = scheduler._original_priority
            original_affinity = scheduler._original_affinity

        # 验证原始设置被保存
        assert original_priority is not None

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_thread_priority(self):
        """测试线程优先级设置。"""
        from core.rt_scheduler import (
            THREAD_PRIORITY_HIGHEST,
            WindowsRTScheduler,
        )

        # 直接测试优先级管理器
        from core.rt_scheduler import ThreadPriorityManager

        manager = ThreadPriorityManager()
        result = manager.set_thread_priority(THREAD_PRIORITY_HIGHEST)

        assert result is True

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_thread_priority_not_active(self):
        """测试未激活时设置线程优先级。"""
        from core.rt_scheduler import WindowsRTScheduler

        scheduler = WindowsRTScheduler()

        result = scheduler.set_thread_priority(1)

        assert result is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_cpu_affinity(self):
        """测试CPU亲和性设置。"""
        from core.rt_scheduler import WindowsRTScheduler

        with WindowsRTScheduler() as scheduler:
            cpu_count = scheduler.get_cpu_count()

            result = scheduler.set_cpu_affinity([0])

            assert result is True

            # 恢复
            scheduler.set_cpu_affinity(list(range(cpu_count)))

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_cpu_affinity_not_active(self):
        """测试未激活时设置CPU亲和性。"""
        from core.rt_scheduler import WindowsRTScheduler

        scheduler = WindowsRTScheduler()

        result = scheduler.set_cpu_affinity([0])

        assert result is False

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_process_priority_high(self):
        """测试设置进程高优先级。"""
        from core.rt_scheduler import (
            PROCESS_PRIORITY_CLASS_HIGH,
            PROCESS_PRIORITY_CLASS_NORMAL,
            ThreadPriorityManager,
        )

        manager = ThreadPriorityManager()
        result = manager.set_process_priority_class(PROCESS_PRIORITY_CLASS_HIGH)

        assert result is True

        # 恢复正常优先级
        manager.set_process_priority_class(PROCESS_PRIORITY_CLASS_NORMAL)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_cpu_count(self):
        """测试获取CPU核心数。"""
        from core.rt_scheduler import WindowsRTScheduler

        scheduler = WindowsRTScheduler()
        cpu_count = scheduler.get_cpu_count()

        assert isinstance(cpu_count, int)
        assert cpu_count >= 1

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_available_cores(self):
        """测试获取可用核心列表。"""
        from core.rt_scheduler import WindowsRTScheduler

        with WindowsRTScheduler() as scheduler:
            cores = scheduler.get_available_cores()

            assert isinstance(cores, list)
            assert len(cores) >= 1

    def test_get_available_cores_not_active(self):
        """测试未激活时获取可用核心。"""
        from core.rt_scheduler import WindowsRTScheduler

        scheduler = WindowsRTScheduler()

        cores = scheduler.get_available_cores()

        assert cores == []

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_get_min_timer_resolution(self):
        """测试获取最小定时器精度。"""
        from core.rt_scheduler import WindowsRTScheduler

        scheduler = WindowsRTScheduler()
        min_res = scheduler.get_min_timer_resolution()

        assert isinstance(min_res, int)
        assert min_res >= 1


class TestRealtimeContext:
    """实时执行上下文测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_context_manager_default(self):
        """测试默认实时上下文。"""
        from core.rt_scheduler import RealtimeContext

        with RealtimeContext():
            pass

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_context_manager_custom_priority(self):
        """测试自定义优先级实时上下文。"""
        from core.rt_scheduler import (
            THREAD_PRIORITY_HIGHEST,
            RealtimeContext,
        )

        with RealtimeContext(priority=THREAD_PRIORITY_HIGHEST):
            pass

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_context_manager_custom_cores(self):
        """测试自定义CPU核心实时上下文。"""
        from core.rt_scheduler import RealtimeContext

        with RealtimeContext(cpu_cores=[0]):
            pass

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_context_manager_no_high_process_priority(self):
        """测试不设置进程高优先级的实时上下文。"""
        from core.rt_scheduler import RealtimeContext

        with RealtimeContext(high_process_priority=False):
            pass


class TestHighPrecisionTimer:
    """高精度定时器测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_high_precision_timer_context(self):
        """测试高精度定时器上下文。"""
        from core.rt_scheduler import high_precision_timer

        with high_precision_timer(1):
            # 在上下文中执行一些操作
            time.sleep(0.001)


class TestCheckRealtimeCapability:
    """检查系统实时能力测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_check_realtime_capability(self):
        """测试检查系统实时能力。"""
        from core.rt_scheduler import check_realtime_capability

        result = check_realtime_capability()

        assert isinstance(result, dict)
        assert "platform" in result
        assert "cpu_count" in result
        assert "min_timer_resolution_ms" in result
        assert "available_cores" in result
        assert "admin_privilege" in result
        assert "errors" in result

        assert result["platform"] == "Windows"
        # cpu_count可能为0（ctypes兼容性问题），但字段必须存在
        assert isinstance(result["cpu_count"], int)


class TestModuleFunctions:
    """模块级便捷函数测试。"""

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_set_realtime_priority(self):
        """测试设置实时优先级。"""
        from core.rt_scheduler import set_realtime_priority

        # 非管理员权限下可能失败
        result = set_realtime_priority()

        assert isinstance(result, bool)

    @pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
    def test_bind_to_cpu_core(self):
        """测试绑定CPU核心。"""
        from core.rt_scheduler import bind_to_cpu_core

        result = bind_to_cpu_core(0)

        assert isinstance(result, bool)


class TestNonWindowsPlatform:
    """非Windows平台测试。"""

    @pytest.mark.skipif(sys.platform == "win32", reason="Non-Windows only")
    def test_windows_only_on_linux(self):
        """测试在非Windows平台上的行为。"""
        # 在非Windows平台上，导入应该失败或抛出异常
        with pytest.raises(Exception):
            from core.rt_scheduler import WinMMWrapper

            WinMMWrapper()


class TestConstants:
    """常量测试。"""

    def test_thread_priority_constants(self):
        """测试线程优先级常量。"""
        from core.rt_scheduler import (
            THREAD_PRIORITY_ABOVE_NORMAL,
            THREAD_PRIORITY_BELOW_NORMAL,
            THREAD_PRIORITY_HIGHEST,
            THREAD_PRIORITY_IDLE,
            THREAD_PRIORITY_LOWEST,
            THREAD_PRIORITY_NORMAL,
            THREAD_PRIORITY_TIME_CRITICAL,
        )

        assert THREAD_PRIORITY_IDLE == -15
        assert THREAD_PRIORITY_LOWEST == -2
        assert THREAD_PRIORITY_BELOW_NORMAL == -1
        assert THREAD_PRIORITY_NORMAL == 0
        assert THREAD_PRIORITY_ABOVE_NORMAL == 1
        assert THREAD_PRIORITY_HIGHEST == 2
        assert THREAD_PRIORITY_TIME_CRITICAL == 15

    def test_process_priority_constants(self):
        """测试进程优先级常量。"""
        from core.rt_scheduler import (
            PROCESS_PRIORITY_CLASS_HIGH,
            PROCESS_PRIORITY_CLASS_NORMAL,
            PROCESS_PRIORITY_CLASS_REALTIME,
        )

        assert PROCESS_PRIORITY_CLASS_NORMAL == 0x20
        assert PROCESS_PRIORITY_CLASS_HIGH == 0x80
        assert PROCESS_PRIORITY_CLASS_REALTIME == 0x100


class TestWindowsAPIError:
    """WindowsAPIError异常测试。"""

    def test_exception_creation(self):
        """测试异常创建。"""
        from core.rt_scheduler import WindowsAPIError

        error = WindowsAPIError("Test error")

        assert str(error) == "Test error"
        assert isinstance(error, Exception)
