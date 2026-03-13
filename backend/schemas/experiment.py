"""
实验管理数据模型

文件名: experiment.py
路径: backend/schemas/
功能: 定义实验管理相关的请求/响应模型，包含实验创建、查询、状态管理
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic

实验状态：
- created: 已创建，未开始
- running: 运行中
- paused: 已暂停
- completed: 已完成
- cancelled: 已取消
"""

from pydantic import BaseModel, Field


class ExperimentRequest(BaseModel):
    """
    实验创建请求。

    用于创建新的实验记录。

    Attributes:
        name: 实验名称，长度1-100字符
        description: 实验描述，可选，默认为空字符串

    Validation Rules:
        - name: 必填，长度1-100字符
        - description: 可选，无长度限制

    Example:
        >>> request = ExperimentRequest(
        ...     name="磁滞回线测量实验#1",
        ...     description="室温下Fe3O4样品的磁滞回线测量"
        ... )
    """

    name: str = Field(..., description="实验名称", min_length=1, max_length=100)
    description: str = Field("", description="实验描述")


class ExperimentInfo(BaseModel):
    """
    实验信息模型。

    描述实验的完整信息，包括状态和时间戳。

    Attributes:
        id: 实验唯一标识符，自增整数
        name: 实验名称
        description: 实验描述
        status: 实验状态，可选值: created, running, paused, completed, cancelled
        created_at: 创建时间(ISO格式)
        started_at: 开始时间(ISO格式)，未开始时为None
        completed_at: 完成时间(ISO格式)，未完成时为None

    Example:
        >>> experiment = ExperimentInfo(
        ...     id=1,
        ...     name="磁滞回线测量实验#1",
        ...     description="室温下Fe3O4样品的磁滞回线测量",
        ...     status="running",
        ...     created_at="2026-03-14T10:00:00Z",
        ...     started_at="2026-03-14T10:05:00Z",
        ...     completed_at=None
        ... )
    """

    id: int
    name: str
    description: str
    status: str
    created_at: str
    started_at: str | None
    completed_at: str | None
