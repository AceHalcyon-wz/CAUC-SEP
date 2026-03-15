"""
WebSocket 消息类型与路由模块

文件名: websocket.py
路径: backend/api/
功能: WebSocket消息路由模块，提供实时数据推送、连接管理、心跳检测等接口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI, msgpack, asyncio

主要功能：
- 定义统一的WebSocket消息格式
- 支持多种设备状态推送
- 实现消息类型路由
- 管理客户端连接
- 心跳检测机制（30秒超时）
- 推送频率控制
- 连接状态日志记录
- MessagePack协议支持（高性能二进制序列化）
- 协议协商机制（JSON/MessagePack）
- 反压控制机制（防止客户端缓冲区溢出）
- 消息队列监控与流量控制
- 消息确认机制（可选）

设备类型：
- stepper: 步进电机
- electromagnet: 电磁铁
- temperature: 温控系统
- piezo: 压电陶瓷
- ammeter: 微电流计

消息类型：
- device_status: 设备状态推送
- waveform_data: 波形数据推送
- alarm_event: 报警事件推送
- experiment_progress: 实验进度推送
- pong: 心跳响应

协议类型：
- json: JSON文本协议（默认，兼容性好）
- msgpack: MessagePack二进制协议（高性能）

配置参数：
- HEARTBEAT_INTERVAL: 心跳间隔（10秒）
- HEARTBEAT_TIMEOUT: 心跳超时（30秒）
- MAX_QUEUE_SIZE: 最大消息队列大小
- BACKPRESSURE_THRESHOLD: 反压阈值
"""

import asyncio
import json
import logging
import time
import uuid
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

import msgpack
from fastapi import WebSocket

logger = logging.getLogger(__name__)

# 心跳检测配置
HEARTBEAT_INTERVAL = 10.0  # 心跳间隔（秒）
HEARTBEAT_TIMEOUT = 30.0  # 心跳超时（秒）

# 反压控制配置
BACKPRESSURE_QUEUE_SIZE = 100  # 每个客户端的消息队列大小
BACKPRESSURE_WATERMARK_HIGH = 0.8  # 高水位线（队列使用率）
BACKPRESSURE_WATERMARK_LOW = 0.5  # 低水位线（队列使用率）
BACKPRESSURE_THROTTLE_DELAY = 0.05  # 节流延迟（秒）
MESSAGE_ACK_TIMEOUT = 5.0  # 消息确认超时（秒）
MAX_UNACKED_MESSAGES = 10  # 最大未确认消息数

# 默认推送频率配置
DEFAULT_PUSH_INTERVALS = {
    "stepper": 0.1,  # 步进电机：100ms
    "electromagnet": 0.1,  # 电磁铁：100ms
    "temperature": 0.5,  # 温控系统：500ms
    "piezo": 0.1,  # 压电陶瓷：100ms
    "ammeter": 0.1,  # 微电流计：100ms
    "all_devices": 0.2,  # 统一设备：200ms
}


class MessageType(str, Enum):
    """WebSocket 消息类型枚举。

    Attributes:
        DEVICE_STATUS: 设备状态推送
        WAVEFORM_DATA: 波形数据推送
        ALARM_EVENT: 报警事件推送
        EXPERIMENT_PROGRESS: 实验进度推送
        PING: 心跳请求
        PONG: 心跳响应
        MSG_ACK: 消息确认
        BACKPRESSURE_WARNING: 反压警告
        FLOW_CONTROL: 流量控制
    """

    DEVICE_STATUS = "device_status"
    WAVEFORM_DATA = "waveform_data"
    ALARM_EVENT = "alarm_event"
    EXPERIMENT_PROGRESS = "experiment_progress"
    PING = "ping"
    PONG = "pong"
    MSG_ACK = "msg_ack"
    BACKPRESSURE_WARNING = "backpressure_warning"
    FLOW_CONTROL = "flow_control"


class DeviceType(str, Enum):
    """设备类型枚举。

    Attributes:
        STEPPER: 步进电机
        ELECTROMAGNET: 电磁铁
        TEMPERATURE: 温控系统
        PIEZO: 压电陶瓷
        AMMETER: 微电流计
    """

    STEPPER = "stepper"
    ELECTROMAGNET = "electromagnet"
    TEMPERATURE = "temperature"
    PIEZO = "piezo"
    AMMETER = "ammeter"


class AlarmLevel(str, Enum):
    """报警级别枚举。

    Attributes:
        INFO: 信息提示
        WARNING: 警告
        ERROR: 错误
        CRITICAL: 严重错误
    """

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class ProtocolType(str, Enum):
    """WebSocket通信协议类型枚举。

    Attributes:
        JSON: JSON文本协议（默认，兼容性好）
        MSGPACK: MessagePack二进制协议（高性能，体积小）
    """

    JSON = "json"
    MSGPACK = "msgpack"


@dataclass
class WebSocketMessage:
    """WebSocket 消息数据类。

    Attributes:
        type: 消息类型
        timestamp: ISO8601 格式时间戳
        data: 消息数据字典
    """

    type: MessageType
    timestamp: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            Dict[str, Any]: 消息字典
        """
        return {
            "type": self.type.value,
            "timestamp": self.timestamp,
            "data": self.data,
        }

    def to_json(self) -> str:
        """转换为 JSON 字符串。

        Returns:
            str: JSON 字符串
        """
        return json.dumps(self.to_dict(), ensure_ascii=False)

    def to_msgpack(self) -> bytes:
        """转换为 MessagePack 二进制格式。

        MessagePack相比JSON的优势：
        - 序列化体积减少30-50%
        - 序列化/反序列化速度提升2-5倍
        - 适合高频数据传输场景（如波形数据）

        Returns:
            bytes: MessagePack 二进制数据
        """
        return msgpack.packb(self.to_dict(), use_bin_type=True)


@dataclass
class DeviceStatusData:
    """设备状态数据类。

    Attributes:
        device_id: 设备唯一标识
        device_type: 设备类型
        status: 设备状态
        connected: 是否已连接
        simulation: 是否仿真模式
        extra: 设备特定数据
    """

    device_id: str
    device_type: DeviceType
    status: str
    connected: bool = True
    simulation: bool = True
    extra: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            Dict[str, Any]: 状态数据字典
        """
        result = {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "status": self.status,
            "connected": self.connected,
            "simulation": self.simulation,
        }
        result.update(self.extra)
        return result


@dataclass
class WaveformDataPoint:
    """波形数据点数据类。

    Attributes:
        channel: 通道号
        value: 数值
        timestamp: 时间戳
    """

    channel: int
    value: float
    timestamp: float


