"""
测试数据工厂模块

文件名: factories.py
路径: backend/tests/
功能: 提供测试数据生成工厂，简化测试数据创建
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: factory_boy, pydantic, sqlalchemy

主要功能：
- 生成用户测试数据
- 生成实验测试数据
- 生成设备测试数据
- 生成传感器数据
- 支持批量数据生成

使用方法：
    from tests.factories import UserFactory, ExperimentFactory

    user = UserFactory.create(username="test_user")
    experiment = ExperimentFactory.create(user_id=user.id)
"""

import random
import time
from datetime import datetime, timedelta
from typing import Any

import numpy as np

try:
    import factory
    from factory import Faker, SubFactory
    from factory.alchemy import SQLAlchemyModelFactory

    FACTORY_BOY_AVAILABLE = True
except ImportError:
    FACTORY_BOY_AVAILABLE = False
    # 创建占位类，避免导入错误
    class factory:
        @staticmethod
        def Faker(*args, **kwargs):
            return None

        class Factory:
            pass

        class SQLAlchemyModelFactory:
            pass


# ==================== 数据生成工具函数 ====================


def generate_random_position(min_mm: float = -100.0, max_mm: float = 100.0) -> float:
    """生成随机位置值。

    Args:
        min_mm: 最小位置(mm)
        max_mm: 最大位置(mm)

    Returns:
        float: 随机位置值
    """
    return round(random.uniform(min_mm, max_mm), 3)


def generate_random_velocity(min_mm_s: float = 1.0, max_mm_s: float = 50.0) -> float:
    """生成随机速度值。

    Args:
        min_mm_s: 最小速度(mm/s)
        max_mm_s: 最大速度(mm/s)

    Returns:
        float: 随机速度值
    """
    return round(random.uniform(min_mm_s, max_mm_s), 2)


def generate_random_current(min_a: float = 0.0, max_a: float = 10.0) -> float:
    """生成随机电流值。

    Args:
        min_a: 最小电流(A)
        max_a: 最大电流(A)

    Returns:
        float: 随机电流值
    """
    return round(random.uniform(min_a, max_a), 4)


def generate_random_field(min_t: float = -1.0, max_t: float = 1.0) -> float:
    """生成随机磁场值。

    Args:
        min_t: 最小磁场(T)
        max_t: 最大磁场(T)

    Returns:
        float: 随机磁场值
    """
    return round(random.uniform(min_t, max_t), 6)


def generate_random_temperature(min_k: float = 100.0, max_k: float = 500.0) -> float:
    """生成随机温度值。

    Args:
        min_k: 最小温度(K)
        max_k: 最大温度(K)

    Returns:
        float: 随机温度值
    """
    return round(random.uniform(min_k, max_k), 2)


def generate_random_voltage(min_v: float = 0.0, max_v: float = 150.0) -> float:
    """生成随机电压值。

    Args:
        min_v: 最小电压(V)
        max_v: 最大电压(V)

    Returns:
        float: 随机电压值
    """
    return round(random.uniform(min_v, max_v), 3)


def generate_random_displacement(min_um: float = 0.0, max_um: float = 100.0) -> float:
    """生成随机位移值。

    Args:
        min_um: 最小位移(μm)
        max_um: 最大位移(μm)

    Returns:
        float: 随机位移值
    """
    return round(random.uniform(min_um, max_um), 4)


def generate_random_current_pa(min_pa: float = -1e-6, max_pa: float = 1e-6) -> float:
    """生成随机微电流值。

    Args:
        min_pa: 最小电流(pA)
        max_pa: 最大电流(pA)

    Returns:
        float: 随机微电流值
    """
    return round(random.uniform(min_pa, max_pa), 9)


# ==================== 字典工厂类（不依赖factory_boy） ====================


