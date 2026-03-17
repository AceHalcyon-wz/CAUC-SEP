"""
测试数据生成工具模块

文件名: test_data.py
路径: backend/tests/helpers/
功能: 提供测试数据生成函数，替代硬编码测试数据
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: numpy

使用方法:
    from tests.helpers import create_test_user, generate_test_hysteresis_data

    def test_experiment():
        user = create_test_user(username="test_user")
        data = generate_test_hysteresis_data(num_points=100)
"""

import time
from datetime import datetime
from typing import Any

import numpy as np


def create_test_user(
    username: str | None = None,
    password_hash: str | None = None,
    role: str = "operator",
    email: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """创建测试用户数据。

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


def create_test_experiment(
    exp_name: str | None = None,
    exp_type: str = "hysteresis",
    description: str = "",
    user_id: int = 1,
    status: str = "running",
    **kwargs,
) -> dict[str, Any]:
    """创建测试实验数据。

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


def create_test_device_config(
    device_type: str = "motor",
    port: str = "COM3",
    slave_id: int = 1,
    **kwargs,
) -> dict[str, Any]:
    """创建测试设备配置。

    Args:
        device_type: 设备类型
        port: 端口
        slave_id: 从站ID
        **kwargs: 额外字段

    Returns:
        Dict: 设备配置字典
    """
    base_config = {
        "port": port,
        "slave_id": slave_id,
        "simulation": True,
    }

    if device_type == "motor":
        base_config.update({
            "steps_per_mm": 1600,
            "baudrate": 115200,
        })
    elif device_type == "temperature":
        base_config.update({
            "baudrate": 9600,
        })
    elif device_type == "piezo":
        base_config.update({
            "max_voltage": 150.0,
            "max_displacement": 100.0,
        })

    base_config.update(kwargs)
    return base_config


def generate_test_hysteresis_data(
    num_points: int = 200,
    ms: float = 1.0,
    hc: float = 200.0,
    noise_level: float = 0.02,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """生成测试磁滞回线数据。

    Args:
        num_points: 数据点数
        ms: 饱和磁矩
        hc: 矫顽力
        noise_level: 噪声水平
        seed: 随机种子

    Returns:
        Tuple[np.ndarray, np.ndarray]: 磁场和磁矩数组
    """
    if seed is not None:
        np.random.seed(seed)

    h_field = np.linspace(-1000, 1000, num_points)
    h_field = np.concatenate([h_field, h_field[::-1]])

    moment = ms * np.tanh(h_field / hc)
    noise = np.random.normal(0, noise_level, len(h_field))
    moment += noise

    return h_field, moment


def generate_test_temperature_ramp(
    num_points: int = 100,
    start_temp: float = 300.0,
    end_temp: float = 400.0,
    noise_level: float = 0.5,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """生成测试温度斜坡数据。

    Args:
        num_points: 数据点数
        start_temp: 起始温度(K)
        end_temp: 结束温度(K)
        noise_level: 噪声水平
        seed: 随机种子

    Returns:
        Tuple[np.ndarray, np.ndarray]: 时间和温度数组
    """
    if seed is not None:
        np.random.seed(seed)

    time_points = np.linspace(0, 100, num_points)
    temperature = np.linspace(start_temp, end_temp, num_points)
    noise = np.random.normal(0, noise_level, len(time_points))
    temperature += noise

    return time_points, temperature


def generate_test_sinewave(
    num_points: int = 100,
    frequency: float = 1.0,
    amplitude: float = 1.0,
    noise_level: float = 0.1,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """生成测试正弦波数据。

    Args:
        num_points: 数据点数
        frequency: 频率
        amplitude: 幅值
        noise_level: 噪声水平
        seed: 随机种子

    Returns:
        Tuple[np.ndarray, np.ndarray]: x坐标和信号数组
    """
    if seed is not None:
        np.random.seed(seed)

    x = np.linspace(0, 10, num_points)
    signal_clean = amplitude * np.sin(2 * np.pi * frequency * x)
    noise = np.random.normal(0, noise_level, len(x))
    signal_noisy = signal_clean + noise

    return x, signal_noisy


def generate_test_current_pulse(
    num_points: int = 100,
    baseline: float = 0.0,
    pulse_height: float = 1e-9,
    pulse_width: int = 10,
    noise_level: float = 1e-12,
    seed: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """生成测试电流脉冲数据。

    Args:
        num_points: 数据点数
        baseline: 基线电流
        pulse_height: 脉冲高度
        pulse_width: 脉冲宽度
        noise_level: 噪声水平
        seed: 随机种子

    Returns:
        Tuple[np.ndarray, np.ndarray]: 时间和电流数组
    """
    if seed is not None:
        np.random.seed(seed)

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


def generate_test_position_trajectory(
    num_points: int = 100,
    start_pos: float = 0.0,
    end_pos: float = 50.0,
    max_velocity: float = 10.0,
    acceleration: float = 5.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """生成测试位置轨迹数据（梯形速度曲线）。

    Args:
        num_points: 数据点数
        start_pos: 起始位置
        end_pos: 目标位置
        max_velocity: 最大速度
        acceleration: 加速度

    Returns:
        Tuple[np.ndarray, np.ndarray, np.ndarray]: 时间、位置、速度数组
    """
    time_points = np.linspace(0, 10, num_points)
    position = np.zeros(num_points)
    velocity = np.zeros(num_points)

    # 简化的梯形速度曲线
    distance = abs(end_pos - start_pos)
    direction = 1 if end_pos > start_pos else -1

    # 计算加速、匀速、减速时间
    t_accel = max_velocity / acceleration
    t_decel = t_accel
    d_accel = 0.5 * acceleration * t_accel**2
    d_decel = d_accel
    d_const = distance - 2 * d_accel

    if d_const < 0:
        # 三角形速度曲线
        t_accel = np.sqrt(distance / acceleration)
        t_decel = t_accel
        t_const = 0
    else:
        t_const = d_const / max_velocity

    total_time = t_accel + t_const + t_decel

    for i, t in enumerate(time_points):
        normalized_t = t / time_points[-1] * total_time
        if normalized_t < t_accel:
            # 加速阶段
            velocity[i] = acceleration * normalized_t * direction
            position[i] = start_pos + 0.5 * acceleration * normalized_t**2 * direction
        elif normalized_t < t_accel + t_const:
            # 匀速阶段
            velocity[i] = max_velocity * direction
            position[i] = start_pos + (d_accel + max_velocity * (normalized_t - t_accel)) * direction
        else:
            # 减速阶段
            t_decel_elapsed = normalized_t - t_accel - t_const
            velocity[i] = (max_velocity - acceleration * t_decel_elapsed) * direction
            position[i] = end_pos - 0.5 * acceleration * (t_decel - t_decel_elapsed)**2 * direction

    return time_points, position, velocity
