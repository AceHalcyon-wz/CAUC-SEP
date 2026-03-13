"""
电磁铁控制数据模型

文件名: electromagnet.py
路径: backend/schemas/
功能: 定义电磁铁控制相关的请求/响应模型，包含电流设置、扫描、校准等
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic, enum

设备参数：
- 最大电流: 10A（基础限制，实际由设备配置决定）
- 最大磁场: 2T
- 扫描速率范围: 0.01-1.0 A/s

扫描模式：
- forward: 正向扫描（电流从低到高）
- reverse: 反向扫描（电流从高到低）
- triangular: 三角波扫描（往返扫描）
"""

from enum import Enum

from pydantic import BaseModel, Field


class ScanMode(str, Enum):
    """
    扫描模式枚举。

    定义电磁铁电流扫描的三种模式。

    Attributes:
        FORWARD: 正向扫描，电流从低到高
        REVERSE: 反向扫描，电流从高到低
        TRIANGULAR: 三角波扫描，往返扫描
    """

    FORWARD = "forward"
    REVERSE = "reverse"
    TRIANGULAR = "triangular"


# 设备参数常量
ELECTROMAGNET_MAX_CURRENT = 10.0
ELECTROMAGNET_MAX_FIELD = 2.0
ELECTROMAGNET_MIN_SCAN_RATE = 0.01
ELECTROMAGNET_MAX_SCAN_RATE = 1.0


class ElectromagnetSetCurrentRequest(BaseModel):
    """
    电磁铁电流设置请求。

    用于设置电磁铁的目标电流值。

    Attributes:
        current: 目标电流值(A)，基础范围: 0-10A，实际限制由设备配置决定

    Validation Rules:
        - current: 基础范围0-10A，实际最大电流限制由设备配置(max_current_limit)决定
        - API层会动态验证电流是否超过设备配置的限制

    Note:
        电流范围验证在API层动态执行，实际最大电流限制由设备配置决定。
        Pydantic仅进行基础范围校验（0-10A）。

    Example:
        >>> request = ElectromagnetSetCurrentRequest(current=5.0)
        >>> # 设置电流为5A
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

    用于建立电流-磁场映射关系，支持多点线性校准。

    Attributes:
        current: 电流值(A)，范围: 0-10A
        field: 磁场值(T)，范围: 0-2T

    Validation Rules:
        - current: 必须在0-10A范围内
        - field: 必须在0-2T范围内

    Example:
        >>> point = CalibrationPoint(current=5.0, field=1.0)
        >>> # 5A电流对应1T磁场
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

    Attributes:
        mode: 扫描模式，可选 'forward', 'reverse', 'triangular'
        start_current: 起始电流(A)，基础范围: 0-10A
        end_current: 目标电流(A)，基础范围: 0-10A
        scan_rate: 扫描速率(A/s)，范围: 0.01-1.0，默认0.1
        cycles: 扫描周期数(仅三角波模式有效)，最小值: 1，默认1
        step_interval_ms: 步进间隔(毫秒)，可选，用于精细控制扫描步进

    Validation Rules:
        - 电流范围在API层动态验证，实际限制由设备配置决定
        - cycles仅在triangular模式下有效
        - step_interval_ms不指定时自动计算

    Example:
        >>> request = ElectromagnetScanRequest(
        ...     mode=ScanMode.TRIANGULAR,
        ...     start_current=0.0,
        ...     end_current=5.0,
        ...     scan_rate=0.1,
        ...     cycles=3
        ... )
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

    用于前端在启动扫描前验证参数有效性，避免无效参数导致的错误。

    Attributes:
        mode: 扫描模式
        start_current: 起始电流(A)
        end_current: 目标电流(A)
        scan_rate: 扫描速率(A/s)，默认0.1
        cycles: 扫描周期数，默认1

    Note:
        此请求仅用于参数验证，不会执行实际扫描。
    """

    mode: ScanMode = Field(..., description="扫描模式")
    start_current: float = Field(..., description="起始电流(A)")
    end_current: float = Field(..., description="目标电流(A)")
    scan_rate: float = Field(0.1, description="扫描速率(A/s)")
    cycles: int = Field(1, description="扫描周期数")


class ElectromagnetScanValidateResponse(BaseModel):
    """
    电磁铁扫描参数验证响应。

    返回参数验证结果，包括错误、警告和预估时间。

    Attributes:
        valid: 参数是否有效
        errors: 错误信息列表，阻止扫描执行的问题
        warnings: 警告信息列表，不影响执行但需要注意的问题
        estimated_duration_s: 预估持续时间(秒)，仅当参数有效时返回

    Example:
        >>> if response.valid:
        ...     print(f"扫描预计耗时: {response.estimated_duration_s}秒")
        ... else:
        ...     print(f"参数错误: {response.errors}")
    """

    valid: bool = Field(..., description="参数是否有效")
    errors: list[str] = Field(default_factory=list, description="错误信息列表")
    warnings: list[str] = Field(default_factory=list, description="警告信息列表")
    estimated_duration_s: float | None = Field(None, description="预估持续时间(秒)")


class ElectromagnetCalibrateRequest(BaseModel):
    """
    电磁铁校准请求。

    用于提交校准点数据，建立电流-磁场映射关系。

    Attributes:
        calibration_points: 校准点列表，至少需要2个点

    Validation Rules:
        - 校准点数量至少为2个
        - 建议使用均匀分布的校准点
        - 校准点应覆盖实际使用范围

    Example:
        >>> request = ElectromagnetCalibrateRequest(
        ...     calibration_points=[
        ...         CalibrationPoint(current=0.0, field=0.0),
        ...         CalibrationPoint(current=5.0, field=1.0),
        ...         CalibrationPoint(current=10.0, field=2.0),
        ...     ]
        ... )
    """

    calibration_points: list[CalibrationPoint] = Field(
        ...,
        description="校准点列表，至少需要2个点",
        min_length=2,
    )


class ElectromagnetStatusResponse(BaseModel):
    """
    电磁铁状态响应。

    返回电磁铁设备的完整状态信息。

    Attributes:
        device_id: 设备唯一标识符
        status: 设备状态，如 'connected', 'disconnected', 'error'
        electromagnet_status: 电磁铁状态，如 'idle', 'scanning', 'settling'
        current_value: 当前电流值(A)
        field_value: 当前磁场值(T)，根据校准系数计算
        max_current_limit: 最大电流限制(A)，来自设备配置
        scan_progress: 扫描进度(0-1)，非扫描状态时为0
        calibration_points_count: 校准点数量
        calibration_coefficient: 校准系数(T/A)
        connected: 是否已连接
        simulation: 是否仿真模式

    Example:
        >>> response = await api.get_electromagnet_status()
        >>> print(f"当前电流: {response.current_value}A")
        >>> print(f"当前磁场: {response.field_value}T")
    """

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
