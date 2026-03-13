"""
数据分析数据模型

文件名: analysis.py
路径: backend/schemas/
功能: 定义数据分析相关的请求/响应模型，包含信号平滑、曲线拟合、磁滞回线分析等
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic, typing

分析功能：
- 信号平滑：Savitzky-Golay滤波、巴特沃斯滤波
- 曲线拟合：Langevin函数拟合、线性拟合
- 磁滞回线分析：矫顽力Hc、剩余磁化强度Mr、饱和磁化强度Ms计算
- 多模型拟合：双曲正切、反正切、Braunbeck、Langevin模型比较
- 历史数据查询与对比分析
"""

from typing import Any

from pydantic import BaseModel, Field


class SmoothRequest(BaseModel):
    """
    信号平滑请求。

    支持两种平滑方法：
    - savgol: Savitzky-Golay滤波，保留信号特征的同时平滑噪声
    - butter: 巴特沃斯低通滤波，去除高频噪声

    Attributes:
        y_data: 待平滑的信号数据
        method: 平滑方法，可选 'savgol' 或 'butter'，默认 'savgol'
        window_length: 窗口长度，必须为奇数且>=3，默认11
        polyorder: 多项式阶数(Savgol方法)，默认2
        butter_lowcut: 巴特沃斯低通截止频率(归一化0-1)，默认0.1
        butter_order: 巴特沃斯滤波器阶数，默认3

    Validation Rules:
        - window_length: 必须为奇数
        - polyorder: 必须小于window_length
    """

    y_data: list[float] = Field(..., description="待平滑的信号数据")
    method: str = Field("savgol", description="平滑方法: savgol 或 butter")
    window_length: int = Field(11, description="窗口长度，必须为奇数", ge=3)
    polyorder: int = Field(2, description="多项式阶数")
    butter_lowcut: float = Field(0.1, description="巴特沃斯低通截止频率(归一化 0-1)")
    butter_order: int = Field(3, description="巴特沃斯滤波器阶数")


class SmoothResponse(BaseModel):
    """
    信号平滑响应。

    Attributes:
        success: 操作是否成功
        message: 操作消息
        smoothed_data: 平滑后的数据
    """

    success: bool
    message: str
    smoothed_data: list[float]


class FitRequest(BaseModel):
    """
    曲线拟合请求。

    支持两种拟合模型：
    - langevin: Langevin函数拟合，适用于超顺磁材料
    - linear: 线性拟合，适用于线性响应区域

    Attributes:
        x_data: X轴数据（自变量）
        y_data: Y轴数据（因变量）
        model_type: 拟合模型类型，可选 'langevin' 或 'linear'，默认 'langevin'

    Validation Rules:
        - x_data和y_data长度必须相同
        - 数据点数量至少为3
    """

    x_data: list[float] = Field(..., description="X轴数据")
    y_data: list[float] = Field(..., description="Y轴数据")
    model_type: str = Field("langevin", description="拟合模型类型: langevin 或 linear")


class FitResponse(BaseModel):
    """
    曲线拟合响应。

    Attributes:
        success: 拟合是否成功
        message: 操作消息
        fit_params: 拟合参数字典，键为参数名，值为参数值
        chi2: 卡方值，衡量拟合优度
        redchi: 约化卡方值，考虑自由度的拟合优度
        fitted_y: 拟合后的Y值列表
    """

    success: bool
    message: str
    fit_params: dict[str, float]
    chi2: float
    redchi: float
    fitted_y: list[float]


class HysteresisRequest(BaseModel):
    """
    磁滞回线分析请求。

    用于分析磁性材料的磁滞回线特性，计算矫顽力、剩余磁化强度等参数。

    Attributes:
        x_field: 磁场强度数据(H)，单位A/m或Oe
        y_moment: 磁矩数据(M)，单位emu或A·m²
        subtract_background: 是否扣除背景（抗磁/顺磁贡献），默认True
        saturation_threshold: 饱和场阈值，用于确定饱和区域，可选

    Note:
        - 数据应包含完整的磁滞回线（正向和反向扫描）
        - 建议数据点均匀分布在磁场范围内
    """

    x_field: list[float] = Field(..., description="磁场强度数据")
    y_moment: list[float] = Field(..., description="磁矩数据")
    subtract_background: bool = Field(True, description="是否扣除背景")
    saturation_threshold: float | None = Field(None, description="饱和场阈值")


class HysteresisResponse(BaseModel):
    """
    磁滞回线分析响应。

    Attributes:
        success: 分析是否成功
        message: 操作消息
        Hc: 矫顽力(Coercivity)，磁场强度单位
        Mr: 剩余磁化强度(Remanent Magnetization)，磁矩单位
        Ms: 饱和磁化强度(Saturation Magnetization)，磁矩单位
        background_params: 背景拟合参数，包含斜率和截距
        x_corrected: 扣除背景后的磁场数据
        y_corrected: 扣除背景后的磁矩数据
    """

    success: bool
    message: str
    Hc: float
    Mr: float
    Ms: float
    background_params: dict[str, float]
    x_corrected: list[float]
    y_corrected: list[float]


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
