"""
Pydantic 数据模型定义

功能：
- 定义所有 API 请求/响应的数据模型
- 提供完整的类型提示和验证
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ScanMode(str, Enum):
    """扫描模式枚举"""

    FORWARD = "forward"
    REVERSE = "reverse"
    TRIANGULAR = "triangular"

# ==================== 通用响应模型 ====================


class SuccessResponse(BaseModel):
    """通用成功响应"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")


class ErrorCode(str, Enum):
    """API错误代码枚举"""

    # 设备状态错误 (1xxx)
    DEVICE_NOT_INITIALIZED = "E1001"
    DEVICE_NOT_CONNECTED = "E1002"
    DEVICE_IN_EMERGENCY_STOP = "E1003"
    DEVICE_BUSY = "E1004"
    DEVICE_ERROR = "E1005"

    # 参数验证错误 (2xxx)
    INVALID_PARAMETER = "E2001"
    PARAM_OUT_OF_RANGE = "E2002"
    MISSING_PARAMETER = "E2003"

    # 限位错误 (3xxx)
    SOFT_LIMIT_EXCEEDED = "E3001"
    HARDWARE_LIMIT_TRIGGERED = "E3002"

    # 操作错误 (4xxx)
    OPERATION_FAILED = "E4001"
    MOTION_FAILED = "E4002"
    CONNECTION_FAILED = "E4003"

    # 系统错误 (5xxx)
    INTERNAL_ERROR = "E5001"
    COMMUNICATION_ERROR = "E5002"
    TIMEOUT_ERROR = "E5003"


class ErrorResponse(BaseModel):
    """
    通用错误响应模型。
    
    提供统一的错误响应格式，包含错误码、详细信息和时间戳。
    """
    
    error_code: str = Field(..., description="错误代码，如 'INVALID_PARAM', 'DEVICE_ERROR'")
    detail: str = Field(..., description="错误详情描述")
    timestamp: str | None = Field(None, description="错误发生时间戳")
    suggestions: list[str] | None = Field(None, description="修复建议列表")


class ValidationErrorDetail(BaseModel):
    """
    参数验证错误详情。
    """
    
    field: str = Field(..., description="错误字段名")
    value: Any = Field(..., description="错误值")
    constraint: str = Field(..., description="约束条件")
    message: str = Field(..., description="错误消息")


class ValidationErrorResponse(BaseModel):
    """
    参数验证错误响应。
    """
    
    error_code: str = Field("VALIDATION_ERROR", description="错误代码")
    detail: str = Field(..., description="错误概述")
    errors: list[ValidationErrorDetail] = Field(..., description="详细错误列表")


# ==================== 电机控制模型 ====================


class MoveRequest(BaseModel):
    """运动请求"""

    position_mm: float = Field(..., description="目标位置(mm)", ge=-100, le=100)
    velocity_mm_s: float = Field(10.0, description="速度(mm/s)", ge=1, le=50)
    accel_mm_s2: float = Field(1000.0, description="加速度(mm/s²)", ge=1, le=10000)
    decel_mm_s2: float = Field(1000.0, description="减速度(mm/s²)", ge=1, le=10000)


class MoveResponse(BaseModel):
    """运动响应"""

    success: bool
    message: str
    target_position_steps: int
    target_position_mm: float


class JogRequest(BaseModel):
    """JOG请求"""

    direction: int = Field(..., description="方向 (1=正, -1=负)", ge=-1, le=1)
    velocity_mm_s: float = Field(5.0, description="速度(mm/s)", ge=1, le=20)


class LimitConfigRequest(BaseModel):
    """限位配置请求"""

    positive_mm: float = Field(50.0, description="正向限位(mm)")
    negative_mm: float = Field(-50.0, description="负向限位(mm)")


class PRPathConfigRequest(BaseModel):
    """PR路径配置请求"""

    path_number: int = Field(..., description="路径编号 (0-15)", ge=0, le=15)
    mode: int = Field(1, description="运动模式")
    position_mm: float = Field(..., description="目标位置(mm)")
    velocity_mm_s: int = Field(1000, description="速度(步/秒)")
    accel_time: int = Field(100, description="加速时间(ms)", ge=0)
    decel_time: int = Field(100, description="减速时间(ms)", ge=0)
    dwell_time: int = Field(0, description="停留时间(ms)", ge=0)
    special_param: int = Field(0, description="特殊参数")