@dataclass
class WaveformData:
    """波形数据类。

    Attributes:
        device_id: 设备唯一标识
        device_type: 设备类型
        sample_rate: 采样率
        data_points: 数据点列表
    """

    device_id: str
    device_type: DeviceType
    sample_rate: float
    data_points: list[WaveformDataPoint] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            Dict[str, Any]: 波形数据字典
        """
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "sample_rate": self.sample_rate,
            "data_points": [
                {
                    "channel": dp.channel,
                    "value": dp.value,
                    "timestamp": dp.timestamp,
                }
                for dp in self.data_points
            ],
        }


@dataclass
class AlarmEventData:
    """报警事件数据类。

    Attributes:
        device_id: 设备唯一标识
        device_type: 设备类型
        alarm_level: 报警级别
        alarm_code: 报警代码
        alarm_message: 报警消息
        alarm_time: 报警时间
        recoverable: 是否可恢复
    """

    device_id: str
    device_type: DeviceType
    alarm_level: AlarmLevel
    alarm_code: str
    alarm_message: str
    alarm_time: str
    recoverable: bool = True

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            Dict[str, Any]: 报警数据字典
        """
        return {
            "device_id": self.device_id,
            "device_type": self.device_type.value,
            "alarm_level": self.alarm_level.value,
            "alarm_code": self.alarm_code,
            "alarm_message": self.alarm_message,
            "alarm_time": self.alarm_time,
            "recoverable": self.recoverable,
        }


@dataclass
class ExperimentProgressData:
    """实验进度数据类。

    Attributes:
        experiment_id: 实验ID
        experiment_name: 实验名称
        progress: 进度（0-1）
        current_step: 当前步骤
        total_steps: 总步骤数
        elapsed_time: 已用时间（秒）
        estimated_remaining: 预计剩余时间（秒）
        status: 实验状态
    """

    experiment_id: int
    experiment_name: str
    progress: float
    current_step: int
    total_steps: int
    elapsed_time: float
    estimated_remaining: float
    status: str

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            Dict[str, Any]: 进度数据字典
        """
        return {
            "experiment_id": self.experiment_id,
            "experiment_name": self.experiment_name,
            "progress": round(self.progress, 4),
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "elapsed_time": round(self.elapsed_time, 2),
            "estimated_remaining": round(self.estimated_remaining, 2),
            "status": self.status,
        }


@dataclass
class BackpressureState:
    """反压状态数据类。

    监控客户端消息队列状态，实现反压控制。

    Attributes:
        message_queue: 消息队列（FIFO）
        queue_size: 队列最大容量
        high_watermark: 高水位线（队列使用率阈值）
        low_watermark: 低水位线（队列使用率阈值）
        is_throttled: 是否处于节流状态
        throttle_start_time: 节流开始时间
        total_messages_sent: 总发送消息数
        total_messages_dropped: 总丢弃消息数
        last_backpressure_warning: 最后一次反压警告时间
        unacked_messages: 未确认消息字典 {message_id: timestamp}
        ack_enabled: 是否启用消息确认机制
    """

    message_queue: deque = field(default_factory=lambda: deque(maxlen=BACKPRESSURE_QUEUE_SIZE))
    queue_size: int = BACKPRESSURE_QUEUE_SIZE
    high_watermark: float = BACKPRESSURE_WATERMARK_HIGH
    low_watermark: float = BACKPRESSURE_WATERMARK_LOW
    is_throttled: bool = False
    throttle_start_time: float = 0.0
    total_messages_sent: int = 0
    total_messages_dropped: int = 0
    last_backpressure_warning: float = 0.0
    unacked_messages: dict[str, float] = field(default_factory=dict)
    ack_enabled: bool = False

    @property
    def queue_usage(self) -> float:
        """计算队列使用率。

        Returns:
            float: 队列使用率（0.0-1.0）
        """
        return len(self.message_queue) / self.queue_size

    @property
    def should_throttle(self) -> bool:
        """判断是否应该启动节流。

        Returns:
            bool: 是否启动节流
        """
        return self.queue_usage >= self.high_watermark

    @property
    def can_resume(self) -> bool:
        """判断是否可以恢复正常发送。

        Returns:
            bool: 是否可以恢复
        """
        return self.queue_usage <= self.low_watermark

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            Dict[str, Any]: 反压状态字典
        """
        return {
            "queue_usage": round(self.queue_usage, 3),
            "queue_size": self.queue_size,
            "queued_messages": len(self.message_queue),
            "is_throttled": self.is_throttled,
            "total_messages_sent": self.total_messages_sent,
            "total_messages_dropped": self.total_messages_dropped,
            "unacked_count": len(self.unacked_messages),
            "ack_enabled": self.ack_enabled,
        }


