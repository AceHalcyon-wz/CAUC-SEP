"""
文件名: dm2c_process.py
路径: backend/drivers/
功能: DM2C步进驱动器进程化封装
作者: Backend Engineer Agent
创建日期: 2026-03-07
依赖: multiprocessing, asyncio, logging
"""

import logging
import time
from typing import Any

from core.abstract import DeviceStatus
from core.dm2c_driver import LeadshineDM2C

from .base import DriverProcessBase

logger = logging.getLogger(__name__)


class DM2CDriverProcess(DriverProcessBase):
    """DM2C步进驱动器进程化封装。

    将DM2C驱动器封装为独立进程运行，通过IPC通信控制。

    支持的命令：
        - move_abs: 绝对位置定位
        - move_rel: 相对位置定位
        - jog: JOG点动
        - jog_stop: 停止JOG
        - home: 回零
        - stop: 停止运动
        - read_position: 读取位置
        - read_status: 读取状态
        - clear_alarm: 清除报警
        - set_soft_limits: 设置软件限位
        - configure_pr_path: 配置PR路径
        - trigger_pr_path: 触发PR路径
        - configure_di: 配置数字输入
        - configure_do: 配置数字输出

    Example:
        >>> from backend.drivers import create_driver_process
        >>> import multiprocessing as mp
        >>>
        >>> command_queue = mp.Queue()
        >>> response_queue = mp.Queue()
        >>>
        >>> process = create_driver_process(
        ...     DM2CDriverProcess,
        ...     "motor_1",
        ...     {"port": "COM1", "slave_id": 1, "steps_per_mm": 1600},
        ...     command_queue,
        ...     response_queue,
        ... )
        >>> process.start()
        >>>
        >>> # 发送命令
        >>> command_queue.put(IPCMessage(
        ...     msg_type=IPCMessageType.COMMAND,
        ...     payload={"command": "move_abs", "params": {"position": 100, "speed": 10, "accel": 100, "decel": 100}}
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
        """初始化DM2C驱动进程。

        Args:
            driver_id: 驱动ID
            config: 驱动配置
                - port: 串口号（默认 "COM1"）
                - slave_id: 从站地址（默认 1）
                - baudrate: 波特率（默认 115200）
                - steps_per_mm: 每毫米步数（默认 1600）
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

        # DM2C驱动实例
        self.driver: LeadshineDM2C | None = None

        # 配置参数
        self.port = config.get("port", "COM1")
        self.slave_id = config.get("slave_id", 1)
        self.baudrate = config.get("baudrate", 115200)
        self.steps_per_mm = config.get("steps_per_mm", 1600)

        # 状态缓存
        self._cached_position = 0.0
        self._last_position_update = 0.0
        self._position_update_interval = 1.0  # 位置更新间隔（秒）

    async def initialize(self) -> bool:
        """初始化DM2C驱动实例。

        Returns:
            bool: 初始化是否成功
        """
        try:
            self.logger.info(
                f"初始化DM2C驱动: port={self.port}, "
                f"slave_id={self.slave_id}, baudrate={self.baudrate}"
            )

            # 创建驱动实例
            self.driver = LeadshineDM2C(
                device_id=self.driver_id,
                config={
                    "port": self.port,
                    "slave_id": self.slave_id,
                    "baudrate": self.baudrate,
                    "steps_per_mm": self.steps_per_mm,
                },
            )

            # 连接驱动
            success = await self.driver.connect()

            if success:
                self.logger.info("DM2C驱动初始化成功")
                return True
            else:
                self.logger.error("DM2C驱动连接失败")
                return False

        except Exception as e:
            self.logger.error(f"DM2C驱动初始化异常: {e}")
            return False

    async def cleanup(self) -> None:
        """清理DM2C驱动资源。"""
        if self.driver:
            try:
                await self.driver.disconnect()
                self.logger.info("DM2C驱动已断开连接")
            except Exception as e:
                self.logger.error(f"DM2C驱动断开连接异常: {e}")
            finally:
                self.driver = None

    async def handle_command(self, command: str, params: dict[str, Any]) -> Any:
        """处理DM2C驱动命令。

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
            raise RuntimeError("DM2C驱动未初始化")

        # 检查驱动状态（部分命令需要READY状态）
        motion_commands = [
            "move_abs",
            "move_rel",
            "jog",
            "home",
            "stop",
            "jog_stop",
            "emergency_stop",
        ]

        if command in motion_commands and self.driver.status not in (
            DeviceStatus.READY,
            DeviceStatus.BUSY,
        ):
            raise RuntimeError(f"驱动状态不允许执行命令: {self.driver.status.value}")

        # 执行命令
        if command == "move_abs":
            return await self.driver.move_abs(
                position=params["position"],
                speed=params["speed"],
                accel=params["accel"],
                decel=params["decel"],
            )

        elif command == "move_rel":
            return await self.driver.move_rel(
                distance=params["distance"],
                speed=params["speed"],
                accel=params["accel"],
                decel=params["decel"],
            )

        elif command == "jog":
            return await self.driver.jog(
                direction=params["direction"],
                speed=params["speed"],
            )

        elif command == "jog_stop":
            return await self.driver.jog_stop()

        elif command == "set_jog_speed":
            return await self.driver.set_jog_speed(speed=params["speed"])

        elif command == "set_jog_acceleration":
            return await self.driver.set_jog_acceleration(
                accel_time=params["accel_time"],
                decel_time=params["decel_time"],
            )

        elif command == "home":
            return await self.driver.home(mode=params.get("mode", "origin"))

        elif command == "set_current_position_zero":
            return await self.driver.set_current_position_zero()

        elif command == "stop":
            return await self.driver.stop(emergency=params.get("emergency", False))

        elif command == "emergency_stop":
            return await self.driver.emergency_stop()

        elif command == "reset_emergency":
            return await self.driver.reset_emergency()

        elif command == "read_position":
            return await self.driver.read_position()

        elif command == "read_status":
            return await self.driver.read_status()

        elif command == "read_status_word":
            return await self.driver.read_status_word()

        elif command == "read_alarm_code":
            alarm_code = await self.driver.read_alarm_code()
            return {"alarm_code": alarm_code}

        elif command == "get_alarm_details":
            return await self.driver.get_alarm_details(language=params.get("language", "zh"))

        elif command == "clear_alarm":
            return await self.driver.clear_alarm()

        elif command == "reset_alarm":
            return await self.driver.reset_alarm()

        elif command == "save_parameters":
            return await self.driver.save_parameters()

        elif command == "factory_reset":
            return await self.driver.factory_reset()

        elif command == "set_soft_limits":
            self.driver.set_soft_limits(
                positive_mm=params["positive_mm"],
                negative_mm=params["negative_mm"],
            )
            return True

        elif command == "set_limits":
            self.driver.set_limits(
                positive=params["positive"],
                negative=params["negative"],
                enable=params.get("enable", True),
            )
            return True

        elif command == "check_position_limit":
            return self.driver.check_position_limit(position=params["position"])

        elif command == "configure_pr_path":
            return await self.driver.configure_pr_path(
                path_number=params["path_number"],
                mode=params["mode"],
                position=params["position"],
                velocity=params["velocity"],
                accel_time=params.get("accel_time", 100),
                decel_time=params.get("decel_time", 100),
                dwell_time=params.get("dwell_time", 0),
                special_param=params.get("special_param", 0),
            )

        elif command == "trigger_pr_path":
            return await self.driver.trigger_pr_path(path_number=params["path_number"])

        elif command == "read_trigger_status":
            return await self.driver.read_trigger_status()

        elif command == "configure_home_mode":
            return await self.driver.configure_home_mode(mode=params["mode"])

        elif command == "configure_home_speed":
            return await self.driver.configure_home_speed(
                speed_high=params["speed_high"],
                speed_low=params["speed_low"],
            )

        elif command == "configure_home_offset":
            return await self.driver.configure_home_offset(offset=params["offset"])

        elif command == "configure_home_direction":
            return await self.driver.configure_home_direction(direction=params["direction"])

        elif command == "configure_di":
            return await self.driver.configure_di(
                di_number=params["di_number"],
                function=params["function"],
            )

        elif command == "configure_do":
            return await self.driver.configure_do(
                do_number=params["do_number"],
                function=params["function"],
            )

        elif command == "read_di_config":
            function = await self.driver.read_di_config(di_number=params["di_number"])
            return {"function": function}

        elif command == "read_do_config":
            function = await self.driver.read_do_config(do_number=params["do_number"])
            return {"function": function}

        elif command == "read_di_status":
            return await self.driver.read_di_status()

        elif command == "read_do_status":
            return await self.driver.read_do_status()

        elif command == "read_io_status":
            return await self.driver.read_io_status()

        elif command == "configure_all_di":
            return await self.driver.configure_all_di(config=params["config"])

        elif command == "configure_all_do":
            return await self.driver.configure_all_do(config=params["config"])

        else:
            raise ValueError(f"未知命令: {command}")

    async def periodic_task(self) -> None:
        """周期性任务：更新位置缓存。"""
        if self.driver is None:
            return

        # 定期更新位置缓存
        current_time = time.time()
        if current_time - self._last_position_update >= self._position_update_interval:
            try:
                position_data = await self.driver.read_position()
                self._cached_position = position_data.get("position_mm", 0.0)
                self._last_position_update = current_time
            except Exception as e:
                self.logger.error(f"更新位置缓存失败: {e}")
