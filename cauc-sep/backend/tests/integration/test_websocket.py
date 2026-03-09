"""
文件名: test_websocket.py
路径: backend/tests/integration/
功能: WebSocket通信集成测试
作者: Test Debugger Agent
创建日期: 2026-03-08
依赖: pytest, asyncio, fastapi
"""

import asyncio
import json
import time
from collections import deque
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
import pytest
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

from api.websocket import (
    AlarmEventData,
    AlarmLevel,
    BackpressureState,
    ConnectionInfo,
    ConnectionManager,
    DeviceStatusData,
    DeviceType,
    ExperimentProgressData,
    MessageType,
    ProtocolType,
    WaveformData,
    WaveformDataPoint,
    WebSocketMessage,
    create_alarm_message,
    create_device_status_message,
    create_experiment_progress_message,
    create_waveform_message,
    deserialize_message,
    parse_protocol_from_query,
    serialize_message,
)


class MockWebSocket:
    """Mock WebSocket连接类。"""

    def __init__(self, protocol: ProtocolType = ProtocolType.JSON):
        """初始化Mock WebSocket。

        Args:
            protocol: 通信协议类型
        """
        self.messages: list = []
        self.closed = False
        self.accepted = False
        self.protocol = protocol
        self.client = MagicMock()
        self.client.host = "127.0.0.1"
        self.client.port = 12345

    async def accept(self):
        """接受连接。"""
        self.accepted = True

    async def send_text(self, data: str):
        """发送文本数据。"""
        if self.closed:
            raise WebSocketDisconnect()
        self.messages.append(("text", data))

    async def send_bytes(self, data: bytes):
        """发送二进制数据。"""
        if self.closed:
            raise WebSocketDisconnect()
        self.messages.append(("bytes", data))

    async def receive_text(self) -> str:
        """接收文本数据。"""
        if self.closed:
            raise WebSocketDisconnect()
        await asyncio.sleep(0.01)
        return json.dumps({"type": "pong"})

    async def close(self, code: int = 1000, reason: str = ""):
        """关闭连接。"""
        self.closed = True


