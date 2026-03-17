"""
文件名: api.py
路径: backend/schemas/
功能: API 通用响应 Schema，提供统一的响应格式、分页数据和错误处理
版本: v1.1
作者: Backend Engineer Agent
创建日期: 2026-03-15
更新日期: 2026-03-16
依赖: pydantic, typing, datetime

响应格式规范：
- ApiResponse: 统一响应包装器，包含 success, data, error, timestamp
- PaginatedData: 分页数据结构，包含 items, total, page, page_size, total_pages
- ApiError: 错误信息结构，包含 code, message, details
- PaginationParams: 分页请求参数
"""

from typing import Generic, TypeVar, Optional, List, Any
from datetime import datetime

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiError(BaseModel):
    """
    API 错误信息模型。

    描述 API 调用失败时的错误详情。

    Attributes:
        code: 错误码，如 'E1001', 'E2001' 等。
        message: 错误消息，人类可读的错误描述。
        details: 错误详情，可选的额外信息字典。

    Example:
        >>> error = ApiError(
        ...     code="E1002",
        ...     message="设备未连接",
        ...     details={"device_id": "motor-001"}
        ... )
    """

    code: str = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    details: dict[str, Any] | None = Field(
        default=None, description="错误详情"
    )


class ApiResponse(BaseModel, Generic[T]):
    """
    API 统一响应格式模型。

    所有 API 响应的统一包装器，支持泛型数据类型。

    Attributes:
        success: 是否成功，True 表示成功，False 表示失败。
        data: 响应数据，成功时包含业务数据，失败时为 None。
        error: 错误信息，失败时包含错误详情，成功时为 None。
        timestamp: 响应时间戳，UTC 时间。

    Example:
        >>> # 成功响应
        >>> response = ApiResponse[dict](
        ...     success=True,
        ...     data={"id": 1, "name": "设备A"}
        ... )
        
        >>> # 失败响应
        >>> response = ApiResponse[None](
        ...     success=False,
        ...     error=ApiError(code="E1002", message="设备未连接")
        ... )
    """

    success: bool = Field(..., description="是否成功")
    data: T | None = Field(default=None, description="响应数据")
    error: ApiError | None = Field(default=None, description="错误信息")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow,
        description="响应时间戳"
    )

    @classmethod
    def ok(cls, data: T, message: str = "操作成功") -> "ApiResponse[T]":
        """
        创建成功响应。

        Args:
            data: 响应数据。
            message: 响应消息，默认为"操作成功"。

        Returns:
            ApiResponse[T]: 成功响应实例。

        Example:
            >>> response = ApiResponse.ok({"id": 1}, "查询成功")
            >>> response.success
            True
        """
        return cls(success=True, data=data, error=None)

    @classmethod
    def error(
        cls,
        message: str,
        error_code: str | None = None,
        details: dict[str, Any] | None = None
    ) -> "ApiResponse[T]":
        """
        创建错误响应。

        Args:
            message: 错误消息。
            error_code: 错误码，可选。
            details: 错误详情，可选。

        Returns:
            ApiResponse[T]: 错误响应实例。

        Example:
            >>> response = ApiResponse.error("设备未连接", "E1002")
            >>> response.success
            False
        """
        api_error = ApiError(
            code=error_code or "E0000",
            message=message,
            details=details
        )
        return cls(success=False, data=None, error=api_error)


class PaginatedData(BaseModel, Generic[T]):
    """
    分页数据模型。

    用于返回分页查询结果的数据结构。

    Attributes:
        items: 数据列表，当前页的数据项。
        total: 总数量，符合查询条件的总记录数。
        page: 当前页码，从1开始。
        page_size: 每页数量，当前页的数据项数量。
        total_pages: 总页数，根据 total 和 page_size 计算。

    Example:
        >>> data = PaginatedData[dict](
        ...     items=[{"id": 1}, {"id": 2}],
        ...     total=100,
        ...     page=1,
        ...     page_size=20,
        ...     total_pages=5
        ... )
    """

    items: list[T] = Field(..., description="数据列表")
    total: int = Field(..., description="总数量")
    page: int = Field(..., ge=1, description="当前页码")
    page_size: int = Field(..., ge=1, le=100, description="每页数量")
    total_pages: int = Field(..., description="总页数")

    @classmethod
    def create(
        cls,
        items: list[T],
        total: int,
        page: int = 1,
        page_size: int = 20
    ) -> "PaginatedData[T]":
        """
        创建分页响应。

        自动计算总页数。

        Args:
            items: 数据列表。
            total: 总数量。
            page: 当前页码，默认为1。
            page_size: 每页数量，默认为20。

        Returns:
            PaginatedData[T]: 分页数据实例。

        Example:
            >>> data = PaginatedData.create([{"id": 1}], total=100, page=1)
            >>> data.total_pages
            5
        """
        total_pages = (total + page_size - 1) // page_size if page_size > 0 else 0
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )


class PaginationParams(BaseModel):
    """
    分页请求参数模型。

    用于接收分页查询请求的参数。

    Attributes:
        page: 页码，从1开始，默认为1。
        page_size: 每页数量，范围1-100，默认为20。
        sort_by: 排序字段，可选。
        sort_order: 排序方向，可选值 'asc' 或 'desc'，默认 'desc'。

    Example:
        >>> params = PaginationParams(page=2, page_size=50, sort_by="created_at")
    """

    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=20, ge=1, le=100, description="每页数量")
    sort_by: str | None = Field(default=None, description="排序字段")
    sort_order: str | None = Field(
        default="desc",
        description="排序方向",
        pattern="^(asc|desc)$",
    )
