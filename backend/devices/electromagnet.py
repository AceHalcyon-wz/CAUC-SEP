"""
电磁铁驱动模块

功能：
- 恒流模式控制
- 扫描模式控制（正向/反向/三角波）
- 磁场-电流校准
- 过流保护机制

技术规范：
- 电流范围：0-10A
- 电流精度：±0.1%
- 磁场范围：0-2T（特斯拉）
- 扫描速率：0.01-1 A/s
- 过流保护阈值：10.5A

安全警告：
- 实验时必须有人值守
- 首次使用前验证电流限制参数
- 过流保护触发后需手动复位

作者：Backend Engineer Agent
更新日期：2026-03-14
"""

from core.electromagnet_driver import (
    CalibrationPoint,
    ElectromagnetDriver,
    ElectromagnetStatus,
    MAX_CURRENT,
    MAX_FIELD,
    MAX_SCAN_RATE,
    MAX_TEMPERATURE,
    MIN_CURRENT,
    MIN_SCAN_RATE,
    OVERCURRENT_THRESHOLD,
    ScanMode,
    ScanParameters,
)

__all__ = [
    "MAX_CURRENT",
    "MAX_FIELD",
    "MAX_SCAN_RATE",
    "MAX_TEMPERATURE",
    "MIN_CURRENT",
    "MIN_SCAN_RATE",
    "OVERCURRENT_THRESHOLD",
    "CalibrationPoint",
    "ElectromagnetDriver",
    "ElectromagnetStatus",
    "ScanMode",
    "ScanParameters",
]
