"""
电磁铁高级控制服务

文件名: electromagnet_advanced_service.py
路径: backend/services/
功能: 提供阶梯波/自定义波形扫描、电流-磁场校准自动拟合、扫描暂停/续跑、磁场闭环控制等高级功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - 阶梯波扫描：多级阶梯电流扫描、可配置阶梯高度和保持时间
    - 自定义波形扫描：支持任意波形定义、波形数据导入导出
    - 电流-磁场校准自动拟合：多项式拟合、样条插值、非线性校准
    - 扫描暂停/续跑：支持扫描过程中暂停、恢复、断点续跑
    - 磁场闭环控制：基于磁场传感器的闭环控制、PID调节

依赖：
    - backend.core.electromagnet_driver: 电磁铁驱动器
    - scipy: 科学计算库（用于曲线拟合、插值）
    - numpy: 数值计算库

安全约束：
    - 所有电流设置必须经过过流保护校验
    - 扫描过程中必须持续监控温度
    - 磁场闭环控制必须设置安全边界
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np
from scipy import interpolate, optimize

from backend.core.abstract import DeviceStatus

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 波形扫描参数
MAX_WAVEFORM_POINTS = 10000  # 最大波形点数
MIN_STEP_HOLD_TIME_MS = 10  # 最小阶梯保持时间（毫秒）
DEFAULT_STEP_HOLD_TIME_MS = 100  # 默认阶梯保持时间（毫秒）

# 校准参数
MAX_CALIBRATION_POINTS = 100  # 最大校准点数
CALIBRATION_POLYNOMIAL_ORDER = 3  # 多项式拟合阶数

# 磁场闭环控制参数
FIELD_CONTROL_KP = 0.5  # 比例系数
FIELD_CONTROL_KI = 0.1  # 积分系数
FIELD_CONTROL_KD = 0.05  # 微分系数
FIELD_CONTROL_SAMPLE_INTERVAL_MS = 50  # 采样间隔（毫秒）
FIELD_CONTROL_MAX_INTEGRAL = 1.0  # 积分限幅

# 扫描暂停/续跑
SCAN_RESUME_TIMEOUT_SECONDS = 3600  # 恢复扫描超时时间（1小时）


class WaveformType(Enum):
    """波形类型枚举。

    Attributes:
        STEP: 阶梯波
        CUSTOM: 自定义波形
        SINE: 正弦波
        SQUARE: 方波
        SAWTOOTH: 锯齿波
        EXPONENTIAL: 指数波
    """

    STEP = "step"
    CUSTOM = "custom"
    SINE = "sine"
    SQUARE = "square"
    SAWTOOTH = "sawtooth"
    EXPONENTIAL = "exponential"


class CalibrationMethod(Enum):
    """校准方法枚举。

    Attributes:
        LINEAR: 线性拟合
        POLYNOMIAL: 多项式拟合
        SPLINE: 样条插值
        PIECEWISE_LINEAR: 分段线性插值
    """

    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    SPLINE = "spline"
    PIECEWISE_LINEAR = "piecewise_linear"


class ScanState(Enum):
    """扫描状态枚举。

    Attributes:
        IDLE: 空闲
        RUNNING: 运行中
        PAUSED: 已暂停
        COMPLETED: 已完成
        ERROR: 错误
    """

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class StepWaveformConfig:
    """阶梯波配置数据类。

    Attributes:
        start_current: 起始电流（A）
        end_current: 结束电流（A）
        step_height: 阶梯高度（A）
        hold_time_ms: 每个阶梯保持时间（毫秒）
        ramp_rate: 阶梯间变化速率（A/s）
        bidirectional: 是否双向扫描（往返）
    """

    start_current: float
    end_current: float
    step_height: float
    hold_time_ms: int = DEFAULT_STEP_HOLD_TIME_MS
    ramp_rate: float = 0.5
    bidirectional: bool = False

    def validate(self) -> bool:
        """验证配置有效性。

        Returns:
            bool: 配置是否有效
        """
        if self.step_height <= 0:
            logger.error(f"Invalid step_height: {self.step_height}")
            return False
        if self.hold_time_ms < MIN_STEP_HOLD_TIME_MS:
            logger.error(f"hold_time_ms too small: {self.hold_time_ms}")
            return False
        if self.ramp_rate <= 0:
            logger.error(f"Invalid ramp_rate: {self.ramp_rate}")
            return False
        return True

    def calculate_steps(self) -> int:
        """计算阶梯数量。

        Returns:
            int: 阶梯数量
        """
        delta = abs(self.end_current - self.start_current)
        return max(1, int(delta / self.step_height))


@dataclass
class CustomWaveformConfig:
    """自定义波形配置数据类。

    Attributes:
        waveform_type: 波形类型
        time_points: 时间点数组（秒）
        current_points: 电流点数组（A）
        loop_count: 循环次数
        interpolation: 插值方法（linear/cubic）
    """

    waveform_type: WaveformType = WaveformType.CUSTOM
    time_points: list[float] = field(default_factory=list)
    current_points: list[float] = field(default_factory=list)
    loop_count: int = 1
    interpolation: str = "linear"

    def validate(self) -> bool:
        """验证配置有效性。

        Returns:
            bool: 配置是否有效
        """
        if len(self.time_points) != len(self.current_points):
            logger.error("time_points and current_points must have same length")
            return False
        if len(self.time_points) < 2:
            logger.error("Need at least 2 points for waveform")
            return False
        if len(self.time_points) > MAX_WAVEFORM_POINTS:
            logger.error(f"Too many points: {len(self.time_points)} > {MAX_WAVEFORM_POINTS}")
            return False
        if self.loop_count < 1:
            logger.error(f"Invalid loop_count: {self.loop_count}")
            return False
        return True


@dataclass
class CalibrationPoint:
    """校准点数据类。

    Attributes:
        current: 电流值（A）
        field: 磁场值（T）
        timestamp: 记录时间戳
    """

    current: float
    field: float
    timestamp: float = 0.0


@dataclass
class CalibrationResult:
    """校准结果数据类。

    Attributes:
        method: 校准方法
        coefficients: 拟合系数
        r_squared: 拟合优度R²
        residuals: 残差统计
        valid_range: 有效范围（最小电流，最大电流）
    """

    method: CalibrationMethod
    coefficients: list[float] = field(default_factory=list)
    r_squared: float = 0.0
    residuals: dict[str, float] = field(default_factory=dict)
    valid_range: tuple[float, float] = (0.0, 10.0)


@dataclass
class ScanCheckpoint:
    """扫描断点数据类。

    Attributes:
        checkpoint_id: 断点ID
        current_position: 当前电流位置
        time_elapsed: 已运行时间
        progress: 进度（0-1）
        waveform_index: 波形索引
        timestamp: 时间戳
    """

    checkpoint_id: str
    current_position: float
    time_elapsed: float
    progress: float
    waveform_index: int
    timestamp: float


@dataclass
class FieldControlConfig:
    """磁场闭环控制配置数据类。

    Attributes:
        target_field: 目标磁场（T）
        kp: 比例系数
        ki: 积分系数
        kd: 微分系数
        max_current: 最大电流限制（A）
        tolerance: 稳态容差（T）
        sample_interval_ms: 采样间隔（毫秒）
    """

    target_field: float
    kp: float = FIELD_CONTROL_KP
    ki: float = FIELD_CONTROL_KI
    kd: float = FIELD_CONTROL_KD
    max_current: float = 10.0
    tolerance: float = 0.001
    sample_interval_ms: int = FIELD_CONTROL_SAMPLE_INTERVAL_MS


class ElectromagnetAdvancedService:
    """电磁铁高级控制服务类。

    提供阶梯波/自定义波形扫描、电流-磁场校准自动拟合、扫描暂停/续跑、磁场闭环控制等高级功能。

    Example:
        >>> service = ElectromagnetAdvancedService(electromagnet_driver)
        >>> # 阶梯波扫描
        >>> config = StepWaveformConfig(
        ...     start_current=0, end_current=10, step_height=0.5, hold_time_ms=100
        ... )
        >>> await service.execute_step_waveform(config)
        >>>
        >>> # 磁场闭环控制
        >>> field_config = FieldControlConfig(target_field=1.0)
        >>> await service.start_field_control(field_config)
    """

    def __init__(self, electromagnet_driver: Any):
        """初始化高级控制服务。

        Args:
            electromagnet_driver: 电磁铁驱动器实例
        """
        self._driver = electromagnet_driver

        # 波形扫描状态
        self._scan_state = ScanState.IDLE
        self._scan_task: asyncio.Task | None = None
        self._scan_checkpoint: ScanCheckpoint | None = None
        self._scan_progress = 0.0

        # 校准数据
        self._calibration_points: list[CalibrationPoint] = []
        self._calibration_result: CalibrationResult | None = None
        self._calibration_spline: Any = None  # 样条插值对象

        # 磁场闭环控制状态
        self._field_control_enabled = False
        self._field_control_task: asyncio.Task | None = None
        self._field_control_config: FieldControlConfig | None = None
        self._field_control_integral = 0.0
        self._field_control_last_error = 0.0

        # 回调函数
        self._scan_progress_callback: Callable[[float, float], None] | None = None
        self._calibration_complete_callback: Callable[[CalibrationResult], None] | None = None
        self._field_control_callback: Callable[[float, float], None] | None = None

        logger.info(f"ElectromagnetAdvancedService initialized for {electromagnet_driver.device_id}")

    # ==================== 阶梯波扫描 ====================

    async def execute_step_waveform(
        self,
        config: StepWaveformConfig,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """执行阶梯波扫描。

        Args:
            config: 阶梯波配置
            progress_callback: 进度回调函数（进度，当前电流）

        Returns:
            bool: 执行是否成功

        Raises:
            ValueError: 配置参数无效
        """
        if not config.validate():
            raise ValueError("Invalid step waveform configuration")

        if self._scan_state == ScanState.RUNNING:
            logger.warning("Scan already running")
            return False

        # 检查设备状态
        if self._driver.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._driver.status.value}")
            return False

        self._scan_progress_callback = progress_callback
        self._scan_state = ScanState.RUNNING
        self._scan_progress = 0.0

        try:
            self._scan_task = asyncio.create_task(
                self._execute_step_waveform_internal(config)
            )
            await self._scan_task
            return True

        except asyncio.CancelledError:
            logger.info("Step waveform scan cancelled")
            return False
        except Exception as e:
            logger.error(f"Step waveform scan error: {e}")
            self._scan_state = ScanState.ERROR
            return False

    async def _execute_step_waveform_internal(self, config: StepWaveformConfig) -> None:
        """内部方法：执行阶梯波扫描。

        Args:
            config: 阶梯波配置
        """
        steps = config.calculate_steps()
        direction = 1 if config.end_current >= config.start_current else -1
        total_steps = steps * (2 if config.bidirectional else 1)

        current_value = config.start_current
        step_count = 0

        # 正向扫描
        for i in range(steps + 1):
            if self._scan_state == ScanState.PAUSED:
                await self._wait_for_resume()

            if self._scan_state != ScanState.RUNNING:
                break

            # 计算当前阶梯电流
            current_value = config.start_current + direction * i * config.step_height

            # 钳位到目标范围
            if direction > 0:
                current_value = min(current_value, config.end_current)
            else:
                current_value = max(current_value, config.end_current)

            # 设置电流
            success = await self._driver.set_current(current_value)
            if not success:
                logger.error(f"Failed to set current: {current_value}A")
                self._scan_state = ScanState.ERROR
                return

            # 更新进度
            self._scan_progress = step_count / total_steps
            if self._scan_progress_callback:
                self._scan_progress_callback(self._scan_progress, current_value)

            # 保持时间
            await asyncio.sleep(config.hold_time_ms / 1000.0)
            step_count += 1

            # 保存断点
            self._save_scan_checkpoint(current_value, step_count / total_steps, i)

        # 双向扫描：反向
        if config.bidirectional and self._scan_state == ScanState.RUNNING:
            for i in range(steps + 1):
                if self._scan_state == ScanState.PAUSED:
                    await self._wait_for_resume()

                if self._scan_state != ScanState.RUNNING:
                    break

                current_value = config.end_current - direction * i * config.step_height

                if direction > 0:
                    current_value = max(current_value, config.start_current)
                else:
                    current_value = min(current_value, config.start_current)

                success = await self._driver.set_current(current_value)
                if not success:
                    logger.error(f"Failed to set current: {current_value}A")
                    self._scan_state = ScanState.ERROR
                    return

                self._scan_progress = step_count / total_steps
                if self._scan_progress_callback:
                    self._scan_progress_callback(self._scan_progress, current_value)

                await asyncio.sleep(config.hold_time_ms / 1000.0)
                step_count += 1

                self._save_scan_checkpoint(current_value, step_count / total_steps, steps + i)

        if self._scan_state == ScanState.RUNNING:
            self._scan_state = ScanState.COMPLETED
            self._scan_progress = 1.0
            logger.info(f"Step waveform scan completed: {step_count} steps")

    # ==================== 自定义波形扫描 ====================

    async def execute_custom_waveform(
        self,
        config: CustomWaveformConfig,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """执行自定义波形扫描。

        Args:
            config: 自定义波形配置
            progress_callback: 进度回调函数

        Returns:
            bool: 执行是否成功

        Raises:
            ValueError: 配置参数无效
        """
        if not config.validate():
            raise ValueError("Invalid custom waveform configuration")

        if self._scan_state == ScanState.RUNNING:
            logger.warning("Scan already running")
            return False

        if self._driver.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._driver.status.value}")
            return False

        self._scan_progress_callback = progress_callback
        self._scan_state = ScanState.RUNNING
        self._scan_progress = 0.0

        try:
            self._scan_task = asyncio.create_task(
                self._execute_custom_waveform_internal(config)
            )
            await self._scan_task
            return True

        except asyncio.CancelledError:
            logger.info("Custom waveform scan cancelled")
            return False
        except Exception as e:
            logger.error(f"Custom waveform scan error: {e}")
            self._scan_state = ScanState.ERROR
            return False

    async def _execute_custom_waveform_internal(self, config: CustomWaveformConfig) -> None:
        """内部方法：执行自定义波形扫描。

        Args:
            config: 自定义波形配置
        """
        # 创建插值函数
        time_array = np.array(config.time_points)
        current_array = np.array(config.current_points)

        if config.interpolation == "cubic":
            interp_func = interpolate.interp1d(
                time_array, current_array, kind="cubic", fill_value="extrapolate"
            )
        else:
            interp_func = interpolate.interp1d(
                time_array, current_array, kind="linear", fill_value="extrapolate"
            )

        # 计算总时间和采样间隔
        total_time = time_array[-1] * config.loop_count
        sample_interval = 0.01  # 10ms采样间隔
        total_samples = int(total_time / sample_interval)

        start_time = time.time()

        for sample_idx in range(total_samples):
            if self._scan_state == ScanState.PAUSED:
                await self._wait_for_resume()

            if self._scan_state != ScanState.RUNNING:
                break

            # 计算当前时间
            elapsed = time.time() - start_time

            # 处理循环
            cycle_time = elapsed % time_array[-1]

            # 插值计算电流
            current_value = float(interp_func(cycle_time))

            # 钳位电流值
            current_value = max(0.0, min(current_value, self._driver.max_current_limit))

            # 设置电流
            success = await self._driver.set_current(current_value)
            if not success:
                logger.error(f"Failed to set current: {current_value}A")
                self._scan_state = ScanState.ERROR
                return

            # 更新进度
            self._scan_progress = sample_idx / total_samples
            if self._scan_progress_callback:
                self._scan_progress_callback(self._scan_progress, current_value)

            # 保存断点
            self._save_scan_checkpoint(current_value, self._scan_progress, sample_idx)

            await asyncio.sleep(sample_interval)

        if self._scan_state == ScanState.RUNNING:
            self._scan_state = ScanState.COMPLETED
            self._scan_progress = 1.0
            logger.info(f"Custom waveform scan completed: {total_samples} samples")

    async def generate_standard_waveform(
        self,
        waveform_type: WaveformType,
        duration: float,
        amplitude: float,
        offset: float = 0.0,
        frequency: float = 1.0,
        num_points: int = 1000,
    ) -> CustomWaveformConfig:
        """生成标准波形配置。

        Args:
            waveform_type: 波形类型
            duration: 持续时间（秒）
            amplitude: 幅值（A）
            offset: 偏移量（A）
            frequency: 频率（Hz）
            num_points: 点数

        Returns:
            CustomWaveformConfig: 波形配置
        """
        time_points = np.linspace(0, duration, num_points).tolist()

        if waveform_type == WaveformType.SINE:
            current_points = amplitude * np.sin(2 * np.pi * frequency * np.array(time_points)) + offset

        elif waveform_type == WaveformType.SQUARE:
            current_points = amplitude * np.sign(np.sin(2 * np.pi * frequency * np.array(time_points))) + offset

        elif waveform_type == WaveformType.SAWTOOTH:
            current_points = amplitude * (2 * (frequency * np.array(time_points) % 1) - 1) + offset

        elif waveform_type == WaveformType.EXPONENTIAL:
            current_points = amplitude * (1 - np.exp(-frequency * np.array(time_points))) + offset

        else:
            raise ValueError(f"Unsupported waveform type: {waveform_type}")

        return CustomWaveformConfig(
            waveform_type=waveform_type,
            time_points=time_points,
            current_points=current_points.tolist(),
        )

    # ==================== 扫描暂停/续跑 ====================

    async def pause_scan(self) -> bool:
        """暂停扫描。

        Returns:
            bool: 暂停是否成功
        """
        if self._scan_state != ScanState.RUNNING:
            logger.warning("No scan running to pause")
            return False

        self._scan_state = ScanState.PAUSED
        logger.info("Scan paused")
        return True

    async def resume_scan(self) -> bool:
        """恢复扫描。

        Returns:
            bool: 恢复是否成功
        """
        if self._scan_state != ScanState.PAUSED:
            logger.warning("No paused scan to resume")
            return False

        self._scan_state = ScanState.RUNNING
        logger.info("Scan resumed")
        return True

    async def _wait_for_resume(self) -> None:
        """等待扫描恢复。"""
        timeout = SCAN_RESUME_TIMEOUT_SECONDS
        start_time = time.time()

        while self._scan_state == ScanState.PAUSED:
            if time.time() - start_time > timeout:
                logger.error("Scan resume timeout")
                self._scan_state = ScanState.ERROR
                return
            await asyncio.sleep(0.1)

    def _save_scan_checkpoint(
        self,
        current_position: float,
        progress: float,
        waveform_index: int,
    ) -> None:
        """保存扫描断点。

        Args:
            current_position: 当前电流位置
            progress: 进度
            waveform_index: 波形索引
        """
        self._scan_checkpoint = ScanCheckpoint(
            checkpoint_id=f"checkpoint_{int(time.time() * 1000)}",
            current_position=current_position,
            time_elapsed=0.0,  # 需要在外部计算
            progress=progress,
            waveform_index=waveform_index,
            timestamp=time.time(),
        )

    async def stop_scan(self) -> bool:
        """停止扫描。

        Returns:
            bool: 停止是否成功
        """
        if self._scan_state == ScanState.IDLE:
            return True

        self._scan_state = ScanState.IDLE

        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        # 将电流归零
        await self._driver.set_current(0.0)

        logger.info("Scan stopped")
        return True

    def get_scan_status(self) -> dict[str, Any]:
        """获取扫描状态。

        Returns:
            Dict[str, Any]: 扫描状态信息
        """
        return {
            "state": self._scan_state.value,
            "progress": round(self._scan_progress, 4),
            "checkpoint": {
                "current_position": self._scan_checkpoint.current_position,
                "progress": self._scan_checkpoint.progress,
                "waveform_index": self._scan_checkpoint.waveform_index,
            } if self._scan_checkpoint else None,
        }

    # ==================== 电流-磁场校准自动拟合 ====================

    async def add_calibration_point(
        self,
        current: float,
        field: float,
    ) -> bool:
        """添加校准点。

        Args:
            current: 电流值（A）
            field: 磁场值（T）

        Returns:
            bool: 添加是否成功
        """
        if len(self._calibration_points) >= MAX_CALIBRATION_POINTS:
            logger.error(f"Max calibration points reached: {MAX_CALIBRATION_POINTS}")
            return False

        point = CalibrationPoint(
            current=current,
            field=field,
            timestamp=time.time(),
        )
        self._calibration_points.append(point)

        logger.info(f"Calibration point added: {current}A -> {field}T")
        return True

    async def auto_calibrate(
        self,
        method: CalibrationMethod = CalibrationMethod.POLYNOMIAL,
        order: int = CALIBRATION_POLYNOMIAL_ORDER,
    ) -> CalibrationResult:
        """执行自动校准拟合。

        Args:
            method: 校准方法
            order: 多项式阶数（仅多项式方法有效）

        Returns:
            CalibrationResult: 校准结果

        Raises:
            ValueError: 校准点不足
        """
        if len(self._calibration_points) < 2:
            raise ValueError("Need at least 2 calibration points for calibration")

        # 提取数据
        currents = np.array([p.current for p in self._calibration_points])
        fields = np.array([p.field for p in self._calibration_points])

        # 排序（按电流值）
        sort_idx = np.argsort(currents)
        currents = currents[sort_idx]
        fields = fields[sort_idx]

        result = CalibrationResult(
            method=method,
            valid_range=(float(np.min(currents)), float(np.max(currents))),
        )

        try:
            if method == CalibrationMethod.LINEAR:
                # 线性拟合
                coeffs = np.polyfit(currents, fields, 1)
                result.coefficients = coeffs.tolist()

                # 计算R²
                predicted = np.polyval(coeffs, currents)
                ss_res = np.sum((fields - predicted) ** 2)
                ss_tot = np.sum((fields - np.mean(fields)) ** 2)
                result.r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            elif method == CalibrationMethod.POLYNOMIAL:
                # 多项式拟合
                order = min(order, len(currents) - 1)
                coeffs = np.polyfit(currents, fields, order)
                result.coefficients = coeffs.tolist()

                # 计算R²
                predicted = np.polyval(coeffs, currents)
                ss_res = np.sum((fields - predicted) ** 2)
                ss_tot = np.sum((fields - np.mean(fields)) ** 2)
                result.r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            elif method == CalibrationMethod.SPLINE:
                # 样条插值
                self._calibration_spline = interpolate.CubicSpline(currents, fields)
                result.coefficients = []  # 样条系数复杂，不存储
                result.r_squared = 1.0  # 样条插值完美拟合数据点

            elif method == CalibrationMethod.PIECEWISE_LINEAR:
                # 分段线性插值
                self._calibration_spline = interpolate.interp1d(
                    currents, fields, kind="linear", fill_value="extrapolate"
                )
                result.coefficients = []
                result.r_squared = 1.0

            # 计算残差统计
            if method in (CalibrationMethod.LINEAR, CalibrationMethod.POLYNOMIAL):
                residuals = fields - predicted
                result.residuals = {
                    "mean": float(np.mean(residuals)),
                    "std": float(np.std(residuals)),
                    "max": float(np.max(np.abs(residuals))),
                }

            self._calibration_result = result
            logger.info(
                f"Calibration completed: method={method.value}, "
                f"R²={result.r_squared:.4f}, points={len(currents)}"
            )

            # 回调通知
            if self._calibration_complete_callback:
                self._calibration_complete_callback(result)

            return result

        except Exception as e:
            logger.error(f"Calibration error: {e}")
            raise

    def current_to_field(self, current: float) -> float:
        """将电流转换为磁场（使用校准结果）。

        Args:
            current: 电流值（A）

        Returns:
            float: 磁场值（T）
        """
        if self._calibration_result is None:
            # 使用默认线性关系
            return current * 0.2

        method = self._calibration_result.method

        if method == CalibrationMethod.LINEAR or method == CalibrationMethod.POLYNOMIAL:
            return float(np.polyval(self._calibration_result.coefficients, current))

        elif method in (CalibrationMethod.SPLINE, CalibrationMethod.PIECEWISE_LINEAR):
            if self._calibration_spline is not None:
                return float(self._calibration_spline(current))

        return current * 0.2

    def field_to_current(self, field: float) -> float:
        """将磁场转换为电流（反向计算）。

        Args:
            field: 磁场值（T）

        Returns:
            float: 电流值（A）
        """
        if self._calibration_result is None:
            return field / 0.2

        method = self._calibration_result.method

        if method == CalibrationMethod.LINEAR:
            # 线性反算
            a, b = self._calibration_result.coefficients
            if abs(a) > 1e-10:
                return (field - b) / a
            return 0.0

        elif method == CalibrationMethod.POLYNOMIAL:
            # 多项式反算（数值求解）
            def objective(current: float) -> float:
                return np.polyval(self._calibration_result.coefficients, current) - field

            try:
                result = optimize.brentq(
                    objective,
                    self._calibration_result.valid_range[0],
                    self._calibration_result.valid_range[1],
                )
                return float(result)
            except ValueError:
                logger.warning("Field to current conversion failed, using approximation")
                return field / 0.2

        elif method in (CalibrationMethod.SPLINE, CalibrationMethod.PIECEWISE_LINEAR):
            # 样条反算（数值求解）
            if self._calibration_spline is not None:
                currents = np.linspace(
                    self._calibration_result.valid_range[0],
                    self._calibration_result.valid_range[1],
                    1000,
                )
                fields = self._calibration_spline(currents)
                idx = np.argmin(np.abs(fields - field))
                return float(currents[idx])

        return field / 0.2

    def get_calibration_data(self) -> dict[str, Any]:
        """获取校准数据。

        Returns:
            Dict[str, Any]: 校准数据
        """
        return {
            "points": [
                {"current": p.current, "field": p.field, "timestamp": p.timestamp}
                for p in self._calibration_points
            ],
            "result": {
                "method": self._calibration_result.method.value,
                "coefficients": self._calibration_result.coefficients,
                "r_squared": self._calibration_result.r_squared,
                "valid_range": self._calibration_result.valid_range,
            } if self._calibration_result else None,
        }

    async def clear_calibration(self) -> bool:
        """清除校准数据。

        Returns:
            bool: 清除是否成功
        """
        self._calibration_points = []
        self._calibration_result = None
        self._calibration_spline = None
        logger.info("Calibration data cleared")
        return True

    # ==================== 磁场闭环控制 ====================

    async def start_field_control(
        self,
        config: FieldControlConfig,
        control_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """启动磁场闭环控制。

        Args:
            config: 磁场控制配置
            control_callback: 控制回调函数（目标磁场，实际磁场）

        Returns:
            bool: 启动是否成功
        """
        if self._field_control_enabled:
            logger.warning("Field control already enabled")
            return False

        if self._driver.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._driver.status.value}")
            return False

        self._field_control_config = config
        self._field_control_callback = control_callback
        self._field_control_enabled = True
        self._field_control_integral = 0.0
        self._field_control_last_error = 0.0

        self._field_control_task = asyncio.create_task(
            self._field_control_loop()
        )

        logger.info(
            f"Field control started: target={config.target_field}T, "
            f"KP={config.kp}, KI={config.ki}, KD={config.kd}"
        )
        return True

    async def stop_field_control(self) -> bool:
        """停止磁场闭环控制。

        Returns:
            bool: 停止是否成功
        """
        if not self._field_control_enabled:
            return True

        self._field_control_enabled = False

        if self._field_control_task:
            self._field_control_task.cancel()
            try:
                await self._field_control_task
            except asyncio.CancelledError:
                pass

        logger.info("Field control stopped")
        return True

    async def _field_control_loop(self) -> None:
        """磁场闭环控制循环。"""
        config = self._field_control_config
        sample_interval = config.sample_interval_ms / 1000.0

        while self._field_control_enabled:
            try:
                # 读取当前磁场（从驱动器状态获取）
                status = await self._driver.read_status()
                actual_field = status.get("field_value", 0.0)

                # 计算误差
                error = config.target_field - actual_field

                # PID计算
                # 比例项
                p_term = config.kp * error

                # 积分项（带限幅）
                self._field_control_integral += error * sample_interval
                self._field_control_integral = max(
                    -FIELD_CONTROL_MAX_INTEGRAL,
                    min(FIELD_CONTROL_MAX_INTEGRAL, self._field_control_integral)
                )
                i_term = config.ki * self._field_control_integral

                # 微分项
                d_term = config.kd * (error - self._field_control_last_error) / sample_interval
                self._field_control_last_error = error

                # 计算输出电流
                output_current = p_term + i_term + d_term

                # 转换为实际电流设置值
                # 使用校准结果反向计算
                target_current = self.field_to_current(config.target_field) + output_current

                # 钳位电流值
                target_current = max(0.0, min(target_current, config.max_current))

                # 设置电流
                await self._driver.set_current(target_current)

                # 回调通知
                if self._field_control_callback:
                    self._field_control_callback(config.target_field, actual_field)

                # 检查稳态
                if abs(error) < config.tolerance:
                    logger.debug(f"Field control steady state reached: error={error:.4f}T")

                await asyncio.sleep(sample_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Field control loop error: {e}")
                await asyncio.sleep(1.0)

    async def set_target_field(self, target_field: float) -> bool:
        """设置目标磁场（闭环控制模式下）。

        Args:
            target_field: 目标磁场（T）

        Returns:
            bool: 设置是否成功
        """
        if not self._field_control_enabled or self._field_control_config is None:
            logger.warning("Field control not enabled")
            return False

        self._field_control_config.target_field = target_field
        logger.info(f"Target field updated: {target_field}T")
        return True

    def get_field_control_status(self) -> dict[str, Any]:
        """获取磁场闭环控制状态。

        Returns:
            Dict[str, Any]: 控制状态信息
        """
        return {
            "enabled": self._field_control_enabled,
            "target_field": self._field_control_config.target_field if self._field_control_config else None,
            "integral": self._field_control_integral,
            "last_error": self._field_control_last_error,
        }

    # ==================== 资源清理 ====================

    async def cleanup(self) -> None:
        """清理所有资源。"""
        await self.stop_scan()
        await self.stop_field_control()
        logger.info("ElectromagnetAdvancedService cleanup completed")

    # ==================== 数据导入导出 ====================

    def export_waveform(self, config: CustomWaveformConfig) -> str:
        """导出波形配置为JSON字符串。

        Args:
            config: 波形配置

        Returns:
            str: JSON字符串
        """
        data = {
            "waveform_type": config.waveform_type.value,
            "time_points": config.time_points,
            "current_points": config.current_points,
            "loop_count": config.loop_count,
            "interpolation": config.interpolation,
        }
        return json.dumps(data, indent=2)

    def import_waveform(self, json_str: str) -> CustomWaveformConfig:
        """从JSON字符串导入波形配置。

        Args:
            json_str: JSON字符串

        Returns:
            CustomWaveformConfig: 波形配置
        """
        data = json.loads(json_str)
        return CustomWaveformConfig(
            waveform_type=WaveformType(data["waveform_type"]),
            time_points=data["time_points"],
            current_points=data["current_points"],
            loop_count=data.get("loop_count", 1),
            interpolation=data.get("interpolation", "linear"),
        )

    def export_calibration(self) -> str:
        """导出校准数据为JSON字符串。

        Returns:
            str: JSON字符串
        """
        return json.dumps(self.get_calibration_data(), indent=2)

    def import_calibration(self, json_str: str) -> bool:
        """从JSON字符串导入校准数据。

        Args:
            json_str: JSON字符串

        Returns:
            bool: 导入是否成功
        """
        try:
            data = json.loads(json_str)

            # 导入校准点
            self._calibration_points = [
                CalibrationPoint(
                    current=p["current"],
                    field=p["field"],
                    timestamp=p.get("timestamp", 0.0),
                )
                for p in data["points"]
            ]

            # 导入校准结果
            if data.get("result"):
                result_data = data["result"]
                self._calibration_result = CalibrationResult(
                    method=CalibrationMethod(result_data["method"]),
                    coefficients=result_data["coefficients"],
                    r_squared=result_data["r_squared"],
                    valid_range=tuple(result_data["valid_range"]),
                )

            logger.info(f"Calibration data imported: {len(self._calibration_points)} points")
            return True

        except Exception as e:
            logger.error(f"Import calibration error: {e}")
            return False
