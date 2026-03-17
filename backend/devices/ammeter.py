"""
微电流采集模块 (Picoammeter)

功能：
- 多通道同步采集（4通道）
- 可配置采样率（1Hz-1kHz）
- 噪声抑制滤波（低通、移动平均、中值滤波）
- 信噪比计算
- 仿真模式和真实硬件模式支持

技术规范：
- 电流范围：1pA-1mA
- 电流分辨率：1pA
- 通道数：4通道
- 采样率：1Hz-1kHz

安全警告：
- 实验时必须有人值守
- 首次使用前验证量程参数

作者：Backend Engineer Agent
更新日期：2026-03-14
"""

from core.picoammeter import (
    AcquisitionConfig,
    ChannelConfig,
    ChannelData,
    CurrentRange,
    FilterType,
    Picoammeter,
)

__all__ = [
    "AcquisitionConfig",
    "ChannelConfig",
    "ChannelData",
    "CurrentRange",
    "FilterType",
    "Picoammeter",
]
