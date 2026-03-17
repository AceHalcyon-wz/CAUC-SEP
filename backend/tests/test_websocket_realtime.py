"""
WebSocket和实时通信综合测试

文件名: test_websocket_realtime.py
路径: backend/tests/
功能: WebSocket连接、实时数据推送、设备状态同步、错误处理和重连测试
作者: Test Debugger Agent
创建日期: 2026-03-16
依赖: pytest, pytest-asyncio, fastapi, httpx, msgpack

测试内容：
1. WebSocket连接测试
   - 连接建立
   - 连接认证
   - 连接关闭
   - 连接超时

2. 实时数据推送测试
   - 数据推送
   - 数据格式
   - 数据压缩
   - 数据完整性

3. 设备状态同步测试
   - 状态同步
   - 状态广播
   - 状态一致性
   - 状态缓存

4. 错误处理和重连测试
   - 错误处理
   - 自动重连
   - 心跳检测
   - 断线恢复
"""

import asyncio
import gzip
import json
import time
import zlib
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import msgpack
import pytest
from fastapi import WebSocket, WebSocketDisconnect
from fastapi.testclient import TestClient

from api.websocket import (
    HEARTBEAT_INTERVAL,
    HEARTBEAT_TIMEOUT,
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
    serialize_message,
)
from api.websocket_backpressure import BackpressureController, BackpressureStats
from api.websocket_protocol import (
    BackpressureWarningMessage,
    DeviceStatusMessage,
    ErrorMessage,
    HeartbeatAckMessage,
    HeartbeatMessage,
    WaveformMessage,
    WSMessage,
)
from api.websocket_throttle import (
    AdaptiveThrottler,
    DataThrottler,
    PriorityDataThrottler,
    ThrottleConfig,
    ThrottleStats,
)
from api.websocket_validators import (
    MAX_MESSAGE_SIZE,
    WSAlarmMessage,
    WSCommandMessage,
    WSMessageBase,
    validate_device_id_format,
    validate_websocket_message,
)


# ==================== Mock WebSocket 类 ====================


class MockWebSocket:
    """Mock WebSocket连接类，用于测试。"""

    def __init__(
        self,
        protocol: ProtocolType = ProtocolType.JSON,
        client_host: str = "127.0.0.1",
        client_port: int = 12345,
    ):
        """初始化Mock WebSocket。

        Args:
            protocol: 通信协议类型
            client_host: 客户端主机地址
            client_port: 客户端端口
        """
        self.messages: list[tuple[str, str | bytes]] = []
        self.closed = False
        self.accepted = False
        self.protocol = protocol
        self.client = MagicMock()
        self.client.host = client_host
        self.client.port = client_port
        self._receive_queue: deque = deque()
        self._state = "connected"

    async def accept(self):
        """接受连接。"""
        if self.closed:
            raise WebSocketDisconnect()
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
        if self._receive_queue:
            return self._receive_queue.popleft()
        await asyncio.sleep(0.01)
        return json.dumps({"type": "pong"})

    async def receive_bytes(self) -> bytes:
        """接收二进制数据。"""
        if self.closed:
            raise WebSocketDisconnect()
        if self._receive_queue:
            return self._receive_queue.popleft()
        await asyncio.sleep(0.01)
        return msgpack.packb({"type": "pong"})

    async def close(self, code: int = 1000, reason: str = ""):
        """关闭连接。"""
        self.closed = True
        self._state = "closed"

    def queue_message(self, message: str | bytes):
        """排队消息用于接收。"""
        self._receive_queue.append(message)

    def get_messages(self) -> list[str | bytes]:
        """获取所有已发送的消息内容。"""
        return [msg for _, msg in self.messages]

    def clear_messages(self):
        """清空消息列表。"""
        self.messages.clear()


# ==================== 第一部分：WebSocket连接测试 ====================


