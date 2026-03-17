"""
性能和压力测试套件

文件名: test_performance_stress.py
路径: backend/tests/
功能: 测试大数据量、并发请求、内存使用等性能场景
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, asyncio, numpy, psutil

测试内容：
- TestLargeDataPerformance: 大数据量性能测试
- TestConcurrentRequests: 并发请求测试
- TestMemoryUsage: 内存使用测试
- TestDatabasePerformance: 数据库性能测试
- TestWebSocketStress: WebSocket压力测试
"""

import asyncio
import gc
import time
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


# ==================== 大数据量性能测试 ====================


class TestLargeDataPerformance:
    """大数据量性能测试。"""

    def test_large_array_processing(self):
        """测试大数组处理性能。"""
        # 创建大数组
        large_array = np.random.rand(1000000)

        start_time = time.time()

        # 执行计算
        mean = np.mean(large_array)
        std = np.std(large_array)
        max_val = np.max(large_array)
        min_val = np.min(large_array)

        elapsed = time.time() - start_time

        # 应在1秒内完成
        assert elapsed < 1.0, f"Large array processing took {elapsed:.3f}s"
        assert isinstance(mean, float)
        assert isinstance(std, float)

    def test_large_dataset_storage(self, temp_storage):
        """测试大数据集存储性能。"""
        # 创建大量数据记录
        user_id = temp_storage.create_user(
            username="perf_test_user",
            password_hash="hash",
            role="operator"
        )

        exp_id = temp_storage.create_experiment(
            exp_name="性能测试实验",
            exp_type="performance",
            user_id=user_id
        )

        start_time = time.time()

        # 插入10000条记录
        for i in range(10000):
            temp_storage.add_data_record(
                experiment_id=exp_id,
                position_steps=i,
                position_mm=i * 0.001,
                field_value=i * 0.1,
                current_value=i * 0.01
            )

        elapsed = time.time() - start_time

        # 应在10秒内完成
        assert elapsed < 10.0, f"Inserting 10000 records took {elapsed:.3f}s"

    def test_large_json_serialization(self):
        """测试大JSON序列化性能。"""
        import json

        # 创建大型数据结构
        large_data = {
            "experiment_id": 1,
            "data_points": [
                {
                    "timestamp": f"2026-03-16T10:00:{i:02d}",
                    "position": i * 0.1,
                    "field": i * 0.01,
                    "current": i * 0.001
                }
                for i in range(10000)
            ]
        }

        start_time = time.time()

        # 序列化
        json_str = json.dumps(large_data)

        # 反序列化
        parsed = json.loads(json_str)

        elapsed = time.time() - start_time

        # 应在1秒内完成
        assert elapsed < 1.0, f"JSON serialization took {elapsed:.3f}s"
        assert len(parsed["data_points"]) == 10000

    def test_waveform_data_throughput(self):
        """测试波形数据吞吐量。"""
        from api.websocket import WaveformData, WaveformDataPoint, DeviceType

        # 创建大量波形数据点
        data_points = [
            WaveformDataPoint(
                channel=i % 4,
                value=np.random.rand() * 100,
                timestamp=time.time() + i * 0.001
            )
            for i in range(10000)
        ]

        start_time = time.time()

        # 创建波形数据对象
        waveform = WaveformData(
            device_id="ammeter_01",
            device_type=DeviceType.AMMETER,
            sample_rate=10000.0,
            data_points=data_points
        )

        # 序列化
        data_dict = waveform.to_dict()

        elapsed = time.time() - start_time

        # 应在500ms内完成
        assert elapsed < 0.5, f"Waveform processing took {elapsed:.3f}s"
        assert len(data_dict["data_points"]) == 10000


# ==================== 并发请求测试 ====================


