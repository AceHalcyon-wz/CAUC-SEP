"""
Mock对象工厂模块

文件名: mock_factories.py
路径: backend/tests/helpers/
功能: 提供统一的Mock对象创建工厂，减少测试代码重复
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: unittest.mock

使用方法:
    from tests.helpers import create_mock_motor_status

    def test_motor():
        mock_status = create_mock_motor_status(position_mm=10.0)
        mock_motor.read_status = AsyncMock(return_value=mock_status)
"""

from typing import Any
from unittest.mock import AsyncMock, MagicMock


def create_mock_motor_status(
    device_id: str = "test_motor",
    status: str = "ready",
    position_mm: float = 0.0,
    position_steps: int = 0,
    velocity_mm_s: float = 0.0,
    alarm_code: int = 0,
    alarm_text: str = "无报警",
    limit_positive: float = 100.0,
    limit_negative: float = -100.0,
    connected: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """创建电机状态Mock数据。

    Args:
        device_id: 设备ID
        status: 设备状态
        position_mm: 位置(mm)
        position_steps: 位置(步)
        velocity_mm_s: 速度(mm/s)
        alarm_code: 报警代码
        alarm_text: 报警文本
        limit_positive: 正向限位
        limit_negative: 负向限位
        connected: 是否连接
        **kwargs: 额外字段

    Returns:
        Dict: 电机状态字典
    """
    return {
        "device_id": device_id,
        "status": status,
        "position_steps": position_steps,
        "position_mm": position_mm,
        "velocity_mm_s": velocity_mm_s,
        "alarm_code": alarm_code,
        "alarm_text": alarm_text,
        "status_word": {
            "fault": alarm_code != 0,
            "enabled": True,
            "running": status == "running",
            "cmd_complete": True,
            "path_complete": True,
            "home_complete": True,
            "raw_value": 0x72,
        },
        "limit_positive": limit_positive,
        "limit_negative": limit_negative,
        "connected": connected,
        "simulation": True,
        **kwargs,
    }


def create_mock_piezo_status(
    device_id: str = "test_piezo",
    status: str = "ready",
    control_mode: str = "open_loop",
    current_voltage_v: float = 0.0,
    current_displacement_um: float = 0.0,
    target_displacement_um: float = 0.0,
    calibration_valid: bool = False,
    calibration_points: int = 0,
    max_voltage_v: float = 150.0,
    max_displacement_um: float = 100.0,
    connected: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """创建压电陶瓷状态Mock数据。

    Args:
        device_id: 设备ID
        status: 设备状态
        control_mode: 控制模式
        current_voltage_v: 当前电压(V)
        current_displacement_um: 当前位移(μm)
        target_displacement_um: 目标位移(μm)
        calibration_valid: 校准是否有效
        calibration_points: 校准点数
        max_voltage_v: 最大电压(V)
        max_displacement_um: 最大位移(μm)
        connected: 是否连接
        **kwargs: 额外字段

    Returns:
        Dict: 压电陶瓷状态字典
    """
    return {
        "device_id": device_id,
        "status": status,
        "control_mode": control_mode,
        "current_voltage_v": current_voltage_v,
        "current_displacement_um": current_displacement_um,
        "target_displacement_um": target_displacement_um,
        "calibration_valid": calibration_valid,
        "calibration_points": calibration_points,
        "max_voltage_v": max_voltage_v,
        "max_displacement_um": max_displacement_um,
        "connected": connected,
        "simulation": True,
        **kwargs,
    }


def create_mock_electromagnet_status(
    device_id: str = "test_electromagnet",
    status: str = "ready",
    current_value: float = 0.0,
    field_value: float = 0.0,
    scan_progress: float = 0.0,
    max_current_limit: float = 10.0,
    connected: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """创建电磁铁状态Mock数据。

    Args:
        device_id: 设备ID
        status: 设备状态
        current_value: 电流值(A)
        field_value: 磁场值(T)
        scan_progress: 扫描进度
        max_current_limit: 最大电流限制
        connected: 是否连接
        **kwargs: 额外字段

    Returns:
        Dict: 电磁铁状态字典
    """
    return {
        "device_id": device_id,
        "electromagnet_status": status,
        "current_value": current_value,
        "field_value": field_value,
        "scan_progress": scan_progress,
        "max_current_limit": max_current_limit,
        "connected": connected,
        "simulation": True,
        **kwargs,
    }


def create_mock_temperature_status(
    device_id: str = "test_temp_controller",
    status: str = "ready",
    current_temperature: float = 300.0,
    current_output: float = 0.0,
    setpoint: float = 300.0,
    mode: str = "PID",
    pid_running: bool = False,
    connected: bool = True,
    program_running: bool = False,
    program_progress: float = 0.0,
    protection_triggered: bool = False,
    protection_type: str | None = None,
    **kwargs,
) -> dict[str, Any]:
    """创建温控状态Mock数据。

    Args:
        device_id: 设备ID
        status: 设备状态
        current_temperature: 当前温度(K)
        current_output: 当前输出(%)
        setpoint: 设定点(K)
        mode: 控制模式
        pid_running: PID是否运行
        connected: 是否连接
        program_running: 程序是否运行
        program_progress: 程序进度
        protection_triggered: 保护是否触发
        protection_type: 保护类型
        **kwargs: 额外字段

    Returns:
        Dict: 温控状态字典
    """
    return {
        "device_id": device_id,
        "status": status,
        "current_temperature": current_temperature,
        "current_output": current_output,
        "setpoint": setpoint,
        "mode": mode,
        "pid_running": pid_running,
        "connected": connected,
        "simulation": True,
        "program": {
            "running": program_running,
            "progress": program_progress,
        },
        "protection": {
            "triggered": protection_triggered,
            "type": protection_type,
        },
        **kwargs,
    }


def create_mock_ammeter_status(
    device_id: str = "test_ammeter",
    status: str = "ready",
    sample_rate: float = 100.0,
    num_channels: int = 4,
    acquiring: bool = False,
    buffer_size: int = 1000,
    connected: bool = True,
    **kwargs,
) -> dict[str, Any]:
    """创建微电流计状态Mock数据。

    Args:
        device_id: 设备ID
        status: 设备状态
        sample_rate: 采样率
        num_channels: 通道数
        acquiring: 是否采集
        buffer_size: 缓冲区大小
        connected: 是否连接
        **kwargs: 额外字段

    Returns:
        Dict: 微电流计状态字典
    """
    return {
        "device_id": device_id,
        "status": status,
        "sample_rate": sample_rate,
        "num_channels": num_channels,
        "acquiring": acquiring,
        "buffer_size": buffer_size,
        "connected": connected,
        "simulation": True,
        **kwargs,
    }


def create_mock_device_response(
    success: bool = True,
    message: str = "操作成功",
    **kwargs,
) -> dict[str, Any]:
    """创建通用设备响应Mock数据。

    Args:
        success: 是否成功
        message: 消息
        **kwargs: 额外字段

    Returns:
        Dict: 设备响应字典
    """
    return {
        "success": success,
        "message": message,
        **kwargs,
    }


def create_mock_motor_controller(
    device_id: str = "test_motor",
    status: str = "ready",
) -> MagicMock:
    """创建Mock电机控制器实例。

    Args:
        device_id: 设备ID
        status: 设备状态

    Returns:
        MagicMock: Mock控制器实例
    """
    from core.abstract import DeviceStatus

    controller = MagicMock()
    controller.device_id = device_id
    controller.status = DeviceStatus.READY if status == "ready" else DeviceStatus.DISCONNECTED
    controller.last_error = None
    controller.simulation_mode = True

    # 异步方法Mock
    controller.connect = AsyncMock(return_value=True)
    controller.disconnect = AsyncMock(return_value=True)
    controller.move_abs = AsyncMock(return_value=True)
    controller.move_rel = AsyncMock(return_value=True)
    controller.jog = AsyncMock(return_value=True)
    controller.home = AsyncMock(return_value=True)
    controller.emergency_stop = AsyncMock(return_value=True)
    controller.reset_emergency = AsyncMock(return_value=True)
    controller.read_status = AsyncMock(return_value=create_mock_motor_status())
    controller.read_status_word = AsyncMock(return_value={
        "fault": False,
        "enabled": True,
        "running": False,
        "cmd_complete": True,
        "path_complete": True,
        "home_complete": True,
        "raw_value": 0x72,
    })
    controller.read_alarm_code = AsyncMock(return_value=0)

    return controller


def create_mock_piezo_controller(
    device_id: str = "test_piezo",
    status: str = "ready",
) -> MagicMock:
    """创建Mock压电陶瓷控制器实例。

    Args:
        device_id: 设备ID
        status: 设备状态

    Returns:
        MagicMock: Mock控制器实例
    """
    from core.abstract import DeviceStatus

    controller = MagicMock()
    controller.device_id = device_id
    controller.status = DeviceStatus.READY if status == "ready" else DeviceStatus.DISCONNECTED
    controller.last_error = None
    controller.simulation_mode = True

    # 异步方法Mock
    controller.connect = AsyncMock(return_value=True)
    controller.disconnect = AsyncMock(return_value=True)
    controller.set_voltage = AsyncMock(return_value=True)
    controller.set_displacement = AsyncMock(return_value=True)
    controller.get_voltage = AsyncMock(return_value=0.0)
    controller.get_displacement = AsyncMock(return_value=0.0)
    controller.add_calibration_point = AsyncMock(return_value=True)
    controller.perform_calibration = AsyncMock(return_value=True)
    controller.clear_calibration = AsyncMock(return_value=True)
    controller.set_control_mode = AsyncMock(return_value=True)
    controller.zero = AsyncMock(return_value=True)
    controller.max_extend = AsyncMock(return_value=True)
    controller.read_status = AsyncMock(return_value=create_mock_piezo_status())

    return controller
