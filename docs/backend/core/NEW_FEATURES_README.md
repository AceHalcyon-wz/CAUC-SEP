# 物理分析引擎 - 新增功能说明

## 概述

本次更新为 `backend/core/analysis.py` 添加了以下新功能：

1. **Braunbeck 磁滞模型拟合**
2. **多模型并行拟合与比较**
3. **拟合优度评估**
4. **分析报告自动生成**

---

## 1. Braunbeck 磁滞模型

### 功能说明

Braunbeck 模型用于描述磁滞回线，基于双曲正切函数：

```
B(H) = Bs * tanh((H - Hc) / S) + Bs * tanh((H + Hc) / S)
```

### 参数说明

- **Bs**: 饱和磁感应强度 (T)
- **Hc**: 矫顽力 (A/m)
- **S**: 磁滞宽度参数 (A/m)

### 使用示例

```python
import numpy as np
from core.analysis import braunbeck_function, PhysicsAnalyzer, FitModelType

# 生成测试数据
H = np.linspace(-1000, 1000, 200)
B = braunbeck_function(H, Bs=1.5, Hc=100.0, S=50.0)

# 添加噪声
B_noisy = B + np.random.normal(0, 0.03, len(H))

# 使用 PhysicsAnalyzer 拟合
analyzer = PhysicsAnalyzer()
result = analyzer.fit_model(H, B_noisy, FitModelType.BRAUNBECK)

# 查看结果
print(f"R² = {result['r_squared']:.4f}")
print(f"Bs = {result['parameters']['Bs']:.4f} T")
print(f"Hc = {result['parameters']['Hc']:.2f} A/m")
print(f"S = {result['parameters']['S']:.2f} A/m")
```

---

## 2. 多模型并行拟合

### 功能说明

`MultiModelFitter` 类支持同时使用多个模型拟合数据，并自动比较选择最佳模型。

### 主要方法

- `register_model()`: 注册拟合模型
- `fit_all()`: 并行执行所有模型拟合
- `compare_models()`: 比较所有模型拟合结果
- `get_best_model()`: 获取最佳模型

### 使用示例

```python
from core.analysis import MultiModelFitter, braunbeck_function

# 创建拟合器
fitter = MultiModelFitter()

# 注册模型
fitter.register_model(
    name="Braunbeck",
    func=braunbeck_function,
    initial_params=[1.0, 50.0, 30.0],
    bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
    param_names=["Bs", "Hc", "S"],
)

fitter.register_model(
    name="Linear",
    func=lambda x, a, b: a * x + b,
    initial_params=[0.0, 0.0],
    param_names=["slope", "intercept"],
)

# 执行拟合
results = fitter.fit_all(H, B_noisy)

# 比较模型
comparison = fitter.compare_models()
print(comparison['summary'])

# 获取最佳模型
best = fitter.get_best_model(criterion="aic")
print(f"最佳模型: {best.model_name}")
```

---

## 3. 拟合优度评估

### 功能说明

`calculate_goodness_of_fit()` 函数计算多个统计指标用于评估拟合质量。

### 返回指标

| 指标 | 说明 | 判断标准 |
|------|------|----------|
| R² | 决定系数 | 越接近1越好 |
| RMSE | 均方根误差 | 越小越好 |
| MAE | 平均绝对误差 | 越小越好 |
| AIC | Akaike信息准则 | 越小越好 |
| BIC | 贝叶斯信息准则 | 越小越好 |

### 使用示例

```python
from core.analysis import calculate_goodness_of_fit

# 计算拟合优度
metrics = calculate_goodness_of_fit(
    y_observed=y_data,
    y_predicted=y_fit,
    n_params=3
)

print(f"R² = {metrics['r_squared']:.4f}")
print(f"RMSE = {metrics['rmse']:.4f}")
print(f"AIC = {metrics['aic']:.2f}")
print(f"BIC = {metrics['bic']:.2f}")
```

---

## 4. 分析报告生成

### 功能说明

`generate_analysis_report()` 函数整合磁滞回线分析和多模型拟合结果，生成结构化的分析报告。

### 报告内容

- 实验ID和时间戳
- 磁滞回线参数（Hc, Mr, Ms, 矩形比）
- 拟合结果列表
- 最佳模型推荐
- 数据质量指标
- 智能建议

### 使用示例

```python
from core.analysis import generate_analysis_report, MultiModelFitter

# 执行多模型拟合
fitter = MultiModelFitter()
# ... 注册模型 ...
fit_results = fitter.fit_all(H, B_noisy)

# 生成报告
report = generate_analysis_report(
    h_data=H,
    b_data=B_noisy,
    fit_results=fit_results,
    experiment_id="EXP_2024_001"
)

# 查看报告
print(f"实验ID: {report.experiment_id}")
print(f"最佳模型: {report.best_model}")
print(f"矫顽力: {report.hysteresis_params['Hc']:.2f} A/m")
print(f"推荐建议: {report.recommendations}")
```

---

## 数据类说明

### FitResult

拟合结果数据类，存储单个模型的拟合结果：

```python
@dataclass
class FitResult:
    model_name: str           # 模型名称
    params: dict[str, float]  # 拟合参数
    r_squared: float          # R²决定系数
    rmse: float               # 均方根误差
    mae: float                # 平均绝对误差
    aic: float                # Akaike信息准则
    bic: float                # 贝叶斯信息准则
    residuals: np.ndarray     # 残差数组
    y_predicted: np.ndarray   # 预测值数组
```

### AnalysisReport

分析报告数据类，存储完整的分析报告：

```python
@dataclass
class AnalysisReport:
    experiment_id: str              # 实验ID
    timestamp: str                  # 时间戳
    hysteresis_params: dict         # 磁滞回线参数
    fit_results: list[FitResult]    # 拟合结果列表
    best_model: str                 # 最佳模型名称
    quality_metrics: dict           # 质量指标
    recommendations: list[str]      # 推荐建议
```

---

## 技术特性

### 数值稳定性

- Braunbeck 函数使用分段计算，避免 tanh 函数的数值溢出
- 小参数区域使用泰勒展开
- 大参数区域使用渐近近似

### 异常处理

- 所有函数包含完整的参数验证
- 拟合失败时自动回退到初始参数
- 数据不足时提供明确的警告信息

### 性能优化

- 使用 NumPy 向量化计算
- 支持大数据集处理
- 自动内存管理

---

## 完整示例

运行示例文件查看完整用法：

```bash
cd backend
python -m core.examples_new_features
```

---

## 更新日志

### v1.1.0 (2026-03-08)

**新增功能：**
- ✨ 添加 Braunbeck 磁滞模型拟合
- ✨ 添加多模型并行拟合器 `MultiModelFitter`
- ✨ 添加拟合优度评估函数 `calculate_goodness_of_fit`
- ✨ 添加分析报告生成函数 `generate_analysis_report`
- ✨ 添加数据类 `FitResult` 和 `AnalysisReport`

**改进：**
- 📝 完善所有函数的 docstring 文档
- 🔧 增强数值稳定性处理
- ⚡ 优化拟合算法性能

---

## 注意事项

⚠️ **重要提示：**

1. 生成的代码需要经过人工审查和测试后才能部署到生产环境
2. 拟合参数的初始值对结果影响较大，建议根据实际数据调整
3. 多模型比较时，确保模型具有可比性（相同的数据范围和单位）
4. AIC/BIC 准则适用于模型选择，但不保证物理意义正确

---

## 技术支持

如有问题或建议，请联系开发团队。
