"""
新增物理分析功能使用示例

本示例展示如何使用新增的物理分析功能：
1. Braunbeck 磁滞模型拟合
2. 多模型并行拟合与比较
3. 拟合优度评估
4. 分析报告自动生成

作者: Agent
创建日期: 2024-03-07
"""

import matplotlib.pyplot as plt
import numpy as np

from core.analysis import (
    FitModelType,
    MultiModelFitter,
    PhysicsAnalyzer,
    braunbeck_function,
    calculate_goodness_of_fit,
    generate_analysis_report,
)


def example_1_braunbeck_fitting():
    """示例 1: 使用 Braunbeck 模型拟合磁滞回线。"""
    print("\n" + "=" * 70)
    print("示例 1: Braunbeck 磁滞模型拟合")
    print("=" * 70)

    H = np.linspace(-1000, 1000, 200)
    Bs_true = 1.5
    Hc_true = 100.0
    S_true = 50.0

    B = braunbeck_function(H, Bs_true, Hc_true, S_true)
    B_noisy = B + np.random.normal(0, 0.03, len(H))

    analyzer = PhysicsAnalyzer()
    result = analyzer.fit_model(H, B_noisy, FitModelType.BRAUNBECK)

    print("\n拟合结果:")
    print(f"  R² = {result['r_squared']:.4f}")
    print(f"  饱和磁感应强度 Bs = {result['parameters']['Bs']:.4f} T")
    print(f"  矫顽力 Hc = {result['parameters']['Hc']:.2f} A/m")
    print(f"  磁滞宽度 S = {result['parameters']['S']:.2f} A/m")

    plt.figure(figsize=(10, 6))
    plt.plot(H, B_noisy, "b.", label="实验数据", alpha=0.5)
    plt.plot(H, result["y_fit"], "r-", linewidth=2, label="Braunbeck 拟合")
    plt.xlabel("磁场强度 H (A/m)")
    plt.ylabel("磁感应强度 B (T)")
    plt.title("Braunbeck 磁滞模型拟合")
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig("braunbeck_fit.png", dpi=150)
    plt.close()
    print("\n图表已保存: braunbeck_fit.png")


def example_2_multi_model_fitting():
    """示例 2: 多模型并行拟合与比较。"""
    print("\n" + "=" * 70)
    print("示例 2: 多模型并行拟合与比较")
    print("=" * 70)

    np.random.seed(42)
    H = np.linspace(-1000, 1000, 200)
    B = braunbeck_function(H, Bs=1.5, Hc=100.0, S=50.0)
    B_noisy = B + np.random.normal(0, 0.05, len(H))

    def linear_model(x, a, b):
        return a * x + b

    def quadratic_model(x, a, b, c):
        return a * x**2 + b * x + c

    fitter = MultiModelFitter()

    fitter.register_model(
        name="Braunbeck",
        func=braunbeck_function,
        initial_params=[1.0, 50.0, 30.0],
        bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
        param_names=["Bs", "Hc", "S"],
    )

    fitter.register_model(
        name="Linear",
        func=linear_model,
        initial_params=[0.0, 0.0],
        param_names=["slope", "intercept"],
    )

    fitter.register_model(
        name="Quadratic",
        func=quadratic_model,
        initial_params=[0.0, 0.0, 0.0],
        param_names=["a", "b", "c"],
    )

    results = fitter.fit_all(H, B_noisy)

    comparison = fitter.compare_models()
    print(f"\n{comparison['summary']}")

    best = fitter.get_best_model(criterion="aic")
    print(f"\n最佳模型: {best.model_name}")
    print(f"  R² = {best.r_squared:.4f}")
    print(f"  RMSE = {best.rmse:.4f}")

    plt.figure(figsize=(12, 8))

    plt.subplot(2, 1, 1)
    plt.plot(H, B_noisy, "k.", label="实验数据", alpha=0.3, markersize=4)
    colors = ["r", "g", "b"]
    for i, result in enumerate(results):
        plt.plot(
            H,
            result.y_predicted,
            colors[i],
            label=f"{result.model_name} (R²={result.r_squared:.3f})",
            linewidth=2,
        )
    plt.xlabel("磁场强度 H (A/m)")
    plt.ylabel("磁感应强度 B (T)")
    plt.title("多模型拟合比较")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.subplot(2, 1, 2)
    for i, result in enumerate(results):
        plt.plot(H, result.residuals, colors[i], label=f"{result.model_name}", alpha=0.7)
    plt.xlabel("磁场强度 H (A/m)")
    plt.ylabel("残差 (T)")
    plt.title("拟合残差比较")
    plt.legend()
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig("multi_model_comparison.png", dpi=150)
    plt.close()
    print("\n图表已保存: multi_model_comparison.png")


