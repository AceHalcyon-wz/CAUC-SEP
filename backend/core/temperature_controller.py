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
- 温度保护阈值：
  - 高温保护：>450K
  - 低温保护：<70K
  - 温度变化率保护：>20 K/min（使用滑动窗口计算）
- 多路传感器：4通道，支持主传感器选择

安全警告：
- 实验时必须有人值守
- 首次使用前验证温度保护参数
- 液氮操作需遵守安全规范
- ⚠️ 生成的代码需要手动审查和测试，不要直接部署到生产环境

作者：Backend Engineer Agent
创建日期：2026-03-07
版本：v1.1（修复版本）
"""

import asyncio
import logging
import time
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

from .abstract import AbstractDevice, DeviceStatus

logger = logging.getLogger(__name__)


# 多路传感器常量
NUM_SENSOR_CHANNELS = 4  # 传感器通道数量

# 温度变化率计算窗口大小
RATE_CALCULATION_WINDOW_SIZE = 10  # 使用最近10个数据点计算平均变化率


class TemperatureControllerMode(Enum):
    """温控模式枚举。

    Attributes:
        MANUAL: 手动控温模式
        PROGRAM: 程序控温模式
        PID: PID闭环控制模式
    """

    MANUAL = "manual"
    PROGRAM = "program"
    PID = "pid"


class TemperatureProtectionType(Enum):
    """温度保护类型枚举。

    Attributes:
        HIGH_TEMP: 高温保护
        LOW_TEMP: 低温保护
        RATE_LIMIT: 温度变化率保护
    """

    HIGH_TEMP = "high_temperature"
    LOW_TEMP = "low_temperature"
    RATE_LIMIT = "rate_limit"


# 保护回调函数类型
ProtectionCallback = Callable[[TemperatureProtectionType, float, float], None]
# 参数：保护类型, 当前温度, 触发阈值


@dataclass
class PIDParameters:
    """PID控制参数数据类。

    Attributes:
        kp: 比例系数（0.1-100）
        ki: 积分系数（0.001-10）
        kd: 微分系数（0.001-10）
        setpoint: 目标温度（K）
        output_min: 最小输出（%），支持负值用于冷却
        output_max: 最大输出（%）
        integral_limit: 积分限幅（防止积分饱和），默认自动计算

    Note:
        output_min可以为负值，表示冷却功率（如液氮流量控制）
        典型配置：output_min=-100（全速冷却），output_max=100（全速加热）
    """

    kp: float = 1.0
    ki: float = 0.1
    kd: float = 0.01
    setpoint: float = 300.0
    output_min: float = -100.0  # 支持负输出（冷却）
    output_max: float = 100.0
    integral_limit: float = 0.0  # 0表示自动计算

    def validate(self, min_temp: float = 77.0, max_temp: float = 400.0) -> bool:
        """验证PID参数是否在有效范围内。

        Args:
            min_temp: 最低温度限制（K）
            max_temp: 最高温度限制（K）

        Returns:
            bool: 参数是否有效
        """
        # 验证Kp范围
        if not (0.1 <= self.kp <= 100):
            logger.error(f"Invalid Kp: {self.kp}, must be 0.1-100")
            return False

        # 验证Ki范围
        if not (0.001 <= self.ki <= 10):
            logger.error(f"Invalid Ki: {self.ki}, must be 0.001-10")
            return False

        # 验证Kd范围
        if not (0.001 <= self.kd <= 10):
            logger.error(f"Invalid Kd: {self.kd}, must be 0.001-10")
            return False

        # 验证setpoint范围
        if not (min_temp <= self.setpoint <= max_temp):
            logger.error(f"Invalid setpoint: {self.setpoint}K, must be {min_temp}K-{max_temp}K")
            return False

        # 验证输出范围（允许负值用于冷却）
        if self.output_min >= self.output_max:
            logger.error(f"Invalid output range: min={self.output_min}%, max={self.output_max}%")
            return False

        # 验证输出范围绝对值不超过100%
        if abs(self.output_min) > 100 or abs(self.output_max) > 100:
            logger.error("Output range must be within -100% to 100%")
            return False

        return True


@dataclass
class SensorChannel:
    """传感器通道数据类。

    Attributes:
        channel_id: 通道ID（0-3）
        enabled: 是否启用通道
        name: 通道名称
        temperature: 当前温度（K）
        last_update: 最后更新时间戳
        calibration_offset: 校准偏移（K）
        calibration_scale: 校准系数
        is_primary: 是否为主传感器（用于控制）
        fault_detected: 是否检测到故障
        fault_message: 故障信息
    """

    channel_id: int = 0
    enabled: bool = True
    name: str = ""
    temperature: float = 300.0
    last_update: float = 0.0
    calibration_offset: float = 0.0
    calibration_scale: float = 1.0
    is_primary: bool = False
    fault_detected: bool = False
    fault_message: str = ""

    def apply_calibration(self, raw_temp: float) -> float:
        """应用校准参数。

        Args:
            raw_temp: 原始温度值（K）

        Returns:
            float: 校准后的温度值（K）
        """
        return raw_temp * self.calibration_scale + self.calibration_offset

    def check_fault(self, min_temp: float = 50.0, max_temp: float = 500.0) -> bool:
        """检查传感器是否有故障。

        Args:
            min_temp: 合理最低温度（K）
            max_temp: 合理最高温度（K）

        Returns:
            bool: 是否检测到故障
        """
        # 检查温度是否在合理范围内
        if not (min_temp <= self.temperature <= max_temp):
            self.fault_detected = True
            self.fault_message = (
                f"Temperature {self.temperature:.1f}K out of range " f"[{min_temp}K, {max_temp}K]"
            )
            return True

        # 检查校准参数是否合理
        if self.calibration_scale <= 0:
            self.fault_detected = True
            self.fault_message = f"Invalid calibration_scale: {self.calibration_scale}"
            return True

        # 清除故障标志
        self.fault_detected = False
        self.fault_message = ""
        return False


@dataclass
class TemperatureProgramSegment:
    """温度程序段数据类。

    Attributes:
        target_temperature: 目标温度（K）
        ramp_rate: 升降温速率（K/min），正值升温，负值降温，0表示立即跳转
        hold_time: 恒温时间（秒）
        segment_id: 程序段ID
        tolerance: 温度跟随容差（K），默认0.5K
        timeout: 段执行超时时间（秒），0表示无限制
    """

    target_temperature: float
    ramp_rate: float = 1.0  # K/min
    hold_time: float = 0.0  # 秒
    segment_id: int = 0
    tolerance: float = 0.5  # K
    timeout: float = 0.0  # 秒，0表示无限制

    def validate(self, min_temp: float = 77.0, max_temp: float = 400.0) -> bool:
        """验证程序段参数是否有效。

        Args:
            min_temp: 最低温度限制（K）
            max_temp: 最高温度限制（K）

        Returns:
            bool: 参数是否有效
        """
        if not (min_temp <= self.target_temperature <= max_temp):
            logger.error(
                f"Invalid target temperature: {self.target_temperature}K, "
                f"must be {min_temp}K-{max_temp}K"
            )
            return False
        # ramp_rate为0表示立即跳转，允许0值
        if abs(self.ramp_rate) > 10:
            logger.error(f"Invalid ramp rate: {self.ramp_rate}K/min, must be -10 to 10 K/min")
            return False
        if self.hold_time < 0:
            logger.error(f"Invalid hold time: {self.hold_time}s, must be >= 0")
            return False
        if self.tolerance <= 0:
            logger.error(f"Invalid tolerance: {self.tolerance}K, must be > 0")
            return False
        return True


@dataclass
class TemperatureProtectionConfig:
    """温度保护配置数据类。

    Attributes:
        high_temp_limit: 高温保护阈值（K）
        low_temp_limit: 低温保护阈值（K）
        max_rate_limit: 最大温度变化率（K/min）
        enable_high_temp: 启用高温保护
        enable_low_temp: 启用低温保护
        enable_rate_limit: 启用温度变化率保护
        rate_window_size: 变化率计算窗口大小（数据点数）
    """

    high_temp_limit: float = 450.0
    low_temp_limit: float = 70.0
    max_rate_limit: float = 20.0
    enable_high_temp: bool = True
    enable_low_temp: bool = True
    enable_rate_limit: bool = True
    rate_window_size: int = RATE_CALCULATION_WINDOW_SIZE

    def validate(self) -> bool:
        """验证保护参数是否有效。

        Returns:
            bool: 参数是否有效
        """
        if self.high_temp_limit <= self.low_temp_limit:
            logger.error(
                f"Invalid temperature limits: high={self.high_temp_limit}K, "
                f"low={self.low_temp_limit}K"
            )
            return False
        if self.max_rate_limit <= 0:
            logger.error(f"Invalid rate limit: {self.max_rate_limit}K/min")
            return False
        if self.rate_window_size < 2:
            logger.error(f"Invalid rate_window_size: {self.rate_window_size}, must be >= 2")
            return False
        return True


@dataclass
class TemperatureDataPoint:
    """温度数据点数据类。

    Attributes:
        timestamp: 时间戳
        temperature: 温度值（K）
        setpoint: 设定温度（K）
        output: 输出功率（%）
        mode: 控制模式
    """

    timestamp: float
    temperature: float
    setpoint: float
    output: float
    mode: str


@dataclass
class PIDState:
    """PID控制器状态数据类。

    Attributes:
        integral: 积分项累积值
        last_error: 上次误差
        last_time: 上次更新时间
        last_derivative: 上次微分项
    """

    integral: float = 0.0
    last_error: float = 0.0
    last_time: float = 0.0
    last_derivative: float = 0.0


class TemperatureController(AbstractDevice):
    """温度控制器实现类。

    实现PID闭环控制、程序控温、温度保护和温度曲线记录功能。

    Attributes:
        device_id: 设备唯一标识符
        config: 设备配置字典
        pid_params: PID控制参数
        protection_config: 温度保护配置
        current_temperature: 当前温度（K）
        current_output: 当前输出功率（%）
        mode: 控制模式
        program: 温度程序段列表
        temperature_history: 温度历史记录

    Example:
        >>> controller = TemperatureController(
        ...     device_id="temp_controller_1",
        ...     config={"simulation": True}
        ... )
        >>> await controller.connect()
        >>> await controller.set_temperature(300.0)
        >>> await controller.start_pid_control()
    """

    # 温度范围常量
    MIN_TEMPERATURE = 77.0  # K (液氮温度)
    MAX_TEMPERATURE = 400.0  # K
    TEMPERATURE_TOLERANCE = 0.1  # K

    # PID控制周期（秒）
    PID_CONTROL_INTERVAL = 1.0

    # 温度历史记录最大长度
    MAX_HISTORY_LENGTH = 10000

    def __init__(self, device_id: str, config: dict[str, Any]):
        """初始化温度控制器。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典
                - simulation: 是否仿真模式（默认True）
                - pid_params: PID参数字典（可选）
                - protection: 保护配置字典（可选）
        """
        super().__init__(device_id, config)

        # 仿真模式标志
        self.simulation_mode = config.get("simulation", True)

        # PID参数
        pid_config = config.get("pid_params", {})
        self.pid_params = PIDParameters(
            kp=pid_config.get("kp", 1.0),
            ki=pid_config.get("ki", 0.1),
            kd=pid_config.get("kd", 0.01),
            setpoint=pid_config.get("setpoint", 300.0),
            output_min=pid_config.get("output_min", 0.0),
            output_max=pid_config.get("output_max", 100.0),
            integral_limit=pid_config.get("integral_limit", 50.0),
        )

        # 温度保护配置
        protection_config = config.get("protection", {})
        self.protection_config = TemperatureProtectionConfig(
            high_temp_limit=protection_config.get("high_temp_limit", 450.0),
            low_temp_limit=protection_config.get("low_temp_limit", 70.0),
            max_rate_limit=protection_config.get("max_rate_limit", 20.0),
            enable_high_temp=protection_config.get("enable_high_temp", True),
            enable_low_temp=protection_config.get("enable_low_temp", True),
            enable_rate_limit=protection_config.get("enable_rate_limit", True),
        )

        # 当前状态
        self._current_temperature = 300.0  # K
        self._current_output = 0.0  # %
        self._mode = TemperatureControllerMode.MANUAL

        # PID控制器状态
        self._pid_state = PIDState()
        self._pid_task: asyncio.Task | None = None
        self._pid_running = False

        # 温度程序
        self._program: list[TemperatureProgramSegment] = []
        self._current_segment_index = 0
        self._segment_start_time = 0.0
        self._segment_start_temperature = 0.0
        self._program_task: asyncio.Task | None = None
        self._program_running = False

        # 温度历史记录
        self._temperature_history: list[TemperatureDataPoint] = []

        # 温度变化率计算
        self._last_temperature = 300.0
        self._last_temperature_time = time.time()
        # 滑动窗口计算温度变化率
        self._temperature_history_window: deque = deque(
            maxlen=self.protection_config.rate_window_size
        )
        self._temperature_history_window.append((time.time(), 300.0))

        # 保护触发标志
        self._protection_triggered = False
        self._protection_type: TemperatureProtectionType | None = None

        # 保护回调函数列表
        self._protection_callbacks: list[ProtectionCallback] = []

        # 多路传感器通道
        self._sensor_channels: list[SensorChannel] = [
            SensorChannel(
                channel_id=i, name=f"Sensor_{i}", is_primary=(i == 0)  # 通道0默认为主传感器
            )
            for i in range(NUM_SENSOR_CHANNELS)
        ]
        # 主传感器通道ID
        self._primary_sensor_id = 0

        logger.info(
            f"TemperatureController {device_id} initialized " f"(simulation={self.simulation_mode})"
        )

    @property
    def current_temperature(self) -> float:
        """获取当前温度。

        Returns:
            float: 当前温度（K）
        """
        return self._current_temperature

    @property
    def current_output(self) -> float:
        """获取当前输出功率。

        Returns:
            float: 当前输出功率（%）
        """
        return self._current_output

    @property
    def mode(self) -> TemperatureControllerMode:
        """获取当前控制模式。

        Returns:
            TemperatureControllerMode: 控制模式
        """
        return self._mode

    async def connect(self) -> bool:
        """建立与温度控制器的连接。

        Returns:
            bool: 连接是否成功
        """
        try:
            self.status = DeviceStatus.CONNECTING

            if self.simulation_mode:
                logger.info(f"[SIMULATION] TemperatureController {self.device_id} connected")
                self.status = DeviceStatus.READY
                return True

            # TODO: 实现真实硬件连接逻辑
            # 例如：通过串口、TCP/IP或GPIB连接温度控制器
            logger.warning("Real hardware connection not implemented yet")
            self.status = DeviceStatus.READY
            return True

        except Exception as e:
            self.status = DeviceStatus.ERROR
            self._last_error = str(e)
            logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开与温度控制器的连接。

        Returns:
            bool: 断开是否成功
        """
        # 停止所有控制任务
        await self.stop_pid_control()
        await self.stop_program()

        self.status = DeviceStatus.DISCONNECTED
        logger.info(f"TemperatureController {self.device_id} disconnected")
        return True

    async def read_status(self) -> dict[str, Any]:
        """读取设备完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典
        """
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "mode": self._mode.value,
            "current_temperature": round(self._current_temperature, 2),
            "current_output": round(self._current_output, 2),
            "setpoint": self.pid_params.setpoint,
            "pid_params": {
                "kp": self.pid_params.kp,
                "ki": self.pid_params.ki,
                "kd": self.pid_params.kd,
            },
            "protection": {
                "high_temp_limit": self.protection_config.high_temp_limit,
                "low_temp_limit": self.protection_config.low_temp_limit,
                "max_rate_limit": self.protection_config.max_rate_limit,
                "triggered": self._protection_triggered,
                "type": self._protection_type.value if self._protection_type else None,
            },
            "program": {
                "running": self._program_running,
                "current_segment": self._current_segment_index,
                "total_segments": len(self._program),
            },
            "pid_running": self._pid_running,
            "connected": self.status != DeviceStatus.DISCONNECTED,
        }

    # ==================== 温度读取与设置 ====================

    async def read_temperature(self) -> float:
        """读取当前温度。

        Returns:
            float: 当前温度（K）
        """
        if self.simulation_mode:
            # 仿真模式：模拟温度变化
            # 根据输出功率和当前温度模拟温度变化
            # 简化模型：输出功率影响温度变化率
            # 正功率（加热）：温度上升
            # 负功率（冷却）：温度下降（液氮冷却）
            # 零功率：温度向环境温度（300K）自然衰减
            ambient_temp = 300.0
            heating_rate = 0.5  # K/s per 100% output
            cooling_rate = 0.3  # K/s per -100% output (液氮冷却更快)
            natural_cooling_rate = 0.1  # K/s natural cooling

            dt = 0.1  # 时间步长（秒）

            if self._current_output > 0:
                # 加热
                delta_t = heating_rate * (self._current_output / 100.0) * dt
                self._current_temperature += delta_t
            elif self._current_output < 0:
                # 冷却（液氮）
                delta_t = cooling_rate * (abs(self._current_output) / 100.0) * dt
                self._current_temperature -= delta_t
            else:
                # 自然冷却（向环境温度趋近）
                temp_diff = ambient_temp - self._current_temperature
                delta_t = natural_cooling_rate * temp_diff * dt
                self._current_temperature += delta_t

            # 限制温度范围（使用保护阈值作为仿真边界）
            min_sim_temp = max(
                self.MIN_TEMPERATURE * 0.9, self.protection_config.low_temp_limit - 10
            )
            max_sim_temp = min(
                self.MAX_TEMPERATURE * 1.1, self.protection_config.high_temp_limit + 10
            )
            self._current_temperature = max(
                min_sim_temp, min(max_sim_temp, self._current_temperature)
            )

            logger.debug(
                f"[SIMULATION] Temperature: {self._current_temperature:.2f}K, "
                f"Output: {self._current_output:.1f}%"
            )

        # TODO: 真实硬件模式下，从硬件读取温度
        return round(self._current_temperature, 2)

    async def read_all_sensors(self) -> list[dict[str, Any]]:
        """读取所有传感器通道数据。

        Returns:
            List[Dict[str, Any]]: 所有传感器通道数据列表

        Note:
            - 主传感器数据用于控制，其他传感器用于监控
            - 自动检测传感器故障并标记
            - 主传感器故障时会记录警告
        """
        import time as time_module

        results = []
        current_time = time_module.time()
        primary_temp = None

        for channel in self._sensor_channels:
            if not channel.enabled:
                continue

            if self.simulation_mode:
                # 仿真模式：模拟多路传感器温度
                # 主传感器使用当前温度，其他传感器添加小偏差
                if channel.channel_id == self._primary_sensor_id:
                    raw_temp = self._current_temperature
                else:
                    # 其他通道模拟温度梯度（主传感器附近温度略低）
                    raw_temp = self._current_temperature - channel.channel_id * 0.5
            else:
                # 真实硬件模式：从硬件读取各通道温度
                # TODO: 实现真实硬件多路传感器读取
                raw_temp = self._current_temperature

            # 应用校准
            calibrated_temp = channel.apply_calibration(raw_temp)

            # 更新通道数据
            channel.temperature = calibrated_temp
            channel.last_update = current_time

            # 检查传感器故障
            channel.check_fault(
                min_temp=self.MIN_TEMPERATURE * 0.5, max_temp=self.MAX_TEMPERATURE * 1.5
            )

            # 记录主传感器温度
            if channel.is_primary:
                primary_temp = calibrated_temp
                if channel.fault_detected:
                    logger.warning(
                        f"Primary sensor (channel {channel.channel_id}) fault: "
                        f"{channel.fault_message}"
                    )

            results.append(
                {
                    "channel_id": channel.channel_id,
                    "name": channel.name,
                    "temperature": round(calibrated_temp, 2),
                    "enabled": channel.enabled,
                    "is_primary": channel.is_primary,
                    "last_update": current_time,
                    "fault_detected": channel.fault_detected,
                    "fault_message": channel.fault_message,
                }
            )

        # 更新当前温度（使用主传感器）
        if primary_temp is not None:
            self._current_temperature = primary_temp

        logger.debug(f"Read {len(results)} sensor channels")
        return results

    def set_primary_sensor(self, channel_id: int) -> bool:
        """设置主传感器通道。

        Args:
            channel_id: 通道ID（0-3）

        Returns:
            bool: 设置是否成功
        """
        if not 0 <= channel_id < NUM_SENSOR_CHANNELS:
            logger.error(f"Invalid channel_id: {channel_id}")
            return False

        # 清除所有通道的主传感器标志
        for channel in self._sensor_channels:
            channel.is_primary = False

        # 设置新的主传感器
        self._sensor_channels[channel_id].is_primary = True
        self._primary_sensor_id = channel_id

        logger.info(f"Primary sensor set to channel {channel_id}")
        return True

    def get_primary_sensor(self) -> SensorChannel | None:
        """获取主传感器通道。

        Returns:
            SensorChannel | None: 主传感器通道，未设置时返回None
        """
        for channel in self._sensor_channels:
            if channel.is_primary:
                return channel
        return None

    def configure_sensor_channel(
        self,
        channel_id: int,
        enabled: bool | None = None,
        name: str | None = None,
        calibration_offset: float | None = None,
        calibration_scale: float | None = None,
        is_primary: bool | None = None,
    ) -> bool:
        """配置传感器通道参数。

        Args:
            channel_id: 通道ID（0-3）
            enabled: 是否启用
            name: 通道名称
            calibration_offset: 校准偏移（K）
            calibration_scale: 校准系数
            is_primary: 是否设为主传感器

        Returns:
            bool: 配置是否成功

        Raises:
            ValueError: 通道ID无效或参数非法
        """
        if not 0 <= channel_id < NUM_SENSOR_CHANNELS:
            logger.error(f"Invalid channel_id: {channel_id}, must be 0-{NUM_SENSOR_CHANNELS - 1}")
            raise ValueError(f"Invalid channel_id: {channel_id}")

        channel = self._sensor_channels[channel_id]

        if enabled is not None:
            channel.enabled = enabled
        if name is not None:
            channel.name = name
        if calibration_offset is not None:
            channel.calibration_offset = calibration_offset
        if calibration_scale is not None:
            if calibration_scale <= 0:
                raise ValueError("calibration_scale must be positive")
            channel.calibration_scale = calibration_scale
        if is_primary is not None and is_primary:
            # 设置为主传感器
            self.set_primary_sensor(channel_id)

        logger.info(
            f"Sensor channel {channel_id} configured: "
            f"enabled={channel.enabled}, name={channel.name}, "
            f"is_primary={channel.is_primary}"
        )
        return True

    async def set_temperature(self, temperature: float) -> bool:
        """设置目标温度（手动模式）。

        Args:
            temperature: 目标温度（K）

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 温度超出范围
        """
        # 参数验证
        if not (self.MIN_TEMPERATURE <= temperature <= self.MAX_TEMPERATURE):
            logger.error(
                f"Invalid temperature: {temperature}K, "
                f"must be {self.MIN_TEMPERATURE}K-{self.MAX_TEMPERATURE}K"
            )
            raise ValueError(f"Temperature must be {self.MIN_TEMPERATURE}K-{self.MAX_TEMPERATURE}K")

        # 检查保护状态
        if self._protection_triggered:
            logger.error("Cannot set temperature: protection triggered")
            return False

        self.pid_params.setpoint = temperature
        self._mode = TemperatureControllerMode.MANUAL

        logger.info(f"Set temperature to {temperature}K (manual mode)")
        return True

    async def set_output(self, output: float) -> bool:
        """直接设置输出功率（手动模式）。

        Args:
            output: 输出功率（%），范围-100到100
                正值表示加热，负值表示冷却（液氮）

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 输出超出范围
        """
        # 参数验证（支持负值）
        if not (-100.0 <= output <= 100.0):
            logger.error(f"Invalid output: {output}%, must be -100% to 100%")
            raise ValueError("Output must be -100% to 100%")

        # 检查保护状态
        if self._protection_triggered:
            logger.error("Cannot set output: protection triggered")
            return False

        self._current_output = output
        self._mode = TemperatureControllerMode.MANUAL

        logger.info(f"Set output to {output}% (manual mode)")
        return True

    # ==================== PID控制 ====================

    def _calculate_pid_output(self, current_temp: float, dt: float) -> float:
        """计算PID控制输出。

        Args:
            current_temp: 当前温度（K）
            dt: 时间间隔（秒）

        Returns:
            float: PID控制输出（%）

        Note:
            输出可以为负值，表示冷却（如液氮流量控制）
            积分限幅采用输出范围的比例，防止积分饱和
        """
        # 计算误差
        error = self.pid_params.setpoint - current_temp

        # 比例项
        p_term = self.pid_params.kp * error

        # 积分项（带抗饱和）
        self._pid_state.integral += error * dt

        # 计算积分限幅（基于输出范围）
        if self.pid_params.integral_limit > 0:
            integral_limit = self.pid_params.integral_limit
        else:
            # 自动计算：积分限幅 = 输出范围 / Ki
            output_range = self.pid_params.output_max - self.pid_params.output_min
            integral_limit = output_range / max(self.pid_params.ki, 0.001) * 0.5

        # 积分限幅（双向）
        self._pid_state.integral = max(
            -integral_limit, min(integral_limit, self._pid_state.integral)
        )
        i_term = self.pid_params.ki * self._pid_state.integral

        # 微分项（带滤波）
        if dt > 0:
            derivative = (error - self._pid_state.last_error) / dt
            # 一阶滤波（减少高频噪声）
            alpha = 0.1
            derivative = alpha * derivative + (1 - alpha) * self._pid_state.last_derivative
        else:
            derivative = 0.0

        d_term = self.pid_params.kd * derivative

        # 更新状态
        self._pid_state.last_error = error
        self._pid_state.last_derivative = derivative

        # 计算总输出
        output = p_term + i_term + d_term

        # 输出限幅（支持负值）
        output = max(self.pid_params.output_min, min(self.pid_params.output_max, output))

        logger.debug(
            f"PID: error={error:.2f}K, P={p_term:.2f}, I={i_term:.2f}, "
            f"D={d_term:.2f}, output={output:.1f}%"
        )

        return output

    async def _pid_control_loop(self) -> None:
        """PID控制循环（异步任务）。"""
        logger.info("PID control loop started")

        self._pid_state = PIDState()  # 重置PID状态
        self._pid_state.last_time = time.time()

        while self._pid_running:
            try:
                # 读取当前温度
                current_temp = await self.read_temperature()

                # 计算时间间隔
                current_time = time.time()
                dt = current_time - self._pid_state.last_time
                self._pid_state.last_time = current_time

                # 计算PID输出
                if dt > 0:
                    output = self._calculate_pid_output(current_temp, dt)
                    self._current_output = output

                # 记录温度数据
                await self._record_temperature(current_temp)

                # 检查温度保护
                await self._check_protection(current_temp)

                # 等待下一个控制周期
                await asyncio.sleep(self.PID_CONTROL_INTERVAL)

            except asyncio.CancelledError:
                logger.info("PID control loop cancelled")
                break
            except Exception as e:
                logger.error(f"PID control loop error: {e}")
                self._last_error = str(e)
                break

        logger.info("PID control loop stopped")

    async def start_pid_control(self) -> bool:
        """启动PID控制。

        Returns:
            bool: 启动是否成功
        """
        # 检查保护状态
        if self._protection_triggered:
            logger.error("Cannot start PID control: protection triggered")
            return False

        # 验证PID参数（传入温度范围）
        if not self.pid_params.validate(self.MIN_TEMPERATURE, self.MAX_TEMPERATURE):
            return False

        # 停止程序控温
        await self.stop_program()

        # 启动PID控制循环
        self._pid_running = True
        self._mode = TemperatureControllerMode.PID
        self._pid_task = asyncio.create_task(self._pid_control_loop())

        logger.info(
            f"PID control started (setpoint={self.pid_params.setpoint}K, "
            f"Kp={self.pid_params.kp}, Ki={self.pid_params.ki}, Kd={self.pid_params.kd})"
        )
        return True

    async def stop_pid_control(self) -> bool:
        """停止PID控制。

        Returns:
            bool: 停止是否成功
        """
        if self._pid_running:
            self._pid_running = False
            if self._pid_task:
                self._pid_task.cancel()
                try:
                    await self._pid_task
                except asyncio.CancelledError:
                    pass
                self._pid_task = None

            self._current_output = 0.0
            logger.info("PID control stopped")

        return True

    async def set_pid_parameters(
        self,
        kp: float | None = None,
        ki: float | None = None,
        kd: float | None = None,
        setpoint: float | None = None,
    ) -> bool:
        """设置PID参数。

        Args:
            kp: 比例系数（可选）
            ki: 积分系数（可选）
            kd: 微分系数（可选）
            setpoint: 目标温度（可选）

        Returns:
            bool: 设置是否成功
        """
        # 更新参数
        if kp is not None:
            if not (0.1 <= kp <= 100):
                logger.error(f"Invalid Kp: {kp}")
                return False
            self.pid_params.kp = kp

        if ki is not None:
            if not (0.001 <= ki <= 10):
                logger.error(f"Invalid Ki: {ki}")
                return False
            self.pid_params.ki = ki

        if kd is not None:
            if not (0.001 <= kd <= 10):
                logger.error(f"Invalid Kd: {kd}")
                return False
            self.pid_params.kd = kd

        if setpoint is not None:
            if not (self.MIN_TEMPERATURE <= setpoint <= self.MAX_TEMPERATURE):
                logger.error(f"Invalid setpoint: {setpoint}K")
                return False
            self.pid_params.setpoint = setpoint
            # 重置积分项（避免积分饱和）
            self._pid_state.integral = 0.0

        logger.info(
            f"PID parameters updated: Kp={self.pid_params.kp}, "
            f"Ki={self.pid_params.ki}, Kd={self.pid_params.kd}, "
            f"setpoint={self.pid_params.setpoint}K"
        )
        return True

    # ==================== 程序控温 ====================

    async def load_program(self, segments: list[TemperatureProgramSegment]) -> bool:
        """加载温度程序。

        Args:
            segments: 温度程序段列表

        Returns:
            bool: 加载是否成功
        """
        # 验证所有程序段
        for i, segment in enumerate(segments):
            segment.segment_id = i
            if not segment.validate(self.MIN_TEMPERATURE, self.MAX_TEMPERATURE):
                logger.error(f"Invalid program segment {i}")
                return False

        self._program = segments
        logger.info(f"Loaded temperature program with {len(segments)} segments")
        return True

    async def _program_control_loop(self) -> None:
        """程序控温循环（异步任务）。

        Note:
            执行流程：升温段 -> 恒温段 -> 降温段
            每段支持温度跟随监控和超时保护
        """
        logger.info("Program control loop started")

        for segment_index, segment in enumerate(self._program):
            if not self._program_running:
                break

            self._current_segment_index = segment_index
            logger.info(
                f"Starting segment {segment_index}: "
                f"target={segment.target_temperature}K, "
                f"rate={segment.ramp_rate}K/min, "
                f"hold={segment.hold_time}s"
            )

            # 记录段开始时间和温度
            self._segment_start_time = time.time()
            self._segment_start_temperature = self._current_temperature

            # 升降温阶段
            await self._execute_ramp(segment)

            # 等待温度稳定
            if self._program_running:
                await self._wait_temperature_stable(
                    segment.target_temperature, segment.tolerance, timeout=30.0  # 最多等待30秒稳定
                )

            # 恒温阶段
            if segment.hold_time > 0 and self._program_running:
                logger.info(f"Holding at {segment.target_temperature}K for {segment.hold_time}s")

                # 确保PID控制运行
                if not self._pid_running:
                    await self.start_pid_control()

                # 分段等待，支持中途停止
                hold_elapsed = 0.0
                hold_interval = 1.0  # 每秒检查一次
                while hold_elapsed < segment.hold_time and self._program_running:
                    await asyncio.sleep(hold_interval)
                    hold_elapsed += hold_interval

                    # 恒温期间监控温度偏差
                    temp_error = abs(self._current_temperature - segment.target_temperature)
                    if temp_error > segment.tolerance:
                        logger.warning(
                            f"Hold temperature deviation: "
                            f"target={segment.target_temperature:.1f}K, "
                            f"actual={self._current_temperature:.1f}K, "
                            f"error={temp_error:.2f}K"
                        )

        # 程序完成
        self._program_running = False
        self._current_segment_index = 0
        logger.info("Program control completed")

    async def _wait_temperature_stable(
        self, target_temp: float, tolerance: float, timeout: float = 30.0
    ) -> bool:
        """等待温度稳定在目标值附近。

        Args:
            target_temp: 目标温度（K）
            tolerance: 容差（K）
            timeout: 超时时间（秒）

        Returns:
            bool: 是否成功稳定
        """
        start_time = time.time()
        stable_count = 0
        required_stable_count = 3  # 连续3次在容差内才算稳定

        while self._program_running:
            elapsed = time.time() - start_time

            # 超时检查
            if elapsed > timeout:
                logger.warning(
                    f"Temperature stabilization timeout ({timeout}s), "
                    f"current={self._current_temperature:.1f}K, target={target_temp:.1f}K"
                )
                return False

            # 检查温度是否在容差内
            temp_error = abs(self._current_temperature - target_temp)
            if temp_error <= tolerance:
                stable_count += 1
                if stable_count >= required_stable_count:
                    logger.info(
                        f"Temperature stabilized at {self._current_temperature:.1f}K "
                        f"(target={target_temp:.1f}K, tolerance={tolerance}K)"
                    )
                    return True
            else:
                stable_count = 0  # 重置计数

            await asyncio.sleep(1.0)

        return False

    async def _execute_ramp(self, segment: TemperatureProgramSegment) -> None:
        """执行升降温段。

        Args:
            segment: 程序段

        Note:
            支持温度跟随监控，当实际温度偏离设定温度超过容差时会记录警告
            支持超时保护，超时后强制进入下一段
        """
        target_temp = segment.target_temperature
        ramp_rate = segment.ramp_rate  # K/min
        current_temp = self._current_temperature

        # 计算温度变化方向
        temp_diff = target_temp - current_temp

        # 如果温度变化方向与速率符号不一致，调整速率
        if (temp_diff > 0 and ramp_rate < 0) or (temp_diff < 0 and ramp_rate > 0):
            ramp_rate = -ramp_rate

        # 计算预计时间
        if abs(ramp_rate) > 0:
            estimated_time = abs(temp_diff / ramp_rate) * 60  # 转换为秒
        else:
            estimated_time = 0

        logger.info(
            f"Ramping from {current_temp:.1f}K to {target_temp:.1f}K "
            f"at {ramp_rate:.1f}K/min (estimated {estimated_time:.1f}s)"
        )

        # 启动PID控制，动态调整设定点
        self._mode = TemperatureControllerMode.PROGRAM

        start_time = time.time()
        last_follow_check_time = start_time
        follow_check_interval = 5.0  # 每5秒检查一次温度跟随情况

        while self._program_running:
            elapsed_time = time.time() - start_time

            # 超时检查
            if segment.timeout > 0 and elapsed_time > segment.timeout:
                logger.warning(
                    f"Segment timeout ({segment.timeout}s) reached, " f"moving to next segment"
                )
                break

            # 计算当前设定温度
            if abs(ramp_rate) > 0:
                temp_change = ramp_rate * (elapsed_time / 60.0)  # K
                current_setpoint = self._segment_start_temperature + temp_change
            else:
                # 零速率：立即跳转到目标温度
                current_setpoint = target_temp

            # 检查是否到达目标温度
            if (ramp_rate > 0 and current_setpoint >= target_temp) or (ramp_rate < 0 and current_setpoint <= target_temp):
                current_setpoint = target_temp
                break
            elif abs(ramp_rate) < 0.001:
                # 零速率模式：直接设置目标温度
                current_setpoint = target_temp
                break

            # 更新PID设定点
            self.pid_params.setpoint = current_setpoint

            # 如果PID控制未运行，启动它
            if not self._pid_running:
                await self.start_pid_control()

            # 温度跟随监控
            if time.time() - last_follow_check_time > follow_check_interval:
                temp_error = abs(self._current_temperature - current_setpoint)
                if temp_error > segment.tolerance:
                    logger.warning(
                        f"Temperature following deviation: "
                        f"setpoint={current_setpoint:.1f}K, "
                        f"actual={self._current_temperature:.1f}K, "
                        f"error={temp_error:.2f}K > tolerance={segment.tolerance}K"
                    )
                last_follow_check_time = time.time()

            # 等待
            await asyncio.sleep(1.0)

        # 确保到达目标温度
        self.pid_params.setpoint = target_temp

    async def start_program(self) -> bool:
        """启动程序控温。

        Returns:
            bool: 启动是否成功
        """
        # 检查保护状态
        if self._protection_triggered:
            logger.error("Cannot start program: protection triggered")
            return False

        # 检查程序是否已加载
        if not self._program:
            logger.error("No program loaded")
            return False

        # 停止PID控制（如果正在运行）
        await self.stop_pid_control()

        # 启动程序控温循环
        self._program_running = True
        self._current_segment_index = 0
        self._program_task = asyncio.create_task(self._program_control_loop())

        logger.info(f"Program control started ({len(self._program)} segments)")
        return True

    async def stop_program(self) -> bool:
        """停止程序控温。

        Returns:
            bool: 停止是否成功
        """
        if self._program_running:
            self._program_running = False
            if self._program_task:
                self._program_task.cancel()
                try:
                    await self._program_task
                except asyncio.CancelledError:
                    pass
                self._program_task = None

            # 同时停止PID控制
            await self.stop_pid_control()

            logger.info("Program control stopped")

        return True

    async def get_program_status(self) -> dict[str, Any]:
        """获取程序控温状态。

        Returns:
            Dict[str, Any]: 程序状态信息
        """
        return {
            "running": self._program_running,
            "current_segment": self._current_segment_index,
            "total_segments": len(self._program),
            "program": [
                {
                    "segment_id": seg.segment_id,
                    "target_temperature": seg.target_temperature,
                    "ramp_rate": seg.ramp_rate,
                    "hold_time": seg.hold_time,
                }
                for seg in self._program
            ],
        }

    # ==================== 温度保护 ====================

    def add_protection_callback(self, callback: ProtectionCallback) -> None:
        """添加保护触发回调函数。

        Args:
            callback: 回调函数，签名：callback(protection_type, current_temp, threshold)
        """
        self._protection_callbacks.append(callback)
        logger.info(f"Protection callback added: {callback.__name__}")

    def remove_protection_callback(self, callback: ProtectionCallback) -> None:
        """移除保护触发回调函数。

        Args:
            callback: 要移除的回调函数
        """
        if callback in self._protection_callbacks:
            self._protection_callbacks.remove(callback)
            logger.info(f"Protection callback removed: {callback.__name__}")

    def _calculate_temperature_rate(self, current_temp: float) -> float:
        """使用滑动窗口计算温度变化率。

        Args:
            current_temp: 当前温度（K）

        Returns:
            float: 温度变化率（K/min），正值表示升温，负值表示降温
        """
        current_time = time.time()

        # 添加当前数据点到窗口
        self._temperature_history_window.append((current_time, current_temp))

        # 需要至少2个数据点才能计算变化率
        if len(self._temperature_history_window) < 2:
            return 0.0

        # 使用窗口内所有数据点计算平均变化率（线性拟合）
        times = [t for t, _ in self._temperature_history_window]
        temps = [temp for _, temp in self._temperature_history_window]

        # 计算时间跨度
        time_span = times[-1] - times[0]
        if time_span < 0.1:  # 时间跨度太小，返回0
            return 0.0

        # 简单线性拟合：rate = (T_end - T_start) / time_span
        rate = (temps[-1] - temps[0]) / time_span * 60.0  # K/min

        return rate

    async def _check_protection(self, current_temp: float) -> bool:
        """检查温度保护。

        Args:
            current_temp: 当前温度（K）

        Returns:
            bool: 是否触发保护

        Note:
            使用滑动窗口计算温度变化率，避免瞬时波动误触发
        """
        # 计算温度变化率（使用滑动窗口）
        rate = self._calculate_temperature_rate(current_temp)

        # 检查温度变化率保护
        if (
            self.protection_config.enable_rate_limit
            and abs(rate) > self.protection_config.max_rate_limit
        ):
            await self._trigger_protection(
                TemperatureProtectionType.RATE_LIMIT,
                current_temp,
                self.protection_config.max_rate_limit,
            )
            return True

        # 检查高温保护
        if (
            self.protection_config.enable_high_temp
            and current_temp > self.protection_config.high_temp_limit
        ):
            await self._trigger_protection(
                TemperatureProtectionType.HIGH_TEMP,
                current_temp,
                self.protection_config.high_temp_limit,
            )
            return True

        # 检查低温保护
        if (
            self.protection_config.enable_low_temp
            and current_temp < self.protection_config.low_temp_limit
        ):
            await self._trigger_protection(
                TemperatureProtectionType.LOW_TEMP,
                current_temp,
                self.protection_config.low_temp_limit,
            )
            return True

        return False

    async def _trigger_protection(
        self, protection_type: TemperatureProtectionType, current_temp: float, threshold: float
    ) -> None:
        """触发温度保护。

        Args:
            protection_type: 保护类型
            current_temp: 当前温度（K）
            threshold: 触发阈值
        """
        self._protection_triggered = True
        self._protection_type = protection_type

        # 停止所有控制
        await self.stop_pid_control()
        await self.stop_program()

        # 设置输出为0
        self._current_output = 0.0

        # 设置设备状态为错误
        self.status = DeviceStatus.ERROR

        logger.error(
            f"Temperature protection triggered: {protection_type.value}, "
            f"current_temp={current_temp:.2f}K, threshold={threshold:.2f}"
        )

        # 调用所有注册的回调函数
        for callback in self._protection_callbacks:
            try:
                callback(protection_type, current_temp, threshold)
            except Exception as e:
                logger.error(f"Protection callback error: {e}")

    async def clear_protection(self) -> bool:
        """清除温度保护状态。

        Returns:
            bool: 清除是否成功
        """
        if not self._protection_triggered:
            return True

        # 检查当前温度是否在安全范围内
        if not (
            self.protection_config.low_temp_limit
            < self._current_temperature
            < self.protection_config.high_temp_limit
        ):
            logger.error("Cannot clear protection: temperature still out of range")
            return False

        self._protection_triggered = False
        self._protection_type = None
        self.status = DeviceStatus.READY

        logger.info("Temperature protection cleared")
        return True

    async def set_protection_config(
        self,
        high_temp_limit: float | None = None,
        low_temp_limit: float | None = None,
        max_rate_limit: float | None = None,
        enable_high_temp: bool | None = None,
        enable_low_temp: bool | None = None,
        enable_rate_limit: bool | None = None,
    ) -> bool:
        """设置温度保护配置。

        Args:
            high_temp_limit: 高温保护阈值（可选）
            low_temp_limit: 低温保护阈值（可选）
            max_rate_limit: 最大温度变化率（可选）
            enable_high_temp: 启用高温保护（可选）
            enable_low_temp: 启用低温保护（可选）
            enable_rate_limit: 启用温度变化率保护（可选）

        Returns:
            bool: 设置是否成功
        """
        # 更新配置
        if high_temp_limit is not None:
            self.protection_config.high_temp_limit = high_temp_limit

        if low_temp_limit is not None:
            self.protection_config.low_temp_limit = low_temp_limit

        if max_rate_limit is not None:
            self.protection_config.max_rate_limit = max_rate_limit

        if enable_high_temp is not None:
            self.protection_config.enable_high_temp = enable_high_temp

        if enable_low_temp is not None:
            self.protection_config.enable_low_temp = enable_low_temp

        if enable_rate_limit is not None:
            self.protection_config.enable_rate_limit = enable_rate_limit

        # 验证配置
        if not self.protection_config.validate():
            return False

        logger.info(
            f"Protection config updated: "
            f"high={self.protection_config.high_temp_limit}K, "
            f"low={self.protection_config.low_temp_limit}K, "
            f"rate={self.protection_config.max_rate_limit}K/min"
        )
        return True

    # ==================== 温度曲线记录 ====================

    async def _record_temperature(self, temperature: float) -> None:
        """记录温度数据点。

        Args:
            temperature: 当前温度（K）
        """
        data_point = TemperatureDataPoint(
            timestamp=time.time(),
            temperature=temperature,
            setpoint=self.pid_params.setpoint,
            output=self._current_output,
            mode=self._mode.value,
        )

        self._temperature_history.append(data_point)

        # 限制历史记录长度
        if len(self._temperature_history) > self.MAX_HISTORY_LENGTH:
            self._temperature_history = self._temperature_history[-self.MAX_HISTORY_LENGTH :]

    async def get_temperature_history(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """获取温度历史记录。

        Args:
            start_time: 起始时间戳（可选）
            end_time: 结束时间戳（可选）
            limit: 返回记录数量限制（可选）

        Returns:
            List[Dict[str, Any]]: 温度历史记录列表
        """
        history = self._temperature_history

        # 时间过滤
        if start_time is not None:
            history = [dp for dp in history if dp.timestamp >= start_time]

        if end_time is not None:
            history = [dp for dp in history if dp.timestamp <= end_time]

        # 数量限制
        if limit is not None and len(history) > limit:
            history = history[-limit:]

        # 转换为字典列表
        return [
            {
                "timestamp": dp.timestamp,
                "datetime": datetime.fromtimestamp(dp.timestamp).isoformat(),
                "temperature": dp.temperature,
                "setpoint": dp.setpoint,
                "output": dp.output,
                "mode": dp.mode,
            }
            for dp in history
        ]

    async def clear_temperature_history(self) -> None:
        """清除温度历史记录。"""
        self._temperature_history.clear()
        logger.info("Temperature history cleared")

    async def export_temperature_history(self, format: str = "csv") -> str:
        """导出温度历史记录。

        Args:
            format: 导出格式（csv或json）

        Returns:
            str: 导出的数据字符串

        Raises:
            ValueError: 不支持的格式
        """
        if format == "csv":
            lines = ["timestamp,datetime,temperature,setpoint,output,mode"]
            for dp in self._temperature_history:
                dt_str = datetime.fromtimestamp(dp.timestamp).isoformat()
                lines.append(
                    f"{dp.timestamp},{dt_str},{dp.temperature},"
                    f"{dp.setpoint},{dp.output},{dp.mode}"
                )
            return "\n".join(lines)

        elif format == "json":
            import json

            data = await self.get_temperature_history()
            return json.dumps(data, indent=2)

        else:
            raise ValueError(f"Unsupported format: {format}")

    # ==================== 急停与复位 ====================

    async def emergency_stop(self) -> bool:
        """紧急停止。

        Returns:
            bool: 是否成功
        """
        logger.warning("EMERGENCY STOP triggered!")

        # 停止所有控制
        await self.stop_pid_control()
        await self.stop_program()

        # 设置输出为0
        self._current_output = 0.0

        # 设置设备状态
        self.status = DeviceStatus.EMERGENCY_STOP

        return True

    async def reset_emergency(self) -> bool:
        """复位急停状态。

        Returns:
            bool: 是否成功
        """
        if self.status == DeviceStatus.EMERGENCY_STOP:
            self.status = DeviceStatus.READY
            logger.info("Emergency stop reset")
        return True
