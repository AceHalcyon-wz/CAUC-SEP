"""
电机控制数据模型

文件名: motor.py
路径: backend/schemas/
功能: 定义电机控制相关的请求/响应模型，包含运动控制、限位配置、PR路径等
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic, typing

运动参数范围：
- 位置: -100 ~ 100 mm
- 速度: 1 ~ 50 mm/s
- 加速度: 1 ~ 10000 mm/s²
- 减速度: 1 ~ 10000 mm/s²

PR路径：
- 支持16条预定义路径（编号0-15）
- 支持连续运动和停留时间配置
"""

from typing import Any

from pydantic import BaseModel, Field


class MoveRequest(BaseModel):
    """
    运动请求。

    用于控制电机移动到指定位置。

    Attributes:
        position_mm: 目标位置(mm)，范围: -100 ~ 100
        velocity_mm_s: 速度(mm/s)，范围: 1 ~ 50，默认10.0
        accel_mm_s2: 加速度(mm/s²)，范围: 1 ~ 10000，默认1000.0
        decel_mm_s2: 减速度(mm/s²)，范围: 1 ~ 10000，默认1000.0

    Validation Rules:
        - position_mm: 受软限位约束，实际范围由限位配置决定
        - 速度和加速度需在设备支持范围内

    Example:
        >>> request = MoveRequest(
        ...     position_mm=25.0,
        ...     velocity_mm_s=20.0,
        ...     accel_mm_s2=500.0,
        ...     decel_mm_s2=500.0
        ... )
    """

    position_mm: float = Field(..., description="目标位置(mm)", ge=-100, le=100)
    velocity_mm_s: float = Field(10.0, description="速度(mm/s)", ge=1, le=50)
    accel_mm_s2: float = Field(1000.0, description="加速度(mm/s²)", ge=1, le=10000)
    decel_mm_s2: float = Field(1000.0, description="减速度(mm/s²)", ge=1, le=10000)


class MoveResponse(BaseModel):
    """
    运动响应。

    返回运动命令的执行结果。

    Attributes:
        success: 运动命令是否成功发送
        message: 操作消息
        target_position_steps: 目标位置(步数)，电机控制器的内部单位
        target_position_mm: 目标位置(mm)，用户友好的单位

    Note:
        success=True仅表示命令成功发送，不代表运动完成。
        需要通过状态查询确认运动是否完成。
    """

    success: bool
    message: str
    target_position_steps: int
    target_position_mm: float


class JogRequest(BaseModel):
    """
    JOG点动请求。

    用于手动控制电机连续移动，松开后停止。

    Attributes:
        direction: 移动方向，1=正向，-1=负向
        velocity_mm_s: 速度(mm/s)，范围: 1 ~ 20，默认5.0

    Validation Rules:
        - direction: 只能是1或-1
        - JOG运动受软限位约束

    Warning:
        JOG模式会持续运动直到触发限位或用户停止，
        使用时需注意安全。
    """

    direction: int = Field(..., description="方向 (1=正, -1=负)", ge=-1, le=1)
    velocity_mm_s: float = Field(5.0, description="速度(mm/s)", ge=1, le=20)


class LimitConfigRequest(BaseModel):
    """
    限位配置请求。

    用于设置电机的软限位范围。

    Attributes:
        positive_mm: 正向限位(mm)，默认50.0
        negative_mm: 负向限位(mm)，默认-50.0

    Validation Rules:
        - positive_mm必须大于negative_mm
        - 限位范围不能超过硬件行程

    Note:
        软限位是软件层面的保护，超出范围的运动请求会被拒绝。
        硬件限位是物理开关，触发后会触发急停。
    """

    positive_mm: float = Field(50.0, description="正向限位(mm)")
    negative_mm: float = Field(-50.0, description="负向限位(mm)")


