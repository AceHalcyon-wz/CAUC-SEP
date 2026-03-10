"""
CAUC-SEP Database Migrations Module

数据库迁移模块，包含：
- 数据库结构更新
- 索引优化
- 约束添加
"""

from .add_calibration_logs_configs import run as add_calibration_logs_configs
from .add_constraints_indexes import run as add_constraints_indexes
from .optimize_indexes import run as optimize_indexes

__all__ = [
    "add_calibration_logs_configs",
    "add_constraints_indexes",
    "optimize_indexes",
]
