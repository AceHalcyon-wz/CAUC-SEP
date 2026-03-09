"""
数据模型模块 - 自旋电子器件实验平台

功能：
- 定义SQLAlchemy数据模型
- 用户管理、设备管理、实验管理、数据记录、PR路径配置
- 包含完整的字段约束、索引优化和外键关系

作者: Agent
创建日期: 2024-03-06
更新日期: 2026-03-07
依赖: sqlalchemy
"""

from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

from models.operation_history import VALID_OPERATION_TYPES, OperationHistory

# 导出用户相关模型
from models.user import DEFAULT_PREFERENCES, VALID_USER_ROLES, User

__all__ = [
    "Base",
    "User",
    "Device",
    "Experiment",
    "DataRecord",
    "PRPath",
    "DeviceCalibration",
    "OperationLog",
    "ExperimentConfig",
    "AuditLog",
    "OperationHistory",
    "VALID_USER_ROLES",
    "DEFAULT_PREFERENCES",
    "VALID_OPERATION_TYPES",
    "VALID_DEVICE_STATUSES",
    "VALID_EXPERIMENT_STATUSES",
    "VALID_OPERATION_CATEGORIES",
    "VALID_REQUEST_METHODS",
]

# ==================== 常量定义 ====================

# 设备状态有效值
VALID_DEVICE_STATUSES = ("offline", "online", "busy", "error", "maintenance")

# 实验状态有效值
VALID_EXPERIMENT_STATUSES = ("pending", "running", "completed", "failed", "cancelled")

# 操作类别有效值
VALID_OPERATION_CATEGORIES = ("device", "experiment", "system", "calibration", "config")

# HTTP请求方法有效值
VALID_REQUEST_METHODS = ("GET", "POST", "PUT", "DELETE", "PATCH")


class Device(Base):
    """
    设备表

    存储系统中注册的硬件设备信息，包括设备ID、类型、名称、连接参数等。
    支持设备状态跟踪和连接配置管理。

    Attributes:
        id: 主键，自增整数
        device_id: 设备唯一标识，最大50字符
        device_type: 设备类型（stepper, electromagnet, temperature, piezo, picoammeter）
        device_name: 设备名称，可选
        connection_params: 连接参数JSON字符串
        status: 设备状态，默认offline
        created_at: 创建时间
    """

    __tablename__ = "devices"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String(50), unique=True, nullable=False, index=True)
    device_type = Column(String(50), nullable=False, index=True)
    device_name = Column(String(100), nullable=True)
    connection_params = Column(Text, nullable=True)
    status = Column(String(20), default="offline", nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.now, nullable=False)

    # 设备状态有效性约束
    __table_args__ = (
        CheckConstraint(f"status IN {VALID_DEVICE_STATUSES}", name="ck_device_status_valid"),
        CheckConstraint("LENGTH(device_id) >= 1", name="ck_device_id_not_empty"),
        Index("ix_devices_type_status", "device_type", "status"),
    )

    pr_paths = relationship("PRPath", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, device_id='{self.device_id}', type='{self.device_type}')>"


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

    # 实验状态有效性约束
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

    # 数据记录索引优化
    __table_args__ = (Index("ix_data_records_exp_timestamp", "experiment_id", "timestamp"),)

    experiment = relationship("Experiment", back_populates="data_records")

    def __repr__(self) -> str:
        return f"<DataRecord(id={self.id}, exp_id={self.experiment_id}, ts='{self.timestamp}')>"


class PRPath(Base):
    """
    PR路径配置表

    存储雷赛DM2C驱动器的PR路径配置参数，每个设备可以配置多段路径(0-15)。
    支持位置、速度、加速度等运动参数配置。

    Attributes:
        id: 主键，自增整数
        device_id: 关联设备ID，外键
        path_number: 路径编号(0-15)
        mode: 运动模式
        position_high: 位置高字
        position_low: 位置低字
        velocity: 速度
        accel_time: 加速时间
        decel_time: 减速时间
        dwell_time: 停留时间
        special_param: 特殊参数
        created_at: 创建时间
        updated_at: 更新时间
    """

    __tablename__ = "pr_paths"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(
        String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True
    )
    path_number = Column(Integer, nullable=False)
    mode = Column(Integer, default=1, nullable=False)
    position_high = Column(Integer, default=0, nullable=False)
    position_low = Column(Integer, default=0, nullable=False)
    velocity = Column(Integer, default=1000, nullable=False)
    accel_time = Column(Integer, default=100, nullable=False)
    decel_time = Column(Integer, default=100, nullable=False)
    dwell_time = Column(Integer, default=0, nullable=False)
    special_param = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, nullable=False, onupdate=datetime.now)

    # PR路径约束：路径编号范围和唯一性
    __table_args__ = (
        CheckConstraint("path_number >= 0 AND path_number <= 15", name="ck_pr_path_number_range"),
        CheckConstraint("velocity > 0", name="ck_pr_path_velocity_positive"),
        CheckConstraint("accel_time >= 0", name="ck_pr_path_accel_time_valid"),
        CheckConstraint("decel_time >= 0", name="ck_pr_path_decel_time_valid"),
        UniqueConstraint("device_id", "path_number", name="_device_path_uc"),
        Index("ix_pr_paths_device_path", "device_id", "path_number"),
    )

    device = relationship("Device", back_populates="pr_paths")

    def __repr__(self) -> str:
        return f"<PRPath(id={self.id}, device='{self.device_id}', path={self.path_number})>"


class DeviceCalibration(Base):
    """
    设备校准参数表

    存储设备的校准参数信息，包括参数名、参数值、校准日期和有效期。
    每个设备的每个参数名唯一，支持校准有效期管理。

    Attributes:
        id: 主键，自增整数
        device_id: 设备ID，外键关联devices.device_id
        param_name: 参数名称
        param_value: 参数值
        calibration_date: 校准日期
        valid_until: 有效期截止日期
    """

    __tablename__ = "device_calibrations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(
        String(50), ForeignKey("devices.device_id", ondelete="CASCADE"), nullable=False, index=True
    )
    param_name = Column(String(100), nullable=False)
    param_value = Column(Text, nullable=True)
    calibration_date = Column(DateTime, nullable=True)
    valid_until = Column(DateTime, nullable=True, index=True)

    # 校准参数约束
    __table_args__ = (
        CheckConstraint("LENGTH(device_id) >= 1", name="ck_calibration_device_id_not_empty"),
        CheckConstraint("LENGTH(param_name) >= 1", name="ck_calibration_param_name_not_empty"),
        UniqueConstraint("device_id", "param_name", name="_device_param_uc"),
        Index("ix_calibrations_device_param", "device_id", "param_name"),
    )

    device = relationship("Device", backref="calibrations")

    def __repr__(self) -> str:
        return f"<DeviceCalibration(id={self.id}, device='{self.device_id}', param='{self.param_name}')>"


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

    # 操作日志约束
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

    # 实验配置约束
    __table_args__ = (
        CheckConstraint("LENGTH(name) >= 1", name="ck_config_name_not_empty"),
        CheckConstraint("LENGTH(config_json) >= 2", name="ck_config_json_not_empty"),
    )

    def __repr__(self) -> str:
        return f"<ExperimentConfig(id={self.id}, name='{self.name}')>"


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

    # 审计日志约束
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
