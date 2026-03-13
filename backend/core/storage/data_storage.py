"""
数据存储模块

功能：
- SQLite数据库管理
- 完整的CRUD操作支持
- 用户、设备、实验、数据记录、PR路径管理
- 集成查询性能监控和索引优化

作者: Agent
创建日期: 2024-03-06
更新日期: 2026-03-07
依赖: sqlalchemy
"""

import json
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from models import (
    Base,
    DataRecord,
    Device,
    DeviceCalibration,
    Experiment,
    ExperimentConfig,
    OperationLog,
    PRPath,
    User,
)

logger = logging.getLogger(__name__)


class DataStorage:
    """
    数据存储管理器

    使用SQLite单文件数据库，零配置。
    支持用户、设备、实验、数据记录、PR路径的完整CRUD操作。
    集成查询性能监控和索引优化功能。

    Attributes:
        db_path: 数据库文件路径
        enable_monitoring: 是否启用性能监控
    """

    def __init__(self, db_path: str = "experiments.db", enable_monitoring: bool = True):
        """
        初始化数据存储

        Args:
            db_path: 数据库文件路径
            enable_monitoring: 是否启用性能监控，默认True
        """
        self._db_path = db_path
        self._enable_monitoring = enable_monitoring

        self.engine = create_engine(
            f"sqlite:///{db_path}", connect_args={"check_same_thread": False}
        )

        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        self._current_experiment_id: int | None = None
        self._data_buffer: list[dict[str, Any]] = []

        # 初始化性能监控
        self._performance_monitor = None
        if enable_monitoring:
            try:
                from core.index_optimizer import QueryPerformanceMonitor, setup_query_monitoring

                self._performance_monitor = QueryPerformanceMonitor(db_path)
                setup_query_monitoring(self.engine, self._performance_monitor)
                logger.info("Query performance monitoring enabled")
            except ImportError:
                logger.warning("Query performance monitoring not available")

        logger.info(f"DataStorage initialized: {db_path}")

    # ==================== 用户管理 ====================

    def create_user(
        self, username: str, password_hash: str, role: str = "operator", email: str | None = None
    ) -> int:
        """
        创建用户

        Args:
            username: 用户名
            password_hash: 密码哈希
            role: 用户角色
            email: 邮箱地址

        Returns:
            int: 用户ID
        """
        session = self.Session()
        try:
            user = User(username=username, password_hash=password_hash, role=role, email=email)
            session.add(user)
            session.commit()
            logger.info(f"User created: {username}")
            return user.id
        finally:
            session.close()

    def get_user(self, user_id: int) -> dict[str, Any] | None:
        """
        获取用户信息

        Args:
            user_id: 用户ID

        Returns:
            Dict: 用户信息字典，未找到时返回None
        """
        session = self.Session()
        try:
            user = session.query(User).get(user_id)
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "is_active": user.is_active,
                }
            return None
        finally:
            session.close()

    def get_user_by_username(self, username: str) -> dict[str, Any] | None:
        """
        通过用户名获取用户

        Args:
            username: 用户名

        Returns:
            Dict: 用户信息字典，未找到时返回None
        """
        session = self.Session()
        try:
            user = session.query(User).filter(User.username == username).first()
            if user:
                return {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "email": user.email,
                    "created_at": user.created_at.isoformat() if user.created_at else None,
                    "last_login": user.last_login.isoformat() if user.last_login else None,
                    "is_active": user.is_active,
                }
            return None
        finally:
            session.close()

    def list_users(self) -> list[dict[str, Any]]:
        """
        列出所有用户

        Returns:
            List[Dict]: 用户列表
        """
        session = self.Session()
        try:
            users = session.query(User).all()
            return [
                {
                    "id": u.id,
                    "username": u.username,
                    "role": u.role,
                    "email": u.email,
                    "is_active": u.is_active,
                }
                for u in users
            ]
        finally:
            session.close()

    def update_user_last_login(self, user_id: int):
        """
        更新用户最后登录时间

        Args:
            user_id: 用户ID
        """
        session = self.Session()
        try:
            user = session.query(User).get(user_id)
            if user:
                user.last_login = datetime.now()
                session.commit()
        finally:
            session.close()

    # ==================== 设备管理 ====================

    def create_device(
        self,
        device_id: str,
        device_type: str,
        device_name: str | None = None,
        connection_params: dict | None = None,
        status: str = "offline",
    ) -> int:
        """
        创建设备

        Args:
            device_id: 设备唯一标识
            device_type: 设备类型
            device_name: 设备名称
            connection_params: 连接参数字典
            status: 设备状态

        Returns:
            int: 设备ID
        """
        session = self.Session()
        try:
            device = Device(
                device_id=device_id,
                device_type=device_type,
                device_name=device_name,
                connection_params=json.dumps(connection_params) if connection_params else None,
                status=status,
            )
            session.add(device)
            session.commit()
            logger.info(f"Device created: {device_id}")
            return device.id
        finally:
            session.close()

    def get_device(self, device_id: str) -> dict[str, Any] | None:
        """
        获取设备信息

        Args:
            device_id: 设备ID

        Returns:
            Dict: 设备信息字典
        """
        session = self.Session()
        try:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if device:
                return {
                    "id": device.id,
                    "device_id": device.device_id,
                    "device_type": device.device_type,
                    "device_name": device.device_name,
                    "connection_params": (
                        json.loads(device.connection_params) if device.connection_params else None
                    ),
                    "status": device.status,
                    "created_at": device.created_at.isoformat() if device.created_at else None,
                }
            return None
        finally:
            session.close()

    def list_devices(self) -> list[dict[str, Any]]:
        """
        列出所有设备

        Returns:
            List[Dict]: 设备列表
        """
        session = self.Session()
        try:
            devices = session.query(Device).all()
            return [
                {
                    "id": d.id,
                    "device_id": d.device_id,
                    "device_type": d.device_type,
                    "device_name": d.device_name,
                    "status": d.status,
                }
                for d in devices
            ]
        finally:
            session.close()

    def update_device_status(self, device_id: str, status: str):
        """
        更新设备状态

        Args:
            device_id: 设备ID
            status: 新状态
        """
        session = self.Session()
        try:
            device = session.query(Device).filter(Device.device_id == device_id).first()
            if device:
                device.status = status
                session.commit()
        finally:
            session.close()

    # ==================== 实验管理 ====================

    def create_experiment(
        self,
        exp_name: str,
        exp_type: str | None = None,
        user_id: int | None = None,
        sequence_config: dict | None = None,
        experiment_metadata: dict | None = None,
    ) -> int:
        """
        创建实验

        Args:
            exp_name: 实验名称
            exp_type: 实验类型
            user_id: 用户ID
            sequence_config: 序列配置
            experiment_metadata: 元数据

        Returns:
            int: 实验ID
        """
        session = self.Session()
        try:
            experiment = Experiment(
                exp_name=exp_name,
                exp_type=exp_type,
                user_id=user_id,
                sequence_config=json.dumps(sequence_config) if sequence_config else None,
                status="pending",
                experiment_metadata=(
                    json.dumps(experiment_metadata) if experiment_metadata else None
                ),
            )
            session.add(experiment)
            session.commit()
            logger.info(f"Experiment created: {exp_name} (ID={experiment.id})")
            return experiment.id
        finally:
            session.close()

    def start_experiment(
        self,
        exp_id: int | None = None,
        name: str | None = None,
        description: str | None = None,
        params: dict | None = None,
    ) -> int:
        """
        开始实验（兼容原有接口）

        Args:
            exp_id: 现有实验ID（可选）
            name: 实验名称（创建新实验时使用）
            description: 实验描述
            params: 实验参数

        Returns:
            int: 实验ID
        """
        session = self.Session()
        try:
            if exp_id:
                experiment = session.query(Experiment).get(exp_id)
            else:
                experiment = Experiment(
                    exp_name=name or "未命名实验",
                    status="running",
                    experiment_metadata=(
                        json.dumps({"description": description, "params": params})
                        if description or params
                        else None
                    ),
                )
                session.add(experiment)

            if experiment:
                experiment.status = "running"
                experiment.started_at = datetime.now()
                session.commit()
                self._current_experiment_id = experiment.id
                self._data_buffer = []
                logger.info(f"Experiment started: ID={experiment.id}")
                return experiment.id
            return 0
        finally:
            session.close()

    def get_experiment(self, exp_id: int) -> dict[str, Any] | None:
        """
        获取实验详情

        Args:
            exp_id: 实验ID

        Returns:
            Dict: 实验数据字典
        """
        session = self.Session()
        try:
            experiment = session.query(Experiment).get(exp_id)
            if experiment:
                return {
                    "id": experiment.id,
                    "exp_name": experiment.exp_name,
                    "exp_type": experiment.exp_type,
                    "user_id": experiment.user_id,
                    "sequence_config": (
                        json.loads(experiment.sequence_config)
                        if experiment.sequence_config
                        else None
                    ),
                    "status": experiment.status,
                    "started_at": (
                        experiment.started_at.isoformat() if experiment.started_at else None
                    ),
                    "completed_at": (
                        experiment.completed_at.isoformat() if experiment.completed_at else None
                    ),
                    "data_file_path": experiment.data_file_path,
                    "experiment_metadata": (
                        json.loads(experiment.experiment_metadata)
                        if experiment.experiment_metadata
                        else None
                    ),
                }
            return None
        finally:
            session.close()

    def list_experiments(
        self, limit: int = 100, user_id: int | None = None
    ) -> list[dict[str, Any]]:
        """
        列出实验

        Args:
            limit: 最大返回数量
            user_id: 过滤用户ID

        Returns:
            List[Dict]: 实验列表
        """
        session = self.Session()
        try:
            query = session.query(Experiment)
            if user_id:
                query = query.filter(Experiment.user_id == user_id)
            experiments = query.order_by(Experiment.created_at.desc()).limit(limit).all()

            return [
                {
                    "id": exp.id,
                    "exp_name": exp.exp_name,
                    "exp_type": exp.exp_type,
                    "status": exp.status,
                    "started_at": exp.started_at.isoformat() if exp.started_at else None,
                    "completed_at": exp.completed_at.isoformat() if exp.completed_at else None,
                }
                for exp in experiments
            ]
        finally:
            session.close()

    def stop_experiment(self, status: str = "completed"):
        """
        停止当前实验

        Args:
            status: 结束状态
        """
        self._save_buffer()

        if not self._current_experiment_id:
            return

        session = self.Session()
        try:
            experiment = session.query(Experiment).get(self._current_experiment_id)
            if experiment:
                experiment.status = status
                experiment.completed_at = datetime.now()
                session.commit()
                logger.info(f"Experiment {self._current_experiment_id} stopped: {status}")
            self._current_experiment_id = None
        finally:
            session.close()

    def delete_experiment(self, exp_id: int) -> bool:
        """
        删除实验

        Args:
            exp_id: 实验ID

        Returns:
            bool: 是否成功
        """
        session = self.Session()
        try:
            experiment = session.query(Experiment).get(exp_id)
            if experiment:
                session.delete(experiment)
                session.commit()
                logger.info(f"Experiment {exp_id} deleted")
                return True
            return False
        finally:
            session.close()

    # ==================== 数据记录管理 ====================

    def add_data_record(
        self,
        experiment_id: int,
        position_steps: int | None = None,
        position_mm: float | None = None,
        field_value: float | None = None,
        current_value: float | None = None,
        temperature: float | None = None,
        extra_data: dict | None = None,
    ) -> int:
        """
        添加数据记录

        Args:
            experiment_id: 实验ID
            position_steps: 位置（步数）
            position_mm: 位置（毫米）
            field_value: 磁场值
            current_value: 电流值
            temperature: 温度值
            extra_data: 额外数据

        Returns:
            int: 数据记录ID
        """
        session = self.Session()
        try:
            record = DataRecord(
                experiment_id=experiment_id,
                position_steps=position_steps,
                position_mm=position_mm,
                field_value=field_value,
                current_value=current_value,
                temperature=temperature,
                extra_data=json.dumps(extra_data) if extra_data else None,
            )
            session.add(record)
            session.commit()
            return record.id
        finally:
            session.close()

    def add_data_point(
        self,
        position_steps: int,
        field_value: float | None = None,
        current_value: float | None = None,
    ):
        """
        添加数据点（兼容原有接口）

        Args:
            position_steps: 位置（步数）
            field_value: 磁场值
            current_value: 电流值
        """
        from .dm2c_driver import steps_to_mm

        data_point = {
            "timestamp": datetime.now().isoformat(),
            "position_steps": position_steps,
            "position_mm": steps_to_mm(position_steps),
            "field": field_value,
            "current": current_value,
        }

        self._data_buffer.append(data_point)

        if len(self._data_buffer) >= 100:
            self._save_buffer()

    def _save_buffer(self):
        """保存缓冲区数据到数据库"""
        if not self._current_experiment_id or not self._data_buffer:
            return

        session = self.Session()
        try:
            for dp in self._data_buffer:
                record = DataRecord(
                    experiment_id=self._current_experiment_id,
                    timestamp=datetime.fromisoformat(dp["timestamp"]),
                    position_steps=dp.get("position_steps"),
                    position_mm=dp.get("position_mm"),
                    field_value=dp.get("field"),
                    current_value=dp.get("current"),
                )
                session.add(record)
            session.commit()
            self._data_buffer = []
        finally:
            session.close()

    def get_experiment_data(self, exp_id: int, limit: int = 10000) -> list[dict[str, Any]]:
        """
        获取实验数据记录

        Args:
            exp_id: 实验ID
            limit: 最大返回数量

        Returns:
            List[Dict]: 数据记录列表
        """
        session = self.Session()
        try:
            records = (
                session.query(DataRecord)
                .filter(DataRecord.experiment_id == exp_id)
                .order_by(DataRecord.timestamp)
                .limit(limit)
                .all()
            )

            return [
                {
                    "id": r.id,
                    "timestamp": r.timestamp.isoformat() if r.timestamp else None,
                    "position_steps": r.position_steps,
                    "position_mm": r.position_mm,
                    "field_value": r.field_value,
                    "current_value": r.current_value,
                    "temperature": r.temperature,
                    "extra_data": json.loads(r.extra_data) if r.extra_data else None,
                }
                for r in records
            ]
        finally:
            session.close()

    # ==================== PR路径管理 ====================

    def create_pr_path(
        self,
        device_id: str,
        path_number: int,
        mode: int = 1,
        position_high: int = 0,
        position_low: int = 0,
        velocity: int = 1000,
        accel_time: int = 100,
        decel_time: int = 100,
        dwell_time: int = 0,
        special_param: int = 0,
    ) -> int:
        """
        创建PR路径配置

        Args:
            device_id: 设备ID
            path_number: 路径编号 (0-15)
            mode: 运动模式
            position_high: 位置高字
            position_low: 位置低字
            velocity: 速度
            accel_time: 加速时间
            decel_time: 减速时间
            dwell_time: 停留时间
            special_param: 特殊参数

        Returns:
            int: PR路径ID
        """
        session = self.Session()
        try:
            pr_path = PRPath(
                device_id=device_id,
                path_number=path_number,
                mode=mode,
                position_high=position_high,
                position_low=position_low,
                velocity=velocity,
                accel_time=accel_time,
                decel_time=decel_time,
                dwell_time=dwell_time,
                special_param=special_param,
            )
            session.add(pr_path)
            session.commit()
            logger.info(f"PR Path created: device={device_id}, path={path_number}")
            return pr_path.id
        finally:
            session.close()

    def get_pr_path(self, device_id: str, path_number: int) -> dict[str, Any] | None:
        """
        获取PR路径配置

        Args:
            device_id: 设备ID
            path_number: 路径编号

        Returns:
            Dict: PR路径配置字典
        """
        session = self.Session()
        try:
            pr_path = (
                session.query(PRPath)
                .filter(PRPath.device_id == device_id, PRPath.path_number == path_number)
                .first()
            )

            if pr_path:
                return {
                    "id": pr_path.id,
                    "device_id": pr_path.device_id,
                    "path_number": pr_path.path_number,
                    "mode": pr_path.mode,
                    "position_high": pr_path.position_high,
                    "position_low": pr_path.position_low,
                    "velocity": pr_path.velocity,
                    "accel_time": pr_path.accel_time,
                    "decel_time": pr_path.decel_time,
                    "dwell_time": pr_path.dwell_time,
                    "special_param": pr_path.special_param,
                    "created_at": pr_path.created_at.isoformat() if pr_path.created_at else None,
                    "updated_at": pr_path.updated_at.isoformat() if pr_path.updated_at else None,
                }
            return None
        finally:
            session.close()

    def list_pr_paths(self, device_id: str) -> list[dict[str, Any]]:
        """
        列出设备的所有PR路径

        Args:
            device_id: 设备ID

        Returns:
            List[Dict]: PR路径列表
        """
        session = self.Session()
        try:
            pr_paths = (
                session.query(PRPath)
                .filter(PRPath.device_id == device_id)
                .order_by(PRPath.path_number)
                .all()
            )

            return [
                {
                    "id": p.id,
                    "path_number": p.path_number,
                    "mode": p.mode,
                    "position_high": p.position_high,
                    "position_low": p.position_low,
                    "velocity": p.velocity,
                    "accel_time": p.accel_time,
                    "decel_time": p.decel_time,
                    "dwell_time": p.dwell_time,
                }
                for p in pr_paths
            ]
        finally:
            session.close()

    def update_pr_path(self, device_id: str, path_number: int, **kwargs) -> bool:
        """
        更新PR路径配置

        Args:
            device_id: 设备ID
            path_number: 路径编号
            **kwargs: 要更新的字段

        Returns:
            bool: 是否成功
        """
        session = self.Session()
        try:
            pr_path = (
                session.query(PRPath)
                .filter(PRPath.device_id == device_id, PRPath.path_number == path_number)
                .first()
            )

            if pr_path:
                allowed_fields = [
                    "mode",
                    "position_high",
                    "position_low",
                    "velocity",
                    "accel_time",
                    "decel_time",
                    "dwell_time",
                    "special_param",
                ]
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        setattr(pr_path, key, value)
                pr_path.updated_at = datetime.now()
                session.commit()
                return True
            return False
        finally:
            session.close()

    # ==================== 导出功能 ====================

    def export_to_csv(self, exp_id: int, filepath: str) -> bool:
        """
        导出实验数据到CSV

        Args:
            exp_id: 实验ID
            filepath: CSV文件路径

        Returns:
            bool: 是否成功
        """
        import csv

        records = self.get_experiment_data(exp_id)
        if not records:
            return False

        try:
            with open(filepath, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)

                headers = ["timestamp", "position_mm"]
                has_field = any(r.get("field_value") is not None for r in records)
                has_current = any(r.get("current_value") is not None for r in records)
                has_temp = any(r.get("temperature") is not None for r in records)

                if has_field:
                    headers.append("field")
                if has_current:
                    headers.append("current")
                if has_temp:
                    headers.append("temperature")

                writer.writerow(headers)

                for i, r in enumerate(records):
                    row = [r.get("timestamp"), r.get("position_mm")]
                    if has_field:
                        row.append(r.get("field_value"))
                    if has_current:
                        row.append(r.get("current_value"))
                    if has_temp:
                        row.append(r.get("temperature"))
                    writer.writerow(row)

            logger.info(f"Experiment {exp_id} exported to {filepath}")
            return True

        except Exception as e:
            logger.error(f"Export error: {e}")
            return False

    # ==================== 设备校准参数管理 ====================

    def create_device_calibration(
        self,
        device_id: str,
        param_name: str,
        param_value: str,
        calibration_date: datetime | None = None,
        valid_until: datetime | None = None,
    ) -> int:
        """
        创建设备校准参数

        Args:
            device_id: 设备ID
            param_name: 参数名称
            param_value: 参数值
            calibration_date: 校准日期
            valid_until: 有效期截止日期

        Returns:
            int: 校准参数ID
        """
        session = self.Session()
        try:
            calibration = DeviceCalibration(
                device_id=device_id,
                param_name=param_name,
                param_value=param_value,
                calibration_date=calibration_date,
                valid_until=valid_until,
            )
            session.add(calibration)
            session.commit()
            logger.info(f"Device calibration created: device={device_id}, param={param_name}")
            return calibration.id
        finally:
            session.close()

    def get_device_calibration(self, device_id: str, param_name: str) -> dict[str, Any] | None:
        """
        获取设备校准参数

        Args:
            device_id: 设备ID
            param_name: 参数名称

        Returns:
            Dict: 校准参数字典，未找到时返回None
        """
        session = self.Session()
        try:
            calibration = (
                session.query(DeviceCalibration)
                .filter(
                    DeviceCalibration.device_id == device_id,
                    DeviceCalibration.param_name == param_name,
                )
                .first()
            )
            if calibration:
                return {
                    "id": calibration.id,
                    "device_id": calibration.device_id,
                    "param_name": calibration.param_name,
                    "param_value": calibration.param_value,
                    "calibration_date": (
                        calibration.calibration_date.isoformat()
                        if calibration.calibration_date
                        else None
                    ),
                    "valid_until": (
                        calibration.valid_until.isoformat() if calibration.valid_until else None
                    ),
                }
            return None
        finally:
            session.close()

    def list_device_calibrations(self, device_id: str) -> list[dict[str, Any]]:
        """
        列出设备的所有校准参数

        Args:
            device_id: 设备ID

        Returns:
            List[Dict]: 校准参数列表
        """
        session = self.Session()
        try:
            calibrations = (
                session.query(DeviceCalibration)
                .filter(DeviceCalibration.device_id == device_id)
                .all()
            )
            return [
                {
                    "id": c.id,
                    "param_name": c.param_name,
                    "param_value": c.param_value,
                    "calibration_date": (
                        c.calibration_date.isoformat() if c.calibration_date else None
                    ),
                    "valid_until": c.valid_until.isoformat() if c.valid_until else None,
                }
                for c in calibrations
            ]
        finally:
            session.close()

    def update_device_calibration(self, device_id: str, param_name: str, **kwargs) -> bool:
        """
        更新设备校准参数

        Args:
            device_id: 设备ID
            param_name: 参数名称
            **kwargs: 要更新的字段

        Returns:
            bool: 是否成功
        """
        session = self.Session()
        try:
            calibration = (
                session.query(DeviceCalibration)
                .filter(
                    DeviceCalibration.device_id == device_id,
                    DeviceCalibration.param_name == param_name,
                )
                .first()
            )
            if calibration:
                allowed_fields = ["param_value", "calibration_date", "valid_until"]
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        setattr(calibration, key, value)
                session.commit()
                return True
            return False
        finally:
            session.close()

    # ==================== 操作日志管理 ====================

    def create_operation_log(
        self,
        operation: str,
        user_id: int | None = None,
        device_id: str | None = None,
        parameters: dict | None = None,
        result: str | None = None,
        error_message: str | None = None,
    ) -> int:
        """
        创建操作日志

        Args:
            operation: 操作类型
            user_id: 用户ID
            device_id: 设备ID
            parameters: 操作参数字典
            result: 操作结果
            error_message: 错误信息

        Returns:
            int: 日志ID
        """
        session = self.Session()
        try:
            log = OperationLog(
                user_id=user_id,
                device_id=device_id,
                operation=operation,
                parameters=json.dumps(parameters) if parameters else None,
                result=result,
                error_message=error_message,
            )
            session.add(log)
            session.commit()
            logger.info(f"Operation log created: {operation}")
            return log.id
        finally:
            session.close()

    def list_operation_logs(
        self,
        limit: int = 100,
        user_id: int | None = None,
        device_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        列出操作日志

        Args:
            limit: 最大返回数量
            user_id: 过滤用户ID
            device_id: 过滤设备ID

        Returns:
            List[Dict]: 日志列表
        """
        session = self.Session()
        try:
            query = session.query(OperationLog)
            if user_id:
                query = query.filter(OperationLog.user_id == user_id)
            if device_id:
                query = query.filter(OperationLog.device_id == device_id)
            logs = query.order_by(OperationLog.created_at.desc()).limit(limit).all()

            return [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "device_id": log.device_id,
                    "operation": log.operation,
                    "parameters": json.loads(log.parameters) if log.parameters else None,
                    "result": log.result,
                    "error_message": log.error_message,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
                for log in logs
            ]
        finally:
            session.close()

    # ==================== 实验配置管理 ====================

    def create_experiment_config(
        self,
        name: str,
        config_json: dict,
        description: str | None = None,
    ) -> int:
        """
        创建实验配置

        Args:
            name: 配置名称
            config_json: 配置数据字典
            description: 配置描述

        Returns:
            int: 配置ID
        """
        session = self.Session()
        try:
            config = ExperimentConfig(
                name=name,
                description=description,
                config_json=json.dumps(config_json),
            )
            session.add(config)
            session.commit()
            logger.info(f"Experiment config created: {name}")
            return config.id
        finally:
            session.close()

    def get_experiment_config(self, config_id: int) -> dict[str, Any] | None:
        """
        获取实验配置

        Args:
            config_id: 配置ID

        Returns:
            Dict: 配置字典，未找到时返回None
        """
        session = self.Session()
        try:
            config = session.query(ExperimentConfig).get(config_id)
            if config:
                return {
                    "id": config.id,
                    "name": config.name,
                    "description": config.description,
                    "config_json": (json.loads(config.config_json) if config.config_json else None),
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "updated_at": config.updated_at.isoformat() if config.updated_at else None,
                }
            return None
        finally:
            session.close()

    def list_experiment_configs(self, limit: int = 100) -> list[dict[str, Any]]:
        """
        列出实验配置

        Args:
            limit: 最大返回数量

        Returns:
            List[Dict]: 配置列表
        """
        session = self.Session()
        try:
            configs = (
                session.query(ExperimentConfig)
                .order_by(ExperimentConfig.created_at.desc())
                .limit(limit)
                .all()
            )
            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "description": c.description,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                    "updated_at": c.updated_at.isoformat() if c.updated_at else None,
                }
                for c in configs
            ]
        finally:
            session.close()

    def update_experiment_config(self, config_id: int, **kwargs) -> bool:
        """
        更新实验配置

        Args:
            config_id: 配置ID
            **kwargs: 要更新的字段

        Returns:
            bool: 是否成功
        """
        session = self.Session()
        try:
            config = session.query(ExperimentConfig).get(config_id)
            if config:
                allowed_fields = ["name", "description", "config_json"]
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        if key == "config_json" and isinstance(value, dict):
                            value = json.dumps(value)
                        setattr(config, key, value)
                session.commit()
                return True
            return False
        finally:
            session.close()

    def delete_experiment_config(self, config_id: int) -> bool:
        """
        删除实验配置

        Args:
            config_id: 配置ID

        Returns:
            bool: 是否成功
        """
        session = self.Session()
        try:
            config = session.query(ExperimentConfig).get(config_id)
            if config:
                session.delete(config)
                session.commit()
                logger.info(f"Experiment config {config_id} deleted")
                return True
            return False
        finally:
            session.close()

    # ==================== 性能监控与索引优化 ====================

    def get_performance_statistics(self) -> dict[str, Any]:
        """获取查询性能统计信息。

        Returns:
            性能统计字典，如果未启用监控则返回空字典
        """
        if not self._performance_monitor:
            return {"monitoring_enabled": False}

        return {
            "monitoring_enabled": True,
            **self._performance_monitor.get_statistics(),
        }

    def get_slow_queries(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取慢查询列表。

        Args:
            limit: 最大返回数量

        Returns:
            慢查询列表，如果未启用监控则返回空列表
        """
        if not self._performance_monitor:
            return []

        return self._performance_monitor.get_slow_queries(limit)

    def get_query_patterns(self, limit: int = 100) -> list[dict[str, Any]]:
        """获取查询模式分析结果。

        Args:
            limit: 最大返回数量

        Returns:
            查询模式列表，如果未启用监控则返回空列表
        """
        if not self._performance_monitor:
            return []

        return self._performance_monitor.get_query_patterns(limit)

    def optimize_indexes(self, dry_run: bool = False) -> dict[str, Any]:
        """优化数据库索引。

        Args:
            dry_run: 是否只分析不执行

        Returns:
            索引优化结果字典
        """
        try:
            from core.index_optimizer import DatabaseIndexMigration

            migration = DatabaseIndexMigration(self._db_path)
            return migration.migrate(dry_run=dry_run)

        except ImportError:
            logger.error("Index optimizer not available")
            return {"error": "Index optimizer not available"}

    def analyze_query_performance(self, sql: str) -> dict[str, Any]:
        """分析单个查询的性能。

        Args:
            sql: SQL语句

        Returns:
            性能分析结果
        """
        try:
            from core.index_optimizer import IndexOptimizer

            optimizer = IndexOptimizer(self._db_path)
            return optimizer.analyze_query_performance(sql)

        except ImportError:
            logger.error("Index optimizer not available")
            return {"error": "Index optimizer not available"}

    def clear_performance_history(self) -> None:
        """清空性能监控历史记录。"""
        if self._performance_monitor:
            self._performance_monitor.clear_history()
            logger.info("Performance history cleared")