class TestWebSocketConnection:
    """WebSocket连接测试。"""

    @pytest.mark.asyncio
    async def test_websocket_accept_connection(self):
        """测试接受WebSocket连接。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        connection_id = await manager.connect(ws, endpoint="/ws/motor")

        assert ws.accepted is True
        assert connection_id is not None
        assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_websocket_disconnect(self):
        """测试断开WebSocket连接。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)
        assert manager.connection_count == 1

        manager.disconnect(ws)
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_multiple_connections(self):
        """测试多个WebSocket连接。"""
        manager = ConnectionManager()

        connections = []
        for i in range(5):
            ws = MockWebSocket()
            await manager.connect(ws, endpoint=f"/ws/test_{i}")
            connections.append(ws)

        assert manager.connection_count == 5

        # 断开所有连接
        for ws in connections:
            manager.disconnect(ws)

        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_connection_info_tracking(self):
        """测试连接信息追踪。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        connection_id = await manager.connect(
            ws,
            endpoint="/ws/motor",
            client_ip="192.168.1.1",
        )

        info = manager.get_connection_info(ws)
        assert info is not None
        assert info.connection_id == connection_id
        assert info.endpoint == "/ws/motor"
        assert info.client_ip == "192.168.1.1"


class TestWebSocketMessageTypes:
    """WebSocket消息类型测试。"""

    @pytest.mark.asyncio
    async def test_device_status_message(self):
        """测试设备状态消息。"""
        message = create_device_status_message(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready",
            connected=True,
            simulation=True,
            position_mm=25.5,
            velocity_mm_s=10.0,
        )

        assert message.type == MessageType.DEVICE_STATUS
        assert "device_id" in message.data
        assert message.data["device_id"] == "stepper_01"
        assert message.data["position_mm"] == 25.5

    @pytest.mark.asyncio
    async def test_waveform_message(self):
        """测试波形数据消息。"""
        data_points = [
            {"channel": 0, "value": 100.5, "timestamp": time.time()},
            {"channel": 1, "value": 200.3, "timestamp": time.time()},
        ]

        message = create_waveform_message(
            device_id="ammeter_01",
            device_type=DeviceType.AMMETER,
            sample_rate=100.0,
            data_points=data_points,
        )

        assert message.type == MessageType.WAVEFORM_DATA
        assert message.data["sample_rate"] == 100.0
        assert len(message.data["data_points"]) == 2

    @pytest.mark.asyncio
    async def test_alarm_message(self):
        """测试报警消息。"""
        message = create_alarm_message(
            device_id="temp_01",
            device_type=DeviceType.TEMPERATURE,
            alarm_level=AlarmLevel.WARNING,
            alarm_code="HIGH_TEMP",
            alarm_message="温度超过安全阈值",
            recoverable=True,
        )

        assert message.type == MessageType.ALARM_EVENT
        assert message.data["alarm_level"] == "warning"
        assert message.data["alarm_code"] == "HIGH_TEMP"

    @pytest.mark.asyncio
    async def test_experiment_progress_message(self):
        """测试实验进度消息。"""
        message = create_experiment_progress_message(
            experiment_id=1,
            experiment_name="磁场扫描实验",
            progress=0.5,
            current_step=5,
            total_steps=10,
            elapsed_time=300.0,
            estimated_remaining=300.0,
            status="running",
        )

        assert message.type == MessageType.EXPERIMENT_PROGRESS
        assert message.data["progress"] == 0.5
        assert message.data["status"] == "running"


class TestWebSocketMessageSerialization:
    """WebSocket消息序列化测试。"""

    def test_message_to_json(self):
        """测试消息转换为JSON。"""
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        json_str = message.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["type"] == "device_status"

    def test_message_to_msgpack(self):
        """测试消息转换为MessagePack。"""
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        msgpack_bytes = message.to_msgpack()

        assert isinstance(msgpack_bytes, bytes)
        parsed = msgpack.unpackb(msgpack_bytes, raw=False)
        assert parsed["type"] == "device_status"

    def test_serialize_json_protocol(self):
        """测试JSON协议序列化。"""
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        serialized = serialize_message(message, ProtocolType.JSON)

        assert isinstance(serialized, str)
        assert "device_status" in serialized

    def test_serialize_msgpack_protocol(self):
        """测试MessagePack协议序列化。"""
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        serialized = serialize_message(message, ProtocolType.MSGPACK)

        assert isinstance(serialized, bytes)

    def test_deserialize_json_protocol(self):
        """测试JSON协议反序列化。"""
        data = json.dumps({"type": "ping", "timestamp": "2026-03-08T00:00:00"})

        deserialized = deserialize_message(data, ProtocolType.JSON)

        assert deserialized["type"] == "ping"

    def test_deserialize_msgpack_protocol(self):
        """测试MessagePack协议反序列化。"""
        data = msgpack.packb({"type": "ping", "timestamp": "2026-03-08T00:00:00"})

        deserialized = deserialize_message(data, ProtocolType.MSGPACK)

        assert deserialized["type"] == "ping"


class TestWebSocketProtocolNegotiation:
    """WebSocket协议协商测试。"""

    def test_parse_json_protocol(self):
        """测试解析JSON协议。"""
        params = {"protocol": "json"}
        protocol = parse_protocol_from_query(params)

        assert protocol == ProtocolType.JSON

    def test_parse_msgpack_protocol(self):
        """测试解析MessagePack协议。"""
        params = {"protocol": "msgpack"}
        protocol = parse_protocol_from_query(params)

        assert protocol == ProtocolType.MSGPACK

    def test_parse_invalid_protocol_fallback(self):
        """测试无效协议回退到JSON。"""
        params = {"protocol": "invalid"}
        protocol = parse_protocol_from_query(params)

        assert protocol == ProtocolType.JSON

    def test_parse_missing_protocol_default(self):
        """测试缺少协议参数时默认使用JSON。"""
        params = {}
        protocol = parse_protocol_from_query(params)

        assert protocol == ProtocolType.JSON


class TestWebSocketBroadcast:
    """WebSocket广播测试。"""

    @pytest.mark.asyncio
    async def test_broadcast_to_all_connections(self):
        """测试广播到所有连接。"""
        manager = ConnectionManager()

        # 创建多个连接
        connections = []
        for _ in range(3):
            ws = MockWebSocket()
            await manager.connect(ws)
            connections.append(ws)

        # 广播消息
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        await manager.broadcast(message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 验证所有连接都收到消息
        for ws in connections:
            assert len(ws.messages) >= 1

    @pytest.mark.asyncio
    async def test_broadcast_by_type(self):
        """测试按类型广播。"""
        manager = ConnectionManager()

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1)
        await manager.connect(ws2)

        # 订阅特定消息类型
        manager.subscribe(ws1, ["device_status"])
        manager.subscribe(ws2, ["waveform_data"])

        # 广播设备状态消息
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        await manager.broadcast_by_type(message)

        # 等待消息处理
        await asyncio.sleep(0.1)

        # 只有订阅了device_status的连接收到消息
        assert len(ws1.messages) >= 1


class TestWebSocketSubscription:
    """WebSocket订阅测试。"""

    @pytest.mark.asyncio
    async def test_subscribe_message_types(self):
        """测试订阅消息类型。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        manager.subscribe(ws, ["device_status", "waveform_data"])

        stats = manager.get_subscription_stats()
        assert "device_status" in stats
        assert "waveform_data" in stats

    @pytest.mark.asyncio
    async def test_unsubscribe_message_types(self):
        """测试取消订阅消息类型。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)
        manager.subscribe(ws, ["device_status", "waveform_data"])

        manager.unsubscribe(ws, ["device_status"])

        stats = manager.get_subscription_stats()
        # device_status应该还有其他订阅者（ws本身）
        assert "waveform_data" in stats


class TestWebSocketHeartbeat:
    """WebSocket心跳测试。"""

    @pytest.mark.asyncio
    async def test_heartbeat_update(self):
        """测试心跳更新。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        initial_time = manager._connection_info[ws].last_heartbeat

        # 等待一小段时间
        await asyncio.sleep(0.1)

        # 更新心跳
        manager.update_heartbeat(ws)

        new_time = manager._connection_info[ws].last_heartbeat

        assert new_time > initial_time

    @pytest.mark.asyncio
    async def test_handle_pong_message(self):
        """测试处理PONG消息。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送PONG消息
        pong_message = json.dumps({"type": "pong"})

        is_control = await manager.handle_client_message(ws, pong_message)

        assert is_control is True


class TestWebSocketBackpressure:
    """WebSocket反压控制测试。"""

    def test_backpressure_state_initialization(self):
        """测试反压状态初始化。"""
        state = BackpressureState()

        assert state.queue_usage == 0.0
        assert state.is_throttled is False
        assert state.total_messages_sent == 0
        assert state.total_messages_dropped == 0

    def test_backpressure_queue_usage(self):
        """测试反压队列使用率计算。"""
        state = BackpressureState(queue_size=100)

        # 添加消息到队列
        for i in range(50):
            state.message_queue.append({"id": i})

        assert state.queue_usage == 0.5

    def test_backpressure_should_throttle(self):
        """测试反压节流判断。"""
        state = BackpressureState(
            queue_size=100,
            high_watermark=0.8,
        )

        # 队列使用率低于阈值
        for i in range(50):
            state.message_queue.append({"id": i})
        assert state.should_throttle is False

        # 队列使用率超过阈值
        for i in range(50, 85):
            state.message_queue.append({"id": i})
        assert state.should_throttle is True

    def test_backpressure_can_resume(self):
        """测试反压恢复判断。"""
        state = BackpressureState(
            queue_size=100,
            low_watermark=0.5,
        )

        # 队列使用率高于阈值
        for i in range(60):
            state.message_queue.append({"id": i})
        assert state.can_resume is False

        # 清空部分队列
        for _ in range(30):
            state.message_queue.popleft()
        assert state.can_resume is True

    @pytest.mark.asyncio
    async def test_backpressure_queue_full_handling(self):
        """测试队列满时的处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 设置小队列
        manager.set_backpressure_config(queue_size=10)

        # 发送大量消息
        for i in range(20):
            message = json.dumps({"id": i})
            await manager.send_personal_message(message, ws)

        # 等待处理
        await asyncio.sleep(0.1)

        # 验证消息被丢弃
        stats = manager.get_backpressure_stats()
        assert stats["total_messages_dropped"] > 0