class TestConcurrentRequests:
    """并发请求测试。"""

    @pytest.mark.asyncio
    async def test_concurrent_api_requests(self):
        """测试并发API请求。"""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/test/{item_id}")
        async def get_item(item_id: int):
            await asyncio.sleep(0.01)  # 模拟处理时间
            return {"item_id": item_id, "status": "ok"}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            start_time = time.time()

            # 并发发送100个请求
            tasks = [
                client.get(f"/api/test/{i}")
                for i in range(100)
            ]

            responses = await asyncio.gather(*tasks)

            elapsed = time.time() - start_time

            # 并发应比顺序执行快
            assert elapsed < 2.0, f"100 concurrent requests took {elapsed:.3f}s"
            assert all(r.status_code == 200 for r in responses)

    @pytest.mark.asyncio
    async def test_concurrent_device_operations(self):
        """测试并发设备操作。"""
        from core.dm2c_driver import LeadshineDM2C
        from core.abstract import DeviceStatus

        # 创建多个模拟设备
        devices = []
        for i in range(10):
            device = MagicMock(spec=LeadshineDM2C)
            device.device_id = f"motor_{i}"
            device.status = DeviceStatus.READY
            device.move_abs = AsyncMock(return_value=True)
            devices.append(device)

        start_time = time.time()

        # 并发执行移动操作
        tasks = [device.move_abs(i * 10.0) for i, device in enumerate(devices)]
        results = await asyncio.gather(*tasks)

        elapsed = time.time() - start_time

        assert all(results)
        assert elapsed < 1.0

    @pytest.mark.asyncio
    async def test_concurrent_database_operations(self, test_db_session):
        """测试并发数据库操作。"""
        from models.device import Device

        async def create_device(i):
            device = Device(
                device_id=f"device_{i}",
                device_type="stepper",
                status="ready"
            )
            test_db_session.add(device)
            return device

        start_time = time.time()

        # 并发创建设备
        tasks = [create_device(i) for i in range(100)]
        devices = await asyncio.gather(*tasks)

        test_db_session.commit()

        elapsed = time.time() - start_time

        assert len(devices) == 100
        assert elapsed < 5.0

    @pytest.mark.asyncio
    async def test_rate_limiting_under_load(self):
        """测试负载下的速率限制。"""
        from middleware.rate_limit import RateLimiter

        limiter = RateLimiter(requests_per_second=100)
        client_id = "stress_test_client"

        start_time = time.time()
        allowed_count = 0
        blocked_count = 0

        # 发送1000个请求
        for _ in range(1000):
            if await limiter.is_allowed(client_id):
                allowed_count += 1
            else:
                blocked_count += 1

        elapsed = time.time() - start_time

        # 应有部分请求被阻止
        assert blocked_count > 0
        # 速率限制应正常工作
        assert allowed_count <= 150  # 允许一些突发


# ==================== 内存使用测试 ====================


class TestMemoryUsage:
    """内存使用测试。"""

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_memory_usage_large_dataset(self):
        """测试大数据集内存使用。"""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # 创建大型数据集
        large_datasets = []
        for _ in range(100):
            dataset = np.random.rand(10000, 100)
            large_datasets.append(dataset)

        peak_memory = process.memory_info().rss / 1024 / 1024

        # 清理
        large_datasets.clear()
        gc.collect()

        final_memory = process.memory_info().rss / 1024 / 1024

        # 内存应被正确释放
        memory_leaked = final_memory - initial_memory
        assert memory_leaked < 100, f"Potential memory leak: {memory_leaked:.2f} MB"

    @pytest.mark.skipif(not PSUTIL_AVAILABLE, reason="psutil not available")
    def test_cache_memory_limit(self):
        """测试缓存内存限制。"""
        from core.cache.local_cache import LocalCache

        cache = LocalCache(max_size_mb=10)

        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024

        # 填充缓存
        for i in range(10000):
            cache.set(f"key_{i}", "x" * 1000)  # 1KB per entry

        peak_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = peak_memory - initial_memory

        # 内存增长应受限
        assert memory_increase < 50, f"Cache exceeded memory limit: {memory_increase:.2f} MB"

    @pytest.mark.asyncio
    async def test_websocket_message_queue_memory(self):
        """测试WebSocket消息队列内存。"""
        from api.websocket import ConnectionManager

        manager = ConnectionManager()

        # 创建连接
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        await manager.connect(mock_ws)

        # 发送大量消息
        for i in range(10000):
            await manager.send_personal_message(f"message_{i}" * 100, mock_ws)

        backpressure_state = manager._connection_info[mock_ws].backpressure_state

        # 队列应有大小限制
        assert len(backpressure_state.message_queue) <= 100

        manager.disconnect(mock_ws)


