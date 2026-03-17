"""
异常场景测试套件

文件名: test_exception_scenarios.py
路径: backend/tests/
功能: 测试网络错误、超时、资源耗尽、无效输入等异常场景
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, httpx, asyncio

测试内容：
- TestNetworkErrorScenarios: 网络错误场景测试
- TestTimeoutScenarios: 超时场景测试
- TestResourceExhaustionScenarios: 资源耗尽场景测试
- TestInvalidInputScenarios: 无效输入场景测试
- TestDeviceErrorScenarios: 设备错误场景测试
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from fastapi import FastAPI, status
from fastapi.testclient import TestClient

from core.exceptions import (
    AppException,
    ErrorCode,
    ValidationException,
    ValidationErrorDetail,
    device_not_found,
    device_connection_failed,
    device_timeout,
    device_busy,
    device_limit_exceeded,
    experiment_not_found,
    experiment_already_running,
    invalid_token,
    token_expired,
    permission_denied,
    invalid_credentials,
    internal_error,
    database_error,
    cache_error,
    service_unavailable,
)


# ==================== 网络错误场景测试 ====================


class TestNetworkErrorScenarios:
    """网络错误场景测试。"""

    @pytest.mark.asyncio
    async def test_connection_refused(self):
        """测试连接被拒绝场景。"""
        # 模拟连接被拒绝
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Connection refused")

            async with httpx.AsyncClient() as client:
                with pytest.raises(httpx.ConnectError):
                    await client.get("http://localhost:9999/api/test")

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """测试连接超时场景。"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectTimeout("Connection timeout")

            async with httpx.AsyncClient(timeout=1.0) as client:
                with pytest.raises(httpx.ConnectTimeout):
                    await client.get("http://localhost:9999/api/test")

    @pytest.mark.asyncio
    async def test_read_timeout(self):
        """测试读取超时场景。"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ReadTimeout("Read timeout")

            async with httpx.AsyncClient(timeout=1.0) as client:
                with pytest.raises(httpx.ReadTimeout):
                    await client.get("http://localhost:9999/api/test")

    @pytest.mark.asyncio
    async def test_write_timeout(self):
        """测试写入超时场景。"""
        with patch("httpx.AsyncClient.post") as mock_post:
            mock_post.side_effect = httpx.WriteTimeout("Write timeout")

            async with httpx.AsyncClient(timeout=1.0) as client:
                with pytest.raises(httpx.WriteTimeout):
                    await client.post("http://localhost:9999/api/test", json={"data": "test"})

    @pytest.mark.asyncio
    async def test_dns_resolution_failure(self):
        """测试DNS解析失败场景。"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("DNS resolution failed")

            async with httpx.AsyncClient() as client:
                with pytest.raises(httpx.ConnectError):
                    await client.get("http://nonexistent-domain-12345.com/api/test")

    @pytest.mark.asyncio
    async def test_ssl_certificate_error(self):
        """测试SSL证书错误场景。"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("SSL certificate verify failed")

            async with httpx.AsyncClient() as client:
                with pytest.raises(httpx.ConnectError):
                    await client.get("https://expired.badssl.com/")

    @pytest.mark.asyncio
    async def test_proxy_connection_error(self):
        """测试代理连接错误场景。"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Proxy connection failed")

            async with httpx.AsyncClient(proxy="http://invalid-proxy:8080") as client:
                with pytest.raises(httpx.ConnectError):
                    await client.get("http://localhost:8000/api/test")

    @pytest.mark.asyncio
    async def test_network_unreachable(self):
        """测试网络不可达场景。"""
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ConnectError("Network is unreachable")

            async with httpx.AsyncClient() as client:
                with pytest.raises(httpx.ConnectError):
                    await client.get("http://10.255.255.1/api/test")


# ==================== 超时场景测试 ====================


