"""
文件名: response_wrapper.py
路径: backend/api/
功能: 统一响应包装工具，提供标准化的API响应格式
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: pydantic, schemas.api, schemas.common

响应格式规范：
- 所有成功响应：{success: true, data: Any, error: null, timestamp: str}
- 所有失败响应：{success: false, data: null, error: {code, message, details}, timestamp: str}
- 支持泛型数据类型，自动生成时间戳

使用示例：
    >>> from api.response_wrapper import success_response, error_response
    >>> # 成功响应
    >>> return success_response(data={"id": 1}, message="查询成功")
    >>> # 失败响应
    >>> return error_response(message="设备未连接", error_code="E1002")
"""

from datetime import datetime
from typing import Any, TypeVar, Generic

from schemas.api import ApiResponse, ApiError, PaginatedData
from schemas.common import ErrorCode

T = TypeVar("T")


def success_response(
    data: T,
    message: str = "操作成功"
) -> ApiResponse[T]:
    """
    创建统一格式的成功响应。

    Args:
        data: 响应数据，支持任意类型
        message: 响应消息，默认为"操作成功"

    Returns:
        ApiResponse[T]: 统一格式的成功响应

    Example:
        >>> response = success_response({"id": 1, "name": "设备A"})
        >>> assert response.success is True
        >>> assert response.data["id"] == 1
    """
    return ApiResponse.ok(data=data, message=message)


def error_response(
    message: str,
    error_code: str | ErrorCode = ErrorCode.INTERNAL_ERROR,
    details: dict[str, Any] | None = None
) -> ApiResponse[None]:
    """
    创建统一格式的错误响应。

    Args:
        message: 错误消息，人类可读的错误描述
        error_code: 错误码，默认为INTERNAL_ERROR
        details: 错误详情，可选的额外信息字典

    Returns:
        ApiResponse[None]: 统一格式的错误响应

    Example:
        >>> response = error_response("设备未连接", ErrorCode.DEVICE_NOT_CONNECTED)
        >>> assert response.success is False
        >>> assert response.error.code == "E1002"
    """
    code = error_code.value if isinstance(error_code, ErrorCode) else error_code
    return ApiResponse.error(message=message, error_code=code, details=details)


def paginated_response(
    items: list[T],
    total: int,
    page: int = 1,
    page_size: int = 20,
    message: str = "查询成功"
) -> ApiResponse[dict]:
    """
    创建统一格式的分页响应。

    Args:
        items: 数据列表
        total: 总数量
        page: 当前页码，默认为1
        page_size: 每页数量，默认为20
        message: 响应消息，默认为"查询成功"

    Returns:
        ApiResponse[dict]: 包含分页数据的响应

    Example:
        >>> response = paginated_response([{"id": 1}], total=100, page=1)
        >>> assert response.data["total"] == 100
        >>> assert response.data["page"] == 1
    """
    paginated_data = PaginatedData.create(
        items=items,
        total=total,
        page=page,
        page_size=page_size
    )

    return ApiResponse.ok(
        data=paginated_data.model_dump(),
        message=message
    )


def validation_error_response(
    field: str,
    value: Any,
    constraint: str,
    message: str
) -> ApiResponse[None]:
    """
    创建参数验证错误响应。

    Args:
        field: 错误字段名
        value: 错误值
        constraint: 约束条件描述
        message: 错误消息

    Returns:
        ApiResponse[None]: 参数验证错误响应

    Example:
        >>> response = validation_error_response(
        ...     field="position_mm",
        ...     value=100.0,
        ...     constraint="le=50.0",
        ...     message="位置超出限位范围"
        ... )
    """
    return ApiResponse.error(
        message=message,
        error_code=ErrorCode.INVALID_PARAMETER.value,
        details={
            "field": field,
            "value": str(value),
            "constraint": constraint
        }
    )


class ResponseBuilder(Generic[T]):
    """
    响应构建器，支持链式调用构建复杂响应。

    Example:
        >>> response = (
        ...     ResponseBuilder()
        ...     .with_data({"id": 1})
        ...     .with_message("查询成功")
        ...     .build()
        ... )
    """

    def __init__(self):
        """初始化响应构建器。"""
        self._data: T | None = None
        self._message: str = "操作成功"
        self._error_code: str | None = None
        self._error_details: dict[str, Any] | None = None

    def with_data(self, data: T) -> "ResponseBuilder[T]":
        """
        设置响应数据。

        Args:
            data: 响应数据

        Returns:
            ResponseBuilder[T]: 构建器实例
        """
        self._data = data
        return self

    def with_message(self, message: str) -> "ResponseBuilder[T]":
        """
        设置响应消息。

        Args:
            message: 响应消息

        Returns:
            ResponseBuilder[T]: 构建器实例
        """
        self._message = message
        return self

    def with_error(
        self,
        error_code: str | ErrorCode,
        details: dict[str, Any] | None = None
    ) -> "ResponseBuilder[T]":
        """
        设置错误信息。

        Args:
            error_code: 错误码
            details: 错误详情

        Returns:
            ResponseBuilder[T]: 构建器实例
        """
        self._error_code = error_code.value if isinstance(error_code, ErrorCode) else error_code
        self._error_details = details
        return self

    def build(self) -> ApiResponse[T]:
        """
        构建最终响应。

        Returns:
            ApiResponse[T]: 构建完成的响应
        """
        if self._error_code:
            return ApiResponse.error(
                message=self._message,
                error_code=self._error_code,
                details=self._error_details
            )
        else:
            return ApiResponse.ok(data=self._data, message=self._message)
