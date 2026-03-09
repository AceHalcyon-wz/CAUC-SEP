"""
单元测试：WebSocket MessagePack协议支持

测试内容：
- MessagePack序列化/反序列化
- 协议协商机制
- JSON/MessagePack双协议兼容性
- 性能对比测试

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import asyncio
import json

import msgpack
import pytest

from api.websocket import (
    AlarmEventData,
    AlarmLevel,
    ConnectionManager,
    DeviceStatusData,
    DeviceType,
    MessageType,
    ProtocolType,
    WebSocketMessage,
    create_alarm_message,
    create_device_status_message,
    deserialize_message,
    parse_protocol_from_query,
    serialize_message,
)


class TestMessagePackSerialization:
    """测试MessagePack序列化功能。"""

    def test_websocket_message_to_msgpack(self):
        """测试WebSocket消息转换为MessagePack格式。"""
        message = WebSocketMessage(
            type=MessageType.DEVICE_STATUS,
            timestamp="2026-03-07T12:00:00",
            data={
                "device_id": "stepper_01",
                "device_type": "stepper",
                "status": "ready",
            },
        )

        msgpack_data = message.to_msgpack()

        # 验证返回的是bytes类型
        assert isinstance(msgpack_data, bytes)

        # 验证可以正确反序列化
        unpacked = msgpack.unpackb(msgpack_data, raw=False)
        assert unpacked["type"] == "device_status"
        assert unpacked["data"]["device_id"] == "stepper_01"

    def test_msgpack_vs_json_size_comparison(self):
        """测试MessagePack与JSON体积对比。"""
        # 创建包含大量数据的消息
        data_points = [
            {"channel": i, "value": i * 10.5, "timestamp": 1234567890.0 + i * 0.1}
            for i in range(100)
        ]

        message = WebSocketMessage(
            type=MessageType.WAVEFORM_DATA,
            timestamp="2026-03-07T12:00:00",
            data={
                "device_id": "ammeter_01",
                "device_type": "ammeter",
                "sample_rate": 1000.0,
                "data_points": data_points,
            },
        )

        json_data = message.to_json()
        msgpack_data = message.to_msgpack()

        # MessagePack体积应该比JSON小30-50%
        json_size = len(json_data.encode())
        msgpack_size = len(msgpack_data)
        size_reduction = (json_size - msgpack_size) / json_size

        assert msgpack_size < json_size
        assert size_reduction > 0.25  # 至少减少25%

        print(f"\nJSON size: {json_size} bytes")
        print(f"MessagePack size: {msgpack_size} bytes")
        print(f"Size reduction: {size_reduction:.1%}")

    def test_msgpack_preserves_data_integrity(self):
        """测试MessagePack保持数据完整性。"""
        original_data = {
            "string": "测试字符串",
            "integer": 12345,
            "float": 3.14159,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3, 4, 5],
            "nested": {"key": "value"},
        }

        message = WebSocketMessage(
            type=MessageType.DEVICE_STATUS,
            timestamp="2026-03-07T12:00:00",
            data=original_data,
        )

        # 序列化并反序列化
        msgpack_data = message.to_msgpack()
        unpacked = msgpack.unpackb(msgpack_data, raw=False)

        # 验证数据完整性
        assert unpacked["data"] == original_data


class TestProtocolNegotiation:
    """测试协议协商机制。"""

    def test_parse_protocol_from_query_json(self):
        """测试解析JSON协议参数。"""
        params = {"protocol": "json"}
        protocol = parse_protocol_from_query(params)
        assert protocol == ProtocolType.JSON

    def test_parse_protocol_from_query_msgpack(self):
        """测试解析MessagePack协议参数。"""
        params = {"protocol": "msgpack"}
        protocol = parse_protocol_from_query(params)
        assert protocol == ProtocolType.MSGPACK

    def test_parse_protocol_default_to_json(self):
        """测试默认协议为JSON。"""
        params = {}
        protocol = parse_protocol_from_query(params)
        assert protocol == ProtocolType.JSON

    def test_parse_protocol_invalid_fallback_to_json(self):
        """测试无效协议回退到JSON。"""
        params = {"protocol": "invalid_protocol"}
        protocol = parse_protocol_from_query(params)
        assert protocol == ProtocolType.JSON

    def test_parse_protocol_case_insensitive(self):
        """测试协议参数大小写不敏感。"""
        params1 = {"protocol": "MSGPACK"}
        params2 = {"protocol": "MsgPack"}

        protocol1 = parse_protocol_from_query(params1)
        protocol2 = parse_protocol_from_query(params2)

        assert protocol1 == ProtocolType.MSGPACK
        assert protocol2 == ProtocolType.MSGPACK


class TestDualProtocolSupport:
    """测试双协议支持（JSON/MessagePack）。"""

    @pytest.mark.asyncio
    async def test_connection_manager_supports_both_protocols(self):
        """测试ConnectionManager支持两种协议。"""
        manager = ConnectionManager()

        # 创建Mock WebSocket
        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, message):
                self.sent_messages.append(("text", message))

            async def send_bytes(self, data):
                self.sent_messages.append(("bytes", data))

        # 测试JSON协议连接
        ws_json = MockWebSocket()
        conn_id_json = await manager.connect(
            ws_json, endpoint="/ws/test", protocol=ProtocolType.JSON
        )
        assert conn_id_json is not None

        # 测试MessagePack协议连接
        ws_msgpack = MockWebSocket()
        conn_id_msgpack = await manager.connect(
            ws_msgpack, endpoint="/ws/test", protocol=ProtocolType.MSGPACK
        )
        assert conn_id_msgpack is not None

        # 验证连接信息中记录了正确的协议
        info_json = manager.get_connection_info(ws_json)
        info_msgpack = manager.get_connection_info(ws_msgpack)

        assert info_json.protocol == ProtocolType.JSON
        assert info_msgpack.protocol == ProtocolType.MSGPACK

    @pytest.mark.asyncio
    async def test_broadcast_uses_correct_protocol(self):
        """测试广播使用正确的协议格式。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self, protocol):
                self.accepted = False
                self.protocol = protocol
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, message):
                if self.protocol == ProtocolType.JSON:
                    self.sent_messages.append(message)

            async def send_bytes(self, data):
                if self.protocol == ProtocolType.MSGPACK:
                    self.sent_messages.append(data)

        # 创建两种协议的连接
        ws_json = MockWebSocket(ProtocolType.JSON)
        ws_msgpack = MockWebSocket(ProtocolType.MSGPACK)

        await manager.connect(ws_json, protocol=ProtocolType.JSON)
        await manager.connect(ws_msgpack, protocol=ProtocolType.MSGPACK)

        # 广播消息
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        await manager.broadcast(message)

        # 等待消息发送任务处理队列中的消息
        await asyncio.sleep(0.1)

        # 验证JSON连接收到JSON格式
        assert len(ws_json.sent_messages) == 1
        assert isinstance(ws_json.sent_messages[0], str)

        # 验证MessagePack连接收到二进制格式
        assert len(ws_msgpack.sent_messages) == 1
        assert isinstance(ws_msgpack.sent_messages[0], bytes)


