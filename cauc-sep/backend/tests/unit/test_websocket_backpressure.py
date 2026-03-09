"""
单元测试：WebSocket反压控制机制

测试内容：
- 消息队列监控
- 反压控制机制
- 消息确认机制
- 客户端缓冲区溢出保护

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

import asyncio

import pytest

from api.websocket import (
    BACKPRESSURE_QUEUE_SIZE,
    BACKPRESSURE_WATERMARK_HIGH,
    BACKPRESSURE_WATERMARK_LOW,
    BackpressureState,
    ConnectionInfo,
    ConnectionManager,
    MessageType,
    create_backpressure_warning_message,
    create_flow_control_message,
    parse_ack_enabled_from_query,
)


class TestBackpressureState:
    """测试反压状态数据类。"""

    def test_backpressure_state_initialization(self):
        """测试反压状态初始化。"""
        state = BackpressureState()

        assert state.queue_size == BACKPRESSURE_QUEUE_SIZE
        assert state.high_watermark == BACKPRESSURE_WATERMARK_HIGH
        assert state.low_watermark == BACKPRESSURE_WATERMARK_LOW
        assert state.is_throttled is False
        assert state.total_messages_sent == 0
        assert state.total_messages_dropped == 0
        assert len(state.message_queue) == 0

    def test_queue_usage_calculation(self):
        """测试队列使用率计算。"""
        state = BackpressureState()

        # 空队列
        assert state.queue_usage == 0.0

        # 添加消息
        for i in range(50):
            state.message_queue.append({"id": i})

        # 队列使用率应为50%
        assert abs(state.queue_usage - 0.5) < 0.01

    def test_should_throttle(self):
        """测试节流判断。"""
        state = BackpressureState()

        # 低于高水位线，不应节流
        assert state.should_throttle is False

        # 添加消息直到超过高水位线
        for i in range(int(BACKPRESSURE_QUEUE_SIZE * BACKPRESSURE_WATERMARK_HIGH) + 1):
            state.message_queue.append({"id": i})

        # 超过高水位线，应该节流
        assert state.should_throttle is True

    def test_can_resume(self):
        """测试恢复正常发送判断。"""
        state = BackpressureState()
        state.is_throttled = True

        # 队列满时，不能恢复
        for i in range(BACKPRESSURE_QUEUE_SIZE):
            state.message_queue.append({"id": i})
        assert state.can_resume is False

        # 清空队列到低水位线以下
        while state.queue_usage > BACKPRESSURE_WATERMARK_LOW:
            state.message_queue.popleft()

        # 可以恢复
        assert state.can_resume is True

    def test_to_dict(self):
        """测试转换为字典。"""
        state = BackpressureState()
        state.total_messages_sent = 100
        state.total_messages_dropped = 5
        state.is_throttled = True

        result = state.to_dict()

        assert result["queue_usage"] == 0.0
        assert result["queue_size"] == BACKPRESSURE_QUEUE_SIZE
        assert result["is_throttled"] is True
        assert result["total_messages_sent"] == 100
        assert result["total_messages_dropped"] == 5


class TestConnectionInfoWithBackpressure:
    """测试包含反压状态的连接信息。"""

    def test_connection_info_includes_backpressure(self):
        """测试连接信息包含反压状态。"""

        class MockWebSocket:
            pass

        ws = MockWebSocket()
        info = ConnectionInfo(
            connection_id="test_01",
            websocket=ws,
            endpoint="/ws/test",
        )

        assert info.backpressure_state is not None
        assert isinstance(info.backpressure_state, BackpressureState)

    def test_connection_info_to_dict_includes_backpressure(self):
        """测试连接信息字典包含反压状态。"""

        class MockWebSocket:
            pass

        ws = MockWebSocket()
        info = ConnectionInfo(
            connection_id="test_01",
            websocket=ws,
            endpoint="/ws/test",
        )
        info.backpressure_state.total_messages_sent = 50

        result = info.to_dict()

        assert "backpressure" in result
        assert result["backpressure"]["total_messages_sent"] == 50


class TestConnectionManagerBackpressure:
    """测试连接管理器的反压控制。"""

    @pytest.mark.asyncio
    async def test_connect_with_backpressure_tasks(self):
        """测试连接时启动反压监控任务。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False

            async def accept(self):
                self.accepted = True

        ws = MockWebSocket()
        connection_id = await manager.connect(ws, endpoint="/ws/test")

        # 验证连接成功
        assert connection_id is not None
        assert len(manager._active_connections) == 1

        # 验证启动了反压监控任务
        assert ws in manager._backpressure_tasks
        assert ws in manager._sender_tasks

        # 清理
        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_send_personal_message_queues_message(self):
        """测试发送个人消息通过队列。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, message):
                self.sent_messages.append(message)

        ws = MockWebSocket()
        await manager.connect(ws)

        # 发送消息
        result = await manager.send_personal_message("test message", ws)

        # 验证消息加入队列
        assert result is True
        connection_info = manager.get_connection_info(ws)
        assert len(connection_info.backpressure_state.message_queue) == 1

        # 等待消息发送
        await asyncio.sleep(0.1)

        # 验证消息已发送
        assert len(ws.sent_messages) == 1

        # 清理
        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_queue_full_drops_oldest_message(self):
        """测试队列满时丢弃最旧消息。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False
                self.sent_messages = []

            async def accept(self):
                self.accepted = True

            async def send_text(self, message):
                self.sent_messages.append(message)

        ws = MockWebSocket()
        await manager.connect(ws)

        connection_info = manager.get_connection_info(ws)
        backpressure_state = connection_info.backpressure_state

        # 填满队列
        for i in range(BACKPRESSURE_QUEUE_SIZE):
            await manager.send_personal_message(f"message_{i}", ws)

        assert len(backpressure_state.message_queue) == BACKPRESSURE_QUEUE_SIZE

        # 再发送一条消息，应该丢弃最旧的
        await manager.send_personal_message("new_message", ws)

        assert backpressure_state.total_messages_dropped == 1
        # 队列大小仍为最大值
        assert len(backpressure_state.message_queue) == BACKPRESSURE_QUEUE_SIZE

        # 清理
        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_backpressure_stats(self):
        """测试反压统计信息。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False

            async def accept(self):
                self.accepted = True

        # 创建多个连接
        for i in range(3):
            ws = MockWebSocket()
            await manager.connect(ws)

        # 获取统计信息
        stats = manager.get_backpressure_stats()

        assert stats["total_connections"] == 3
        assert stats["total_messages_sent"] == 0
        assert stats["total_messages_dropped"] == 0
        assert len(stats["connections"]) == 3

        # 清理
        for ws in list(manager._active_connections):
            manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_set_backpressure_config(self):
        """测试设置反压配置。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False

            async def accept(self):
                self.accepted = True

        ws = MockWebSocket()
        await manager.connect(ws)

        # 修改配置
        manager.set_backpressure_config(
            queue_size=50,
            high_watermark=0.9,
            low_watermark=0.4,
        )

        connection_info = manager.get_connection_info(ws)
        backpressure_state = connection_info.backpressure_state

        assert backpressure_state.queue_size == 50
        assert backpressure_state.high_watermark == 0.9
        assert backpressure_state.low_watermark == 0.4

        # 清理
        manager.disconnect(ws)


