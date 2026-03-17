"""
温控系统驱动模块

功能：
- PID闭环控制算法（支持双向控制：加热/冷却）
- 程序控温（多段温度程序，支持升温段、恒温段、降温段）
- 温度保护机制（高/低温保护、温度变化率保护）
- 温度曲线记录
- 多路传感器支持（4通道，支持主传感器选择和故障检测）
- 支持仿真模式和真实硬件模式

技术规范：
- 温度范围：77K-400K（液氮釜）
- 温度精度：±0.1K
- PID参数范围：
  - Kp: 0.1-100
  - Ki: 0.001-10
  - Kd: 0.001-10
  - setpoint: 77K-400K
  - output: -100%到100%（负值表示冷却）
- 升降温速率：-10到10 K/min（0表示立即跳转）

安全警告：
- 实验时必须有人值守
- 首次使用前验证温度保护参数
- 液氮操作需遵守安全规范

作者：Backend Engineer Agent
更新日期：2026-03-14
"""

from core.temperature_controller import (
    NUM_SENSOR_CHANNELS,
    PIDParameters,
    ProtectionCallback,
    RATE_CALCULATION_WINDOW_SIZE,
    SensorChannel,
    TemperatureController,
    TemperatureControllerMode,
    TemperatureProtectionType,
)

__all__ = [
    "NUM_SENSOR_CHANNELS",
    "RATE_CALCULATION_WINDOW_SIZE",
    "PIDParameters",
    "ProtectionCallback",
    "SensorChannel",
    "TemperatureController",
    "TemperatureControllerMode",
    "TemperatureProtectionType",
]