class TestSerializeDeserialize:
    """测试序列化/反序列化工具函数。"""

    def test_serialize_to_json(self):
        """测试序列化为JSON。"""
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        result = serialize_message(message, ProtocolType.JSON)

        assert isinstance(result, str)
        # 验证可以解析为JSON
        parsed = json.loads(result)
        assert parsed["type"] == "device_status"

    def test_serialize_to_msgpack(self):
        """测试序列化为MessagePack。"""
        message = create_device_status_message(
            device_id="test_01",
            device_type=DeviceType.STEPPER,
            status="ready",
        )

        result = serialize_message(message, ProtocolType.MSGPACK)

        assert isinstance(result, bytes)
        # 验证可以解析为MessagePack
        parsed = msgpack.unpackb(result, raw=False)
        assert parsed["type"] == "device_status"

    def test_deserialize_from_json(self):
        """测试从JSON反序列化。"""
        data = json.dumps(
            {
                "type": "device_status",
                "timestamp": "2026-03-07T12:00:00",
                "data": {"device_id": "test_01"},
            }
        )

        result = deserialize_message(data, ProtocolType.JSON)

        assert result["type"] == "device_status"
        assert result["data"]["device_id"] == "test_01"

    def test_deserialize_from_msgpack(self):
        """测试从MessagePack反序列化。"""
        original = {
            "type": "device_status",
            "timestamp": "2026-03-07T12:00:00",
            "data": {"device_id": "test_01"},
        }
        data = msgpack.packb(original, use_bin_type=True)

        result = deserialize_message(data, ProtocolType.MSGPACK)

        assert result == original