class TestMessageAcknowledgment:
    """测试消息确认机制。"""

    def test_parse_ack_enabled_from_query(self):
        """测试从查询参数解析消息确认开关。"""
        # 启用
        assert parse_ack_enabled_from_query({"ack": "true"}) is True
        assert parse_ack_enabled_from_query({"ack": "1"}) is True
        assert parse_ack_enabled_from_query({"ack": "yes"}) is True

        # 禁用
        assert parse_ack_enabled_from_query({"ack": "false"}) is False
        assert parse_ack_enabled_from_query({}) is False

    @pytest.mark.asyncio
    async def test_ack_enabled_connection(self):
        """测试启用消息确认的连接。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False

            async def accept(self):
                self.accepted = True

        ws = MockWebSocket()
        await manager.connect(ws, ack_enabled=True)

        connection_info = manager.get_connection_info(ws)

        assert connection_info.ack_enabled is True
        assert connection_info.backpressure_state.ack_enabled is True

        # 清理
        manager.disconnect(ws)

    @pytest.mark.asyncio
    async def test_handle_message_ack(self):
        """测试处理消息确认。"""
        manager = ConnectionManager()

        class MockWebSocket:
            def __init__(self):
                self.accepted = False

            async def accept(self):
                self.accepted = True

        ws = MockWebSocket()
        await manager.connect(ws, ack_enabled=True)

        connection_info = manager.get_connection_info(ws)
        backpressure_state = connection_info.backpressure_state

        # 添加未确认消息
        backpressure_state.unacked_messages["msg_001"] = 100.0

        # 处理确认消息
        ack_message = '{"type": "msg_ack", "message_id": "msg_001"}'
        result = await manager.handle_client_message(ws, ack_message)

        # 验证确认成功
        assert result is True
        assert "msg_001" not in backpressure_state.unacked_messages

        # 清理
        manager.disconnect(ws)


class TestBackpressureMessages:
    """测试反压相关消息。"""

    def test_create_backpressure_warning_message(self):
        """测试创建反压警告消息。"""
        message = create_backpressure_warning_message(
            queue_usage=0.85,
            is_throttled=True,
            queue_size=100,
        )

        assert message.type == MessageType.BACKPRESSURE_WARNING
        assert message.data["queue_usage"] == 0.85
        assert message.data["is_throttled"] is True
        assert message.data["queue_size"] == 100

    def test_create_flow_control_message(self):
        """测试创建流量控制消息。"""
        message = create_flow_control_message("resumed")

        assert message.type == MessageType.FLOW_CONTROL
        assert message.data["status"] == "resumed"


class TestMessageType:
    """测试新增的消息类型。"""

    def test_backpressure_message_types(self):
        """测试反压相关消息类型。"""
        assert MessageType.MSG_ACK.value == "msg_ack"
        assert MessageType.BACKPRESSURE_WARNING.value == "backpressure_warning"
        assert MessageType.FLOW_CONTROL.value == "flow_control"
