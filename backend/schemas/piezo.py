"""
压电陶瓷控制数据模型

文件名: piezo.py
路径: backend/schemas/
功能: 定义压电陶瓷控制相关的请求/响应模型，包含电压设置、位移控制、校准等
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic, typing

设备参数：
- 最大电压: 150V
- 最大位移: 100μm
- 控制模式: 开环(open_loop)、闭环(closed_loop)

校准类型：
- linear: 线性校准
- polynomial: 多项式校准
- piecewise: 分段校准
"""

from typing import Any

from pydantic import BaseModel, Field


class VoltageSetRequest(BaseModel):
    """
    电压设置请求。

    用于直接设置压电陶瓷的驱动电压（开环控制）。

    Attributes:
        voltage_v: 目标电压(V)，范围: 0 ~ 150V

    Validation Rules:
        - voltage_v: 必须在0-150V范围内

    Note:
        开环模式下电压与位移的关系由压电陶瓷特性决定，
        建议使用校准后的位移控制模式。

    Example:
        >>> request = VoltageSetRequest(voltage_v=75.0)
        >>> # 设置电压为75V
    """

    voltage_v: float = Field(
        ...,
        description="目标电压(V)",
        ge=0.0,
        le=150.0,
    )


class DisplacementSetRequest(BaseModel):
    """
    位移设置请求。

    用于设置压电陶瓷的目标位移（闭环控制）。

    Attributes:
        displacement_um: 目标位移(μm)，范围: 0 ~ 100μm

    Validation Rules:
        - displacement_um: 必须在0-100μm范围内
        - 需要有效的校准数据才能使用位移控制

    Note:
        位移控制需要先完成校准，系统会根据校准数据
        计算对应的驱动电压。

    Example:
        >>> request = DisplacementSetRequest(displacement_um=50.0)
        >>> # 设置位移为50μm
    """

    displacement_um: float = Field(
        ...,
        description="目标位移(μm)",
        ge=0.0,
        le=100.0,
    )


class CalibrationPointRequest(BaseModel):
    """
    校准点请求。

    用于添加电压-位移校准点。

    Attributes:
        voltage_v: 电压值(V)，范围: 0 ~ 150V
        displacement_um: 位移值(μm)，范围: 0 ~ 100μm

    Validation Rules:
        - voltage_v: 必须在0-150V范围内
        - displacement_um: 必须在0-100μm范围内

    Note:
        建议在校准范围内均匀选取多个校准点，
        至少需要2个点才能进行校准。

    Example:
        >>> point = CalibrationPointRequest(voltage_v=75.0, displacement_um=50.0)
    """

    voltage_v: float = Field(..., description="电压值(V)", ge=0.0, le=150.0)
    displacement_um: float = Field(..., description="位移值(μm)", ge=0.0, le=100.0)


class CalibrationPerformRequest(BaseModel):
    """
    执行校准请求。

    用于根据已添加的校准点执行校准计算。

    Attributes:
        calibration_type: 校准类型，可选值:
            - linear: 线性校准，适用于线性响应区域
            - polynomial: 多项式校准，适用于非线性响应
            - piecewise: 分段校准，适用于复杂非线性响应
            默认为 'polynomial'

    Validation Rules:
        - 需要至少2个校准点
        - 校准点应覆盖实际使用范围

    Example:
        >>> request = CalibrationPerformRequest(calibration_type="polynomial")
    """

    calibration_type: str = Field(
        "polynomial",
        description="校准类型: linear, polynomial, piecewise",
    )


class ControlModeRequest(BaseModel):
    """
    控制模式请求。

    用于切换压电陶瓷的控制模式。

    Attributes:
        mode: 控制模式，可选值:
            - open_loop: 开环模式，直接控制电压
            - closed_loop: 闭环模式，通过校准数据控制位移

    Validation Rules:
        - 切换到闭环模式需要有效的校准数据

    Note:
        开环模式响应快但精度低，闭环模式精度高但需要校准。

    Example:
        >>> request = ControlModeRequest(mode="closed_loop")
    """

    mode: str = Field(
        ...,
        description="控制模式: open_loop 或 closed_loop",
    )


class VoltageResponse(BaseModel):
    """
    电压响应。

    返回电压设置操作的结果。

    Attributes:
        success: 操作是否成功
        message: 操作消息
        current_voltage_v: 当前电压(V)
        current_displacement_um: 当前位移(μm)，根据校准数据计算
    """

    success: bool
    message: str
    current_voltage_v: float
    current_displacement_um: float


class DisplacementResponse(BaseModel):
    """
    位移响应。

    返回位移设置操作的结果。

    Attributes:
        success: 操作是否成功
        message: 操作消息
        current_displacement_um: 当前位移(μm)
        current_voltage_v: 当前电压(V)，根据校准数据计算
    """

    success: bool
    message: str
    current_displacement_um: float
    current_voltage_v: float


class CalibrationPointResponse(BaseModel):
    """
    校准点响应。

    返回校准点添加操作的结果。

    Attributes:
        success: 操作是否成功
        message: 操作消息
        point_count: 当前校准点总数
    """

    success: bool
    message: str
    point_count: int


class CalibrationDataResponse(BaseModel):
    """
    校准数据响应。

    返回当前校准数据的详细信息。

    Attributes:
        valid: 校准数据是否有效
        type: 校准类型，如 'linear', 'polynomial', 'piecewise'
        points: 校准点列表，每个点包含 'voltage_v' 和 'displacement_um'
        coefficients: 校准系数列表，用于电压-位移转换
        point_count: 校准点数量

    Example:
        >>> response = await api.get_calibration_data()
        >>> if response.valid:
        ...     print(f"校准类型: {response.type}")
        ...     print(f"校准点数: {response.point_count}")
    """

    valid: bool
    type: str
    points: list[dict[str, float]]
    coefficients: list[float]
    point_count: int


class PiezoStatusResponse(BaseModel):
    """
    压电陶瓷状态响应。

    返回压电陶瓷控制器的完整状态信息。

    Attributes:
        device_id: 设备唯一标识符
        status: 设备状态，如 'connected', 'disconnected', 'error'
        control_mode: 控制模式，'open_loop' 或 'closed_loop'
        current_voltage_v: 当前电压(V)
        current_displacement_um: 当前位移(μm)
        target_displacement_um: 目标位移(μm)，闭环模式下有效
        calibration_valid: 校准数据是否有效
        calibration_points: 校准点数量
        max_voltage_v: 最大电压限制(V)
        max_displacement_um: 最大位移限制(μm)

    Example:
        >>> response = await api.get_piezo_status()
        >>> print(f"当前电压: {response.current_voltage_v}V")
        >>> print(f"当前位移: {response.current_displacement_um}μm")
        >>> print(f"控制模式: {response.control_mode}")
    """

    device_id: str
    status: str
    control_mode: str
    current_voltage_v: float
    current_displacement_um: float
    target_displacement_um: float
    calibration_valid: bool
    calibration_points: int
    max_voltage_v: float
    max_displacement_um: float
