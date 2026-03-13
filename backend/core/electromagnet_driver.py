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
"""

import asyncio
import logging
import random
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
from typing import Any

from .abstract import AbstractDevice, DeviceStatus

logger = logging.getLogger(__name__)


# 技术规范常量
MAX_CURRENT = 10.0  # 最大电流（A）
MIN_CURRENT = 0.0  # 最小电流（A）
CURRENT_PRECISION = 0.001  # 电流精度（A），±0.1%
MAX_FIELD = 2.0  # 最大磁场（T）
MIN_SCAN_RATE = 0.01  # 最小扫描速率（A/s）
MAX_SCAN_RATE = 1.0  # 最大扫描速率（A/s）
OVERCURRENT_THRESHOLD = 10.5  # 过流保护阈值（A）
MAX_TEMPERATURE = 80.0  # 过温保护阈值（°C）


class ScanMode(Enum):
    """扫描模式枚举。

    Attributes:
        FORWARD: 正向扫描（从起始电流到目标电流）
        REVERSE: 反向扫描（从起始电流到目标电流）
        TRIANGULAR: 三角波扫描（往返扫描）
    """

    FORWARD = "forward"
    REVERSE = "reverse"
    TRIANGULAR = "triangular"


class ElectromagnetStatus(Enum):
    """电磁铁状态枚举。

    Attributes:
        IDLE: 空闲状态
        CONSTANT_CURRENT: 恒流模式运行中
        SCANNING: 扫描模式运行中
        OVERCURRENT: 过流保护触发
        OVERTEMPERATURE: 过温保护触发
        CALIBRATING: 校准中
    """

    IDLE = "idle"
    CONSTANT_CURRENT = "constant_current"
    SCANNING = "scanning"
    OVERCURRENT = "overcurrent"
    OVERTEMPERATURE = "overtemperature"
    CALIBRATING = "calibrating"


@dataclass
class CalibrationPoint:
    """校准点数据类。

    Attributes:
        current: 电流值（A）
        field: 磁场值（T）
    """

    current: float
    field: float


@dataclass
class ScanParameters:
    """
    扫描参数数据类。

    Attributes:
        mode: 扫描模式
        start_current: 起始电流（A）
        end_current: 目标电流（A）
        scan_rate: 扫描速率（A/s）
        cycles: 扫描周期数（仅三角波模式有效）
        step_interval_ms: 步进间隔（毫秒），可选参数
    """

    mode: ScanMode
    start_current: float
    end_current: float
    scan_rate: float
    cycles: int = 1
    step_interval_ms: float | None = None


class ElectromagnetDriver(AbstractDevice):
    """
    电磁铁驱动器实现类。

    提供恒流控制、扫描控制和磁场校准功能。
    支持仿真模式和真实硬件模式。

    安全警告：
    - 实验时必须有人值守
    - 首次使用前验证电流限制参数
    - 过流保护触发后需手动复位
    """

    def __init__(self, device_id: str, config: dict[str, Any]):
        """
        初始化电磁铁驱动器。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典
                - port: 通信端口（默认 "COM3"）
                - baudrate: 波特率（默认 9600）
                - max_current: 最大电流限制（默认 10.0A）
                - calibration_points: 校准点列表（可选）
                - simulation: 是否仿真模式（默认 True）
        """
        super().__init__(device_id, config)

        # 通信配置
        self.port = config.get("port", "COM3")
        self.baudrate = config.get("baudrate", 9600)
        self.simulation = config.get("simulation", True)

        # 电流限制
        self.max_current_limit = min(config.get("max_current", MAX_CURRENT), MAX_CURRENT)

        # 状态变量
        self._current_value = 0.0
        self._field_value = 0.0
        self._current_temperature = 25.0  # 当前温度（°C），默认室温
        self._electromagnet_status = ElectromagnetStatus.IDLE
        self._scan_task: asyncio.Task | None = None
        self._scan_progress = 0.0
        self._scan_cancelled = False

        # 保护监控任务
        self._protection_monitor_task: asyncio.Task | None = None
        self._protection_monitor_interval = 0.5  # 监控间隔（秒）

        # 校准数据
        self._calibration_points: list[CalibrationPoint] = []
        self._calibration_coefficient = 0.2  # 默认校准系数（T/A），斜率
        self._calibration_intercept = 0.0  # 校准截距（T），用于零点偏移修正

        # 加载校准点
        calibration_data = config.get("calibration_points", [])
        for point in calibration_data:
            if isinstance(point, dict):
                self._calibration_points.append(
                    CalibrationPoint(
                        current=point.get("current", 0.0), field=point.get("field", 0.0)
                    )
                )

        # 回调函数
        self._status_callback: Callable[[dict[str, Any]], None] | None = None
        self._progress_callback: Callable[[float], None] | None = None

        logger.info(
            f"ElectromagnetDriver {device_id} initialized "
            f"(port={self.port}, max_current={self.max_current_limit}A, "
            f"simulation={self.simulation})"
        )

    @property
    def current_value(self) -> float:
        """获取当前电流值（A）。"""
        return self._current_value

    @property
    def field_value(self) -> float:
        """获取当前磁场值（T）。"""
        return self._field_value

    @property
    def electromagnet_status(self) -> ElectromagnetStatus:
        """获取电磁铁状态。"""
        return self._electromagnet_status

    @property
    def current_temperature(self) -> float:
        """获取当前温度（°C）。"""
        return self._current_temperature

    @property
    def scan_progress(self) -> float:
        """获取扫描进度（0-1）。"""
        return self._scan_progress

    def set_status_callback(self, callback: Callable[[dict[str, Any]], None] | None) -> None:
        """
        设置状态回调函数。

        Args:
            callback: 回调函数，接收状态字典
        """
        self._status_callback = callback

    def set_progress_callback(self, callback: Callable[[float], None] | None) -> None:
        """
        设置进度回调函数。

        Args:
            callback: 回调函数，接收进度值（0-1）
        """
        self._progress_callback = callback

    async def connect(self) -> bool:
        """
        建立与设备的连接。

        Returns:
            bool: 连接是否成功
        """
        try:
            self.status = DeviceStatus.CONNECTING

            if self.simulation:
                self.status = DeviceStatus.READY
                self._electromagnet_status = ElectromagnetStatus.IDLE
                # 启动保护监控
                self._start_protection_monitor()
                logger.info(f"ElectromagnetDriver {self.device_id} connected (simulation mode)")
                return True

            # 真实硬件连接逻辑（待实现）
            # TODO: 实现真实硬件通信协议
            logger.warning("Real hardware mode not implemented, falling back to simulation")
            self.simulation = True
            self.status = DeviceStatus.READY
            # 启动保护监控
            self._start_protection_monitor()
            return True

        except Exception as e:
            self.status = DeviceStatus.ERROR
            self._last_error = str(e)
            logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        """
        断开与设备的连接。

        Returns:
            bool: 断开是否成功
        """
        # 停止保护监控
        self._stop_protection_monitor()

        # 停止正在进行的扫描
        if self._scan_task and not self._scan_task.done():
            self._scan_cancelled = True
            try:
                await asyncio.wait_for(self._scan_task, timeout=5.0)
            except TimeoutError:
                self._scan_task.cancel()

        # 将电流归零
        await self._set_current_internal(0.0)

        self.status = DeviceStatus.DISCONNECTED
        self._electromagnet_status = ElectromagnetStatus.IDLE
        logger.info(f"ElectromagnetDriver {self.device_id} disconnected")
        return True

    async def read_status(self) -> dict[str, Any]:
        """
        读取设备完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典
        """
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "electromagnet_status": self._electromagnet_status.value,
            "current_value": round(self._current_value, 4),
            "field_value": round(self._field_value, 4),
            "current_temperature": round(self._current_temperature, 2),
            "max_current_limit": self.max_current_limit,
            "scan_progress": round(self._scan_progress, 4),
            "calibration_points_count": len(self._calibration_points),
            "calibration_coefficient": round(self._calibration_coefficient, 4),
            "calibration_intercept": round(self._calibration_intercept, 4),
            "connected": self.status != DeviceStatus.DISCONNECTED,
            "simulation": self.simulation,
        }

    # ==================== 恒流模式控制 ====================

    async def set_current(self, current: float) -> bool:
        """
        设置恒流模式电流值。

        Args:
            current: 目标电流值（A），范围：0-10A

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 电流值超出范围
        """
        # 参数校验
        if not self._validate_current(current):
            raise ValueError(
                f"Current {current}A exceeds valid range "
                f"[{MIN_CURRENT}, {self.max_current_limit}]A"
            )

        # 检查设备状态
        if self.status != DeviceStatus.READY:
            logger.error(f"Device not ready, current status: {self.status.value}")
            return False

        # 停止正在进行的扫描
        if self._electromagnet_status == ElectromagnetStatus.SCANNING:
            await self.stop_scan()

        try:
            self.status = DeviceStatus.BUSY
            self._electromagnet_status = ElectromagnetStatus.CONSTANT_CURRENT

            # 设置电流
            success = await self._set_current_internal(current)

            if success:
                logger.info(f"Current set to {current}A (constant mode)")
                self._notify_status_change()
                return True
            else:
                self._electromagnet_status = ElectromagnetStatus.IDLE
                return False

        except Exception as e:
            logger.error(f"Set current error: {e}")
            self._last_error = str(e)
            self._electromagnet_status = ElectromagnetStatus.IDLE
            return False
        finally:
            self.status = DeviceStatus.READY

    async def _set_current_internal(self, current: float) -> bool:
        """
        内部方法：设置电流值（不改变状态）。

        Args:
            current: 目标电流值（A）

        Returns:
            bool: 设置是否成功
        """
        # 过流检查（严格检查，超过阈值立即触发）
        if current > OVERCURRENT_THRESHOLD:
            await self._trigger_overcurrent_protection(current)
            return False

        # 过温检查（温度过高时拒绝设置电流）
        if self._current_temperature > MAX_TEMPERATURE:
            logger.error(
                f"Cannot set current: temperature too high "
                f"({self._current_temperature:.1f}°C > {MAX_TEMPERATURE}°C)"
            )
            await self._trigger_overtemperature_protection()
            return False

        if self.simulation:
            # 仿真模式：直接设置值
            self._current_value = current
            self._field_value = self._current_to_field(current)
            # 注意：温度由保护监控循环更新，此处不再更新
            return True

        # 真实硬件模式（待实现）
        # TODO: 实现真实硬件通信协议
        self._current_value = current
        self._field_value = self._current_to_field(current)
        return True

    # ==================== 扫描模式控制 ====================

    async def start_scan(
        self,
        mode: ScanMode,
        start_current: float,
        end_current: float,
        scan_rate: float,
        cycles: int = 1,
        step_interval_ms: float | None = None,
    ) -> bool:
        """
        启动扫描模式。

        Args:
            mode: 扫描模式（正向/反向/三角波）
            start_current: 起始电流（A）
            end_current: 目标电流（A）
            scan_rate: 扫描速率（A/s），范围：0.01-1 A/s
            cycles: 扫描周期数（仅三角波模式有效），默认为1
            step_interval_ms: 步进间隔（毫秒），可选参数用于精细控制。默认自动计算

        Returns:
            bool: 启动是否成功

        Raises:
            ValueError: 参数无效
        """
        # 参数校验：电流范围
        if not self._validate_current(start_current):
            raise ValueError(
                f"Start current {start_current}A exceeds valid range "
                f"[{MIN_CURRENT}, {self.max_current_limit}]A"
            )

        if not self._validate_current(end_current):
            raise ValueError(
                f"End current {end_current}A exceeds valid range "
                f"[{MIN_CURRENT}, {self.max_current_limit}]A"
            )

        # 参数校验：扫描速率
        if not MIN_SCAN_RATE <= scan_rate <= MAX_SCAN_RATE:
            raise ValueError(
                f"Scan rate {scan_rate}A/s exceeds valid range "
                f"[{MIN_SCAN_RATE}, {MAX_SCAN_RATE}]A/s"
            )

        # 参数校验：周期数
        if mode == ScanMode.TRIANGULAR:
            if cycles < 1:
                raise ValueError("Cycles must be at least 1 for triangular mode")
            if cycles > 100:
                logger.warning(f"Large cycle count ({cycles}) may cause long scan duration")

        # 参数校验：步进间隔
        if step_interval_ms is not None:
            if step_interval_ms < 1.0:
                raise ValueError(f"Step interval {step_interval_ms}ms is below minimum 1ms")
            if step_interval_ms > 1000.0:
                raise ValueError(f"Step interval {step_interval_ms}ms exceeds maximum 1000ms")

        # 参数校验：扫描时间预估（防止过长时间）
        estimated_duration = self._estimate_scan_duration(
            mode, start_current, end_current, scan_rate, cycles
        )
        max_duration = 3600 * 24  # 24小时上限
        if estimated_duration > max_duration:
            raise ValueError(
                f"Estimated scan duration ({estimated_duration:.1f}s = "
                f"{estimated_duration/3600:.1f}h) exceeds maximum allowed "
                f"({max_duration/3600:.1f}h)"
            )

        # 参数校验：防止无效扫描（起始=目标且非三角波）
        if mode != ScanMode.TRIANGULAR and abs(start_current - end_current) < 0.001:
            raise ValueError(
                f"Start and end currents are too close ({start_current}A vs "
                f"{end_current}A), scan would be ineffective"
            )

        # 检查设备状态
        if self.status != DeviceStatus.READY:
            logger.error(f"Device not ready, current status: {self.status.value}")
            return False

        # 检查保护状态
        if self._electromagnet_status in (
            ElectromagnetStatus.OVERCURRENT,
            ElectromagnetStatus.OVERTEMPERATURE,
        ):
            logger.error(
                f"Cannot start scan: protection triggered " f"({self._electromagnet_status.value})"
            )
            return False

        # 停止正在进行的扫描
        if self._electromagnet_status == ElectromagnetStatus.SCANNING:
            await self.stop_scan()

        try:
            self.status = DeviceStatus.BUSY
            self._electromagnet_status = ElectromagnetStatus.SCANNING
            self._scan_cancelled = False
            self._scan_progress = 0.0

            # 创建扫描参数
            params = ScanParameters(
                mode=mode,
                start_current=start_current,
                end_current=end_current,
                scan_rate=scan_rate,
                cycles=cycles,
                step_interval_ms=step_interval_ms,
            )

            # 启动扫描任务
            self._scan_task = asyncio.create_task(self._execute_scan(params))

            logger.info(
                f"Scan started: mode={mode.value}, "
                f"start={start_current}A, end={end_current}A, "
                f"rate={scan_rate}A/s, cycles={cycles}, "
                f"step_interval={step_interval_ms}ms, "
                f"estimated_duration={estimated_duration:.1f}s"
            )
            self._notify_status_change()
            return True

        except Exception as e:
            logger.error(f"Start scan error: {e}")
            self._last_error = str(e)
            self._electromagnet_status = ElectromagnetStatus.IDLE
            self.status = DeviceStatus.READY
            return False

    def _estimate_scan_duration(
        self,
        mode: ScanMode,
        start_current: float,
        end_current: float,
        scan_rate: float,
        cycles: int,
    ) -> float:
        """
        估算扫描持续时间。

        Args:
            mode: 扫描模式
            start_current: 起始电流（A）
            end_current: 目标电流（A）
            scan_rate: 扫描速率（A/s）
            cycles: 扫描周期数

        Returns:
            float: 预估持续时间（秒）
        """
        delta = abs(end_current - start_current)
        single_scan_time = delta / scan_rate if scan_rate > 0 else 0

        if mode == ScanMode.TRIANGULAR:
            # 三角波：往返扫描，每个周期2次
            return single_scan_time * 2 * cycles
        else:
            # 正向/反向：单次扫描
            return single_scan_time

    async def stop_scan(self) -> bool:
        """
        停止扫描模式。

        Returns:
            bool: 停止是否成功
        """
        if self._electromagnet_status != ElectromagnetStatus.SCANNING:
            logger.warning("No scan in progress")
            return True

        self._scan_cancelled = True

        # 等待扫描任务结束
        if self._scan_task and not self._scan_task.done():
            try:
                await asyncio.wait_for(self._scan_task, timeout=5.0)
            except TimeoutError:
                self._scan_task.cancel()
                logger.warning("Scan task cancelled due to timeout")

        self._electromagnet_status = ElectromagnetStatus.IDLE
        self.status = DeviceStatus.READY
        logger.info("Scan stopped")
        self._notify_status_change()
        return True

    async def _execute_scan(self, params: ScanParameters) -> None:
        """
        执行扫描任务。

        Args:
            params: 扫描参数
        """
        try:
            if params.mode == ScanMode.FORWARD:
                await self._execute_forward_scan(params)
            elif params.mode == ScanMode.REVERSE:
                await self._execute_reverse_scan(params)
            elif params.mode == ScanMode.TRIANGULAR:
                await self._execute_triangular_scan(params)

        except asyncio.CancelledError:
            logger.info("Scan task cancelled")
        except Exception as e:
            logger.error(f"Scan execution error: {e}")
            self._last_error = str(e)
        finally:
            if not self._scan_cancelled:
                self._electromagnet_status = ElectromagnetStatus.IDLE
                self.status = DeviceStatus.READY
                self._scan_progress = 1.0
                self._notify_status_change()

    async def _execute_forward_scan(self, params: ScanParameters) -> None:
        """
        执行正向扫描。

        正向扫描：电流从低值增加到高值。
        如果参数顺序错误，自动调整方向。

        Args:
            params: 扫描参数
        """
        # 自动调整扫描方向：确保从小到大扫描
        start = min(params.start_current, params.end_current)
        end = max(params.start_current, params.end_current)

        if start != params.start_current:
            logger.warning(f"Forward scan auto-adjusted: start={params.start_current}A -> {start}A")

        await self._ramp_current(
            start=start,
            end=end,
            rate=params.scan_rate,
            step_interval_ms=params.step_interval_ms,
        )

    async def _execute_reverse_scan(self, params: ScanParameters) -> None:
        """
        执行反向扫描。

        反向扫描：电流从高值减少到低值。
        如果参数顺序错误，自动调整方向。

        Args:
            params: 扫描参数
        """
        # 自动调整扫描方向：确保从大到小扫描
        start = max(params.start_current, params.end_current)
        end = min(params.start_current, params.end_current)

        if start != params.start_current:
            logger.warning(f"Reverse scan auto-adjusted: start={params.start_current}A -> {start}A")

        await self._ramp_current(
            start=start,
            end=end,
            rate=params.scan_rate,
            step_interval_ms=params.step_interval_ms,
        )

    async def _execute_triangular_scan(self, params: ScanParameters) -> None:
        """
        执行三角波扫描。

        三角波扫描：从起始电流扫描到目标电流，再返回起始电流。
        自动确定扫描方向，支持任意起始/目标电流组合。

        Args:
            params: 扫描参数
        """
        # 确定扫描方向
        low_current = min(params.start_current, params.end_current)
        high_current = max(params.start_current, params.end_current)

        for cycle in range(params.cycles):
            if self._scan_cancelled:
                break

            logger.info(f"Triangular scan cycle {cycle + 1}/{params.cycles}")

            # 第一阶段：从起始电流扫描到目标电流
            await self._ramp_current(
                start=params.start_current,
                end=params.end_current,
                rate=params.scan_rate,
                cycle_progress=(cycle, params.cycles, 0.0, 0.5),
                step_interval_ms=params.step_interval_ms,
            )

            if self._scan_cancelled:
                break

            # 第二阶段：从目标电流返回起始电流
            await self._ramp_current(
                start=params.end_current,
                end=params.start_current,
                rate=params.scan_rate,
                cycle_progress=(cycle, params.cycles, 0.5, 1.0),
                step_interval_ms=params.step_interval_ms,
            )

    async def _ramp_current(
        self,
        start: float,
        end: float,
        rate: float,
        cycle_progress: tuple[int, int, float, float] | None = None,
        step_interval_ms: float | None = None,
    ) -> None:
        """
        斜坡电流变化。

        Args:
            start: 起始电流（A）
            end: 目标电流（A）
            rate: 变化速率（A/s）
            cycle_progress: 周期进度信息（周期索引，总周期，起始进度，结束进度）
            step_interval_ms: 步进间隔（毫秒），可选参数用于精细控制
        """
        delta = end - start

        # 边界检查：如果起始和目标相同，直接返回
        if abs(delta) < 1e-6:
            logger.debug(f"Ramp skipped: start={start}A equals end={end}A")
            return

        # 计算持续时间（秒）
        duration = abs(delta) / rate

        # 计算步进间隔
        if step_interval_ms is not None:
            # 使用指定的步进间隔
            step_interval = step_interval_ms / 1000.0
            steps = int(duration / step_interval)
        else:
            # 自动计算步数（100步/秒，最少1步）
            steps = max(1, int(duration * 100))
            # 计算步进间隔（秒）
            step_interval = duration / steps

        # 边界检查：确保间隔合理
        min_interval = 0.001  # 最小1ms间隔
        if step_interval < min_interval:
            step_interval = min_interval
            steps = int(duration / step_interval)

        for i in range(steps + 1):
            if self._scan_cancelled:
                return

            # 计算当前电流值（线性插值）
            progress = i / steps
            current = start + delta * progress

            # 设置电流
            success = await self._set_current_internal(current)
            if not success:
                logger.error(f"Failed to set current during ramp: {current:.4f}A")
                return

            # 更新进度
            if cycle_progress:
                cycle_idx, total_cycles, start_prog, end_prog = cycle_progress
                cycle_base = cycle_idx / total_cycles
                cycle_range = (end_prog - start_prog) / total_cycles
                self._scan_progress = (
                    cycle_base + start_prog / total_cycles + progress * cycle_range
                )
            else:
                self._scan_progress = progress

            self._notify_progress_change()

            # 等待（跳过最后一步的等待）
            if i < steps:
                await asyncio.sleep(step_interval)

    # ==================== 磁场-电流校准 ====================

    async def calibrate(self, calibration_points: list[dict[str, float]]) -> bool:
        """
        执行磁场-电流校准。

        Args:
            calibration_points: 校准点列表，每个点包含：
                - current: 电流值（A）
                - field: 磁场值（T）

        Returns:
            bool: 校准是否成功

        Raises:
            ValueError: 校准点数据无效
        """
        # 参数校验
        if len(calibration_points) < 2:
            raise ValueError("At least 2 calibration points required")

        for point in calibration_points:
            if "current" not in point or "field" not in point:
                raise ValueError("Each calibration point must contain 'current' and 'field'")
            if not self._validate_current(point["current"]):
                raise ValueError(f"Current {point['current']}A exceeds valid range")
            if point["field"] < 0 or point["field"] > MAX_FIELD:
                raise ValueError(f"Field {point['field']}T exceeds valid range [0, {MAX_FIELD}]T")

        # 检查设备状态
        if self.status != DeviceStatus.READY:
            logger.error(f"Device not ready, current status: {self.status.value}")
            return False

        try:
            self.status = DeviceStatus.BUSY
            self._electromagnet_status = ElectromagnetStatus.CALIBRATING

            # 保存校准点
            self._calibration_points = [
                CalibrationPoint(current=p["current"], field=p["field"]) for p in calibration_points
            ]

            # 计算校准系数（线性拟合）
            self._calculate_calibration_coefficient()

            logger.info(
                f"Calibration completed with {len(calibration_points)} points, "
                f"coefficient={self._calibration_coefficient:.4f} T/A"
            )
            self._notify_status_change()
            return True

        except Exception as e:
            logger.error(f"Calibration error: {e}")
            self._last_error = str(e)
            return False
        finally:
            self._electromagnet_status = ElectromagnetStatus.IDLE
            self.status = DeviceStatus.READY

    def _calculate_calibration_coefficient(self) -> None:
        """
        计算校准系数（线性拟合）。

        使用最小二乘法拟合电流-磁场关系：
        B = coefficient * I + intercept

        其中：
        - coefficient: 斜率（T/A），表示电流到磁场的转换系数
        - intercept: 截距（T），用于修正零点偏移
        """
        if len(self._calibration_points) < 2:
            return

        # 提取数据
        currents = [p.current for p in self._calibration_points]
        fields = [p.field for p in self._calibration_points]

        # 最小二乘法线性拟合（带截距）
        n = len(currents)
        sum_x = sum(currents)
        sum_y = sum(fields)
        sum_xy = sum(c * f for c, f in zip(currents, fields))
        sum_x2 = sum(c * c for c in currents)

        # 计算斜率和截距
        denominator = n * sum_x2 - sum_x * sum_x
        if abs(denominator) < 1e-10:
            # 数据退化，使用简单平均值
            self._calibration_coefficient = sum_y / sum_x if sum_x > 0 else 0.2
            self._calibration_intercept = 0.0
            logger.warning(
                "Calibration data degenerate (all currents same), "
                f"using average coefficient={self._calibration_coefficient:.4f} T/A"
            )
            return

        # 斜率（校准系数）
        self._calibration_coefficient = (n * sum_xy - sum_x * sum_y) / denominator
        # 截距
        self._calibration_intercept = (sum_y - self._calibration_coefficient * sum_x) / n

        logger.info(
            f"Calibration fitted: B = {self._calibration_coefficient:.4f} * I + "
            f"{self._calibration_intercept:.4f} (T)"
        )

    def _current_to_field(self, current: float) -> float:
        """
        将电流值转换为磁场值。

        使用校准数据或线性关系进行转换：
        B = coefficient * I + intercept

        Args:
            current: 电流值（A）

        Returns:
            float: 磁场值（T）
        """
        # 如果有校准点，使用插值
        if len(self._calibration_points) >= 2:
            return self._interpolate_field(current)

        # 否则使用线性关系（含截距）
        return current * self._calibration_coefficient + self._calibration_intercept

    def _interpolate_field(self, current: float) -> float:
        """
        使用校准点插值计算磁场值。

        Args:
            current: 电流值（A）

        Returns:
            float: 磁场值（T）
        """
        # 排序校准点
        sorted_points = sorted(self._calibration_points, key=lambda p: p.current)

        # 边界检查
        if current <= sorted_points[0].current:
            return sorted_points[0].field
        if current >= sorted_points[-1].current:
            return sorted_points[-1].field

        # 线性插值
        for i in range(len(sorted_points) - 1):
            if sorted_points[i].current <= current <= sorted_points[i + 1].current:
                ratio = (current - sorted_points[i].current) / (
                    sorted_points[i + 1].current - sorted_points[i].current
                )
                return sorted_points[i].field + ratio * (
                    sorted_points[i + 1].field - sorted_points[i].field
                )

        return current * self._calibration_coefficient

    def get_calibration_data(self) -> dict[str, Any]:
        """
        获取校准数据。

        Returns:
            Dict[str, Any]: 校准数据字典，包含：
                - calibration_points: 校准点列表
                - calibration_coefficient: 斜率（T/A）
                - calibration_intercept: 截距（T）
                - points_count: 校准点数量
        """
        return {
            "calibration_points": [
                {"current": p.current, "field": p.field} for p in self._calibration_points
            ],
            "calibration_coefficient": round(self._calibration_coefficient, 4),
            "calibration_intercept": round(self._calibration_intercept, 4),
            "points_count": len(self._calibration_points),
        }

    async def clear_calibration(self) -> bool:
        """
        清除所有校准数据。

        重置为默认校准系数（0.2 T/A）。

        Returns:
            bool: 清除是否成功
        """
        try:
            self._calibration_points = []
            self._calibration_coefficient = 0.2  # 默认校准系数（T/A）
            self._calibration_intercept = 0.0  # 默认截距

            logger.info("Calibration data cleared, reset to default coefficient (0.2 T/A)")
            self._notify_status_change()
            return True

        except Exception as e:
            logger.error(f"Clear calibration error: {e}")
            self._last_error = str(e)
            return False

    # ==================== 过流保护机制 ====================

    def _start_protection_monitor(self) -> None:
        """启动保护监控任务。"""
        if self._protection_monitor_task is None or self._protection_monitor_task.done():
            self._protection_monitor_task = asyncio.create_task(self._protection_monitor_loop())
            logger.info("Protection monitor started")

    def _stop_protection_monitor(self) -> None:
        """停止保护监控任务。"""
        if self._protection_monitor_task and not self._protection_monitor_task.done():
            self._protection_monitor_task.cancel()
            logger.info("Protection monitor stopped")

    async def _protection_monitor_loop(self) -> None:
        """
        保护监控循环。

        持续监控电流和温度，触发保护机制。
        监控间隔：0.5秒
        """
        while True:
            try:
                await asyncio.sleep(self._protection_monitor_interval)

                # 跳过空闲状态或已触发保护的状态
                if self._electromagnet_status in (
                    ElectromagnetStatus.IDLE,
                    ElectromagnetStatus.OVERCURRENT,
                    ElectromagnetStatus.OVERTEMPERATURE,
                ):
                    continue

                # 检查过流保护
                if self._current_value > OVERCURRENT_THRESHOLD:
                    await self._trigger_overcurrent_protection(self._current_value)
                    break

                # 检查过温保护
                if self._current_temperature > MAX_TEMPERATURE:
                    await self._trigger_overtemperature_protection()
                    break

                # 仿真模式下模拟温度变化
                if self.simulation and self._current_value > 0:
                    # 温度模型：电流越大温度越高，考虑散热
                    # dT/dt = k*I - h*(T - T_ambient)
                    # 简化为：T = T_ambient + I * 5.0 + 随机波动
                    ambient_temp = 25.0
                    heat_factor = 5.0
                    noise = random.uniform(-0.5, 0.5)
                    self._current_temperature = (
                        ambient_temp + self._current_value * heat_factor + noise
                    )

            except asyncio.CancelledError:
                logger.info("Protection monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Protection monitor error: {e}")
                await asyncio.sleep(1.0)  # 错误后等待更长时间

    async def _trigger_overtemperature_protection(self) -> None:
        """触发过温保护。"""
        logger.error(
            f"OVERTEMPERATURE PROTECTION TRIGGERED: "
            f"{self._current_temperature:.1f}°C > {MAX_TEMPERATURE}°C threshold"
        )

        # 停止所有操作
        self._scan_cancelled = True
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()

        # 将电流归零
        await self._set_current_internal(0.0)

        # 更新状态
        self._electromagnet_status = ElectromagnetStatus.OVERTEMPERATURE
        self.status = DeviceStatus.ERROR
        self._last_error = (
            f"Overtemperature protection triggered: {self._current_temperature:.1f}°C"
        )

        self._notify_status_change()

    async def reset_overtemperature_protection(self) -> bool:
        """
        复位过温保护状态。

        Returns:
            bool: 复位是否成功
        """
        if self._electromagnet_status != ElectromagnetStatus.OVERTEMPERATURE:
            logger.warning("No overtemperature protection to reset")
            return True

        # 检查温度是否已恢复正常
        if self._current_temperature > MAX_TEMPERATURE * 0.9:
            logger.error(
                f"Cannot reset: temperature still high " f"({self._current_temperature:.1f}°C)"
            )
            return False

        # 确保电流已归零
        await self._set_current_internal(0.0)

        self._electromagnet_status = ElectromagnetStatus.IDLE
        self.status = DeviceStatus.READY
        self._last_error = None

        logger.info("Overtemperature protection reset")
        self._notify_status_change()
        return True

    async def _trigger_overcurrent_protection(self, current: float) -> None:
        """
        触发过流保护。

        Args:
            current: 触发过流的电流值（A）
        """
        logger.error(
            f"OVERCURRENT PROTECTION TRIGGERED: {current}A > " f"{OVERCURRENT_THRESHOLD}A threshold"
        )

        # 停止所有操作
        self._scan_cancelled = True
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()

        # 将电流归零
        await self._set_current_internal(0.0)

        # 更新状态
        self._electromagnet_status = ElectromagnetStatus.OVERCURRENT
        self.status = DeviceStatus.ERROR
        self._last_error = f"Overcurrent protection triggered: {current}A"

        self._notify_status_change()

    async def reset_overcurrent_protection(self) -> bool:
        """
        复位过流保护状态。

        Returns:
            bool: 复位是否成功
        """
        if self._electromagnet_status != ElectromagnetStatus.OVERCURRENT:
            logger.warning("No overcurrent protection to reset")
            return True

        # 确保电流已归零
        await self._set_current_internal(0.0)

        self._electromagnet_status = ElectromagnetStatus.IDLE
        self.status = DeviceStatus.READY
        self._last_error = None

        logger.info("Overcurrent protection reset")
        self._notify_status_change()
        return True

    # ==================== 辅助方法 ====================

    def _validate_current(self, current: float) -> bool:
        """
        验证电流值是否在有效范围内。

        Args:
            current: 电流值（A）

        Returns:
            bool: 是否有效
        """
        return MIN_CURRENT <= current <= self.max_current_limit

    def _validate_current_strict(self, current: float) -> tuple[bool, str]:
        """
        严格验证电流值并返回详细错误信息。

        Args:
            current: 电流值（A）

        Returns:
            tuple[bool, str]: (是否有效, 错误信息)
        """
        if current < MIN_CURRENT:
            return False, f"Current {current}A is below minimum {MIN_CURRENT}A"
        if current > self.max_current_limit:
            return False, f"Current {current}A exceeds maximum {self.max_current_limit}A"
        if current > OVERCURRENT_THRESHOLD:
            return (
                False,
                f"Current {current}A exceeds overcurrent threshold {OVERCURRENT_THRESHOLD}A",
            )
        return True, ""

    def validate_scan_params(
        self,
        mode: ScanMode,
        start_current: float,
        end_current: float,
        scan_rate: float,
        cycles: int = 1,
    ) -> tuple[bool, list[str]]:
        """
        验证扫描参数（不执行扫描）。

        用于前端预检查参数有效性。

        Args:
            mode: 扫描模式
            start_current: 起始电流（A）
            end_current: 目标电流（A）
            scan_rate: 扫描速率（A/s）
            cycles: 扫描周期数

        Returns:
            tuple[bool, list[str]]: (是否有效, 错误信息列表)
        """
        errors = []

        # 验证电流范围
        valid, msg = self._validate_current_strict(start_current)
        if not valid:
            errors.append(f"Start current: {msg}")

        valid, msg = self._validate_current_strict(end_current)
        if not valid:
            errors.append(f"End current: {msg}")

        # 验证扫描速率
        if scan_rate < MIN_SCAN_RATE:
            errors.append(f"Scan rate {scan_rate}A/s is below minimum {MIN_SCAN_RATE}A/s")
        if scan_rate > MAX_SCAN_RATE:
            errors.append(f"Scan rate {scan_rate}A/s exceeds maximum {MAX_SCAN_RATE}A/s")

        # 验证周期数
        if mode == ScanMode.TRIANGULAR:
            if cycles < 1:
                errors.append("Cycles must be at least 1 for triangular mode")

        # 验证扫描有效性
        if mode != ScanMode.TRIANGULAR and abs(start_current - end_current) < 0.001:
            errors.append("Start and end currents are too close")

        # 验证扫描时间
        if scan_rate > 0:
            duration = self._estimate_scan_duration(
                mode, start_current, end_current, scan_rate, cycles
            )
            if duration > 3600 * 24:
                errors.append(f"Estimated duration ({duration/3600:.1f}h) exceeds 24h limit")

        return len(errors) == 0, errors

    def _notify_status_change(self) -> None:
        """通知状态变化。"""
        if self._status_callback:
            try:
                status_data = {
                    "device_id": self.device_id,
                    "status": self.status.value,
                    "electromagnet_status": self._electromagnet_status.value,
                    "current_value": round(self._current_value, 4),
                    "field_value": round(self._field_value, 4),
                    "timestamp": time.time(),
                }
                self._status_callback(status_data)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def _notify_progress_change(self) -> None:
        """通知进度变化。"""
        if self._progress_callback:
            try:
                self._progress_callback(self._scan_progress)
            except Exception as e:
                logger.error(f"Progress callback error: {e}")

    # ==================== 便捷方法 ====================

    async def set_field(self, field: float) -> bool:
        """
        设置目标磁场值（自动转换为电流）。

        使用校准公式反算：I = (B - intercept) / coefficient

        Args:
            field: 目标磁场值（T），范围：0-2T

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 磁场值超出范围
        """
        if field < 0 or field > MAX_FIELD:
            raise ValueError(f"Field {field}T exceeds valid range [0, {MAX_FIELD}]T")

        # 反向计算电流（考虑截距）
        if abs(self._calibration_coefficient) > 1e-10:
            current = (field - self._calibration_intercept) / self._calibration_coefficient
        else:
            # 系数为零时使用默认值
            current = field / 0.2

        # 验证计算出的电流值
        if current < MIN_CURRENT:
            logger.warning(
                f"Calculated current {current:.4f}A is negative, " f"clamping to {MIN_CURRENT}A"
            )
            current = MIN_CURRENT

        return await self.set_current(current)

    async def quick_scan(
        self, start_field: float, end_field: float, scan_rate: float = 0.1
    ) -> bool:
        """
        快速启动磁场扫描（自动转换电流值）。

        使用校准公式反算电流：I = (B - intercept) / coefficient

        Args:
            start_field: 起始磁场（T）
            end_field: 目标磁场（T）
            scan_rate: 扫描速率（A/s）

        Returns:
            bool: 启动是否成功
        """
        # 转换磁场为电流（考虑截距）
        if abs(self._calibration_coefficient) > 1e-10:
            start_current = (
                start_field - self._calibration_intercept
            ) / self._calibration_coefficient
            end_current = (end_field - self._calibration_intercept) / self._calibration_coefficient
        else:
            start_current = start_field / 0.2
            end_current = end_field / 0.2

        # 验证并钳位电流值
        start_current = max(MIN_CURRENT, min(start_current, self.max_current_limit))
        end_current = max(MIN_CURRENT, min(end_current, self.max_current_limit))

        # 确定扫描模式
        if start_current < end_current:
            mode = ScanMode.FORWARD
        else:
            mode = ScanMode.REVERSE

        return await self.start_scan(
            mode=mode, start_current=start_current, end_current=end_current, scan_rate=scan_rate
        )

    async def emergency_stop(self) -> bool:
        """
        紧急停止。

        立即将电流归零并停止所有操作。

        Returns:
            bool: 是否成功
        """
        logger.warning("EMERGENCY STOP triggered!")

        # 取消所有任务
        self._scan_cancelled = True
        if self._scan_task and not self._scan_task.done():
            self._scan_task.cancel()

        # 立即将电流归零
        await self._set_current_internal(0.0)

        # 更新状态
        self._electromagnet_status = ElectromagnetStatus.IDLE
        self.status = DeviceStatus.EMERGENCY_STOP

        self._notify_status_change()
        return True

    async def reset_emergency(self) -> bool:
        """
        复位紧急停止状态。

        Returns:
            bool: 是否成功
        """
        if self.status != DeviceStatus.EMERGENCY_STOP:
            logger.warning("No emergency stop to reset")
            return True

        self.status = DeviceStatus.READY
        self._electromagnet_status = ElectromagnetStatus.IDLE

        logger.info("Emergency stop reset")
        self._notify_status_change()
        return True