def example_3_goodness_of_fit():
    """示例 3: 拟合优度评估。"""
    print("\n" + "=" * 70)
    print("示例 3: 拟合优度评估")
    print("=" * 70)

    np.random.seed(42)
    x = np.linspace(0, 10, 100)
    y_true = 2.5 * np.sin(x) + 1.0
    y_observed = y_true + np.random.normal(0, 0.3, len(x))

    y_fit_good = 2.4 * np.sin(x) + 1.1
    y_fit_poor = 0.5 * x + 2.0

    metrics_good = calculate_goodness_of_fit(y_observed, y_fit_good, n_params=2)
    metrics_poor = calculate_goodness_of_fit(y_observed, y_fit_poor, n_params=2)

    print("\n较好拟合的质量指标:")
    print(f"  R² = {metrics_good['r_squared']:.4f}")
    print(f"  RMSE = {metrics_good['rmse']:.4f}")
    print(f"  MAE = {metrics_good['mae']:.4f}")
    print(f"  AIC = {metrics_good['aic']:.2f}")
    print(f"  BIC = {metrics_good['bic']:.2f}")

    print("\n较差拟合的质量指标:")
    print(f"  R² = {metrics_poor['r_squared']:.4f}")
    print(f"  RMSE = {metrics_poor['rmse']:.4f}")
    print(f"  MAE = {metrics_poor['mae']:.4f}")
    print(f"  AIC = {metrics_poor['aic']:.2f}")
    print(f"  BIC = {metrics_poor['bic']:.2f}")

    print("\n指标解释:")
    print("  - R²: 决定系数，越接近1越好")
    print("  - RMSE: 均方根误差，越小越好")
    print("  - MAE: 平均绝对误差，越小越好")
    print("  - AIC: Akaike信息准则，越小越好（平衡拟合优度与模型复杂度）")
    print("  - BIC: 贝叶斯信息准则，越小越好（对复杂模型惩罚更严格）")


def example_4_analysis_report():
    """示例 4: 生成完整的分析报告。"""
    print("\n" + "=" * 70)
    print("示例 4: 分析报告自动生成")
    print("=" * 70)

    np.random.seed(42)
    H = np.linspace(-1000, 1000, 300)
    B = braunbeck_function(H, Bs=1.5, Hc=100.0, S=50.0)
    B_noisy = B + np.random.normal(0, 0.02, len(H))

    fitter = MultiModelFitter()
    fitter.register_model(
        name="Braunbeck",
        func=braunbeck_function,
        initial_params=[1.0, 50.0, 30.0],
        bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
        param_names=["Bs", "Hc", "S"],
    )
    fit_results = fitter.fit_all(H, B_noisy)

    report = generate_analysis_report(
        h_data=H,
        b_data=B_noisy,
        fit_results=fit_results,
        experiment_id="EXP_2024_001",
    )

    print(f"\n{'='*70}")
    print("分析报告")
    print(f"{'='*70}")
    print(f"实验ID: {report.experiment_id}")
    print(f"分析时间: {report.timestamp}")
    print(f"最佳模型: {report.best_model}")

    print("\n磁滞回线参数:")
    print(f"  矫顽力 Hc = {report.hysteresis_params.get('Hc', 0):.2f} A/m")
    print(f"  剩磁 Mr = {report.hysteresis_params.get('Mr', 0):.4f} T")
    print(f"  饱和磁矩 Ms = {report.hysteresis_params.get('Ms', 0):.4f}")
    print(f"  矩形比 = {report.hysteresis_params.get('squareness', 0):.4f}")

    print("\n数据质量指标:")
    for key, value in report.quality_metrics.items():
        print(f"  {key}: {value:.4f}")

    print("\n拟合结果:")
    for result in report.fit_results:
        print(f"  {result.model_name}: R²={result.r_squared:.4f}, AIC={result.aic:.2f}")

    print("\n推荐建议:")
    for i, rec in enumerate(report.recommendations, 1):
        print(f"  {i}. {rec}")


def main():
    """运行所有示例。"""
    print("\n" + "=" * 70)
    print("新增物理分析功能使用示例")
    print("=" * 70)

    example_1_braunbeck_fitting()
    example_2_multi_model_fitting()
    example_3_goodness_of_fit()
    example_4_analysis_report()

    print("\n" + "=" * 70)
    print("示例运行完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()