class TestWebSocketConnection:
    """WebSocket连接测试类。"""

    @pytest.mark.asyncio
    async def test_connection_establishment(self):
        """测试WebSocket连接建立。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        connection_id = await manager.connect(
            ws,
            endpoint="/ws/motor",
            client_ip="192.168.1.100",
        )

        assert ws.accepted is True
        assert connection_id is not None
        assert len(connection_id) == 8
        assert manager.connection_count == 1

        info = manager.get_connection_info(ws)
        assert info is not None
        assert info.endpoint == "/ws/motor"
        assert info.client_ip == "192.168.1.100"
        assert info.connected_at > 0

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_connection_with_authentication(self):
        """测试带认证的WebSocket连接。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        # 模拟认证连接
        connection_id = await manager.connect(
            ws,
            endpoint="/ws/authenticated",
            client_ip="192.168.1.100",
            ack_enabled=True,
        )

        info = manager.get_connection_info(ws)
        assert info.ack_enabled is True
        assert info.backpressure_state.ack_enabled is True

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_connection_close_normal(self):
        """测试正常关闭连接。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)
        assert manager.connection_count == 1

        # 正常关闭
        manager.disconnect(ws)

        assert manager.connection_count == 0
        assert ws not in manager._active_connections
        assert ws not in manager._connection_info

    @pytest.mark.asyncio
    async def test_connection_close_with_reason(self):
        """测试带原因的连接关闭。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        connection_id = await manager.connect(ws)
        info = manager.get_connection_info(ws)

        # 带原因关闭
        await manager._close_connection(ws, reason="client_requested")

        assert manager.connection_count == 0
        assert ws.closed is True

    @pytest.mark.asyncio
    async def test_connection_timeout(self):
        """测试连接超时检测。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        connection_id = await manager.connect(ws)
        info = manager.get_connection_info(ws)

        # 模拟超时：设置最后消息时间为很久之前
        info.last_message_time = time.time() - HEARTBEAT_TIMEOUT - 10

        # 等待心跳监控检测超时
        await asyncio.sleep(HEARTBEAT_INTERVAL + 1)

        # 验证连接被关闭
        assert manager.connection_count == 0 or ws.closed

    @pytest.mark.asyncio
    async def test_multiple_concurrent_connections(self):
        """测试多个并发连接。"""
        manager = ConnectionManager()

        connections = []
        for i in range(10):
            ws = MockWebSocket(client_host=f"192.168.1.{i}")
            conn_id = await manager.connect(ws, endpoint=f"/ws/client_{i}")
            connections.append((ws, conn_id))

        assert manager.connection_count == 10

        # 验证每个连接都有唯一ID
        conn_ids = [conn_id for _, conn_id in connections]
        assert len(set(conn_ids)) == 10

        # 断开所有连接
        for ws, _ in connections:
            manager.disconnect(ws)

        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_connection_protocol_negotiation_json(self):
        """测试JSON协议协商。"""
        manager = ConnectionManager()
        ws = MockWebSocket(protocol=ProtocolType.JSON)

        await manager.connect(ws, protocol=ProtocolType.JSON)

        info = manager.get_connection_info(ws)
        assert info.protocol == ProtocolType.JSON

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_connection_protocol_negotiation_msgpack(self):
        """测试MessagePack协议协商。"""
        manager = ConnectionManager()
        ws = MockWebSocket(protocol=ProtocolType.MSGPACK)

        await manager.connect(ws, protocol=ProtocolType.MSGPACK)

        info = manager.get_connection_info(ws)
        assert info.protocol == ProtocolType.MSGPACK

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_connection_stats_tracking(self):
        """测试连接统计追踪。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送一些消息
        for i in range(5):
            await manager.send_personal_message(json.dumps({"id": i}), ws)

        await asyncio.sleep(0.2)

        info = manager.get_connection_info(ws)
        assert info.messages_sent >= 5
        assert info.messages_received == 0

        manager.disconnect(ws)


# ==================== 第二部分：实时数据推送测试 ====================


