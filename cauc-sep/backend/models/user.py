"""
用户数据模型模块

功能：
- 定义用户表结构
- 支持用户角色权限管理
- 用户偏好设置（JSON格式）
- 头像管理

作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: sqlalchemy
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Integer,
    String,
    Text,
    Index,
)
from sqlalchemy.orm import relationship

from models import Base

# ==================== 常量定义 ====================

# 用户角色有效值
VALID_USER_ROLES = ("admin", "user", "guest")

# 默认用户偏好设置
DEFAULT_PREFERENCES = {
    "theme": "light",
    "language": "zh-CN",
    "notifications": {
        "enabled": True,
        "sound": True,
    },
    "display_options": {
        "refresh_rate": 1000,
        "chart_default": "line",
    },
}


class User(Base):
    """
    用户表

    存储系统用户信息，包括用户名、密码哈希、角色、邮箱、头像、偏好设置等。
    支持角色权限管理和登录审计。

    Attributes:
        id: 主键，自增整数
        username: 用户名，唯一，最大50字符
        email: 邮箱地址，唯一，最大100字符
        password_hash: 密码哈希值，最大255字符
        role: 用户角色，默认user
        avatar: 头像URL，可选
        preferences: 用户偏好设置JSON字符串
        created_at: 创建时间
        updated_at: 更新时间
        is_active: 是否激活状态
    """

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="user", nullable=False, index=True)
    avatar = Column(String(500), nullable=True)
    preferences = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False, onupdate=datetime.now)
    is_active = Column(Boolean, default=True, nullable=False)

    # 角色有效性约束
    __table_args__ = (
        CheckConstraint(
            f"role IN {VALID_USER_ROLES}",
            name="ck_user_role_valid"
        ),
        CheckConstraint(
            "LENGTH(username) >= 3",
            name="ck_user_username_length"
        ),
        CheckConstraint(
            "LENGTH(password_hash) >= 32",
            name="ck_user_password_hash_length"
        ),
        Index("ix_users_role_active", "role", "is_active"),
    )

    # 关系定义
    experiments = relationship("Experiment", back_populates="user")
    operation_logs = relationship("OperationLog", back_populates="user")
    audit_logs = relationship("AuditLog", back_populates="user")
    operation_histories = relationship("OperationHistory", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User(id={self.id}, username='{self.username}', role='{self.role}')>"

    def get_preferences(self) -> dict:
        """
        获取用户偏好设置。

        Returns:
            dict: 用户偏好设置字典
        """
        import json
        if self.preferences:
            try:
                return json.loads(self.preferences)
            except (json.JSONDecodeError, TypeError):
                pass
        return DEFAULT_PREFERENCES.copy()

    def set_preferences(self, preferences: dict) -> None:
        """
        设置用户偏好设置。

        Args:
            preferences: 用户偏好设置字典
        """
        import json
        self.preferences = json.dumps(preferences, ensure_ascii=False)
