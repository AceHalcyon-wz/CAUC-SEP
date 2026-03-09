"""
操作历史数据模型模块

功能：
- 记录用户操作历史
- 支持设备关联
- 操作详情JSON存储

作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: sqlalchemy
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from models import Base

# ==================== 常量定义 ====================

# 操作类型有效值
VALID_OPERATION_TYPES = (
    "login",
    "logout",
    "motor_move",
    "motor_jog",
    "motor_stop",
    "electromagnet_set",
    "electromagnet_scan",
    "temperature_set",
    "temperature_program",
    "piezo_set",
    "ammeter_start",
    "ammeter_stop",
    "experiment_start",
    "experiment_stop",
    "config_change",
    "calibration",
    "file_export",
    "other",
)


class OperationHistory(Base):
    """
    操作历史表

    记录用户对设备和系统的操作历史，包括操作类型、详情、相关设备等。
    用于操作追溯和问题排查。

    Attributes:
        id: 主键，自增整数
        user_id: 关联用户ID，外键
        operation_type: 操作类型
        operation_detail: 操作详情JSON字符串
        device_id: 相关设备ID，可选
        created_at: 创建时间
    """

    __tablename__ = "operation_histories"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    operation_type = Column(String(50), nullable=False, index=True)
    operation_detail = Column(Text, nullable=True)
    device_id = Column(String(50), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)

    # 索引优化
    __table_args__ = (
        Index("ix_operation_histories_user_created", "user_id", "created_at"),
        Index("ix_operation_histories_type_created", "operation_type", "created_at"),
        Index("ix_operation_histories_device_created", "device_id", "created_at"),
    )

    # 关系定义
    user = relationship("User", back_populates="operation_histories")

    def __repr__(self) -> str:
        return f"<OperationHistory(id={self.id}, user_id={self.user_id}, type='{self.operation_type}')>"

    def get_detail(self) -> dict:
        """
        获取操作详情。

        Returns:
            dict: 操作详情字典
        """
        import json

        if self.operation_detail:
            try:
                return json.loads(self.operation_detail)
            except (json.JSONDecodeError, TypeError):
                pass
        return {}

    def set_detail(self, detail: dict) -> None:
        """
        设置操作详情。

        Args:
            detail: 操作详情字典
        """
        import json

        self.operation_detail = json.dumps(detail, ensure_ascii=False)
