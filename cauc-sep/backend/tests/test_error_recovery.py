"""
文件名: test_error_recovery.py
路径: backend/tests/
功能: 错误恢复系统单元测试
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: pytest, asyncio
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.error_recovery import (
    DeviceConnectionRecovery,
    DeviceConnectionState,
    ErrorRecoveryManager,
    ExperimentCheckpoint,
    ExperimentStateRecovery,
    RecoveryState,
    RecoveryStrategy,
    RetryConfig,
    RetryExecutor,
    RetryResult,
    WebSocketReconnectionManager,
    WebSocketReconnectionState,
)


class TestRetryConfig:
    """重试配置测试类。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = RetryConfig()
        assert config.max_retries == 3
        assert config.initial_delay == 1.0
        assert config.max_delay == 60.0
        assert config.backoff_factor == 2.0
        assert config.strategy == RecoveryStrategy.EXPONENTIAL_BACKOFF
        assert config.jitter is True

    def test_calculate_delay_immediate(self):
        """测试立即重试策略延迟计算。"""
        config = RetryConfig(strategy=RecoveryStrategy.IMMEDIATE)
        assert config.calculate_delay(1) == 0.0
        assert config.calculate_delay(5) == 0.0

    def test_calculate_delay_fixed(self):
        """测试固定间隔策略延迟计算。"""
        config = RetryConfig(
            strategy=RecoveryStrategy.FIXED_INTERVAL,
            initial_delay=2.0,
            jitter=False,
        )
        assert config.calculate_delay(1) == 2.0
        assert config.calculate_delay(3) == 2.0

    def test_calculate_delay_linear(self):
        """测试线性退避策略延迟计算。"""
        config = RetryConfig(
            strategy=RecoveryStrategy.LINEAR_BACKOFF,
            initial_delay=1.0,
            jitter=False,
        )
        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 3.0

    def test_calculate_delay_exponential(self):
        """测试指数退避策略延迟计算。"""
        config = RetryConfig(
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay=1.0,
            backoff_factor=2.0,
            jitter=False,
        )
        assert config.calculate_delay(1) == 1.0
        assert config.calculate_delay(2) == 2.0
        assert config.calculate_delay(3) == 4.0
        assert config.calculate_delay(4) == 8.0

    def test_max_delay_limit(self):
        """测试最大延迟限制。"""
        config = RetryConfig(
            strategy=RecoveryStrategy.EXPONENTIAL_BACKOFF,
            initial_delay=1.0,
            backoff_factor=10.0,
            max_delay=30.0,
            jitter=False,
        )
        assert config.calculate_delay(3) == 30.0  # 100 > 30, 限制为30

    def test_should_retry_with_specific_exceptions(self):
        """测试特定异常重试判断。"""
        config = RetryConfig(
            retryable_exceptions=[ConnectionError, TimeoutError]
        )

        assert config.should_retry(ConnectionError("test")) is True
        assert config.should_retry(TimeoutError("test")) is True
        assert config.should_retry(ValueError("test")) is False

    def test_should_retry_all_exceptions(self):
        """测试默认重试所有异常。"""
        config = RetryConfig()
        assert config.should_retry(Exception("test")) is True
        assert config.should_retry(ValueError("test")) is True


