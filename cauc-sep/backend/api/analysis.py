"""
数据分析 API 路由模块

功能：
- 信号平滑
- 曲线拟合
- 磁滞回线分析
- 多模型拟合对比
- 分析报告生成与导出

安全加固：
- SubTask 13.1: 输入验证增强（数据数组长度限制）
"""

import json
import logging
from datetime import datetime
from io import BytesIO

import numpy as np
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from api.schemas import (
    AnalysisReportResponse,
    CompareRequest,
    CompareResponse,
    FitRequest,
    FitResponse,
    HistoryQueryRequest,
    HistoryQueryResponse,
    HysteresisRequest,
    HysteresisResponse,
    ModelFitResult,
    MultiFitRequest,
    MultiFitResponse,
    ReportGenerateRequest,
    SmoothRequest,
    SmoothResponse,
)
from core.analysis import (
    FitResult,
    MultiModelFitter,
    PhysicsAnalyzer,
    braunbeck_function,
    generate_analysis_report,
)
from middleware.security import validate_array_length

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/api/v1/analysis",
    tags=["analysis"],
    responses={404: {"description": "Not found"}},
)

analyzer = PhysicsAnalyzer()

# 数据数组最大长度限制（防止内存耗尽攻击）
MAX_DATA_POINTS = 100000