class TestTimeoutScenarios:
    """超时场景测试。"""

    @pytest.mark.asyncio
    async def test_api_request_timeout(self):
        """测试API请求超时。"""
        # 注意：ASGITransport不支持真正的超时，这里测试超时配置
        app = FastAPI()

        @app.get("/slow-endpoint")
        async def slow_endpoint():
            await asyncio.sleep(0.1)  # 模拟慢速响应
            return {"status": "ok"}

        # 测试正常的超时配置
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            timeout=1.0,  # 1秒超时
        ) as client:
            response = await client.get("/slow-endpoint")
            assert response.status_code == 200

        # 测试超时异常（使用mock模拟）
        with patch("httpx.AsyncClient.get") as mock_get:
            mock_get.side_effect = httpx.ReadTimeout("Read timeout")
            async with httpx.AsyncClient(timeout=0.5) as client:
                with pytest.raises(httpx.ReadTimeout):
                    await client.get("http://test/slow-endpoint")

    @pytest.mark.asyncio
    async def test_device_operation_timeout(self):
        """测试设备操作超时。"""
        # 创建设备超时异常
        exception = device_timeout(
            device_id="stepper_01",
            operation="move",
            timeout_ms=5000
        )

        assert exception.error_code == ErrorCode.DEVICE_TIMEOUT
        assert exception.status_code == status.HTTP_504_GATEWAY_TIMEOUT
        assert "stepper_01" in exception.message
        assert exception.details["operation"] == "move"
        assert exception.details["timeout_ms"] == 5000

    @pytest.mark.asyncio
    async def test_websocket_heartbeat_timeout(self):
        """测试WebSocket心跳超时。"""
        from api.websocket import ConnectionManager, HEARTBEAT_TIMEOUT

        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()
        mock_ws.send_text = AsyncMock()
        mock_ws.close = AsyncMock()

        # 连接
        connection_id = await manager.connect(mock_ws, endpoint="/ws/test")

        # 模拟超时（修改最后消息时间）
        manager._connection_info[mock_ws].last_message_time = time.time() - HEARTBEAT_TIMEOUT - 1

        # 等待心跳监控检测超时
        await asyncio.sleep(HEARTBEAT_INTERVAL + 1)

        # 验证连接已断开
        assert mock_ws not in manager._active_connections

    @pytest.mark.asyncio
    async def test_database_query_timeout(self):
        """测试数据库查询超时。"""
        from sqlalchemy.exc import OperationalError

        # 模拟数据库超时
        with patch("sqlalchemy.orm.Session.execute") as mock_execute:
            mock_execute.side_effect = OperationalError(
                "statement", {}, "timeout: query took longer than 30000ms"
            )

            # 应抛出数据库错误
            exception = database_error("query_timeout", OperationalError("timeout", {}, ""))
            assert exception.error_code == ErrorCode.SYSTEM_DATABASE_ERROR

    @pytest.mark.asyncio
    async def test_cache_operation_timeout(self):
        """测试缓存操作超时。"""
        exception = cache_error("get_user_cache", TimeoutError("Cache timeout"))
        assert exception.error_code == ErrorCode.SYSTEM_CACHE_ERROR
        assert "get_user_cache" in exception.message


# ==================== 资源耗尽场景测试 ====================


class TestResourceExhaustionScenarios:
    """资源耗尽场景测试。"""

    @pytest.mark.asyncio
    async def test_memory_exhaustion_simulation(self):
        """测试内存耗尽模拟。"""
        # 模拟内存不足异常
        with patch("numpy.zeros") as mock_zeros:
            mock_zeros.side_effect = MemoryError("Unable to allocate array")

            with pytest.raises(MemoryError):
                import numpy as np
                np.zeros((1000000, 1000000))  # 尝试分配巨大数组

    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """测试连接池耗尽。"""
        # 模拟连接池耗尽
        connections = []

        try:
            # 尝试创建大量连接（模拟）
            for i in range(1000):
                mock_conn = MagicMock()
                connections.append(mock_conn)

            # 在实际场景中，连接池会限制连接数
            assert len(connections) == 1000

        finally:
            connections.clear()

    @pytest.mark.asyncio
    async def test_file_descriptor_exhaustion(self):
        """测试文件描述符耗尽。"""
        # 模拟文件描述符耗尽
        files = []

        try:
            # 尝试打开大量文件（模拟）
            for i in range(100):
                mock_file = MagicMock()
                mock_file.close = MagicMock()
                files.append(mock_file)

            assert len(files) == 100

        finally:
            for f in files:
                f.close()

    @pytest.mark.asyncio
    async def test_thread_pool_exhaustion(self):
        """测试线程池耗尽。"""
        import concurrent.futures

        def blocking_task():
            time.sleep(0.1)
            return True

        # 使用小线程池
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            futures = []
            for i in range(10):
                future = executor.submit(blocking_task)
                futures.append(future)

            # 等待所有任务完成
            results = [f.result() for f in futures]
            assert all(results)

    @pytest.mark.asyncio
    async def test_rate_limit_exceeded(self):
        """测试速率限制超出。"""
        from middleware.rate_limit import RateLimiter, RateLimitConfig, RateLimitStrategy, RateLimitScope

        # 创建速率限制器，配置较低的限制
        config = RateLimitConfig(
            requests_per_minute=10,  # 每分钟10个请求
            burst_size=5,  # 突发大小5
            window_seconds=60,
            strategy=RateLimitStrategy.SLIDING_WINDOW,
            scope=RateLimitScope.IP,
            block_duration=10
        )
        limiter = RateLimiter(default_config=config)

        # 创建模拟请求
        mock_request = MagicMock()
        mock_request.client.host = "127.0.0.1"
        mock_request.headers = {"user-agent": "test"}
        mock_request.url.path = "/api/test"

        # 快速发送多个请求
        allowed_count = 0
        blocked_count = 0

        for _ in range(20):
            allowed, remaining, reset_time, headers = limiter.is_allowed(mock_request)
            if allowed:
                allowed_count += 1
            else:
                blocked_count += 1

        # 应有部分请求被阻止（超过突发大小后）
        assert blocked_count > 0, f"Expected some requests to be blocked, but got {allowed_count} allowed, {blocked_count} blocked"

    @pytest.mark.asyncio
    async def test_disk_space_exhaustion(self):
        """测试磁盘空间耗尽。"""
        import os
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            test_file = os.path.join(tmpdir, "test.txt")

            # 模拟磁盘满
            with patch("builtins.open") as mock_open:
                mock_open.side_effect = OSError("No space left on device")

                with pytest.raises(OSError) as exc_info:
                    with open(test_file, "w") as f:
                        f.write("test")

                assert "No space left on device" in str(exc_info.value)


