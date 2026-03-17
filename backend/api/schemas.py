"""
Pydantic 数据模型定义（向后兼容模块）

文件名: schemas.py
路径: backend/api/
功能: Pydantic数据模型重导出模块，提供向后兼容的导入入口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: pydantic, schemas

说明：
此文件已重构，所有模型已移动到 schemas/ 目录。
此文件仅作为向后兼容的导入入口。

新代码应直接从 schemas 模块导入：
    from schemas import MoveRequest, MoveResponse

旧代码仍可使用：
    from api.schemas import MoveRequest, MoveResponse

包含的模型类别：
- 请求模型（Request Models）
- 响应模型（Response Models）
- 枚举模型（Enum Models）
- 配置模型（Config Models）
"""

from schemas import *  # noqa: F403
from schemas import (
    __all__,
)

__all__ = __all__
