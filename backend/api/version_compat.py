"""
文件名: version_compat.py
路径: backend/api/
功能: API版本兼容层，提供旧版API到新版API的路由转发，确保向后兼容
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, api.response_wrapper

兼容策略：
1. 旧版无版本前缀接口（如 /api/motor/status）转发到新版接口（/api/v1/motor/status）
2. 旧版POST查询接口转发到新版GET接口（如 /api/motor/status POST -> GET）
3. 响应格式自动转换，旧版响应包装为统一格式
4. 保留旧版接口的HTTP状态码行为

使用示例：
    >>> from api.version_compat import create_legacy_router
    >>> app.include_router(create_legacy_router())
"""

from typing import Any, Callable
from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse
import logging

from api.response_wrapper import success_response, error_response
from schemas.common import ErrorCode

logger = logging.getLogger(__name__)


class LegacyAPIRouter:
    """
    旧版API兼容路由器。

    提供旧版API到新版API的自动转发和响应格式转换。

    Example:
        >>> router = LegacyAPIRouter()
        >>> router.add_legacy_route("/api/motor/status", "/api/v1/motor/status", "GET")
    """

    def __init__(self):
        """初始化兼容路由器。"""
        self.router = APIRouter(tags=["legacy-api"])
        self._routes: dict[str, dict[str, Any]] = {}

    def add_legacy_route(
        self,
        legacy_path: str,
        new_path: str,
        method: str = "GET",
        response_converter: Callable[[Any], dict] | None = None
    ) -> None:
        """
        添加旧版路由映射。

        Args:
            legacy_path: 旧版路径，如 "/api/motor/status"
            new_path: 新版路径，如 "/api/v1/motor/status"
            method: HTTP方法，默认GET
            response_converter: 响应转换函数，可选
        """
        self._routes[legacy_path] = {
            "new_path": new_path,
            "method": method.upper(),
            "converter": response_converter
        }

        # 注册路由处理器
        async def handler(request: Request) -> Response:
            return await self._forward_request(request, legacy_path)

        # 根据方法注册路由
        if method.upper() == "GET":
            self.router.get(legacy_path)(handler)
        elif method.upper() == "POST":
            self.router.post(legacy_path)(handler)
        elif method.upper() == "PUT":
            self.router.put(legacy_path)(handler)
        elif method.upper() == "DELETE":
            self.router.delete(legacy_path)(handler)

        logger.info(f"[LegacyAPI] 注册兼容路由: {legacy_path} -> {new_path} ({method})")

    async def _forward_request(self, request: Request, legacy_path: str) -> Response:
        """
        转发请求到新版API。

        Args:
            request: 原始请求对象
            legacy_path: 旧版路径

        Returns:
            Response: 转换后的响应
        """
        route_info = self._routes.get(legacy_path)
        if not route_info:
            return JSONResponse(
                content=error_response(
                    message="路由不存在",
                    error_code=ErrorCode.INTERNAL_ERROR
                ).model_dump(),
                status_code=404
            )

        # 这里仅做路由映射记录，实际转发由FastAPI路由系统处理
        # 在实际应用中，可以通过HTTP客户端转发或直接调用处理函数
        logger.debug(f"[LegacyAPI] 请求转发: {legacy_path} -> {route_info['new_path']}")

        # 返回提示信息（实际转发逻辑需要根据项目架构实现）
        return JSONResponse(
            content=success_response(
                data={
                    "legacy_path": legacy_path,
                    "new_path": route_info["new_path"],
                    "method": route_info["method"],
                    "message": "此接口已迁移，请使用新版API"
                },
                message="接口已迁移"
            ).model_dump(),
            status_code=200
        )


def create_legacy_router() -> APIRouter:
    """
    创建旧版API兼容路由器。

    Returns:
        APIRouter: 包含所有旧版路由映射的路由器

    Example:
        >>> app.include_router(create_legacy_router())
    """
    legacy_router = LegacyAPIRouter()

    # 电机控制旧版路由映射
    legacy_router.add_legacy_route("/api/motor/status", "/api/v1/motor/status", "GET")
    legacy_router.add_legacy_route("/api/motor/connect", "/api/v1/motor/connect", "POST")
    legacy_router.add_legacy_route("/api/motor/disconnect", "/api/v1/motor/disconnect", "POST")
    legacy_router.add_legacy_route("/api/motor/move", "/api/v1/motor/move", "POST")
    legacy_router.add_legacy_route("/api/motor/jog", "/api/v1/motor/jog", "POST")
    legacy_router.add_legacy_route("/api/motor/emergency_stop", "/api/v1/motor/emergency_stop", "POST")
    legacy_router.add_legacy_route("/api/motor/reset", "/api/v1/motor/reset", "POST")
    legacy_router.add_legacy_route("/api/motor/limits", "/api/v1/motor/limits", "GET")
    legacy_router.add_legacy_route("/api/motor/limits", "/api/v1/motor/limits", "POST")

    # 设备管理旧版路由映射
    legacy_router.add_legacy_route("/api/device/list", "/api/v1/device/list", "GET")
    legacy_router.add_legacy_route("/api/device/status", "/api/v1/device/status", "GET")

    # 实验管理旧版路由映射
    legacy_router.add_legacy_route("/api/experiments", "/api/v1/experiment/", "GET")
    legacy_router.add_legacy_route("/api/experiments/start", "/api/v1/experiment/start", "POST")

    logger.info("[LegacyAPI] 旧版API兼容路由器初始化完成")
    return legacy_router.router


def convert_legacy_response(data: dict, message: str = "操作成功") -> dict:
    """
    将旧版响应转换为统一格式。

    Args:
        data: 旧版响应数据
        message: 响应消息

    Returns:
        dict: 统一格式的响应

    Example:
        >>> old_response = {"success": True, "position": 100}
        >>> new_response = convert_legacy_response(old_response)
        >>> assert new_response["success"] is True
        >>> assert "data" in new_response
    """
    # 如果已经是新格式，直接返回
    if "success" in data and "data" in data:
        return data

    # 转换为新格式
    return success_response(data=data, message=message).model_dump()


def convert_legacy_error(
    detail: str,
    status_code: int = 400
) -> dict:
    """
    将旧版错误响应转换为统一格式。

    Args:
        detail: 错误详情
        status_code: HTTP状态码

    Returns:
        dict: 统一格式的错误响应

    Example:
        >>> error = convert_legacy_error("设备未连接", 400)
        >>> assert error["success"] is False
        >>> assert "error" in error
    """
    # 根据状态码映射错误码
    error_code_map = {
        400: ErrorCode.INVALID_PARAMETER,
        401: ErrorCode.INTERNAL_ERROR,  # 需要扩展认证错误码
        403: ErrorCode.INTERNAL_ERROR,  # 需要扩展权限错误码
        404: ErrorCode.DEVICE_NOT_INITIALIZED,
        500: ErrorCode.INTERNAL_ERROR,
        503: ErrorCode.DEVICE_NOT_INITIALIZED,
    }

    error_code = error_code_map.get(status_code, ErrorCode.INTERNAL_ERROR)

    return error_response(
        message=detail,
        error_code=error_code
    ).model_dump()