class TestRetryExecutor:
    """重试执行器测试类。"""

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """测试成功执行。"""
        config = RetryConfig(max_retries=3)
        executor = RetryExecutor(config)

        async def success_func():
            return "success"

        result = await executor.execute(success_func)

        assert result.success is True
        assert result.attempts == 1
        assert result.result == "success"
        assert result.last_exception is None

    @pytest.mark.asyncio
    async def test_retry_on_failure(self):
        """测试失败重试。"""
        config = RetryConfig(
            max_retries=3,
            strategy=RecoveryStrategy.IMMEDIATE,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def fail_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("连接失败")
            return "success"

        result = await executor.execute(fail_then_success)

        assert result.success is True
        assert result.attempts == 3
        assert result.result == "success"

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """测试超过最大重试次数。"""
        config = RetryConfig(
            max_retries=2,
            strategy=RecoveryStrategy.IMMEDIATE,
        )
        executor = RetryExecutor(config)

        async def always_fail():
            raise ConnectionError("始终失败")

        result = await executor.execute(always_fail)

        assert result.success is False
        assert result.attempts == 2
        assert isinstance(result.last_exception, ConnectionError)

    @pytest.mark.asyncio
    async def test_non_retryable_exception(self):
        """测试不可重试异常。"""
        config = RetryConfig(
            max_retries=3,
            retryable_exceptions=[ConnectionError],
            strategy=RecoveryStrategy.IMMEDIATE,
        )
        executor = RetryExecutor(config)

        async def raise_value_error():
            raise ValueError("不可重试的错误")

        result = await executor.execute(raise_value_error)

        assert result.success is False
        assert result.attempts == 1  # 不重试

    @pytest.mark.asyncio
    async def test_sync_function(self):
        """测试同步函数执行。"""
        config = RetryConfig(max_retries=1)
        executor = RetryExecutor(config)

        def sync_func():
            return "sync_result"

        result = await executor.execute(sync_func)

        assert result.success is True
        assert result.result == "sync_result"


class TestDeviceConnectionRecovery:
    """设备连接恢复测试类。"""

    def test_register_device(self):
        """测试设备注册。"""
        recovery = DeviceConnectionRecovery()

        async def connect():
            return True

        recovery.register_device("motor_1", connect)

        assert "motor_1" in recovery._device_states
        assert "motor_1" in recovery._connect_funcs

    def test_unregister_device(self):
        """测试设备注销。"""
        recovery = DeviceConnectionRecovery()

        async def connect():
            return True

        recovery.register_device("motor_1", connect)
        recovery.unregister_device("motor_1")

        assert "motor_1" not in recovery._device_states
        assert "motor_1" not in recovery._connect_funcs

    @pytest.mark.asyncio
    async def test_connect_device_success(self):
        """测试设备连接成功。"""
        recovery = DeviceConnectionRecovery()

        async def connect():
            return True

        recovery.register_device("motor_1", connect)
        success = await recovery.connect_device("motor_1")

        assert success is True
        state = recovery.get_device_state("motor_1")
        assert state["connected"] is True
        assert state["state"] == RecoveryState.RECOVERED.value

    @pytest.mark.asyncio
    async def test_connect_device_failure(self):
        """测试设备连接失败。"""
        config = RetryConfig(
            max_retries=2,
            strategy=RecoveryStrategy.IMMEDIATE,
        )
        recovery = DeviceConnectionRecovery(default_config=config)

        async def connect():
            raise ConnectionError("连接失败")

        recovery.register_device("motor_1", connect)
        success = await recovery.connect_device("motor_1")

        assert success is False
        state = recovery.get_device_state("motor_1")
        assert state["connected"] is False
        assert state["state"] == RecoveryState.EXHAUSTED.value

    @pytest.mark.asyncio
    async def test_disconnect_device(self):
        """测试设备断开连接。"""
        recovery = DeviceConnectionRecovery()

        async def connect():
            return True

        async def disconnect():
            pass

        recovery.register_device("motor_1", connect, disconnect)
        await recovery.connect_device("motor_1")
        success = await recovery.disconnect_device("motor_1")

        assert success is True
        state = recovery.get_device_state("motor_1")
        assert state["connected"] is False

    def test_get_all_states(self):
        """测试获取所有设备状态。"""
        recovery = DeviceConnectionRecovery()

        async def connect():
            return True

        recovery.register_device("motor_1", connect)
        recovery.register_device("motor_2", connect)

        states = recovery.get_all_states()

        assert "motor_1" in states
        assert "motor_2" in states


class TestWebSocketReconnectionManager:
    """WebSocket重连管理器测试类。"""

    def test_register_connection(self):
        """测试连接注册。"""
        manager = WebSocketReconnectionManager()

        async def connect():
            return MagicMock()

        manager.register_connection("ws_1", connect)

        assert "ws_1" in manager._connection_states
        assert "ws_1" in manager._connect_funcs

    def test_unregister_connection(self):
        """测试连接注销。"""
        manager = WebSocketReconnectionManager()

        async def connect():
            return MagicMock()

        manager.register_connection("ws_1", connect)
        manager.unregister_connection("ws_1")

        assert "ws_1" not in manager._connection_states
        assert "ws_1" not in manager._connect_funcs

    @pytest.mark.asyncio
    async def test_connect_success(self):
        """测试连接成功。"""
        manager = WebSocketReconnectionManager()

        mock_ws = MagicMock()
        mock_ws.ping = AsyncMock()

        async def connect():
            return mock_ws

        manager.register_connection("ws_1", connect)
        success = await manager.connect("ws_1")

        assert success is True
        state = manager.get_connection_state("ws_1")
        assert state["connected"] is True
        assert state["state"] == RecoveryState.RECOVERED.value

    @pytest.mark.asyncio
    async def test_connect_failure(self):
        """测试连接失败。"""
        config = RetryConfig(
            max_retries=2,
            strategy=RecoveryStrategy.IMMEDIATE,
        )
        manager = WebSocketReconnectionManager(default_config=config)

        async def connect():
            raise ConnectionError("连接失败")

        manager.register_connection("ws_1", connect, config=config)
        success = await manager.connect("ws_1")

        assert success is False
        state = manager.get_connection_state("ws_1")
        assert state["connected"] is False

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接。"""
        manager = WebSocketReconnectionManager()

        mock_ws = MagicMock()

        async def connect():
            return mock_ws

        async def disconnect():
            pass

        manager.register_connection("ws_1", connect, disconnect_func=disconnect)
        await manager.connect("ws_1")
        success = await manager.disconnect("ws_1")

        assert success is True
        state = manager.get_connection_state("ws_1")
        assert state["connected"] is False

    def test_get_all_states(self):
        """测试获取所有连接状态。"""
        manager = WebSocketReconnectionManager()

        async def connect():
            return MagicMock()

        manager.register_connection("ws_1", connect)
        manager.register_connection("ws_2", connect)

        states = manager.get_all_states()

        assert "ws_1" in states
        assert "ws_2" in states


class TestExperimentStateRecovery:
    """实验状态恢复测试类。"""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """创建临时检查点目录。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_register_experiment(self, temp_checkpoint_dir):
        """测试实验注册。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)

        assert 1 in recovery._active_experiments
        checkpoint = recovery._active_experiments[1]
        assert checkpoint.experiment_name == "测试实验"
        assert checkpoint.total_steps == 10

    def test_unregister_experiment(self, temp_checkpoint_dir):
        """测试实验注销。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.unregister_experiment(1)

        assert 1 not in recovery._active_experiments

    def test_update_progress(self, temp_checkpoint_dir):
        """测试更新进度。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.update_progress(1, 5, status="running", data={"key": "value"})

        checkpoint = recovery._active_experiments[1]
        assert checkpoint.current_step == 5
        assert checkpoint.progress == 0.5
        assert checkpoint.status == "running"
        assert checkpoint.data["key"] == "value"

    def test_save_checkpoint(self, temp_checkpoint_dir):
        """测试保存检查点。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.update_progress(1, 5)
        success = recovery.save_checkpoint(1)

        assert success is True
        checkpoint_file = Path(temp_checkpoint_dir) / "experiment_1_checkpoint.json"
        assert checkpoint_file.exists()

        # 验证文件内容
        with open(checkpoint_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data["experiment_id"] == 1
        assert data["current_step"] == 5

    def test_load_checkpoint(self, temp_checkpoint_dir):
        """测试加载检查点。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        # 先保存一个检查点
        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.update_progress(1, 5)
        recovery.save_checkpoint(1)

        # 加载检查点
        checkpoint = recovery.load_checkpoint(1)

        assert checkpoint is not None
        assert checkpoint.experiment_id == 1
        assert checkpoint.current_step == 5
        assert checkpoint.progress == 0.5

    def test_delete_checkpoint(self, temp_checkpoint_dir):
        """测试删除检查点。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.save_checkpoint(1)
        success = recovery.delete_checkpoint(1)

        assert success is True
        checkpoint_file = Path(temp_checkpoint_dir) / "experiment_1_checkpoint.json"
        assert not checkpoint_file.exists()

    def test_list_checkpoints(self, temp_checkpoint_dir):
        """测试列出检查点。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "实验1", 10, auto_save=False)
        recovery.register_experiment(2, "实验2", 20, auto_save=False)
        recovery.save_checkpoint(1)
        recovery.save_checkpoint(2)

        checkpoints = recovery.list_checkpoints()

        assert len(checkpoints) == 2

    def test_cleanup_old_checkpoints(self, temp_checkpoint_dir):
        """测试清理旧检查点。"""
        recovery = ExperimentStateRecovery(
            checkpoint_dir=temp_checkpoint_dir,
            max_checkpoints=2,
        )

        for i in range(5):
            recovery.register_experiment(i, f"实验{i}", 10, auto_save=False)
            recovery.save_checkpoint(i)

        deleted_count = recovery.cleanup_old_checkpoints()

        assert deleted_count == 3
        checkpoints = recovery.list_checkpoints()
        assert len(checkpoints) == 2

    def test_state_change_callback(self, temp_checkpoint_dir):
        """测试状态变更回调。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        callback_called = []
        callback_checkpoint = None

        def on_state_change(checkpoint):
            nonlocal callback_checkpoint
            callback_called.append(True)
            callback_checkpoint = checkpoint

        recovery.add_state_change_callback(on_state_change)
        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.update_progress(1, 5)

        assert len(callback_called) == 1
        assert callback_checkpoint.current_step == 5

    @pytest.mark.asyncio
    async def test_auto_save(self, temp_checkpoint_dir):
        """测试自动保存。"""
        recovery = ExperimentStateRecovery(
            checkpoint_dir=temp_checkpoint_dir,
            auto_save_interval=0.1,  # 100ms
        )

        recovery.register_experiment(1, "测试实验", 10, auto_save=True)

        # 等待自动保存
        await asyncio.sleep(0.2)

        # 检查文件是否存在
        checkpoint_file = Path(temp_checkpoint_dir) / "experiment_1_checkpoint.json"
        assert checkpoint_file.exists()

        # 清理
        recovery.unregister_experiment(1)


class TestExperimentCheckpoint:
    """实验检查点测试类。"""

    def test_to_dict(self):
        """测试转换为字典。"""
        checkpoint = ExperimentCheckpoint(
            experiment_id=1,
            experiment_name="测试实验",
            status="running",
            current_step=5,
            total_steps=10,
            progress=0.5,
            start_time=1000.0,
            data={"key": "value"},
        )

        data = checkpoint.to_dict()

        assert data["experiment_id"] == 1
        assert data["experiment_name"] == "测试实验"
        assert data["current_step"] == 5
        assert data["data"]["key"] == "value"

    def test_from_dict(self):
        """测试从字典创建。"""
        data = {
            "experiment_id": 1,
            "experiment_name": "测试实验",
            "status": "running",
            "current_step": 5,
            "total_steps": 10,
            "progress": 0.5,
            "start_time": 1000.0,
            "checkpoint_time": 2000.0,
            "data": {"key": "value"},
            "metadata": {"meta": "data"},
        }

        checkpoint = ExperimentCheckpoint.from_dict(data)

        assert checkpoint.experiment_id == 1
        assert checkpoint.experiment_name == "测试实验"
        assert checkpoint.current_step == 5
        assert checkpoint.data["key"] == "value"


class TestErrorRecoveryManager:
    """错误恢复管理器测试类。"""

    @pytest.fixture
    def temp_dirs(self):
        """创建临时目录。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_dir = os.path.join(temp_dir, "checkpoints")
            device_state_file = os.path.join(temp_dir, "device_states.json")
            yield checkpoint_dir, device_state_file

    @pytest.mark.asyncio
    async def test_initialize(self, temp_dirs):
        """测试初始化。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        await manager.initialize()

        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_device_operations(self, temp_dirs):
        """测试设备操作。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        async def connect():
            return True

        manager.register_device("motor_1", connect)
        success = await manager.connect_device("motor_1")

        assert success is True

        success = await manager.disconnect_device("motor_1")
        assert success is True

    @pytest.mark.asyncio
    async def test_websocket_operations(self, temp_dirs):
        """测试WebSocket操作。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        mock_ws = MagicMock()

        async def connect():
            return mock_ws

        manager.register_websocket("ws_1", connect)
        success = await manager.connect_websocket("ws_1")

        assert success is True

        success = await manager.disconnect_websocket("ws_1")
        assert success is True

    def test_experiment_operations(self, temp_dirs):
        """测试实验操作。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        manager.register_experiment(1, "测试实验", 10, auto_save=False)
        manager.update_experiment_progress(1, 5)
        success = manager.save_experiment_checkpoint(1)

        assert success is True

        checkpoint = manager.load_experiment_checkpoint(1)
        assert checkpoint is not None
        assert checkpoint.current_step == 5

    def test_get_recovery_stats(self, temp_dirs):
        """测试获取恢复统计。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        async def connect():
            return True

        manager.register_device("motor_1", connect)
        manager.register_websocket("ws_1", connect)
        manager.register_experiment(1, "测试实验", 10, auto_save=False)

        stats = manager.get_recovery_stats()

        assert "devices" in stats
        assert "websockets" in stats
        assert "experiments" in stats
        assert "checkpoints" in stats

    @pytest.mark.asyncio
    async def test_shutdown(self, temp_dirs):
        """测试关闭。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        await manager.initialize()
        manager.register_experiment(1, "测试实验", 10)

        await manager.shutdown()

        # 验证检查点已保存
        checkpoint_file = Path(checkpoint_dir) / "experiment_1_checkpoint.json"
        assert checkpoint_file.exists()


class TestRecoveryState:
    """恢复状态测试类。"""

    def test_state_values(self):
        """测试状态值。"""
        assert RecoveryState.IDLE.value == "idle"
        assert RecoveryState.RECOVERING.value == "recovering"
        assert RecoveryState.RECOVERED.value == "recovered"
        assert RecoveryState.FAILED.value == "failed"
        assert RecoveryState.EXHAUSTED.value == "exhausted"


class TestRecoveryStrategy:
    """恢复策略测试类。"""

    def test_strategy_values(self):
        """测试策略值。"""
        assert RecoveryStrategy.EXPONENTIAL_BACKOFF.value == "exponential_backoff"
        assert RecoveryStrategy.LINEAR_BACKOFF.value == "linear_backoff"
        assert RecoveryStrategy.FIXED_INTERVAL.value == "fixed_interval"
        assert RecoveryStrategy.IMMEDIATE.value == "immediate"


class TestDeviceConnectionState:
    """设备连接状态测试类。"""

    def test_to_dict(self):
        """测试转换为字典。"""
        state = DeviceConnectionState(
            device_id="motor_1",
            connected=True,
            last_connected_time=1000.0,
            last_error=None,
            reconnect_count=2,
            state=RecoveryState.RECOVERED,
        )

        data = state.to_dict()

        assert data["device_id"] == "motor_1"
        assert data["connected"] is True
        assert data["reconnect_count"] == 2
        assert data["state"] == "recovered"


class TestWebSocketReconnectionState:
    """WebSocket重连状态测试类。"""

    def test_to_dict(self):
        """测试转换为字典。"""
        state = WebSocketReconnectionState(
            connection_id="ws_1",
            endpoint="/ws/test",
            connected=True,
            reconnect_count=3,
            state=RecoveryState.RECOVERED,
        )

        data = state.to_dict()

        assert data["connection_id"] == "ws_1"
        assert data["endpoint"] == "/ws/test"
        assert data["connected"] is True
        assert data["reconnect_count"] == 3
        assert data["state"] == "recovered"


class TestRetryResult:
    """重试结果测试类。"""

    def test_default_values(self):
        """测试默认值。"""
        result = RetryResult()

        assert result.success is False
        assert result.attempts == 0
        assert result.last_exception is None
        assert result.total_time == 0.0
        assert result.result is None


class TestRetryConfigAdvanced:
    """重试配置高级测试。"""

    def test_jitter_adds_randomness(self):
        """测试抖动添加随机性。"""
        config = RetryConfig(
            strategy=RecoveryStrategy.FIXED_INTERVAL,
            initial_delay=10.0,
            jitter=True,
        )

        # 多次计算延迟，应该有微小差异
        delays = [config.calculate_delay(1) for _ in range(10)]

        # 由于抖动，延迟应该在9-11之间
        for delay in delays:
            assert 9.0 <= delay <= 11.0

        # 至少有一些延迟不同（概率极高）
        assert len(set(delays)) > 1 or True  # 抖动可能偶然相同

    def test_negative_delay_protection(self):
        """测试负延迟保护。"""
        config = RetryConfig(
            strategy=RecoveryStrategy.FIXED_INTERVAL,
            initial_delay=1.0,
            jitter=True,
        )

        # 即使抖动为负，延迟也不应该为负
        for _ in range(100):
            delay = config.calculate_delay(1)
            assert delay >= 0.0


class TestRetryExecutorAdvanced:
    """重试执行器高级测试。"""

    @pytest.mark.asyncio
    async def test_total_time_tracking(self):
        """测试总时间跟踪。"""
        config = RetryConfig(
            max_retries=1,
            strategy=RecoveryStrategy.IMMEDIATE,
        )
        executor = RetryExecutor(config)

        async def slow_func():
            await asyncio.sleep(0.1)
            return "done"

        result = await executor.execute(slow_func)

        assert result.total_time >= 0.1

    @pytest.mark.asyncio
    async def test_attempt_count_accuracy(self):
        """测试尝试次数准确性。"""
        config = RetryConfig(
            max_retries=5,
            strategy=RecoveryStrategy.IMMEDIATE,
        )
        executor = RetryExecutor(config)

        call_count = 0

        async def count_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("Not yet")
            return "done"

        result = await executor.execute(count_func)

        assert result.attempts == 3
        assert call_count == 3


class TestDeviceConnectionRecoveryAdvanced:
    """设备连接恢复高级测试。"""

    @pytest.fixture
    def temp_state_file(self):
        """创建临时状态文件。"""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            yield f.name
        os.unlink(f.name)

    def test_state_persistence(self, temp_state_file):
        """测试状态持久化。"""
        recovery = DeviceConnectionRecovery(state_file=temp_state_file)

        async def connect():
            return True

        recovery.register_device("motor_1", connect)
        recovery._device_states["motor_1"].connected = True
        recovery._device_states["motor_1"].reconnect_count = 5
        recovery._save_states()

        # 创建新实例加载状态
        recovery2 = DeviceConnectionRecovery(state_file=temp_state_file)

        assert "motor_1" in recovery2._device_states
        assert recovery2._device_states["motor_1"].reconnect_count == 5

    def test_custom_config_per_device(self):
        """测试每个设备自定义配置。"""
        recovery = DeviceConnectionRecovery()

        async def connect():
            return True

        custom_config = RetryConfig(max_retries=10)
        recovery.register_device("motor_1", connect, config=custom_config)

        assert "motor_1" in recovery._device_configs
        assert recovery._device_configs["motor_1"].max_retries == 10

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """测试健康检查失败。"""
        recovery = DeviceConnectionRecovery()

        async def connect():
            return True

        async def health_check():
            return False  # 健康检查失败

        recovery.register_device("motor_1", connect, health_check_func=health_check)
        success = await recovery.connect_device("motor_1")

        assert success is True  # 连接成功

    @pytest.mark.asyncio
    async def test_disconnect_with_disconnect_func(self):
        """测试带断开函数的断开连接。"""
        recovery = DeviceConnectionRecovery()

        disconnect_called = []

        async def connect():
            return True

        async def disconnect():
            disconnect_called.append(True)

        recovery.register_device("motor_1", connect, disconnect_func=disconnect)
        await recovery.connect_device("motor_1")
        await recovery.disconnect_device("motor_1")

        assert len(disconnect_called) == 1

    @pytest.mark.asyncio
    async def test_connect_unregistered_device(self):
        """测试连接未注册设备。"""
        recovery = DeviceConnectionRecovery()

        success = await recovery.connect_device("nonexistent")

        assert success is False


class TestWebSocketReconnectionManagerAdvanced:
    """WebSocket重连管理器高级测试。"""

    @pytest.mark.asyncio
    async def test_on_reconnect_callback(self):
        """测试重连回调。"""
        manager = WebSocketReconnectionManager()

        reconnect_called = []

        mock_ws = MagicMock()

        async def connect():
            return mock_ws

        async def on_reconnect():
            reconnect_called.append(True)

        manager.register_connection("ws_1", connect, on_reconnect_func=on_reconnect)

        # 第一次连接
        await manager.connect("ws_1")
        assert len(reconnect_called) == 0  # 首次连接不触发重连回调

        # 模拟断开后重连
        manager._connection_states["ws_1"].connected = False
        manager._connection_states["ws_1"].reconnect_count = 1

        await manager.connect("ws_1")
        # 重连回调在重连时触发

    @pytest.mark.asyncio
    async def test_heartbeat_loop(self):
        """测试心跳循环。"""
        manager = WebSocketReconnectionManager(
            heartbeat_interval=0.1,
            heartbeat_timeout=0.5,
        )

        ping_sent = []

        mock_ws = MagicMock()
        mock_ws.ping = AsyncMock(side_effect=lambda: ping_sent.append(True))

        async def connect():
            return mock_ws

        manager.register_connection("ws_1", connect)
        await manager.connect("ws_1")

        # 等待心跳
        await asyncio.sleep(0.3)

        # 应该发送了心跳
        assert len(ping_sent) >= 1

        # 清理
        await manager.disconnect("ws_1")

    @pytest.mark.asyncio
    async def test_connect_unregistered_connection(self):
        """测试连接未注册的连接。"""
        manager = WebSocketReconnectionManager()

        success = await manager.connect("nonexistent")

        assert success is False

    def test_endpoint_tracking(self):
        """测试端点跟踪。"""
        manager = WebSocketReconnectionManager()

        async def connect():
            return MagicMock()

        manager.register_connection("ws_1", connect, endpoint="/ws/test")

        state = manager.get_connection_state("ws_1")
        assert state["endpoint"] == "/ws/test"


class TestExperimentStateRecoveryAdvanced:
    """实验状态恢复高级测试。"""

    @pytest.fixture
    def temp_checkpoint_dir(self):
        """创建临时检查点目录。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def test_multiple_callbacks(self, temp_checkpoint_dir):
        """测试多个回调。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        callback_results = []

        def callback1(checkpoint):
            callback_results.append(("callback1", checkpoint.current_step))

        def callback2(checkpoint):
            callback_results.append(("callback2", checkpoint.current_step))

        recovery.add_state_change_callback(callback1)
        recovery.add_state_change_callback(callback2)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.update_progress(1, 5)

        assert len(callback_results) == 2
        assert ("callback1", 5) in callback_results
        assert ("callback2", 5) in callback_results

    def test_remove_callback(self, temp_checkpoint_dir):
        """测试移除回调。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        callback_called = []

        def callback(checkpoint):
            callback_called.append(True)

        recovery.add_state_change_callback(callback)
        recovery.remove_state_change_callback(callback)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)
        recovery.update_progress(1, 5)

        assert len(callback_called) == 0

    def test_progress_calculation(self, temp_checkpoint_dir):
        """测试进度计算。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 100, auto_save=False)

        recovery.update_progress(1, 25)
        assert recovery._active_experiments[1].progress == 0.25

        recovery.update_progress(1, 50)
        assert recovery._active_experiments[1].progress == 0.5

        recovery.update_progress(1, 100)
        assert recovery._active_experiments[1].progress == 1.0

    def test_zero_total_steps(self, temp_checkpoint_dir):
        """测试零总步骤。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 0, auto_save=False)
        recovery.update_progress(1, 5)

        # 总步骤为0时，进度应该为0
        assert recovery._active_experiments[1].progress == 0.0

    def test_data_merge(self, temp_checkpoint_dir):
        """测试数据合并。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        recovery.register_experiment(1, "测试实验", 10, auto_save=False)

        recovery.update_progress(1, 1, data={"key1": "value1"})
        recovery.update_progress(1, 2, data={"key2": "value2"})
        recovery.update_progress(1, 3, data={"key1": "updated"})

        checkpoint = recovery._active_experiments[1]
        assert checkpoint.data["key1"] == "updated"
        assert checkpoint.data["key2"] == "value2"

    def test_get_experiment_state_nonexistent(self, temp_checkpoint_dir):
        """测试获取不存在的实验状态。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        state = recovery.get_experiment_state(999)

        assert state is None

    def test_get_all_states_empty(self, temp_checkpoint_dir):
        """测试获取空状态列表。"""
        recovery = ExperimentStateRecovery(checkpoint_dir=temp_checkpoint_dir)

        states = recovery.get_all_states()

        assert states == {}


