"""
文件名: __init__.py
路径: backend/drivers/
功能: 驱动进程化模块，提供独立进程运行的设备驱动
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: multiprocessing, asyncio

模块说明:
    本模块将设备驱动封装为独立进程运行，实现进程隔离和故障隔离。
    通过IPC（进程间通信）机制实现主进程与驱动进程之间的命令传递和状态同步。

导出类:
    DriverProcessBase: 驱动进程基类，提供进程生命周期管理和IPC通信框架
    DriverProcessConfig: 驱动进程配置数据类
    DriverProcessState: 驱动进程状态枚举
    DM2CDriverProcess: DM2C步进驱动器进程封装
    ElectromagnetDriverProcess: 电磁铁驱动进程封装
    TemperatureDriverProcess: 温控驱动进程封装

使用示例:
    >>> from backend.drivers import create_driver_process, DM2CDriverProcess
    >>> import multiprocessing as mp
    >>>
    >>> command_queue = mp.Queue()
    >>> response_queue = mp.Queue()
    >>>
    >>> process = create_driver_process(
    ...     DM2CDriverProcess,
    ...     "motor_1",
    ...     {"port": "COM1", "slave_id": 1},
    ...     command_queue,
    ...     response_queue,
    ... )
    >>> process.start()

注意事项:
    - Windows平台使用spawn方式创建子进程
    - 回调函数不能跨进程传递，需使用轮询或消息队列替代
    - 子进程异常不会影响主进程运行
"""

from .base import (
    DriverProcessBase,
    DriverProcessConfig,
    DriverProcessState,
    IPCMessage,
    IPCMessageType,
    create_driver_process,
)
from .dm2c_process import DM2CDriverProcess
from .electromagnet_process import ElectromagnetDriverProcess
from .temperature_process import TemperatureDriverProcess

__all__ = [
    # 基类和配置
    "DriverProcessBase",
    "DriverProcessConfig",
    "DriverProcessState",
    # IPC通信
    "IPCMessage",
    "IPCMessageType",
    "create_driver_process",
    # 具体驱动实现
    "DM2CDriverProcess",
    "ElectromagnetDriverProcess",
    "TemperatureDriverProcess",
]