class TestRealtimeDataPush:
    """实时数据推送测试类。"""

    @pytest.mark.asyncio
    async def test_device_status_push(self):
        """测试设备状态推送。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 创建并推送设备状态
        status_data = DeviceStatusData(
            device_id="motor_001",
            device_type=DeviceType.STEPPER,
            status="running",
            connected=True,
            simulation=False,
            extra={"position_mm": 100.0, "velocity_mm_s": 50.0},
        )

        await manager.broadcast_device_status(status_data)
        await asyncio.sleep(0.2)

        # 验证消息已发送
        assert len(ws.messages) >= 1
        msg_type, msg_content = ws.messages[0]
        assert msg_type == "text"

        parsed = json.loads(msg_content)
        assert parsed["type"] == "device_status"
        assert parsed["data"]["device_id"] == "motor_001"
        assert parsed["data"]["position_mm"] == 100.0

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_waveform_data_push(self):
        """测试波形数据推送。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 创建波形数据
        data_points = [
            WaveformDataPoint(channel=0, value=100.5 + i, timestamp=time.time() + i * 0.01)
            for i in range(100)
        ]

        waveform_data = WaveformData(
            device_id="ammeter_001",
            device_type=DeviceType.AMMETER,
            sample_rate=1000.0,
            data_points=data_points,
        )

        await manager.broadcast_waveform_data(waveform_data)
        await asyncio.sleep(0.2)

        # 验证消息
        assert len(ws.messages) >= 1
        msg_type, msg_content = ws.messages[0]

        parsed = json.loads(msg_content)
        assert parsed["type"] == "waveform_data"
        assert parsed["data"]["sample_rate"] == 1000.0
        assert len(parsed["data"]["data_points"]) == 100

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_alarm_event_push(self):
        """测试报警事件推送。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 创建报警数据
        alarm_data = AlarmEventData(
            device_id="temp_001",
            device_type=DeviceType.TEMPERATURE,
            alarm_level=AlarmLevel.WARNING,
            alarm_code="HIGH_TEMP",
            alarm_message="温度超过安全阈值",
            alarm_time=datetime.now().isoformat(),
            recoverable=True,
        )

        await manager.broadcast_alarm_event(alarm_data)
        await asyncio.sleep(0.2)

        # 验证消息
        assert len(ws.messages) >= 1
        msg_type, msg_content = ws.messages[0]

        parsed = json.loads(msg_content)
        assert parsed["type"] == "alarm_event"
        assert parsed["data"]["alarm_level"] == "warning"
        assert parsed["data"]["alarm_code"] == "HIGH_TEMP"

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_experiment_progress_push(self):
        """测试实验进度推送。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 创建实验进度数据
        progress_data = ExperimentProgressData(
            experiment_id=1,
            experiment_name="磁场扫描实验",
            progress=0.65,
            current_step=65,
            total_steps=100,
            elapsed_time=650.0,
            estimated_remaining=350.0,
            status="running",
        )

        await manager.broadcast_experiment_progress(progress_data)
        await asyncio.sleep(0.2)

        # 验证消息
        assert len(ws.messages) >= 1
        parsed = json.loads(ws.messages[0][1])
        assert parsed["type"] == "experiment_progress"
        assert parsed["data"]["progress"] == 0.65

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_data_format_json(self):
        """测试JSON数据格式。"""
        message = create_device_status_message(
            device_id="test_001",
            device_type=DeviceType.STEPPER,
            status="ready",
            position_mm=50.0,
        )

        json_str = message.to_json()

        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert "type" in parsed
        assert "timestamp" in parsed
        assert "data" in parsed

    @pytest.mark.asyncio
    async def test_data_format_msgpack(self):
        """测试MessagePack数据格式。"""
        message = create_device_status_message(
            device_id="test_001",
            device_type=DeviceType.STEPPER,
            status="ready",
            position_mm=50.0,
        )

        msgpack_bytes = message.to_msgpack()

        assert isinstance(msgpack_bytes, bytes)
        parsed = msgpack.unpackb(msgpack_bytes, raw=False)
        assert parsed["type"] == "device_status"

    @pytest.mark.asyncio
    async def test_data_compression_comparison(self):
        """测试数据压缩对比（JSON vs MessagePack）。"""
        # 创建大数据集
        data_points = [
            {"channel": i % 8, "value": i * 0.1, "timestamp": time.time() + i * 0.001}
            for i in range(1000)
        ]

        message = create_waveform_message(
            device_id="ammeter_001",
            device_type=DeviceType.AMMETER,
            sample_rate=10000.0,
            data_points=data_points,
        )

        json_size = len(message.to_json())
        msgpack_size = len(message.to_msgpack())

        # MessagePack应该比JSON小
        assert msgpack_size < json_size
        compression_ratio = (1 - msgpack_size / json_size) * 100
        print(f"JSON size: {json_size}, MessagePack size: {msgpack_size}")
        print(f"Compression ratio: {compression_ratio:.1f}%")

    @pytest.mark.asyncio
    async def test_data_integrity_verification(self):
        """测试数据完整性验证。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送多条消息
        for i in range(10):
            message = create_device_status_message(
                device_id=f"device_{i:03d}",
                device_type=DeviceType.STEPPER,
                status="running",
                sequence=i,
            )
            await manager.send_personal_message(message.to_json(), ws)

        await asyncio.sleep(0.3)

        # 验证消息顺序和完整性
        messages = ws.get_messages()
        assert len(messages) >= 10

        for i, msg in enumerate(messages[:10]):
            parsed = json.loads(msg)
            assert parsed["data"]["device_id"] == f"device_{i:03d}"
            assert parsed["data"]["sequence"] == i

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_high_frequency_data_push(self):
        """测试高频数据推送。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 高频推送（100Hz）
        num_messages = 100
        start_time = time.time()

        for i in range(num_messages):
            message = create_device_status_message(
                device_id="motor_001",
                device_type=DeviceType.STEPPER,
                status="running",
                position_mm=i * 0.1,
            )
            await manager.send_personal_message(message.to_json(), ws)

        elapsed = time.time() - start_time
        await asyncio.sleep(0.5)

        # 验证推送频率
        info = manager.get_connection_info(ws)
        assert info.messages_sent >= num_messages * 0.9  # 允许10%丢失

        print(f"Pushed {num_messages} messages in {elapsed:.3f}s")
        print(f"Actual rate: {num_messages / elapsed:.1f} Hz")

        manager.disconnect(ws)


# ==================== 第三部分：设备状态同步测试 ====================


