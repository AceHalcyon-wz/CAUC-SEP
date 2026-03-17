"""
WebSocket高级功能测试套件

文件名: test_websocket_advanced.py
路径: backend/tests/
功能: 测试WebSocket反压控制、消息确认、协议协商等高级功能
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, asyncio, msgpack

测试内容：
- TestWebSocketBackpressure: WebSocket反压控制测试
- TestWebSocketMessageAck: WebSocket消息确认测试
- TestWebSocketProtocolNegotiation: WebSocket协议协商测试
- TestWebSocketConnectionManagement: WebSocket连接管理测试
- TestWebSocketMessageRouting: WebSocket消息路由测试
"""

import asyncio
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
import pytest

from api.websocket import (
    BACKPRESSURE_QUEUE_SIZE,
    BACKPRESSURE_WATERMARK_HIGH,
    BACKPRESSURE_WATERMARK_LOW,
    MESSAGE_ACK_TIMEOUT,
    MAX_UNACKED_MESSAGES,
    AlarmEventData,
    AlarmLevel,
    BackpressureState,
    ConnectionInfo,
    ConnectionManager,
    DeviceStatusData,
    DeviceType,
    ExperimentProgressData,
    MessageType,
    MessageRouter,
    ProtocolType,
    WaveformData,
    WaveformDataPoint,
    WebSocketMessage,
    create_alarm_message,
    create_backpressure_warning_message,
    create_device_status_message,
    create_experiment_progress_message,
    create_flow_control_message,
    create_waveform_message,
    deserialize_message,
    parse_ack_enabled_from_query,
    parse_protocol_from_query,
    serialize_message,
)


# ==================== 反压控制测试 ====================


