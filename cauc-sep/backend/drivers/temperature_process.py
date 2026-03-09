"""
文件名: temperature_process.py
路径: backend/drivers/
功能: 温控驱动进程化封装
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: multiprocessing, asyncio, logging
"""

import logging
import time
from typing import Any, Dict, List

from .base import DriverProcessBase
from core.temperature_controller import (
    TemperatureController,
    TemperatureControllerMode,
    TemperatureProtectionType,
    TemperatureProgramSegment,
)
from core.abstract import DeviceStatus

logger = logging.getLogger(__name__)


class TemperatureDriverProcess(DriverProcessBase):
    """温控驱动进程化封装。

    将温控驱动器封装为独立进程运行，通过IPC通信控制。

    支持的命令：
        - set_temperature: 设置目标温度（手动模式）
        - set_output: 直接设置输出功率（手动模式）
        - start_pid_control: 启动PID控制
        - stop_pid_control: 停止PID控制
        - set_pid_parameters: 设置PID参数
        - load_program: 加载温度程序
        - start_program: 启动程序控温
        - stop_program: 停止程序控温
        - get_program_status: 获取程序控温状态
        - read_temperature: 读取当前温度
        - read_all_sensors: 读取所有传感器通道
        - set_primary_sensor: 设置主传感器通道
        - configure_sensor_channel: 配置传感器通道
        - read_status: 读取设备状态
        - set_protection_config: 设置温度保护配置
        - clear_protection: 清除温度保护状态
        - get_temperature_history: 获取温度历史记录
        - clear_temperature_history: 清除温度历史记录
        - export_temperature_history: 导出温度历史记录
        - emergency_stop: 紧急停止
        - reset_emergency: 复位紧急停止
        - add_protection_callback: 添加保护回调（进程模式下无效）
        - remove_protection_callback: 移除保护回调（进程模式下无效）

    Example:
        >>> from backend.drivers import create_driver_process
        >>> import multiprocessing as mp
        >>> 
        >>> command_queue = mp.Queue()
        >>> response_queue = mp.Queue()
        >>> 
        >>> process = create_driver_process(
        ...     TemperatureDriverProcess,
        ...     "temp_controller_1",
        ...     {"simulation": True, "pid_params": {"kp": 1.0, "ki": 0.1, "kd": 0.01}},
        ...     command_queue,
        ...     response_queue,
        ... )
        >>> process.start()
        >>> 
        >>> # 发送命令
        >>> command_queue.put(IPCMessage(
        ...     msg_type=IPCMessageType.COMMAND,
        ...     payload={"command": "set_temperature", "params": {"temperature": 300.0}}
        ... ))
    """

    def __init__(
        self,
        driver_id: str,
        config: Dict[str, Any],
        command_queue,
        response_queue,
        heartbeat_interval: float = 10.0,
    ):
        """初始化温控驱动进程。

        Args:
            driver_id: 驱动ID
            config: 驱动配置
                - simulation: 是否仿真模式（默认 True）
                - pid_params: PID参数字典（可选）
                - protection: 保护配置字典（可选）
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

        # 温控驱动实例
        self.driver: TemperatureController | None = None

        # 配置参数
        self.simulation = config.get("simulation", True)

        # 状态缓存
        self._cached_temperature = 300.0
        self._cached_output = 0.0
        self._last_status_update = 0.0
        self._status_update_interval = 1.0  # 状态更新间隔（秒）

    async def initialize(self) -> bool:
        """初始化温控驱动实例。

        Returns:
            bool: 初始化是否成功
        """
        try:
            self.logger.info(
                f"初始化温控驱动: simulation={self.simulation}"
            )

            # 创建驱动实例
            self.driver = TemperatureController(
                device_id=self.driver_id,
                config={
                    "simulation": self.simulation,
                    "pid_params": self.config.get("pid_params", {}),
                    "protection": self.config.get("protection", {}),
                },
            )

            # 连接驱动
            success = await self.driver.connect()

            if success:
                self.logger.info("温控驱动初始化成功")
                return True
            else:
                self.logger.error("温控驱动连接失败")
                return False

        except Exception as e:
            self.logger.error(f"温控驱动初始化异常: {e}")
            return False

    async def cleanup(self) -> None:
        """清理温控驱动资源。"""
        if self.driver:
            try:
                await self.driver.disconnect()
                self.logger.info("温控驱动已断开连接")
            except Exception as e:
                self.logger.error(f"温控驱动断开连接异常: {e}")
            finally:
                self.driver = None

    async def handle_command(self, command: str, params: Dict[str, Any]) -> Any:
        """处理温控驱动命令。

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
            raise RuntimeError("温控驱动未初始化")

        # 检查驱动状态（部分命令需要READY状态）
        control_commands = [
            "set_temperature", "set_output", "start_pid_control", 
            "start_program", "load_program"
        ]

        if command in control_commands and self.driver.status not in (
            DeviceStatus.READY,
        ):
            raise RuntimeError(
                f"驱动状态不允许执行命令: {self.driver.status.value}"
            )

        # 检查保护状态
        if command in control_commands and self.driver._protection_triggered:
            raise RuntimeError("保护状态不允许执行命令")

        # 执行命令
        if command == "set_temperature":
            return await self.driver.set_temperature(temperature=params["temperature"])

        elif command == "set_output":
            return await self.driver.set_output(output=params["output"])

        elif command == "start_pid_control":
            return await self.driver.start_pid_control()

        elif command == "stop_pid_control":
            return await self.driver.stop_pid_control()

        elif command == "set_pid_parameters":
            return await self.driver.set_pid_parameters(
                kp=params.get("kp"),
                ki=params.get("ki"),
                kd=params.get("kd"),
                setpoint=params.get("setpoint"),
            )

        elif command == "load_program":
            # 转换程序段
            segments = []
            for seg_data in params["segments"]:
                segment = TemperatureProgramSegment(
                    target_temperature=seg_data["target_temperature"],
                    ramp_rate=seg_data.get("ramp_rate", 1.0),
                    hold_time=seg_data.get("hold_time", 0.0),
                    segment_id=seg_data.get("segment_id", 0),
                    tolerance=seg_data.get("tolerance", 0.5),
                    timeout=seg_data.get("timeout", 0.0),
                )
                segments.append(segment)
            
            return await self.driver.load_program(segments=segments)

        elif command == "start_program":
            return await self.driver.start_program()

        elif command == "stop_program":
            return await self.driver.stop_program()

        elif command == "get_program_status":
            return await self.driver.get_program_status()

        elif command == "read_temperature":
            temperature = await self.driver.read_temperature()
            return {"temperature": temperature}

        elif command == "read_all_sensors":
            return await self.driver.read_all_sensors()

        elif command == "set_primary_sensor":
            return self.driver.set_primary_sensor(channel_id=params["channel_id"])

        elif command == "configure_sensor_channel":
            return self.driver.configure_sensor_channel(
                channel_id=params["channel_id"],
                enabled=params.get("enabled"),
                name=params.get("name"),
                calibration_offset=params.get("calibration_offset"),
                calibration_scale=params.get("calibration_scale"),
                is_primary=params.get("is_primary"),
            )

        elif command == "read_status":
            return await self.driver.read_status()

        elif command == "get_current_temperature":
            return {"current_temperature": self.driver.current_temperature}

        elif command == "get_current_output":
            return {"current_output": self.driver.current_output}

        elif command == "get_mode":
            return {"mode": self.driver.mode.value}

        elif command == "set_protection_config":
            return await self.driver.set_protection_config(
                high_temp_limit=params.get("high_temp_limit"),
                low_temp_limit=params.get("low_temp_limit"),
                max_rate_limit=params.get("max_rate_limit"),
                enable_high_temp=params.get("enable_high_temp"),
                enable_low_temp=params.get("enable_low_temp"),
                enable_rate_limit=params.get("enable_rate_limit"),
            )

        elif command == "clear_protection":
            return await self.driver.clear_protection()

        elif command == "get_temperature_history":
            return await self.driver.get_temperature_history(
                start_time=params.get("start_time"),
                end_time=params.get("end_time"),
                limit=params.get("limit"),
            )

        elif command == "clear_temperature_history":
            await self.driver.clear_temperature_history()
            return True

        elif command == "export_temperature_history":
            data = await self.driver.export_temperature_history(
                format=params.get("format", "csv")
            )
            return {"data": data}

        elif command == "emergency_stop":
            return await self.driver.emergency_stop()

        elif command == "reset_emergency":
            return await self.driver.reset_emergency()

        elif command == "add_protection_callback":
            # 注意：回调函数不能跨进程传递，此命令在进程模式下无效
            self.logger.warning("add_protection_callback not supported in process mode")
            return False

        elif command == "remove_protection_callback":
            # 注意：回调函数不能跨进程传递，此命令在进程模式下无效
            self.logger.warning("remove_protection_callback not supported in process mode")
            return False

        elif command == "get_pid_params":
            return {
                "kp": self.driver.pid_params.kp,
                "ki": self.driver.pid_params.ki,
                "kd": self.driver.pid_params.kd,
                "setpoint": self.driver.pid_params.setpoint,
                "output_min": self.driver.pid_params.output_min,
                "output_max": self.driver.pid_params.output_max,
            }

        elif command == "get_protection_config":
            return {
                "high_temp_limit": self.driver.protection_config.high_temp_limit,
                "low_temp_limit": self.driver.protection_config.low_temp_limit,
                "max_rate_limit": self.driver.protection_config.max_rate_limit,
                "enable_high_temp": self.driver.protection_config.enable_high_temp,
                "enable_low_temp": self.driver.protection_config.enable_low_temp,
                "enable_rate_limit": self.driver.protection_config.enable_rate_limit,
            }

        elif command == "is_pid_running":
            return {"pid_running": self.driver._pid_running}

        elif command == "is_program_running":
            return {"program_running": self.driver._program_running}

        elif command == "is_protection_triggered":
            return {
                "protection_triggered": self.driver._protection_triggered,
                "protection_type": self.driver._protection_type.value if self.driver._protection_type else None,
            }

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
                self._cached_temperature = self.driver.current_temperature
                self._cached_output = self.driver.current_output
                self._last_status_update = current_time
            except Exception as e:
                self.logger.error(f"更新状态缓存失败: {e}")
