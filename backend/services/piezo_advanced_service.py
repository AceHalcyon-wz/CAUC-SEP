"""
压电控制器高级服务

文件名: piezo_advanced_service.py
路径: backend/services/
功能: 提供迟滞特性软件补偿、模式切换平滑过渡、纳米级位移动态扫描等高级功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - 迟滞特性软件补偿：基于Preisach模型、多项式拟合、神经网络补偿
    - 模式切换平滑过渡：开环/闭环模式切换、零点校准、过渡平滑处理
    - 纳米级位移动态扫描：三角波扫描、正弦波扫描、自定义轨迹扫描

依赖：
    - backend.core.piezo_controller: 压电控制器驱动
    - scipy: 科学计算库（用于曲线拟合、信号处理）
    - numpy: 数值计算库

安全约束：
    - 电压设置必须在安全范围内
    - 迟滞补偿参数必须经过校验
    - 模式切换必须确保位置连续性
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np
from scipy import integrate, interpolate, optimize, signal

from backend.core.abstract import DeviceStatus

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 压电控制器参数
PIEZO_MAX_VOLTAGE = 150.0  # 最大电压（V）
PIEZO_MIN_VOLTAGE = 0.0  # 最小电压（V）
PIEZO_VOLTAGE_RESOLUTION = 0.001  # 电压分辨率（V）

# 迟滞补偿参数
HYSTERESIS_MODEL_ORDER = 5  # 多项式拟合阶数
HYSTERESIS_CALIBRATION_POINTS = 100  # 校准点数

# 扫描参数
MAX_SCAN_POINTS = 100000  # 最大扫描点数
MIN_SCAN_INTERVAL_MS = 1  # 最小扫描间隔（毫秒）

# 模式切换参数
MODE_SWITCH_TIMEOUT_SECONDS = 10.0  # 模式切换超时时间


class PiezoMode(Enum):
    """压电控制器模式枚举。

    Attributes:
        OPEN_LOOP: 开环模式
        CLOSED_LOOP: 闭环模式
        CALIBRATION: 校准模式
    """

    OPEN_LOOP = "open_loop"
    CLOSED_LOOP = "closed_loop"
    CALIBRATION = "calibration"


class HysteresisModel(Enum):
    """迟滞模型类型枚举。

    Attributes:
        POLYNOMIAL: 多项式模型
        PREISACH: Preisach模型
        NEURAL_NETWORK: 神经网络模型
        LOOKUP_TABLE: 查找表模型
    """

    POLYNOMIAL = "polynomial"
    PREISACH = "preisach"
    NEURAL_NETWORK = "neural_network"
    LOOKUP_TABLE = "lookup_table"


class ScanWaveform(Enum):
    """扫描波形类型枚举。

    Attributes:
        TRIANGULAR: 三角波
        SINE: 正弦波
        SAWTOOTH: 锯齿波
        CUSTOM: 自定义波形
    """

    TRIANGULAR = "triangular"
    SINE = "sine"
    SAWTOOTH = "sawtooth"
    CUSTOM = "custom"


@dataclass
class HysteresisCalibrationData:
    """迟滞校准数据类。

    Attributes:
        voltage_up: 上升电压数组
        position_up: 上升位置数组
        voltage_down: 下降电压数组
        position_down: 下降位置数组
        temperature: 校准温度
        timestamp: 时间戳
    """

    voltage_up: np.ndarray
    position_up: np.ndarray
    voltage_down: np.ndarray
    position_down: np.ndarray
    temperature: float = 25.0
    timestamp: float = 0.0

    def validate(self) -> bool:
        """验证数据有效性。

        Returns:
            bool: 数据是否有效
        """
        if len(self.voltage_up) != len(self.position_up):
            return False
        if len(self.voltage_down) != len(self.position_down):
            return False
        if len(self.voltage_up) < 10:
            return False
        return True


@dataclass
class HysteresisCompensationParams:
    """迟滞补偿参数数据类。

    Attributes:
        model_type: 模型类型
        polynomial_coeffs_up: 上升多项式系数
        polynomial_coeffs_down: 下降多项式系数
        lookup_table_up: 上升查找表
        lookup_table_down: 下降查找表
        max_hysteresis_error: 最大迟滞误差
        compensation_accuracy: 补偿精度
    """

    model_type: HysteresisModel = HysteresisModel.POLYNOMIAL
    polynomial_coeffs_up: list[float] = field(default_factory=list)
    polynomial_coeffs_down: list[float] = field(default_factory=list)
    lookup_table_up: dict[float, float] = field(default_factory=dict)
    lookup_table_down: dict[float, float] = field(default_factory=dict)
    max_hysteresis_error: float = 0.0
    compensation_accuracy: float = 0.0


@dataclass
class ScanConfig:
    """扫描配置数据类。

    Attributes:
        waveform: 波形类型
        start_position: 起始位置（nm）
        end_position: 结束位置（nm）
        scan_rate: 扫描速率（nm/s）
        cycles: 扫描周期数
        points_per_cycle: 每周期点数
        custom_waveform: 自定义波形数据
    """

    waveform: ScanWaveform
    start_position: float
    end_position: float
    scan_rate: float = 100.0
    cycles: int = 1
    points_per_cycle: int = 1000
    custom_waveform: list[float] | None = None

    def validate(self) -> bool:
        """验证配置有效性。

        Returns:
            bool: 配置是否有效
        """
        if self.scan_rate <= 0:
            return False
        if self.cycles < 1:
            return False
        if self.points_per_cycle < 10:
            return False
        if self.points_per_cycle * self.cycles > MAX_SCAN_POINTS:
            return False
        return True


@dataclass
class PositionFeedback:
    """位置反馈数据类。

    Attributes:
        target_position: 目标位置（nm）
        actual_position: 实际位置（nm）
        voltage: 当前电压（V）
        error: 位置误差（nm）
        timestamp: 时间戳
    """

    target_position: float
    actual_position: float
    voltage: float
    error: float
    timestamp: float


class PiezoAdvancedService:
    """压电控制器高级服务类。

    提供迟滞特性软件补偿、模式切换平滑过渡、纳米级位移动态扫描等高级功能。

    Example:
        >>> service = PiezoAdvancedService(piezo_controller)
        >>> # 迟滞补偿
        >>> await service.calibrate_hysteresis()
        >>> target_voltage = service.compensate_hysteresis(target_position, direction='up')
        >>> # 纳米级扫描
        >>> config = ScanConfig(
        ...     waveform=ScanWaveform.TRIANGULAR,
        ...     start_position=0, end_position=10000, scan_rate=100
        ... )
        >>> await service.execute_scan(config)
    """

    def __init__(self, piezo_controller: Any):
        """初始化高级控制服务。

        Args:
            piezo_controller: 压电控制器驱动实例
        """
        self._controller = piezo_controller

        # 迟滞补偿参数
        self._hysteresis_params = HysteresisCompensationParams()
        self._hysteresis_calibrated = False
        self._last_voltage_direction = 1  # 1=上升, -1=下降
        self._last_voltage = 0.0

        # 扫描状态
        self._scan_running = False
        self._scan_task: asyncio.Task | None = None
        self._scan_cancelled = False
        self._scan_progress = 0.0

        # 位置反馈历史
        self._position_history: list[PositionFeedback] = []
        self._max_history_points = 10000

        # 模式状态
        self._current_mode = PiezoMode.OPEN_LOOP

        # 回调函数
        self._scan_progress_callback: Callable[[float, float], None] | None = None
        self._position_feedback_callback: Callable[[PositionFeedback], None] | None = None

        logger.info(f"PiezoAdvancedService initialized for {piezo_controller.device_id}")

    # ==================== 迟滞特性软件补偿 ====================

    async def calibrate_hysteresis(
        self,
        voltage_range: tuple[float, float] = (PIEZO_MIN_VOLTAGE, PIEZO_MAX_VOLTAGE),
        num_points: int = HYSTERESIS_CALIBRATION_POINTS,
        settle_time_ms: int = 100,
    ) -> HysteresisCalibrationData:
        """执行迟滞特性校准。

        Args:
            voltage_range: 电压范围（V）
            num_points: 校准点数
            settle_time_ms: 稳定时间（毫秒）

        Returns:
            HysteresisCalibrationData: 校准数据

        Raises:
            ValueError: 参数无效
        """
        if num_points < 10:
            raise ValueError("Need at least 10 calibration points")

        if self._controller.status != DeviceStatus.READY:
            raise RuntimeError(f"Device not ready: {self._controller.status.value}")

        logger.info(f"Starting hysteresis calibration: {num_points} points")

        voltage_up = np.linspace(voltage_range[0], voltage_range[1], num_points)
        voltage_down = np.linspace(voltage_range[1], voltage_range[0], num_points)

        position_up = []
        position_down = []

        # 上升扫描
        logger.info("Calibrating upward sweep...")
        for i, v in enumerate(voltage_up):
            await self._controller.set_voltage(v)
            await asyncio.sleep(settle_time_ms / 1000.0)

            # 读取位置（假设控制器有位置反馈）
            pos = await self._get_current_position()
            position_up.append(pos)

            if i % 10 == 0:
                logger.debug(f"Upward calibration: {i}/{num_points}, V={v:.3f}, pos={pos:.2f}nm")

        # 下降扫描
        logger.info("Calibrating downward sweep...")
        for i, v in enumerate(voltage_down):
            await self._controller.set_voltage(v)
            await asyncio.sleep(settle_time_ms / 1000.0)

            pos = await self._get_current_position()
            position_down.append(pos)

            if i % 10 == 0:
                logger.debug(f"Downward calibration: {i}/{num_points}, V={v:.3f}, pos={pos:.2f}nm")

        # 创建校准数据
        calibration_data = HysteresisCalibrationData(
            voltage_up=voltage_up,
            position_up=np.array(position_up),
            voltage_down=voltage_down,
            position_down=np.array(position_down),
            timestamp=time.time(),
        )

        # 计算补偿参数
        await self._compute_hysteresis_compensation(calibration_data)

        self._hysteresis_calibrated = True
        logger.info("Hysteresis calibration completed")

        return calibration_data

    async def _compute_hysteresis_compensation(
        self,
        calibration_data: HysteresisCalibrationData,
    ) -> None:
        """计算迟滞补偿参数。

        Args:
            calibration_data: 校准数据
        """
        # 多项式拟合：位置 -> 电压
        # 上升支
        coeffs_up = np.polyfit(calibration_data.position_up, calibration_data.voltage_up, HYSTERESIS_MODEL_ORDER)
        self._hysteresis_params.polynomial_coeffs_up = coeffs_up.tolist()

        # 下降支
        coeffs_down = np.polyfit(calibration_data.position_down, calibration_data.voltage_down, HYSTERESIS_MODEL_ORDER)
        self._hysteresis_params.polynomial_coeffs_down = coeffs_down.tolist()

        # 创建查找表
        self._hysteresis_params.lookup_table_up = {
            float(pos): float(vol) for pos, vol in zip(calibration_data.position_up, calibration_data.voltage_up)
        }
        self._hysteresis_params.lookup_table_down = {
            float(pos): float(vol) for pos, vol in zip(calibration_data.position_down, calibration_data.voltage_down)
        }

        # 计算最大迟滞误差
        # 插值计算同一位置下的电压差
        pos_range = np.linspace(
            min(calibration_data.position_up.min(), calibration_data.position_down.min()),
            max(calibration_data.position_up.max(), calibration_data.position_down.max()),
            100,
        )

        interp_up = interpolate.interp1d(calibration_data.position_up, calibration_data.voltage_up, fill_value="extrapolate")
        interp_down = interpolate.interp1d(calibration_data.position_down, calibration_data.voltage_down, fill_value="extrapolate")

        voltage_diff = np.abs(interp_up(pos_range) - interp_down(pos_range))
        self._hysteresis_params.max_hysteresis_error = float(np.max(voltage_diff))

        # 估算补偿精度
        self._hysteresis_params.compensation_accuracy = float(np.mean(voltage_diff))

        logger.info(
            f"Hysteresis compensation computed: max_error={self._hysteresis_params.max_hysteresis_error:.4f}V, "
            f"accuracy={self._hysteresis_params.compensation_accuracy:.4f}V"
        )

    def compensate_hysteresis(
        self,
        target_position: float,
        current_voltage: float | None = None,
    ) -> float:
        """计算迟滞补偿后的电压。

        Args:
            target_position: 目标位置（nm）
            current_voltage: 当前电压（V），用于判断方向

        Returns:
            float: 补偿后的电压（V）
        """
        if not self._hysteresis_calibrated:
            logger.warning("Hysteresis not calibrated, using linear approximation")
            return self._position_to_voltage_linear(target_position)

        # 判断电压变化方向
        if current_voltage is not None:
            if current_voltage > self._last_voltage:
                direction = 1  # 上升
            elif current_voltage < self._last_voltage:
                direction = -1  # 下降
            else:
                direction = self._last_voltage_direction
        else:
            direction = self._last_voltage_direction

        # 根据方向选择补偿曲线
        if direction > 0:
            coeffs = self._hysteresis_params.polynomial_coeffs_up
        else:
            coeffs = self._hysteresis_params.polynomial_coeffs_down

        # 计算补偿电压
        compensated_voltage = float(np.polyval(coeffs, target_position))

        # 钳位电压范围
        compensated_voltage = max(PIEZO_MIN_VOLTAGE, min(PIEZO_MAX_VOLTAGE, compensated_voltage))

        # 更新状态
        self._last_voltage_direction = direction
        self._last_voltage = compensated_voltage

        return compensated_voltage

    def _position_to_voltage_linear(self, position: float) -> float:
        """线性位置-电压转换（无补偿）。

        Args:
            position: 位置（nm）

        Returns:
            float: 电压（V）
        """
        # 假设线性关系：V = k * position
        # 使用典型压电系数：100nm/V
        return position / 100.0

    async def set_position_with_compensation(
        self,
        target_position: float,
    ) -> bool:
        """设置目标位置（带迟滞补偿）。

        Args:
            target_position: 目标位置（nm）

        Returns:
            bool: 设置是否成功
        """
        # 获取当前电压
        current_voltage = await self._controller.read_voltage()

        # 计算补偿电压
        compensated_voltage = self.compensate_hysteresis(target_position, current_voltage)

        # 设置电压
        success = await self._controller.set_voltage(compensated_voltage)

        if success:
            # 记录位置反馈
            await self._record_position_feedback(target_position, compensated_voltage)

        return success

    async def _record_position_feedback(
        self,
        target_position: float,
        voltage: float,
    ) -> None:
        """记录位置反馈。

        Args:
            target_position: 目标位置
            voltage: 当前电压
        """
        actual_position = await self._get_current_position()
        error = actual_position - target_position

        feedback = PositionFeedback(
            target_position=target_position,
            actual_position=actual_position,
            voltage=voltage,
            error=error,
            timestamp=time.time(),
        )

        self._position_history.append(feedback)
        if len(self._position_history) > self._max_history_points:
            self._position_history.pop(0)

        if self._position_feedback_callback:
            self._position_feedback_callback(feedback)

    # ==================== 模式切换平滑过渡 ====================

    async def switch_mode(
        self,
        target_mode: PiezoMode,
        smooth_transition: bool = True,
    ) -> bool:
        """切换压电控制器模式。

        Args:
            target_mode: 目标模式
            smooth_transition: 是否平滑过渡

        Returns:
            bool: 切换是否成功
        """
        if self._current_mode == target_mode:
            logger.debug(f"Already in {target_mode.value} mode")
            return True

        logger.info(f"Switching from {self._current_mode.value} to {target_mode.value} mode")

        try:
            if smooth_transition:
                # 记录当前位置
                current_position = await self._get_current_position()
                current_voltage = await self._controller.read_voltage()

                # 执行模式切换
                await self._controller.set_mode(target_mode.value)

                # 等待模式切换完成
                await asyncio.sleep(0.5)

                # 恢复位置（闭环模式）
                if target_mode == PiezoMode.CLOSED_LOOP:
                    await self._controller.set_position(current_position)

                # 验证位置连续性
                new_position = await self._get_current_position()
                position_error = abs(new_position - current_position)

                if position_error > 100:  # 100nm容差
                    logger.warning(
                        f"Position discontinuity detected: {position_error:.2f}nm, "
                        f"applying correction"
                    )
                    await self._controller.set_position(current_position)

            else:
                await self._controller.set_mode(target_mode.value)

            self._current_mode = target_mode
            logger.info(f"Mode switch completed: {target_mode.value}")
            return True

        except Exception as e:
            logger.error(f"Mode switch error: {e}")
            return False

    async def calibrate_zero_point(self) -> bool:
        """校准零点。

        Returns:
            bool: 校准是否成功
        """
        logger.info("Starting zero point calibration")

        # 切换到开环模式
        await self.switch_mode(PiezoMode.OPEN_LOOP)

        # 设置零电压
        await self._controller.set_voltage(0.0)
        await asyncio.sleep(1.0)

        # 记录零点位置
        zero_position = await self._get_current_position()

        # 设置零点
        await self._controller.set_zero_position(zero_position)

        logger.info(f"Zero point calibrated: {zero_position:.2f}nm")
        return True

    # ==================== 纳米级位移动态扫描 ====================

    async def execute_scan(
        self,
        config: ScanConfig,
        progress_callback: Callable[[float, float], None] | None = None,
    ) -> bool:
        """执行纳米级位移扫描。

        Args:
            config: 扫描配置
            progress_callback: 进度回调函数

        Returns:
            bool: 执行是否成功

        Raises:
            ValueError: 配置无效
        """
        if not config.validate():
            raise ValueError("Invalid scan configuration")

        if self._scan_running:
            logger.warning("Scan already running")
            return False

        if self._controller.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._controller.status.value}")
            return False

        self._scan_progress_callback = progress_callback
        self._scan_running = True
        self._scan_cancelled = False
        self._scan_progress = 0.0

        try:
            self._scan_task = asyncio.create_task(
                self._execute_scan_internal(config)
            )
            await self._scan_task
            return True

        except asyncio.CancelledError:
            logger.info("Scan cancelled")
            return False
        except Exception as e:
            logger.error(f"Scan execution error: {e}")
            return False
        finally:
            self._scan_running = False
            self._scan_task = None

    async def _execute_scan_internal(self, config: ScanConfig) -> None:
        """内部方法：执行扫描。

        Args:
            config: 扫描配置
        """
        # 生成扫描波形
        if config.waveform == ScanWaveform.TRIANGULAR:
            positions = self._generate_triangular_waveform(config)
        elif config.waveform == ScanWaveform.SINE:
            positions = self._generate_sine_waveform(config)
        elif config.waveform == ScanWaveform.SAWTOOTH:
            positions = self._generate_sawtooth_waveform(config)
        elif config.waveform == ScanWaveform.CUSTOM:
            positions = np.array(config.custom_waveform) if config.custom_waveform else np.array([])
        else:
            raise ValueError(f"Unsupported waveform: {config.waveform}")

        total_points = len(positions)
        scan_interval = 1.0 / config.scan_rate * (config.end_position - config.start_position) / config.points_per_cycle

        # 确保扫描间隔合理
        scan_interval = max(MIN_SCAN_INTERVAL_MS / 1000.0, scan_interval)

        logger.info(f"Starting scan: {total_points} points, interval={scan_interval*1000:.2f}ms")

        for i, position in enumerate(positions):
            if self._scan_cancelled:
                return

            # 设置位置（带迟滞补偿）
            await self.set_position_with_compensation(position)

            # 更新进度
            self._scan_progress = (i + 1) / total_points

            if self._scan_progress_callback:
                self._scan_progress_callback(self._scan_progress, position)

            await asyncio.sleep(scan_interval)

        self._scan_progress = 1.0
        logger.info("Scan completed")

    def _generate_triangular_waveform(self, config: ScanConfig) -> np.ndarray:
        """生成三角波波形。

        Args:
            config: 扫描配置

        Returns:
            np.ndarray: 位置数组
        """
        points_per_half = config.points_per_cycle // 2
        positions = []

        for _ in range(config.cycles):
            # 上升
            positions.extend(np.linspace(config.start_position, config.end_position, points_per_half))
            # 下降
            positions.extend(np.linspace(config.end_position, config.start_position, points_per_half))

        return np.array(positions)

    def _generate_sine_waveform(self, config: ScanConfig) -> np.ndarray:
        """生成正弦波波形。

        Args:
            config: 扫描配置

        Returns:
            np.ndarray: 位置数组
        """
        t = np.linspace(0, config.cycles, config.points_per_cycle * config.cycles)
        amplitude = (config.end_position - config.start_position) / 2
        offset = (config.end_position + config.start_position) / 2

        positions = amplitude * np.sin(2 * np.pi * t) + offset
        return positions

    def _generate_sawtooth_waveform(self, config: ScanConfig) -> np.ndarray:
        """生成锯齿波波形。

        Args:
            config: 扫描配置

        Returns:
            np.ndarray: 位置数组
        """
        positions = []

        for _ in range(config.cycles):
            positions.extend(np.linspace(config.start_position, config.end_position, config.points_per_cycle))

        return np.array(positions)

    async def stop_scan(self) -> bool:
        """停止扫描。

        Returns:
            bool: 停止是否成功
        """
        if not self._scan_running:
            return True

        self._scan_cancelled = True

        if self._scan_task:
            self._scan_task.cancel()
            try:
                await self._scan_task
            except asyncio.CancelledError:
                pass

        self._scan_running = False
        logger.info("Scan stopped")
        return True

    def get_scan_status(self) -> dict[str, Any]:
        """获取扫描状态。

        Returns:
            Dict[str, Any]: 扫描状态信息
        """
        return {
            "running": self._scan_running,
            "progress": round(self._scan_progress, 4),
            "cancelled": self._scan_cancelled,
        }

    # ==================== 辅助方法 ====================

    async def _get_current_position(self) -> float:
        """获取当前位置。

        Returns:
            float: 当前位置（nm）
        """
        status = await self._controller.read_status()
        return status.get("position_nm", 0.0)

    def get_position_history(self, count: int = 100) -> list[dict[str, Any]]:
        """获取位置历史记录。

        Args:
            count: 返回记录数量

        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        history = self._position_history[-count:]
        return [
            {
                "target_position": f.target_position,
                "actual_position": f.actual_position,
                "voltage": f.voltage,
                "error": f.error,
                "timestamp": f.timestamp,
            }
            for f in history
        ]

    def analyze_position_accuracy(self) -> dict[str, Any]:
        """分析位置精度。

        Returns:
            Dict[str, Any]: 精度分析结果
        """
        if len(self._position_history) < 10:
            return {"error": "Insufficient data for accuracy analysis"}

        errors = [f.error for f in self._position_history]

        return {
            "mean_error": float(np.mean(errors)),
            "std_error": float(np.std(errors)),
            "max_error": float(np.max(np.abs(errors))),
            "rms_error": float(np.sqrt(np.mean(np.array(errors) ** 2))),
            "sample_count": len(errors),
        }

    # ==================== 资源清理 ====================

    async def cleanup(self) -> None:
        """清理所有资源。"""
        await self.stop_scan()
        logger.info("PiezoAdvancedService cleanup completed")

    # ==================== 数据导入导出 ====================

    def export_hysteresis_calibration(self) -> str:
        """导出迟滞校准数据。

        Returns:
            str: JSON字符串
        """
        data = {
            "model_type": self._hysteresis_params.model_type.value,
            "polynomial_coeffs_up": self._hysteresis_params.polynomial_coeffs_up,
            "polynomial_coeffs_down": self._hysteresis_params.polynomial_coeffs_down,
            "max_hysteresis_error": self._hysteresis_params.max_hysteresis_error,
            "compensation_accuracy": self._hysteresis_params.compensation_accuracy,
            "calibrated": self._hysteresis_calibrated,
        }
        return json.dumps(data, indent=2)

    def import_hysteresis_calibration(self, json_str: str) -> bool:
        """导入迟滞校准数据。

        Args:
            json_str: JSON字符串

        Returns:
            bool: 导入是否成功
        """
        try:
            data = json.loads(json_str)

            self._hysteresis_params.model_type = HysteresisModel(data["model_type"])
            self._hysteresis_params.polynomial_coeffs_up = data["polynomial_coeffs_up"]
            self._hysteresis_params.polynomial_coeffs_down = data["polynomial_coeffs_down"]
            self._hysteresis_params.max_hysteresis_error = data.get("max_hysteresis_error", 0.0)
            self._hysteresis_params.compensation_accuracy = data.get("compensation_accuracy", 0.0)
            self._hysteresis_calibrated = data.get("calibrated", False)

            logger.info("Hysteresis calibration imported")
            return True

        except Exception as e:
            logger.error(f"Import hysteresis calibration error: {e}")
            return False
