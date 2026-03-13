"""
日志数据模型模块

文件名: logs.py
路径: backend/models/
功能: 定义日志相关的 SQLAlchemy 模型，包含操作日志、审计日志等
作者: Backend Engineer Agent
创建日期: 2024-03-06
更新日期: 2026-03-14
依赖: sqlalchemy

模块内容:
    - OperationLog: 操作日志表模型
    - AuditLog: 审计日志表模型
    - VALID_OPERATION_CATEGORIES: 有效操作类别常量
    - VALID_REQUEST_METHODS: 有效请求方法常量
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from models.device import Base

VALID_OPERATION_CATEGORIES = ("device", "experiment", "system", "calibration", "config")
VALID_REQUEST_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


class OperationLog(Base):
    """
    操作日志表

    记录用户对设备和系统的操作历史，包括操作类型、参数、结果和错误信息。
    用于操作追溯和问题排查。

    Attributes:
        id: 主键，自增整数
        user_id: 关联用户ID，外键
        device_id: 设备ID，外键关联devices.device_id
        operation: 操作类型
        parameters: 操作参数JSON字符串
        result: 操作结果(success/failed)
        error_message: 错误信息
        created_at: 创建时间
    """

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    device_id = Column(
        String(50), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True, index=True
    )
    operation = Column(String(100), nullable=False, index=True)
    parameters = Column(Text, nullable=True)
    result = Column(String(20), nullable=True, index=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    __table_args__ = (
        CheckConstraint(
            "result IN ('success', 'failed', 'pending') OR result IS NULL",
            name="ck_operation_log_result_valid",
        ),
        Index("ix_operation_logs_user_created", "user_id", "created_at"),
        Index("ix_operation_logs_device_created", "device_id", "created_at"),
    )

    user = relationship("User", back_populates="operation_logs")
    device = relationship("Device", backref="operation_logs")

    def __repr__(self) -> str:
        return f"<OperationLog(id={self.id}, operation='{self.operation}', result='{self.result}')>"


class AuditLog(Base):
    """
    审计日志表

    记录系统中所有关键操作的审计日志，包括设备操作、参数修改、校准操作等。
    用于安全审计、操作追溯和问题排查。

    Attributes:
        id: 主键，自增整数
        timestamp: 审计时间戳
        user_id: 关联用户ID，外键
        device_id: 设备ID，外键关联devices.device_id
        operation_type: 操作类型
        operation_category: 操作类别
        request_method: HTTP请求方法
        request_path: 请求路径
        request_params: 请求参数JSON字符串
        response_status: 响应状态码
        response_message: 响应消息
        ip_address: 客户端IP地址
        user_agent: 用户代理字符串
        duration_ms: 操作耗时(毫秒)
        extra_data: 额外数据JSON字符串
    """

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    device_id = Column(
        String(50), ForeignKey("devices.device_id", ondelete="SET NULL"), nullable=True, index=True
    )
    operation_type = Column(String(50), nullable=False, index=True)
    operation_category = Column(String(30), nullable=False, index=True)
    request_method = Column(String(10), nullable=False)
    request_path = Column(String(255), nullable=False, index=True)
    request_params = Column(Text, nullable=True)
    response_status = Column(Integer, nullable=True, index=True)
    response_message = Column(Text, nullable=True)
    ip_address = Column(String(45), nullable=True, index=True)
    user_agent = Column(String(255), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    extra_data = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"operation_category IN {VALID_OPERATION_CATEGORIES}",
            name="ck_audit_log_category_valid",
        ),
        CheckConstraint(
            f"request_method IN {VALID_REQUEST_METHODS}", name="ck_audit_log_method_valid"
        ),
        CheckConstraint(
            "response_status >= 100 AND response_status < 600 OR response_status IS NULL",
            name="ck_audit_log_status_valid",
        ),
        CheckConstraint(
            "duration_ms >= 0 OR duration_ms IS NULL", name="ck_audit_log_duration_valid"
        ),
        Index("ix_audit_logs_timestamp_desc", "timestamp"),
        Index("ix_audit_logs_user_timestamp", "user_id", "timestamp"),
        Index("ix_audit_logs_device_timestamp", "device_id", "timestamp"),
        Index("ix_audit_logs_category_timestamp", "operation_category", "timestamp"),
    )

    user = relationship("User", back_populates="audit_logs")
    device = relationship("Device", backref="audit_logs")

    def __repr__(self) -> str:
        return f"<AuditLog(id={self.id}, type='{self.operation_type}', device='{self.device_id}')>"