class PRPathConfigRequest(BaseModel):
    """
    PR路径配置请求。

    用于配置预定义运动路径（PR模式）。

    Attributes:
        path_number: 路径编号，范围: 0-15
        mode: 运动模式，默认1
        position_mm: 目标位置(mm)
        velocity_mm_s: 速度(步/秒)，默认1000
        accel_time: 加速时间(ms)，默认100
        decel_time: 减速时间(ms)，默认100
        dwell_time: 停留时间(ms)，默认0
        special_param: 特殊参数，默认0

    Validation Rules:
        - path_number: 必须在0-15范围内
        - 加速/减速时间不能为负

    Note:
        PR路径配置后可通过PRPathTriggerRequest触发执行，
        支持多路径连续执行。
    """

    path_number: int = Field(..., description="路径编号 (0-15)", ge=0, le=15)
    mode: int = Field(1, description="运动模式")
    position_mm: float = Field(..., description="目标位置(mm)")
    velocity_mm_s: int = Field(1000, description="速度(步/秒)")
    accel_time: int = Field(100, description="加速时间(ms)", ge=0)
    decel_time: int = Field(100, description="减速时间(ms)", ge=0)
    dwell_time: int = Field(0, description="停留时间(ms)", ge=0)
    special_param: int = Field(0, description="特殊参数")


class PRPathTriggerRequest(BaseModel):
    """
    PR路径触发请求。

    用于触发执行已配置的PR路径。

    Attributes:
        path_number: 路径编号，范围: 0-15

    Validation Rules:
        - path_number: 必须在0-15范围内
        - 路径必须已配置

    Example:
        >>> request = PRPathTriggerRequest(path_number=0)
        >>> # 触发执行路径0
    """

    path_number: int = Field(..., description="路径编号 (0-15)", ge=0, le=15)


class HomeRequest(BaseModel):
    """
    回零请求。

    用于执行回零操作，建立位置参考点。

    Attributes:
        mode: 回零模式，默认 'origin'

    Note:
        回零操作会移动电机到参考点位置，
        执行前请确保运动范围内无障碍物。
    """

    mode: str = Field("origin", description="回零模式")


class StatusWordResponse(BaseModel):
    """
    状态字响应。

    解析电机控制器的状态字，提供人类可读的状态信息。

    Attributes:
        fault: 是否存在故障
        enabled: 电机是否使能
        running: 电机是否正在运行
        cmd_complete: 命令是否完成
        path_complete: PR路径是否完成
        home_complete: 回零是否完成
        raw_value: 原始状态字值，用于调试

    Example:
        >>> if response.fault:
        ...     print("电机故障，请检查报警代码")
        ... elif response.running:
        ...     print("电机正在运动中...")
    """

    fault: bool = Field(..., description="故障状态")
    enabled: bool = Field(..., description="使能状态")
    running: bool = Field(..., description="运行状态")
    cmd_complete: bool = Field(..., description="命令完成")
    path_complete: bool = Field(..., description="路径完成")
    home_complete: bool = Field(..., description="回零完成")
    raw_value: int = Field(..., description="原始状态字值")


class AlarmCodeResponse(BaseModel):
    """
    报警代码响应。

    返回电机控制器的报警信息。

    Attributes:
        alarm_code: 报警代码，数值型
        alarm_text: 报警描述，人类可读的错误信息

    Note:
        常见报警代码：
        - 0: 无报警
        - 其他代码请参考电机控制器手册
    """

    alarm_code: int = Field(..., description="报警代码")
    alarm_text: str = Field(..., description="报警描述")


class MotorStatusResponse(BaseModel):
    """
    电机状态响应。

    返回电机的完整状态信息。

    Attributes:
        device_id: 设备唯一标识符
        status: 设备状态，如 'connected', 'disconnected', 'error'
        position_steps: 当前位置(步数)
        position_mm: 当前位置(mm)
        alarm_code: 报警代码
        alarm_text: 报警描述
        status_word: 状态字字典，包含解析后的状态位
        limit_positive: 正向软限位(mm)
        limit_negative: 负向软限位(mm)
        connected: 是否已连接

    Example:
        >>> response = await api.get_motor_status()
        >>> print(f"当前位置: {response.position_mm}mm")
        >>> if response.alarm_code != 0:
        ...     print(f"报警: {response.alarm_text}")
    """

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


class SerialModeRequest(BaseModel):
    """
    串口模式请求。

    用于切换串口通信模式（RS485/RS232）。

    Attributes:
        mode: 串口模式，'rs485' 或 'rs232'
        port: 串口号（如 'COM3'）

    Note:
        RS232模式使用默认设置：
        - 波特率：9600
        - 从站地址：1
        - 数据位：8位
        - 校验位：无
        - 停止位：1位
    """

    mode: str = Field(..., description="串口模式 (rs485 或 rs232)")
    port: str = Field(..., description="串口号 (如 COM3)")