class TestProtocolType:
    """测试ProtocolType枚举。"""

    def test_protocol_type_values(self):
        """测试协议类型枚举值。"""
        assert ProtocolType.JSON.value == "json"
        assert ProtocolType.MSGPACK.value == "msgpack"

    def test_protocol_type_string_conversion(self):
        """测试协议类型字符串转换。"""
        assert ProtocolType("json") == ProtocolType.JSON
        assert ProtocolType("msgpack") == ProtocolType.MSGPACK


class TestMessageCreationWithProtocol:
    """测试消息创建函数的协议支持。"""

    def test_create_device_status_message_serialization(self):
        """测试创建设备状态消息的序列化。"""
        message = create_device_status_message(
            device_id="stepper_01",
            device_type=DeviceType.STEPPER,
            status="ready",
            position_mm=25.5,
        )

        # JSON序列化
        json_str = message.to_json()
        assert isinstance(json_str, str)

        # MessagePack序列化
        msgpack_bytes = message.to_msgpack()
        assert isinstance(msgpack_bytes, bytes)

        # 验证两种格式数据一致
        json_data = json.loads(json_str)
        msgpack_data = msgpack.unpackb(msgpack_bytes, raw=False)

        assert json_data == msgpack_data

    def test_create_alarm_message_serialization(self):
        """测试创建报警消息的序列化。"""
        message = create_alarm_message(
            device_id="temp_01",
            device_type=DeviceType.TEMPERATURE,
            alarm_level=AlarmLevel.WARNING,
            alarm_code="HIGH_TEMP",
            alarm_message="温度超过安全阈值",
        )

        # 验证两种序列化格式都可用
        json_str = message.to_json()
        msgpack_bytes = message.to_msgpack()

        assert len(json_str) > 0
        assert len(msgpack_bytes) > 0


class TestPerformance:
    """性能测试。"""

    def test_msgpack_serialization_performance(self):
        """测试MessagePack序列化性能。"""
        import time

        # 创建大量数据
        data_points = [
            {"channel": i, "value": i * 10.5, "timestamp": 1234567890.0 + i * 0.1}
            for i in range(1000)
        ]

        message = WebSocketMessage(
            type=MessageType.WAVEFORM_DATA,
            timestamp="2026-03-07T12:00:00",
            data={"data_points": data_points},
        )

        # JSON序列化性能
        start = time.time()
        for _ in range(100):
            _ = message.to_json()
        json_time = time.time() - start

        # MessagePack序列化性能
        start = time.time()
        for _ in range(100):
            _ = message.to_msgpack()
        msgpack_time = time.time() - start

        print(f"\nJSON serialization time (100 iterations): {json_time:.4f}s")
        print(f"MessagePack serialization time (100 iterations): {msgpack_time:.4f}s")
        print(f"Speed improvement: {(json_time - msgpack_time) / json_time:.1%}")

        # MessagePack应该更快
        assert msgpack_time < json_time * 1.5  # 允许一定的误差

    def test_msgpack_deserialization_performance(self):
        """测试MessagePack反序列化性能。"""
        import time

        # 创建测试数据
        data = {
            "type": "waveform_data",
            "timestamp": "2026-03-07T12:00:00",
            "data": {
                "data_points": [
                    {"channel": i, "value": i * 10.5, "timestamp": 1234567890.0 + i * 0.1}
                    for i in range(1000)
                ]
            },
        }

        json_str = json.dumps(data)
        msgpack_bytes = msgpack.packb(data, use_bin_type=True)

        # JSON反序列化性能
        start = time.time()
        for _ in range(100):
            _ = json.loads(json_str)
        json_time = time.time() - start

        # MessagePack反序列化性能
        start = time.time()
        for _ in range(100):
            _ = msgpack.unpackb(msgpack_bytes, raw=False)
        msgpack_time = time.time() - start

        print(f"\nJSON deserialization time (100 iterations): {json_time:.4f}s")
        print(f"MessagePack deserialization time (100 iterations): {msgpack_time:.4f}s")
        print(f"Speed improvement: {(json_time - msgpack_time) / json_time:.1%}")

        # MessagePack应该更快
        assert msgpack_time < json_time * 1.5  # 允许一定的误差