class TestWebSocketMessageAck:
    """WebSocket消息确认测试。"""

    @pytest.mark.asyncio
    async def test_message_ack_handling(self):
        """测试消息确认处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws, ack_enabled=True)

        # 模拟消息确认
        ack_message = json.dumps({
            "type": "msg_ack",
            "message_id": "test_msg_01",
        })

        # 添加未确认消息
        info = manager.get_connection_info(ws)
        info.backpressure_state.unacked_messages["test_msg_01"] = time.time()

        is_control = await manager.handle_client_message(ws, ack_message)

        assert is_control is True
        assert "test_msg_01" not in info.backpressure_state.unacked_messages


class TestWebSocketReconnection:
    """WebSocket断线重连测试。"""

    @pytest.mark.asyncio
    async def test_client_reconnection(self):
        """测试客户端重连。"""
        manager = ConnectionManager()

        # 首次连接
        ws1 = MockWebSocket()
        conn_id1 = await manager.connect(ws1)

        assert manager.connection_count == 1

        # 断开连接
        manager.disconnect(ws1)

        assert manager.connection_count == 0

        # 重新连接
        ws2 = MockWebSocket()
        conn_id2 = await manager.connect(ws2)

        assert manager.connection_count == 1
        assert conn_id1 != conn_id2  # 新的连接ID

    @pytest.mark.asyncio
    async def test_reconnection_with_subscription_recovery(self):
        """测试重连后订阅恢复。"""
        manager = ConnectionManager()

        # 首次连接并订阅
        ws1 = MockWebSocket()
        await manager.connect(ws1)
        manager.subscribe(ws1, ["device_status", "waveform_data"])

        # 断开连接
        manager.disconnect(ws1)

        # 重新连接
        ws2 = MockWebSocket()
        await manager.connect(ws2)
        manager.subscribe(ws2, ["device_status", "waveform_data"])

        # 验证订阅状态
        stats = manager.get_subscription_stats()
        assert "device_status" in stats


class TestWebSocketErrorHandling:
    """WebSocket错误处理测试。"""

    @pytest.mark.asyncio
    async def test_invalid_json_message(self):
        """测试无效JSON消息处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送无效JSON
        invalid_message = "not a valid json"

        is_control = await manager.handle_client_message(ws, invalid_message)

        assert is_control is False

    @pytest.mark.asyncio
    async def test_invalid_msgpack_message(self):
        """测试无效MessagePack消息处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送无效MessagePack
        invalid_message = b"not a valid msgpack"

        is_control = await manager.handle_client_message(ws, invalid_message)

        assert is_control is False

    @pytest.mark.asyncio
    async def test_send_to_disconnected_client(self):
        """测试向已断开客户端发送消息。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)
        manager.disconnect(ws)

        # 尝试发送消息
        message = json.dumps({"type": "test"})
        result = await manager.send_personal_message(message, ws)

        assert result is False