class PRPathTriggerRequest(BaseModel):
    """PR路径触发请求"""

    path_number: int = Field(..., description="路径编号 (0-15)", ge=0, le=15)


class HomeRequest(BaseModel):
    """回零请求"""

    mode: str = Field("origin", description="回零模式")


class StatusWordResponse(BaseModel):
    """状态字响应"""

    fault: bool = Field(..., description="故障状态")
    enabled: bool = Field(..., description="使能状态")
    running: bool = Field(..., description="运行状态")
    cmd_complete: bool = Field(..., description="命令完成")
    path_complete: bool = Field(..., description="路径完成")
    home_complete: bool = Field(..., description="回零完成")
    raw_value: int = Field(..., description="原始状态字值")


class AlarmCodeResponse(BaseModel):
    """报警代码响应"""

    alarm_code: int = Field(..., description="报警代码")
    alarm_text: str = Field(..., description="报警描述")


class MotorStatusResponse(BaseModel):
    """电机状态响应"""

    device_id: str
    status: str
    position_steps: int
    position_mm: float
    alarm_code: int
    alarm_text: str
    status_word: dict[str, Any]
    limit_positive: float
    limit_negative: float
    connected: bool


# ==================== 设备管理模型 ====================


class DeviceInfo(BaseModel):
    """设备信息"""

    device_id: str
    device_type: str
    device_name: str | None
    connection_params: str | None
    status: str
    created_at: str


# ==================== 实验管理模型 ====================


class ExperimentRequest(BaseModel):
    """实验请求"""

    name: str = Field(..., description="实验名称", min_length=1, max_length=100)
    description: str = Field("", description="实验描述")


class ExperimentInfo(BaseModel):
    """实验信息"""

    id: int
    name: str
    description: str
    status: str
    created_at: str
    started_at: str | None
    completed_at: str | None


# ==================== 数据分析模型 ====================


class SmoothRequest(BaseModel):
    """信号平滑请求"""

    y_data: list[float] = Field(..., description="待平滑的信号数据")
    method: str = Field("savgol", description="平滑方法: savgol 或 butter")
    window_length: int = Field(11, description="窗口长度，必须为奇数", ge=3)
    polyorder: int = Field(2, description="多项式阶数")
    butter_lowcut: float = Field(0.1, description="巴特沃斯低通截止频率(归一化 0-1)")
    butter_order: int = Field(3, description="巴特沃斯滤波器阶数")


class SmoothResponse(BaseModel):
    """信号平滑响应"""

    success: bool
    message: str
    smoothed_data: list[float]


class FitRequest(BaseModel):
    """曲线拟合请求"""

    x_data: list[float] = Field(..., description="X轴数据")
    y_data: list[float] = Field(..., description="Y轴数据")
    model_type: str = Field("langevin", description="拟合模型类型: langevin 或 linear")


class FitResponse(BaseModel):
    """曲线拟合响应"""

    success: bool
    message: str
    fit_params: dict[str, float]
    chi2: float
    redchi: float
    fitted_y: list[float]


class HysteresisRequest(BaseModel):
    """磁滞回线分析请求"""

    x_field: list[float] = Field(..., description="磁场强度数据")
    y_moment: list[float] = Field(..., description="磁矩数据")
    subtract_background: bool = Field(True, description="是否扣除背景")
    saturation_threshold: float | None = Field(None, description="饱和场阈值")


class HysteresisResponse(BaseModel):
    """磁滞回线分析响应"""

    success: bool
    message: str
    Hc: float
    Mr: float
    Ms: float
    background_params: dict[str, float]
    x_corrected: list[float]
    y_corrected: list[float]


# ==================== 电磁铁控制模型 ====================

# 电磁铁技术规范常量（与驱动层保持一致）
ELECTROMAGNET_MAX_CURRENT = 10.0  # 最大电流（A）
ELECTROMAGNET_MAX_FIELD = 2.0     # 最大磁场（T）
ELECTROMAGNET_MIN_SCAN_RATE = 0.01  # 最小扫描速率（A/s）
ELECTROMAGNET_MAX_SCAN_RATE = 1.0   # 最大扫描速率（A/s）


