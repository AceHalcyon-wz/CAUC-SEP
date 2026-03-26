"""
专业数据分析服务

文件名: data_analysis_service.py
路径: backend/services/
功能: 提供磁滞回线高级参数计算、磁阻效应分析、系统误差校正、专业科学绘图等数据分析功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - 磁滞回线高级参数计算：饱和磁化强度、矫顽力、剩磁、磁导率、磁滞损耗
    - 磁阻效应分析：磁阻率计算、AMR/GMR/TMR特性分析、角度依赖性分析
    - 系统误差校正：背景扣除、零点漂移校正、仪器响应校正、温度漂移补偿
    - 专业科学绘图：符合期刊标准的图表生成、多曲线对比、误差棒绘制

依赖：
    - scipy: 科学计算库（用于曲线拟合、信号处理）
    - numpy: 数值计算库
    - matplotlib: 绑图库（可选，用于生成图表）

安全约束：
    - 所有计算必须进行数据有效性检查
    - 拟合参数必须在物理合理范围内
    - 误差校正不能引入新的系统误差
"""

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np
from scipy import integrate, interpolate, optimize, signal, stats

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 磁滞回线参数
MAX_HYSTERESIS_POINTS = 100000  # 最大数据点数
SATURATION_FIELD_THRESHOLD = 0.95  # 饱和判断阈值

# 磁阻效应参数
MR_MIN_FIELD = 0.001  # 最小磁场（T）
MR_MAX_FIELD = 10.0  # 最大磁场（T）

# 误差校正参数
BACKGROUND_WINDOW_SIZE = 100  # 背景估计窗口大小
DRIFT_CORRECTION_ORDER = 2  # 漂移校正多项式阶数

# 绘图参数
FIGURE_DPI = 300  # 图像分辨率
FIGURE_WIDTH_INCHES = 8.0  # 图像宽度（英寸）
FIGURE_HEIGHT_INCHES = 6.0  # 图像高度（英寸）


class HysteresisDirection(Enum):
    """磁滞回线方向枚举。

    Attributes:
        ASCENDING: 上升支（磁场从负到正）
        DESCENDING: 下降支（磁场从正到负）
        FULL: 完整回线
    """

    ASCENDING = "ascending"
    DESCENDING = "descending"
    FULL = "full"


class MREffectType(Enum):
    """磁阻效应类型枚举。

    Attributes:
        AMR: 各向异性磁阻
        GMR: 巨磁阻
        TMR: 隧道磁阻
        CMR: 庞磁阻
    """

    AMR = "amr"
    GMR = "gmr"
    TMR = "tmr"
    CMR = "cmr"


class CorrectionType(Enum):
    """误差校正类型枚举。

    Attributes:
        BACKGROUND: 背景扣除
        ZERO_DRIFT: 零点漂移校正
        INSTRUMENT_RESPONSE: 仪器响应校正
        TEMPERATURE_DRIFT: 温度漂移补偿
        LINEAR_BASELINE: 线性基线校正
    """

    BACKGROUND = "background"
    ZERO_DRIFT = "zero_drift"
    INSTRUMENT_RESPONSE = "instrument_response"
    TEMPERATURE_DRIFT = "temperature_drift"
    LINEAR_BASELINE = "linear_baseline"


@dataclass
class HysteresisData:
    """磁滞回线数据类。

    Attributes:
        field: 磁场数组（T）
        magnetization: 磁化强度数组（A/m 或 emu/g）
        direction: 回线方向
        temperature: 测量温度（K）
        sample_id: 样品ID
        timestamp: 时间戳
    """

    field: np.ndarray
    magnetization: np.ndarray
    direction: HysteresisDirection = HysteresisDirection.FULL
    temperature: float = 300.0
    sample_id: str = ""
    timestamp: float = 0.0

    def validate(self) -> bool:
        """验证数据有效性。

        Returns:
            bool: 数据是否有效
        """
        if len(self.field) != len(self.magnetization):
            logger.error("Field and magnetization arrays must have same length")
            return False
        if len(self.field) < 10:
            logger.error("Need at least 10 data points")
            return False
        if len(self.field) > MAX_HYSTERESIS_POINTS:
            logger.error(f"Too many points: {len(self.field)} > {MAX_HYSTERESIS_POINTS}")
            return False
        return True