@dataclass
class ConnectionInfo:
    """WebSocket 连接信息数据类。

    Attributes:
        connection_id: 连接唯一标识
        websocket: WebSocket 连接对象
        endpoint: 连接的端点路径
        connected_at: 连接建立时间
        last_heartbeat: 最后一次心跳时间
        last_message_time: 最后一次收到消息的时间
        messages_sent: 已发送消息数
        messages_received: 已接收消息数
        client_ip: 客户端IP地址
        protocol: 通信协议类型（json/msgpack）
        backpressure_state: 反压状态对象
        ack_enabled: 是否启用消息确认机制
    """

    connection_id: str
    websocket: WebSocket
    endpoint: str = ""
    connected_at: float = field(default_factory=time.time)
    last_heartbeat: float = field(default_factory=time.time)
    last_message_time: float = field(default_factory=time.time)
    messages_sent: int = 0
    messages_received: int = 0
    client_ip: str = "unknown"
    protocol: ProtocolType = ProtocolType.JSON
    backpressure_state: BackpressureState = field(default_factory=BackpressureState)
    ack_enabled: bool = False

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            Dict[str, Any]: 连接信息字典
        """
        return {
            "connection_id": self.connection_id,
            "endpoint": self.endpoint,
            "connected_at": datetime.fromtimestamp(self.connected_at).isoformat(),
            "connected_duration": round(time.time() - self.connected_at, 2),
            "last_heartbeat": datetime.fromtimestamp(self.last_heartbeat).isoformat(),
            "last_message_time": datetime.fromtimestamp(self.last_message_time).isoformat(),
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "client_ip": self.client_ip,
            "protocol": self.protocol.value,
            "backpressure": self.backpressure_state.to_dict(),
            "ack_enabled": self.ack_enabled,
        }


class ConnectionManager:
    """WebSocket 连接管理器。

    管理所有 WebSocket 客户端连接，支持：
    - 按订阅类型分组推送消息
    - 心跳检测机制（30秒超时）
    - 推送频率控制
    - 连接状态日志记录
    - 协议协商机制（JSON/MessagePack）
    - 高性能二进制序列化
    - 反压控制机制（防止客户端缓冲区溢出）
    - 消息队列监控与流量控制
    - 消息确认机制（可选）

    Example:
        >>> manager = ConnectionManager()
        >>> await manager.connect(websocket, endpoint="/ws/motor")
        >>> await manager.broadcast(message)
    """

    def __init__(self):
        """初始化连接管理器。"""
        # 活跃连接列表
        self._active_connections: list[WebSocket] = []

        # 连接信息映射
        self._connection_info: dict[WebSocket, ConnectionInfo] = {}

        # 按订阅类型分组的连接
        self._subscriptions: dict[str, list[WebSocket]] = {
            MessageType.DEVICE_STATUS.value: [],
            MessageType.WAVEFORM_DATA.value: [],
            MessageType.ALARM_EVENT.value: [],
            MessageType.EXPERIMENT_PROGRESS.value: [],
        }

        # 连接的订阅信息
        self._connection_subscriptions: dict[WebSocket, set[str]] = {}

        # 推送频率控制
        self._push_intervals: dict[str, float] = DEFAULT_PUSH_INTERVALS.copy()

        # 心跳任务映射
        self._heartbeat_tasks: dict[WebSocket, asyncio.Task] = {}

        # 反压监控任务映射
        self._backpressure_tasks: dict[WebSocket, asyncio.Task] = {}

        # 消息发送任务映射
        self._sender_tasks: dict[WebSocket, asyncio.Task] = {}

        logger.info("ConnectionManager initialized with backpressure control")

    async def connect(
        self,
        websocket: WebSocket,
        endpoint: str = "",
        client_ip: str = "unknown",
        protocol: ProtocolType = ProtocolType.JSON,
        ack_enabled: bool = False,
    ) -> str:
        """接受新的 WebSocket 连接。

        支持协议协商机制：
        - 客户端可通过查询参数指定协议类型（?protocol=msgpack）
        - 默认使用JSON协议确保向后兼容
        - MessagePack协议适合高频数据传输场景
        - 可选启用消息确认机制（?ack=true）

        Args:
            websocket: WebSocket 连接对象
            endpoint: 连接的端点路径
            client_ip: 客户端IP地址
            protocol: 通信协议类型（json/msgpack）
            ack_enabled: 是否启用消息确认机制

        Returns:
            str: 连接唯一标识
        """
        await websocket.accept()
        self._active_connections.append(websocket)
        self._connection_subscriptions[websocket] = set()

        # 创建连接信息（包含反压状态）
        connection_id = str(uuid.uuid4())[:8]
        connection_info = ConnectionInfo(
            connection_id=connection_id,
            websocket=websocket,
            endpoint=endpoint,
            client_ip=client_ip,
            protocol=protocol,
            ack_enabled=ack_enabled,
        )
        connection_info.backpressure_state.ack_enabled = ack_enabled
        self._connection_info[websocket] = connection_info

        # 启动心跳检测任务
        self._heartbeat_tasks[websocket] = asyncio.create_task(self._heartbeat_monitor(websocket))

        # 启动反压监控任务
        self._backpressure_tasks[websocket] = asyncio.create_task(
            self._backpressure_monitor(websocket)
        )

        # 启动消息发送任务
        self._sender_tasks[websocket] = asyncio.create_task(self._message_sender(websocket))

        logger.info(
            f"[WS-{connection_id}] Client connected from {client_ip}, "
            f"endpoint={endpoint}, protocol={protocol.value}, "
            f"ack_enabled={ack_enabled}, total={len(self._active_connections)}"
        )

        return connection_id

    async def _heartbeat_monitor(self, websocket: WebSocket) -> None:
        """心跳监控任务。

        定期检查连接是否超时，超时则断开连接。
        根据连接协议类型发送相应格式的心跳消息。

        Args:
            websocket: WebSocket 连接对象
        """
        connection_info = self._connection_info.get(websocket)
        if not connection_info:
            return

        connection_id = connection_info.connection_id
        protocol = connection_info.protocol

        try:
            while websocket in self._active_connections:
                await asyncio.sleep(HEARTBEAT_INTERVAL)

                # 检查是否超时
                time_since_last_msg = time.time() - connection_info.last_message_time

                if time_since_last_msg > HEARTBEAT_TIMEOUT:
                    logger.warning(
                        f"[WS-{connection_id}] Heartbeat timeout "
                        f"({time_since_last_msg:.1f}s > {HEARTBEAT_TIMEOUT}s), "
                        f"closing connection"
                    )
                    await self._close_connection(websocket, reason="heartbeat_timeout")
                    break

                # 发送心跳请求（根据协议类型选择格式）
                try:
                    ping_data = {
                        "type": MessageType.PING.value,
                        "timestamp": datetime.now().isoformat(),
                    }

                    if protocol == ProtocolType.MSGPACK:
                        # MessagePack二进制格式
                        ping_message = msgpack.packb(ping_data, use_bin_type=True)
                        await websocket.send_bytes(ping_message)
                    else:
                        # JSON文本格式（默认）
                        ping_message = json.dumps(ping_data)
                        await websocket.send_text(ping_message)

                    logger.debug(f"[WS-{connection_id}] Ping sent via {protocol.value}")
                except Exception as e:
                    logger.error(f"[WS-{connection_id}] Failed to send ping: {e}")
                    await self._close_connection(websocket, reason="ping_failed")
                    break

        except asyncio.CancelledError:
            logger.debug(f"[WS-{connection_id}] Heartbeat monitor cancelled")
        except Exception as e:
            logger.error(f"[WS-{connection_id}] Heartbeat monitor error: {e}")

    async def _backpressure_monitor(self, websocket: WebSocket) -> None:
        """反压监控任务。

        监控消息队列状态，实现反压控制：
        - 队列使用率超过高水位线时启动节流
        - 队列使用率低于低水位线时恢复正常发送
        - 定期清理超时的未确认消息

        Args:
            websocket: WebSocket 连接对象
        """
        connection_info = self._connection_info.get(websocket)
        if not connection_info:
            return

        connection_id = connection_info.connection_id
        backpressure_state = connection_info.backpressure_state

        try:
            while websocket in self._active_connections:
                await asyncio.sleep(0.5)  # 每0.5秒检查一次

                # 检查是否需要启动节流
                if backpressure_state.should_throttle and not backpressure_state.is_throttled:
                    backpressure_state.is_throttled = True
                    backpressure_state.throttle_start_time = time.time()

                    logger.warning(
                        f"[WS-{connection_id}] Backpressure activated: "
                        f"queue_usage={backpressure_state.queue_usage:.2%}"
                    )

                    # 发送反压警告
                    await self._send_backpressure_warning(websocket, backpressure_state)

                # 检查是否可以恢复正常发送
                elif backpressure_state.can_resume and backpressure_state.is_throttled:
                    backpressure_state.is_throttled = False
                    throttle_duration = time.time() - backpressure_state.throttle_start_time

                    logger.info(
                        f"[WS-{connection_id}] Backpressure deactivated: "
                        f"queue_usage={backpressure_state.queue_usage:.2%}, "
                        f"throttle_duration={throttle_duration:.2f}s"
                    )

                    # 发送流量恢复通知
                    await self._send_flow_control_resume(websocket)

                # 清理超时的未确认消息
                if backpressure_state.ack_enabled:
                    current_time = time.time()
                    expired_msgs = [
                        msg_id
                        for msg_id, timestamp in backpressure_state.unacked_messages.items()
                        if current_time - timestamp > MESSAGE_ACK_TIMEOUT
                    ]

                    for msg_id in expired_msgs:
                        del backpressure_state.unacked_messages[msg_id]
                        backpressure_state.total_messages_dropped += 1
                        logger.warning(f"[WS-{connection_id}] Message ack timeout: {msg_id}")

        except asyncio.CancelledError:
            logger.debug(f"[WS-{connection_id}] Backpressure monitor cancelled")
        except Exception as e:
            logger.error(f"[WS-{connection_id}] Backpressure monitor error: {e}")

    async def _message_sender(self, websocket: WebSocket) -> None:
        """消息发送任务。

        从消息队列中取出消息并发送，实现反压控制：
        - 节流状态下降低发送速率
        - 队列满时丢弃最旧的消息

        Args:
            websocket: WebSocket 连接对象
        """
        connection_info = self._connection_info.get(websocket)
        if not connection_info:
            return

        connection_id = connection_info.connection_id
        backpressure_state = connection_info.backpressure_state

        try:
            while websocket in self._active_connections:
                # 从队列中取出消息
                if not backpressure_state.message_queue:
                    await asyncio.sleep(0.01)  # 队列为空时短暂休眠
                    continue

                # 节流状态下延迟发送
                if backpressure_state.is_throttled:
                    await asyncio.sleep(BACKPRESSURE_THROTTLE_DELAY)

                # 取出消息
                message_data = backpressure_state.message_queue.popleft()

                # 检查是否需要等待消息确认
                if backpressure_state.ack_enabled:
                    # 等待未确认消息数降低
                    while len(backpressure_state.unacked_messages) >= MAX_UNACKED_MESSAGES:
                        await asyncio.sleep(0.01)

                    # 记录未确认消息
                    message_id = message_data.get("message_id", str(uuid.uuid4())[:8])
                    backpressure_state.unacked_messages[message_id] = time.time()

                # 发送消息
                try:
                    if isinstance(message_data["content"], bytes):
                        await websocket.send_bytes(message_data["content"])
                    else:
                        await websocket.send_text(message_data["content"])

                    backpressure_state.total_messages_sent += 1
                    self.update_message_stats(websocket, sent=True)

                except Exception as e:
                    logger.error(f"[WS-{connection_id}] Failed to send message: {e}")
                    backpressure_state.total_messages_dropped += 1

        except asyncio.CancelledError:
            logger.debug(f"[WS-{connection_id}] Message sender cancelled")
        except Exception as e:
            logger.error(f"[WS-{connection_id}] Message sender error: {e}")

    async def _send_backpressure_warning(
        self, websocket: WebSocket, backpressure_state: BackpressureState
    ) -> None:
        """发送反压警告消息。

        Args:
            websocket: WebSocket 连接对象
            backpressure_state: 反压状态对象
        """
        connection_info = self._connection_info.get(websocket)
        if not connection_info:
            return

        # 限制警告频率（每5秒最多一次）
        current_time = time.time()
        if current_time - backpressure_state.last_backpressure_warning < 5.0:
            return

        backpressure_state.last_backpressure_warning = current_time

        warning_data = {
            "type": MessageType.BACKPRESSURE_WARNING.value,
            "timestamp": datetime.now().isoformat(),
            "data": backpressure_state.to_dict(),
        }

        try:
            if connection_info.protocol == ProtocolType.MSGPACK:
                warning_message = msgpack.packb(warning_data, use_bin_type=True)
                await websocket.send_bytes(warning_message)
            else:
                warning_message = json.dumps(warning_data)
                await websocket.send_text(warning_message)
        except Exception as e:
            logger.error(f"Failed to send backpressure warning: {e}")

    async def _send_flow_control_resume(self, websocket: WebSocket) -> None:
        """发送流量恢复通知。

        Args:
            websocket: WebSocket 连接对象
        """
        connection_info = self._connection_info.get(websocket)
        if not connection_info:
            return

        resume_data = {
            "type": MessageType.FLOW_CONTROL.value,
            "timestamp": datetime.now().isoformat(),
            "data": {"status": "resumed"},
        }

        try:
            if connection_info.protocol == ProtocolType.MSGPACK:
                resume_message = msgpack.packb(resume_data, use_bin_type=True)
                await websocket.send_bytes(resume_message)
            else:
                resume_message = json.dumps(resume_data)
                await websocket.send_text(resume_message)
        except Exception as e:
            logger.error(f"Failed to send flow control resume: {e}")

    async def _close_connection(self, websocket: WebSocket, reason: str = "unknown") -> None:
        """关闭连接。

        Args:
            websocket: WebSocket 连接对象
            reason: 关闭原因
        """
        connection_info = self._connection_info.get(websocket)

        try:
            await websocket.close(code=1000, reason=reason)
        except Exception:
            pass

        self.disconnect(websocket)

        if connection_info:
            logger.info(
                f"[WS-{connection_info.connection_id}] Connection closed, "
                f"reason={reason}, duration={time.time() - connection_info.connected_at:.2f}s"
            )

    def update_heartbeat(self, websocket: WebSocket) -> None:
        """更新心跳时间。

        Args:
            websocket: WebSocket 连接对象
        """
        if websocket in self._connection_info:
            self._connection_info[websocket].last_heartbeat = time.time()
            self._connection_info[websocket].last_message_time = time.time()
            logger.debug(
                f"[WS-{self._connection_info[websocket].connection_id}] " f"Heartbeat updated"
            )

    def update_message_stats(
        self, websocket: WebSocket, sent: bool = False, received: bool = False
    ) -> None:
        """更新消息统计。

        Args:
            websocket: WebSocket 连接对象
            sent: 是否发送消息
            received: 是否接收消息
        """
        if websocket in self._connection_info:
            if sent:
                self._connection_info[websocket].messages_sent += 1
            if received:
                self._connection_info[websocket].messages_received += 1
                self._connection_info[websocket].last_message_time = time.time()

    def disconnect(self, websocket: WebSocket) -> None:
        """断开 WebSocket 连接。

        Args:
            websocket: WebSocket 连接对象
        """
        # 取消心跳任务
        if websocket in self._heartbeat_tasks:
            self._heartbeat_tasks[websocket].cancel()
            del self._heartbeat_tasks[websocket]

        # 取消反压监控任务
        if websocket in self._backpressure_tasks:
            self._backpressure_tasks[websocket].cancel()
            del self._backpressure_tasks[websocket]

        # 取消消息发送任务
        if websocket in self._sender_tasks:
            self._sender_tasks[websocket].cancel()
            del self._sender_tasks[websocket]

        if websocket in self._active_connections:
            self._active_connections.remove(websocket)

        # 清理订阅信息
        if websocket in self._connection_subscriptions:
            subscriptions = self._connection_subscriptions[websocket]
            for sub_type in subscriptions:
                if websocket in self._subscriptions.get(sub_type, []):
                    self._subscriptions[sub_type].remove(websocket)
            del self._connection_subscriptions[websocket]

        # 清理连接信息
        connection_info = self._connection_info.pop(websocket, None)

        if connection_info:
            backpressure_state = connection_info.backpressure_state
            logger.info(
                f"[WS-{connection_info.connection_id}] Client disconnected, "
                f"endpoint={connection_info.endpoint}, "
                f"duration={time.time() - connection_info.connected_at:.2f}s, "
                f"sent={connection_info.messages_sent}, "
                f"received={connection_info.messages_received}, "
                f"queue_dropped={backpressure_state.total_messages_dropped}, "
                f"remaining={len(self._active_connections)}"
            )
        else:
            logger.info(
                f"WebSocket client disconnected, "
                f"remaining connections: {len(self._active_connections)}"
            )

    def subscribe(self, websocket: WebSocket, message_types: list[str]) -> None:
        """订阅消息类型。

        Args:
            websocket: WebSocket 连接对象
            message_types: 要订阅的消息类型列表
        """
        if websocket not in self._connection_subscriptions:
            return

        for msg_type in message_types:
            if msg_type in self._subscriptions:
                if websocket not in self._subscriptions[msg_type]:
                    self._subscriptions[msg_type].append(websocket)
                self._connection_subscriptions[websocket].add(msg_type)

        logger.info(
            f"Client subscribed to: {message_types}, "
            f"total subscriptions: {len(self._connection_subscriptions[websocket])}"
        )

    def unsubscribe(self, websocket: WebSocket, message_types: list[str]) -> None:
        """取消订阅消息类型。

        Args:
            websocket: WebSocket 连接对象
            message_types: 要取消订阅的消息类型列表
        """
        if websocket not in self._connection_subscriptions:
            return

        for msg_type in message_types:
            if msg_type in self._subscriptions:
                if websocket in self._subscriptions[msg_type]:
                    self._subscriptions[msg_type].remove(websocket)
                self._connection_subscriptions[websocket].discard(msg_type)

        logger.info(f"Client unsubscribed from: {message_types}")

    async def send_personal_message(self, message: str | bytes, websocket: WebSocket) -> bool:
        """发送个人消息（通过消息队列）。

        支持JSON和MessagePack两种协议格式：
        - JSON: 传入str类型，使用send_text发送
        - MessagePack: 传入bytes类型，使用send_bytes发送

        实现反压控制：
        - 消息先进入队列，由发送任务异步发送
        - 队列满时丢弃最旧的消息

        Args:
            message: 消息内容（str或bytes）
            websocket: 目标 WebSocket 连接

        Returns:
            bool: 消息是否成功加入队列
        """
        connection_info = self._connection_info.get(websocket)
        if not connection_info:
            logger.debug("Connection not found in connection_info (may have been disconnected)")
            return False

        backpressure_state = connection_info.backpressure_state

        # 检查队列是否已满
        if len(backpressure_state.message_queue) >= backpressure_state.queue_size:
            # 队列满，丢弃最旧的消息
            backpressure_state.message_queue.popleft()
            backpressure_state.total_messages_dropped += 1
            logger.warning(
                f"[WS-{connection_info.connection_id}] Queue full, " f"dropping oldest message"
            )

        # 将消息加入队列
        message_data = {
            "content": message,
            "message_id": str(uuid.uuid4())[:8],
            "timestamp": time.time(),
        }
        backpressure_state.message_queue.append(message_data)

        return True

    async def broadcast(self, message: WebSocketMessage) -> None:
        """广播消息到所有连接（通过消息队列）。

        根据每个连接的协议类型自动选择消息格式：
        - JSON协议连接：发送JSON文本
        - MessagePack协议连接：发送二进制数据

        实现反压控制：
        - 消息先进入各连接的队列
        - 队列满时丢弃最旧的消息

        Args:
            message: WebSocket 消息对象
        """
        disconnected = []
        for connection in self._active_connections:
            try:
                connection_info = self._connection_info.get(connection)
                if not connection_info:
                    continue

                backpressure_state = connection_info.backpressure_state

                # 准备消息内容
                if connection_info.protocol == ProtocolType.MSGPACK:
                    message_content = message.to_msgpack()
                else:
                    message_content = message.to_json()

                # 检查队列是否已满
                if len(backpressure_state.message_queue) >= backpressure_state.queue_size:
                    backpressure_state.message_queue.popleft()
                    backpressure_state.total_messages_dropped += 1
                    logger.warning(
                        f"[WS-{connection_info.connection_id}] Queue full during broadcast"
                    )

                # 将消息加入队列
                message_data = {
                    "content": message_content,
                    "message_id": str(uuid.uuid4())[:8],
                    "timestamp": time.time(),
                }
                backpressure_state.message_queue.append(message_data)

            except Exception as e:
                logger.error(f"Broadcast error: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

    async def broadcast_by_type(self, message: WebSocketMessage) -> None:
        """按消息类型广播消息（通过消息队列）。

        只推送给订阅了该消息类型的客户端。
        根据每个连接的协议类型自动选择消息格式。

        实现反压控制：
        - 消息先进入各连接的队列
        - 队列满时丢弃最旧的消息

        Args:
            message: WebSocket 消息对象
        """
        msg_type = message.type.value
        subscribers = self._subscriptions.get(msg_type, [])

        if not subscribers:
            # 如果没有特定订阅者，广播给所有连接
            await self.broadcast(message)
            return

        disconnected = []
        for connection in subscribers:
            try:
                connection_info = self._connection_info.get(connection)
                if not connection_info:
                    continue

                backpressure_state = connection_info.backpressure_state

                # 准备消息内容
                if connection_info.protocol == ProtocolType.MSGPACK:
                    message_content = message.to_msgpack()
                else:
                    message_content = message.to_json()

                # 检查队列是否已满
                if len(backpressure_state.message_queue) >= backpressure_state.queue_size:
                    backpressure_state.message_queue.popleft()
                    backpressure_state.total_messages_dropped += 1
                    logger.warning(
                        f"[WS-{connection_info.connection_id}] Queue full during broadcast_by_type"
                    )

                # 将消息加入队列
                message_data = {
                    "content": message_content,
                    "message_id": str(uuid.uuid4())[:8],
                    "timestamp": time.time(),
                }
                backpressure_state.message_queue.append(message_data)

            except Exception as e:
                logger.error(f"Broadcast by type error: {e}")
                disconnected.append(connection)

        # 清理断开的连接
        for connection in disconnected:
            self.disconnect(connection)

    async def handle_client_message(self, websocket: WebSocket, message: str | bytes) -> bool:
        """处理客户端消息。

        处理心跳响应、订阅请求和消息确认。
        支持JSON和MessagePack两种协议格式。

        Args:
            websocket: WebSocket 连接对象
            message: 消息内容（str或bytes）

        Returns:
            bool: 是否为控制消息（心跳/订阅/确认）
        """
        self.update_message_stats(websocket, received=True)

        try:
            # 根据消息类型解析
            if isinstance(message, bytes):
                # MessagePack二进制格式
                data = msgpack.unpackb(message, raw=False)
            else:
                # JSON文本格式
                data = json.loads(message)

            msg_type = data.get("type")

            # 处理心跳响应
            if msg_type == MessageType.PONG.value:
                self.update_heartbeat(websocket)
                logger.debug(
                    f"[WS-{self._connection_info[websocket].connection_id}] "
                    f"Pong received, heartbeat updated"
                )
                return True

            # 处理消息确认
            if msg_type == MessageType.MSG_ACK.value:
                connection_info = self._connection_info.get(websocket)
                if connection_info and connection_info.backpressure_state.ack_enabled:
                    message_id = data.get("message_id")
                    if message_id in connection_info.backpressure_state.unacked_messages:
                        del connection_info.backpressure_state.unacked_messages[message_id]
                        logger.debug(
                            f"[WS-{connection_info.connection_id}] "
                            f"Message ack received: {message_id}"
                        )
                return True

            # 处理订阅请求
            if data.get("action") == "subscribe":
                message_types = data.get("types", [])
                self.subscribe(websocket, message_types)

                # 获取连接协议类型
                connection_info = self._connection_info.get(websocket)
                protocol = connection_info.protocol if connection_info else ProtocolType.JSON

                # 根据协议类型发送确认消息
                confirm_data = {
                    "type": "subscription_confirmed",
                    "timestamp": datetime.now().isoformat(),
                    "subscribed_types": message_types,
                }

                if protocol == ProtocolType.MSGPACK:
                    confirm_message = msgpack.packb(confirm_data, use_bin_type=True)
                else:
                    confirm_message = json.dumps(confirm_data)

                await self.send_personal_message(confirm_message, websocket)
                return True

            # 处理取消订阅请求
            if data.get("action") == "unsubscribe":
                message_types = data.get("types", [])
                self.unsubscribe(websocket, message_types)
                return True

        except (json.JSONDecodeError, msgpack.UnpackException) as e:
            logger.warning(f"Invalid message format: {e}, message[:100]={str(message)[:100]}")
        except Exception as e:
            logger.error(f"Error handling client message: {e}")

        return False

    def set_push_interval(self, device_type: str, interval: float) -> None:
        """设置推送频率。

        Args:
            device_type: 设备类型
            interval: 推送间隔（秒）
        """
        self._push_intervals[device_type] = interval
        logger.info(f"Push interval set: {device_type}={interval}s")

    def get_push_interval(self, device_type: str) -> float:
        """获取推送频率。

        Args:
            device_type: 设备类型

        Returns:
            float: 推送间隔（秒）
        """
        return self._push_intervals.get(device_type, 0.1)

    async def broadcast_device_status(self, status_data: DeviceStatusData) -> None:
        """广播设备状态消息。

        Args:
            status_data: 设备状态数据
        """
        message = WebSocketMessage(
            type=MessageType.DEVICE_STATUS,
            timestamp=datetime.now().isoformat(),
            data=status_data.to_dict(),
        )
        await self.broadcast_by_type(message)

    async def broadcast_waveform_data(self, waveform_data: WaveformData) -> None:
        """广播波形数据消息。

        Args:
            waveform_data: 波形数据
        """
        message = WebSocketMessage(
            type=MessageType.WAVEFORM_DATA,
            timestamp=datetime.now().isoformat(),
            data=waveform_data.to_dict(),
        )
        await self.broadcast_by_type(message)

    async def broadcast_alarm_event(self, alarm_data: AlarmEventData) -> None:
        """广播报警事件消息。

        Args:
            alarm_data: 报警事件数据
        """
        message = WebSocketMessage(
            type=MessageType.ALARM_EVENT,
            timestamp=datetime.now().isoformat(),
            data=alarm_data.to_dict(),
        )
        await self.broadcast_by_type(message)

    async def broadcast_experiment_progress(self, progress_data: ExperimentProgressData) -> None:
        """广播实验进度消息。

        Args:
            progress_data: 实验进度数据
        """
        message = WebSocketMessage(
            type=MessageType.EXPERIMENT_PROGRESS,
            timestamp=datetime.now().isoformat(),
            data=progress_data.to_dict(),
        )
        await self.broadcast_by_type(message)

    @property
    def connection_count(self) -> int:
        """获取当前连接数。

        Returns:
            int: 连接数量
        """
        return len(self._active_connections)

    def get_subscription_stats(self) -> dict[str, int]:
        """获取订阅统计信息。

        Returns:
            Dict[str, int]: 各消息类型的订阅数量
        """
        return {msg_type: len(connections) for msg_type, connections in self._subscriptions.items()}

    def get_connection_stats(self) -> dict[str, Any]:
        """获取连接统计信息。

        Returns:
            Dict[str, Any]: 连接统计信息
        """
        return {
            "total_connections": len(self._active_connections),
            "subscription_stats": self.get_subscription_stats(),
            "connections": [info.to_dict() for info in self._connection_info.values()],
            "push_intervals": self._push_intervals.copy(),
        }

    def get_connection_info(self, websocket: WebSocket) -> ConnectionInfo | None:
        """获取连接信息。

        Args:
            websocket: WebSocket 连接对象

        Returns:
            ConnectionInfo | None: 连接信息，不存在时返回 None
        """
        return self._connection_info.get(websocket)

    def get_backpressure_stats(self) -> dict[str, Any]:
        """获取所有连接的反压统计信息。

        Returns:
            Dict[str, Any]: 反压统计信息
        """
        stats = {
            "total_connections": len(self._active_connections),
            "connections_with_backpressure": 0,
            "total_messages_sent": 0,
            "total_messages_dropped": 0,
            "total_queued_messages": 0,
            "connections": [],
        }

        for connection_info in self._connection_info.values():
            backpressure_state = connection_info.backpressure_state

            if backpressure_state.is_throttled:
                stats["connections_with_backpressure"] += 1

            stats["total_messages_sent"] += backpressure_state.total_messages_sent
            stats["total_messages_dropped"] += backpressure_state.total_messages_dropped
            stats["total_queued_messages"] += len(backpressure_state.message_queue)

            stats["connections"].append(
                {
                    "connection_id": connection_info.connection_id,
                    "endpoint": connection_info.endpoint,
                    "queue_usage": round(backpressure_state.queue_usage, 3),
                    "is_throttled": backpressure_state.is_throttled,
                    "queued_messages": len(backpressure_state.message_queue),
                    "total_sent": backpressure_state.total_messages_sent,
                    "total_dropped": backpressure_state.total_messages_dropped,
                    "unacked_count": len(backpressure_state.unacked_messages),
                }
            )

        return stats

    def set_backpressure_config(
        self,
        queue_size: int | None = None,
        high_watermark: float | None = None,
        low_watermark: float | None = None,
    ) -> None:
        """设置反压控制配置。

        Args:
            queue_size: 队列大小
            high_watermark: 高水位线
            low_watermark: 低水位线
        """
        for connection_info in self._connection_info.values():
            backpressure_state = connection_info.backpressure_state

            if queue_size is not None:
                backpressure_state.queue_size = queue_size
                # 重新创建队列（保留现有消息）
                old_queue = list(backpressure_state.message_queue)
                backpressure_state.message_queue = deque(old_queue[-queue_size:], maxlen=queue_size)

            if high_watermark is not None:
                backpressure_state.high_watermark = high_watermark

            if low_watermark is not None:
                backpressure_state.low_watermark = low_watermark

        logger.info(
            f"Backpressure config updated: queue_size={queue_size}, "
            f"high_watermark={high_watermark}, low_watermark={low_watermark}"
        )


class MessageRouter:
    """消息路由器。

    根据设备类型和消息类型，将消息路由到相应的处理器。

    Example:
        >>> router = MessageRouter()
        >>> router.register_handler("stepper", handle_stepper_status)
        >>> await router.route(message)
    """

    def __init__(self):
        """初始化消息路由器。"""
        # 设备状态处理器映射
        self._status_handlers: dict[DeviceType, Callable] = {}

        # 波形数据处理器映射
        self._waveform_handlers: dict[DeviceType, Callable] = {}

        # 报警事件处理器映射
        self._alarm_handlers: dict[DeviceType, Callable] = {}

        logger.info("MessageRouter initialized")

    def register_status_handler(self, device_type: DeviceType, handler: Callable) -> None:
        """注册设备状态处理器。

        Args:
            device_type: 设备类型
            handler: 处理函数，签名为 async (device_id: str) -> DeviceStatusData
        """
        self._status_handlers[device_type] = handler
        logger.info(f"Registered status handler for device type: {device_type.value}")

    def register_waveform_handler(self, device_type: DeviceType, handler: Callable) -> None:
        """注册波形数据处理器。

        Args:
            device_type: 设备类型
            handler: 处理函数，签名为 async (device_id: str) -> WaveformData
        """
        self._waveform_handlers[device_type] = handler
        logger.info(f"Registered waveform handler for device type: {device_type.value}")

    def register_alarm_handler(self, device_type: DeviceType, handler: Callable) -> None:
        """注册报警事件处理器。

        Args:
            device_type: 设备类型
            handler: 处理函数，签名为 async (device_id: str) -> AlarmEventData
        """
        self._alarm_handlers[device_type] = handler
        logger.info(f"Registered alarm handler for device type: {device_type.value}")

    async def get_device_status(
        self, device_type: DeviceType, device_id: str
    ) -> DeviceStatusData | None:
        """获取设备状态。

        Args:
            device_type: 设备类型
            device_id: 设备ID

        Returns:
            DeviceStatusData | None: 设备状态数据，无处理器时返回 None
        """
        handler = self._status_handlers.get(device_type)
        if handler:
            try:
                return await handler(device_id)
            except Exception as e:
                logger.error(f"Status handler error for {device_type.value}: {e}")
                return None
        return None

    async def get_waveform_data(
        self, device_type: DeviceType, device_id: str
    ) -> WaveformData | None:
        """获取波形数据。

        Args:
            device_type: 设备类型
            device_id: 设备ID

        Returns:
            WaveformData | None: 波形数据，无处理器时返回 None
        """
        handler = self._waveform_handlers.get(device_type)
        if handler:
            try:
                return await handler(device_id)
            except Exception as e:
                logger.error(f"Waveform handler error for {device_type.value}: {e}")
                return None
        return None

    async def get_alarm_event(
        self, device_type: DeviceType, device_id: str
    ) -> AlarmEventData | None:
        """获取报警事件。

        Args:
            device_type: 设备类型
            device_id: 设备ID

        Returns:
            AlarmEventData | None: 报警事件数据，无处理器时返回 None
        """
        handler = self._alarm_handlers.get(device_type)
        if handler:
            try:
                return await handler(device_id)
            except Exception as e:
                logger.error(f"Alarm handler error for {device_type.value}: {e}")
                return None
        return None


# 全局连接管理器实例
manager = ConnectionManager()

# 全局消息路由器实例
router = MessageRouter()


def create_device_status_message(
    device_id: str,
    device_type: DeviceType,
    status: str,
    connected: bool = True,
    simulation: bool = True,
    **extra: Any,
) -> WebSocketMessage:
    """创建设备状态消息。

    Args:
        device_id: 设备唯一标识
        device_type: 设备类型
        status: 设备状态
        connected: 是否已连接
        simulation: 是否仿真模式
        **extra: 设备特定数据

    Returns:
        WebSocketMessage: WebSocket 消息对象

    Example:
        >>> msg = create_device_status_message(
        ...     device_id="stepper_01",
        ...     device_type=DeviceType.STEPPER,
        ...     status="ready",
        ...     position_mm=25.5
        ... )
    """
    status_data = DeviceStatusData(
        device_id=device_id,
        device_type=device_type,
        status=status,
        connected=connected,
        simulation=simulation,
        extra=extra,
    )

    return WebSocketMessage(
        type=MessageType.DEVICE_STATUS,
        timestamp=datetime.now().isoformat(),
        data=status_data.to_dict(),
    )


def create_waveform_message(
    device_id: str,
    device_type: DeviceType,
    sample_rate: float,
    data_points: list[dict[str, Any]],
) -> WebSocketMessage:
    """创建波形数据消息。

    Args:
        device_id: 设备唯一标识
        device_type: 设备类型
        sample_rate: 采样率
        data_points: 数据点列表，每个点包含 channel, value, timestamp

    Returns:
        WebSocketMessage: WebSocket 消息对象

    Example:
        >>> msg = create_waveform_message(
        ...     device_id="ammeter_01",
        ...     device_type=DeviceType.AMMETER,
        ...     sample_rate=100.0,
        ...     data_points=[
        ...         {"channel": 0, "value": 100.5, "timestamp": time.time()},
        ...         {"channel": 1, "value": 200.3, "timestamp": time.time()},
        ...     ]
        ... )
    """
    waveform_data = WaveformData(
        device_id=device_id,
        device_type=device_type,
        sample_rate=sample_rate,
        data_points=[
            WaveformDataPoint(
                channel=dp["channel"],
                value=dp["value"],
                timestamp=dp["timestamp"],
            )
            for dp in data_points
        ],
    )

    return WebSocketMessage(
        type=MessageType.WAVEFORM_DATA,
        timestamp=datetime.now().isoformat(),
        data=waveform_data.to_dict(),
    )


def create_alarm_message(
    device_id: str,
    device_type: DeviceType,
    alarm_level: AlarmLevel,
    alarm_code: str,
    alarm_message: str,
    recoverable: bool = True,
) -> WebSocketMessage:
    """创建报警事件消息。

    Args:
        device_id: 设备唯一标识
        device_type: 设备类型
        alarm_level: 报警级别
        alarm_code: 报警代码
        alarm_message: 报警消息
        recoverable: 是否可恢复

    Returns:
        WebSocketMessage: WebSocket 消息对象

    Example:
        >>> msg = create_alarm_message(
        ...     device_id="temp_01",
        ...     device_type=DeviceType.TEMPERATURE,
        ...     alarm_level=AlarmLevel.WARNING,
        ...     alarm_code="HIGH_TEMP",
        ...     alarm_message="温度超过安全阈值"
        ... )
    """
    alarm_data = AlarmEventData(
        device_id=device_id,
        device_type=device_type,
        alarm_level=alarm_level,
        alarm_code=alarm_code,
        alarm_message=alarm_message,
        alarm_time=datetime.now().isoformat(),
        recoverable=recoverable,
    )

    return WebSocketMessage(
        type=MessageType.ALARM_EVENT,
        timestamp=datetime.now().isoformat(),
        data=alarm_data.to_dict(),
    )


def create_experiment_progress_message(
    experiment_id: int,
    experiment_name: str,
    progress: float,
    current_step: int,
    total_steps: int,
    elapsed_time: float,
    estimated_remaining: float,
    status: str,
) -> WebSocketMessage:
    """创建实验进度消息。

    Args:
        experiment_id: 实验ID
        experiment_name: 实验名称
        progress: 进度（0-1）
        current_step: 当前步骤
        total_steps: 总步骤数
        elapsed_time: 已用时间（秒）
        estimated_remaining: 预计剩余时间（秒）
        status: 实验状态

    Returns:
        WebSocketMessage: WebSocket 消息对象

    Example:
        >>> msg = create_experiment_progress_message(
        ...     experiment_id=1,
        ...     experiment_name="磁场扫描实验",
        ...     progress=0.5,
        ...     current_step=5,
        ...     total_steps=10,
        ...     elapsed_time=300.0,
        ...     estimated_remaining=300.0,
        ...     status="running"
        ... )
    """
    progress_data = ExperimentProgressData(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        progress=progress,
        current_step=current_step,
        total_steps=total_steps,
        elapsed_time=elapsed_time,
        estimated_remaining=estimated_remaining,
        status=status,
    )

    return WebSocketMessage(
        type=MessageType.EXPERIMENT_PROGRESS,
        timestamp=datetime.now().isoformat(),
        data=progress_data.to_dict(),
    )


def parse_protocol_from_query(query_params: dict[str, str]) -> ProtocolType:
    """从查询参数解析协议类型。

    协议协商机制：
    - 客户端通过查询参数指定协议：?protocol=msgpack
    - 不指定或指定无效值时默认使用JSON协议
    - 确保向后兼容性

    Args:
        query_params: 查询参数字典

    Returns:
        ProtocolType: 协议类型枚举

    Example:
        >>> params = {"protocol": "msgpack"}
        >>> protocol = parse_protocol_from_query(params)
        >>> print(protocol)
        ProtocolType.MSGPACK
    """
    protocol_str = query_params.get("protocol", "json").lower()

    try:
        return ProtocolType(protocol_str)
    except ValueError:
        logger.warning(f"Invalid protocol '{protocol_str}', falling back to JSON")
        return ProtocolType.JSON


def serialize_message(message: WebSocketMessage, protocol: ProtocolType) -> str | bytes:
    """根据协议类型序列化消息。

    统一的序列化接口，简化消息发送逻辑。

    Args:
        message: WebSocket 消息对象
        protocol: 协议类型

    Returns:
        str | bytes: 序列化后的消息（JSON字符串或MessagePack字节）

    Example:
        >>> msg = create_device_status_message(...)
        >>> json_data = serialize_message(msg, ProtocolType.JSON)
        >>> msgpack_data = serialize_message(msg, ProtocolType.MSGPACK)
    """
    if protocol == ProtocolType.MSGPACK:
        return message.to_msgpack()
    else:
        return message.to_json()


def deserialize_message(data: str | bytes, protocol: ProtocolType) -> dict[str, Any]:
    """根据协议类型反序列化消息。

    统一的反序列化接口，简化消息接收逻辑。

    Args:
        data: 序列化的消息数据
        protocol: 协议类型

    Returns:
        Dict[str, Any]: 反序列化后的字典

    Raises:
        json.JSONDecodeError: JSON解析失败
        msgpack.UnpackException: MessagePack解析失败

    Example:
        >>> data = b'\\x82\\xa4type\\xa4ping\\xa9timestamp\\xb72026-03-07...'
        >>> msg_dict = deserialize_message(data, ProtocolType.MSGPACK)
    """
    if isinstance(data, bytes) or protocol == ProtocolType.MSGPACK:
        return msgpack.unpackb(data if isinstance(data, bytes) else data.encode(), raw=False)
    else:
        return json.loads(data)


def parse_ack_enabled_from_query(query_params: dict[str, str]) -> bool:
    """从查询参数解析是否启用消息确认机制。

    Args:
        query_params: 查询参数字典

    Returns:
        bool: 是否启用消息确认

    Example:
        >>> params = {"ack": "true"}
        >>> ack_enabled = parse_ack_enabled_from_query(params)
        >>> print(ack_enabled)
        True
    """
    ack_str = query_params.get("ack", "false").lower()
    return ack_str in ("true", "1", "yes")


def create_backpressure_warning_message(
    queue_usage: float,
    is_throttled: bool,
    queue_size: int,
) -> WebSocketMessage:
    """创建反压警告消息。

    Args:
        queue_usage: 队列使用率
        is_throttled: 是否处于节流状态
        queue_size: 队列大小

    Returns:
        WebSocketMessage: 反压警告消息对象

    Example:
        >>> msg = create_backpressure_warning_message(0.85, True, 100)
        >>> print(msg.type)
        MessageType.BACKPRESSURE_WARNING
    """
    return WebSocketMessage(
        type=MessageType.BACKPRESSURE_WARNING,
        timestamp=datetime.now().isoformat(),
        data={
            "queue_usage": round(queue_usage, 3),
            "is_throttled": is_throttled,
            "queue_size": queue_size,
            "warning": "Message queue is nearly full, throttling activated",
        },
    )


def create_flow_control_message(status: str) -> WebSocketMessage:
    """创建流量控制消息。

    Args:
        status: 流量控制状态（resumed/throttled）

    Returns:
        WebSocketMessage: 流量控制消息对象

    Example:
        >>> msg = create_flow_control_message("resumed")
        >>> print(msg.type)
        MessageType.FLOW_CONTROL
    """
    return WebSocketMessage(
        type=MessageType.FLOW_CONTROL,
        timestamp=datetime.now().isoformat(),
        data={
            "status": status,
            "message": f"Flow control status changed to {status}",
        },
    )
