"""
步进电机驱动模块 (DM2C)

功能：
- Modbus RTU通信
- PR模式支持（16段位置表）
- 状态字完整解析
- 报警代码读取和解析
- 报警描述本地化（中英文）
- 报警清除功能
- 回零操作
- JOG模式
- 参数保存到EEPROM
- 恢复出厂设置
- 报警复位

安全警告：
- 实验时必须有人值守
- 首次使用前验证限位参数

参考文档：DM2C-RS556用户手册 V1.8

作者：Backend Engineer Agent
更新日期：2026-03-14
"""

from core.dm2c_driver import (
    ALARM_CODES,
    ALARM_INFO_MAP,
    AlarmInfo,
    AlarmSeverity,
    LeadshineDM2C,
    mm_to_steps,
    steps_to_mm,
)

__all__ = [
    "LeadshineDM2C",
    "mm_to_steps",
    "steps_to_mm",
    "ALARM_CODES",
    "ALARM_INFO_MAP",
    "AlarmInfo",
    "AlarmSeverity",
]
