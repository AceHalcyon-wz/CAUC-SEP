"""
文件名: electromagnet_process.py
路径: backend/drivers/
功能: 电磁铁驱动进程化封装
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: multiprocessing, asyncio, logging
"""

import logging
import time
from typing import Any

from core.abstract import DeviceStatus
from core.electromagnet_driver import ElectromagnetDriver, ElectromagnetStatus, ScanMode

from .base import DriverProcessBase

logger = logging.getLogger(__name__)


class ElectromagnetDriverProcess(DriverProcessBase):
    """电磁铁驱动进程化封装。

    将电磁铁驱动器封装为独立进程运行，通过IPC通信控制。

    支持的命令：
        - set_current: 设置恒流模式电流
        - start_scan: 启动扫描模式
        - stop_scan: 停止扫描模式
        - calibrate: 执行磁场-电流校准
        - clear_calibration: 清除校准数据
        - get_calibration_data: 获取校准数据
        - set_field: 设置目标磁场值
        - quick_scan: 快速启动磁场扫描
        - emergency_stop: 紧急停止
        - reset_emergency: 复位紧急停止
        - reset_overcurrent_protection: 复位过流保护
        - reset_overtemperature_protection: 复位过温保护
        - read_status: 读取设备状态
        - validate_scan_params: 验证扫描参数

    Example:
        >>> from backend.drivers import create_driver_process
        >>> import multiprocessing as mp
        >>>
        >>> command_queue = mp.Queue()
        >>> response_queue = mp.Queue()
        >>>
        >>> process = create_driver_process(
        ...     ElectromagnetDriverProcess,
        ...     "electromagnet_1",
        ...     {"port": "COM3", "max_current": 10.0, "simulation": True},
        ...     command_queue,
        ...     response_queue,
        ... )
        >>> process.start()
        >>>
        >>> # 发送命令
        >>> command_queue.put(IPCMessage(
        ...     msg_type=IPCMessageType.COMMAND,
        ...     payload={"command": "set_current", "params": {"current": 5.0}}
        ... ))
    """

    def __init__(
        self,
        driver_id: str,
        config: dict[str, Any],
        command_queue,
        response_queue,
        heartbeat_interval: float = 10.0,
    ):
        """初始化电磁铁驱动进程。

        Args:
            driver_id: 驱动ID
            config: 驱动配置
                - port: 通信端口（默认 "COM3"）
                - baudrate: 波特率（默认 9600）
                - max_current: 最大电流限制（默认 10.0A）
                - calibration_points: 校准点列表（可选）
                - simulation: 是否仿真模式（默认 True）
            command_queue: 命令队列
            response_queue: 响应队列
            heartbeat_interval: 心跳间隔（秒）
        """
        super().__init__(
            driver_id=driver_id,
            config=config,
            command_queue=command_queue,
            response_queue=response_queue,
            heartbeat_interval=heartbeat_interval,
        )

        # 电磁铁驱动实例
        self.driver: ElectromagnetDriver | None = None

        # 配置参数
        self.port = config.get("port", "COM3")
        self.baudrate = config.get("baudrate", 9600)
        self.max_current = config.get("max_current", 10.0)
        self.simulation = config.get("simulation", True)

        # 状态缓存
        self._cached_current = 0.0
        self._cached_field = 0.0
        self._last_status_update = 0.0
        self._status_update_interval = 0.5  # 状态更新间隔（秒）

    async def initialize(self) -> bool:
        """初始化电磁铁驱动实例。

        Returns:
            bool: 初始化是否成功
        """
        try:
            self.logger.info(
                f"初始化电磁铁驱动: port={self.port}, "
                f"max_current={self.max_current}A, simulation={self.simulation}"
            )

            # 创建驱动实例
            self.driver = ElectromagnetDriver(
                device_id=self.driver_id,
                config={
                    "port": self.port,
                    "baudrate": self.baudrate,
                    "max_current": self.max_current,
                    "simulation": self.simulation,
                    "calibration_points": self.config.get("calibration_points", []),
                },
            )

            # 连接驱动
            success = await self.driver.connect()

            if success:
                self.logger.info("电磁铁驱动初始化成功")
                return True
            else:
                self.logger.error("电磁铁驱动连接失败")
                return False

        except Exception as e:
            self.logger.error(f"电磁铁驱动初始化异常: {e}")
            return False

    async def cleanup(self) -> None:
        """清理电磁铁驱动资源。"""
        if self.driver:
            try:
                await self.driver.disconnect()
                self.logger.info("电磁铁驱动已断开连接")
            except Exception as e:
                self.logger.error(f"电磁铁驱动断开连接异常: {e}")
            finally:
                self.driver = None

    async def handle_command(self, command: str, params: dict[str, Any]) -> Any:
        """处理电磁铁驱动命令。

        Args:
            command: 命令名称
            params: 命令参数

        Returns:
            Any: 命令执行结果

        Raises:
            RuntimeError: 驱动未初始化
            ValueError: 未知命令
        """
        if self.driver is None:
            raise RuntimeError("电磁铁驱动未初始化")

        # 检查驱动状态（部分命令需要READY状态）
        motion_commands = ["set_current", "start_scan", "set_field", "quick_scan"]

        if command in motion_commands and self.driver.status not in (DeviceStatus.READY,):
            raise RuntimeError(f"驱动状态不允许执行命令: {self.driver.status.value}")

        # 检查保护状态
        protection_commands = ["set_current", "start_scan", "set_field", "quick_scan"]

        if command in protection_commands and self.driver.electromagnet_status in (
            ElectromagnetStatus.OVERCURRENT,
            ElectromagnetStatus.OVERTEMPERATURE,
        ):
            raise RuntimeError(f"保护状态不允许执行命令: {self.driver.electromagnet_status.value}")

        # 执行命令
        if command == "set_current":
            return await self.driver.set_current(current=params["current"])

        elif command == "start_scan":
            return await self.driver.start_scan(
                mode=ScanMode(params["mode"]),
                start_current=params["start_current"],
                end_current=params["end_current"],
                scan_rate=params["scan_rate"],
                cycles=params.get("cycles", 1),
                step_interval_ms=params.get("step_interval_ms"),
            )

        elif command == "stop_scan":
            return await self.driver.stop_scan()

        elif command == "calibrate":
            return await self.driver.calibrate(calibration_points=params["calibration_points"])

        elif command == "clear_calibration":
            return await self.driver.clear_calibration()

        elif command == "get_calibration_data":
            return self.driver.get_calibration_data()

        elif command == "set_field":
            return await self.driver.set_field(field=params["field"])

        elif command == "quick_scan":
            return await self.driver.quick_scan(
                start_field=params["start_field"],
                end_field=params["end_field"],
                scan_rate=params.get("scan_rate", 0.1),
            )

        elif command == "emergency_stop":
            return await self.driver.emergency_stop()

        elif command == "reset_emergency":
            return await self.driver.reset_emergency()

        elif command == "reset_overcurrent_protection":
            return await self.driver.reset_overcurrent_protection()

        elif command == "reset_overtemperature_protection":
            return await self.driver.reset_overtemperature_protection()

        elif command == "read_status":
            return await self.driver.read_status()

        elif command == "get_current_value":
            return {"current_value": self.driver.current_value}

        elif command == "get_field_value":
            return {"field_value": self.driver.field_value}

        elif command == "get_electromagnet_status":
            return {"electromagnet_status": self.driver.electromagnet_status.value}

        elif command == "get_current_temperature":
            return {"current_temperature": self.driver.current_temperature}

        elif command == "get_scan_progress":
            return {"scan_progress": self.driver.scan_progress}

        elif command == "validate_scan_params":
            valid, errors = self.driver.validate_scan_params(
                mode=ScanMode(params["mode"]),
                start_current=params["start_current"],
                end_current=params["end_current"],
                scan_rate=params["scan_rate"],
                cycles=params.get("cycles", 1),
            )
            return {"valid": valid, "errors": errors}

        elif command == "set_status_callback":
            # 注意：回调函数不能跨进程传递，此命令在进程模式下无效
            self.logger.warning("set_status_callback not supported in process mode")
            return False

        elif command == "set_progress_callback":
            # 注意：回调函数不能跨进程传递，此命令在进程模式下无效
            self.logger.warning("set_progress_callback not supported in process mode")
            return False

        else:
            raise ValueError(f"未知命令: {command}")

    async def periodic_task(self) -> None:
        """周期性任务：更新状态缓存。"""
        if self.driver is None:
            return

        # 定期更新状态缓存
        current_time = time.time()
        if current_time - self._last_status_update >= self._status_update_interval:
            try:
                self._cached_current = self.driver.current_value
                self._cached_field = self.driver.field_value
                self._last_status_update = current_time
            except Exception as e:
                self.logger.error(f"更新状态缓存失败: {e}")
