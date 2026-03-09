"""
物理数据分析引擎 (Physics Analysis Engine)

本模块实现了自旋电子器件实验的数据分析功能，包括：
- PhysicsAnalyzer: 主分析类
- 信号平滑处理：Savitzky-Golay 滤波和巴特沃斯低通滤波
- 磁滞回线分析：背景扣除、矫顽力、剩磁、饱和磁矩计算
- 基于 lmfit 的曲线拟合（线性、多项式、指数、高斯、Langevin、Braunbeck）
- 多模型并行拟合与比较
- 拟合优度评估（R²、RMSE、AIC、BIC）
- 分析报告自动生成
- 数据导出：CSV、HDF5、JSON 格式

设计参考：技术设计文档第9章节

作者: Agent
创建日期: 2024-03-07
依赖: numpy, scipy, lmfit, h5py
"""

import json
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import h5py
import lmfit
import numpy as np
from scipy import optimize, signal


class BackgroundMethod(str, Enum):
    """背景扣除方法枚举。"""

    LINEAR = "linear"
    POLYNOMIAL = "polynomial"


class FitModelType(str, Enum):
    """拟合模型类型枚举。"""

    LINEAR = "linear"
    POLYNOMIAL = "polynomial"
    EXPONENTIAL = "exponential"
    GAUSSIAN = "gaussian"
    LANGEVIN = "langevin"
    BRAUNBECK = "braunbeck"


@dataclass
class FitResult:
    """拟合结果数据类。

    存储单个模型的拟合结果，包括参数、拟合优度指标和残差。

    Attributes:
        model_name: 模型名称
        params: 拟合参数字典
        r_squared: R²决定系数
        rmse: 均方根误差
        mae: 平均绝对误差
        aic: Akaike信息准则
        bic: 贝叶斯信息准则
        residuals: 残差数组
        y_predicted: 预测值数组
        n_params: 参数数量
        n_data_points: 数据点数量
    """

    model_name: str
    params: dict[str, float]
    r_squared: float
    rmse: float
    mae: float
    aic: float
    bic: float
    residuals: np.ndarray
    y_predicted: np.ndarray
    n_params: int = 0
    n_data_points: int = 0


@dataclass
class AnalysisReport:
    """分析报告数据类。

    存储完整的磁滞回线分析报告。

    Attributes:
        experiment_id: 实验ID
        timestamp: 时间戳
        hysteresis_params: 磁滞回线参数字典
        fit_results: 拟合结果列表
        best_model: 最佳模型名称
        quality_metrics: 质量指标字典
        recommendations: 推荐建议列表
    """

    experiment_id: str
    timestamp: str
    hysteresis_params: dict[str, Any]
    fit_results: list[FitResult]
    best_model: str
    quality_metrics: dict[str, float]
    recommendations: list[str] = field(default_factory=list)


class ExportFormat(str, Enum):
    """数据导出格式枚举。"""

    CSV = "csv"
    HDF5 = "hdf5"
    JSON = "json"