class CommunicationConfigRequest(BaseModel):
    """
    通信参数配置请求。

    用于在线修改Modbus通信参数。

    Attributes:
        baudrate: 波特率 (2400, 4800, 9600, 19200, 38400, 57600, 115200)
        slave_id: 从站地址 (0-127)
        data_type: 数据类型 (0-5)
            - 0: 8位数据，偶校验，2个停止位
            - 1: 8位数据，奇校验，2个停止位
            - 2: 8位数据，偶校验，1个停止位
            - 3: 8位数据，奇校验，1个停止位
            - 4: 8位数据，无校验，1个停止位（默认）
            - 5: 8位数据，无校验，2个停止位

    Warning:
        波特率只能在当前波特率为9600时在线修改。
        修改后需要保存参数到EEPROM并重新上电才能生效。
    """

    baudrate: int | None = Field(None, description="波特率")
    slave_id: int | None = Field(None, description="从站地址 (0-127)", ge=0, le=127)
    data_type: int | None = Field(None, description="数据类型 (0-5)", ge=0, le=5)


class CommunicationConfigResponse(BaseModel):
    """
    通信参数配置响应。

    返回通信参数配置结果。

    Attributes:
        success: 是否成功
        baudrate: 设置的波特率
        slave_id: 设置的从站地址
        data_type: 设置的数据类型
        warnings: 警告信息列表
        errors: 错误信息列表
    """

    success: bool
    baudrate: int | None = None
    slave_id: int | None = None
    data_type: int | None = None
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


class CommunicationConfigReadResponse(BaseModel):
    """
    通信参数读取响应。

    返回当前通信参数配置。

    Attributes:
        baudrate: 当前波特率
        slave_id: 当前从站地址
        data_type: 当前数据类型
        serial_mode: 当前串口模式
    """

    baudrate: int
    slave_id: int
    data_type: int
    serial_mode: str


class DriverSoftLimitRequest(BaseModel):
    """
    驱动器软件限位配置请求。

    用于设置驱动器内部的软件限位。

    Attributes:
        positive_limit_mm: 正向限位(mm)
        negative_limit_mm: 负向限位(mm)
        positive_limit_steps: 正向限位(步数)，优先于positive_limit_mm
        negative_limit_steps: 负向限位(步数)，优先于negative_limit_mm

    Note:
        软件限位在回零时无效。
        修改后需要保存参数到EEPROM才能永久生效。
    """

    positive_limit_mm: float | None = Field(None, description="正向限位(mm)")
    negative_limit_mm: float | None = Field(None, description="负向限位(mm)")
    positive_limit_steps: int | None = Field(None, description="正向限位(步数)")
    negative_limit_steps: int | None = Field(None, description="负向限位(步数)")


class DriverSoftLimitResponse(BaseModel):
    """
    驱动器软件限位响应。

    返回驱动器软件限位配置结果。

    Attributes:
        success: 是否成功
        positive_limit: 正向限位(步数)
        negative_limit: 负向限位(步数)
        errors: 错误信息列表
    """

    success: bool
    positive_limit: int | None = None
    negative_limit: int | None = None
    errors: list[str] = Field(default_factory=list)


class DriverSoftLimitReadResponse(BaseModel):
    """
    驱动器软件限位读取响应。

    返回当前驱动器软件限位配置。

    Attributes:
        positive_limit: 正向限位(步数)
        negative_limit: 负向限位(步数)
        positive_limit_mm: 正向限位(mm)
        negative_limit_mm: 负向限位(mm)
    """

    positive_limit: int
    negative_limit: int
    positive_limit_mm: float
    negative_limit_mm: float


class SupportedBaudratesResponse(BaseModel):
    """
    支持的波特率列表响应。

    Attributes:
        baudrates: 支持的波特率列表
    """

    baudrates: list[int]


class SupportedDataTypesResponse(BaseModel):
    """
    支持的数据类型列表响应。

    Attributes:
        data_types: 数据类型代码到描述的映射
    """

    data_types: dict[int, str]