class TestWebSocketBackpressure:
    """WebSocket反压控制测试。"""

    def test_backpressure_state_initialization(self):
        """测试反压状态初始化。"""
        state = BackpressureState()

        assert state.queue_size == BACKPRESSURE_QUEUE_SIZE
        assert state.high_watermark == BACKPRESSURE_WATERMARK_HIGH
        assert state.low_watermark == BACKPRESSURE_WATERMARK_LOW
        assert state.is_throttled is False
        assert state.total_messages_sent == 0
        assert state.total_messages_dropped == 0

    def test_backpressure_queue_usage_calculation(self):
        """测试反压队列使用率计算。"""
        state = BackpressureState()

        # 空队列
        assert state.queue_usage == 0.0

        # 添加消息
        for i in range(50):
            state.message_queue.append({"id": i})

        # 50%使用率
        assert state.queue_usage == 0.5

        # 填满队列
        for i in range(50, 100):
            state.message_queue.append({"id": i})

        # 100%使用率
        assert state.queue_usage == 1.0

    def test_backpressure_should_throttle(self):
        """测试反压节流判断。"""
        state = BackpressureState()

        # 低于高水位线，不节流
        for i in range(70):
            state.message_queue.append({"id": i})
        assert not state.should_throttle

        # 超过高水位线，应节流
        for i in range(70, 85):
            state.message_queue.append({"id": i})
        assert state.should_throttle

    def test_backpressure_can_resume(self):
        """测试反压恢复判断。"""
        state = BackpressureState()

        # 填充到高水位线以上
        for i in range(85):
            state.message_queue.append({"id": i})
        assert state.should_throttle

        # 清空到低水位线以下
        for _ in range(40):
            state.message_queue.popleft()
        assert state.can_resume

    def test_backpressure_state_to_dict(self):
        """测试反压状态序列化。"""
        state = BackpressureState()
        state.total_messages_sent = 100
        state.total_messages_dropped = 5
        state.is_throttled = True

        data = state.to_dict()

        assert data["queue_usage"] == 0.0
        assert data["queue_size"] == BACKPRESSURE_QUEUE_SIZE
        assert data["is_throttled"] is True
        assert data["total_messages_sent"] == 100
        assert data["total_messages_dropped"] == 5

    @pytest.mark.asyncio
    async def test_backpressure_warning_message(self):
        """测试反压警告消息创建。"""
        msg = create_backpressure_warning_message(
            queue_usage=0.85,
            is_throttled=True,
            queue_size=100
        )

        assert msg.type == MessageType.BACKPRESSURE_WARNING
        assert msg.data["queue_usage"] == 0.85
        assert msg.data["is_throttled"] is True
        assert msg.data["queue_size"] == 100

    @pytest.mark.asyncio
    async def test_flow_control_message(self):
        """测试流量控制消息创建。"""
        msg = create_flow_control_message("resumed")

        assert msg.type == MessageType.FLOW_CONTROL
        assert msg.data["status"] == "resumed"

    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self):
        """测试队列溢出处理。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        # 获取反压状态
        backpressure_state = manager._connection_info[mock_ws].backpressure_state

        # 填充队列超过容量
        for i in range(BACKPRESSURE_QUEUE_SIZE + 10):
            await manager.send_personal_message(f"message_{i}", mock_ws)

        # 队列不应超过最大容量
        assert len(backpressure_state.message_queue) <= BACKPRESSURE_QUEUE_SIZE

        # 应有消息被丢弃
        assert backpressure_state.total_messages_dropped > 0

        # 清理
        manager.disconnect(mock_ws)


# ==================== 消息确认测试 ====================


class TestWebSocketMessageAck:
    """WebSocket消息确认测试。"""

    def test_parse_ack_enabled_from_query(self):
        """测试从查询参数解析消息确认启用状态。"""
        # 启用
        assert parse_ack_enabled_from_query({"ack": "true"}) is True
        assert parse_ack_enabled_from_query({"ack": "1"}) is True
        assert parse_ack_enabled_from_query({"ack": "yes"}) is True

        # 禁用
        assert parse_ack_enabled_from_query({"ack": "false"}) is False
        assert parse_ack_enabled_from_query({"ack": "0"}) is False
        assert parse_ack_enabled_from_query({}) is False

    @pytest.mark.asyncio
    async def test_connection_with_ack_enabled(self):
        """测试启用消息确认的连接。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        connection_id = await manager.connect(
            mock_ws,
            ack_enabled=True
        )

        connection_info = manager._connection_info[mock_ws]
        assert connection_info.ack_enabled is True
        assert connection_info.backpressure_state.ack_enabled is True

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_unacked_message_tracking(self):
        """测试未确认消息跟踪。"""
        state = BackpressureState(ack_enabled=True)

        # 添加未确认消息
        state.unacked_messages["msg_001"] = time.time()
        state.unacked_messages["msg_002"] = time.time()

        assert len(state.unacked_messages) == 2

        # 确认消息
        del state.unacked_messages["msg_001"]
        assert len(state.unacked_messages) == 1

    @pytest.mark.asyncio
    async def test_message_ack_timeout_handling(self):
        """测试消息确认超时处理。"""
        state = BackpressureState(ack_enabled=True)

        # 添加超时的未确认消息
        expired_time = time.time() - MESSAGE_ACK_TIMEOUT - 1
        state.unacked_messages["expired_msg"] = expired_time

        # 添加正常的未确认消息
        state.unacked_messages["valid_msg"] = time.time()

        # 清理超时消息
        current_time = time.time()
        expired_msgs = [
            msg_id
            for msg_id, timestamp in state.unacked_messages.items()
            if current_time - timestamp > MESSAGE_ACK_TIMEOUT
        ]

        for msg_id in expired_msgs:
            del state.unacked_messages[msg_id]
            state.total_messages_dropped += 1

        assert len(state.unacked_messages) == 1
        assert "valid_msg" in state.unacked_messages
        assert state.total_messages_dropped == 1

    @pytest.mark.asyncio
    async def test_max_unacked_messages_limit(self):
        """测试最大未确认消息数限制。"""
        state = BackpressureState(ack_enabled=True)

        # 添加最大数量的未确认消息
        for i in range(MAX_UNACKED_MESSAGES):
            state.unacked_messages[f"msg_{i}"] = time.time()

        # 应达到限制
        assert len(state.unacked_messages) == MAX_UNACKED_MESSAGES


# ==================== 协议协商测试 ====================