@router.post("/smooth", response_model=SmoothResponse)
async def smooth_signal(request: SmoothRequest):
    """
    信号平滑处理

    支持两种平滑方法：
    - Savitzky-Golay 滤波（局部多项式拟合平滑）
    - 巴特沃斯低通滤波（频域滤波平滑）

    Args:
        request: 平滑请求

    Returns:
        SmoothResponse: 平滑结果

    Raises:
        HTTPException: 数据验证失败时抛出400错误
    """
    try:
        # SubTask 13.1: 输入验证 - 数据数组长度限制
        if not validate_array_length(request.y_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.y_data)} 个",
            )

        y_data = np.array(request.y_data)

        # 验证数据点数量最小值
        MIN_DATA_POINTS = 3
        if len(y_data) < MIN_DATA_POINTS:
            raise HTTPException(
                status_code=400,
                detail=f"数据点数量不足，至少需要 {MIN_DATA_POINTS} 个数据点，当前 {len(y_data)} 个",
            )

        smoothed = analyzer.smooth_signal(
            y_data,
            method=request.method,
            window_length=request.window_length,
            polyorder=request.polyorder,
            butter_lowcut=request.butter_lowcut,
            butter_order=request.butter_order,
        )

        return SmoothResponse(
            success=True,
            message=f"Signal smoothed using {request.method}",
            smoothed_data=smoothed.tolist(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Smooth error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fit", response_model=FitResponse)
async def fit_curve(request: FitRequest):
    """
    曲线拟合

    支持的拟合模型：
    - langevin: Langevin 函数拟合磁化曲线
    - linear: 线性拟合

    Args:
        request: 拟合请求

    Returns:
        FitResponse: 拟合结果

    Raises:
        HTTPException: 数据验证失败时抛出400错误
    """
    try:
        # SubTask 13.1: 输入验证 - 数据数组长度限制
        if not validate_array_length(request.x_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"x_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.x_data)} 个",
            )
        if not validate_array_length(request.y_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"y_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.y_data)} 个",
            )

        x_data = np.array(request.x_data)
        y_data = np.array(request.y_data)

        # 验证x_data和y_data长度一致性
        if len(x_data) != len(y_data):
            raise HTTPException(
                status_code=400,
                detail=f"x_data和y_data长度不一致: x_data={len(x_data)}, y_data={len(y_data)}",
            )

        # 验证数据点数量最小值
        MIN_DATA_POINTS = 2
        if len(x_data) < MIN_DATA_POINTS:
            raise HTTPException(
                status_code=400,
                detail=f"数据点数量不足，至少需要 {MIN_DATA_POINTS} 个数据点，当前 {len(x_data)} 个",
            )

        if request.model_type == "langevin":
            result, fit_params = analyzer.fit_langevin(x_data, y_data)
            fitted_y = result.best_fit.tolist()
        elif request.model_type == "linear":
            slope, intercept = np.polyfit(x_data, y_data, 1)
            fitted_y = (slope * x_data + intercept).tolist()
            fit_params = {
                "slope": float(slope),
                "intercept": float(intercept),
                "chi2": 0.0,
                "redchi": 0.0,
            }
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported model type: {request.model_type}",
            )

        return FitResponse(
            success=True,
            message=f"Curve fitted using {request.model_type}",
            fit_params=fit_params,
            chi2=fit_params.get("chi2", 0.0),
            redchi=fit_params.get("redchi", 0.0),
            fitted_y=fitted_y,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Fit error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/hysteresis", response_model=HysteresisResponse)
async def analyze_hysteresis(request: HysteresisRequest):
    """
    磁滞回线分析

    完整的磁滞回线分析，包括背景扣除和关键参数提取：
    - Hc: 矫顽力
    - Mr: 剩磁
    - Ms: 饱和磁矩

    Args:
        request: 磁滞回线分析请求

    Returns:
        HysteresisResponse: 分析结果

    Raises:
        HTTPException: 数据验证失败时抛出400错误
    """
    try:
        # SubTask 13.1: 输入验证 - 数据数组长度限制
        if not validate_array_length(request.x_field, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"x_field数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.x_field)} 个",
            )
        if not validate_array_length(request.y_moment, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"y_moment数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.y_moment)} 个",
            )

        x_field = np.array(request.x_field)
        y_moment = np.array(request.y_moment)

        # 验证x_field和y_moment长度一致性
        if len(x_field) != len(y_moment):
            raise HTTPException(
                status_code=400,
                detail=f"x_field和y_moment长度不一致: x_field={len(x_field)}, y_moment={len(y_moment)}",
            )

        # 验证数据点数量最小值
        MIN_DATA_POINTS = 10
        if len(x_field) < MIN_DATA_POINTS:
            raise HTTPException(
                status_code=400,
                detail=f"数据点数量不足，磁滞回线分析至少需要 {MIN_DATA_POINTS} 个数据点，当前 {len(x_field)} 个",
            )

        result = analyzer.analyze_hysteresis_loop(
            x_field,
            y_moment,
            subtract_background=request.subtract_background,
            saturation_threshold=request.saturation_threshold,
        )

        return HysteresisResponse(
            success=True,
            message="Hysteresis loop analysis completed",
            Hc=result["Hc"],
            Mr=result["Mr"],
            Ms=result["Ms"],
            background_params=result["background_params"],
            x_corrected=result["x_corrected"].tolist(),
            y_corrected=result["y_corrected"].tolist(),
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Hysteresis analysis error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


# ==================== 多模型拟合对比 ====================


def _hyperbolic_function(H: np.ndarray, Bs: float, Hc: float, S: float) -> np.ndarray:
    """双曲正切磁滞模型函数。

    模型: B(H) = Bs * tanh((H - Hc) / S)

    Args:
        H: 磁场强度数组
        Bs: 饱和磁感应强度
        Hc: 矫顽力
        S: 磁滞宽度参数

    Returns:
        磁感应强度数组
    """
    S = max(S, 1e-10)  # 避免除零
    return Bs * np.tanh((H - Hc) / S)


def _arctangent_function(H: np.ndarray, Bs: float, Hc: float, S: float) -> np.ndarray:
    """反正切磁滞模型函数。

    模型: B(H) = (2 * Bs / pi) * arctan((H - Hc) / S)

    Args:
        H: 磁场强度数组
        Bs: 饱和磁感应强度
        Hc: 矫顽力
        S: 磁滞宽度参数

    Returns:
        磁感应强度数组
    """
    S = max(S, 1e-10)  # 避免除零
    return (2 * Bs / np.pi) * np.arctan((H - Hc) / S)


def _langevin_function(H: np.ndarray, Ms: float, alpha: float) -> np.ndarray:
    """Langevin函数模型。

    模型: M(H) = Ms * L(alpha * H)，其中 L(x) = coth(x) - 1/x

    Args:
        H: 磁场强度数组
        Ms: 饱和磁矩
        alpha: 拟合参数

    Returns:
        磁矩数组
    """
    ax = alpha * H
    result = np.zeros_like(ax, dtype=float)

    # 小参数区域：使用泰勒展开
    small_mask = np.abs(ax) < 0.1
    result[small_mask] = (
        ax[small_mask] / 3.0 - (ax[small_mask] ** 3) / 45.0 + 2 * (ax[small_mask] ** 5) / 945.0
    )

    # 大参数区域：使用渐近展开
    large_mask = np.abs(ax) > 20
    result[large_mask] = 1.0 - 1.0 / ax[large_mask]

    # 中等参数区域：使用标准公式
    medium_mask = ~small_mask & ~large_mask
    if np.any(medium_mask):
        with np.errstate(divide="ignore", invalid="ignore"):
            coth_ax = np.cosh(ax[medium_mask]) / np.sinh(ax[medium_mask])
            result[medium_mask] = coth_ax - 1.0 / ax[medium_mask]

    return Ms * result


def _convert_fit_result_to_response(result: FitResult) -> ModelFitResult:
    """将内部FitResult转换为API响应模型。

    Args:
        result: 内部拟合结果对象

    Returns:
        API响应模型
    """
    return ModelFitResult(
        model_name=result.model_name,
        params=result.params,
        r_squared=result.r_squared,
        rmse=result.rmse,
        aic=result.aic,
        bic=result.bic,
    )


@router.post("/multi-fit", response_model=MultiFitResponse)
async def multi_model_fit(request: MultiFitRequest):
    """执行多模型拟合对比。

    同时使用多个磁滞模型拟合数据，比较拟合结果并推荐最佳模型。

    支持的模型：
    - hyperbolic: 双曲正切模型 B(H) = Bs * tanh((H - Hc) / S)
    - arctangent: 反正切模型 B(H) = (2*Bs/pi) * arctan((H - Hc) / S)
    - braunbeck: Braunbeck磁滞模型
    - langevin: Langevin函数模型

    Args:
        request: 多模型拟合请求

    Returns:
        MultiFitResponse: 包含所有模型拟合结果和比较指标

    Raises:
        HTTPException: 数据验证失败或拟合失败时抛出400错误
    """
    try:
        # 输入验证 - 数据数组长度限制
        if not validate_array_length(request.h_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"h_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.h_data)} 个",
            )
        if not validate_array_length(request.b_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"b_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.b_data)} 个",
            )

        h_data = np.array(request.h_data)
        b_data = np.array(request.b_data)

        # 验证h_data和b_data长度一致性
        if len(h_data) != len(b_data):
            raise HTTPException(
                status_code=400,
                detail=f"h_data和b_data长度不一致: h_data={len(h_data)}, b_data={len(b_data)}",
            )

        # 验证数据点数量最小值
        MIN_DATA_POINTS = 5
        if len(h_data) < MIN_DATA_POINTS:
            raise HTTPException(
                status_code=400,
                detail=f"数据点数量不足，多模型拟合至少需要 {MIN_DATA_POINTS} 个数据点，当前 {len(h_data)} 个",
            )

        # 验证模型列表
        valid_models = ["hyperbolic", "arctangent", "braunbeck", "langevin"]
        invalid_models = [m for m in request.models if m not in valid_models]
        if invalid_models:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的模型类型: {invalid_models}。支持的模型: {valid_models}",
            )

        # 创建多模型拟合器
        fitter = MultiModelFitter()

        # 估计初始参数
        bs_init = np.max(np.abs(b_data)) * 0.8
        hc_init = np.max(np.abs(h_data)) * 0.1
        s_init = np.max(np.abs(h_data)) * 0.05
        alpha_init = 1.0

        # 注册模型
        for model_name in request.models:
            if model_name == "hyperbolic":
                fitter.register_model(
                    name="hyperbolic",
                    func=_hyperbolic_function,
                    initial_params=[bs_init, hc_init, s_init],
                    bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
                    param_names=["Bs", "Hc", "S"],
                )
            elif model_name == "arctangent":
                fitter.register_model(
                    name="arctangent",
                    func=_arctangent_function,
                    initial_params=[bs_init, hc_init, s_init],
                    bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
                    param_names=["Bs", "Hc", "S"],
                )
            elif model_name == "braunbeck":
                fitter.register_model(
                    name="braunbeck",
                    func=braunbeck_function,
                    initial_params=[bs_init, hc_init, s_init],
                    bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
                    param_names=["Bs", "Hc", "S"],
                )
            elif model_name == "langevin":
                fitter.register_model(
                    name="langevin",
                    func=_langevin_function,
                    initial_params=[bs_init, alpha_init],
                    bounds=([0.1, 1e-6], [np.inf, np.inf]),
                    param_names=["Ms", "alpha"],
                )

        # 执行拟合
        fit_results = fitter.fit_all(h_data, b_data)

        if not fit_results:
            raise HTTPException(
                status_code=400,
                detail="所有模型拟合均失败，请检查数据质量",
            )

        # 获取比较结果
        comparison = fitter.compare_models()

        # 转换结果格式
        response_results = [_convert_fit_result_to_response(r) for r in fit_results]

        # 生成建议
        recommendations = _generate_fit_recommendations(fit_results, comparison)

        return MultiFitResponse(
            results=response_results,
            best_model=comparison["best_model"],
            comparison_metrics={
                "rankings": comparison["rankings"],
                "delta_aic": comparison["delta_aic"],
                "aic_weights": comparison["aic_weights"],
            },
            recommendations=recommendations,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Multi-model fit error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


def _generate_fit_recommendations(
    fit_results: list[FitResult],
    comparison: dict,
) -> list[str]:
    """生成拟合建议。

    Args:
        fit_results: 拟合结果列表
        comparison: 比较结果字典

    Returns:
        建议列表
    """
    recommendations = []

    if not fit_results:
        recommendations.append("拟合失败，请检查数据质量")
        return recommendations

    best_result = fit_results[0]  # 已按AIC排序

    # 拟合质量建议
    if best_result.r_squared >= 0.95:
        recommendations.append(
            f"最佳模型 {best_result.model_name} 拟合效果优秀 (R²={best_result.r_squared:.4f})"
        )
    elif best_result.r_squared >= 0.90:
        recommendations.append(
            f"最佳模型 {best_result.model_name} 拟合效果良好 (R²={best_result.r_squared:.4f})"
        )
    elif best_result.r_squared >= 0.80:
        recommendations.append(
            f"最佳模型 {best_result.model_name} 拟合效果一般 (R²={best_result.r_squared:.4f})，"
            "建议检查数据质量或考虑其他模型"
        )
    else:
        recommendations.append(
            f"最佳模型 {best_result.model_name} 拟合效果较差 (R²={best_result.r_squared:.4f})，"
            "数据可能存在异常点或不适合当前模型"
        )

    # 模型选择建议
    if len(fit_results) > 1:
        delta_aic = comparison["delta_aic"]
        second_best = list(delta_aic.keys())[1] if len(delta_aic) > 1 else None

        if second_best and delta_aic[second_best] < 2:
            recommendations.append(
                f"模型 {best_result.model_name} 和 {second_best} 的 AIC 差值较小 "
                f"(ΔAIC={delta_aic[second_best]:.2f})，两者拟合效果相近"
            )
        elif second_best and delta_aic[second_best] < 10:
            recommendations.append(
                f"模型 {best_result.model_name} 相比 {second_best} 有一定优势 "
                f"(ΔAIC={delta_aic[second_best]:.2f})"
            )

    # RMSE建议
    if best_result.rmse > 0.1 * np.max(np.abs(best_result.y_predicted)):
        recommendations.append(f"拟合误差较大 (RMSE={best_result.rmse:.4f})，" "可能存在异常数据点")

    if not recommendations:
        recommendations.append("多模型拟合完成，结果质量良好")

    return recommendations


# ==================== 分析报告生成 ====================


@router.post("/report/generate", response_model=AnalysisReportResponse)
async def generate_report(request: ReportGenerateRequest):
    """生成分析报告。

    整合磁滞回线分析和多模型拟合结果，生成完整的分析报告。

    报告内容包括：
    - 磁滞回线参数（Hc、Mr、Ms、矩形比等）
    - 多模型拟合结果对比
    - 数据质量指标
    - 分析建议

    Args:
        request: 报告生成请求

    Returns:
        AnalysisReportResponse: 完整的分析报告

    Raises:
        HTTPException: 数据验证失败或分析失败时抛出400错误
    """
    try:
        # 输入验证 - 数据数组长度限制
        if not validate_array_length(request.h_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"h_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.h_data)} 个",
            )
        if not validate_array_length(request.b_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"b_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.b_data)} 个",
            )

        h_data = np.array(request.h_data)
        b_data = np.array(request.b_data)

        # 验证h_data和b_data长度一致性
        if len(h_data) != len(b_data):
            raise HTTPException(
                status_code=400,
                detail=f"h_data和b_data长度不一致: h_data={len(h_data)}, b_data={len(b_data)}",
            )

        # 验证数据点数量最小值
        MIN_DATA_POINTS = 5
        if len(h_data) < MIN_DATA_POINTS:
            raise HTTPException(
                status_code=400,
                detail=f"数据点数量不足，报告生成至少需要 {MIN_DATA_POINTS} 个数据点，当前 {len(h_data)} 个",
            )

        # 创建多模型拟合器并执行拟合
        fitter = MultiModelFitter()

        # 估计初始参数
        bs_init = np.max(np.abs(b_data)) * 0.8
        hc_init = np.max(np.abs(h_data)) * 0.1
        s_init = np.max(np.abs(h_data)) * 0.05

        # 注册默认模型
        fitter.register_model(
            name="hyperbolic",
            func=_hyperbolic_function,
            initial_params=[bs_init, hc_init, s_init],
            bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
            param_names=["Bs", "Hc", "S"],
        )
        fitter.register_model(
            name="arctangent",
            func=_arctangent_function,
            initial_params=[bs_init, hc_init, s_init],
            bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
            param_names=["Bs", "Hc", "S"],
        )
        fitter.register_model(
            name="braunbeck",
            func=braunbeck_function,
            initial_params=[bs_init, hc_init, s_init],
            bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
            param_names=["Bs", "Hc", "S"],
        )

        # 执行拟合
        fit_results = fitter.fit_all(h_data, b_data)

        # 生成分析报告
        report = generate_analysis_report(
            h_data=h_data,
            b_data=b_data,
            fit_results=fit_results,
            experiment_id=request.experiment_id,
            analyzer=analyzer,
        )

        # 转换拟合结果格式
        response_fit_results = [_convert_fit_result_to_response(r) for r in report.fit_results]

        # 序列化磁滞参数（处理numpy数组）
        hysteresis_params_serialized = _serialize_hysteresis_params(report.hysteresis_params)

        return AnalysisReportResponse(
            experiment_id=report.experiment_id,
            timestamp=report.timestamp,
            hysteresis_params=hysteresis_params_serialized,
            fit_results=response_fit_results,
            best_model=report.best_model,
            quality_metrics=report.quality_metrics,
            recommendations=report.recommendations,
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report generation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


def _serialize_hysteresis_params(params: dict) -> dict:
    """序列化磁滞参数，处理numpy数组。

    Args:
        params: 原始参数字典

    Returns:
        序列化后的参数字典
    """
    serialized = {}
    for key, value in params.items():
        if isinstance(value, np.ndarray):
            serialized[key] = value.tolist()
        elif isinstance(value, (np.integer, np.floating)):
            serialized[key] = float(value)
        elif isinstance(value, np.bool_):
            serialized[key] = bool(value)
        else:
            serialized[key] = value
    return serialized


# ==================== 报告导出 ====================


@router.post("/report/export")
async def export_report(
    request: ReportGenerateRequest,
    format: str = Query(
        default="json",
        description="导出格式: json, csv, pdf",
        pattern="^(json|csv|pdf)$",
    ),
):
    """导出分析报告。

    将分析报告导出为指定格式的文件。

    支持的导出格式：
    - json: JSON格式，包含完整结构和元数据
    - csv: CSV格式，包含数据表格和关键参数
    - pdf: PDF格式（预留接口，当前返回JSON）

    Args:
        request: 报告导出请求
        format: 导出格式，默认json

    Returns:
        Response: 文件下载响应

    Raises:
        HTTPException: 数据验证失败或导出失败时抛出400错误
    """
    try:
        # 输入验证 - 数据数组长度限制
        if not validate_array_length(request.h_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"h_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.h_data)} 个",
            )
        if not validate_array_length(request.b_data, MAX_DATA_POINTS):
            raise HTTPException(
                status_code=400,
                detail=f"b_data数据点数量超过最大限制 {MAX_DATA_POINTS}，当前 {len(request.b_data)} 个",
            )

        h_data = np.array(request.h_data)
        b_data = np.array(request.b_data)

        # 验证h_data和b_data长度一致性
        if len(h_data) != len(b_data):
            raise HTTPException(
                status_code=400,
                detail=f"h_data和b_data长度不一致: h_data={len(h_data)}, b_data={len(b_data)}",
            )

        # 验证数据点数量最小值
        MIN_DATA_POINTS = 5
        if len(h_data) < MIN_DATA_POINTS:
            raise HTTPException(
                status_code=400,
                detail=f"数据点数量不足，报告导出至少需要 {MIN_DATA_POINTS} 个数据点，当前 {len(h_data)} 个",
            )

        # 创建多模型拟合器并执行拟合
        fitter = MultiModelFitter()

        # 估计初始参数
        bs_init = np.max(np.abs(b_data)) * 0.8
        hc_init = np.max(np.abs(h_data)) * 0.1
        s_init = np.max(np.abs(h_data)) * 0.05

        # 注册默认模型
        fitter.register_model(
            name="hyperbolic",
            func=_hyperbolic_function,
            initial_params=[bs_init, hc_init, s_init],
            bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
            param_names=["Bs", "Hc", "S"],
        )
        fitter.register_model(
            name="braunbeck",
            func=braunbeck_function,
            initial_params=[bs_init, hc_init, s_init],
            bounds=([0.1, 0.0, 1e-6], [np.inf, np.inf, np.inf]),
            param_names=["Bs", "Hc", "S"],
        )

        # 执行拟合
        fit_results = fitter.fit_all(h_data, b_data)

        # 生成分析报告
        report = generate_analysis_report(
            h_data=h_data,
            b_data=b_data,
            fit_results=fit_results,
            experiment_id=request.experiment_id,
            analyzer=analyzer,
        )

        # 根据格式导出
        if format == "json":
            return _export_json_report(report, h_data, b_data, request.include_raw_data)
        elif format == "csv":
            return _export_csv_report(report, h_data, b_data, request.include_raw_data)
        elif format == "pdf":
            # PDF导出预留接口，当前返回JSON
            logger.warning("PDF export not implemented, returning JSON instead")
            return _export_json_report(report, h_data, b_data, request.include_raw_data)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"不支持的导出格式: {format}",
            )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Report export error: {e}")
        raise HTTPException(status_code=400, detail=str(e))


def _export_json_report(
    report,
    h_data: np.ndarray,
    b_data: np.ndarray,
    include_raw_data: bool,
) -> Response:
    """导出JSON格式报告。

    Args:
        report: 分析报告对象
        h_data: 磁场数据
        b_data: 磁感应强度数据
        include_raw_data: 是否包含原始数据

    Returns:
        Response: JSON文件响应
    """
    # 构建报告数据结构
    report_data = {
        "experiment_id": report.experiment_id,
        "timestamp": report.timestamp,
        "hysteresis_params": _serialize_hysteresis_params(report.hysteresis_params),
        "fit_results": [
            {
                "model_name": r.model_name,
                "params": r.params,
                "r_squared": r.r_squared,
                "rmse": r.rmse,
                "aic": r.aic,
                "bic": r.bic,
            }
            for r in report.fit_results
        ],
        "best_model": report.best_model,
        "quality_metrics": report.quality_metrics,
        "recommendations": report.recommendations,
    }

    # 可选：包含原始数据
    if include_raw_data:
        report_data["raw_data"] = {
            "h_data": h_data.tolist(),
            "b_data": b_data.tolist(),
        }

    # 生成JSON字符串
    json_content = json.dumps(report_data, indent=2, ensure_ascii=False)

    # 生成文件名
    filename = f"analysis_report_{report.experiment_id}.json"

    return Response(
        content=json_content,
        media_type="application/json",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


def _export_csv_report(
    report,
    h_data: np.ndarray,
    b_data: np.ndarray,
    include_raw_data: bool,
) -> Response:
    """导出CSV格式报告。

    Args:
        report: 分析报告对象
        h_data: 磁场数据
        b_data: 磁感应强度数据
        include_raw_data: 是否包含原始数据

    Returns:
        Response: CSV文件响应
    """
    lines = []

    # 报告头信息
    lines.append(f"# 分析报告")
    lines.append(f"# 实验ID: {report.experiment_id}")
    lines.append(f"# 生成时间: {report.timestamp}")
    lines.append(f"# 最佳模型: {report.best_model}")
    lines.append("#")

    # 磁滞参数
    lines.append("# 磁滞回线参数")
    for key, value in _serialize_hysteresis_params(report.hysteresis_params).items():
        if not isinstance(value, list):  # 跳过数组类型
            lines.append(f"# {key}: {value}")
    lines.append("#")

    # 质量指标
    lines.append("# 数据质量指标")
    for key, value in report.quality_metrics.items():
        lines.append(f"# {key}: {value}")
    lines.append("#")

    # 拟合结果表格
    lines.append("# 拟合结果对比")
    lines.append("model_name,r_squared,rmse,aic,bic")
    for r in report.fit_results:
        lines.append(f"{r.model_name},{r.r_squared:.6f},{r.rmse:.6f},{r.aic:.2f},{r.bic:.2f}")
    lines.append("#")

    # 建议
    lines.append("# 分析建议")
    for rec in report.recommendations:
        lines.append(f"# - {rec}")
    lines.append("#")

    # 原始数据（可选）
    if include_raw_data:
        lines.append("# 原始数据")
        lines.append("h_data,b_data")
        for h, b in zip(h_data, b_data):
            lines.append(f"{h:.6f},{b:.6f}")

    # 生成CSV内容
    csv_content = "\n".join(lines)

    # 生成文件名
    filename = f"analysis_report_{report.experiment_id}.csv"

    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
        },
    )


# ==================== 历史数据查询 ====================


@router.get("/history", response_model=HistoryQueryResponse)
async def query_history_data(
    experiment_ids: str | None = Query(None, description="实验ID列表，逗号分隔"),
    devices: str | None = Query(None, description="设备列表，逗号分隔"),
    start_time: str | None = Query(None, description="开始时间(ISO格式)"),
    end_time: str | None = Query(None, description="结束时间(ISO格式)"),
    data_types: str | None = Query(None, description="数据类型列表，逗号分隔"),
    limit: int = Query(1000, ge=1, le=10000, description="返回数据点数量限制"),
    offset: int = Query(0, ge=0, description="数据偏移量"),
):
    """
    查询历史数据。

    支持按实验ID、设备、时间范围等条件查询历史数据。
    返回符合条件的数据点和统计信息。

    Args:
        experiment_ids: 实验ID列表，逗号分隔
        devices: 设备列表，逗号分隔
        start_time: 开始时间(ISO格式)
        end_time: 结束时间(ISO格式)
        data_types: 数据类型列表，逗号分隔
        limit: 返回数据点数量限制
        offset: 数据偏移量

    Returns:
        HistoryQueryResponse: 历史数据查询结果

    Raises:
        HTTPException: 查询失败时抛出400错误
    """
    try:
        from datetime import datetime

        from core.data_storage import DataStorage

        # 获取存储实例
        storage = DataStorage()

        # 解析参数
        exp_id_list = None
        if experiment_ids:
            exp_id_list = [int(x.strip()) for x in experiment_ids.split(",") if x.strip()]

        device_list = None
        if devices:
            device_list = [x.strip() for x in devices.split(",") if x.strip()]

        data_type_list = None
        if data_types:
            data_type_list = [x.strip() for x in data_types.split(",") if x.strip()]

        # 解析时间
        start_dt = None
        end_dt = None
        if start_time:
            try:
                start_dt = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
            except ValueError:
                pass
        if end_time:
            try:
                end_dt = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
            except ValueError:
                pass

        # 查询数据
        all_data = []

        try:
            # 如果指定了实验ID，查询这些实验的数据
            if exp_id_list:
                for exp_id in exp_id_list:
                    try:
                        records = storage.get_experiment_data(exp_id, limit=limit)
                        all_data.extend(records)
                    except Exception as e:
                        logger.warning(f"Failed to get experiment {exp_id} data: {e}")
                        continue
            else:
                # 否则查询最近的实验数据
                try:
                    experiments = storage.list_experiments(limit=10)
                    for exp in experiments:
                        try:
                            records = storage.get_experiment_data(
                                exp["id"], limit=limit // len(experiments) if experiments else limit
                            )
                            all_data.extend(records)
                        except Exception as e:
                            logger.warning(
                                f"Failed to get experiment {exp.get('id', 'unknown')} data: {e}"
                            )
                            continue
                except Exception as e:
                    logger.warning(f"Failed to list experiments: {e}")
                    # 返回空数据而不是报错
                    pass
        except Exception as e:
            logger.error(f"Database query error: {e}")
            # 返回空数据而不是报错
            return HistoryQueryResponse(
                success=True,
                message="数据库查询异常，返回空数据",
                total=0,
                data=[],
                statistics={},
            )

        # 转换数据格式
        data_points = []
        for record in all_data[offset : offset + limit]:
            # 确定主要数值和单位
            value = 0.0
            unit = ""

            if (
                data_type_list
                and "field" in data_type_list
                and record.get("field_value") is not None
            ):
                value = record["field_value"]
                unit = "T"
            elif (
                data_type_list
                and "current" in data_type_list
                and record.get("current_value") is not None
            ):
                value = record["current_value"]
                unit = "A"
            elif (
                data_type_list
                and "temperature" in data_type_list
                and record.get("temperature") is not None
            ):
                value = record["temperature"]
                unit = "K"
            elif record.get("field_value") is not None:
                value = record["field_value"]
                unit = "T"
            elif record.get("current_value") is not None:
                value = record["current_value"]
                unit = "A"
            elif record.get("temperature") is not None:
                value = record["temperature"]
                unit = "K"
            elif record.get("position_mm") is not None:
                value = record["position_mm"]
                unit = "mm"

            data_points.append(
                {
                    "timestamp": record.get("timestamp", ""),
                    "experiment_id": record.get("experiment_id", 0),
                    "device": record.get("device"),
                    "position_mm": record.get("position_mm"),
                    "field_value": record.get("field_value"),
                    "current_value": record.get("current_value"),
                    "temperature": record.get("temperature"),
                    "value": value,
                    "unit": unit,
                }
            )

        # 计算统计信息
        values = [d["value"] for d in data_points if d["value"] != 0]
        statistics = {}
        if values:
            statistics = {
                "total": len(values),
                "avg": float(np.mean(values)),
                "max": float(np.max(values)),
                "min": float(np.min(values)),
                "std": float(np.std(values)),
            }

        return HistoryQueryResponse(
            success=True,
            message=f"查询成功，共 {len(data_points)} 条数据",
            total=len(all_data),
            data=data_points,
            statistics=statistics,
        )
    except Exception as e:
        logger.error(f"History query error: {e}")
        # 返回空数据而不是抛出异常
        return HistoryQueryResponse(
            success=False,
            message=f"查询失败: {str(e)}",
            total=0,
            data=[],
            statistics={},
        )


# ==================== 数据对比 ====================


@router.post("/compare", response_model=CompareResponse)
async def compare_datasets(request: CompareRequest):
    """
    对比多个数据集。

    对比多个实验或数据集的数据，计算差异指标。

    Args:
        request: 对比请求

    Returns:
        CompareResponse: 对比结果

    Raises:
        HTTPException: 对比失败时抛出400错误
    """
    try:
        from core.data_storage import DataStorage

        storage = DataStorage()

        # 收集各数据集的数据
        dataset_results = []

        for dataset in request.datasets:
            # 查询实验数据
            records = storage.get_experiment_data(dataset.experiment_id, limit=10000)

            # 根据数据类型提取数据
            data_points = []
            for record in records:
                value = None
                if dataset.data_type == "field" and record.get("field_value") is not None:
                    value = record["field_value"]
                elif dataset.data_type == "current" and record.get("current_value") is not None:
                    value = record["current_value"]
                elif dataset.data_type == "temperature" and record.get("temperature") is not None:
                    value = record["temperature"]
                elif dataset.data_type == "position" and record.get("position_mm") is not None:
                    value = record["position_mm"]

                if value is not None:
                    data_points.append(
                        {
                            "timestamp": record.get("timestamp", ""),
                            "value": value,
                        }
                    )

            # 归一化处理
            if request.normalize and data_points:
                values = [d["value"] for d in data_points]
                min_val = min(values)
                max_val = max(values)
                if max_val > min_val:
                    for d in data_points:
                        d["value"] = (d["value"] - min_val) / (max_val - min_val)

            # 计算统计信息
            values = [d["value"] for d in data_points]
            statistics = {}
            if values:
                statistics = {
                    "total": len(values),
                    "avg": float(np.mean(values)),
                    "max": float(np.max(values)),
                    "min": float(np.min(values)),
                    "std": float(np.std(values)),
                }

            dataset_results.append(
                {
                    "experiment_id": dataset.experiment_id,
                    "name": dataset.name,
                    "data": data_points,
                    "statistics": statistics,
                }
            )

        # 计算差异指标
        difference_metrics = {}
        if len(dataset_results) >= 2:
            values1 = [d["value"] for d in dataset_results[0]["data"]]
            values2 = [d["value"] for d in dataset_results[1]["data"]]

            if values1 and values2:
                # 对齐数据长度
                min_len = min(len(values1), len(values2))
                values1 = values1[:min_len]
                values2 = values2[:min_len]

                # 计算差异
                diff = [v1 - v2 for v1, v2 in zip(values1, values2)]

                difference_metrics = {
                    "mean_difference": float(np.mean(diff)),
                    "max_difference": float(np.max(diff)),
                    "min_difference": float(np.min(diff)),
                    "std_difference": float(np.std(diff)),
                    "correlation": (
                        float(np.corrcoef(values1, values2)[0, 1]) if min_len > 1 else 0.0
                    ),
                }

        return CompareResponse(
            success=True,
            message=f"对比完成，共 {len(dataset_results)} 个数据集",
            datasets=dataset_results,
            difference_metrics=difference_metrics,
        )
    except Exception as e:
        logger.error(f"Compare datasets error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