class PhysicsAnalyzer:
    """物理数据分析引擎。

    用于处理自旋电子学实验数据的核心分析类，提供信号处理和磁滞回线分析功能。
    """

    def __init__(self):
        """初始化物理分析引擎。"""
        self.data_buffer: np.ndarray | None = None
        self.metadata: dict[str, Any] = {}

    def load_data(
        self, x_data: np.ndarray, y_data: np.ndarray, metadata: dict[str, Any] | None = None
    ) -> None:
        """加载实验数据。

        Args:
            x_data: X轴数据数组（如磁场强度）
            y_data: Y轴数据数组（如磁矩）
            metadata: 可选的元数据字典
        """
        self.data_buffer = np.column_stack((x_data, y_data))
        if metadata is not None:
            self.metadata = metadata.copy()

    def smooth_signal(
        self,
        y_data: np.ndarray,
        method: str = "savgol",
        window_length: int = 11,
        polyorder: int = 2,
        **kwargs,
    ) -> np.ndarray:
        """信号平滑处理。

        支持两种平滑方法：
        - Savitzky-Golay 滤波（局部多项式拟合平滑
        - 巴特沃斯低通滤波（频域滤波平滑

        Args:
            y_data: 待平滑的信号数据
            method: 平滑方法，可选 "savgol" 或 "butter"
            window_length: 窗口长度，必须为奇数
            polyorder: 多项式阶数
            **kwargs: 额外参数
                - butter_lowcut: 巴特沃斯低通截止频率（归一化 0-1）
                - butter_order: 巴特沃斯滤波器阶数

        Returns:
            平滑后的信号数据

        Raises:
            ValueError: 当参数无效时抛出异常
        """
        # 输入数据验证
        if y_data is None or len(y_data) == 0:
            raise ValueError("y_data 不能为空")
        if len(y_data) < 3:
            warnings.warn("数据点数不足3，返回原始数据")
            return y_data.copy()

        if method == "savgol":
            if window_length % 2 == 0:
                raise ValueError("window_length 必须为奇数")
            if window_length < 3:
                raise ValueError("window_length 必须大于等于3")
            if polyorder >= window_length:
                raise ValueError("polyorder 必须小于 window_length")
            if window_length > len(y_data):
                raise ValueError("window_length 不能大于数据长度")
            return signal.savgol_filter(y_data, window_length, polyorder)

        elif method == "butter":
            lowcut = kwargs.get("butter_lowcut", 0.1)
            order = kwargs.get("butter_order", 3)

            # 参数验证
            if not 0 < lowcut < 1:
                raise ValueError(f"butter_lowcut 必须在 (0, 1) 范围内，当前值: {lowcut}")
            if order < 1:
                raise ValueError(f"butter_order 必须大于等于1，当前值: {order}")

            # 使用二阶节(sos)格式提高数值稳定性
            sos = signal.butter(order, lowcut, btype="low", output="sos")
            return signal.sosfiltfilt(sos, y_data)

        else:
            raise ValueError(f"不支持的平滑方法: {method}")

    def butterworth_filter(
        self, y_data: np.ndarray, cutoff: float, fs: float, order: int = 3
    ) -> np.ndarray:
        """巴特沃斯低通滤波器。

        使用采样率和截止频率的完整实现。

        Args:
            y_data: 待滤波的信号数据
            cutoff: 截止频率（Hz）
            fs: 采样率（Hz）
            order: 滤波器阶数

        Returns:
            滤波后的信号数据

        Raises:
            ValueError: 当参数无效时抛出异常
        """
        # 输入数据验证
        if y_data is None or len(y_data) == 0:
            raise ValueError("y_data 不能为空")
        if fs <= 0:
            raise ValueError(f"采样率 fs 必须大于0，当前值: {fs}")
        if cutoff <= 0:
            raise ValueError(f"截止频率 cutoff 必须大于0，当前值: {cutoff}")
        if order < 1:
            raise ValueError(f"滤波器阶数 order 必须大于等于1，当前值: {order}")

        nyquist = 0.5 * fs
        normal_cutoff = cutoff / nyquist

        # 验证归一化截止频率在有效范围内
        if not 0 < normal_cutoff < 1:
            raise ValueError(
                f"归一化截止频率必须在 (0, 1) 范围内，当前值: {normal_cutoff}。"
                f"请确保 cutoff < fs/2 (Nyquist频率)"
            )

        # 使用二阶节(sos)格式提高数值稳定性
        sos = signal.butter(order, normal_cutoff, btype="low", output="sos")
        return signal.sosfiltfilt(sos, y_data)

    def subtract_background(
        self,
        x_field: np.ndarray,
        y_moment: np.ndarray,
        method: BackgroundMethod = BackgroundMethod.LINEAR,
        high_field_threshold: float | None = None,
        polynomial_order: int = 2,
    ) -> tuple[np.ndarray, np.ndarray, dict[str, Any]]:
        """背景扣除。

        通过拟合高场区数据，扣除背景信号（源于顺磁/抗磁杂质）。
        支持线性背景和多项式背景扣除。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组
            method: 背景扣除方法，LINEAR（线性）或 POLYNOMIAL（多项式）
            high_field_threshold: 高场阈值，默认取磁场绝对值最大值的 80%
            polynomial_order: 多项式阶数，仅当 method=POLYNOMIAL 时有效

        Returns:
            元组：(扣除背景后的磁场, 扣除背景后的磁矩, 拟合参数字典)
                拟合参数包含：
                - coefficients: 拟合系数数组
                - r_squared: R²值
                - method: 使用的方法
        """
        if high_field_threshold is None:
            high_field_threshold = np.max(np.abs(x_field)) * 0.8

        high_field_mask = np.abs(x_field) >= high_field_threshold

        if np.sum(high_field_mask) < 2:
            warnings.warn("高场数据点不足，无法拟合背景")
            return (
                x_field,
                y_moment,
                {"coefficients": [0.0], "r_squared": 1.0, "method": method.value},
            )

        x_high = x_field[high_field_mask]
        y_high = y_moment[high_field_mask]

        # 根据方法选择拟合阶数
        fit_order = 1 if method == BackgroundMethod.LINEAR else polynomial_order

        # 确保数据点足够拟合
        if np.sum(high_field_mask) < fit_order + 1:
            warnings.warn(f"数据点不足，无法进行{fit_order}阶拟合，降级为线性拟合")
            fit_order = 1

        # 多项式拟合
        coefficients = np.polyfit(x_high, y_high, fit_order)

        # 计算拟合背景
        background = np.polyval(coefficients, x_field)

        # 扣除背景
        y_corrected = y_moment - background

        # 计算 R² 值
        y_mean = np.mean(y_high)
        ss_tot = np.sum((y_high - y_mean) ** 2)
        y_fit = np.polyval(coefficients, x_high)
        ss_res = np.sum((y_high - y_fit) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0

        fit_params = {
            "coefficients": coefficients.tolist(),
            "r_squared": float(r_squared),
            "method": method.value,
            "polynomial_order": fit_order,
        }

        return x_field, y_corrected, fit_params

    def _calculate_coercivity(self, x_field: np.ndarray, y_moment: np.ndarray) -> float:
        """计算矫顽力 Hc。

        矫顽力是磁矩 M=0 时对应的磁场值，通过插值法精确计算。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组

        Returns:
            矫顽力 Hc
        """
        result = self._calculate_coercivity_detailed(x_field, y_moment)
        return result["Hc"]

    def _calculate_coercivity_detailed(
        self, x_field: np.ndarray, y_moment: np.ndarray
    ) -> dict[str, float]:
        """详细计算矫顽力 Hc。

        矫顽力是磁矩 M=0 时对应的磁场值，通过插值法精确计算。
        分别计算正向和负向矫顽力。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组

        Returns:
            包含以下键的字典：
                - Hc: 平均矫顽力（绝对值）
                - Hc_positive: 正向矫顽力（磁矩从正到负穿过零点）
                - Hc_negative: 负向矫顽力（磁矩从负到正穿过零点）
        """
        sign_changes = np.where(np.diff(np.sign(y_moment)))[0]

        if len(sign_changes) == 0:
            warnings.warn("未找到磁矩过零点，无法计算矫顽力")
            return {"Hc": 0.0, "Hc_positive": 0.0, "Hc_negative": 0.0}

        hc_values = []
        for idx in sign_changes:
            x1, x2 = x_field[idx], x_field[idx + 1]
            y1, y2 = y_moment[idx], y_moment[idx + 1]
            if y2 != y1:
                hc = x1 - y1 * (x2 - x1) / (y2 - y1)
                hc_values.append(hc)

        if len(hc_values) == 0:
            return {"Hc": 0.0, "Hc_positive": 0.0, "Hc_negative": 0.0}

        # 区分正向和负向矫顽力
        hc_positive = 0.0
        hc_negative = 0.0

        for i, hc in enumerate(hc_values):
            idx = sign_changes[i] if i < len(sign_changes) else sign_changes[-1]
            # 判断穿越方向：y1 > 0 表示从正到负
            if y_moment[idx] > 0:
                hc_positive = abs(hc)
            else:
                hc_negative = abs(hc)

        # 如果只有一个过零点，使用该值
        if hc_positive == 0.0 and hc_negative == 0.0:
            hc_avg = np.mean(np.abs(hc_values))
            return {"Hc": float(hc_avg), "Hc_positive": float(hc_avg), "Hc_negative": float(hc_avg)}

        # 平均矫顽力
        hc_avg = (
            (hc_positive + hc_negative) / 2
            if (hc_positive > 0 and hc_negative > 0)
            else max(hc_positive, hc_negative)
        )

        return {
            "Hc": float(hc_avg),
            "Hc_positive": float(hc_positive),
            "Hc_negative": float(hc_negative),
        }

    def _calculate_remanence(self, x_field: np.ndarray, y_moment: np.ndarray) -> float:
        """计算剩磁 Mr。

        剩磁是磁场 H=0 时的磁矩平均值。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组

        Returns:
            剩磁 Mr
        """
        result = self._calculate_remanence_detailed(x_field, y_moment)
        return result["Mr"]

    def _calculate_remanence_detailed(
        self, x_field: np.ndarray, y_moment: np.ndarray
    ) -> dict[str, float]:
        """详细计算剩磁 Mr。

        剩磁是磁场 H=0 时的磁矩值。
        分别计算正向和负向剩磁。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组

        Returns:
            包含以下键的字典：
                - Mr: 平均剩磁（绝对值）
                - Mr_positive: 正向剩磁（磁场从正到负穿过零点时的磁矩）
                - Mr_negative: 负向剩磁（磁场从负到正穿过零点时的磁矩）
        """
        zero_field_mask = np.isclose(x_field, 0.0, atol=1e-6)

        if np.sum(zero_field_mask) > 0:
            mr_value = float(np.mean(y_moment[zero_field_mask]))
            return {"Mr": abs(mr_value), "Mr_positive": mr_value, "Mr_negative": mr_value}

        sign_changes = np.where(np.diff(np.sign(x_field)))[0]

        if len(sign_changes) == 0:
            warnings.warn("未找到磁场过零点，无法计算剩磁")
            return {"Mr": 0.0, "Mr_positive": 0.0, "Mr_negative": 0.0}

        mr_values = []
        for idx in sign_changes:
            x1, x2 = x_field[idx], x_field[idx + 1]
            y1, y2 = y_moment[idx], y_moment[idx + 1]
            if x2 != x1:
                mr = y1 + (0.0 - x1) * (y2 - y1) / (x2 - x1)
                mr_values.append(mr)

        if len(mr_values) == 0:
            return {"Mr": 0.0, "Mr_positive": 0.0, "Mr_negative": 0.0}

        # 区分正向和负向剩磁
        mr_positive = 0.0
        mr_negative = 0.0

        for i, mr in enumerate(mr_values):
            idx = sign_changes[i] if i < len(sign_changes) else sign_changes[-1]
            # 判断穿越方向：x1 > 0 表示从正到负
            if x_field[idx] > 0:
                mr_positive = mr
            else:
                mr_negative = mr

        # 如果只有一个过零点，使用该值
        if mr_positive == 0.0 and mr_negative == 0.0:
            mr_avg = float(np.mean(np.abs(mr_values)))
            return {
                "Mr": mr_avg,
                "Mr_positive": float(mr_values[0]),
                "Mr_negative": float(mr_values[0]),
            }

        # 平均剩磁
        mr_avg = (abs(mr_positive) + abs(mr_negative)) / 2

        return {
            "Mr": float(mr_avg),
            "Mr_positive": float(mr_positive),
            "Mr_negative": float(mr_negative),
        }

    def _calculate_saturation_moment(
        self,
        x_field: np.ndarray,
        y_moment: np.ndarray,
        saturation_threshold: float | None = None,
    ) -> float:
        """计算饱和磁矩 Ms。

        饱和磁矩是高场区磁矩的平均值。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组
            saturation_threshold: 饱和场阈值，默认取磁场绝对值最大值的 80%

        Returns:
            饱和磁矩 Ms
        """
        if saturation_threshold is None:
            saturation_threshold = np.max(np.abs(x_field)) * 0.8

        saturation_mask = np.abs(x_field) >= saturation_threshold

        if np.sum(saturation_mask) == 0:
            warnings.warn("未找到饱和场区数据点")
            return np.max(np.abs(y_moment))

        return np.mean(np.abs(y_moment[saturation_mask]))

    def analyze_hysteresis_loop(
        self,
        x_field: np.ndarray,
        y_moment: np.ndarray,
        subtract_background: bool = True,
        background_method: BackgroundMethod = BackgroundMethod.LINEAR,
        saturation_threshold: float | None = None,
        polynomial_order: int = 2,
    ) -> dict[str, Any]:
        """分析磁滞回线。

        完整的磁滞回线分析，包括背景扣除和关键参数提取。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组
            subtract_background: 是否扣除背景，默认为 True
            background_method: 背景扣除方法，LINEAR 或 POLYNOMIAL
            saturation_threshold: 饱和场阈值
            polynomial_order: 多项式阶数（仅当 background_method=POLYNOMIAL 时有效）

        Returns:
            包含分析结果的字典，包括：
                - Hc: 矫顽力（磁场为零时的磁矩）
                - Mr: 剩磁（磁矩为零时的磁场）
                - Ms: 饱和磁矩
                - Hc_positive: 正向矫顽力
                - Hc_negative: 负向矫顽力
                - Mr_positive: 正向剩磁
                - Mr_negative: 负向剩磁
                - squareness: 矩形比 (Mr/Ms)
                - background_params: 背景拟合参数
                - x_corrected: 扣除背景后的磁场
                - y_corrected: 扣除背景后的磁矩
        """
        x_corrected = x_field.copy()
        y_corrected = y_moment.copy()
        background_params: dict[str, Any] = {}

        if subtract_background:
            x_corrected, y_corrected, background_params = self.subtract_background(
                x_field, y_moment, method=background_method, polynomial_order=polynomial_order
            )

        # 计算矫顽力（磁矩为零时的磁场）
        hc_result = self._calculate_coercivity_detailed(x_corrected, y_corrected)

        # 计算剩磁（磁场为零时的磁矩）
        mr_result = self._calculate_remanence_detailed(x_corrected, y_corrected)

        # 计算饱和磁矩
        ms = self._calculate_saturation_moment(x_corrected, y_corrected, saturation_threshold)

        # 计算矩形比
        squareness = mr_result["Mr"] / ms if ms > 0 else 0.0

        return {
            "Hc": hc_result["Hc"],
            "Hc_positive": hc_result["Hc_positive"],
            "Hc_negative": hc_result["Hc_negative"],
            "Mr": mr_result["Mr"],
            "Mr_positive": mr_result["Mr_positive"],
            "Mr_negative": mr_result["Mr_negative"],
            "Ms": ms,
            "squareness": float(squareness),
            "background_params": background_params,
            "x_corrected": x_corrected,
            "y_corrected": y_corrected,
        }

    def fit_langevin(
        self, x_field: np.ndarray, y_moment: np.ndarray
    ) -> tuple[lmfit.model.ModelResult, dict[str, float]]:
        """使用 Langevin 函数拟合磁化曲线。

        Langevin 函数：M(H) = Ms * L(mu*H/(kT))，其中 L(x) = coth(x) - 1/x

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组

        Returns:
            元组：(拟合结果对象, 拟合参数字典)
        """

        def langevin(x, Ms, alpha):
            """Langevin 函数，数值稳定实现。

            L(x) = coth(x) - 1/x
            - 当 x -> 0 时，L(x) -> x/3（泰勒展开）
            - 当 x -> ∞ 时，L(x) -> 1 - 1/x（渐近展开）
            """
            # 使用 alpha * x 作为实际参数
            ax = alpha * x

            result = np.zeros_like(ax, dtype=float)

            # 小参数区域：使用泰勒展开 L(x) ≈ x/3 - x³/45 + 2x⁵/945
            small_mask = np.abs(ax) < 0.1
            result[small_mask] = (
                ax[small_mask] / 3.0
                - (ax[small_mask] ** 3) / 45.0
                + 2 * (ax[small_mask] ** 5) / 945.0
            )

            # 大参数区域：使用渐近展开 L(x) ≈ 1 - 1/x
            # 当 |x| > 20 时，coth(x) ≈ 1（误差 < 1e-9）
            large_mask = np.abs(ax) > 20
            result[large_mask] = 1.0 - 1.0 / ax[large_mask]

            # 中等参数区域：使用标准公式
            medium_mask = ~small_mask & ~large_mask
            if np.any(medium_mask):
                with np.errstate(divide="ignore", invalid="ignore"):
                    coth_ax = np.cosh(ax[medium_mask]) / np.sinh(ax[medium_mask])
                    result[medium_mask] = coth_ax - 1.0 / ax[medium_mask]

            return Ms * result

        model = lmfit.Model(langevin)
        params = model.make_params(Ms=np.max(np.abs(y_moment)), alpha=1.0)

        result = model.fit(y_moment, params, x=x_field)

        fit_params = {
            "Ms": result.params["Ms"].value,
            "alpha": result.params["alpha"].value,
            "chi2": result.chisqr,
            "redchi": result.redchi,
        }

        return result, fit_params

    def fit_model(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        model_type: FitModelType,
        initial_params: dict[str, float] | None = None,
        polynomial_order: int = 2,
    ) -> dict[str, Any]:
        """统一模型拟合接口。

        支持多种拟合模型，使用最小二乘法拟合，返回拟合参数和 R² 值。

        Args:
            x_data: X轴数据数组
            y_data: Y轴数据数组
            model_type: 拟合模型类型
            initial_params: 初始参数字典（可选）
            polynomial_order: 多项式阶数（仅当 model_type=POLYNOMIAL 时有效）

        Returns:
            包含以下键的字典：
                - model_type: 模型类型
                - parameters: 拟合参数字典
                - r_squared: R² 值
                - chi_squared: 卡方值
                - y_fit: 拟合曲线数据
                - residuals: 残差数组

        Raises:
            ValueError: 当模型类型不支持时抛出异常
        """
        if model_type == FitModelType.LINEAR:
            return self._fit_linear(x_data, y_data)
        elif model_type == FitModelType.POLYNOMIAL:
            return self._fit_polynomial(x_data, y_data, polynomial_order)
        elif model_type == FitModelType.EXPONENTIAL:
            return self._fit_exponential(x_data, y_data, initial_params)
        elif model_type == FitModelType.GAUSSIAN:
            return self._fit_gaussian(x_data, y_data, initial_params)
        elif model_type == FitModelType.LANGEVIN:
            return self._fit_langevin_wrapper(x_data, y_data)
        elif model_type == FitModelType.BRAUNBECK:
            return self._fit_braunbeck(x_data, y_data, initial_params)
        else:
            raise ValueError(f"不支持的模型类型: {model_type}")

    def _fit_linear(self, x_data: np.ndarray, y_data: np.ndarray) -> dict[str, Any]:
        """线性拟合。

        模型: y = a * x + b

        Args:
            x_data: X轴数据数组
            y_data: Y轴数据数组

        Returns:
            拟合结果字典
        """
        # 使用 numpy 进行线性拟合
        coefficients = np.polyfit(x_data, y_data, 1)
        a, b = coefficients[0], coefficients[1]

        # 计算拟合曲线
        y_fit = a * x_data + b

        # 计算 R²
        r_squared = self._calculate_r_squared(y_data, y_fit)

        # 计算卡方
        residuals = y_data - y_fit
        chi_squared = np.sum(residuals**2)

        return {
            "model_type": FitModelType.LINEAR.value,
            "parameters": {"slope": float(a), "intercept": float(b)},
            "r_squared": float(r_squared),
            "chi_squared": float(chi_squared),
            "y_fit": y_fit,
            "residuals": residuals,
        }

    def _fit_polynomial(
        self, x_data: np.ndarray, y_data: np.ndarray, order: int = 2
    ) -> dict[str, Any]:
        """多项式拟合。

        模型: y = a_n * x^n + a_{n-1} * x^{n-1} + ... + a_1 * x + a_0

        Args:
            x_data: X轴数据数组
            y_data: Y轴数据数组
            order: 多项式阶数

        Returns:
            拟合结果字典
        """
        # 确保阶数合理
        order = max(1, min(order, len(x_data) - 1))

        # 多项式拟合
        coefficients = np.polyfit(x_data, y_data, order)

        # 计算拟合曲线
        y_fit = np.polyval(coefficients, x_data)

        # 计算 R²
        r_squared = self._calculate_r_squared(y_data, y_fit)

        # 计算卡方
        residuals = y_data - y_fit
        chi_squared = np.sum(residuals**2)

        # 构建参数字典
        params = {f"a_{i}": float(coefficients[order - i]) for i in range(order + 1)}

        return {
            "model_type": FitModelType.POLYNOMIAL.value,
            "parameters": params,
            "polynomial_order": order,
            "r_squared": float(r_squared),
            "chi_squared": float(chi_squared),
            "y_fit": y_fit,
            "residuals": residuals,
        }

    def _fit_exponential(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        initial_params: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """指数拟合。

        模型: y = A * exp(B * x) + C

        Args:
            x_data: X轴数据数组
            y_data: Y轴数据数组
            initial_params: 初始参数字典，包含 A, B, C

        Returns:
            拟合结果字典
        """
        # 默认初始参数
        if initial_params is None:
            # 估计初始参数
            A_init = np.max(y_data) - np.min(y_data)
            B_init = 0.01
            C_init = np.min(y_data)
            initial_params = {"A": A_init, "B": B_init, "C": C_init}

        def exponential_func(x, A, B, C):
            return A * np.exp(B * x) + C

        try:
            # 使用 curve_fit 进行拟合
            popt, _ = optimize.curve_fit(
                exponential_func,
                x_data,
                y_data,
                p0=[initial_params["A"], initial_params["B"], initial_params["C"]],
                maxfev=5000,
            )
            A, B, C = popt
        except (RuntimeError, optimize.OptimizeWarning):
            # 拟合失败时使用初始参数
            warnings.warn("指数拟合失败，使用初始参数")
            A = initial_params["A"]
            B = initial_params["B"]
            C = initial_params["C"]

        # 计算拟合曲线
        y_fit = exponential_func(x_data, A, B, C)

        # 计算 R²
        r_squared = self._calculate_r_squared(y_data, y_fit)

        # 计算卡方
        residuals = y_data - y_fit
        chi_squared = np.sum(residuals**2)

        return {
            "model_type": FitModelType.EXPONENTIAL.value,
            "parameters": {"A": float(A), "B": float(B), "C": float(C)},
            "r_squared": float(r_squared),
            "chi_squared": float(chi_squared),
            "y_fit": y_fit,
            "residuals": residuals,
        }

    def _fit_gaussian(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        initial_params: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """高斯拟合。

        模型: y = A * exp(-((x - mu)^2) / (2 * sigma^2)) + C

        Args:
            x_data: X轴数据数组
            y_data: Y轴数据数组
            initial_params: 初始参数字典，包含 A, mu, sigma, C

        Returns:
            拟合结果字典
        """
        # 默认初始参数
        if initial_params is None:
            # 估计初始参数
            A_init = np.max(y_data) - np.min(y_data)
            mu_init = x_data[np.argmax(y_data)]
            sigma_init = (np.max(x_data) - np.min(x_data)) / 4
            C_init = np.min(y_data)
            initial_params = {
                "A": A_init,
                "mu": mu_init,
                "sigma": sigma_init,
                "C": C_init,
            }

        def gaussian_func(x, A, mu, sigma, C):
            return A * np.exp(-((x - mu) ** 2) / (2 * sigma**2)) + C

        try:
            # 使用 curve_fit 进行拟合
            popt, _ = optimize.curve_fit(
                gaussian_func,
                x_data,
                y_data,
                p0=[
                    initial_params["A"],
                    initial_params["mu"],
                    initial_params["sigma"],
                    initial_params["C"],
                ],
                maxfev=5000,
            )
            A, mu, sigma, C = popt
        except (RuntimeError, optimize.OptimizeWarning):
            # 拟合失败时使用初始参数
            warnings.warn("高斯拟合失败，使用初始参数")
            A = initial_params["A"]
            mu = initial_params["mu"]
            sigma = initial_params["sigma"]
            C = initial_params["C"]

        # 计算拟合曲线
        y_fit = gaussian_func(x_data, A, mu, sigma, C)

        # 计算 R²
        r_squared = self._calculate_r_squared(y_data, y_fit)

        # 计算卡方
        residuals = y_data - y_fit
        chi_squared = np.sum(residuals**2)

        return {
            "model_type": FitModelType.GAUSSIAN.value,
            "parameters": {
                "A": float(A),
                "mu": float(mu),
                "sigma": float(abs(sigma)),
                "C": float(C),
            },
            "r_squared": float(r_squared),
            "chi_squared": float(chi_squared),
            "y_fit": y_fit,
            "residuals": residuals,
        }

    def _fit_langevin_wrapper(self, x_data: np.ndarray, y_data: np.ndarray) -> dict[str, Any]:
        """Langevin 函数拟合包装器。

        Args:
            x_data: X轴数据数组
            y_data: Y轴数据数组

        Returns:
            拟合结果字典
        """
        result, fit_params = self.fit_langevin(x_data, y_data)

        # 计算拟合曲线
        y_fit = result.best_fit

        # 计算 R²
        r_squared = self._calculate_r_squared(y_data, y_fit)

        return {
            "model_type": FitModelType.LANGEVIN.value,
            "parameters": fit_params,
            "r_squared": float(r_squared),
            "chi_squared": float(result.chisqr),
            "y_fit": y_fit,
            "residuals": result.residual,
        }

    def _fit_braunbeck(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        initial_params: dict[str, float] | None = None,
    ) -> dict[str, Any]:
        """Braunbeck 磁滞模型拟合。

        使用 Braunbeck 函数拟合磁滞回线数据。

        模型: B(H) = Bs * tanh((H - Hc) / S) + Bs * tanh((H + Hc) / S)

        Args:
            x_data: 磁场强度数组
            y_data: 磁感应强度数组
            initial_params: 初始参数字典，包含 Bs, Hc, S

        Returns:
            拟合结果字典，包含：
                - model_type: 模型类型
                - parameters: 拟合参数字典 (Bs, Hc, S)
                - r_squared: R² 值
                - chi_squared: 卡方值
                - y_fit: 拟合曲线数据
                - residuals: 残差数组
        """
        # 默认初始参数
        if initial_params is None:
            # 从数据估计初始参数
            Bs_init = np.max(np.abs(y_data)) * 0.8
            Hc_init = np.max(np.abs(x_data)) * 0.1
            S_init = np.max(np.abs(x_data)) * 0.05
            initial_params = {"Bs": Bs_init, "Hc": Hc_init, "S": S_init}

        try:
            # 使用 curve_fit 进行拟合
            # 参数边界：Bs > 0, Hc >= 0, S > 0
            popt, _ = optimize.curve_fit(
                braunbeck_function,
                x_data,
                y_data,
                p0=[initial_params["Bs"], initial_params["Hc"], initial_params["S"]],
                bounds=([0.0, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
                maxfev=5000,
            )
            Bs, Hc, S = popt
        except (RuntimeError, optimize.OptimizeWarning) as e:
            # 拟合失败时使用初始参数
            warnings.warn(f"Braunbeck 拟合失败，使用初始参数: {e}")
            Bs = initial_params["Bs"]
            Hc = initial_params["Hc"]
            S = initial_params["S"]

        # 计算拟合曲线
        y_fit = braunbeck_function(x_data, Bs, Hc, S)

        # 计算 R²
        r_squared = self._calculate_r_squared(y_data, y_fit)

        # 计算卡方
        residuals = y_data - y_fit
        chi_squared = np.sum(residuals**2)

        return {
            "model_type": FitModelType.BRAUNBECK.value,
            "parameters": {
                "Bs": float(Bs),
                "Hc": float(abs(Hc)),
                "S": float(abs(S)),
            },
            "r_squared": float(r_squared),
            "chi_squared": float(chi_squared),
            "y_fit": y_fit,
            "residuals": residuals,
        }

    def _calculate_r_squared(self, y_data: np.ndarray, y_fit: np.ndarray) -> float:
        """计算 R² 值（决定系数）。

        R² = 1 - SS_res / SS_tot

        Args:
            y_data: 原始数据
            y_fit: 拟合数据

        Returns:
            R² 值
        """
        ss_res = np.sum((y_data - y_fit) ** 2)
        ss_tot = np.sum((y_data - np.mean(y_data)) ** 2)

        if ss_tot == 0:
            return 1.0 if ss_res == 0 else 0.0

        return 1 - (ss_res / ss_tot)

    # ==================== 数据导出功能 ====================

    def export_data(
        self,
        filepath: str | Path,
        x_data: np.ndarray,
        y_data: np.ndarray,
        format: ExportFormat = ExportFormat.CSV,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> bool:
        """数据导出统一接口。

        支持多种格式导出：CSV、HDF5、JSON。

        Args:
            filepath: 导出文件路径
            x_data: X轴数据数组
            y_data: Y轴数据数组
            format: 导出格式
            metadata: 元数据字典
            **kwargs: 格式特定参数
                - CSV: delimiter（分隔符，默认逗号）
                - HDF5: group_path（数据组路径，默认 '/data'）
                - JSON: indent（缩进，默认 2）

        Returns:
            导出是否成功

        Raises:
            ValueError: 当格式不支持时抛出异常
        """
        filepath = Path(filepath)

        if format == ExportFormat.CSV:
            return self._export_csv(filepath, x_data, y_data, metadata, **kwargs)
        elif format == ExportFormat.HDF5:
            return self._export_hdf5(filepath, x_data, y_data, metadata, **kwargs)
        elif format == ExportFormat.JSON:
            return self._export_json(filepath, x_data, y_data, metadata, **kwargs)
        else:
            raise ValueError(f"不支持的导出格式: {format}")

    def _export_csv(
        self,
        filepath: Path,
        x_data: np.ndarray,
        y_data: np.ndarray,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> bool:
        """导出为 CSV 格式。

        Args:
            filepath: 文件路径
            x_data: X轴数据
            y_data: Y轴数据
            metadata: 元数据
            **kwargs: delimiter（分隔符）, precision（数值精度，默认15）

        Returns:
            导出是否成功
        """
        delimiter = kwargs.get("delimiter", ",")
        precision = kwargs.get("precision", 15)

        try:
            with open(filepath, "w", encoding="utf-8") as f:
                # 写入元数据作为注释
                if metadata:
                    f.write(f"# 导出时间: {datetime.now().isoformat()}\n")
                    for key, value in metadata.items():
                        # 将数组转换为字符串表示
                        if isinstance(value, np.ndarray):
                            value_str = np.array2string(value, threshold=10)
                        else:
                            value_str = str(value)
                        f.write(f"# {key}: {value_str}\n")
                    f.write("#\n")

                # 写入表头
                f.write(f"x{delimiter}y\n")

                # 写入数据（使用高精度格式化）
                fmt_str = f"{{:.{precision}g}}"
                for x, y in zip(x_data, y_data):
                    f.write(f"{fmt_str.format(x)}{delimiter}{fmt_str.format(y)}\n")

            return True
        except Exception as e:
            warnings.warn(f"CSV 导出失败: {e}")
            return False

    def _export_hdf5(
        self,
        filepath: Path,
        x_data: np.ndarray,
        y_data: np.ndarray,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> bool:
        """导出为 HDF5 格式。

        HDF5 格式支持大数据存储和高效读写。

        Args:
            filepath: 文件路径
            x_data: X轴数据
            y_data: Y轴数据
            metadata: 元数据
            **kwargs: group_path（数据组路径）

        Returns:
            导出是否成功
        """
        group_path = kwargs.get("group_path", "/data")

        try:
            with h5py.File(filepath, "w") as f:
                # 创建数据组
                grp = f.create_group(group_path.lstrip("/"))

                # 存储数据
                grp.create_dataset("x", data=x_data, compression="gzip")
                grp.create_dataset("y", data=y_data, compression="gzip")

                # 存储元数据
                if metadata:
                    meta_grp = f.create_group("metadata")
                    for key, value in metadata.items():
                        # 处理不同类型的数据
                        if isinstance(value, np.ndarray):
                            meta_grp.create_dataset(key, data=value, compression="gzip")
                        elif isinstance(value, (str, int, float, bool)):
                            meta_grp.attrs[key] = value
                        elif isinstance(value, dict):
                            # 字典转换为 JSON 字符串
                            meta_grp.attrs[key] = json.dumps(value)
                        else:
                            meta_grp.attrs[key] = str(value)

                # 添加导出时间戳
                grp.attrs["export_time"] = datetime.now().isoformat()

            return True
        except Exception as e:
            warnings.warn(f"HDF5 导出失败: {e}")
            return False

    def _export_json(
        self,
        filepath: Path,
        x_data: np.ndarray,
        y_data: np.ndarray,
        metadata: dict[str, Any] | None = None,
        **kwargs,
    ) -> bool:
        """导出为 JSON 格式。

        JSON 格式包含完整元数据，便于人类阅读和跨平台使用。

        Args:
            filepath: 文件路径
            x_data: X轴数据
            y_data: Y轴数据
            metadata: 元数据
            **kwargs: indent（缩进）

        Returns:
            导出是否成功
        """
        indent = kwargs.get("indent", 2)

        try:
            # 构建导出数据结构
            export_data = {
                "metadata": {
                    "export_time": datetime.now().isoformat(),
                    "data_points": len(x_data),
                    "x_range": [float(np.min(x_data)), float(np.max(x_data))],
                    "y_range": [float(np.min(y_data)), float(np.max(y_data))],
                },
                "data": {
                    "x": x_data.tolist(),
                    "y": y_data.tolist(),
                },
            }

            # 合并用户元数据
            if metadata:
                export_data["metadata"].update(self._serialize_metadata(metadata))

            # 写入文件
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=indent, ensure_ascii=False)

            return True
        except Exception as e:
            warnings.warn(f"JSON 导出失败: {e}")
            return False

    def _serialize_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """序列化元数据，处理 NumPy 数组和特殊类型。

        Args:
            metadata: 原始元数据字典

        Returns:
            序列化后的元数据字典
        """
        serialized = {}
        for key, value in metadata.items():
            if isinstance(value, np.ndarray):
                serialized[key] = value.tolist()
            elif isinstance(value, (np.integer, np.floating)):
                serialized[key] = float(value)
            elif isinstance(value, np.bool_):
                serialized[key] = bool(value)
            elif isinstance(value, dict):
                serialized[key] = self._serialize_metadata(value)
            else:
                serialized[key] = value
        return serialized

    def export_analysis_results(
        self,
        filepath: str | Path,
        analysis_results: dict[str, Any],
        format: ExportFormat = ExportFormat.JSON,
        **kwargs,
    ) -> bool:
        """导出分析结果。

        专门用于导出磁滞回线分析结果等复杂数据结构。

        Args:
            filepath: 导出文件路径
            analysis_results: 分析结果字典
            format: 导出格式
            **kwargs: 格式特定参数

        Returns:
            导出是否成功
        """
        filepath = Path(filepath)

        # 提取主要数据
        x_data = analysis_results.get("x_corrected", np.array([]))
        y_data = analysis_results.get("y_corrected", np.array([]))

        # 构建元数据（排除数组数据）
        metadata = {
            k: v for k, v in analysis_results.items() if k not in ["x_corrected", "y_corrected"]
        }

        return self.export_data(filepath, x_data, y_data, format, metadata, **kwargs)

    def fit_custom_model(
        self,
        x_field: np.ndarray,
        y_moment: np.ndarray,
        model_func: Callable,
        initial_params: dict[str, float],
    ) -> tuple[lmfit.model.ModelResult, dict[str, float]]:
        """使用自定义模型拟合数据。

        Args:
            x_field: 磁场强度数组
            y_moment: 磁矩数组
            model_func: 自定义拟合函数
            initial_params: 初始参数字典

        Returns:
            元组：(拟合结果对象, 拟合参数字典)
        """
        model = lmfit.Model(model_func)
        params = model.make_params(**initial_params)

        result = model.fit(y_moment, params, x=x_field)

        fit_params = {}
        for name in result.params:
            fit_params[name] = result.params[name].value
        fit_params["chi2"] = result.chisqr
        fit_params["redchi"] = result.redchi

        return result, fit_params


# ==================== Braunbeck 磁滞模型 ====================


def braunbeck_function(H: np.ndarray, Bs: float, Hc: float, S: float) -> np.ndarray:
    """Braunbeck磁滞模型函数。

    Braunbeck模型用于描述磁滞回线，基于双曲正切函数。
    B(H) = Bs * tanh((H - Hc) / S) + Bs * tanh((H + Hc) / S)

    该模型能够较好地描述铁磁材料的磁滞特性，包括：
    - 饱和磁化行为
    - 矫顽力效应
    - 磁滞回线的对称性

    Args:
        H: 磁场强度数组 (A/m 或 Oe)
        Bs: 饱和磁感应强度 (T 或 G)
        Hc: 矫顽力 (A/m 或 Oe)
        S: 磁滞宽度参数，控制回线宽度 (A/m 或 Oe)

    Returns:
        磁感应强度数组 (T 或 G)

    Raises:
        ValueError: 当 S 参数为零或负数时抛出异常

    Example:
        >>> H = np.linspace(-1000, 1000, 500)
        >>> B = braunbeck_function(H, Bs=1.5, Hc=100, S=50)
        >>> # 绘制磁滞回线
        >>> import matplotlib.pyplot as plt
        >>> plt.plot(H, B)
    """
    # 参数验证：确保数值稳定性
    if S <= 0:
        raise ValueError(f"磁滞宽度参数 S 必须大于零，当前值: {S}")

    # 避免除零和数值溢出
    S = max(S, 1e-10)

    # 计算归一化参数
    x1 = (H - Hc) / S
    x2 = (H + Hc) / S

    # 使用数值稳定的 tanh 实现
    # 当 |x| > 20 时，tanh(x) ≈ sign(x)
    result = np.zeros_like(H, dtype=float)

    # 中等参数区域：使用标准 tanh
    medium_mask = (np.abs(x1) <= 20) & (np.abs(x2) <= 20)
    if np.any(medium_mask):
        result[medium_mask] = Bs * (np.tanh(x1[medium_mask]) + np.tanh(x2[medium_mask]))

    # 大参数区域：使用渐近近似
    large_mask = (np.abs(x1) > 20) | (np.abs(x2) > 20)
    if np.any(large_mask):
        # tanh(x) ≈ sign(x) for |x| >> 1
        tanh_x1 = np.sign(x1[large_mask])
        tanh_x2 = np.sign(x2[large_mask])
        result[large_mask] = Bs * (tanh_x1 + tanh_x2)

    return result


# ==================== 拟合优度评估 ====================


def calculate_goodness_of_fit(
    y_observed: np.ndarray,
    y_predicted: np.ndarray,
    n_params: int,
) -> dict[str, float]:
    """计算拟合优度指标。

    计算多个统计指标用于评估拟合质量，包括：
    - R²: 决定系数，衡量模型解释数据变异的比例
    - RMSE: 均方根误差，衡量预测值与观测值的偏差
    - MAE: 平均绝对误差，对异常值不敏感
    - AIC: Akaike信息准则，平衡拟合优度与模型复杂度
    - BIC: 贝叶斯信息准则，对模型复杂度惩罚更严格

    Args:
        y_observed: 观测值数组
        y_predicted: 预测值数组
        n_params: 模型参数数量

    Returns:
        包含拟合优度指标的字典：
            - r_squared: R²决定系数 (范围 0-1，越接近1越好)
            - rmse: 均方根误差 (越小越好)
            - mae: 平均绝对误差 (越小越好)
            - aic: Akaike信息准则 (越小越好)
            - bic: 贝叶斯信息准则 (越小越好)

    Raises:
        ValueError: 当输入数组长度不匹配或为空时抛出异常

    Example:
        >>> y_obs = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        >>> y_pred = np.array([1.1, 2.1, 2.9, 4.2, 4.8])
        >>> metrics = calculate_goodness_of_fit(y_obs, y_pred, n_params=2)
        >>> print(f"R² = {metrics['r_squared']:.4f}")
    """
    # 输入验证
    if y_observed is None or y_predicted is None:
        raise ValueError("观测值和预测值数组不能为空")

    y_observed = np.asarray(y_observed, dtype=float)
    y_predicted = np.asarray(y_predicted, dtype=float)

    if len(y_observed) != len(y_predicted):
        raise ValueError(f"观测值和预测值数组长度不匹配: {len(y_observed)} vs {len(y_predicted)}")

    n = len(y_observed)
    if n == 0:
        raise ValueError("输入数组不能为空")

    if n_params < 1:
        raise ValueError(f"参数数量必须大于等于1，当前值: {n_params}")

    # 计算残差
    residuals = y_observed - y_predicted

    # R² 决定系数
    ss_res = np.sum(residuals**2)
    ss_tot = np.sum((y_observed - np.mean(y_observed)) ** 2)

    if ss_tot == 0:
        r_squared = 1.0 if ss_res == 0 else 0.0
    else:
        r_squared = 1.0 - (ss_res / ss_tot)

    # 确保 R² 在合理范围内（某些情况下可能为负）
    r_squared = max(-1.0, min(1.0, r_squared))

    # RMSE 均方根误差
    rmse = np.sqrt(np.mean(residuals**2))

    # MAE 平均绝对误差
    mae = np.mean(np.abs(residuals))

    # AIC (Akaike Information Criterion)
    # AIC = n * ln(RSS/n) + 2k，其中 k 为参数数量
    # 对于高斯噪声假设
    if ss_res > 0:
        aic = n * np.log(ss_res / n) + 2 * n_params
    else:
        # 完美拟合情况
        aic = -np.inf

    # BIC (Bayesian Information Criterion)
    # BIC = n * ln(RSS/n) + k * ln(n)
    if ss_res > 0:
        bic = n * np.log(ss_res / n) + n_params * np.log(n)
    else:
        bic = -np.inf

    return {
        "r_squared": float(r_squared),
        "rmse": float(rmse),
        "mae": float(mae),
        "aic": float(aic),
        "bic": float(bic),
    }


# ==================== 多模型拟合器 ====================


class MultiModelFitter:
    """多模型拟合器。

    支持同时使用多个模型拟合数据，并比较拟合结果以选择最佳模型。
    适用于需要确定最佳物理模型的场景。

    Attributes:
        models: 注册的模型字典
        results: 拟合结果列表

    Example:
        >>> fitter = MultiModelFitter()
        >>> fitter.register_model("linear", linear_func, [1.0, 0.0])
        >>> fitter.register_model("polynomial", poly_func, [1.0, 0.0, 0.0])
        >>> results = fitter.fit_all(x_data, y_data)
        >>> best = fitter.get_best_model(criterion="aic")
    """

    def __init__(self):
        """初始化多模型拟合器。"""
        self.models: dict[str, dict[str, Any]] = {}
        self.results: list[FitResult] = []

    def register_model(
        self,
        name: str,
        func: Callable,
        initial_params: list[float],
        bounds: tuple[list[float], list[float]] | None = None,
        param_names: list[str] | None = None,
    ) -> None:
        """注册拟合模型。

        Args:
            name: 模型名称（唯一标识符）
            func: 拟合函数，签名为 f(x, *params) -> y
            initial_params: 初始参数值列表
            bounds: 参数边界元组 (lower_bounds, upper_bounds)
            param_names: 参数名称列表（可选，用于结果展示）

        Raises:
            ValueError: 当模型名称已存在或参数无效时抛出异常

        Example:
            >>> fitter = MultiModelFitter()
            >>> fitter.register_model(
            ...     "braunbeck",
            ...     braunbeck_function,
            ...     initial_params=[1.5, 100.0, 50.0],
            ...     bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
            ...     param_names=["Bs", "Hc", "S"]
            ... )
        """
        if name in self.models:
            raise ValueError(f"模型名称 '{name}' 已存在，请使用不同的名称")

        if not callable(func):
            raise ValueError("拟合函数必须是可调用对象")

        if not initial_params or len(initial_params) == 0:
            raise ValueError("初始参数列表不能为空")

        # 生成默认参数名称
        if param_names is None:
            param_names = [f"param_{i}" for i in range(len(initial_params))]

        if len(param_names) != len(initial_params):
            raise ValueError("参数名称列表长度必须与初始参数列表长度一致")

        self.models[name] = {
            "func": func,
            "initial_params": initial_params,
            "bounds": bounds,
            "param_names": param_names,
        }

    def fit_all(
        self,
        x_data: np.ndarray,
        y_data: np.ndarray,
        maxfev: int = 5000,
    ) -> list[FitResult]:
        """并行执行所有模型拟合。

        对所有注册的模型执行拟合，并计算拟合优度指标。

        Args:
            x_data: X轴数据数组
            y_data: Y轴数据数组
            maxfev: 最大函数评估次数（默认5000）

        Returns:
            拟合结果列表，按 AIC 值升序排列

        Raises:
            ValueError: 当没有注册模型或数据无效时抛出异常

        Example:
            >>> results = fitter.fit_all(H_field, B_moment)
            >>> for result in results:
            ...     print(f"{result.model_name}: R²={result.r_squared:.4f}")
        """
        if not self.models:
            raise ValueError("未注册任何模型，请先调用 register_model()")

        # 数据验证
        x_data = np.asarray(x_data, dtype=float)
        y_data = np.asarray(y_data, dtype=float)

        if len(x_data) != len(y_data):
            raise ValueError("X和Y数据数组长度不匹配")

        if len(x_data) < 3:
            raise ValueError("数据点数量不足，至少需要3个点")

        # 清空之前的结果
        self.results = []

        # 对每个模型进行拟合
        for model_name, model_info in self.models.items():
            try:
                result = self._fit_single_model(
                    model_name,
                    model_info,
                    x_data,
                    y_data,
                    maxfev,
                )
                self.results.append(result)
            except Exception as e:
                # 拟合失败时记录警告，继续下一个模型
                warnings.warn(f"模型 '{model_name}' 拟合失败: {e}")
                continue

        # 按 AIC 值排序（越小越好）
        self.results.sort(key=lambda r: r.aic)

        return self.results

    def _fit_single_model(
        self,
        model_name: str,
        model_info: dict[str, Any],
        x_data: np.ndarray,
        y_data: np.ndarray,
        maxfev: int,
    ) -> FitResult:
        """拟合单个模型。

        Args:
            model_name: 模型名称
            model_info: 模型信息字典
            x_data: X轴数据
            y_data: Y轴数据
            maxfev: 最大函数评估次数

        Returns:
            拟合结果对象
        """
        func = model_info["func"]
        initial_params = model_info["initial_params"]
        bounds = model_info["bounds"]
        param_names = model_info["param_names"]

        # 执行拟合
        if bounds is not None:
            popt, _ = optimize.curve_fit(
                func,
                x_data,
                y_data,
                p0=initial_params,
                bounds=bounds,
                maxfev=maxfev,
            )
        else:
            popt, _ = optimize.curve_fit(
                func,
                x_data,
                y_data,
                p0=initial_params,
                maxfev=maxfev,
            )

        # 计算预测值
        y_predicted = func(x_data, *popt)

        # 计算拟合优度
        n_params = len(popt)
        metrics = calculate_goodness_of_fit(y_data, y_predicted, n_params)

        # 构建参数字典
        params = {name: float(value) for name, value in zip(param_names, popt)}

        # 创建拟合结果对象
        return FitResult(
            model_name=model_name,
            params=params,
            r_squared=metrics["r_squared"],
            rmse=metrics["rmse"],
            mae=metrics["mae"],
            aic=metrics["aic"],
            bic=metrics["bic"],
            residuals=y_data - y_predicted,
            y_predicted=y_predicted,
            n_params=n_params,
            n_data_points=len(y_data),
        )

    def compare_models(self) -> dict[str, Any]:
        """比较所有模型拟合结果。

        生成模型比较报告，包括排名、相对性能和推荐。

        Returns:
            包含比较结果的字典：
                - rankings: 模型排名列表（按AIC）
                - best_model: 最佳模型名称
                - delta_aic: AIC差值（相对于最佳模型）
                - aic_weights: AIC权重（模型选择概率）
                - summary: 比较摘要文本

        Raises:
            ValueError: 当没有拟合结果时抛出异常

        Example:
            >>> comparison = fitter.compare_models()
            >>> print(f"最佳模型: {comparison['best_model']}")
        """
        if not self.results:
            raise ValueError("没有拟合结果，请先调用 fit_all()")

        # 计算AIC差值和权重
        min_aic = min(r.aic for r in self.results)

        # AIC差值
        delta_aic = {r.model_name: r.aic - min_aic for r in self.results}

        # AIC权重（Akaike weights）
        # w_i = exp(-delta_i/2) / sum(exp(-delta_j/2))
        exp_delta = {name: np.exp(-delta / 2) for name, delta in delta_aic.items()}
        sum_exp = sum(exp_delta.values())
        aic_weights = {name: value / sum_exp for name, value in exp_delta.items()}

        # 生成排名
        rankings = [
            {
                "rank": i + 1,
                "model": r.model_name,
                "r_squared": r.r_squared,
                "rmse": r.rmse,
                "aic": r.aic,
                "delta_aic": delta_aic[r.model_name],
                "weight": aic_weights[r.model_name],
            }
            for i, r in enumerate(self.results)
        ]

        # 生成摘要文本
        summary_lines = ["模型比较结果（按AIC排序）："]
        for r in rankings:
            summary_lines.append(
                f"  {r['rank']}. {r['model']}: "
                f"R²={r['r_squared']:.4f}, "
                f"RMSE={r['rmse']:.4f}, "
                f"ΔAIC={r['delta_aic']:.2f}, "
                f"权重={r['weight']:.3f}"
            )

        return {
            "rankings": rankings,
            "best_model": self.results[0].model_name,
            "delta_aic": delta_aic,
            "aic_weights": aic_weights,
            "summary": "\n".join(summary_lines),
        }

    def get_best_model(self, criterion: str = "aic") -> FitResult:
        """根据指定准则获取最佳模型。

        Args:
            criterion: 选择准则，可选 "aic"、"bic"、"r_squared"、"rmse"
                - aic: Akaike信息准则（越小越好）
                - bic: 贝叶斯信息准则（越小越好）
                - r_squared: R²决定系数（越大越好）
                - rmse: 均方根误差（越小越好）

        Returns:
            最佳模型的拟合结果

        Raises:
            ValueError: 当没有拟合结果或准则无效时抛出异常

        Example:
            >>> best = fitter.get_best_model(criterion="bic")
            >>> print(f"最佳模型: {best.model_name}")
        """
        if not self.results:
            raise ValueError("没有拟合结果，请先调用 fit_all()")

        valid_criteria = ["aic", "bic", "r_squared", "rmse"]
        if criterion not in valid_criteria:
            raise ValueError(f"无效的选择准则: {criterion}。可选: {', '.join(valid_criteria)}")

        if criterion in ["aic", "bic", "rmse"]:
            # 越小越好
            return min(self.results, key=lambda r: getattr(r, criterion))
        else:
            # r_squared: 越大越好
            return max(self.results, key=lambda r: getattr(r, criterion))


# ==================== 分析报告生成 ====================


def generate_analysis_report(
    h_data: np.ndarray,
    b_data: np.ndarray,
    fit_results: list[FitResult],
    experiment_id: str | None = None,
    analyzer: PhysicsAnalyzer | None = None,
) -> AnalysisReport:
    """生成完整的分析报告。

    整合磁滞回线分析和多模型拟合结果，生成结构化的分析报告。

    Args:
        h_data: 磁场强度数据数组
        b_data: 磁感应强度数据数组
        fit_results: 拟合结果列表
        experiment_id: 实验ID（可选，默认使用时间戳）
        analyzer: PhysicsAnalyzer实例（可选，用于磁滞回线分析）

    Returns:
        完整的分析报告对象

    Raises:
        ValueError: 当输入数据无效时抛出异常

    Example:
        >>> report = generate_analysis_report(H, B, fit_results, "exp_001")
        >>> print(f"最佳模型: {report.best_model}")
        >>> print(f"矫顽力: {report.hysteresis_params['Hc']:.2f} A/m")
    """
    # 数据验证
    h_data = np.asarray(h_data, dtype=float)
    b_data = np.asarray(b_data, dtype=float)

    if len(h_data) != len(b_data):
        raise ValueError("磁场和磁感应强度数据数组长度不匹配")

    if len(h_data) < 5:
        raise ValueError("数据点数量不足，至少需要5个点")

    # 生成实验ID
    if experiment_id is None:
        experiment_id = f"exp_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    # 生成时间戳
    timestamp = datetime.now().isoformat()

    # 磁滞回线分析
    hysteresis_params: dict[str, Any] = {}
    if analyzer is not None:
        try:
            hysteresis_params = analyzer.analyze_hysteresis_loop(h_data, b_data)
        except Exception as e:
            warnings.warn(f"磁滞回线分析失败: {e}")
            hysteresis_params = {}
    else:
        # 创建临时分析器
        temp_analyzer = PhysicsAnalyzer()
        try:
            hysteresis_params = temp_analyzer.analyze_hysteresis_loop(h_data, b_data)
        except Exception as e:
            warnings.warn(f"磁滞回线分析失败: {e}")
            hysteresis_params = {}

    # 确定最佳模型
    best_model = ""
    if fit_results:
        # 按AIC选择最佳模型
        best_result = min(fit_results, key=lambda r: r.aic)
        best_model = best_result.model_name

    # 计算质量指标
    quality_metrics = _calculate_quality_metrics(h_data, b_data, hysteresis_params)

    # 生成推荐建议
    recommendations = _generate_recommendations(
        hysteresis_params,
        fit_results,
        quality_metrics,
    )

    return AnalysisReport(
        experiment_id=experiment_id,
        timestamp=timestamp,
        hysteresis_params=hysteresis_params,
        fit_results=fit_results,
        best_model=best_model,
        quality_metrics=quality_metrics,
        recommendations=recommendations,
    )


def _calculate_quality_metrics(
    h_data: np.ndarray,
    b_data: np.ndarray,
    hysteresis_params: dict[str, Any],
) -> dict[str, float]:
    """计算数据质量指标。

    Args:
        h_data: 磁场数据
        b_data: 磁感应强度数据
        hysteresis_params: 磁滞参数

    Returns:
        质量指标字典
    """
    metrics = {}

    # 数据点数量
    metrics["n_data_points"] = float(len(h_data))

    # 磁场范围
    metrics["h_range"] = float(np.max(h_data) - np.min(h_data))

    # 磁感应强度范围
    metrics["b_range"] = float(np.max(b_data) - np.min(b_data))

    # 数据密度（点/单位磁场）
    if metrics["h_range"] > 0:
        metrics["data_density"] = float(len(h_data) / metrics["h_range"])
    else:
        metrics["data_density"] = 0.0

    # 矩形比（如果有）
    if "squareness" in hysteresis_params:
        metrics["squareness"] = float(hysteresis_params["squareness"])

    # 矫顽力（如果有）
    if "Hc" in hysteresis_params:
        metrics["coercivity"] = float(hysteresis_params["Hc"])

    # 信噪比估计（使用数据标准差）
    metrics["signal_to_noise"] = float(np.std(b_data) / (np.mean(np.abs(b_data)) + 1e-10))

    return metrics


def _generate_recommendations(
    hysteresis_params: dict[str, Any],
    fit_results: list[FitResult],
    quality_metrics: dict[str, float],
) -> list[str]:
    """生成分析建议。

    基于分析结果生成实用的建议。

    Args:
        hysteresis_params: 磁滞参数
        fit_results: 拟合结果
        quality_metrics: 质量指标

    Returns:
        建议列表
    """
    recommendations = []

    # 数据质量建议
    if quality_metrics.get("data_density", 0) < 10:
        recommendations.append("建议增加数据采集密度以获得更精确的分析结果")

    if quality_metrics.get("signal_to_noise", 0) < 5:
        recommendations.append("信噪比较低，建议检查实验设置或增加信号平均次数")

    # 拟合质量建议
    if fit_results:
        best_result = min(fit_results, key=lambda r: r.aic)

        if best_result.r_squared < 0.9:
            recommendations.append(
                f"最佳模型 {best_result.model_name} 的 R² 值较低 ({best_result.r_squared:.3f})，"
                "建议检查数据质量或尝试其他模型"
            )

        if best_result.rmse > 0.1 * quality_metrics.get("b_range", 1.0):
            recommendations.append(
                f"拟合误差较大 (RMSE={best_result.rmse:.4f})，" "可能存在异常数据点或模型选择不当"
            )

    # 磁滞特性建议
    if hysteresis_params:
        squareness = hysteresis_params.get("squareness", 0)
        if squareness < 0.3:
            recommendations.append(f"矩形比较低 ({squareness:.3f})，材料可能具有软磁特性")
        elif squareness > 0.8:
            recommendations.append(f"矩形比较高 ({squareness:.3f})，材料可能具有硬磁特性")

        hc = hysteresis_params.get("Hc", 0)
        if hc > 0:
            recommendations.append(f"矫顽力 Hc = {hc:.2f} A/m，可用于评估材料磁硬度")

    # 如果没有建议，添加默认建议
    if not recommendations:
        recommendations.append("数据分析完成，结果质量良好")

    return recommendations