class ElectromagnetSetCurrentRequest(BaseModel):
    """
    电磁铁电流设置请求。
    
    注意：电流范围验证在API层动态执行，
    实际最大电流限制由设备配置决定（max_current_limit）。
    Pydantic仅进行基础范围校验（0-10A）。
    """
    
    current: float = Field(
        ...,
        description="目标电流值(A)，基础范围: 0-10A，实际限制由设备配置决定",
        ge=0.0,
        le=ELECTROMAGNET_MAX_CURRENT,
    )


class CalibrationPoint(BaseModel):
    """
    校准点数据模型。
    
    用于建立电流-磁场映射关系。
    """
    
    current: float = Field(
        ...,
        description="电流值(A)",
        ge=0.0,
        le=ELECTROMAGNET_MAX_CURRENT,
    )
    field: float = Field(
        ...,
        description="磁场值(T)",
        ge=0.0,
        le=ELECTROMAGNET_MAX_FIELD,
    )


class ElectromagnetScanRequest(BaseModel):
    """
    电磁铁扫描请求模型。
    
    支持三种扫描模式：
    - forward: 正向扫描（电流从低到高）
    - reverse: 反向扫描（电流从高到低）
    - triangular: 三角波扫描（往返扫描）
    
    注意：电流范围验证在API层动态执行，
    实际最大电流限制由设备配置决定。
    """
    
    mode: ScanMode = Field(
        ...,
        description="扫描模式: forward(正向), reverse(反向), triangular(三角波)",
    )
    start_current: float = Field(
        ...,
        description="起始电流(A)，基础范围: 0-10A",
        ge=0.0,
        le=ELECTROMAGNET_MAX_CURRENT,
    )
    end_current: float = Field(
        ...,
        description="目标电流(A)，基础范围: 0-10A",
        ge=0.0,
        le=ELECTROMAGNET_MAX_CURRENT,
    )
    scan_rate: float = Field(
        0.1,
        description=f"扫描速率(A/s)，范围: {ELECTROMAGNET_MIN_SCAN_RATE}-{ELECTROMAGNET_MAX_SCAN_RATE}",
        ge=ELECTROMAGNET_MIN_SCAN_RATE,
        le=ELECTROMAGNET_MAX_SCAN_RATE,
    )
    cycles: int = Field(
        1,
        description="扫描周期数(仅三角波模式有效)，最小值: 1",
        ge=1,
    )
    step_interval_ms: float | None = Field(
        None,
        description="步进间隔(毫秒)，可选参数，用于精细控制扫描步进。默认自动计算",
        ge=1.0,
        le=1000.0,
    )


class ElectromagnetScanValidateRequest(BaseModel):
    """
    电磁铁扫描参数预验证请求。
    
    用于前端在启动扫描前验证参数有效性。
    """
    
    mode: ScanMode = Field(..., description="扫描模式")
    start_current: float = Field(..., description="起始电流(A)")
    end_current: float = Field(..., description="目标电流(A)")
    scan_rate: float = Field(0.1, description="扫描速率(A/s)")
    cycles: int = Field(1, description="扫描周期数")


class ElectromagnetScanValidateResponse(BaseModel):
    """
    电磁铁扫描参数验证响应。
    """
    
    valid: bool = Field(..., description="参数是否有效")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")
    estimated_duration_s: float | None = Field(None, description="预估持续时间(秒)")


class ElectromagnetCalibrateRequest(BaseModel):
    """电磁铁校准请求"""

    calibration_points: list[CalibrationPoint] = Field(
        ...,
        description="校准点列表，至少需要2个点",
        min_length=2,
    )


class ElectromagnetStatusResponse(BaseModel):
    """电磁铁状态响应"""

    device_id: str = Field(..., description="设备ID")
    status: str = Field(..., description="设备状态")
    electromagnet_status: str = Field(..., description="电磁铁状态")
    current_value: float = Field(..., description="当前电流值(A)")
    field_value: float = Field(..., description="当前磁场值(T)")
    max_current_limit: float = Field(..., description="最大电流限制(A)")
    scan_progress: float = Field(..., description="扫描进度(0-1)")
    calibration_points_count: int = Field(..., description="校准点数量")
    calibration_coefficient: float = Field(..., description="校准系数(T/A)")
    connected: bool = Field(..., description="是否已连接")
    simulation: bool = Field(..., description="是否仿真模式")