class TestWebSocketProtocolNegotiation:
    """WebSocket协议协商测试。"""

    def test_parse_protocol_from_query_json(self):
        """测试解析JSON协议。"""
        # 默认JSON
        assert parse_protocol_from_query({}) == ProtocolType.JSON
        assert parse_protocol_from_query({"protocol": "json"}) == ProtocolType.JSON

    def test_parse_protocol_from_query_msgpack(self):
        """测试解析MessagePack协议。"""
        assert parse_protocol_from_query({"protocol": "msgpack"}) == ProtocolType.MSGPACK

    def test_parse_protocol_invalid_fallback(self):
        """测试无效协议回退到JSON。"""
        assert parse_protocol_from_query({"protocol": "invalid"}) == ProtocolType.JSON
        assert parse_protocol_from_query({"protocol": "xml"}) == ProtocolType.JSON

    @pytest.mark.asyncio
    async def test_connection_with_json_protocol(self):
        """测试JSON协议连接。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws, protocol=ProtocolType.JSON)

        connection_info = manager._connection_info[mock_ws]
        assert connection_info.protocol == ProtocolType.JSON

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_connection_with_msgpack_protocol(self):
        """测试MessagePack协议连接。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws, protocol=ProtocolType.MSGPACK)

        connection_info = manager._connection_info[mock_ws]
        assert connection_info.protocol == ProtocolType.MSGPACK

        manager.disconnect(mock_ws)

    def test_serialize_message_json(self):
        """测试JSON消息序列化。"""
        msg = create_device_status_message(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready"
        )

        serialized = serialize_message(msg, ProtocolType.JSON)

        assert isinstance(serialized, str)
        data = json.loads(serialized)
        assert data["type"] == "device_status"

    def test_serialize_message_msgpack(self):
        """测试MessagePack消息序列化。"""
        msg = create_device_status_message(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready"
        )

        serialized = serialize_message(msg, ProtocolType.MSGPACK)

        assert isinstance(serialized, bytes)
        data = msgpack.unpackb(serialized, raw=False)
        assert data["type"] == "device_status"

    def test_deserialize_message_json(self):
        """测试JSON消息反序列化。"""
        json_str = '{"type": "ping", "timestamp": "2026-03-16T10:00:00", "data": {}}'

        data = deserialize_message(json_str, ProtocolType.JSON)

        assert data["type"] == "ping"
        assert "timestamp" in data

    def test_deserialize_message_msgpack(self):
        """测试MessagePack消息反序列化。"""
        msg_data = {
            "type": "ping",
            "timestamp": "2026-03-16T10:00:00",
            "data": {}
        }
        msgpack_bytes = msgpack.packb(msg_data, use_bin_type=True)

        data = deserialize_message(msgpack_bytes, ProtocolType.MSGPACK)

        assert data["type"] == "ping"

    def test_msgpack_size_advantage(self):
        """测试MessagePack体积优势。"""
        # 创建包含大量数据的消息
        data_points = [
            {"channel": i, "value": i * 0.1, "timestamp": time.time()}
            for i in range(100)
        ]

        msg = create_waveform_message(
            device_id="ammeter_01",
            device_type=DeviceType.AMMETER,
            sample_rate=1000.0,
            data_points=data_points
        )

        json_size = len(serialize_message(msg, ProtocolType.JSON))
        msgpack_size = len(serialize_message(msg, ProtocolType.MSGPACK))

        # MessagePack应比JSON小
        assert msgpack_size < json_size
        # 通常小20-40%
        compression_ratio = msgpack_size / json_size
        assert compression_ratio < 0.9


# ==================== 连接管理测试 ====================


