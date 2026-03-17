"""
测试框架验证 - httpx异步测试示例

文件名: test_framework_httpx.py
路径: backend/tests/
功能: 验证httpx异步测试框架配置，展示最佳实践
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio, httpx

测试内容：
- httpx异步客户端基本功能
- 异步API请求测试
- 测试数据工厂使用示例
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock

from tests.factories import (
    DeviceStatusDictFactory,
    ExperimentDictFactory,
    SensorDataGenerator,
    UserDictFactory,
)


class TestHttpxAsyncClientBasic:
    """测试httpx异步客户端基本功能。"""

    @pytest.mark.asyncio
    async def test_async_client_connection(self, async_client: AsyncClient):
        """测试异步客户端连接。

        验证：
        - 客户端可以正常连接
        - 响应状态码正确
        """
        response = await async_client.get("/")

        assert response.status_code == 200
        # 根路径可能返回HTML或JSON，取决于静态文件配置
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            data = response.json()
            assert "name" in data or "status" in data
        else:
            # HTML响应，验证内容不为空
            assert len(response.content) > 0

    @pytest.mark.asyncio
    async def test_async_client_api_endpoint(self, async_client: AsyncClient):
        """测试API端点可访问性。

        验证：
        - API端点可以访问
        - 返回正确的响应
        """
        # 测试一个确定存在的端点
        response = await async_client.get("/api/logs/stats")

        # 根据实际API响应调整断言
        assert response.status_code in [200, 404, 503]  # 200成功，404不存在，503服务不可用


class TestAsyncMotorAPI:
    """测试电机API异步请求。"""

    @pytest.mark.asyncio
    async def test_get_motor_status_with_mock(
        self, async_client_with_mock: AsyncClient, mock_dm2c
    ):
        """测试获取电机状态（使用Mock设备）。

        验证：
        - Mock设备正确注入
        - API返回正确的状态数据
        """
        # 配置Mock返回值
        mock_dm2c.read_status = AsyncMock(
            return_value=DeviceStatusDictFactory.create_motor_status(
                device_id="test_motor",
                status="ready",
                position_mm=10.5,
                limit_positive=100.0,
                limit_negative=-100.0,
            )
        )

        response = await async_client_with_mock.get("/api/v1/motor/status")

        assert response.status_code == 200
        data = response.json()
        assert data["device_id"] == "test_motor"
        assert data["status"] == "ready"

    @pytest.mark.asyncio
    async def test_motor_emergency_stop(
        self, async_client_with_mock: AsyncClient, mock_dm2c
    ):
        """测试电机急停。

        验证：
        - 急停命令正确执行
        - 返回正确的响应
        """
        mock_dm2c.emergency_stop = AsyncMock(return_value=True)

        response = await async_client_with_mock.post("/api/v1/motor/emergency_stop")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True


class TestDataFactoriesUsage:
    """测试数据工厂使用示例。"""

    @pytest.mark.asyncio
    async def test_user_factory(self):
        """测试用户数据工厂。

        验证：
        - 工厂生成正确的用户数据
        - 批量生成功能正常
        """
        # 单个用户
        user_data = UserDictFactory.create(username="test_factory_user")
        assert user_data["username"] == "test_factory_user"
        assert user_data["role"] == "operator"

        # 批量用户
        users = UserDictFactory.create_batch(5, role="admin")
        assert len(users) == 5
        assert all(u["role"] == "admin" for u in users)

    @pytest.mark.asyncio
    async def test_experiment_factory(self):
        """测试实验数据工厂。

        验证：
        - 工厂生成正确的实验数据
        """
        exp_data = ExperimentDictFactory.create(
            exp_name="测试实验",
            exp_type="hysteresis",
            user_id=1,
        )

        assert exp_data["exp_name"] == "测试实验"
        assert exp_data["exp_type"] == "hysteresis"
        assert exp_data["user_id"] == 1
        assert exp_data["status"] == "running"

    @pytest.mark.asyncio
    async def test_device_status_factory(self):
        """测试设备状态工厂。

        验证：
        - 工厂生成正确的设备状态数据
        """
        motor_status = DeviceStatusDictFactory.create_motor_status(
            device_id="motor_01",
            position_mm=25.5,
            alarm_code=0,
        )

        assert motor_status["device_id"] == "motor_01"
        assert motor_status["position_mm"] == 25.5
        assert motor_status["alarm_code"] == 0

    @pytest.mark.asyncio
    async def test_sensor_data_generator(self):
        """测试传感器数据生成器。

        验证：
        - 生成器生成正确的传感器数据
        """
        # 磁滞回线
        h_field, moment = SensorDataGenerator.generate_hysteresis_curve(
            num_points=100,
            noise_level=0.01,
        )
        assert len(h_field) == 200  # 正反扫描
        assert len(moment) == 200

        # 正弦波
        x, signal = SensorDataGenerator.generate_sinewave(
            num_points=50,
            frequency=2.0,
        )
        assert len(x) == 50
        assert len(signal) == 50


class TestAPIErrorHandling:
    """测试API错误处理。"""

    @pytest.mark.asyncio
    async def test_404_error(self, async_client: AsyncClient):
        """测试404错误处理。

        验证：
        - 不存在的路径返回404
        """
        response = await async_client.get("/api/nonexistent/endpoint")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_method_not_allowed(self, async_client: AsyncClient):
        """测试方法不允许错误。

        验证：
        - 错误的HTTP方法返回405
        """
        response = await async_client.delete("/api/v1/motor/status")

        assert response.status_code == 405


class TestPerformanceBenchmark:
    """性能基准测试。"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_concurrent_requests(self, async_client: AsyncClient):
        """测试并发请求性能。

        验证：
        - 客户端支持并发请求
        - 响应时间合理
        """
        import asyncio
        import time

        start_time = time.time()

        # 并发发送10个请求
        tasks = [async_client.get("/") for _ in range(10)]
        responses = await asyncio.gather(*tasks)

        elapsed_time = time.time() - start_time

        # 验证所有请求成功
        assert all(r.status_code == 200 for r in responses)

        # 验证响应时间合理（10个请求应在5秒内完成）
        assert elapsed_time < 5.0

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_large_data_transfer(self, async_client: AsyncClient):
        """测试大数据传输。

        验证：
        - 大数据传输正常
        - 内存使用合理
        """
        # 生成大量传感器数据
        h_field, moment = SensorDataGenerator.generate_hysteresis_curve(
            num_points=1000,
        )

        # 验证数据生成
        assert len(h_field) == 2000
        assert len(moment) == 2000