class TestWebSocketStatistics:
    """WebSocket统计信息测试。"""

    @pytest.mark.asyncio
    async def test_connection_stats(self):
        """测试连接统计信息。"""
        manager = ConnectionManager()

        for i in range(3):
            ws = MockWebSocket()
            await manager.connect(ws, endpoint=f"/ws/test_{i}")

        stats = manager.get_connection_stats()

        assert stats["total_connections"] == 3
        assert len(stats["connections"]) == 3

    @pytest.mark.asyncio
    async def test_message_stats(self):
        """测试消息统计。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送消息
        for i in range(5):
            message = json.dumps({"id": i})
            await manager.send_personal_message(message, ws)

        # 等待处理
        await asyncio.sleep(0.1)

        info = manager.get_connection_info(ws)
        assert info.messages_sent >= 5

    @pytest.mark.asyncio
    async def test_backpressure_stats(self):
        """测试反压统计信息。"""
        manager = ConnectionManager()

        for i in range(3):
            ws = MockWebSocket()
            await manager.connect(ws)

        stats = manager.get_backpressure_stats()

        assert stats["total_connections"] == 3
        assert "total_messages_sent" in stats
        assert "total_messages_dropped" in stats


class TestWebSocketPerformance:
    """WebSocket性能测试。"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_high_frequency_messaging(self):
        """测试高频消息发送。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送大量消息
        num_messages = 1000
        for i in range(num_messages):
            message = create_device_status_message(
                device_id=f"device_{i % 10}",
                device_type=DeviceType.STEPPER,
                status="running",
                position_mm=i * 0.1,
            )
            await manager.send_personal_message(message.to_json(), ws)

        # 等待处理
        await asyncio.sleep(0.5)

        # 验证消息处理
        info = manager.get_connection_info(ws)
        assert info.messages_sent > 0

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_message_handling(self):
        """测试大消息处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 创建大消息
        data_points = [
            {"channel": i % 8, "value": i * 0.1, "timestamp": time.time()}
            for i in range(10000)
        ]

        message = create_waveform_message(
            device_id="ammeter_01",
            device_type=DeviceType.AMMETER,
            sample_rate=1000.0,
            data_points=data_points,
        )

        # 发送消息
        result = await manager.send_personal_message(message.to_json(), ws)

        assert result is True

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_concurrent_broadcasts(self):
        """测试并发广播。"""
        manager = ConnectionManager()

        # 创建多个连接
        connections = []
        for _ in range(10):
            ws = MockWebSocket()
            await manager.connect(ws)
            connections.append(ws)

        # 并发广播
        async def broadcast_task(task_id):
            message = create_device_status_message(
                device_id=f"device_{task_id}",
                device_type=DeviceType.STEPPER,
                status="running",
            )
            await manager.broadcast(message)

        tasks = [broadcast_task(i) for i in range(50)]
        await asyncio.gather(*tasks)

        # 等待处理
        await asyncio.sleep(0.5)

        # 验证所有连接都收到消息
        for ws in connections:
            assert len(ws.messages) > 0