class TestWebSocketConnectionManagement:
    """WebSocket连接管理测试。"""

    @pytest.mark.asyncio
    async def test_connection_info_creation(self):
        """测试连接信息创建。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        connection_id = await manager.connect(
            mock_ws,
            endpoint="/ws/motor",
            client_ip="192.168.1.100",
            protocol=ProtocolType.JSON
        )

        connection_info = manager._connection_info[mock_ws]

        assert connection_info.connection_id == connection_id
        assert connection_info.endpoint == "/ws/motor"
        assert connection_info.client_ip == "192.168.1.100"
        assert connection_info.protocol == ProtocolType.JSON
        assert connection_info.messages_sent == 0
        assert connection_info.messages_received == 0

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_connection_stats(self):
        """测试连接统计。"""
        manager = ConnectionManager()

        # 创建多个连接
        for i in range(3):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            await manager.connect(mock_ws, endpoint=f"/ws/test{i}")

        stats = manager.get_connection_stats()

        assert stats["total_connections"] == 3
        assert "subscription_stats" in stats
        assert "connections" in stats
        assert len(stats["connections"]) == 3

        # 清理
        for ws in list(manager._active_connections):
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_backpressure_stats(self):
        """测试反压统计。"""
        manager = ConnectionManager()

        # 创建连接
        for i in range(2):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            await manager.connect(mock_ws)

        stats = manager.get_backpressure_stats()

        assert stats["total_connections"] == 2
        assert "total_messages_sent" in stats
        assert "total_messages_dropped" in stats
        assert "connections" in stats

        # 清理
        for ws in list(manager._active_connections):
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_set_backpressure_config(self):
        """测试设置反压配置。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        # 修改配置
        manager.set_backpressure_config(
            queue_size=200,
            high_watermark=0.9,
            low_watermark=0.6
        )

        backpressure_state = manager._connection_info[mock_ws].backpressure_state

        assert backpressure_state.queue_size == 200
        assert backpressure_state.high_watermark == 0.9
        assert backpressure_state.low_watermark == 0.6

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_message_stats_update(self):
        """测试消息统计更新。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        # 更新发送统计
        manager.update_message_stats(mock_ws, sent=True)
        manager.update_message_stats(mock_ws, sent=True)

        # 更新接收统计
        manager.update_message_stats(mock_ws, received=True)

        connection_info = manager._connection_info[mock_ws]
        assert connection_info.messages_sent == 2
        assert connection_info.messages_received == 1

        manager.disconnect(mock_ws)


# ==================== 消息路由测试 ====================


class TestWebSocketMessageRouting:
    """WebSocket消息路由测试。"""

    @pytest.mark.asyncio
    async def test_subscribe_to_message_types(self):
        """测试订阅消息类型。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        # 订阅消息类型
        manager.subscribe(mock_ws, ["device_status", "alarm_event"])

        subscriptions = manager._connection_subscriptions[mock_ws]
        assert "device_status" in subscriptions
        assert "alarm_event" in subscriptions

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_unsubscribe_from_message_types(self):
        """测试取消订阅消息类型。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        # 订阅
        manager.subscribe(mock_ws, ["device_status", "alarm_event"])

        # 取消订阅
        manager.unsubscribe(mock_ws, ["alarm_event"])

        subscriptions = manager._connection_subscriptions[mock_ws]
        assert "device_status" in subscriptions
        assert "alarm_event" not in subscriptions

        manager.disconnect(mock_ws)

    @pytest.mark.asyncio
    async def test_broadcast_by_type(self):
        """测试按类型广播消息。"""
        manager = ConnectionManager()

        # 创建两个连接，一个订阅，一个不订阅
        mock_ws1 = AsyncMock()
        mock_ws1.accept = AsyncMock()
        mock_ws2 = AsyncMock()
        mock_ws2.accept = AsyncMock()

        await manager.connect(mock_ws1)
        await manager.connect(mock_ws2)

        # 只有ws1订阅device_status
        manager.subscribe(mock_ws1, ["device_status"])

        # 广播设备状态消息
        msg = create_device_status_message(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready"
        )

        await manager.broadcast_by_type(msg)

        # 等待消息发送
        await asyncio.sleep(0.1)

        manager.disconnect(mock_ws1)
        manager.disconnect(mock_ws2)

    @pytest.mark.asyncio
    async def test_message_router_registration(self):
        """测试消息路由器注册。"""
        router = MessageRouter()

        async def status_handler(device_id: str):
            return DeviceStatusData(
                device_id=device_id,
                device_type=DeviceType.STEPPER,
                status="ready"
            )

        router.register_status_handler(DeviceType.STEPPER, status_handler)

        assert DeviceType.STEPPER in router._status_handlers

    @pytest.mark.asyncio
    async def test_message_router_get_status(self):
        """测试消息路由器获取状态。"""
        router = MessageRouter()

        async def status_handler(device_id: str):
            return DeviceStatusData(
                device_id=device_id,
                device_type=DeviceType.STEPPER,
                status="ready",
                extra={"position_mm": 50.0}
            )

        router.register_status_handler(DeviceType.STEPPER, status_handler)

        status = await router.get_device_status(DeviceType.STEPPER, "stepper_01")

        assert status is not None
        assert status.device_id == "stepper_01"
        assert status.status == "ready"
        assert status.extra["position_mm"] == 50.0


# ==================== 消息创建测试 ====================


class TestWebSocketMessageCreation:
    """WebSocket消息创建测试。"""

    def test_create_device_status_message(self):
        """测试创建设备状态消息。"""
        msg = create_device_status_message(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready",
            position_mm=50.0,
            velocity_mm_s=10.0
        )

        assert msg.type == MessageType.DEVICE_STATUS
        assert msg.data["device_id"] == "stepper_01"
        assert msg.data["device_type"] == "stepper"
        assert msg.data["status"] == "ready"
        assert msg.data["position_mm"] == 50.0

    def test_create_waveform_message(self):
        """测试创建波形数据消息。"""
        data_points = [
            {"channel": 0, "value": 100.5, "timestamp": time.time()},
            {"channel": 1, "value": 200.3, "timestamp": time.time()},
        ]

        msg = create_waveform_message(
            device_id="ammeter_01",
            device_type=DeviceType.AMMETER,
            sample_rate=1000.0,
            data_points=data_points
        )

        assert msg.type == MessageType.WAVEFORM_DATA
        assert msg.data["device_id"] == "ammeter_01"
        assert msg.data["sample_rate"] == 1000.0
        assert len(msg.data["data_points"]) == 2

    def test_create_alarm_message(self):
        """测试创建报警消息。"""
        msg = create_alarm_message(
            device_id="temp_01",
            device_type=DeviceType.TEMPERATURE,
            alarm_level=AlarmLevel.WARNING,
            alarm_code="HIGH_TEMP",
            alarm_message="温度超过安全阈值",
            recoverable=True
        )

        assert msg.type == MessageType.ALARM_EVENT
        assert msg.data["device_id"] == "temp_01"
        assert msg.data["alarm_level"] == "warning"
        assert msg.data["alarm_code"] == "HIGH_TEMP"

    def test_create_experiment_progress_message(self):
        """测试创建实验进度消息。"""
        msg = create_experiment_progress_message(
            experiment_id=1,
            experiment_name="磁场扫描实验",
            progress=0.5,
            current_step=5,
            total_steps=10,
            elapsed_time=300.0,
            estimated_remaining=300.0,
            status="running"
        )

        assert msg.type == MessageType.EXPERIMENT_PROGRESS
        assert msg.data["experiment_id"] == 1
        assert msg.data["progress"] == 0.5
        assert msg.data["status"] == "running"


# ==================== 数据类测试 ====================


class TestWebSocketDataClasses:
    """WebSocket数据类测试。"""

    def test_device_status_data_to_dict(self):
        """测试设备状态数据序列化。"""
        data = DeviceStatusData(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready",
            connected=True,
            simulation=False,
            extra={"position_mm": 50.0}
        )

        result = data.to_dict()

        assert result["device_id"] == "stepper_01"
        assert result["device_type"] == "stepper"
        assert result["status"] == "ready"
        assert result["connected"] is True
        assert result["simulation"] is False
        assert result["position_mm"] == 50.0

    def test_waveform_data_to_dict(self):
        """测试波形数据序列化。"""
        data = WaveformData(
            device_id="ammeter_01",
            device_type=DeviceType.AMMETER,
            sample_rate=1000.0,
            data_points=[
                WaveformDataPoint(channel=0, value=100.5, timestamp=time.time()),
                WaveformDataPoint(channel=1, value=200.3, timestamp=time.time()),
            ]
        )

        result = data.to_dict()

        assert result["device_id"] == "ammeter_01"
        assert result["sample_rate"] == 1000.0
        assert len(result["data_points"]) == 2

    def test_alarm_event_data_to_dict(self):
        """测试报警事件数据序列化。"""
        data = AlarmEventData(
            device_id="temp_01",
            device_type=DeviceType.TEMPERATURE,
            alarm_level=AlarmLevel.ERROR,
            alarm_code="SENSOR_FAIL",
            alarm_message="温度传感器故障",
            alarm_time="2026-03-16T10:00:00",
            recoverable=False
        )

        result = data.to_dict()

        assert result["device_id"] == "temp_01"
        assert result["alarm_level"] == "error"
        assert result["recoverable"] is False

    def test_experiment_progress_data_to_dict(self):
        """测试实验进度数据序列化。"""
        data = ExperimentProgressData(
            experiment_id=1,
            experiment_name="测试实验",
            progress=0.75,
            current_step=75,
            total_steps=100,
            elapsed_time=450.0,
            estimated_remaining=150.0,
            status="running"
        )

        result = data.to_dict()

        assert result["experiment_id"] == 1
        assert result["progress"] == 0.75
        assert result["elapsed_time"] == 450.0

    def test_websocket_message_to_json(self):
        """测试WebSocket消息JSON序列化。"""
        msg = WebSocketMessage(
            type=MessageType.DEVICE_STATUS,
            timestamp="2026-03-16T10:00:00",
            data={"device_id": "test"}
        )

        json_str = msg.to_json()

        assert isinstance(json_str, str)
        assert "device_status" in json_str

    def test_websocket_message_to_msgpack(self):
        """测试WebSocket消息MessagePack序列化。"""
        msg = WebSocketMessage(
            type=MessageType.DEVICE_STATUS,
            timestamp="2026-03-16T10:00:00",
            data={"device_id": "test"}
        )

        msgpack_bytes = msg.to_msgpack()

        assert isinstance(msgpack_bytes, bytes)

        # 反序列化验证
        data = msgpack.unpackb(msgpack_bytes, raw=False)
        assert data["type"] == "device_status"


# ==================== 并发测试 ====================


class TestWebSocketConcurrency:
    """WebSocket并发测试。"""

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """测试并发连接。"""
        manager = ConnectionManager()

        async def create_connection(i):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            await manager.connect(mock_ws, endpoint=f"/ws/test{i}")
            return mock_ws

        # 并发创建10个连接
        connections = await asyncio.gather(*[create_connection(i) for i in range(10)])

        assert manager.connection_count == 10

        # 清理
        for ws in connections:
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_concurrent_message_broadcast(self):
        """测试并发消息广播。"""
        manager = ConnectionManager()

        # 创建多个连接
        connections = []
        for i in range(5):
            mock_ws = AsyncMock()
            mock_ws.accept = AsyncMock()
            await manager.connect(mock_ws)
            connections.append(mock_ws)

        # 并发广播多条消息
        async def broadcast_message(i):
            msg = create_device_status_message(
                device_id=f"device_{i}",
                device_type=DeviceType.STEPPER,
                status="ready"
            )
            await manager.broadcast(msg)

        await asyncio.gather(*[broadcast_message(i) for i in range(20)])

        # 清理
        for ws in connections:
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_concurrent_subscribe_unsubscribe(self):
        """测试并发订阅/取消订阅。"""
        manager = ConnectionManager()
        mock_ws = AsyncMock()
        mock_ws.accept = AsyncMock()

        await manager.connect(mock_ws)

        # 并发订阅和取消订阅
        async def subscribe_task(i):
            manager.subscribe(mock_ws, [f"type_{i}"])

        async def unsubscribe_task(i):
            manager.unsubscribe(mock_ws, [f"type_{i}"])

        await asyncio.gather(
            *[subscribe_task(i) for i in range(10)],
            *[unsubscribe_task(i) for i in range(5)]
        )

        manager.disconnect(mock_ws)