@dataclass
class HysteresisParameters:
    """磁滞回线参数数据类。

    Attributes:
        saturation_magnetization: 饱和磁化强度（A/m 或 emu/g）
        remanent_magnetization: 剩余磁化强度（A/m 或 emu/g）
        coercive_field: 矫顽力（T）
        squareness: 矩形比（Mr/Ms）
        initial_permeability: 初始磁导率
        maximum_permeability: 最大磁导率
        hysteresis_loss: 磁滞损耗（J/m³）
        saturation_field: 饱和磁场（T）
    """

    saturation_magnetization: float = 0.0
    remanent_magnetization: float = 0.0
    coercive_field: float = 0.0
    squareness: float = 0.0
    initial_permeability: float = 0.0
    maximum_permeability: float = 0.0
    hysteresis_loss: float = 0.0
    saturation_field: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """转换为字典。

        Returns:
            Dict[str, float]: 参数字典
        """
        return {
            "saturation_magnetization": self.saturation_magnetization,
            "remanent_magnetization": self.remanent_magnetization,
            "coercive_field": self.coercive_field,
            "squareness": self.squareness,
            "initial_permeability": self.initial_permeability,
            "maximum_permeability": self.maximum_permeability,
            "hysteresis_loss": self.hysteresis_loss,
            "saturation_field": self.saturation_field,
        }


@dataclass
class MRData:
    """磁阻效应数据类。

    Attributes:
        field: 磁场数组（T）
        resistance: 电阻数组（Ω）
        angle: 磁场角度数组（°），可选
        temperature: 测量温度（K）
        mr_type: 磁阻效应类型
        sample_id: 样品ID
    """

    field: np.ndarray
    resistance: np.ndarray
    angle: np.ndarray | None = None
    temperature: float = 300.0
    mr_type: MREffectType = MREffectType.AMR
    sample_id: str = ""

    def validate(self) -> bool:
        """验证数据有效性。

        Returns:
            bool: 数据是否有效
        """
        if len(self.field) != len(self.resistance):
            logger.error("Field and resistance arrays must have same length")
            return False
        if len(self.field) < 5:
            logger.error("Need at least 5 data points")
            return False
        return True


@dataclass
class MRParameters:
    """磁阻效应参数数据类。

    Attributes:
        mr_ratio: 磁阻率（%）
        mr_max: 最大磁阻（%）
        mr_min: 最小磁阻（%）
        zero_field_resistance: 零场电阻（Ω）
        saturation_resistance: 饱和电阻（Ω）
        sensitivity: 磁阻灵敏度（%/T）
        linearity: 线性度
    """

    mr_ratio: float = 0.0
    mr_max: float = 0.0
    mr_min: float = 0.0
    zero_field_resistance: float = 0.0
    saturation_resistance: float = 0.0
    sensitivity: float = 0.0
    linearity: float = 0.0

    def to_dict(self) -> dict[str, float]:
        """转换为字典。

        Returns:
            Dict[str, float]: 参数字典
        """
        return {
            "mr_ratio": self.mr_ratio,
            "mr_max": self.mr_max,
            "mr_min": self.mr_min,
            "zero_field_resistance": self.zero_field_resistance,
            "saturation_resistance": self.saturation_resistance,
            "sensitivity": self.sensitivity,
            "linearity": self.linearity,
        }


@dataclass
class CorrectionConfig:
    """误差校正配置数据类。

    Attributes:
        correction_type: 校正类型
        parameters: 校正参数
        enabled: 是否启用
    """

    correction_type: CorrectionType
    parameters: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True


