"""
文件名: exception_utils.py
路径: backend/core/utils/exception_utils.py
功能: 设备异常处理通用工具类，提供统一的异常定义、处理、重试机制
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+, typing, logging, asyncio

安全约束:
- 所有设备异常必须继承统一的基类
- 异常处理必须包含完整的日志记录
- 通信异常必须实现重试机制
"""

from __future__ import annotations

import asyncio
import functools
import logging
import traceback
from typing import Any, Callable, Coroutine, TypeVar

logger = logging.getLogger(__name__)

# 类型变量
T = TypeVar("T")


# ==================== 异常类定义 ====================


class DeviceException(Exception):
    """
    设备异常基类。

    所有设备相关异常必须继承此类。

    Attributes:
        message: 异常消息
        device_id: 设备ID
        error_code: 错误代码
        details: 详细信息字典
    """

    def __init__(
        self,
        message: str,
        device_id: str | None = None,
        error_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        """
        初始化设备异常。

        Args:
            message: 异常消息
            device_id: 设备ID
            error_code: 错误代码
            details: 详细信息字典
        """
        super().__init__(message)
        self.message = message
        self.device_id = device_id
        self.error_code = error_code
        self.details = details or {}

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式。

        Returns:
            Dict[str, Any]: 异常信息字典
        """
        return {
            "exception_type": self.__class__.__name__,
            "message": self.message,
            "device_id": self.device_id,
            "error_code": self.error_code,
            "details": self.details,
        }

    def __str__(self) -> str:
        """
        返回字符串表示。

        Returns:
            str: 异常字符串
        """
        parts = [self.message]
        if self.device_id:
            parts.append(f"device_id={self.device_id}")
        if self.error_code:
            parts.append(f"error_code={self.error_code}")
        return f"{self.__class__.__name__}: {', '.join(parts)}"


class DeviceCommunicationError(DeviceException):
    """
    设备通信异常。

    当与设备的通信失败时抛出此异常。

    Attributes:
        retry_count: 已重试次数
        last_error: 最后一次错误信息
    """

    def __init__(
        self,
        message: str,
        device_id: str | None = None,
        retry_count: int = 0,
        last_error: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化通信异常。

        Args:
            message: 异常消息
            device_id: 设备ID
            retry_count: 已重试次数
            last_error: 最后一次错误信息
        """
        super().__init__(message, device_id, error_code=1001, **kwargs)
        self.retry_count = retry_count
        self.last_error = last_error


class DeviceParameterError(DeviceException):
    """
    设备参数异常。

    当设备参数无效时抛出此异常。

    Attributes:
        parameter_name: 参数名称
        parameter_value: 参数值
        expected_range: 期望范围
    """

    def __init__(
        self,
        message: str,
        device_id: str | None = None,
        parameter_name: str | None = None,
        parameter_value: Any | None = None,
        expected_range: tuple[Any, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化参数异常。

        Args:
            message: 异常消息
            device_id: 设备ID
            parameter_name: 参数名称
            parameter_value: 参数值
            expected_range: 期望范围
        """
        super().__init__(message, device_id, error_code=1002, **kwargs)
        self.parameter_name = parameter_name
        self.parameter_value = parameter_value
        self.expected_range = expected_range


class DeviceAlarmError(DeviceException):
    """
    设备报警异常。

    当设备处于报警状态时抛出此异常。

    Attributes:
        alarm_code: 报警代码
        alarm_message: 报警消息
        alarm_level: 报警级别
    """

    def __init__(
        self,
        message: str,
        device_id: str | None = None,
        alarm_code: int | None = None,
        alarm_message: str | None = None,
        alarm_level: int = 1,
        **kwargs: Any,
    ) -> None:
        """
        初始化报警异常。

        Args:
            message: 异常消息
            device_id: 设备ID
            alarm_code: 报警代码
            alarm_message: 报警消息
            alarm_level: 报警级别
        """
        super().__init__(message, device_id, error_code=2001, **kwargs)
        self.alarm_code = alarm_code
        self.alarm_message = alarm_message
        self.alarm_level = alarm_level


class DeviceTimeoutError(DeviceException):
    """
    设备超时异常。

    当设备操作超时时抛出此异常。

    Attributes:
        timeout_seconds: 超时时间（秒）
        operation: 操作描述
    """

    def __init__(
        self,
        message: str,
        device_id: str | None = None,
        timeout_seconds: float | None = None,
        operation: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化超时异常。

        Args:
            message: 异常消息
            device_id: 设备ID
            timeout_seconds: 超时时间（秒）
            operation: 操作描述
        """
        super().__init__(message, device_id, error_code=1003, **kwargs)
        self.timeout_seconds = timeout_seconds
        self.operation = operation


class DeviceNotConnectedError(DeviceException):
    """
    设备未连接异常。

    当尝试操作未连接的设备时抛出此异常。
    """

    def __init__(
        self,
        message: str = "设备未连接",
        device_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化未连接异常。

        Args:
            message: 异常消息
            device_id: 设备ID
        """
        super().__init__(message, device_id, error_code=1004, **kwargs)


class DeviceBusyError(DeviceException):
    """
    设备忙碌异常。

    当设备正在执行其他操作时抛出此异常。
    """

    def __init__(
        self,
        message: str = "设备正在执行其他操作",
        device_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化忙碌异常。

        Args:
            message: 异常消息
            device_id: 设备ID
        """
        super().__init__(message, device_id, error_code=1005, **kwargs)


class DeviceEmergencyStopError(DeviceException):
    """
    设备急停异常。

    当设备处于急停状态时抛出此异常。
    """

    def __init__(
        self,
        message: str = "设备处于急停状态",
        device_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化急停异常。

        Args:
            message: 异常消息
            device_id: 设备ID
        """
        super().__init__(message, device_id, error_code=1006, **kwargs)


class DeviceLimitError(DeviceException):
    """
    设备限位异常。

    当设备超出软件限位范围时抛出此异常。

    Attributes:
        limit_type: 限位类型
        actual_value: 实际值
        limit_value: 限值
    """

    def __init__(
        self,
        message: str,
        device_id: str | None = None,
        limit_type: str | None = None,
        actual_value: float | None = None,
        limit_value: float | None = None,
        **kwargs: Any,
    ) -> None:
        """
        初始化限位异常。

        Args:
            message: 异常消息
            device_id: 设备ID
            limit_type: 限位类型
            actual_value: 实际值
            limit_value: 限值
        """
        super().__init__(message, device_id, error_code=2007, **kwargs)
        self.limit_type = limit_type
        self.actual_value = actual_value
        self.limit_value = limit_value


# ==================== 异常处理函数 ====================


def handle_device_exception(
    exception: Exception,
    device_id: str | None = None,
    operation: str | None = None,
    log_level: int = logging.ERROR,
) -> dict[str, Any]:
    """
    统一处理设备异常。

    Args:
        exception: 异常对象
        device_id: 设备ID
        operation: 操作描述
        log_level: 日志级别

    Returns:
        Dict[str, Any]: 异常信息字典

    安全约束:
        - 所有异常必须记录完整日志
        - 敏感信息必须脱敏
    """
    # 构建异常信息
    if isinstance(exception, DeviceException):
        error_info = exception.to_dict()
        if device_id and not error_info.get("device_id"):
            error_info["device_id"] = device_id
    else:
        error_info = {
            "exception_type": exception.__class__.__name__,
            "message": str(exception),
            "device_id": device_id,
            "error_code": None,
            "details": {},
        }

    # 添加操作信息
    if operation:
        error_info["operation"] = operation

    # 添加堆栈信息
    error_info["traceback"] = traceback.format_exc()

    # 记录日志
    log_msg = f"设备异常: {error_info['message']}"
    if device_id:
        log_msg += f", device_id={device_id}"
    if operation:
        log_msg += f", operation={operation}"

    logger.log(log_level, log_msg, extra=error_info)

    return error_info


async def retry_with_backoff(
    func: Callable[..., Coroutine[Any, Any, T]],
    max_retries: int = 3,
    base_delay: float = 0.1,
    max_delay: float = 5.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
    on_retry: Callable[[int, Exception], None] | None = None,
    device_id: str | None = None,
) -> T:
    """
    带指数退避的重试机制。

    Args:
        func: 要执行的异步函数
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        max_delay: 最大延迟（秒）
        exceptions: 要捕获的异常类型元组
        on_retry: 重试时的回调函数
        device_id: 设备ID

    Returns:
        T: 函数返回值

    Raises:
        Exception: 所有重试失败后抛出最后一次异常

    Example:
        >>> result = await retry_with_backoff(
        ...     lambda: device.read_status(),
        ...     max_retries=3,
        ...     base_delay=0.1,
        ...     exceptions=(DeviceCommunicationError,),
        ... )
    """
    last_exception: Exception | None = None

    for attempt in range(max_retries):
        try:
            return await func()
        except exceptions as e:
            last_exception = e

            # 计算退避延迟（指数退避）
            delay = min(base_delay * (2**attempt), max_delay)

            logger.warning(
                f"操作失败，准备重试: attempt={attempt + 1}/{max_retries}, "
                f"delay={delay:.3f}s, error={str(e)}",
                extra={"device_id": device_id, "attempt": attempt, "error": str(e)},
            )

            # 调用重试回调
            if on_retry:
                try:
                    on_retry(attempt, e)
                except Exception as callback_error:
                    logger.error(f"重试回调异常: {callback_error}")

            # 等待退避延迟
            if attempt < max_retries - 1:
                await asyncio.sleep(delay)

    # 所有重试失败
    if last_exception:
        logger.error(
            f"操作失败（已重试{max_retries}次）: {str(last_exception)}",
            extra={"device_id": device_id, "max_retries": max_retries},
        )
        raise last_exception

    # 不应该到达这里
    raise RuntimeError("retry_with_backoff: 不应该到达的代码路径")


def with_retry(
    max_retries: int = 3,
    base_delay: float = 0.1,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Coroutine[Any, Any, T]]:
    """
    重试装饰器。

    为异步函数添加重试机制。

    Args:
        max_retries: 最大重试次数
        base_delay: 基础延迟（秒）
        exceptions: 要捕获的异常类型元组

    Returns:
        Callable: 装饰器函数

    Example:
        >>> @with_retry(max_retries=3, exceptions=(DeviceCommunicationError,))
        ... async def read_device_status(device_id: str) -> dict:
        ...     # 可能失败的操作
        ...     pass
    """

    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Coroutine[Any, Any, T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            return await retry_with_backoff(
                lambda: func(*args, **kwargs),
                max_retries=max_retries,
                base_delay=base_delay,
                exceptions=exceptions,
            )

        return wrapper

    return decorator
