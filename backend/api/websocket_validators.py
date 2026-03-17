"""
WebSocket 消息验证模块

文件名: websocket_validators.py
路径: backend/api/
功能: WebSocket 消息验证，防止注入攻击和非法消息
作者: Backend Engineer Agent
创建日期: 2026-03-16
依赖: pydantic, json

安全特性：
- 消息大小限制（1MB）
- 消息类型验证
- 字段长度限制
- JSON 格式验证
- 时间戳验证

注意事项：
- 所有 WebSocket 消息必须经过验证后才能处理
- 验证失败的消息将被丢弃并记录日志
"""

import json
import logging
from typing import Any

from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)

# 消息大小限制常量
MAX_MESSAGE_SIZE = 1024 * 1024  # 1MB
MAX_TYPE_LENGTH = 50
MAX_COMMAND_LENGTH = 50
MAX_DEVICE_ID_LENGTH = 50
MAX_PARAMS_DEPTH = 5


class WSMessageBase(BaseModel):
    """
    WebSocket 消息基类。

    所有 WebSocket 消息的基础模型，包含通用字段验证。

    Attributes:
        type: 消息类型，长度限制 1-50 字符
        timestamp: 消息时间戳（可选）

    Example:
        >>> msg = WSMessageBase(type="ping", timestamp=1234567890.0)
        >>> msg.type
        'ping'
    """

    type: str = Field(..., min_length=1, max_length=MAX_TYPE_LENGTH, description="消息类型")
    timestamp: float | None = Field(None, description="消息时间戳（Unix 时间戳）")

    @classmethod
    def validate_type(cls, msg_type: str) -> bool:
        """
        验证消息类型是否有效。

        Args:
            msg_type: 消息类型字符串

        Returns:
            bool: 类型是否有效

        Note:
            有效类型只包含字母、数字、下划线和连字符
        """
        if not msg_type or len(msg_type) > MAX_TYPE_LENGTH:
            return False
        return all(c.isalnum() or c in "_-" for c in msg_type)


class WSCommandMessage(WSMessageBase):
    """
    WebSocket 命令消息模型。

    用于设备控制命令的消息验证。

    Attributes:
        command: 命令名称，长度限制 1-50 字符
        device_id: 设备 ID（可选），最大长度 50 字符
        params: 命令参数字典，默认为空

    Validation Rules:
        - command 必须是有效字符串
        - device_id 只能包含字母、数字、下划线和连字符
        - params 嵌套深度不能超过 5 层

    Example:
        >>> msg = WSCommandMessage(
        ...     type="command",
        ...     command="move",
        ...     device_id="stepper_01",
        ...     params={"position": 10.0}
        ... )
    """

    command: str = Field(..., min_length=1, max_length=MAX_COMMAND_LENGTH, description="命令名称")
    device_id: str | None = Field(None, max_length=MAX_DEVICE_ID_LENGTH, description="设备 ID")
    params: dict[str, Any] = Field(default_factory=dict, description="命令参数")

    @classmethod
    def validate_message(cls, data: str | bytes) -> "WSCommandMessage | None":
        """
        验证并解析消息。

        Args:
            data: 原始消息数据（字符串或字节）

        Returns:
            WSCommandMessage | None: 验证后的消息对象，验证失败返回 None

        Note:
            此方法会捕获所有验证异常并记录日志
        """
        try:
            if isinstance(data, bytes):
                data = data.decode("utf-8")

            parsed = json.loads(data)
            return cls.model_validate(parsed)
        except json.JSONDecodeError as e:
            logger.warning(f"WebSocket message JSON decode error: {e}")
            return None
        except ValidationError as e:
            logger.warning(f"WebSocket message validation error: {e}")
            return None
        except UnicodeDecodeError as e:
            logger.warning(f"WebSocket message decode error: {e}")
            return None


class WSStatusMessage(WSMessageBase):
    """
    WebSocket 状态消息模型。

    用于设备状态推送的消息验证。

    Attributes:
        status: 状态值
        device_id: 设备 ID（可选）
        data: 状态数据字典

    Example:
        >>> msg = WSStatusMessage(
        ...     type="device_status",
        ...     status="running",
        ...     device_id="stepper_01",
        ...     data={"position": 25.5}
        ... )
    """

    status: str = Field(..., min_length=1, max_length=50, description="状态值")
    device_id: str | None = Field(None, max_length=MAX_DEVICE_ID_LENGTH, description="设备 ID")
    data: dict[str, Any] = Field(default_factory=dict, description="状态数据")


class WSAlarmMessage(WSMessageBase):
    """
    WebSocket 报警消息模型。

    用于设备报警事件的消息验证。

    Attributes:
        level: 报警级别（info/warning/error/critical）
        code: 报警代码
        message: 报警消息
        device_id: 设备 ID（可选）

    Example:
        >>> msg = WSAlarmMessage(
        ...     type="alarm",
        ...     level="warning",
        ...     code="HIGH_TEMP",
        ...     message="温度超过阈值"
        ... )
    """

    level: str = Field("info", description="报警级别")
    code: str = Field(..., min_length=1, max_length=50, description="报警代码")
    message: str = Field(..., min_length=1, max_length=500, description="报警消息")
    device_id: str | None = Field(None, max_length=MAX_DEVICE_ID_LENGTH, description="设备 ID")

    @classmethod
    def validate_level(cls, level: str) -> bool:
        """
        验证报警级别是否有效。

        Args:
            level: 报警级别字符串

        Returns:
            bool: 级别是否有效
        """
        valid_levels = {"info", "warning", "error", "critical"}
        return level.lower() in valid_levels


