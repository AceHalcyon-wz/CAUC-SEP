"""
设备数据模型模块

文件名: device.py
路径: backend/models/
功能: 定义设备相关的 SQLAlchemy 模型，包含设备信息、PR路径配置、校准参数等
作者: Backend Engineer Agent
创建日期: 2024-03-06
更新日期: 2026-03-14
依赖: sqlalchemy

模块内容:
    - Device: 设备表模型
    - PRPath: PR路径配置表模型
    - DeviceCalibration: 设备校准参数表模型
    - VALID_DEVICE_STATUSES: 有效设备状态常量
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
    UniqueConstraint,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

VALID_DEVICE_STATUSES = ("offline", "online", "busy", "error", "maintenance")


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

    __table_args__ = (
        CheckConstraint(f"status IN {VALID_DEVICE_STATUSES}", name="ck_device_status_valid"),
        CheckConstraint("LENGTH(device_id) >= 1", name="ck_device_id_not_empty"),
        Index("ix_devices_type_status", "device_type", "status"),
    )

    pr_paths = relationship("PRPath", back_populates="device", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Device(id={self.id}, device_id='{self.device_id}', type='{self.device_type}')>"


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

    __table_args__ = (
        CheckConstraint("LENGTH(device_id) >= 1", name="ck_calibration_device_id_not_empty"),
        CheckConstraint("LENGTH(param_name) >= 1", name="ck_calibration_param_name_not_empty"),
        UniqueConstraint("device_id", "param_name", name="_device_param_uc"),
        Index("ix_calibrations_device_param", "device_id", "param_name"),
    )

    device = relationship("Device", backref="calibrations")

    def __repr__(self) -> str:
        return f"<DeviceCalibration(id={self.id}, device='{self.device_id}', param='{self.param_name}')>"
