"""
高级服务模块初始化

文件名: __init__.py
路径: backend/services/
功能: 统一导出所有高级服务模块
作者: Backend Engineer Agent
创建日期: 2026-03-25
"""

from backend.services.motor_advanced_service import (
    DITriggerAction,
    DITriggerConfig,
    HomeMode,
    MotorAdvancedService,
    PositionCheckResult,
    PRPathConfig,
    PRPathExecutionMode,
    PRPathSequence,
)
from backend.services.electromagnet_advanced_service import (
    CalibrationMethod,
    CalibrationPoint,
    CalibrationResult,
    CustomWaveformConfig,
    ElectromagnetAdvancedService,
    FieldControlConfig,
    ScanCheckpoint,
    ScanState,
    StepWaveformConfig,
    WaveformType,
)
from backend.services.temperature_advanced_service import (
    PIDParameters,
    PIDTuningMethod,
    ProgramCheckpoint,
    ProgramSegment,
    ProgramSegmentType,
    TemperatureAdvancedService,
    TemperatureHistoryPoint,
    TemperatureProgram,
    TemperatureProtection,
)
from backend.services.piezo_advanced_service import (
    HysteresisCalibrationData,
    HysteresisCompensationParams,
    HysteresisModel,
    PiezoAdvancedService,
    PiezoMode,
    PositionFeedback,
    ScanConfig,
    ScanWaveform,
)
from backend.services.picoammeter_advanced_service import (
    AnalysisResult,
    AnalysisType,
    CacheMetadata,
    ChannelConfig,
    ConnectionStatus,
    DataPoint,
    PicoammeterAdvancedService,
    TriggerConfig,
    TriggerType,
)
from backend.services.device_coordinator_service import (
    DeviceCoordinatorService,
    DeviceState,
    InterlockRule,
    InterlockType,
    SyncData,
    WorkflowDefinition,
    WorkflowNode,
    WorkflowNodeType,
    WorkflowState,
)
from backend.services.data_analysis_service import (
    CorrectionConfig,
    CorrectionType,
    DataAnalysisService,
    HysteresisData,
    HysteresisParameters,
    MRData,
    MRParameters,
    MREffectType,
)
from backend.services.experiment_lifecycle_service import (
    ExperimentData,
    ExperimentLifecycleService,
    ExperimentMetadata,
    ExperimentStatus,
    ExperimentTemplate,
    ExportConfig,
    ExportFormat,
    ReportConfig,
    ReportType,
)

__all__ = [
    # 步进电机高级服务
    "MotorAdvancedService",
    "PRPathConfig",
    "PRPathSequence",
    "PRPathExecutionMode",
    "HomeMode",
    "PositionCheckResult",
    "DITriggerConfig",
    "DITriggerAction",
    # 电磁铁高级服务
    "ElectromagnetAdvancedService",
    "StepWaveformConfig",
    "CustomWaveformConfig",
    "WaveformType",
    "CalibrationPoint",
    "CalibrationResult",
    "CalibrationMethod",
    "ScanState",
    "ScanCheckpoint",
    "FieldControlConfig",
    # 温度控制器高级服务
    "TemperatureAdvancedService",
    "TemperatureProgram",
    "ProgramSegment",
    "ProgramSegmentType",
    "ProgramCheckpoint",
    "PIDParameters",
    "PIDTuningMethod",
    "TemperatureProtection",
    "TemperatureHistoryPoint",
    # 压电控制器高级服务
    "PiezoAdvancedService",
    "PiezoMode",
    "HysteresisModel",
    "HysteresisCalibrationData",
    "HysteresisCompensationParams",
    "ScanConfig",
    "ScanWaveform",
    "PositionFeedback",
    # 皮安表高级服务
    "PicoammeterAdvancedService",
    "ChannelConfig",
    "TriggerConfig",
    "TriggerType",
    "DataPoint",
    "AnalysisResult",
    "AnalysisType",
    "ConnectionStatus",
    "CacheMetadata",
    # 多设备协同控制服务
    "DeviceCoordinatorService",
    "WorkflowNode",
    "WorkflowNodeType",
    "WorkflowDefinition",
    "WorkflowState",
    "InterlockRule",
    "InterlockType",
    "DeviceState",
    "SyncData",
    # 数据分析服务
    "DataAnalysisService",
    "HysteresisData",
    "HysteresisParameters",
    "MRData",
    "MRParameters",
    "MREffectType",
    "CorrectionType",
    "CorrectionConfig",
    # 实验生命周期管理服务
    "ExperimentLifecycleService",
    "ExperimentMetadata",
    "ExperimentData",
    "ExperimentStatus",
    "ExperimentTemplate",
    "ExportFormat",
    "ExportConfig",
    "ReportType",
    "ReportConfig",
]
