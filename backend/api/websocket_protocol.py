"""
WebSocket 消息协议定义。

提供 MessagePack 二进制序列化支持，相比 JSON 减少 30-50% 体积，
提升 2-5 倍序列化/反序列化速度。

文件路径: backend/api/websocket_protocol.py
功能: 定义 WebSocket 消息类型、基类和序列化方法
作者: Agent
创建日期: 2026-03-16
依赖: msgpack, pydantic
"""

import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Self

import msgpack

logger = logging.getLogger(__name__)


class MessageType(str, Enum):
    """
    WebSocket 消息类型枚举。

    定义系统中所有 WebSocket 消息的类型标识。
    """

    DEVICE_STATUS = "device_status"
    WAVEFORM = "waveform"
    HEARTBEAT = "heartbeat"
    HEARTBEAT_ACK = "heartbeat_ack"
    ERROR = "error"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    BACKPRESSURE_WARNING = "backpressure_warning"
    FLOW_CONTROL = "flow_control"


@dataclass
class WSMessage:
    """
    WebSocket 消息基类。

    所有 WebSocket 消息都应继承此类，提供统一的序列化接口。

    Attributes:
        type: 消息类型
        timestamp: 消息时间戳（Unix 时间戳）

    Example:
        >>> msg = WSMessage(type=MessageType.HEARTBEAT)
        >>> json_data = msg.to_json()
        >>> msgpack_data = msg.to_msgpack()
    """

    type: MessageType
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式。

        Returns:
            dict[str, Any]: 消息的字典表示
        """
        data = asdict(self)
        # 将枚举转换为字符串值
        data["type"] = self.type.value
        return data

    def to_json(self) -> str:
        """
        序列化为 JSON 字符串。

        Returns:
            str: JSON 格式的消息字符串
        """
        return json.dumps(self.to_dict())

    def to_msgpack(self) -> bytes:
        """
        序列化为 MessagePack 二进制格式。

        MessagePack 相比 JSON 有以下优势：
        - 体积减少 30-50%
        - 序列化/反序列化速度提升 2-5 倍
        - 适合高频数据推送场景

        Returns:
            bytes: MessagePack 二进制数据
        """
        return msgpack.packb(self.to_dict())

    @classmethod
    def from_msgpack(cls, data: bytes) -> Self:
        """
        从 MessagePack 二进制数据反序列化。

        Args:
            data: MessagePack 二进制数据

        Returns:
            Self: 反序列化后的消息对象

        Raises:
            ValueError: 数据格式无效
        """
        try:
            unpacked = msgpack.unpackb(data, raw=False)
            # 将字符串类型转换回枚举
            if "type" in unpacked and isinstance(unpacked["type"], str):
                unpacked["type"] = MessageType(unpacked["type"])
            return cls(**unpacked)
        except (msgpack.UnpackException, KeyError) as e:
            logger.error(f"Failed to deserialize MessagePack: {e}")
            raise ValueError(f"Invalid MessagePack data: {e}") from e


@dataclass
class DeviceStatusMessage(WSMessage):
    """
    设备状态消息。

    用于推送设备的实时状态信息。

    Attributes:
        type: 消息类型（默认为 DEVICE_STATUS）
        device_id: 设备唯一标识
        device_type: 设备类型（motor, electromagnet 等）
        status: 设备状态字符串
        connected: 是否已连接
        simulation: 是否为仿真模式
        data: 设备详细数据字典

    Example:
        >>> msg = DeviceStatusMessage(
        ...     device_id="motor-001",
        ...     device_type="motor",
        ...     status="running",
        ...     connected=True,
        ...     simulation=False,
        ...     data={"position": 100.0, "velocity": 50.0}
        ... )
    """

    type: MessageType = field(default=MessageType.DEVICE_STATUS, init=False)
    device_id: str = ""
    device_type: str = ""
    status: str = ""
    connected: bool = False
    simulation: bool = False
    data: dict[str, Any] = field(default_factory=dict)


@dataclass
class WaveformMessage(WSMessage):
    """
    波形数据消息。

    用于推送高频波形数据（如压电传感器、电流表数据）。

    Attributes:
        type: 消息类型（默认为 WAVEFORM）
        device_id: 设备唯一标识
        device_type: 设备类型
        sample_rate: 采样率（Hz）
        channels: 通道数
        data_points: 数据点列表，每个点包含时间戳和各通道值

    Example:
        >>> msg = WaveformMessage(
        ...     device_id="piezo-001",
        ...     device_type="piezo",
        ...     sample_rate=10000.0,
        ...     channels=2,
        ...     data_points=[
        ...         {"t": 0.0, "ch1": 1.23, "ch2": 4.56},
        ...         {"t": 0.0001, "ch1": 1.24, "ch2": 4.57}
        ...     ]
        ... )
    """

    type: MessageType = field(default=MessageType.WAVEFORM, init=False)
    device_id: str = ""
    device_type: str = ""
    sample_rate: float = 0.0
    channels: int = 1
    data_points: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class HeartbeatMessage(WSMessage):
    """
    心跳消息。

    用于保持 WebSocket 连接活跃，检测连接状态。

    Attributes:
        type: 消息类型（默认为 HEARTBEAT）
        server_time: 服务器时间戳

    Example:
        >>> msg = HeartbeatMessage()
        >>> # 客户端收到后应回复 HeartbeatAckMessage
    """

    type: MessageType = field(default=MessageType.HEARTBEAT, init=False)
    server_time: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class HeartbeatAckMessage(WSMessage):
    """
    心跳确认消息。

    客户端收到心跳消息后应回复此消息。

    Attributes:
        type: 消息类型（默认为 HEARTBEAT_ACK）
        client_time: 客户端发送时间戳
        server_time: 服务器时间戳（来自心跳消息）

    Example:
        >>> ack = HeartbeatAckMessage(
        ...     client_time=time.time(),
        ...     server_time=heartbeat.server_time
        ... )
    """

    type: MessageType = field(default=MessageType.HEARTBEAT_ACK, init=False)
    client_time: float = field(default_factory=lambda: datetime.now().timestamp())
    server_time: float = 0.0


@dataclass
class ErrorMessage(WSMessage):
    """
    错误消息。

    用于通知客户端发生的错误。

    Attributes:
        type: 消息类型（默认为 ERROR）
        code: 错误代码
        message: 错误描述
        details: 错误详情字典

    Example:
        >>> msg = ErrorMessage(
        ...     code=400,
        ...     message="Invalid device ID",
        ...     details={"device_id": "invalid-xxx"}
        ... )
    """

    type: MessageType = field(default=MessageType.ERROR, init=False)
    code: int = 0
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackpressureWarningMessage(WSMessage):
    """
    背压警告消息。

    当服务器端消息队列接近满载时发送，通知客户端降低发送频率。

    Attributes:
        type: 消息类型（默认为 BACKPRESSURE_WARNING）
        queue_usage: 当前队列使用率（0.0-1.0）
        recommended_interval: 建议的发送间隔（秒）

    Example:
        >>> msg = BackpressureWarningMessage(
        ...     queue_usage=0.85,
        ...     recommended_interval=0.2
        ... )
    """

    type: MessageType = field(default=MessageType.BACKPRESSURE_WARNING, init=False)
    queue_usage: float = 0.0
    recommended_interval: float = 0.1


def serialize_message(message: WSMessage, use_msgpack: bool = True) -> bytes | str:
    """
    序列化消息。

    根据配置选择 JSON 或 MessagePack 格式。

    Args:
        message: 要序列化的消息对象
        use_msgpack: 是否使用 MessagePack 格式

    Returns:
        bytes | str: 序列化后的数据（MessagePack 返回 bytes，JSON 返回 str）
    """
    if use_msgpack:
        return message.to_msgpack()
    return message.to_json()


def deserialize_message(data: bytes | str, use_msgpack: bool = True) -> dict[str, Any]:
    """
    反序列化消息。

    根据配置从 JSON 或 MessagePack 格式反序列化。

    Args:
        data: 要反序列化的数据
        use_msgpack: 是否使用 MessagePack 格式

    Returns:
        dict[str, Any]: 反序列化后的字典

    Raises:
        ValueError: 数据格式无效
    """
    try:
        if use_msgpack and isinstance(data, bytes):
            return msgpack.unpackb(data, raw=False)
        if isinstance(data, str):
            return json.loads(data)
        # 如果是 bytes 但不使用 msgpack，尝试解码为 JSON
        if isinstance(data, bytes):
            return json.loads(data.decode("utf-8"))
        raise ValueError(f"Unsupported data type: {type(data)}")
    except (msgpack.UnpackException, json.JSONDecodeError, UnicodeDecodeError) as e:
        logger.error(f"Failed to deserialize message: {e}")
        raise ValueError(f"Invalid message data: {e}") from e