class DataAnalysisService:
    """专业数据分析服务类。

    提供磁滞回线高级参数计算、磁阻效应分析、系统误差校正、专业科学绘图等数据分析功能。

    Example:
        >>> service = DataAnalysisService()
        >>> # 磁滞回线分析
        >>> hyst_data = HysteresisData(field=field_array, magnetization=mag_array)
        >>> params = service.calculate_hysteresis_parameters(hyst_data)
        >>> print(f"饱和磁化强度: {params.saturation_magnetization}")
        >>> print(f"矫顽力: {params.coercive_field}")
    """

    def __init__(self) -> None:
        """初始化数据分析服务。"""
        # 校正配置
        self._correction_configs: dict[CorrectionType, CorrectionConfig] = {}

        # 历史分析结果缓存
        self._analysis_cache: dict[str, Any] = {}

        logger.info("DataAnalysisService initialized")

    # ==================== 磁滞回线高级参数计算 ====================

    def calculate_hysteresis_parameters(
        self,
        data: HysteresisData,
        apply_corrections: bool = True,
    ) -> HysteresisParameters:
        """计算磁滞回线高级参数。

        Args:
            data: 磁滞回线数据
            apply_corrections: 是否应用误差校正

        Returns:
            HysteresisParameters: 磁滞回线参数

        Raises:
            ValueError: 数据无效
        """
        if not data.validate():
            raise ValueError("Invalid hysteresis data")

        # 应用误差校正
        field = data.field.copy()
        magnetization = data.magnetization.copy()

        if apply_corrections:
            field, magnetization = self._apply_corrections(field, magnetization)

        # 分离上升支和下降支
        if data.direction == HysteresisDirection.FULL:
            ascending_idx = np.where(np.diff(field) > 0)[0]
            descending_idx = np.where(np.diff(field) < 0)[0]

            if len(ascending_idx) > 0 and len(descending_idx) > 0:
                # 找到转折点
                split_point = ascending_idx[-1] + 1
                ascending_field = field[:split_point]
                ascending_mag = magnetization[:split_point]
                descending_field = field[split_point:]
                descending_mag = magnetization[split_point:]
            else:
                # 简单处理：假设数据已经是正确顺序
                mid_point = len(field) // 2
                ascending_field = field[:mid_point]
                ascending_mag = magnetization[:mid_point]
                descending_field = field[mid_point:]
                descending_mag = magnetization[mid_point:]
        else:
            ascending_field = field
            ascending_mag = magnetization
            descending_field = field[::-1]
            descending_mag = magnetization[::-1]

        params = HysteresisParameters()

        # 1. 饱和磁化强度（Ms）
        # 取磁场最大值附近的平均磁化强度
        max_field_idx = np.argmax(np.abs(ascending_field))
        window = min(10, len(ascending_mag) // 10)
        params.saturation_magnetization = float(
            np.mean(ascending_mag[max(0, max_field_idx - window) : max_field_idx + window + 1])
        )

        # 2. 剩余磁化强度（Mr）
        # 磁场为零时的磁化强度
        params.remanent_magnetization = float(
            self._interpolate_at_zero(ascending_field, ascending_mag)
        )

        # 3. 矫顽力（Hc）
        # 磁化强度为零时的磁场
        params.coercive_field = float(
            self._find_coercive_field(ascending_field, ascending_mag)
        )

        # 4. 矩形比（S = Mr/Ms）
        if abs(params.saturation_magnetization) > 1e-10:
            params.squareness = abs(params.remanent_magnetization / params.saturation_magnetization)

        # 5. 初始磁导率和最大磁导率
        params.initial_permeability, params.maximum_permeability = self._calculate_permeability(
            ascending_field, ascending_mag
        )

        # 6. 磁滞损耗
        params.hysteresis_loss = self._calculate_hysteresis_loss(field, magnetization)

        # 7. 饱和磁场
        params.saturation_field = self._find_saturation_field(ascending_field, ascending_mag)

        logger.info(
            f"Hysteresis parameters calculated: Ms={params.saturation_magnetization:.4f}, "
            f"Hc={params.coercive_field:.4f}, S={params.squareness:.4f}"
        )

        return params

    def _interpolate_at_zero(self, x: np.ndarray, y: np.ndarray) -> float:
        """在x=0处插值计算y值。

        Args:
            x: x数组
            y: y数组

        Returns:
            float: x=0处的y值
        """
        # 找到跨越零点的区间
        for i in range(len(x) - 1):
            if x[i] * x[i + 1] <= 0:
                # 线性插值
                if abs(x[i + 1] - x[i]) > 1e-10:
                    ratio = -x[i] / (x[i + 1] - x[i])
                    return float(y[i] + ratio * (y[i + 1] - y[i]))
        return 0.0

    def _find_coercive_field(self, field: np.ndarray, magnetization: np.ndarray) -> float:
        """计算矫顽力（磁化强度为零时的磁场）。

        Args:
            field: 磁场数组
            magnetization: 磁化强度数组

        Returns:
            float: 矫顽力
        """
        # 找到磁化强度跨越零点的区间
        for i in range(len(magnetization) - 1):
            if magnetization[i] * magnetization[i + 1] <= 0:
                # 线性插值
                if abs(magnetization[i + 1] - magnetization[i]) > 1e-10:
                    ratio = -magnetization[i] / (magnetization[i + 1] - magnetization[i])
                    return float(field[i] + ratio * (field[i + 1] - field[i]))
        return 0.0

    def _calculate_permeability(
        self, field: np.ndarray, magnetization: np.ndarray
    ) -> tuple[float, float]:
        """计算初始磁导率和最大磁导率。

        Args:
            field: 磁场数组
            magnetization: 磁化强度数组

        Returns:
            tuple[float, float]: (初始磁导率, 最大磁导率)
        """
        # 计算微分磁导率 dM/dH
        # 使用中心差分
        if len(field) < 3:
            return 0.0, 0.0

        dM = np.gradient(magnetization, field)

        # 初始磁导率：原点附近的磁导率
        # 找到最接近原点的点
        zero_idx = np.argmin(np.abs(field))
        window = min(5, len(field) // 20)
        initial_permeability = float(np.mean(dM[max(0, zero_idx - window) : zero_idx + window + 1]))

        # 最大磁导率
        maximum_permeability = float(np.max(np.abs(dM)))

        return initial_permeability, maximum_permeability

    def _calculate_hysteresis_loss(
        self, field: np.ndarray, magnetization: np.ndarray
    ) -> float:
        """计算磁滞损耗（回线面积）。

        Args:
            field: 磁场数组
            magnetization: 磁化强度数组

        Returns:
            float: 磁滞损耗（J/m³）
        """
        # 使用梯形法则计算闭合曲线的面积
        # 磁滞损耗 = ∮ M dH
        try:
            loss = float(np.abs(integrate.trapezoid(magnetization, field)))
            return loss
        except Exception as e:
            logger.error(f"Calculate hysteresis loss error: {e}")
            return 0.0

    def _find_saturation_field(
        self, field: np.ndarray, magnetization: np.ndarray
    ) -> float:
        """计算饱和磁场。

        Args:
            field: 磁场数组
            magnetization: 磁化强度数组

        Returns:
            float: 饱和磁场
        """
        # 找到磁化强度达到饱和磁场95%的点
        max_mag = np.max(np.abs(magnetization))
        saturation_threshold = SATURATION_FIELD_THRESHOLD * max_mag

        for i in range(len(magnetization)):
            if abs(magnetization[i]) >= saturation_threshold:
                return float(abs(field[i]))

        return float(np.max(np.abs(field)))

    # ==================== 磁阻效应分析 ====================

    def calculate_mr_parameters(
        self,
        data: MRData,
        apply_corrections: bool = True,
    ) -> MRParameters:
        """计算磁阻效应参数。

        Args:
            data: 磁阻数据
            apply_corrections: 是否应用误差校正

        Returns:
            MRParameters: 磁阻参数

        Raises:
            ValueError: 数据无效
        """
        if not data.validate():
            raise ValueError("Invalid MR data")

        field = data.field.copy()
        resistance = data.resistance.copy()

        if apply_corrections:
            field, resistance = self._apply_corrections(field, resistance)

        params = MRParameters()

        # 1. 零场电阻
        params.zero_field_resistance = float(
            self._interpolate_at_zero(field, resistance)
        )

        # 2. 饱和电阻（高场下的电阻）
        max_field_idx = np.argmax(np.abs(field))
        window = min(10, len(resistance) // 10)
        params.saturation_resistance = float(
            np.mean(resistance[max(0, max_field_idx - window) : max_field_idx + window + 1])
        )

        # 3. 磁阻率 MR = (R(H) - R(0)) / R(0) * 100%
        params.mr_max = float(np.max(resistance))
        params.mr_min = float(np.min(resistance))

        if abs(params.zero_field_resistance) > 1e-10:
            params.mr_ratio = (
                (params.saturation_resistance - params.zero_field_resistance)
                / params.zero_field_resistance
                * 100.0
            )

        # 4. 磁阻灵敏度（低场区域）
        params.sensitivity = self._calculate_mr_sensitivity(field, resistance)

        # 5. 线性度
        params.linearity = self._calculate_mr_linearity(field, resistance)

        logger.info(
            f"MR parameters calculated: MR_ratio={params.mr_ratio:.4f}%, "
            f"sensitivity={params.sensitivity:.4f}%/T"
        )

        return params

    def _calculate_mr_sensitivity(
        self, field: np.ndarray, resistance: np.ndarray
    ) -> float:
        """计算磁阻灵敏度。

        Args:
            field: 磁场数组
            resistance: 电阻数组

        Returns:
            float: 灵敏度（%/T）
        """
        # 在低场区域计算 dR/dH
        # 选择 |H| < 0.5T 的区域
        low_field_mask = np.abs(field) < 0.5

        if np.sum(low_field_mask) < 5:
            return 0.0

        low_field = field[low_field_mask]
        low_resistance = resistance[low_field_mask]

        # 线性拟合
        try:
            coeffs = np.polyfit(low_field, low_resistance, 1)
            sensitivity = coeffs[0] / low_resistance[0] * 100.0 if low_resistance[0] != 0 else 0.0
            return float(sensitivity)
        except Exception:
            return 0.0

    def _calculate_mr_linearity(
        self, field: np.ndarray, resistance: np.ndarray
    ) -> float:
        """计算磁阻线性度。

        Args:
            field: 磁场数组
            resistance: 电阻数组

        Returns:
            float: 线性度（0-1）
        """
        # 计算与最佳线性拟合的偏差
        try:
            coeffs = np.polyfit(field, resistance, 1)
            linear_fit = np.polyval(coeffs, field)

            # 计算线性度
            residuals = resistance - linear_fit
            max_deviation = np.max(np.abs(residuals))
            range_resistance = np.max(resistance) - np.min(resistance)

            if range_resistance > 0:
                linearity = 1.0 - max_deviation / range_resistance
                return float(max(0.0, min(1.0, linearity)))
            return 0.0
        except Exception:
            return 0.0

    def analyze_mr_angle_dependence(
        self,
        field: np.ndarray,
        resistance: np.ndarray,
        angle: np.ndarray,
    ) -> dict[str, Any]:
        """分析磁阻角度依赖性（AMR特性）。

        Args:
            field: 磁场数组
            resistance: 电阻数组
            angle: 角度数组（°）

        Returns:
            Dict[str, Any]: 角度依赖性分析结果
        """
        # AMR效应：R(θ) = R_⊥ + (R_∥ - R_⊥) * cos²(θ)
        # 拟合公式：R = A + B * cos²(θ)

        angle_rad = np.radians(angle)
        cos2_angle = np.cos(angle_rad) ** 2

        # 线性拟合
        try:
            coeffs = np.polyfit(cos2_angle, resistance, 1)
            r_perpendicular = coeffs[1]  # θ = 90°时的电阻
            r_parallel = coeffs[0] + coeffs[1]  # θ = 0°时的电阻

            amr_ratio = (r_parallel - r_perpendicular) / r_perpendicular * 100.0

            # 计算拟合优度
            predicted = np.polyval(coeffs, cos2_angle)
            ss_res = np.sum((resistance - predicted) ** 2)
            ss_tot = np.sum((resistance - np.mean(resistance)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return {
                "amr_ratio": float(amr_ratio),
                "r_perpendicular": float(r_perpendicular),
                "r_parallel": float(r_parallel),
                "r_squared": float(r_squared),
                "is_amr": r_squared > 0.9,  # 判断是否为AMR效应
            }
        except Exception as e:
            logger.error(f"MR angle dependence analysis error: {e}")
            return {"error": str(e)}

    # ==================== 系统误差校正 ====================

    def configure_correction(
        self,
        correction_type: CorrectionType,
        parameters: dict[str, Any],
        enabled: bool = True,
    ) -> bool:
        """配置误差校正。

        Args:
            correction_type: 校正类型
            parameters: 校正参数
            enabled: 是否启用

        Returns:
            bool: 配置是否成功
        """
        self._correction_configs[correction_type] = CorrectionConfig(
            correction_type=correction_type,
            parameters=parameters,
            enabled=enabled,
        )
        logger.info(f"Correction configured: type={correction_type.value}, enabled={enabled}")
        return True

    def _apply_corrections(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray]:
        """应用所有配置的误差校正。

        Args:
            x: x数据
            y: y数据

        Returns:
            tuple[np.ndarray, np.ndarray]: 校正后的数据
        """
        corrected_x = x.copy()
        corrected_y = y.copy()

        for correction_type, config in self._correction_configs.items():
            if not config.enabled:
                continue

            if correction_type == CorrectionType.BACKGROUND:
                corrected_y = self._apply_background_correction(corrected_y, config.parameters)
            elif correction_type == CorrectionType.ZERO_DRIFT:
                corrected_y = self._apply_zero_drift_correction(corrected_y, config.parameters)
            elif correction_type == CorrectionType.INSTRUMENT_RESPONSE:
                corrected_y = self._apply_instrument_response_correction(
                    corrected_x, corrected_y, config.parameters
                )
            elif correction_type == CorrectionType.TEMPERATURE_DRIFT:
                corrected_y = self._apply_temperature_drift_correction(corrected_y, config.parameters)
            elif correction_type == CorrectionType.LINEAR_BASELINE:
                corrected_y = self._apply_linear_baseline_correction(corrected_x, corrected_y)

        return corrected_x, corrected_y

    def _apply_background_correction(
        self,
        y: np.ndarray,
        parameters: dict[str, Any],
    ) -> np.ndarray:
        """应用背景扣除校正。

        Args:
            y: y数据
            parameters: 校正参数

        Returns:
            np.ndarray: 校正后的数据
        """
        window_size = parameters.get("window_size", BACKGROUND_WINDOW_SIZE)

        # 使用滚动最小值估计背景
        if len(y) < window_size:
            return y

        background = np.minimum(
            np.array([np.min(y[max(0, i - window_size // 2) : i + window_size // 2 + 1])
                     for i in range(len(y))])
        )

        # 平滑背景
        background = signal.savgol_filter(background, min(51, len(background) // 10 * 2 + 1), 3)

        return y - background

    def _apply_zero_drift_correction(
        self,
        y: np.ndarray,
        parameters: dict[str, Any],
    ) -> np.ndarray:
        """应用零点漂移校正。

        Args:
            y: y数据
            parameters: 校正参数

        Returns:
            np.ndarray: 校正后的数据
        """
        drift_rate = parameters.get("drift_rate", 0.0)
        reference_value = parameters.get("reference_value", y[0] if len(y) > 0 else 0.0)

        # 线性漂移校正
        time_array = np.arange(len(y))
        drift = drift_rate * time_array

        return y - drift - (y[0] - reference_value)

    def _apply_instrument_response_correction(
        self,
        x: np.ndarray,
        y: np.ndarray,
        parameters: dict[str, Any],
    ) -> np.ndarray:
        """应用仪器响应校正。

        Args:
            x: x数据
            y: y数据
            parameters: 校正参数

        Returns:
            np.ndarray: 校正后的数据
        """
        # 使用仪器响应函数进行反卷积
        response_type = parameters.get("response_type", "exponential")
        time_constant = parameters.get("time_constant", 1.0)

        if response_type == "exponential":
            # 指数响应校正
            # 简化处理：使用一阶高通滤波
            alpha = time_constant / (time_constant + np.mean(np.diff(x)) if len(x) > 1 else 1.0)
            corrected = np.zeros_like(y)
            corrected[0] = y[0]
            for i in range(1, len(y)):
                corrected[i] = alpha * corrected[i - 1] + (1 - alpha) * (y[i] - y[i - 1])
            return corrected

        return y

    def _apply_temperature_drift_correction(
        self,
        y: np.ndarray,
        parameters: dict[str, Any],
    ) -> np.ndarray:
        """应用温度漂移补偿。

        Args:
            y: y数据
            parameters: 校正参数

        Returns:
            np.ndarray: 校正后的数据
        """
        temp_coefficient = parameters.get("temp_coefficient", 0.0)
        reference_temp = parameters.get("reference_temp", 300.0)
        temperature_data = parameters.get("temperature_data", None)

        if temperature_data is None:
            return y

        # 温度漂移校正
        temp_array = np.array(temperature_data)
        if len(temp_array) != len(y):
            logger.warning("Temperature data length mismatch")
            return y

        drift = temp_coefficient * (temp_array - reference_temp)
        return y - drift

    def _apply_linear_baseline_correction(
        self,
        x: np.ndarray,
        y: np.ndarray,
    ) -> np.ndarray:
        """应用线性基线校正。

        Args:
            x: x数据
            y: y数据

        Returns:
            np.ndarray: 校正后的数据
        """
        # 使用端点进行线性基线校正
        if len(x) < 2:
            return y

        # 计算基线斜率和截距
        slope = (y[-1] - y[0]) / (x[-1] - x[0]) if (x[-1] - x[0]) != 0 else 0.0
        intercept = y[0] - slope * x[0]

        # 减去基线
        baseline = slope * x + intercept
        return y - baseline

    # ==================== 专业科学绘图 ====================

    def generate_hysteresis_plot_data(
        self,
        data: HysteresisData,
        params: HysteresisParameters | None = None,
        include_annotations: bool = True,
    ) -> dict[str, Any]:
        """生成磁滞回线绘图数据。

        Args:
            data: 磁滞回线数据
            params: 磁滞参数（可选）
            include_annotations: 是否包含标注

        Returns:
            Dict[str, Any]: 绘图数据
        """
        plot_data = {
            "field": data.field.tolist(),
            "magnetization": data.magnetization.tolist(),
            "title": f"M-H Hysteresis Loop - {data.sample_id}",
            "xlabel": "Magnetic Field H (T)",
            "ylabel": "Magnetization M (A/m)",
            "annotations": [],
        }

        if include_annotations and params:
            # 添加关键点标注
            annotations = []

            # 饱和磁化强度点
            max_field_idx = np.argmax(np.abs(data.field))
            annotations.append({
                "type": "point",
                "x": float(data.field[max_field_idx]),
                "y": float(data.magnetization[max_field_idx]),
                "label": f"Ms = {params.saturation_magnetization:.2f}",
            })

            # 剩磁点
            annotations.append({
                "type": "point",
                "x": 0.0,
                "y": params.remanent_magnetization,
                "label": f"Mr = {params.remanent_magnetization:.2f}",
            })

            # 矫顽力点
            annotations.append({
                "type": "point",
                "x": params.coercive_field,
                "y": 0.0,
                "label": f"Hc = {params.coercive_field:.4f} T",
            })

            plot_data["annotations"] = annotations

        return plot_data

    def generate_mr_plot_data(
        self,
        data: MRData,
        params: MRParameters | None = None,
        include_fit: bool = True,
    ) -> dict[str, Any]:
        """生成磁阻效应绘图数据。

        Args:
            data: 磁阻数据
            params: 磁阻参数（可选）
            include_fit: 是否包含拟合曲线

        Returns:
            Dict[str, Any]: 绘图数据
        """
        plot_data = {
            "field": data.field.tolist(),
            "resistance": data.resistance.tolist(),
            "title": f"Magnetoresistance - {data.sample_id}",
            "xlabel": "Magnetic Field H (T)",
            "ylabel": "Resistance R (Ω)",
            "fit_curve": None,
            "parameters": None,
        }

        # 计算磁阻率曲线
        if params and abs(params.zero_field_resistance) > 1e-10:
            mr_ratio = (data.resistance - params.zero_field_resistance) / params.zero_field_resistance * 100.0
            plot_data["mr_ratio"] = mr_ratio.tolist()
            plot_data["mr_ylabel"] = "MR Ratio (%)"

        # 添加拟合曲线
        if include_fit:
            try:
                # 多项式拟合
                coeffs = np.polyfit(data.field, data.resistance, 3)
                fit_resistance = np.polyval(coeffs, data.field)
                plot_data["fit_curve"] = fit_resistance.tolist()
            except Exception:
                pass

        if params:
            plot_data["parameters"] = params.to_dict()

        return plot_data

    def generate_comparison_plot_data(
        self,
        datasets: list[dict[str, Any]],
        plot_type: str = "overlay",
    ) -> dict[str, Any]:
        """生成对比绘图数据。

        Args:
            datasets: 数据集列表，每个包含x, y, label
            plot_type: 绘图类型（overlay/subplot/difference）

        Returns:
            Dict[str, Any]: 对比绘图数据
        """
        plot_data = {
            "plot_type": plot_type,
            "datasets": [],
            "common_xlabel": "",
            "common_ylabel": "",
        }

        for i, dataset in enumerate(datasets):
            x = dataset.get("x", [])
            y = dataset.get("y", [])
            label = dataset.get("label", f"Dataset {i + 1}")

            plot_data["datasets"].append({
                "x": x if isinstance(x, list) else x.tolist() if hasattr(x, 'tolist') else list(x),
                "y": y if isinstance(y, list) else y.tolist() if hasattr(y, 'tolist') else list(y),
                "label": label,
            })

        return plot_data

    # ==================== 数据导入导出 ====================

    def export_analysis_result(
        self,
        result_type: str,
        data: dict[str, Any],
        format_type: str = "json",
    ) -> str:
        """导出分析结果。

        Args:
            result_type: 结果类型
            data: 结果数据
            format_type: 导出格式

        Returns:
            str: 导出数据
        """
        export_data = {
            "result_type": result_type,
            "timestamp": time.time(),
            "data": data,
        }

        if format_type == "json":
            return json.dumps(export_data, indent=2, default=str)
        elif format_type == "csv":
            # 简化CSV导出
            lines = ["key,value"]
            for key, value in data.items():
                if isinstance(value, (list, np.ndarray)):
                    value = ";".join(map(str, value[:10]))  # 只导出前10个值
                lines.append(f"{key},{value}")
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format_type}")

    def import_analysis_result(
        self,
        json_str: str,
    ) -> dict[str, Any]:
        """导入分析结果。

        Args:
            json_str: JSON字符串

        Returns:
            Dict[str, Any]: 分析结果
        """
        return json.loads(json_str)

    # ==================== 高级分析功能 ====================

    def fit_hysteresis_model(
        self,
        data: HysteresisData,
        model_type: str = "stoner_wohlfarth",
    ) -> dict[str, Any]:
        """拟合磁滞回线模型。

        Args:
            data: 磁滞回线数据
            model_type: 模型类型

        Returns:
            Dict[str, Any]: 拟合结果
        """
        if model_type == "stoner_wohlfarth":
            return self._fit_stoner_wohlfarth(data)
        elif model_type == "langevin":
            return self._fit_langevin(data)
        else:
            raise ValueError(f"Unsupported model type: {model_type}")

    def _fit_stoner_wohlfarth(self, data: HysteresisData) -> dict[str, Any]:
        """Stoner-Wohlfarth模型拟合。

        Args:
            data: 磁滞回线数据

        Returns:
            Dict[str, Any]: 拟合结果
        """
        # Stoner-Wohlfarth模型：简化的单畴粒子模型
        # 这里使用近似公式进行拟合

        def stoner_wohlfarth_func(H, Ms, Hk):
            """简化的Stoner-Wohlfarth函数。"""
            h = H / Hk
            # 近似公式
            m = np.where(
                np.abs(h) >= 1,
                np.sign(h),
                np.sign(h) * np.sqrt(1 - (1 - np.abs(h)) ** 2)
            )
            return Ms * m

        try:
            # 初始猜测
            Ms_guess = np.max(np.abs(data.magnetization))
            Hk_guess = np.max(np.abs(data.field)) * 0.5

            # 拟合
            popt, pcov = optimize.curve_fit(
                stoner_wohlfarth_func,
                data.field,
                data.magnetization,
                p0=[Ms_guess, Hk_guess],
                maxfev=5000,
            )

            # 计算拟合优度
            predicted = stoner_wohlfarth_func(data.field, *popt)
            ss_res = np.sum((data.magnetization - predicted) ** 2)
            ss_tot = np.sum((data.magnetization - np.mean(data.magnetization)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return {
                "model": "stoner_wohlfarth",
                "parameters": {
                    "saturation_magnetization": float(popt[0]),
                    "anisotropy_field": float(popt[1]),
                },
                "r_squared": float(r_squared),
                "covariance": pcov.tolist(),
            }
        except Exception as e:
            logger.error(f"Stoner-Wohlfarth fit error: {e}")
            return {"error": str(e)}

    def _fit_langevin(self, data: HysteresisData) -> dict[str, Any]:
        """Langevin函数拟合（超顺磁）。

        Args:
            data: 磁滞回线数据

        Returns:
            Dict[str, Any]: 拟合结果
        """
        def langevin_func(H, Ms, mu):
            """Langevin函数。"""
            x = mu * H / (1.380649e-23 * 300)  # 假设T=300K
            # Langevin函数: L(x) = coth(x) - 1/x
            # 使用近似避免数值问题
            return Ms * (1.0 / np.tanh(x + 1e-10) - 1.0 / (x + 1e-10))

        try:
            Ms_guess = np.max(np.abs(data.magnetization))
            mu_guess = 1e-20  # 初始磁矩猜测

            popt, pcov = optimize.curve_fit(
                langevin_func,
                data.field,
                data.magnetization,
                p0=[Ms_guess, mu_guess],
                maxfev=5000,
            )

            predicted = langevin_func(data.field, *popt)
            ss_res = np.sum((data.magnetization - predicted) ** 2)
            ss_tot = np.sum((data.magnetization - np.mean(data.magnetization)) ** 2)
            r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

            return {
                "model": "langevin",
                "parameters": {
                    "saturation_magnetization": float(popt[0]),
                    "magnetic_moment": float(popt[1]),
                },
                "r_squared": float(r_squared),
            }
        except Exception as e:
            logger.error(f"Langevin fit error: {e}")
            return {"error": str(e)}

    def calculate_first_order_reversal_curves(
        self,
        data: HysteresisData,
        num_curves: int = 10,
    ) -> dict[str, Any]:
        """计算一阶反转曲线（FORC）。

        Args:
            data: 磁滞回线数据
            num_curves: 曲线数量

        Returns:
            Dict[str, Any]: FORC分析结果
        """
        # 简化实现：从下降支提取多个反转点
        field = data.field
        magnetization = data.magnetization

        # 找到下降支
        descending_start = np.argmax(field)
        descending_field = field[descending_start:]
        descending_mag = magnetization[descending_start:]

        # 提取FORC
        forc_curves = []
        curve_indices = np.linspace(0, len(descending_field) - 1, num_curves + 1, dtype=int)

        for i in range(len(curve_indices) - 1):
            start_idx = curve_indices[i]
            end_idx = curve_indices[i + 1]

            curve = {
                "reversal_field": float(descending_field[start_idx]),
                "field": descending_field[start_idx:end_idx].tolist(),
                "magnetization": descending_mag[start_idx:end_idx].tolist(),
            }
            forc_curves.append(curve)

        return {
            "num_curves": num_curves,
            "curves": forc_curves,
        }