def _check_dict_depth(data: dict[str, Any], current_depth: int = 0) -> bool:
    """
    检查字典嵌套深度。

    Args:
        data: 要检查的字典
        current_depth: 当前深度

    Returns:
        bool: 深度是否在限制范围内

    Note:
        最大深度为 MAX_PARAMS_DEPTH
    """
    if current_depth > MAX_PARAMS_DEPTH:
        return False

    for value in data.values():
        if isinstance(value, dict):
            if not _check_dict_depth(value, current_depth + 1):
                return False

    return True


def validate_websocket_message(data: str | bytes) -> dict[str, Any] | None:
    """
    验证 WebSocket 消息。

    执行基础的消息验证，包括大小、格式和必要字段检查。
    此函数用于快速过滤无效消息，不进行完整的 Pydantic 验证。

    Args:
        data: 原始消息数据（字符串或字节）

    Returns:
        dict[str, Any] | None: 验证后的消息字典，验证失败返回 None

    Validation Steps:
        1. 检查消息大小（不超过 1MB）
        2. 解码字节为字符串（如需要）
        3. 解析 JSON 格式
        4. 验证顶层是字典类型
        5. 验证必须包含 type 字段
        6. 验证 type 字段格式
        7. 清理无效的时间戳字段

    Example:
        >>> data = '{"type": "ping", "timestamp": 1234567890}'
        >>> result = validate_websocket_message(data)
        >>> result["type"]
        'ping'

        >>> invalid = '{"type": "x" * 100}'  # type 过长
        >>> validate_websocket_message(invalid) is None
        True
    """
    # 大小限制检查
    if len(data) > MAX_MESSAGE_SIZE:
        logger.warning(
            f"WebSocket message size exceeded: {len(data)} > {MAX_MESSAGE_SIZE}"
        )
        return None

    try:
        # 解码字节
        if isinstance(data, bytes):
            data = data.decode("utf-8")

        # 解析 JSON
        parsed = json.loads(data)

        # 类型检查：必须是字典
        if not isinstance(parsed, dict):
            logger.warning("WebSocket message is not a dictionary")
            return None

        # 必须有 type 字段
        if "type" not in parsed:
            logger.warning("WebSocket message missing 'type' field")
            return None

        # type 字段验证
        msg_type = parsed.get("type")
        if not isinstance(msg_type, str):
            logger.warning("WebSocket message 'type' is not a string")
            return None

        if len(msg_type) == 0 or len(msg_type) > MAX_TYPE_LENGTH:
            logger.warning(
                f"WebSocket message 'type' length invalid: {len(msg_type)}"
            )
            return None

        # 检查 type 字段格式（只允许字母、数字、下划线、连字符）
        if not all(c.isalnum() or c in "_-" for c in msg_type):
            logger.warning(f"WebSocket message 'type' contains invalid characters: {msg_type}")
            return None

        # 时间戳验证（可选字段）
        if "timestamp" in parsed:
            ts = parsed["timestamp"]
            if not isinstance(ts, (int, float)):
                # 移除无效的时间戳
                del parsed["timestamp"]
                logger.debug("Removed invalid timestamp from WebSocket message")
            elif ts < 0:
                # 负数时间戳无效
                del parsed["timestamp"]
                logger.debug("Removed negative timestamp from WebSocket message")

        # 检查嵌套深度
        if not _check_dict_depth(parsed):
            logger.warning("WebSocket message nested depth exceeded")
            return None

        return parsed

    except json.JSONDecodeError as e:
        logger.warning(f"WebSocket message JSON decode error: {e}")
        return None
    except UnicodeDecodeError as e:
        logger.warning(f"WebSocket message decode error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error validating WebSocket message: {e}")
        return None


def validate_device_id_format(device_id: str | None) -> bool:
    """
    验证设备 ID 格式。

    Args:
        device_id: 设备 ID 字符串

    Returns:
        bool: 格式是否有效

    Note:
        有效格式：字母、数字、下划线、连字符，长度 1-50
    """
    if device_id is None:
        return True  # None 是允许的（可选字段）

    if not isinstance(device_id, str):
        return False

    if len(device_id) == 0 or len(device_id) > MAX_DEVICE_ID_LENGTH:
        return False

    return all(c.isalnum() or c in "_-" for c in device_id)


def sanitize_message_params(params: dict[str, Any]) -> dict[str, Any]:
    """
    清理消息参数。

    移除可能包含危险内容的参数字段。

    Args:
        params: 原始参数字典

    Returns:
        dict[str, Any]: 清理后的参数字典

    Note:
        - 移除以 __ 开头的字段（防止 Python 特殊属性访问）
        - 限制字符串字段长度
        - 递归处理嵌套字典
    """
    if not isinstance(params, dict):
        return {}

    result = {}
    for key, value in params.items():
        # 跳过危险键名
        if key.startswith("__") or key.startswith("_"):
            continue

        # 限制键名长度
        if len(key) > 100:
            continue

        if isinstance(value, dict):
            result[key] = sanitize_message_params(value)
        elif isinstance(value, str):
            # 限制字符串长度
            result[key] = value[:10000]
        elif isinstance(value, (int, float, bool)):
            result[key] = value
        elif isinstance(value, list):
            # 限制列表长度
            result[key] = value[:1000]
        else:
            # 其他类型转为字符串
            result[key] = str(value)[:1000]

    return result