# ==================== 压电陶瓷控制模型 ====================


class VoltageSetRequest(BaseModel):
    """电压设置请求"""

    voltage_v: float = Field(
        ...,
        description="目标电压(V)",
        ge=0.0,
        le=150.0,
    )


class DisplacementSetRequest(BaseModel):
    """位移设置请求"""

    displacement_um: float = Field(
        ...,
        description="目标位移(μm)",
        ge=0.0,
        le=100.0,
    )


class CalibrationPointRequest(BaseModel):
    """校准点请求"""

    voltage_v: float = Field(..., description="电压值(V)", ge=0.0, le=150.0)
    displacement_um: float = Field(..., description="位移值(μm)", ge=0.0, le=100.0)


class CalibrationPerformRequest(BaseModel):
    """执行校准请求"""

    calibration_type: str = Field(
        "polynomial",
        description="校准类型: linear, polynomial, piecewise",
    )


class ControlModeRequest(BaseModel):
    """控制模式请求"""

    mode: str = Field(
        ...,
        description="控制模式: open_loop 或 closed_loop",
    )


class VoltageResponse(BaseModel):
    """电压响应"""

    success: bool
    message: str
    current_voltage_v: float
    current_displacement_um: float


class DisplacementResponse(BaseModel):
    """位移响应"""

    success: bool
    message: str
    current_displacement_um: float
    current_voltage_v: float


class CalibrationPointResponse(BaseModel):
    """校准点响应"""

    success: bool
    message: str
    point_count: int


class CalibrationDataResponse(BaseModel):
    """校准数据响应"""

    valid: bool
    type: str
    points: list[dict[str, float]]
    coefficients: list[float]
    point_count: int


class PiezoStatusResponse(BaseModel):
    """压电陶瓷状态响应"""

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


# ==================== 微电流采集模型 ====================


class AmmeterStartRequest(BaseModel):
    """微电流采集启动请求"""

    sample_rate: float | None = Field(
        None,
        description="采样率(Hz)，范围1-1000",
        ge=1.0,
        le=1000.0,
    )


class AmmeterChannelConfigRequest(BaseModel):
    """微电流采集通道配置请求"""

    channel: int = Field(..., description="通道号(0-3)", ge=0, le=3)
    enabled: bool | None = Field(None, description="是否启用通道")
    current_range: str | None = Field(
        None,
        description="电流量程: 1nA, 10nA, 100nA, 1uA, 10uA, 100uA, 1mA",
    )
    filter_type: str | None = Field(
        None,
        description="滤波类型: none, lowpass, moving_average, median",
    )
    filter_cutoff: float | None = Field(
        None,
        description="低通滤波截止频率(Hz)",
        ge=0.1,
        le=500.0,
    )
    filter_window: int | None = Field(
        None,
        description="移动平均/中值滤波窗口大小",
        ge=1,
        le=100,
    )
    offset: float | None = Field(None, description="电流偏移校准值(pA)")


class AmmeterChannelData(BaseModel):
    """微电流采集通道数据"""

    channel: int = Field(..., description="通道号")
    current_pa: float = Field(..., description="电流值(pA)")
    timestamp: float = Field(..., description="时间戳(秒)")
    snr_db: float = Field(..., description="信噪比(dB)")
    raw_current_pa: float = Field(..., description="原始电流值(pA)")
    noise_rms_pa: float = Field(..., description="噪声RMS值(pA)")
    signal_rms_pa: float = Field(..., description="信号RMS值(pA)")