# ==================== 数据库性能测试 ====================


class TestDatabasePerformance:
    """数据库性能测试。"""

    def test_bulk_insert_performance(self, test_db_session):
        """测试批量插入性能。"""
        from models.experiment import Experiment
        from models.user import User

        # 创建用户
        user = User(
            username="perf_user",
            password_hash="hash",
            role="operator"
        )
        test_db_session.add(user)
        test_db_session.commit()

        start_time = time.time()

        # 批量插入实验
        experiments = [
            Experiment(
                name=f"Experiment_{i}",
                type="test",
                user_id=user.id
            )
            for i in range(1000)
        ]

        test_db_session.add_all(experiments)
        test_db_session.commit()

        elapsed = time.time() - start_time

        # 应在5秒内完成
        assert elapsed < 5.0, f"Bulk insert took {elapsed:.3f}s"

    def test_query_performance_with_index(self, test_db_session):
        """测试带索引的查询性能。"""
        from models.device import Device

        # 创建设备
        for i in range(10000):
            device = Device(
                device_id=f"device_{i:05d}",
                device_type="stepper",
                status="ready"
            )
            test_db_session.add(device)

        test_db_session.commit()

        start_time = time.time()

        # 查询特定设备
        for _ in range(100):
            device = test_db_session.query(Device).filter(
                Device.device_id == "device_05000"
            ).first()
            assert device is not None

        elapsed = time.time() - start_time

        # 100次查询应在1秒内完成
        assert elapsed < 1.0, f"100 queries took {elapsed:.3f}s"

    def test_complex_query_performance(self, test_db_session):
        """测试复杂查询性能。"""
        from models.experiment import Experiment
        from models.user import User
        from sqlalchemy import func

        # 创建测试数据
        user = User(username="complex_user", password_hash="hash", role="operator")
        test_db_session.add(user)
        test_db_session.commit()

        for i in range(1000):
            exp = Experiment(
                name=f"Exp_{i}",
                type="test" if i % 2 == 0 else "production",
                user_id=user.id
            )
            test_db_session.add(exp)

        test_db_session.commit()

        start_time = time.time()

        # 复杂聚合查询
        result = test_db_session.query(
            Experiment.type,
            func.count(Experiment.id)
        ).group_by(Experiment.type).all()

        elapsed = time.time() - start_time

        assert len(result) == 2
        assert elapsed < 0.5


# ==================== WebSocket压力测试 ====================