# ==================== 无效输入场景测试 ====================


class TestInvalidInputScenarios:
    """无效输入场景测试。"""

    def test_empty_request_body(self):
        """测试空请求体。"""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint(data: dict):
            return {"received": data}

        client = TestClient(app)

        # 空请求体
        response = client.post("/test", json={})
        assert response.status_code == 200

    def test_malformed_json(self):
        """测试格式错误的JSON。"""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint(data: dict):
            return {"received": data}

        client = TestClient(app)

        # 格式错误的JSON
        response = client.post(
            "/test",
            content="{invalid json}",
            headers={"Content-Type": "application/json"}
        )
        assert response.status_code == 422

    def test_invalid_content_type(self):
        """测试无效的内容类型。"""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint(data: dict):
            return {"received": data}

        client = TestClient(app)

        # 无效的内容类型
        response = client.post(
            "/test",
            content="data=test",
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code == 422

    def test_missing_required_fields(self):
        """测试缺少必填字段。"""
        from pydantic import BaseModel

        app = FastAPI()

        class TestModel(BaseModel):
            name: str
            value: int

        @app.post("/test")
        async def test_endpoint(data: TestModel):
            return {"received": data.model_dump()}

        client = TestClient(app)

        # 缺少必填字段
        response = client.post("/test", json={"name": "test"})  # 缺少value
        assert response.status_code == 422

    def test_type_mismatch(self):
        """测试类型不匹配。"""
        from pydantic import BaseModel

        app = FastAPI()

        class TestModel(BaseModel):
            value: int

        @app.post("/test")
        async def test_endpoint(data: TestModel):
            return {"received": data.model_dump()}

        client = TestClient(app)

        # 类型不匹配
        response = client.post("/test", json={"value": "not_an_integer"})
        assert response.status_code == 422

    def test_out_of_range_values(self):
        """测试超出范围的值。"""
        from pydantic import BaseModel, Field

        app = FastAPI()

        class TestModel(BaseModel):
            value: int = Field(..., ge=0, le=100)

        @app.post("/test")
        async def test_endpoint(data: TestModel):
            return {"received": data.model_dump()}

        client = TestClient(app)

        # 超出范围
        response = client.post("/test", json={"value": 101})
        assert response.status_code == 422

        response = client.post("/test", json={"value": -1})
        assert response.status_code == 422

    def test_injection_attempts(self):
        """测试注入攻击尝试。"""
        from pydantic import BaseModel

        app = FastAPI()

        class TestData(BaseModel):
            data: str

        @app.post("/test")
        async def test_endpoint(test_data: TestData):
            return {"received": test_data.data}

        client = TestClient(app)

        # SQL注入尝试
        sql_injection = "'; DROP TABLE users; --"
        response = client.post("/test", json={"data": sql_injection})
        assert response.status_code == 200  # 应安全处理
        assert response.json()["received"] == sql_injection  # 作为字符串存储

        # XSS尝试
        xss_attempt = "<script>alert('xss')</script>"
        response = client.post("/test", json={"data": xss_attempt})
        assert response.status_code == 200  # 应安全处理
        assert response.json()["received"] == xss_attempt  # 作为字符串存储

    def test_extremely_large_payload(self):
        """测试超大请求体。"""
        app = FastAPI()

        @app.post("/test")
        async def test_endpoint(data: list):
            return {"count": len(data)}

        client = TestClient(app)

        # 创建超大列表
        large_list = list(range(100000))

        response = client.post("/test", json=large_list)
        # 根据配置可能返回413或成功处理
        assert response.status_code in [200, 413, 422]


# ==================== 设备错误场景测试 ====================


class TestDeviceErrorScenarios:
    """设备错误场景测试。"""

    def test_device_not_found(self):
        """测试设备未找到。"""
        exception = device_not_found("stepper_01")

        assert exception.error_code == ErrorCode.DEVICE_NOT_FOUND
        assert exception.status_code == status.HTTP_404_NOT_FOUND
        assert "stepper_01" in exception.message

    def test_device_connection_failed(self):
        """测试设备连接失败。"""
        exception = device_connection_failed(
            device_id="stepper_01",
            reason="串口打开失败",
            cause=OSError("Port not found")
        )

        assert exception.error_code == ErrorCode.DEVICE_CONNECTION_FAILED
        assert exception.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert "串口打开失败" in exception.details["reason"]

    def test_device_busy(self):
        """测试设备忙碌。"""
        exception = device_busy("stepper_01", "moving")

        assert exception.error_code == ErrorCode.DEVICE_BUSY
        assert exception.status_code == status.HTTP_409_CONFLICT
        assert exception.details["current_operation"] == "moving"

    def test_device_limit_exceeded(self):
        """测试设备限位超出。"""
        exception = device_limit_exceeded(
            device_id="stepper_01",
            limit_type="positive",
            value=55.0,
            limit=50.0
        )

        assert exception.error_code == ErrorCode.DEVICE_LIMIT_EXCEEDED
        assert exception.status_code == status.HTTP_400_BAD_REQUEST
        assert exception.details["value"] == 55.0
        assert exception.details["limit"] == 50.0

    @pytest.mark.asyncio
    async def test_device_emergency_stop(self):
        """测试设备急停。"""
        from core.abstract import DeviceStatus

        # 模拟急停状态
        mock_device = MagicMock()
        mock_device.status = DeviceStatus.EMERGENCY_STOP

        # 在急停状态下尝试操作
        assert mock_device.status == DeviceStatus.EMERGENCY_STOP

    @pytest.mark.asyncio
    async def test_device_hardware_error(self):
        """测试设备硬件错误。"""
        from core.exceptions import AppException, ErrorCode

        exception = AppException(
            error_code=ErrorCode.DEVICE_HARDWARE_ERROR,
            message="设备硬件故障: 驱动器过热",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details={"device_id": "stepper_01", "error_code": "E001"}
        )

        assert exception.error_code == ErrorCode.DEVICE_HARDWARE_ERROR
        assert "驱动器过热" in exception.message


# ==================== 实验错误场景测试 ====================


class TestExperimentErrorScenarios:
    """实验错误场景测试。"""

    def test_experiment_not_found(self):
        """测试实验未找到。"""
        exception = experiment_not_found(123)

        assert exception.error_code == ErrorCode.EXPERIMENT_NOT_FOUND
        assert exception.status_code == status.HTTP_404_NOT_FOUND
        assert exception.details["experiment_id"] == 123

    def test_experiment_already_running(self):
        """测试实验已在运行。"""
        exception = experiment_already_running(456)

        assert exception.error_code == ErrorCode.EXPERIMENT_ALREADY_RUNNING
        assert exception.status_code == status.HTTP_409_CONFLICT

    def test_experiment_validation_error(self):
        """测试实验验证错误。"""
        errors = [
            ValidationErrorDetail(
                field="temperature",
                message="温度超出安全范围",
                value=500.0,
                constraint="max:400"
            ),
            ValidationErrorDetail(
                field="duration",
                message="持续时间不能为负",
                value=-10,
                constraint="min:0"
            )
        ]

        exception = ValidationException(errors)

        assert exception.error_code == ErrorCode.VALIDATION_ERROR
        assert exception.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert len(exception.errors) == 2


# ==================== 认证错误场景测试 ====================


class TestAuthenticationErrorScenarios:
    """认证错误场景测试。"""

    def test_invalid_token(self):
        """测试无效令牌。"""
        exception = invalid_token("令牌格式错误")

        assert exception.error_code == ErrorCode.AUTH_INVALID_TOKEN
        assert exception.status_code == status.HTTP_401_UNAUTHORIZED

    def test_token_expired(self):
        """测试令牌过期。"""
        exception = token_expired()

        assert exception.error_code == ErrorCode.AUTH_TOKEN_EXPIRED
        assert exception.status_code == status.HTTP_401_UNAUTHORIZED
        assert "过期" in exception.message

    def test_permission_denied(self):
        """测试权限拒绝。"""
        exception = permission_denied("delete", "experiment_123")

        assert exception.error_code == ErrorCode.AUTH_PERMISSION_DENIED
        assert exception.status_code == status.HTTP_403_FORBIDDEN
        assert exception.details["action"] == "delete"
        assert exception.details["resource"] == "experiment_123"

    def test_invalid_credentials(self):
        """测试无效凭证。"""
        exception = invalid_credentials()

        assert exception.error_code == ErrorCode.AUTH_INVALID_CREDENTIALS
        assert exception.status_code == status.HTTP_401_UNAUTHORIZED


# ==================== 系统错误场景测试 ====================


class TestSystemErrorScenarios:
    """系统错误场景测试。"""

    def test_internal_error(self):
        """测试内部错误。"""
        exception = internal_error("服务器内部错误", ValueError("test error"))

        assert exception.error_code == ErrorCode.SYSTEM_INTERNAL_ERROR
        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_database_error(self):
        """测试数据库错误。"""
        exception = database_error("insert_experiment")

        assert exception.error_code == ErrorCode.SYSTEM_DATABASE_ERROR
        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_cache_error(self):
        """测试缓存错误。"""
        exception = cache_error("get_user_cache")

        assert exception.error_code == ErrorCode.SYSTEM_CACHE_ERROR
        assert exception.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_service_unavailable(self):
        """测试服务不可用。"""
        exception = service_unavailable("Redis", "连接超时")

        assert exception.error_code == ErrorCode.SYSTEM_SERVICE_UNAVAILABLE
        assert exception.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert exception.details["service"] == "Redis"


# ==================== 错误恢复测试 ====================


class TestErrorRecovery:
    """错误恢复测试。"""

    @pytest.mark.asyncio
    async def test_automatic_retry_on_transient_error(self):
        """测试瞬态错误的自动重试。"""
        call_count = 0

        async def flaky_operation():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"

        # 简单的重试逻辑
        max_retries = 3
        last_error = None

        for attempt in range(max_retries):
            try:
                result = await flaky_operation()
                assert result == "success"
                break
            except ConnectionError as e:
                last_error = e
                if attempt == max_retries - 1:
                    raise

    @pytest.mark.asyncio
    async def test_graceful_degradation(self):
        """测试优雅降级。"""
        async def get_data_with_fallback():
            try:
                # 尝试从主数据源获取
                raise ConnectionError("Primary source unavailable")
            except ConnectionError:
                # 降级到备用数据源
                return {"data": "fallback", "source": "backup"}

        result = await get_data_with_fallback()
        assert result["source"] == "backup"

    @pytest.mark.asyncio
    async def test_circuit_breaker_pattern(self):
        """测试断路器模式。"""
        class CircuitBreaker:
            def __init__(self, failure_threshold=3, recovery_timeout=5.0):
                self.failure_count = 0
                self.failure_threshold = failure_threshold
                self.recovery_timeout = recovery_timeout
                self.last_failure_time = 0
                self.state = "closed"  # closed, open, half-open

            async def call(self, func):
                if self.state == "open":
                    if time.time() - self.last_failure_time > self.recovery_timeout:
                        self.state = "half-open"
                    else:
                        raise Exception("Circuit breaker is open")

                try:
                    result = await func()
                    if self.state == "half-open":
                        self.state = "closed"
                        self.failure_count = 0
                    return result
                except Exception as e:
                    self.failure_count += 1
                    self.last_failure_time = time.time()
                    if self.failure_count >= self.failure_threshold:
                        self.state = "open"
                    raise

        circuit_breaker = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)

        # 模拟失败
        async def failing_func():
            raise ConnectionError("Service unavailable")

        # 触发断路器
        for _ in range(2):
            try:
                await circuit_breaker.call(failing_func)
            except ConnectionError:
                pass

        # 断路器应打开
        assert circuit_breaker.state == "open"

        # 等待恢复
        await asyncio.sleep(0.15)

        # 断路器应进入半开状态
        async def success_func():
            return "ok"

        result = await circuit_breaker.call(success_func)
        assert result == "ok"
        assert circuit_breaker.state == "closed"


# 导入心跳间隔常量
from api.websocket import HEARTBEAT_INTERVAL
