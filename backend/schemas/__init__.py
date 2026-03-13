"""
Pydantic 数据模型模块

文件名: __init__.py
路径: backend/schemas/
功能: 定义所有 API 请求/响应的数据模型，提供完整的类型提示和验证，按功能模块组织
作者: Backend Engineer Agent
创建日期: 2026-03-14
依赖: pydantic

模块结构：
- common: 通用响应模型（成功/错误响应）
- motor: 电机控制模型（运动控制、限位配置、PR路径）
- device: 设备管理模型（设备信息）
- experiment: 实验管理模型（实验创建、查询）
- analysis: 数据分析模型（信号平滑、曲线拟合、磁滞回线分析）
- electromagnet: 电磁铁控制模型（电流设置、扫描、校准）
- piezo: 压电陶瓷控制模型（电压设置、位移控制、校准）
- ammeter: 微电流采集模型（采集控制、通道配置）
- temperature: 温度控制模型（温度设定、程序控制、PID参数）
"""

from schemas.common import (
    ErrorCode,
    ErrorResponse,
    SuccessResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)
from schemas.motor import (
    AlarmCodeResponse,
    HomeRequest,
    JogRequest,
    LimitConfigRequest,
    MoveRequest,
    MoveResponse,
    MotorStatusResponse,
    PRPathConfigRequest,
    PRPathTriggerRequest,
    StatusWordResponse,
)
from schemas.device import DeviceInfo
from schemas.experiment import ExperimentInfo, ExperimentRequest
from schemas.analysis import (
    AnalysisReportResponse,
    CompareDataset,
    CompareDatasetResult,
    CompareRequest,
    CompareResponse,
    FitRequest,
    FitResponse,
    HistoryDataPoint,
    HistoryQueryRequest,
    HistoryQueryResponse,
    HysteresisRequest,
    HysteresisResponse,
    ModelFitResult,
    MultiFitRequest,
    MultiFitResponse,
    ReportExportRequest,
    ReportGenerateRequest,
    SmoothRequest,
    SmoothResponse,
)
from schemas.electromagnet import (
    CalibrationPoint,
    ElectromagnetCalibrateRequest,
    ElectromagnetScanRequest,
    ElectromagnetScanValidateRequest,
    ElectromagnetScanValidateResponse,
    ElectromagnetSetCurrentRequest,
    ElectromagnetStatusResponse,
    ScanMode,
    ELECTROMAGNET_MAX_CURRENT,
    ELECTROMAGNET_MAX_FIELD,
    ELECTROMAGNET_MAX_SCAN_RATE,
    ELECTROMAGNET_MIN_SCAN_RATE,
)
from schemas.piezo import (
    CalibrationDataResponse,
    CalibrationPerformRequest,
    CalibrationPointRequest,
    CalibrationPointResponse,
    ControlModeRequest,
    DisplacementResponse,
    DisplacementSetRequest,
    PiezoStatusResponse,
    VoltageResponse,
    VoltageSetRequest,
)
from schemas.ammeter import (
    AmmeterChannelConfigRequest,
    AmmeterChannelData,
    AmmeterChannelStatus,
    AmmeterDataResponse,
    AmmeterStartRequest,
    AmmeterStatusResponse,
)
from schemas.temperature import (
    PIDParametersRequest,
    ProtectionConfigRequest,
    TemperatureHistoryRecord,
    TemperatureHistoryRequest,
    TemperatureHistoryResponse,
    TemperatureProgramRequest,
    TemperatureProgramSegmentRequest,
    TemperatureSetpointRequest,
    TemperatureStatusResponse,
    TEMP_MAX_K,
    TEMP_MIN_K,
)

__all__ = [
    "SuccessResponse",
    "ErrorCode",
    "ErrorResponse",
    "ValidationErrorDetail",
    "ValidationErrorResponse",
    "MoveRequest",
    "MoveResponse",
    "JogRequest",
    "LimitConfigRequest",
    "PRPathConfigRequest",
    "PRPathTriggerRequest",
    "HomeRequest",
    "StatusWordResponse",
    "AlarmCodeResponse",
    "MotorStatusResponse",
    "DeviceInfo",
    "ExperimentRequest",
    "ExperimentInfo",
    "SmoothRequest",
    "SmoothResponse",
    "FitRequest",
    "FitResponse",
    "HysteresisRequest",
    "HysteresisResponse",
    "MultiFitRequest",
    "ModelFitResult",
    "MultiFitResponse",
    "ReportGenerateRequest",
    "AnalysisReportResponse",
    "ReportExportRequest",
    "HistoryQueryRequest",
    "HistoryDataPoint",
    "HistoryQueryResponse",
    "CompareDataset",
    "CompareRequest",
    "CompareDatasetResult",
    "CompareResponse",
    "ScanMode",
    "ELECTROMAGNET_MAX_CURRENT",
    "ELECTROMAGNET_MAX_FIELD",
    "ELECTROMAGNET_MIN_SCAN_RATE",
    "ELECTROMAGNET_MAX_SCAN_RATE",
    "ElectromagnetSetCurrentRequest",
    "CalibrationPoint",
    "ElectromagnetScanRequest",
    "ElectromagnetScanValidateRequest",
    "ElectromagnetScanValidateResponse",
    "ElectromagnetCalibrateRequest",
    "ElectromagnetStatusResponse",
    "VoltageSetRequest",
    "DisplacementSetRequest",
    "CalibrationPointRequest",
    "CalibrationPerformRequest",
    "ControlModeRequest",
    "VoltageResponse",
    "DisplacementResponse",
    "CalibrationPointResponse",
    "CalibrationDataResponse",
    "PiezoStatusResponse",
    "AmmeterStartRequest",
    "AmmeterChannelConfigRequest",
    "AmmeterChannelData",
    "AmmeterDataResponse",
    "AmmeterChannelStatus",
    "AmmeterStatusResponse",
    "TEMP_MIN_K",
    "TEMP_MAX_K",
    "TemperatureSetpointRequest",
    "TemperatureProgramSegmentRequest",
    "TemperatureProgramRequest",
    "PIDParametersRequest",
    "ProtectionConfigRequest",
    "TemperatureStatusResponse",
    "TemperatureHistoryRequest",
    "TemperatureHistoryRecord",
    "TemperatureHistoryResponse",
]