class AmmeterDataResponse(BaseModel):
    """微电流采集数据响应"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    is_acquiring: bool = Field(..., description="是否正在采集")
    data: list[AmmeterChannelData] = Field(..., description="通道数据列表")


class AmmeterChannelStatus(BaseModel):
    """微电流采集通道状态"""

    enabled: bool = Field(..., description="是否启用")
    range: str = Field(..., description="电流量程")
    filter: str = Field(..., description="滤波类型")
    offset: float = Field(..., description="偏移校准值")


class AmmeterStatusResponse(BaseModel):
    """微电流采集设备状态响应"""

    device_id: str = Field(..., description="设备ID")
    status: str = Field(..., description="设备状态")
    simulation: bool = Field(..., description="是否仿真模式")
    sample_rate: float = Field(..., description="采样率(Hz)")
    is_acquiring: bool = Field(..., description="是否正在采集")
    buffer_usage: list[int] = Field(..., description="各通道缓冲区使用情况")
    channel_configs: list[AmmeterChannelStatus] = Field(..., description="通道配置列表")


# ==================== 温度控制模型 ====================

# 温度范围常量（与技术设计文档一致）
TEMP_MIN_K = 77.0   # 液氮温度
TEMP_MAX_K = 400.0  # 最高温度


class TemperatureSetpointRequest(BaseModel):
    """温度设定点请求。
    
    温度范围：77K-400K（液氮釜温控系统）
    """

    temperature: float = Field(
        ...,
        description="目标温度(K)，范围: 77K-400K",
        ge=TEMP_MIN_K,
        le=TEMP_MAX_K,
    )


class TemperatureProgramSegmentRequest(BaseModel):
    """温度程序段请求。
    
    参数范围：
    - target_temperature: 77K-400K
    - ramp_rate: -10到10 K/min（正值升温，负值降温，0表示立即跳转）
    - hold_time: >= 0 秒
    """

    target_temperature: float = Field(
        ...,
        description="目标温度(K)，范围: 77K-400K",
        ge=TEMP_MIN_K,
        le=TEMP_MAX_K,
    )
    ramp_rate: float = Field(
        1.0,
        description="升温/降温速率(K/min)，范围: -10到10，正值升温，负值降温，0表示立即跳转",
        ge=-10.0,
        le=10.0,
    )
    hold_time: float = Field(
        0.0,
        description="保持时间(秒)，>= 0",
        ge=0.0,
    )


class TemperatureProgramRequest(BaseModel):
    """温度程序请求"""

    segments: list[TemperatureProgramSegmentRequest] = Field(
        ...,
        description="温度程序段列表",
        min_length=1,
    )


class PIDParametersRequest(BaseModel):
    """PID参数请求。
    
    参数范围：
    - Kp: 0.1-100（比例系数）
    - Ki: 0.001-10（积分系数）
    - Kd: 0.001-10（微分系数）
    - setpoint: 77K-400K（设定温度）
    """

    kp: float = Field(
        ...,
        description="比例系数(Kp)，范围: 0.1-100",
        ge=0.1,
        le=100.0,
    )
    ki: float = Field(
        ...,
        description="积分系数(Ki)，范围: 0.001-10",
        ge=0.001,
        le=10.0,
    )
    kd: float = Field(
        ...,
        description="微分系数(Kd)，范围: 0.001-10",
        ge=0.001,
        le=10.0,
    )
    setpoint: float = Field(
        ...,
        description="设定温度(K)，范围: 77K-400K",
        ge=TEMP_MIN_K,
        le=TEMP_MAX_K,
    )


class ProtectionConfigRequest(BaseModel):
    """温度保护配置请求。
    
    保护阈值范围：
    - 高温保护: >450K 触发
    - 低温保护: <70K 触发
    - 温度变化率: >20 K/min 触发
    """

    max_temperature: float = Field(
        450.0,
        description="高温保护阈值(K)，超过此温度触发保护",
        ge=TEMP_MAX_K,
        le=500.0,
    )
    min_temperature: float = Field(
        70.0,
        description="低温保护阈值(K)，低于此温度触发保护",
        ge=50.0,
        le=TEMP_MIN_K,
    )
    max_deviation: float = Field(
        20.0,
        description="最大温度变化率限制(K/min)，超过此速率触发保护",
        ge=1.0,
        le=50.0,
    )


class TemperatureStatusResponse(BaseModel):
    """温度控制器状态响应。
    
    温度单位：开尔文(K)
    """

    device_id: str = Field(..., description="设备ID")
    status: str = Field(..., description="设备状态")
    current_temperature: float = Field(..., description="当前温度(K)，范围: 77K-400K")
    target_temperature: float = Field(..., description="目标温度(K)，范围: 77K-400K")
    heater_power: float = Field(..., description="加热功率百分比(%)")
    pid_enabled: bool = Field(..., description="PID控制是否启用")
    program_running: bool = Field(..., description="温度程序是否运行中")
    program_segment: int = Field(..., description="当前程序段索引")
    protection_active: bool = Field(..., description="保护是否激活")
    protection_type: str | None = Field(None, description="保护类型")
    connected: bool = Field(..., description="是否已连接")
    simulation: bool = Field(..., description="是否仿真模式")


class TemperatureHistoryRequest(BaseModel):
    """温度历史记录请求"""

    duration_seconds: float = Field(
        60.0,
        description="历史记录时长(秒)，默认60秒",
        ge=1.0,
        le=3600.0,
    )


class TemperatureHistoryRecord(BaseModel):
    """温度历史记录项"""

    timestamp: float = Field(..., description="时间戳")
    temperature: float = Field(..., description="温度值(K)")
    target: float = Field(..., description="目标温度(K)")
    power: float = Field(..., description="加热功率(%)")


class TemperatureHistoryResponse(BaseModel):
    """温度历史记录响应"""

    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    timestamps: list[float] = Field(..., description="时间戳列表")
    temperatures: list[float] = Field(..., description="温度值列表(K)")
    setpoints: list[float] = Field(..., description="设定温度列表(K)")


# ==================== 多模型拟合与报告模型 ====================


class MultiFitRequest(BaseModel):
    """多模型拟合请求。

    用于同时使用多个模型拟合磁滞回线数据，并比较拟合结果。
    """

    h_data: list[float] = Field(
        ...,
        description="磁场强度数据(H)，单位: A/m 或 Oe",
        min_length=5,
    )
    b_data: list[float] = Field(
        ...,
        description="磁感应强度数据(B)，单位: T 或 G",
        min_length=5,
    )
    models: list[str] = Field(
        default=["hyperbolic", "arctangent", "braunbeck"],
        description="要拟合的模型列表，可选: hyperbolic, arctangent, braunbeck, langevin",
    )


class ModelFitResult(BaseModel):
    """单个模型拟合结果。

    包含模型参数和拟合优度指标。
    """

    model_name: str = Field(..., description="模型名称")
    params: dict[str, float] = Field(..., description="拟合参数字典")
    r_squared: float = Field(..., description="R²决定系数，范围0-1，越接近1越好")
    rmse: float = Field(..., description="均方根误差，越小越好")
    aic: float = Field(..., description="Akaike信息准则，越小越好")
    bic: float = Field(..., description="贝叶斯信息准则，越小越好")


class MultiFitResponse(BaseModel):
    """多模型拟合响应。

    包含所有模型的拟合结果、最佳模型推荐和比较指标。
    """

    results: list[ModelFitResult] = Field(..., description="各模型拟合结果列表")
    best_model: str = Field(..., description="最佳模型名称（按AIC准则）")
    comparison_metrics: dict[str, Any] = Field(
        ...,
        description="模型比较指标，包含排名、AIC差值、权重等",
    )
    recommendations: list[str] = Field(..., description="分析建议列表")


class ReportGenerateRequest(BaseModel):
    """分析报告生成请求。

    用于生成完整的磁滞回线分析报告。
    """

    h_data: list[float] = Field(
        ...,
        description="磁场强度数据(H)",
        min_length=5,
    )
    b_data: list[float] = Field(
        ...,
        description="磁感应强度数据(B)",
        min_length=5,
    )
    experiment_id: str | None = Field(
        None,
        description="实验ID，可选，默认自动生成时间戳ID",
    )
    include_raw_data: bool = Field(
        False,
        description="是否在报告中包含原始数据",
    )


class AnalysisReportResponse(BaseModel):
    """分析报告响应。

    包含完整的磁滞回线分析结果和拟合报告。
    """

    experiment_id: str = Field(..., description="实验ID")
    timestamp: str = Field(..., description="报告生成时间戳")
    hysteresis_params: dict[str, Any] = Field(
        ...,
        description="磁滞回线参数，包含Hc、Mr、Ms、squareness等",
    )
    fit_results: list[ModelFitResult] = Field(..., description="各模型拟合结果")
    best_model: str = Field(..., description="最佳模型名称")
    quality_metrics: dict[str, float] = Field(..., description="数据质量指标")
    recommendations: list[str] = Field(..., description="分析建议列表")


class ReportExportRequest(BaseModel):
    """报告导出请求。

    用于导出分析报告到指定格式。
    """

    h_data: list[float] = Field(..., description="磁场强度数据(H)")
    b_data: list[float] = Field(..., description="磁感应强度数据(B)")
    experiment_id: str | None = Field(None, description="实验ID")
    include_raw_data: bool = Field(False, description="是否包含原始数据")
    format: str = Field(
        "json",
        description="导出格式: json, csv, pdf",
        pattern="^(json|csv|pdf)$",
    )


# ==================== 历史数据查询模型 ====================


class HistoryQueryRequest(BaseModel):
    """历史数据查询请求。
    
    支持按实验ID、设备、时间范围等条件查询历史数据。
    """
    
    experiment_ids: list[int] | None = Field(
        None,
        description="实验ID列表，可选，不指定则查询所有实验",
    )
    devices: list[str] | None = Field(
        None,
        description="设备列表，可选",
    )
    start_time: str | None = Field(
        None,
        description="开始时间(ISO格式)，可选",
    )
    end_time: str | None = Field(
        None,
        description="结束时间(ISO格式)，可选",
    )
    data_types: list[str] | None = Field(
        None,
        description="数据类型列表(field, current, temperature等)，可选",
    )
    limit: int = Field(
        1000,
        description="返回数据点数量限制",
        ge=1,
        le=10000,
    )
    offset: int = Field(
        0,
        description="数据偏移量，用于分页",
        ge=0,
    )


class HistoryDataPoint(BaseModel):
    """历史数据点。"""
    
    timestamp: str = Field(..., description="时间戳")
    experiment_id: int = Field(..., description="实验ID")
    device: str | None = Field(None, description="设备名称")
    position_mm: float | None = Field(None, description="位置(mm)")
    field_value: float | None = Field(None, description="磁场值")
    current_value: float | None = Field(None, description="电流值")
    temperature: float | None = Field(None, description="温度值")
    value: float = Field(..., description="数值(用于图表展示)")
    unit: str = Field("", description="单位")


class HistoryQueryResponse(BaseModel):
    """历史数据查询响应。"""
    
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    total: int = Field(..., description="总数据点数")
    data: list[HistoryDataPoint] = Field(..., description="数据点列表")
    statistics: dict[str, Any] = Field(
        default_factory=dict,
        description="统计信息(平均值、最大值、最小值等)",
    )


# ==================== 数据对比模型 ====================


class CompareDataset(BaseModel):
    """对比数据集。"""
    
    experiment_id: int = Field(..., description="实验ID")
    name: str = Field(..., description="数据集名称")
    data_type: str = Field(
        "field",
        description="数据类型: field, current, temperature等",
    )


class CompareRequest(BaseModel):
    """数据对比请求。
    
    用于对比多个实验或数据集的数据。
    """
    
    datasets: list[CompareDataset] = Field(
        ...,
        description="要对比的数据集列表，至少2个",
        min_length=2,
        max_length=4,
    )
    align_mode: str = Field(
        "time",
        description="对齐模式: time(时间对齐), position(位置对齐), index(索引对齐)",
    )
    normalize: bool = Field(
        False,
        description="是否归一化数据",
    )


class CompareDatasetResult(BaseModel):
    """对比数据集结果。"""
    
    experiment_id: int = Field(..., description="实验ID")
    name: str = Field(..., description="数据集名称")
    data: list[dict[str, Any]] = Field(..., description="数据点列表")
    statistics: dict[str, float] = Field(..., description="统计信息")


class CompareResponse(BaseModel):
    """数据对比响应。"""
    
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(..., description="操作消息")
    datasets: list[CompareDatasetResult] = Field(..., description="对比数据集结果")
    difference_metrics: dict[str, Any] = Field(
        default_factory=dict,
        description="差异指标(平均值差异、最大值差异等)",
    )
