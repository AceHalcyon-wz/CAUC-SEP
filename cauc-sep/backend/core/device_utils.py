"""
设备状态验证工具模块

本模块提供设备状态验证的通用工具函数和异常类，用于：
- 验证设备状态是否允许操作
- 创建标准化的错误响应
- 统一设备验证异常处理

设计参考：技术设计文档第3.1章节
"""

from typing import Any

from core.abstract import DeviceStatus


class DeviceValidationError(Exception):
    """设备验证异常类。

    当设备状态不允许执行操作时抛出此异常。

    Attributes:
        message: 错误消息
        device_id: 设备ID（可选）
        status: 设备状态（可选）
    """

    def __init__(
        self,
        message: str,
        device_id: str | None = None,
        status: str | None = None,
    ):
        """初始化设备验证异常。

        Args:
            message: 错误消息描述
            device_id: 设备唯一标识符（可选）
            status: 设备当前状态（可选）
        """
        self.message = message
        self.device_id = device_id
        self.status = status
        super().__init__(message)

    def __repr__(self) -> str:
        """返回异常的字符串表示。"""
        parts = [f"DeviceValidationError(message={self.message!r}"]
        if self.device_id is not None:
            parts.append(f", device_id={self.device_id!r}")
        if self.status is not None:
            parts.append(f", status={self.status!r}")
        parts.append(")")
        return "".join(parts)


def validate_device_state(device: Any, require_ready: bool = True) -> None:
    """验证设备状态是否允许操作。

    检查设备状态，如果状态不允许操作则抛出 DeviceValidationError 异常。

    Args:
        device: 设备实例，必须包含 status 属性（DeviceStatus 类型）
        require_ready: 是否要求设备处于就绪状态，默认为 True
            - True: 设备必须处于 READY 状态才能通过验证
            - False: 允许设备处于 BUSY 状态（用于某些特殊操作）

    Returns:
        None: 验证通过时返回 None

    Raises:
        DeviceValidationError: 设备状态不允许操作时抛出
            - DISCONNECTED: 设备未连接
            - EMERGENCY_STOP: 设备处于急停状态
            - ERROR: 设备处于错误状态
            - BUSY: 设备正在运行中（仅当 require_ready=True 时）

    Example:
        >>> from core.abstract import DeviceStatus
        >>> class MockDevice:
        ...     def __init__(self):
        ...         self.status = DeviceStatus.READY
        ...         self.device_id = "motor_001"
        >>> device = MockDevice()
        >>> validate_device_state(device)  # 验证通过，无异常
        >>> device.status = DeviceStatus.DISCONNECTED
        >>> validate_device_state(device)  # 抛出 DeviceValidationError
        DeviceValidationError: 设备未连接
    """
    # 获取设备状态
    current_status = device.status

    # 检查设备是否断开连接
    if current_status == DeviceStatus.DISCONNECTED:
        raise DeviceValidationError(
            message="设备未连接",
            device_id=getattr(device, "device_id", None),
            status=current_status.value,
        )

    # 检查设备是否处于急停状态
    if current_status == DeviceStatus.EMERGENCY_STOP:
        raise DeviceValidationError(
            message="设备处于急停状态",
            device_id=getattr(device, "device_id", None),
            status=current_status.value,
        )

    # 检查设备是否处于错误状态
    if current_status == DeviceStatus.ERROR:
        raise DeviceValidationError(
            message="设备处于错误状态",
            device_id=getattr(device, "device_id", None),
            status=current_status.value,
        )

    # 检查设备是否忙碌（仅当要求就绪状态时）
    if require_ready and current_status == DeviceStatus.BUSY:
        raise DeviceValidationError(
            message="设备正在运行中",
            device_id=getattr(device, "device_id", None),
            status=current_status.value,
        )


def create_device_error_response(
    message: str,
    device_id: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """创建设备错误响应字典。

    生成统一格式的错误响应，用于 API 返回或日志记录。

    Args:
        message: 错误消息描述
        device_id: 设备唯一标识符（可选）
        status: 设备当前状态（可选）

    Returns:
        Dict[str, Any]: 统一格式的错误响应字典，包含以下字段：
            - success: 固定为 False
            - message: 错误消息
            - device_id: 设备ID（可选）
            - status: 设备状态（可选）

    Example:
        >>> response = create_device_error_response(
        ...     message="设备未连接",
        ...     device_id="motor_001",
        ...     status="disconnected"
        ... )
        >>> response["success"]
        False
        >>> response["message"]
        '设备未连接'
    """
    response: dict[str, Any] = {
        "success": False,
        "message": message,
    }

    # 添加可选字段
    if device_id is not None:
        response["device_id"] = device_id

    if status is not None:
        response["status"] = status

    return response