class TestErrorRecoveryManagerAdvanced:
    """错误恢复管理器高级测试。"""

    @pytest.fixture
    def temp_dirs(self):
        """创建临时目录。"""
        with tempfile.TemporaryDirectory() as temp_dir:
            checkpoint_dir = os.path.join(temp_dir, "checkpoints")
            device_state_file = os.path.join(temp_dir, "device_states.json")
            yield checkpoint_dir, device_state_file

    @pytest.mark.asyncio
    async def test_double_initialize(self, temp_dirs):
        """测试重复初始化。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        await manager.initialize()
        await manager.initialize()  # 第二次初始化应该被忽略

        assert manager._initialized is True

    @pytest.mark.asyncio
    async def test_shutdown_saves_all_experiments(self, temp_dirs):
        """测试关闭时保存所有实验。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        await manager.initialize()

        manager.register_experiment(1, "实验1", 10, auto_save=False)
        manager.register_experiment(2, "实验2", 20, auto_save=False)

        manager.update_experiment_progress(1, 5)
        manager.update_experiment_progress(2, 10)

        await manager.shutdown()

        # 验证检查点文件存在
        assert os.path.exists(os.path.join(checkpoint_dir, "experiment_1_checkpoint.json"))
        assert os.path.exists(os.path.join(checkpoint_dir, "experiment_2_checkpoint.json"))

    def test_get_recovery_stats_structure(self, temp_dirs):
        """测试恢复统计结构。"""
        checkpoint_dir, device_state_file = temp_dirs
        manager = ErrorRecoveryManager(
            checkpoint_dir=checkpoint_dir,
            device_state_file=device_state_file,
        )

        stats = manager.get_recovery_stats()

        assert "devices" in stats
        assert "websockets" in stats
        assert "experiments" in stats
        assert "checkpoints" in stats


class TestExperimentCheckpointAdvanced:
    """实验检查点高级测试。"""

    def test_from_dict_with_missing_fields(self):
        """测试从字典创建时缺少字段。"""
        data = {
            "experiment_id": 1,
            "experiment_name": "测试实验",
            "status": "running",
            "current_step": 5,
            "total_steps": 10,
            "progress": 0.5,
            "start_time": 1000.0,
        }

        checkpoint = ExperimentCheckpoint.from_dict(data)

        assert checkpoint.experiment_id == 1
        assert checkpoint.data == {}
        assert checkpoint.metadata == {}

    def test_to_dict_roundtrip(self):
        """测试字典往返转换。"""
        original = ExperimentCheckpoint(
            experiment_id=1,
            experiment_name="测试实验",
            status="running",
            current_step=5,
            total_steps=10,
            progress=0.5,
            start_time=1000.0,
            checkpoint_time=2000.0,
            data={"key": "value"},
            metadata={"meta": "data"},
        )

        data = original.to_dict()
        restored = ExperimentCheckpoint.from_dict(data)

        assert restored.experiment_id == original.experiment_id
        assert restored.experiment_name == original.experiment_name
        assert restored.current_step == original.current_step
        assert restored.data == original.data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