class UserDictFactory:
    """用户数据字典工厂。"""

    @staticmethod
    def create(
        username: str | None = None,
        password_hash: str | None = None,
        role: str = "operator",
        email: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """创建用户数据字典。

        Args:
            username: 用户名
            password_hash: 密码哈希
            role: 角色
            email: 邮箱
            **kwargs: 额外字段

        Returns:
            Dict: 用户数据字典
        """
        timestamp = int(time.time() * 1000)
        return {
            "username": username or f"test_user_{timestamp}",
            "password_hash": password_hash or f"hash_{timestamp}",
            "role": role,
            "email": email or f"user_{timestamp}@test.com",
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            **kwargs,
        }

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[dict[str, Any]]:
        """批量创建用户数据。

        Args:
            count: 数量
            **kwargs: 额外字段

        Returns:
            List[Dict]: 用户数据列表
        """
        return [UserDictFactory.create(**kwargs) for _ in range(count)]


class ExperimentDictFactory:
    """实验数据字典工厂。"""

    @staticmethod
    def create(
        exp_name: str | None = None,
        exp_type: str = "hysteresis",
        description: str = "",
        user_id: int = 1,
        status: str = "running",
        **kwargs,
    ) -> dict[str, Any]:
        """创建实验数据字典。

        Args:
            exp_name: 实验名称
            exp_type: 实验类型
            description: 描述
            user_id: 用户ID
            status: 状态
            **kwargs: 额外字段

        Returns:
            Dict: 实验数据字典
        """
        timestamp = int(time.time() * 1000)
        return {
            "exp_name": exp_name or f"实验_{timestamp}",
            "exp_type": exp_type,
            "description": description,
            "user_id": user_id,
            "status": status,
            "start_time": datetime.now(),
            "end_time": None,
            **kwargs,
        }

    @staticmethod
    def create_batch(count: int, **kwargs) -> list[dict[str, Any]]:
        """批量创建实验数据。

        Args:
            count: 数量
            **kwargs: 额外字段

        Returns:
            List[Dict]: 实验数据列表
        """
        return [ExperimentDictFactory.create(**kwargs) for _ in range(count)]


class DataRecordDictFactory:
    """数据记录字典工厂。"""

    @staticmethod
    def create(
        experiment_id: int = 1,
        position_steps: int | None = None,
        position_mm: float | None = None,
        field_value: float | None = None,
        current_value: float | None = None,
        temperature: float | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """创建数据记录字典。

        Args:
            experiment_id: 实验ID
            position_steps: 位置(步)
            position_mm: 位置(mm)
            field_value: 磁场值
            current_value: 电流值
            temperature: 温度
            **kwargs: 额外字段

        Returns:
            Dict: 数据记录字典
        """
        timestamp = time.time()
        return {
            "experiment_id": experiment_id,
            "position_steps": position_steps or random.randint(0, 160000),
            "position_mm": position_mm or generate_random_position(),
            "field_value": field_value or generate_random_field(),
            "current_value": current_value or generate_random_current(),
            "temperature": temperature or generate_random_temperature(),
            "timestamp": datetime.fromtimestamp(timestamp),
            **kwargs,
        }

    @staticmethod
    def create_batch(count: int, experiment_id: int = 1, **kwargs) -> list[dict[str, Any]]:
        """批量创建数据记录。

        Args:
            count: 数量
            experiment_id: 实验ID
            **kwargs: 额外字段

        Returns:
            List[Dict]: 数据记录列表
        """
        return [
            DataRecordDictFactory.create(experiment_id=experiment_id, **kwargs)
            for _ in range(count)
        ]


class DeviceStatusDictFactory:
    """设备状态字典工厂。"""

    @staticmethod
    def create_motor_status(
        device_id: str = "test_motor",
        status: str = "ready",
        position_mm: float | None = None,
        velocity_mm_s: float | None = None,
        alarm_code: int = 0,
        limit_positive: float = 100.0,
        limit_negative: float = -100.0,
        **kwargs,
    ) -> dict[str, Any]:
        """创建电机状态字典。

        Args:
            device_id: 设备ID
            status: 状态
            position_mm: 位置(mm)
            velocity_mm_s: 速度(mm/s)
            alarm_code: 报警代码
            limit_positive: 正向限位
            limit_negative: 负向限位
            **kwargs: 额外字段

        Returns:
            Dict: 电机状态字典
        """
        return {
            "device_id": device_id,
            "status": status,
            "position_steps": int((position_mm or 0.0) * 1600),
            "position_mm": position_mm or 0.0,
            "velocity_mm_s": velocity_mm_s or 0.0,
            "alarm_code": alarm_code,
            "alarm_text": "无报警" if alarm_code == 0 else f"报警代码: {alarm_code}",
            "status_word": {
                "fault": alarm_code != 0,
                "enabled": True,
                "running": False,
                "cmd_complete": True,
                "path_complete": True,
                "home_complete": True,
                "raw_value": 0x72,
            },
            "limit_positive": limit_positive,
            "limit_negative": limit_negative,
            "connected": True,
            "simulation": True,
            **kwargs,
        }

    @staticmethod
    def create_electromagnet_status(
        device_id: str = "test_electromagnet",
        status: str = "ready",
        current_value: float | None = None,
        field_value: float | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """创建电磁铁状态字典。

        Args:
            device_id: 设备ID
            status: 状态
            current_value: 电流值
            field_value: 磁场值
            **kwargs: 额外字段

        Returns:
            Dict: 电磁铁状态字典
        """
        return {
            "device_id": device_id,
            "electromagnet_status": status,
            "current_value": current_value or 0.0,
            "field_value": field_value or 0.0,
            "scan_progress": 0.0,
            "max_current_limit": 10.0,
            "connected": True,
            "simulation": True,
            **kwargs,
        }

    @staticmethod
    def create_temperature_status(
        device_id: str = "test_temp_controller",
        status: str = "ready",
        current_temperature: float | None = None,
        setpoint: float | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """创建温控状态字典。

        Args:
            device_id: 设备ID
            status: 状态
            current_temperature: 当前温度
            setpoint: 设定点
            **kwargs: 额外字段

        Returns:
            Dict: 温控状态字典
        """
        return {
            "device_id": device_id,
            "status": status,
            "current_temperature": current_temperature or 300.0,
            "current_output": 0.0,
            "setpoint": setpoint or 300.0,
            "mode": "PID",
            "pid_running": False,
            "connected": True,
            "simulation": True,
            "program": {"running": False, "progress": 0.0},
            "protection": {"triggered": False, "type": None},
            **kwargs,
        }

    @staticmethod
    def create_piezo_status(
        device_id: str = "test_piezo",
        status: str = "ready",
        current_voltage: float | None = None,
        current_displacement: float | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """创建压电陶瓷状态字典。

        Args:
            device_id: 设备ID
            status: 状态
            current_voltage: 当前电压
            current_displacement: 当前位移
            **kwargs: 额外字段

        Returns:
            Dict: 压电陶瓷状态字典
        """
        return {
            "device_id": device_id,
            "status": status,
            "current_voltage_v": current_voltage or 0.0,
            "current_displacement_um": current_displacement or 0.0,
            "target_displacement_um": 0.0,
            "control_mode": "voltage",
            "calibration_valid": True,
            "connected": True,
            "simulation": True,
            **kwargs,
        }

    @staticmethod
    def create_ammeter_status(
        device_id: str = "test_ammeter",
        status: str = "ready",
        sample_rate: float = 100.0,
        num_channels: int = 4,
        **kwargs,
    ) -> dict[str, Any]:
        """创建微电流计状态字典。

        Args:
            device_id: 设备ID
            status: 状态
            sample_rate: 采样率
            num_channels: 通道数
            **kwargs: 额外字段

        Returns:
            Dict: 微电流计状态字典
        """
        return {
            "device_id": device_id,
            "status": status,
            "sample_rate": sample_rate,
            "num_channels": num_channels,
            "acquiring": False,
            "buffer_size": 1000,
            "connected": True,
            "simulation": True,
            **kwargs,
        }


# ==================== 传感器数据生成器 ====================


class SensorDataGenerator:
    """传感器数据生成器。"""

    @staticmethod
    def generate_hysteresis_curve(
        num_points: int = 200,
        ms: float = 1.0,
        hc: float = 200.0,
        noise_level: float = 0.02,
    ) -> tuple[np.ndarray, np.ndarray]:
        """生成磁滞回线数据。

        Args:
            num_points: 数据点数
            ms: 饱和磁矩
            hc: 矫顽力
            noise_level: 噪声水平

        Returns:
            Tuple[np.ndarray, np.ndarray]: 磁场和磁矩数组
        """
        h_field = np.linspace(-1000, 1000, num_points)
        h_field = np.concatenate([h_field, h_field[::-1]])

        moment = ms * np.tanh(h_field / hc)
        noise = np.random.normal(0, noise_level, len(h_field))
        moment += noise

        return h_field, moment

    @staticmethod
    def generate_sinewave(
        num_points: int = 100,
        frequency: float = 1.0,
        amplitude: float = 1.0,
        noise_level: float = 0.1,
    ) -> tuple[np.ndarray, np.ndarray]:
        """生成正弦波数据。

        Args:
            num_points: 数据点数
            frequency: 频率
            amplitude: 幅值
            noise_level: 噪声水平

        Returns:
            Tuple[np.ndarray, np.ndarray]: x坐标和信号数组
        """
        x = np.linspace(0, 10, num_points)
        signal_clean = amplitude * np.sin(2 * np.pi * frequency * x)
        noise = np.random.normal(0, noise_level, len(x))
        signal_noisy = signal_clean + noise

        return x, signal_noisy

    @staticmethod
    def generate_temperature_ramp(
        num_points: int = 100,
        start_temp: float = 300.0,
        end_temp: float = 400.0,
        noise_level: float = 0.5,
    ) -> tuple[np.ndarray, np.ndarray]:
        """生成温度斜坡数据。

        Args:
            num_points: 数据点数
            start_temp: 起始温度
            end_temp: 结束温度
            noise_level: 噪声水平

        Returns:
            Tuple[np.ndarray, np.ndarray]: 时间和温度数组
        """
        time_points = np.linspace(0, 100, num_points)
        temperature = np.linspace(start_temp, end_temp, num_points)
        noise = np.random.normal(0, noise_level, len(time_points))
        temperature += noise

        return time_points, temperature

    @staticmethod
    def generate_current_pulse(
        num_points: int = 100,
        baseline: float = 0.0,
        pulse_height: float = 1e-9,
        pulse_width: int = 10,
        noise_level: float = 1e-12,
    ) -> tuple[np.ndarray, np.ndarray]:
        """生成电流脉冲数据。

        Args:
            num_points: 数据点数
            baseline: 基线电流
            pulse_height: 脉冲高度
            pulse_width: 脉冲宽度
            noise_level: 噪声水平

        Returns:
            Tuple[np.ndarray, np.ndarray]: 时间和电流数组
        """
        time_points = np.arange(num_points)
        current = np.full(num_points, baseline)

        # 添加脉冲
        pulse_start = num_points // 3
        pulse_end = pulse_start + pulse_width
        current[pulse_start:pulse_end] += pulse_height

        # 添加噪声
        noise = np.random.normal(0, noise_level, num_points)
        current += noise

        return time_points, current


# ==================== 导出工厂类 ====================

__all__ = [
    # 数据生成工具函数
    "generate_random_position",
    "generate_random_velocity",
    "generate_random_current",
    "generate_random_field",
    "generate_random_temperature",
    "generate_random_voltage",
    "generate_random_displacement",
    "generate_random_current_pa",
    # 字典工厂类
    "UserDictFactory",
    "ExperimentDictFactory",
    "DataRecordDictFactory",
    "DeviceStatusDictFactory",
    # 传感器数据生成器
    "SensorDataGenerator",
    # factory_boy可用性标志
    "FACTORY_BOY_AVAILABLE",
]