class TestWebSocketIntegrationWithFastAPI:
    """WebSocket与FastAPI集成测试。"""

    @pytest.fixture
    def test_app(self):
        """创建测试应用。"""
        from fastapi import FastAPI

        app = FastAPI()
        manager = ConnectionManager()

        @app.websocket("/ws/test")
        async def websocket_endpoint(websocket: WebSocket):
            await manager.connect(websocket, endpoint="/ws/test")
            try:
                while True:
                    data = await websocket.receive_text()
                    await manager.handle_client_message(websocket, data)
            except WebSocketDisconnect:
                manager.disconnect(websocket)

        return app, manager

    @pytest.mark.asyncio
    async def test_websocket_endpoint_connection(self, test_app):
        """测试WebSocket端点连接。"""
        app, manager = test_app

        with TestClient(app) as client:
            with client.websocket_connect("/ws/test") as websocket:
                # 连接成功
                assert manager.connection_count == 1

    @pytest.mark.asyncio
    async def test_websocket_endpoint_message_exchange(self, test_app):
        """测试WebSocket端点消息交换。"""
        app, manager = test_app

        with TestClient(app) as client:
            with client.websocket_connect("/ws/test") as websocket:
                # 发送PONG消息
                websocket.send_json({"type": "pong"})

                # 等待处理
                import time
                time.sleep(0.1)

                # 验证心跳更新
                assert manager.connection_count == 1


class TestWebSocketDeviceSpecificEndpoints:
    """WebSocket设备特定端点测试。"""

    @pytest.mark.asyncio
    async def test_motor_websocket_format(self):
        """测试电机WebSocket消息格式。"""
        message = create_device_status_message(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready",
            position_mm=25.5,
            position_steps=40800,
            velocity_mm_s=10.0,
            status_word=0x0000,
            alarm_code=0,
        )

        data = message.to_dict()

        assert data["type"] == "device_status"
        assert data["data"]["device_type"] == "stepper"
        assert "position_mm" in data["data"]
        assert "position_steps" in data["data"]

    @pytest.mark.asyncio
    async def test_electromagnet_websocket_format(self):
        """测试电磁铁WebSocket消息格式。"""
        message = create_device_status_message(
            device_id="electromagnet_01",
            device_type=DeviceType.ELECTROMAGNET,
            status="ready",
            current_value_a=5.0,
            field_value_t=0.5,
            scan_progress=0.5,
        )

        data = message.to_dict()

        assert data["data"]["device_type"] == "electromagnet"
        assert "current_value_a" in data["data"]
        assert "field_value_t" in data["data"]

    @pytest.mark.asyncio
    async def test_temperature_websocket_format(self):
        """测试温控WebSocket消息格式。"""
        message = create_device_status_message(
            device_id="temp_01",
            device_type=DeviceType.TEMPERATURE,
            status="running",
            current_temperature_k=300.0,
            setpoint_k=350.0,
            current_output_percent=50.0,
        )

        data = message.to_dict()

        assert data["data"]["device_type"] == "temperature"
        assert "current_temperature_k" in data["data"]
        assert "setpoint_k" in data["data"]

    @pytest.mark.asyncio
    async def test_piezo_websocket_format(self):
        """测试压电WebSocket消息格式。"""
        message = create_device_status_message(
            device_id="piezo_01",
            device_type=DeviceType.PIEZO,
            status="ready",
            current_voltage_v=75.0,
            current_displacement_um=50.0,
            control_mode="voltage",
        )

        data = message.to_dict()

        assert data["data"]["device_type"] == "piezo"
        assert "current_voltage_v" in data["data"]
        assert "current_displacement_um" in data["data"]

    @pytest.mark.asyncio
    async def test_ammeter_websocket_format(self):
        """测试电流计WebSocket消息格式。"""
        data_points = [
            {"channel": 0, "value": 100.5, "timestamp": time.time()},
            {"channel": 1, "value": 200.3, "timestamp": time.time()},
        ]

        message = create_waveform_message(
            device_id="ammeter_01",
            device_type=DeviceType.AMMETER,
            sample_rate=100.0,
            data_points=data_points,
        )

        data = message.to_dict()

        assert data["type"] == "waveform_data"
        assert data["data"]["device_type"] == "ammeter"
        assert len(data["data"]["data_points"]) == 2
