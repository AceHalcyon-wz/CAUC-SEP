"""
实验数据模型模块

文件名: experiment.py
路径: backend/models/
功能: 定义实验相关的 SQLAlchemy 模型，包含实验记录、数据记录、实验配置等
作者: Backend Engineer Agent
创建日期: 2024-03-06
更新日期: 2026-03-14
依赖: sqlalchemy

模块内容:
    - Experiment: 实验表模型
    - DataRecord: 数据记录表模型
    - ExperimentConfig: 实验配置表模型
    - VALID_EXPERIMENT_STATUSES: 有效实验状态常量
"""

from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from models.device import Base

VALID_EXPERIMENT_STATUSES = ("pending", "running", "completed", "failed", "cancelled")


class Experiment(Base):
    """
    实验表

    存储实验记录，包括实验名称、类型、用户、序列配置、状态、时间等。
    支持实验生命周期管理和数据关联。

    Attributes:
        id: 主键，自增整数
        exp_name: 实验名称，最大100字符
        exp_type: 实验类型，可选
        user_id: 关联用户ID，外键
        sequence_config: 序列配置JSON字符串
        status: 实验状态，默认pending
        created_at: 创建时间
        started_at: 开始时间
        completed_at: 完成时间
        data_file_path: 数据文件路径
        experiment_metadata: 实验元数据JSON字符串
    """

    __tablename__ = "experiments"

    id = Column(Integer, primary_key=True, autoincrement=True)
    exp_name = Column(String(100), nullable=False, index=True)
    exp_type = Column(String(50), nullable=True, index=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    sequence_config = Column(Text, nullable=True)
    status = Column(String(20), default="pending", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False, index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    data_file_path = Column(String(255), nullable=True)
    experiment_metadata = Column(Text, nullable=True)

    __table_args__ = (
        CheckConstraint(
            f"status IN {VALID_EXPERIMENT_STATUSES}", name="ck_experiment_status_valid"
        ),
        CheckConstraint("LENGTH(exp_name) >= 1", name="ck_experiment_name_not_empty"),
        Index("ix_experiments_user_status", "user_id", "status"),
        Index("ix_experiments_created_desc", "created_at"),
    )

    user = relationship("User", back_populates="experiments")
    data_records = relationship(
        "DataRecord", back_populates="experiment", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Experiment(id={self.id}, name='{self.exp_name}', status='{self.status}')>"


class DataRecord(Base):
    """
    数据记录表

    关联实验表，存储实验过程中采集的时间序列数据。
    支持位置、磁场、电流、温度等多维度数据采集。

    Attributes:
        id: 主键，自增整数
        experiment_id: 关联实验ID，外键
        timestamp: 数据采集时间戳
        position_steps: 位置（步数）
        position_mm: 位置（毫米）
        field_value: 磁场值
        current_value: 电流值
        temperature: 温度值
        extra_data: 额外数据JSON字符串
    """

    __tablename__ = "data_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    experiment_id = Column(
        Integer, ForeignKey("experiments.id", ondelete="CASCADE"), nullable=False, index=True
    )
    timestamp = Column(DateTime, default=datetime.now, nullable=False, index=True)
    position_steps = Column(Integer, nullable=True)
    position_mm = Column(Float, nullable=True)
    field_value = Column(Float, nullable=True)
    current_value = Column(Float, nullable=True)
    temperature = Column(Float, nullable=True)
    extra_data = Column(Text, nullable=True)

    __table_args__ = (Index("ix_data_records_exp_timestamp", "experiment_id", "timestamp"),)

    experiment = relationship("Experiment", back_populates="data_records")

    def __repr__(self) -> str:
        return f"<DataRecord(id={self.id}, exp_id={self.experiment_id}, ts='{self.timestamp}')>"


class ExperimentConfig(Base):
    """
    实验配置表

    存储实验的预设配置模板，包括配置名称、描述和JSON格式的配置数据。
    支持实验模板管理和快速配置复用。

    Attributes:
        id: 主键，自增整数
        name: 配置名称
        description: 配置描述
        config_json: 配置数据JSON字符串
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "experiment_configs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    description = Column(Text, nullable=True)
    config_json = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False, onupdate=datetime.now)

    __table_args__ = (
        CheckConstraint("LENGTH(name) >= 1", name="ck_config_name_not_empty"),
        CheckConstraint("LENGTH(config_json) >= 2", name="ck_config_json_not_empty"),
    )

    def __repr__(self) -> str:
        return f"<ExperimentConfig(id={self.id}, name='{self.name}')>"