class TestWebSocketStress:
    """WebSocket压力测试。"""

    @pytest.mark.asyncio
    async def test_many_concurrent_connections(self):
        """测试大量并发连接。"""
        from api.websocket import ConnectionManager

        manager = ConnectionManager()

        connections = []
        start_time = time.time()

        # 创建100个连接
        for i in range(100):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            connection_id = await manager.connect(mock_ws, endpoint=f"/ws/test{i}")
            connections.append(mock_ws)

        elapsed = time.time() - start_time

        assert manager.connection_count == 100
        assert elapsed < 5.0, f"Creating 100 connections took {elapsed:.3f}s"

        # 清理
        for ws in connections:
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_high_frequency_messages(self):
        """测试高频消息处理。"""
        from api.websocket import ConnectionManager, create_device_status_message, DeviceType

        manager = ConnectionManager()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        await manager.connect(mock_ws)

        start_time = time.time()
        message_count = 0

        # 发送1000条消息
        for i in range(1000):
            msg = create_device_status_message(
                device_id=f"device_{i}",
                device_type=DeviceType.STEPPER,
                status="ready"
            )
            await manager.broadcast(msg)
            message_count += 1

        elapsed = time.time() - start_time

        # 应在5秒内完成
        assert elapsed < 5.0, f"Sending 1000 messages took {elapsed:.3f}s"
        assert message_count == 1000

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_backpressure_under_load(self):
        """测试负载下的反压控制。"""
        from api.websocket import (
            ConnectionManager,
            BACKPRESSURE_QUEUE_SIZE,
            create_device_status_message,
            DeviceType
        )

        manager = ConnectionManager()

        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        await manager.connect(mock_ws)

        backpressure_state = manager._connection_info[mock_ws].backpressure_state

        # 快速发送超过队列容量的消息
        for i in range(BACKPRESSURE_QUEUE_SIZE * 2):
            msg = create_device_status_message(
                device_id=f"device_{i}",
                device_type=DeviceType.STEPPER,
                status="ready"
            )
            await manager.broadcast(msg)

        # 应有消息被丢弃
        assert backpressure_state.total_messages_dropped > 0

        # 队列不应超过最大容量
        assert len(backpressure_state.message_queue) <= BACKPRESSURE_QUEUE_SIZE

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_message_throughput(self):
        """测试消息吞吐量。"""
        from api.websocket import (
            ConnectionManager,
            create_waveform_message,
            DeviceType
        )

        manager = ConnectionManager()

        # 创建多个连接
        connections = []
        for i in range(10):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            await manager.connect(mock_ws)
            connections.append(mock_ws)

        # 准备波形数据
        data_points = [
            {"channel": 0, "value": i * 0.1, "timestamp": time.time()}
            for i in range(100)
        ]

        start_time = time.time()
        message_count = 0

        # 发送消息持续5秒
        while time.time() - start_time < 5.0:
            msg = create_waveform_message(
                device_id="ammeter_01",
                device_type=DeviceType.AMMETER,
                sample_rate=1000.0,
                data_points=data_points
            )
            await manager.broadcast(msg)
            message_count += 1

        elapsed = time.time() - start_time

        # 计算吞吐量
        throughput = message_count / elapsed

        # 应达到至少100条/秒
        assert throughput >= 100, f"Throughput too low: {throughput:.1f} msg/s"

        # 清理
        for ws in connections:
            manager.disconnect(ws)


# ==================== 基准测试 ====================


class TestBenchmarks:
    """基准测试。"""

    def test_validation_benchmark(self):
        """验证函数基准测试。"""
        from schemas.validators import validate_device_id, validate_position

        iterations = 10000

        # 设备ID验证基准
        start_time = time.time()
        for i in range(iterations):
            validate_device_id(f"device_{i:05d}")
        device_id_time = time.time() - start_time

        # 位置验证基准
        start_time = time.time()
        for i in range(iterations):
            validate_position(i * 0.1 - 500)
        position_time = time.time() - start_time

        # 每次验证应在0.1ms内
        assert device_id_time / iterations < 0.0001
        assert position_time / iterations < 0.0001

    def test_serialization_benchmark(self):
        """序列化基准测试。"""
        import json
        import msgpack

        data = {
            "device_id": "test_device",
            "status": "ready",
            "position": 100.5,
            "velocity": 10.0,
            "timestamp": time.time()
        }

        iterations = 10000

        # JSON序列化基准
        start_time = time.time()
        for _ in range(iterations):
            json.dumps(data)
        json_time = time.time() - start_time

        # MessagePack序列化基准
        start_time = time.time()
        for _ in range(iterations):
            msgpack.packb(data, use_bin_type=True)
        msgpack_time = time.time() - start_time

        # MessagePack应比JSON快
        assert msgpack_time < json_time

    @pytest.mark.asyncio
    async def test_api_response_time_benchmark(self):
        """API响应时间基准测试。"""
        from fastapi import FastAPI
        from httpx import ASGITransport, AsyncClient

        app = FastAPI()

        @app.get("/api/benchmark")
        async def benchmark_endpoint():
            return {"status": "ok", "timestamp": time.time()}

        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test"
        ) as client:
            iterations = 1000
            response_times = []

            for _ in range(iterations):
                start_time = time.time()
                response = await client.get("/api/benchmark")
                response_time = time.time() - start_time
                response_times.append(response_time)

            avg_response_time = sum(response_times) / len(response_times)
            max_response_time = max(response_times)
            p95_response_time = sorted(response_times)[int(len(response_times) * 0.95)]

            # 平均响应时间应小于10ms
            assert avg_response_time < 0.01
            # P95响应时间应小于50ms
            assert p95_response_time < 0.05