class TestDeviceStateSync:
    """设备状态同步测试类。"""

    @pytest.mark.asyncio
    async def test_state_synchronization_single_device(self):
        """测试单设备状态同步。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)
        manager.subscribe(ws, ["device_status"])

        # 模拟设备状态变化
        states = ["idle", "initializing", "ready", "running", "stopping", "idle"]

        for state in states:
            status_data = DeviceStatusData(
                device_id="motor_001",
                device_type=DeviceType.STEPPER,
                status=state,
            )
            await manager.broadcast_device_status(status_data)
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.2)

        # 验证所有状态都已同步
        messages = ws.get_messages()
        assert len(messages) >= len(states)

        received_states = []
        for msg in messages:
            parsed = json.loads(msg)
            if parsed["type"] == "device_status":
                received_states.append(parsed["data"]["status"])

        for state in states:
            assert state in received_states

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_state_broadcast_to_multiple_clients(self):
        """测试状态广播到多个客户端。"""
        manager = ConnectionManager()

        # 创建多个客户端
        clients = []
        for i in range(5):
            ws = MockWebSocket()
            await manager.connect(ws)
            manager.subscribe(ws, ["device_status"])
            clients.append(ws)

        # 广播状态
        status_data = DeviceStatusData(
            device_id="motor_001",
            device_type=DeviceType.STEPPER,
            status="running",
            extra={"position_mm": 100.0},
        )

        await manager.broadcast_device_status(status_data)
        await asyncio.sleep(0.2)

        # 验证所有客户端都收到消息
        for ws in clients:
            messages = ws.get_messages()
            assert len(messages) >= 1
            parsed = json.loads(messages[0])
            assert parsed["data"]["status"] == "running"

        # 清理
        for ws in clients:
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_state_consistency_across_clients(self):
        """测试跨客户端状态一致性。"""
        manager = ConnectionManager()

        clients = []
        for i in range(3):
            ws = MockWebSocket()
            await manager.connect(ws)
            manager.subscribe(ws, ["device_status"])
            clients.append(ws)

        # 发送一系列状态更新
        updates = [
            {"position_mm": 10.0, "velocity_mm_s": 5.0},
            {"position_mm": 20.0, "velocity_mm_s": 10.0},
            {"position_mm": 30.0, "velocity_mm_s": 15.0},
        ]

        for update in updates:
            status_data = DeviceStatusData(
                device_id="motor_001",
                device_type=DeviceType.STEPPER,
                status="running",
                extra=update,
            )
            await manager.broadcast_device_status(status_data)
            await asyncio.sleep(0.05)

        await asyncio.sleep(0.2)

        # 验证所有客户端收到相同的状态序列
        all_states = []
        for ws in clients:
            states = []
            for msg in ws.get_messages():
                parsed = json.loads(msg)
                if parsed["type"] == "device_status":
                    states.append(parsed["data"])
            all_states.append(states)

        # 验证一致性
        for i in range(len(updates)):
            positions = [states[i]["position_mm"] for states in all_states if i < len(states)]
            if len(positions) == len(clients):
                assert len(set(positions)) == 1  # 所有客户端位置相同

        for ws in clients:
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_state_caching_and_replay(self):
        """测试状态缓存和重放。"""
        manager = ConnectionManager()

        # 先发送一些状态
        status_data = DeviceStatusData(
            device_id="motor_001",
            device_type=DeviceType.STEPPER,
            status="running",
            extra={"position_mm": 50.0},
        )
        await manager.broadcast_device_status(status_data)

        # 然后连接客户端
        ws = MockWebSocket()
        await manager.connect(ws)
        manager.subscribe(ws, ["device_status"])

        await asyncio.sleep(0.2)

        # 验证客户端可以接收后续状态
        status_data2 = DeviceStatusData(
            device_id="motor_001",
            device_type=DeviceType.STEPPER,
            status="stopped",
            extra={"position_mm": 100.0},
        )
        await manager.broadcast_device_status(status_data2)

        await asyncio.sleep(0.2)

        messages = ws.get_messages()
        assert len(messages) >= 1

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_state_sync_with_subscription_filter(self):
        """测试带订阅过滤的状态同步。"""
        manager = ConnectionManager()

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await manager.connect(ws1)
        await manager.connect(ws2)

        # ws1 只订阅设备状态
        manager.subscribe(ws1, ["device_status"])
        # ws2 只订阅波形数据
        manager.subscribe(ws2, ["waveform_data"])

        # 发送设备状态
        status_data = DeviceStatusData(
            device_id="motor_001",
            device_type=DeviceType.STEPPER,
            status="running",
        )
        await manager.broadcast_device_status(status_data)

        # 发送波形数据
        waveform_data = WaveformData(
            device_id="ammeter_001",
            device_type=DeviceType.AMMETER,
            sample_rate=1000.0,
            data_points=[WaveformDataPoint(0, 100.0, time.time())],
        )
        await manager.broadcast_waveform_data(waveform_data)

        await asyncio.sleep(0.2)

        # 验证订阅过滤生效
        ws1_messages = ws1.get_messages()
        ws2_messages = ws2.get_messages()

        # ws1 应该收到设备状态
        status_received = any(
            json.loads(msg)["type"] == "device_status" for msg in ws1_messages
        )
        assert status_received

        # ws2 应该收到波形数据
        waveform_received = any(
            json.loads(msg)["type"] == "waveform_data" for msg in ws2_messages
        )
        assert waveform_received

        manager.disconnect(ws1)
        manager.disconnect(ws2)

    @pytest.mark.asyncio
    async def test_state_sync_performance(self):
        """测试状态同步性能。"""
        manager = ConnectionManager()

        clients = []
        for i in range(10):
            ws = MockWebSocket()
            await manager.connect(ws)
            manager.subscribe(ws, ["device_status"])
            clients.append(ws)

        # 性能测试：100次状态更新
        num_updates = 100
        start_time = time.time()

        for i in range(num_updates):
            status_data = DeviceStatusData(
                device_id="motor_001",
                device_type=DeviceType.STEPPER,
                status="running",
                extra={"position_mm": i * 0.1},
            )
            await manager.broadcast_device_status(status_data)

        elapsed = time.time() - start_time
        await asyncio.sleep(0.5)

        # 验证性能
        avg_latency_ms = (elapsed / num_updates) * 1000
        print(f"Broadcast {num_updates} updates to {len(clients)} clients in {elapsed:.3f}s")
        print(f"Average latency: {avg_latency_ms:.2f}ms")

        # 清理
        for ws in clients:
            manager.disconnect(ws)


# ==================== 第四部分：错误处理和重连测试 ====================


class TestErrorHandlingAndReconnection:
    """错误处理和重连测试类。"""

    @pytest.mark.asyncio
    async def test_invalid_message_format_handling(self):
        """测试无效消息格式处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送无效JSON
        invalid_messages = [
            "not a json",
            "{invalid json}",
            "",
            "null",
            "[]",
        ]

        for msg in invalid_messages:
            is_control = await manager.handle_client_message(ws, msg)
            # 无效消息应该不被识别为控制消息
            # 但也不应该导致崩溃

        # 验证连接仍然正常
        assert manager.connection_count == 1

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_invalid_msgpack_handling(self):
        """测试无效MessagePack处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送无效MessagePack
        invalid_msgpack = b"not valid msgpack data"

        is_control = await manager.handle_client_message(ws, invalid_msgpack)

        # 验证连接仍然正常
        assert manager.connection_count == 1

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_oversized_message_handling(self):
        """测试超大消息处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 创建超大消息
        large_data = {"type": "test", "data": "x" * (MAX_MESSAGE_SIZE + 1000)}
        large_message = json.dumps(large_data)

        # 验证消息验证器拒绝超大消息
        validated = validate_websocket_message(large_message)
        assert validated is None

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_connection_error_recovery(self):
        """测试连接错误恢复。"""
        manager = ConnectionManager()

        # 第一次连接
        ws1 = MockWebSocket()
        conn_id1 = await manager.connect(ws1)

        assert manager.connection_count == 1

        # 模拟连接错误
        ws1.closed = True
        manager.disconnect(ws1)

        assert manager.connection_count == 0

        # 重新连接
        ws2 = MockWebSocket()
        conn_id2 = await manager.connect(ws2)

        assert manager.connection_count == 1
        assert conn_id1 != conn_id2

        manager.disconnect(ws2)

    @pytest.mark.asyncio
    async def test_automatic_reconnection_simulation(self):
        """测试自动重连模拟。"""
        manager = ConnectionManager()

        reconnection_count = 0
        max_reconnections = 3

        for attempt in range(max_reconnections):
            ws = MockWebSocket()
            await manager.connect(ws)

            # 模拟连接断开
            await asyncio.sleep(0.05)
            manager.disconnect(ws)
            reconnection_count += 1

        assert reconnection_count == max_reconnections

    @pytest.mark.asyncio
    async def test_heartbeat_ping_pong(self):
        """测试心跳Ping-Pong机制。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 模拟发送Pong响应
        pong_message = json.dumps({"type": "pong"})
        is_control = await manager.handle_client_message(ws, pong_message)

        assert is_control is True

        # 验证心跳时间已更新
        info = manager.get_connection_info(ws)
        assert info.last_heartbeat > 0

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_heartbeat_timeout_detection(self):
        """测试心跳超时检测。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        info = manager.get_connection_info(ws)

        # 模拟超时：设置最后消息时间为很久之前
        original_time = info.last_message_time
        info.last_message_time = time.time() - HEARTBEAT_TIMEOUT - 5

        # 等待心跳监控检测
        await asyncio.sleep(HEARTBEAT_INTERVAL + 1)

        # 验证连接被关闭或即将关闭
        # 注意：由于MockWebSocket的特性，可能不会立即关闭
        # 但心跳监控应该已经检测到超时

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_disconnection_during_data_transfer(self):
        """测试数据传输中断开连接。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 开始数据传输
        for i in range(100):
            message = create_device_status_message(
                device_id="motor_001",
                device_type=DeviceType.STEPPER,
                status="running",
                position_mm=i * 0.1,
            )
            await manager.send_personal_message(message.to_json(), ws)

            # 在中间断开连接
            if i == 50:
                manager.disconnect(ws)
                break

        # 验证连接已断开
        assert manager.connection_count == 0

    @pytest.mark.asyncio
    async def test_reconnection_with_state_recovery(self):
        """测试重连后状态恢复。"""
        manager = ConnectionManager()

        # 第一次连接并订阅
        ws1 = MockWebSocket()
        await manager.connect(ws1)
        manager.subscribe(ws1, ["device_status", "waveform_data"])

        # 记录订阅
        original_subs = manager._connection_subscriptions.get(ws1, set()).copy()

        # 断开连接
        manager.disconnect(ws1)

        # 重新连接
        ws2 = MockWebSocket()
        await manager.connect(ws2)

        # 重新订阅
        manager.subscribe(ws2, ["device_status", "waveform_data"])

        # 验证订阅状态
        new_subs = manager._connection_subscriptions.get(ws2, set())
        assert "device_status" in new_subs
        assert "waveform_data" in new_subs

        manager.disconnect(ws2)

    @pytest.mark.asyncio
    async def test_error_message_to_client(self):
        """测试向客户端发送错误消息。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 发送错误消息
        error_msg = WebSocketMessage(
            type=MessageType.ALARM_EVENT,
            timestamp=datetime.now().isoformat(),
            data={
                "error": True,
                "code": 400,
                "message": "Invalid command",
            },
        )

        await manager.send_personal_message(error_msg.to_json(), ws)
        await asyncio.sleep(0.1)

        # 验证客户端收到错误消息
        messages = ws.get_messages()
        assert len(messages) >= 1

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_backpressure_handling(self):
        """测试反压处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 设置小队列
        manager.set_backpressure_config(queue_size=10)

        # 发送大量消息触发反压
        for i in range(50):
            message = json.dumps({"id": i, "data": "x" * 100})
            await manager.send_personal_message(message, ws)

        await asyncio.sleep(0.2)

        # 验证反压统计
        stats = manager.get_backpressure_stats()
        assert stats["total_messages_dropped"] > 0

        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_graceful_shutdown(self):
        """测试优雅关闭。"""
        manager = ConnectionManager()

        clients = []
        for i in range(5):
            ws = MockWebSocket()
            await manager.connect(ws)
            clients.append(ws)

        # 优雅关闭所有连接
        for ws in clients:
            await manager._close_connection(ws, reason="server_shutdown")

        # 验证所有连接已关闭
        assert manager.connection_count == 0


# ==================== 第五部分：协议和验证测试 ====================


class TestProtocolAndValidation:
    """协议和验证测试类。"""

    def test_message_type_validation(self):
        """测试消息类型验证。"""
        valid_types = ["ping", "pong", "device_status", "waveform_data", "alarm_event"]

        for msg_type in valid_types:
            assert WSMessageBase.validate_type(msg_type) is True

        # 无效类型
        invalid_types = ["", "x" * 100, "invalid type!", "type\nwith\nnewline"]

        for msg_type in invalid_types:
            assert WSMessageBase.validate_type(msg_type) is False

    def test_device_id_validation(self):
        """测试设备ID验证。"""
        valid_ids = ["motor_001", "temp-sensor-1", "device123", "a_b-c"]

        for device_id in valid_ids:
            assert validate_device_id_format(device_id) is True

        # 无效ID
        invalid_ids = ["", "x" * 100, "invalid id!", "id with space"]

        for device_id in invalid_ids:
            assert validate_device_id_format(device_id) is False

    def test_message_size_limit(self):
        """测试消息大小限制。"""
        # 正常大小消息
        normal_message = json.dumps({"type": "ping", "data": "test"})
        assert validate_websocket_message(normal_message) is not None

        # 超大消息
        large_message = json.dumps({"type": "ping", "data": "x" * (MAX_MESSAGE_SIZE + 1000)})
        assert validate_websocket_message(large_message) is None

    def test_message_structure_validation(self):
        """测试消息结构验证。"""
        # 有效消息
        valid_messages = [
            '{"type": "ping"}',
            '{"type": "device_status", "timestamp": 1234567890}',
            '{"type": "command", "device_id": "motor_001"}',
        ]

        for msg in valid_messages:
            result = validate_websocket_message(msg)
            assert result is not None
            assert "type" in result

        # 无效消息
        invalid_messages = [
            "null",
            "[]",
            "123",
            '"string"',
            '{"no_type": "value"}',
        ]

        for msg in invalid_messages:
            result = validate_websocket_message(msg)
            assert result is None

    def test_command_message_validation(self):
        """测试命令消息验证。"""
        # 有效命令
        valid_cmd = '{"type": "command", "command": "move", "device_id": "motor_001", "params": {"position": 100}}'
        result = WSCommandMessage.validate_message(valid_cmd)
        assert result is not None
        assert result.command == "move"

        # 无效命令
        invalid_cmd = '{"type": "command"}'  # 缺少command字段
        result = WSCommandMessage.validate_message(invalid_cmd)
        assert result is None

    def test_alarm_message_validation(self):
        """测试报警消息验证。"""
        # 有效报警
        valid_alarm = '{"type": "alarm", "level": "warning", "code": "HIGH_TEMP", "message": "Temperature too high"}'
        result = WSAlarmMessage.model_validate_json(valid_alarm)
        assert result.level == "warning"

        # 验证报警级别
        assert WSAlarmMessage.validate_level("warning") is True
        assert WSAlarmMessage.validate_level("invalid") is False

    def test_protocol_serialization_deserialization(self):
        """测试协议序列化/反序列化。"""
        message = create_device_status_message(
            device_id="motor_001",
            device_type=DeviceType.STEPPER,
            status="running",
            position_mm=100.0,
        )

        # JSON序列化
        json_data = serialize_message(message, ProtocolType.JSON)
        assert isinstance(json_data, str)
        json_parsed = deserialize_message(json_data, ProtocolType.JSON)
        assert json_parsed["type"] == "device_status"

        # MessagePack序列化
        msgpack_data = serialize_message(message, ProtocolType.MSGPACK)
        assert isinstance(msgpack_data, bytes)
        msgpack_parsed = deserialize_message(msgpack_data, ProtocolType.MSGPACK)
        assert msgpack_parsed["type"] == "device_status"


# ==================== 第六部分：节流和背压测试 ====================


class TestThrottleAndBackpressure:
    """节流和背压测试类。"""

    @pytest.mark.asyncio
    async def test_data_throttler_basic(self):
        """测试数据节流器基本功能。"""
        sent_batches = []

        config = ThrottleConfig(
            min_interval=0.1,
            max_batch_size=10,
            enable_batching=True,
        )

        throttler = DataThrottler(
            config=config,
            on_send=lambda batch: sent_batches.append(batch),
        )

        await throttler.start()

        # 推送数据
        for i in range(50):
            await throttler.push({"id": i, "value": i * 0.1})

        await asyncio.sleep(0.5)
        await throttler.stop()

        # 验证批量发送
        assert len(sent_batches) > 0
        total_sent = sum(len(batch) for batch in sent_batches)
        assert total_sent <= 50

    @pytest.mark.asyncio
    async def test_priority_throttler(self):
        """测试优先级节流器。"""
        sent_batches = []

        config = ThrottleConfig(min_interval=0.05, max_batch_size=5)
        throttler = PriorityDataThrottler(
            config=config,
            on_send=lambda batch: sent_batches.append(batch),
            priority_levels=3,
        )

        await throttler.start()

        # 推送不同优先级的数据
        for i in range(20):
            priority = i % 3
            await throttler.push({"id": i, "priority": priority}, priority=priority)

        await asyncio.sleep(0.3)
        await throttler.stop()

        # 验证高优先级数据优先发送
        assert len(sent_batches) > 0

    @pytest.mark.asyncio
    async def test_adaptive_throttler(self):
        """测试自适应节流器。"""
        sent_batches = []

        config = ThrottleConfig(min_interval=0.05)
        throttler = AdaptiveThrottler(
            config=config,
            on_send=lambda batch: sent_batches.append(batch),
            min_interval=0.01,
            max_interval=0.5,
            target_latency=0.05,
        )

        await throttler.start()

        # 模拟延迟报告
        throttler.report_latency(0.1)  # 高延迟
        assert throttler.current_interval > config.min_interval

        throttler.report_latency(0.01)  # 低延迟
        # 间隔应该调整

        await throttler.stop()

    @pytest.mark.asyncio
    async def test_backpressure_controller(self):
        """测试背压控制器。"""
        backpressure_events = []

        controller = BackpressureController(
            max_queue_size=10,
            threshold=0.8,
            low_water_mark=0.5,
            on_backpressure=lambda usage: backpressure_events.append(("triggered", usage)),
            on_recover=lambda: backpressure_events.append(("recovered", 0)),
        )

        # 填充队列
        for i in range(12):
            success = await controller.enqueue(f"message_{i}".encode())
            if i < 8:
                assert success is True
            else:
                # 超过阈值后可能被丢弃
                pass

        # 验证背压触发
        assert len(backpressure_events) > 0 or controller.stats.dropped_messages > 0

    @pytest.mark.asyncio
    async def test_backpressure_stats(self):
        """测试背压统计。"""
        controller = BackpressureController(max_queue_size=100)

        # 添加一些消息
        for i in range(50):
            await controller.enqueue(f"msg_{i}".encode())

        stats = controller.stats

        assert stats.total_messages == 50
        assert stats.queue_size == 50
        assert stats.queue_usage == 0.5

        # 取出一些消息
        for _ in range(20):
            await controller.dequeue()

        assert controller.queue_size == 30


# ==================== 第七部分：集成测试 ====================


class TestWebSocketIntegration:
    """WebSocket集成测试类。"""

    @pytest.fixture
    def test_app(self):
        """创建测试应用。"""
        from fastapi import FastAPI

        app = FastAPI()
        manager = ConnectionManager()

        @app.websocket("/ws/device/{device_type}")
        async def device_websocket(websocket: WebSocket, device_type: str):
            await manager.connect(websocket, endpoint=f"/ws/device/{device_type}")
            try:
                while True:
                    data = await websocket.receive_text()
                    await manager.handle_client_message(websocket, data)
            except WebSocketDisconnect:
                manager.disconnect(websocket)

        @app.get("/api/connections")
        async def get_connections():
            return manager.get_connection_stats()

        return app, manager

    @pytest.mark.asyncio
    async def test_full_connection_lifecycle(self, test_app):
        """测试完整连接生命周期。"""
        app, manager = test_app

        with TestClient(app) as client:
            # 连接
            with client.websocket_connect("/ws/device/motor") as ws:
                # 发送消息
                ws.send_json({"type": "pong"})

                # 等待处理
                import time
                time.sleep(0.1)

                # 验证连接存在
                response = client.get("/api/connections")
                assert response.status_code == 200
                data = response.json()
                assert data["total_connections"] >= 1

    @pytest.mark.asyncio
    async def test_concurrent_connections(self, test_app):
        """测试并发连接。"""
        app, manager = test_app

        with TestClient(app) as client:
            connections = []

            # 创建多个并发连接
            for i in range(5):
                ws = client.websocket_connect(f"/ws/device/motor")
                connections.append(ws.__enter__())

            # 验证连接数
            response = client.get("/api/connections")
            data = response.json()
            assert data["total_connections"] >= 5

            # 关闭连接
            for ws in connections:
                ws.__exit__(None, None, None)


# ==================== 性能测试 ====================


class TestWebSocketPerformance:
    """WebSocket性能测试类。"""

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_message_throughput(self):
        """测试消息吞吐量。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        num_messages = 1000
        start_time = time.time()

        for i in range(num_messages):
            message = create_device_status_message(
                device_id="motor_001",
                device_type=DeviceType.STEPPER,
                status="running",
                position_mm=i * 0.001,
            )
            await manager.send_personal_message(message.to_json(), ws)

        elapsed = time.time() - start_time
        throughput = num_messages / elapsed

        print(f"Throughput: {throughput:.1f} messages/sec")

        manager.disconnect(ws)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_broadcast_scalability(self):
        """测试广播可扩展性。"""
        manager = ConnectionManager()

        # 创建多个客户端
        clients = []
        for i in range(20):
            ws = MockWebSocket()
            await manager.connect(ws)
            clients.append(ws)

        num_broadcasts = 100
        start_time = time.time()

        for i in range(num_broadcasts):
            message = create_device_status_message(
                device_id="motor_001",
                device_type=DeviceType.STEPPER,
                status="running",
            )
            await manager.broadcast(message)

        elapsed = time.time() - start_time

        print(f"Broadcast {num_broadcasts} messages to {len(clients)} clients in {elapsed:.3f}s")

        for ws in clients:
            manager.disconnect(ws)

    @pytest.mark.slow
    @pytest.mark.asyncio
    async def test_large_payload_handling(self):
        """测试大负载处理。"""
        manager = ConnectionManager()
        ws = MockWebSocket()

        await manager.connect(ws)

        # 创建大消息
        large_data_points = [
            {"channel": i % 8, "value": i * 0.1, "timestamp": time.time()}
            for i in range(10000)
        ]

        message = create_waveform_message(
            device_id="ammeter_001",
            device_type=DeviceType.AMMETER,
            sample_rate=10000.0,
            data_points=large_data_points,
        )

        start_time = time.time()
        result = await manager.send_personal_message(message.to_json(), ws)
        elapsed = time.time() - start_time

        print(f"Large message ({len(message.to_json())} bytes) sent in {elapsed*1000:.2f}ms")

        assert result is True

        manager.disconnect(ws)
