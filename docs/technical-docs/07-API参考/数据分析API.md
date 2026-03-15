# 数据分析 API

本文档描述 CAUC-SEP 自旋电子器件实验平台的数据分析 API 接口规范。

## 目录

- [概述](#概述)
- [信号处理 API](#信号处理-api)
- [曲线拟合 API](#曲线拟合-api)
- [磁滞回线分析 API](#磁滞回线分析-api)
- [多模型拟合 API](#多模型拟合-api)
- [报告生成 API](#报告生成-api)
- [历史数据查询 API](#历史数据查询-api)
- [数据对比 API](#数据对比-api)

---

## 概述

数据分析 API 提供实验数据的后处理和分析功能，支持：

- **信号平滑**：Savitzky-Golay 滤波、巴特沃斯低通滤波
- **曲线拟合**：Langevin 函数拟合、线性拟合
- **磁滞回线分析**：矫顽力、剩磁、饱和磁矩计算
- **多模型拟合对比**：双曲正切、反正切、Braunbeck、Langevin 模型
- **分析报告生成**：整合分析结果，支持 JSON/CSV/PDF 导出
- **历史数据查询**：多条件筛选、统计分析

基础路径：`/api/v1/analysis`

---

## 信号处理 API

### 信号平滑

```http
POST /api/v1/analysis/smooth
Content-Type: application/json

{
  "y_data": [1.0, 2.0, 3.0, 4.0, 5.0],
  "method": "savgol",
  "window_length": 11,
  "polyorder": 2,
  "butter_lowcut": 0.1,
  "butter_order": 4
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `y_data` | array | 是 | 待平滑的数据数组（最大100000点） |
| `method` | string | 是 | 平滑方法（savgol/butterworth） |
| `window_length` | integer | 否 | Savitzky-Golay 窗口长度（奇数） |
| `polyorder` | integer | 否 | Savitzky-Golay 多项式阶数 |
| `butter_lowcut` | float | 否 | 巴特沃斯滤波器截止频率 |
| `butter_order` | integer | 否 | 巴特沃斯滤波器阶数 |

**响应示例**：

```json
{
  "success": true,
  "message": "Signal smoothed using savgol",
  "smoothed_data": [1.1, 1.9, 3.0, 4.1, 4.9]
}
```

**支持的平滑方法**：

| 方法 | 说明 |
|------|------|
| `savgol` | Savitzky-Golay 滤波（局部多项式拟合平滑） |
| `butterworth` | 巴特沃斯低通滤波（频域滤波平滑） |

---

## 曲线拟合 API

### 曲线拟合

```http
POST /api/v1/analysis/fit
Content-Type: application/json

{
  "x_data": [0.0, 0.1, 0.2, 0.3, 0.4],
  "y_data": [0.0, 0.5, 0.8, 0.9, 0.95],
  "model_type": "langevin"
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `x_data` | array | 是 | X 轴数据数组（最大100000点） |
| `y_data` | array | 是 | Y 轴数据数组（最大100000点） |
| `model_type` | string | 是 | 拟合模型类型 |

**响应示例**：

```json
{
  "success": true,
  "message": "Curve fitted using langevin",
  "fit_params": {
    "Ms": 1.0,
    "alpha": 0.5,
    "chi2": 0.001,
    "redchi": 0.0002
  },
  "chi2": 0.001,
  "redchi": 0.0002,
  "fitted_y": [0.0, 0.48, 0.79, 0.91, 0.96]
}
```

**支持的拟合模型**：

| 模型 | 公式 | 说明 |
|------|------|------|
| `langevin` | M(H) = Ms * L(α*H) | Langevin 函数拟合磁化曲线 |
| `linear` | y = slope * x + intercept | 线性拟合 |

---

## 磁滞回线分析 API

### 磁滞回线分析

```http
POST /api/v1/analysis/hysteresis
Content-Type: application/json

{
  "x_field": [-1.0, -0.8, -0.6, -0.4, -0.2, 0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
  "y_moment": [-0.9, -0.7, -0.5, -0.3, -0.1, 0.0, 0.1, 0.3, 0.5, 0.7, 0.9],
  "subtract_background": true,
  "saturation_threshold": 0.8
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `x_field` | array | 是 | 磁场强度数据（A/m） |
| `y_moment` | array | 是 | 磁矩数据（任意单位） |
| `subtract_background` | boolean | 否 | 是否扣除背景，默认 true |
| `saturation_threshold` | float | 否 | 饱和阈值，默认 0.8 |

**响应示例**：

```json
{
  "success": true,
  "message": "Hysteresis loop analysis completed",
  "Hc": 125.3,
  "Mr": 0.85,
  "Ms": 1.52,
  "background_params": {
    "coefficients": [0.001, 0.002],
    "r_squared": 0.98,
    "method": "linear"
  },
  "x_corrected": [-1.0, -0.8, ...],
  "y_corrected": [-0.9, -0.7, ...]
}
```

**返回参数说明**：

| 参数 | 类型 | 说明 |
|------|------|------|
| `Hc` | float | 矫顽力（A/m） |
| `Mr` | float | 剩磁（任意单位） |
| `Ms` | float | 饱和磁矩（任意单位） |
| `background_params` | object | 背景扣除参数 |
| `x_corrected` | array | 校正后的磁场数据 |
| `y_corrected` | array | 校正后的磁矩数据 |

---

## 多模型拟合 API

### 多模型拟合对比

```http
POST /api/v1/analysis/multi-fit
Content-Type: application/json

{
  "h_data": [-1000, -800, -600, -400, -200, 0, 200, 400, 600, 800, 1000],
  "b_data": [-1.45, -1.42, -1.38, -1.30, -1.10, 0.0, 1.10, 1.30, 1.38, 1.42, 1.45],
  "models": ["hyperbolic", "arctangent", "braunbeck", "langevin"]
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `h_data` | array | 是 | 磁场强度数据（A/m） |
| `b_data` | array | 是 | 磁感应强度数据（T） |
| `models` | array | 是 | 拟合模型列表 |

**支持的模型**：

| 模型 | 公式 | 说明 |
|------|------|------|
| `hyperbolic` | B(H) = Bs * tanh((H - Hc) / S) | 双曲正切模型 |
| `arctangent` | B(H) = (2*Bs/π) * arctan((H - Hc) / S) | 反正切模型 |
| `braunbeck` | B(H) = Bs * tanh((H-Hc)/S) + Bs * tanh((H+Hc)/S) | Braunbeck 磁滞模型 |
| `langevin` | M(H) = Ms * L(α*H) | Langevin 函数模型 |

**响应示例**：

```json
{
  "results": [
    {
      "model_name": "braunbeck",
      "params": {"Bs": 1.52, "Hc": 125.3, "S": 45.2},
      "r_squared": 0.9985,
      "rmse": 0.0123,
      "aic": -1250.5,
      "bic": -1245.3
    },
    {
      "model_name": "hyperbolic",
      "params": {"Bs": 1.50, "Hc": 120.0, "S": 50.0},
      "r_squared": 0.9920,
      "rmse": 0.0256,
      "aic": -1235.3,
      "bic": -1230.1
    }
  ],
  "best_model": "braunbeck",
  "comparison_metrics": {
    "rankings": [
      {"model": "braunbeck", "rank": 1, "score": 0.85},
      {"model": "hyperbolic", "rank": 2, "score": 0.15}
    ],
    "delta_aic": {"braunbeck": 0.0, "hyperbolic": 15.2},
    "aic_weights": {"braunbeck": 0.85, "hyperbolic": 0.15}
  },
  "recommendations": [
    "最佳模型 braunbeck 拟合效果优秀 (R²=0.9985)"
  ]
}
```

**拟合结果字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `model_name` | string | 模型名称 |
| `params` | object | 拟合参数 |
| `r_squared` | float | 决定系数 R² |
| `rmse` | float | 均方根误差 |
| `aic` | float | 赤池信息准则 |
| `bic` | float | 贝叶斯信息准则 |

---

## 报告生成 API

### 生成分析报告

```http
POST /api/v1/analysis/report/generate
Content-Type: application/json

{
  "h_data": [-1000, -800, -600, -400, -200, 0, 200, 400, 600, 800, 1000],
  "b_data": [-1.45, -1.42, -1.38, -1.30, -1.10, 0.0, 1.10, 1.30, 1.38, 1.42, 1.45],
  "experiment_id": "exp_20260315_001"
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `h_data` | array | 是 | 磁场强度数据 |
| `b_data` | array | 是 | 磁感应强度数据 |
| `experiment_id` | string | 否 | 实验ID |

**响应示例**：

```json
{
  "experiment_id": "exp_20260315_001",
  "timestamp": "2026-03-15T10:30:00.000Z",
  "hysteresis_params": {
    "Hc": 125.3,
    "Mr": 0.85,
    "Ms": 1.52,
    "squareness": 0.56,
    "Hc_positive": 124.8,
    "Hc_negative": 125.8
  },
  "fit_results": [
    {
      "model_name": "braunbeck",
      "params": {"Bs": 1.52, "Hc": 125.3, "S": 45.2},
      "r_squared": 0.9985,
      "rmse": 0.0123,
      "aic": -1250.5,
      "bic": -1245.3
    }
  ],
  "best_model": "braunbeck",
  "quality_metrics": {
    "n_data_points": 500,
    "h_range": 2000.0,
    "b_range": 2.9,
    "data_density": 0.25,
    "signal_to_noise": 45.2
  },
  "recommendations": [
    "数据分析完成，结果质量良好",
    "矫顽力 Hc = 125.30 A/m，可用于评估材料磁硬度"
  ]
}
```

### 导出分析报告

```http
POST /api/v1/analysis/report/export?format=json
Content-Type: application/json

{
  "h_data": [-1000, -800, -600, -400, -200, 0, 200, 400, 600, 800, 1000],
  "b_data": [-1.45, -1.42, -1.38, -1.30, -1.10, 0.0, 1.10, 1.30, 1.38, 1.42, 1.45],
  "experiment_id": "exp_20260315_001",
  "include_raw_data": true
}
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `format` | string | 否 | 导出格式（json/csv/pdf），默认 json |

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `include_raw_data` | boolean | 否 | 是否包含原始数据，默认 false |

**支持的导出格式**：

| 格式 | 说明 |
|------|------|
| `json` | JSON 格式，包含完整结构和元数据 |
| `csv` | CSV 格式，包含数据表格和关键参数 |
| `pdf` | PDF 格式（预留接口） |

**响应**：返回文件下载响应，Content-Disposition 头包含文件名。

---

## 历史数据查询 API

### 查询历史数据

```http
GET /api/v1/analysis/history?experiment_ids=1,2,3&devices=electromagnet&start_time=2026-03-01T00:00:00Z&limit=1000
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `experiment_ids` | string | 否 | 实验 ID 列表，逗号分隔 |
| `devices` | string | 否 | 设备列表，逗号分隔 |
| `start_time` | string | 否 | 开始时间（ISO 格式） |
| `end_time` | string | 否 | 结束时间（ISO 格式） |
| `data_types` | string | 否 | 数据类型列表，逗号分隔 |
| `limit` | integer | 否 | 返回数据点数量限制，默认 1000 |
| `offset` | integer | 否 | 数据偏移量，默认 0 |

**响应示例**：

```json
{
  "success": true,
  "message": "查询成功，共 500 条数据",
  "total": 500,
  "data": [
    {
      "timestamp": "2026-03-15T10:30:00.000Z",
      "experiment_id": 1,
      "device": "electromagnet",
      "position_mm": 10.0,
      "field_value": 0.5,
      "current_value": 2.5,
      "temperature": 298.15,
      "value": 0.5,
      "unit": "T"
    }
  ],
  "statistics": {
    "total": 500,
    "avg": 0.45,
    "max": 1.0,
    "min": 0.0,
    "std": 0.15
  }
}
```

---

## 数据对比 API

### 对比多个数据集

```http
POST /api/v1/analysis/compare
Content-Type: application/json

{
  "datasets": [
    {
      "experiment_id": 1,
      "name": "实验1",
      "data_type": "field"
    },
    {
      "experiment_id": 2,
      "name": "实验2",
      "data_type": "field"
    }
  ],
  "normalize": true
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `datasets` | array | 是 | 数据集列表 |
| `normalize` | boolean | 否 | 是否归一化数据，默认 false |

**数据集参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `experiment_id` | integer | 是 | 实验 ID |
| `name` | string | 否 | 数据集名称 |
| `data_type` | string | 是 | 数据类型（field/current/temperature/position） |

**响应示例**：

```json
{
  "success": true,
  "message": "对比完成，共 2 个数据集",
  "datasets": [
    {
      "experiment_id": 1,
      "name": "实验1",
      "data": [
        {"timestamp": "2026-03-15T10:30:00.000Z", "value": 0.5}
      ],
      "statistics": {
        "total": 100,
        "avg": 0.45,
        "max": 1.0,
        "min": 0.0,
        "std": 0.15
      }
    }
  ],
  "difference_metrics": {
    "mean_difference": 0.05,
    "max_difference": 0.15,
    "min_difference": -0.10,
    "std_difference": 0.08,
    "correlation": 0.95
  }
}
```

---

## 数据限制说明

### 输入数据限制

为防止内存耗尽攻击，所有数据数组输入均有以下限制：

| 参数 | 最大值 |
|------|--------|
| 数据点数量 | 100,000 |

### 最小数据点要求

| 分析类型 | 最小数据点 |
|----------|------------|
| 信号平滑 | 3 |
| 曲线拟合 | 2 |
| 磁滞回线分析 | 10 |
| 多模型拟合 | 5 |
| 报告生成 | 5 |

---

## 相关文档

- [设备控制 API](./设备控制API.md)
- [用户管理 API](./用户管理API.md)
- [系统监控 API](./系统监控API.md)
- [数据分析引擎](../04-核心模块/数据分析引擎.md)
