# CAUC-SEP 开发者指南

<!--
文件名: DEVELOPER_GUIDE.md
路径: docs/
功能: 开发者技术文档，详细介绍核心模块使用方法
版本: v1.1
项目版本: v0.3.0

作者: CAUC-SEP 开发团队
创建日期: 2024-03-01
最后更新: 2026-03-14
-->

**版本**: v1.1  
**更新日期**: 2026-03-14  
**适用对象**: 开发人员、维护人员

---

## 目录

1. [项目概述](#1-项目概述)
2. [技术栈](#2-技术栈)
3. [开发环境搭建](#3-开发环境搭建)
4. [项目结构](#4-项目结构)
5. [核心模块说明](#5-核心模块说明)
6. [API开发指南](#6-api开发指南)
7. [前端开发指南](#7-前端开发指南)
8. [数据库设计](#8-数据库设计)
9. [测试指南](#9-测试指南)
10. [部署指南](#10-部署指南)
11. [代码规范](#11-代码规范)
12. [安全加固](#12-安全加固)
13. [性能优化](#13-性能优化)
14. [常见问题](#14-常见问题)

---

## 1. 概述

本文档面向CAUC-SEP自旋电子器件实验平台的开发者，详细介绍新增核心模块的使用方法、API调用示例和性能优化建议。

### 1.1 新增模块概览

| 模块 | 文件路径 | 功能说明 |
|------|----------|----------|
| 实时调度器 | `backend/core/rt_scheduler.py` | Windows高精度定时器和实时调度 |
| 数据管道 | `backend/core/data_pipeline.py` | 流式数据处理与触发器管理 |
| 健康监控 | `backend/api/health.py` | 系统健康检查与Prometheus指标 |
| 多模型拟合 | `backend/core/analysis.py` | 多模型并行拟合与比较 |
| 分析报告 | `backend/api/analysis.py` | 报告生成与导出功能 |

---

## 2. 新增模块使用说明

### 2.1 实时调度器 (rt_scheduler.py)

实时调度器模块提供Windows平台的高精度定时和实时调度功能，适用于需要精确时序控制的场景。

#### 2.1.1 核心类

**WindowsRTScheduler**

综合管理高精度定时、线程优先级和CPU亲和性。

```python
from core.rt_scheduler import (
    WindowsRTScheduler,
    RealtimeContext,
    THREAD_PRIORITY_HIGHEST,
    THREAD_PRIORITY_TIME_CRITICAL,
)

# 方式一：使用上下文管理器（推荐）
with WindowsRTScheduler(interval_ms=5) as scheduler:
    # 设置线程优先级
    scheduler.set_thread_priority(THREAD_PRIORITY_HIGHEST)
    
    # 设置进程高优先级
    scheduler.set_process_priority_high()
    
    # 绑定到指定CPU核心
    scheduler.set_cpu_affinity([0])
    
    # 执行实时任务
    for i in range(1000):
        # 精确控制循环
        pass

# 方式二：使用简化上下文
with RealtimeContext(
    priority=THREAD_PRIORITY_HIGHEST,
    cpu_cores=[0, 1],
    interval_ms=5
):
    # 执行实时任务
    pass
```

**WinMMWrapper**

Windows多媒体定时器API封装，实现毫秒级精度控制。

```python
from core.rt_scheduler import WinMMWrapper

winmm = WinMMWrapper()

# 获取最小定时器精度
min_res = winmm.get_min_resolution()  # 通常返回1ms

# 设置定时器精度为1ms
winmm.time_begin_period(1)

try:
    # 执行需要高精度定时的代码
    pass
finally:
    # 恢复系统设置
    winmm.time_end_period(1)
```

**ThreadPriorityManager**

线程优先级管理器。

```python
from core.rt_scheduler import (
    ThreadPriorityManager,
    THREAD_PRIORITY_HIGHEST,
    THREAD_PRIORITY_TIME_CRITICAL,
)

manager = ThreadPriorityManager()

# 设置线程优先级
manager.set_thread_priority(THREAD_PRIORITY_HIGHEST)

# 获取当前优先级
current = manager.get_thread_priority()

# 设置进程优先级类
manager.set_process_priority_high()
```

**CPUAffinityManager**

CPU亲和性管理器，将线程绑定到指定核心。

```python
from core.rt_scheduler import CPUAffinityManager

manager = CPUAffinityManager()

# 获取CPU核心数
cpu_count = manager.get_cpu_count()

# 获取可用核心列表
available_cores = manager.get_available_cores()

# 绑定到核心0
manager.set_thread_affinity([0])

# 绑定到多个核心
manager.set_thread_affinity([0, 1, 2])
```

#### 2.1.2 便捷函数

```python
from core.rt_scheduler import (
    high_precision_timer,
    set_realtime_priority,
    bind_to_cpu_core,
    check_realtime_capability,
)

# 高精度定时器上下文
with high_precision_timer(interval_ms=1):
    # 执行需要高精度定时的代码
    pass

# 设置实时优先级（需要管理员权限）
set_realtime_priority()

# 绑定到指定CPU核心
bind_to_cpu_core(0)

# 检查系统实时能力
capability = check_realtime_capability()
print(f"CPU核心数: {capability['cpu_count']}")
print(f"最小定时器精度: {capability['min_timer_resolution_ms']}ms")
print(f"管理员权限: {capability['admin_privilege']}")
```

#### 2.1.3 使用注意事项

1. **管理员权限**: 设置实时优先级（`THREAD_PRIORITY_TIME_CRITICAL`）需要管理员权限
2. **系统稳定性**: 实时优先级可能导致系统不稳定，谨慎使用
3. **资源释放**: 使用上下文管理器确保资源正确释放
4. **平台限制**: 仅支持Windows平台

---

### 2.2 数据管道 (data_pipeline.py)

数据管道模块实现流式数据处理，支持环形缓冲区、触发器管理和多通道数据缓存。

#### 2.2.1 核心类

**RingBuffer**

线程安全的环形缓冲区。

```python
from core.data_pipeline import RingBuffer
import numpy as np

# 创建缓冲区
buffer = RingBuffer(size=10000, dtype=np.float64)

# 写入数据
data = np.random.randn(1000)
written = buffer.write(data)

# 读取数据（FIFO，读取后移除）
read_data = buffer.read(500)

# 查看最新数据（不移除）
latest = buffer.peek(100)

# 获取所有数据（不移除）
all_data = buffer.read_all()

# 获取统计信息
stats = buffer.get_statistics()
print(f"缓冲区使用率: {stats['usage_percent']:.1f}%")
print(f"数据范围: [{stats['min']:.3f}, {stats['max']:.3f}]")

# 清空缓冲区
buffer.clear()
```

**StreamProcessor**

流式数据处理器，支持多种触发机制。

```python
from core.data_pipeline import StreamProcessor, TriggerType
import numpy as np

processor = StreamProcessor(buffer_size=10000)

# 添加阈值触发器
def threshold_callback(data):
    print(f"触发器激活！数据长度: {len(data)}")

processor.add_trigger(
    name="high_threshold",
    trigger_type=TriggerType.THRESHOLD,
    condition=lambda data: len(data) > 0 and data[-1] > 10.0,
    callback=threshold_callback,
)

# 添加模式触发器
pattern = np.array([1.0, 2.0, 3.0])
processor.add_trigger(
    name="pattern_match",
    trigger_type=TriggerType.PATTERN,
    condition=lambda data: len(data) >= 3 and np.allclose(data[-3:], pattern),
    callback=lambda data: print("模式匹配！"),
)

# 处理数据
data = np.random.randn(100)
result = processor.process(data)
print(f"写入数据点: {result['written_count']}")
print(f"激活的触发器: {result['triggered']}")

# 检测磁滞回线完成
x_data = np.linspace(-1, 1, 100)
y_data = np.sin(x_data * np.pi)
is_complete = processor.detect_hysteresis_loop(x_data, y_data)

# 检测峰值
peaks = processor.detect_peak(data, threshold=2.0)
print(f"检测到 {peaks['peak_count']} 个峰值")
```

**DataPipeline**

完整的数据管道，整合缓冲区和处理器。

```python
from core.data_pipeline import DataPipeline
import asyncio

pipeline = DataPipeline(buffer_size=10000)

# 注册分析回调
def analysis_callback(data):
    channel = data['channel']
    values = data['values']
    print(f"通道 {channel}: 收到 {len(values)} 个数据点")

pipeline.register_analysis_callback(analysis_callback)

# 启动管道
pipeline.start()

# 消费硬件数据流（异步）
async def consume_data():
    for i in range(100):
        await pipeline.consume_hardware_stream({
            'channel': 'default',
            'values': np.random.randn(100),
            'timestamp': time.time(),
        })

# 获取通道数据
channel_data = pipeline.get_channel_data('default')

# 获取统计信息
stats = pipeline.get_statistics()

# 停止管道
pipeline.stop()
```

#### 2.2.2 便捷函数

```python
from core.data_pipeline import (
    create_threshold_trigger,
    create_pattern_trigger,
    create_periodic_trigger,
)

# 创建阈值触发器
trigger_type, condition, callback = create_threshold_trigger(
    threshold=10.0,
    callback=lambda data: print("超过阈值！"),
    comparison="greater",
)

# 创建模式触发器
pattern = np.array([1.0, 2.0, 3.0])
trigger_type, condition, callback = create_pattern_trigger(
    pattern=pattern,
    callback=lambda data: print("模式匹配！"),
    tolerance=0.1,
)

# 创建周期触发器
trigger_type, condition, callback = create_periodic_trigger(
    interval_points=100,
    callback=lambda data: print("周期触发！"),
)
```

---

### 2.3 健康监控 (health.py)

健康监控模块提供系统健康检查和Prometheus指标导出功能。

#### 2.3.1 API端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 系统健康检查 |
| `/api/metrics` | GET | Prometheus指标 |
| `/api/devices/status` | GET | 设备状态汇总 |
| `/api/resources` | GET | 详细系统资源 |

#### 2.3.2 使用示例

**健康检查**

```bash
curl http://localhost:8000/api/health
```

响应示例：

```json
{
  "status": "healthy",
  "timestamp": "2026-03-07T10:30:00.000Z",
  "version": "0.3.0",
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.5,
    "disk_percent": 35.8,
    "uptime_seconds": 3600.5,
    "devices": [...]
  }
}
```

**Prometheus指标**

```bash
curl http://localhost:8000/api/metrics
```

响应示例：

```
# HELP cpu_usage_percent CPU使用率百分比
# TYPE cpu_usage_percent gauge
cpu_usage_percent 45.2

# HELP device_connected 设备连接状态
# TYPE device_connected gauge
device_connected{device_id="stepper_01",device_type="stepper_motor"} 1
```

**设备状态汇总**

```bash
curl http://localhost:8000/api/devices/status
```

#### 2.3.3 Prometheus集成

在Prometheus配置文件中添加：

```yaml
scrape_configs:
  - job_name: 'cauc-sep'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
    scrape_interval: 15s
```

#### 2.3.4 健康状态判断逻辑

| 条件 | 状态 |
|------|------|
| CPU < 80%, 内存 < 80%, 磁盘 < 85%, 所有设备连接 | `healthy` |
| CPU >= 80% 或 内存 >= 80% 或 磁盘 >= 85% 或 部分设备断开 | `degraded` |
| CPU >= 95% 或 内存 >= 95% 或 磁盘 >= 95% 或 多数设备故障 | `unhealthy` |

---

### 2.4 多模型拟合 (analysis.py)

多模型拟合模块支持同时使用多个物理模型拟合数据，并自动选择最佳模型。

#### 2.4.1 支持的模型

| 模型 | 公式 | 参数 | 适用场景 |
|------|------|------|----------|
| `hyperbolic` | B(H) = Bs * tanh((H - Hc) / S) | Bs, Hc, S | 简单磁滞回线 |
| `arctangent` | B(H) = (2*Bs/π) * arctan((H - Hc) / S) | Bs, Hc, S | 中等非线性 |
| `braunbeck` | B(H) = Bs * tanh((H-Hc)/S) + Bs * tanh((H+Hc)/S) | Bs, Hc, S | 完整磁滞回线 |
| `langevin` | M(H) = Ms * L(α*H) | Ms, α | 超顺磁颗粒 |
| `linear` | y = a * x + b | a, b | 线性关系 |
| `polynomial` | y = Σ a_i * x^i | a_0, a_1, ... | 多项式拟合 |
| `exponential` | y = A * exp(B * x) + C | A, B, C | 指数衰减/增长 |
| `gaussian` | y = A * exp(-(x-μ)²/(2σ²)) + C | A, μ, σ, C | 高斯分布 |

#### 2.4.2 使用示例

**单模型拟合**

```python
from core.analysis import PhysicsAnalyzer, FitModelType

analyzer = PhysicsAnalyzer()

# 线性拟合
result = analyzer.fit_model(x_data, y_data, FitModelType.LINEAR)
print(f"斜率: {result['parameters']['slope']}")
print(f"截距: {result['parameters']['intercept']}")
print(f"R²: {result['r_squared']}")

# Langevin函数拟合
result = analyzer.fit_model(x_data, y_data, FitModelType.LANGEVIN)
print(f"饱和磁矩 Ms: {result['parameters']['Ms']}")
print(f"拟合参数 α: {result['parameters']['alpha']}")

# Braunbeck模型拟合
result = analyzer.fit_model(x_data, y_data, FitModelType.BRAUNBECK)
print(f"饱和磁感应强度 Bs: {result['parameters']['Bs']}")
print(f"矫顽力 Hc: {result['parameters']['Hc']}")
```

**多模型拟合对比**

```python
from core.analysis import MultiModelFitter, braunbeck_function
import numpy as np

# 创建拟合器
fitter = MultiModelFitter()

# 注册模型
fitter.register_model(
    name="hyperbolic",
    func=lambda H, Bs, Hc, S: Bs * np.tanh((H - Hc) / S),
    initial_params=[1.5, 100.0, 50.0],
    bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
    param_names=["Bs", "Hc", "S"],
)

fitter.register_model(
    name="braunbeck",
    func=braunbeck_function,
    initial_params=[1.5, 100.0, 50.0],
    bounds=([0.1, 0.0, 1.0], [10.0, 1000.0, 500.0]),
    param_names=["Bs", "Hc", "S"],
)

# 执行拟合
results = fitter.fit_all(H_data, B_data)

# 获取比较结果
comparison = fitter.compare_models()
print(f"最佳模型: {comparison['best_model']}")
print(comparison['summary'])

# 根据不同准则选择最佳模型
best_by_aic = fitter.get_best_model(criterion="aic")
best_by_r2 = fitter.get_best_model(criterion="r_squared")
```

**磁滞回线分析**

```python
from core.analysis import PhysicsAnalyzer, BackgroundMethod

analyzer = PhysicsAnalyzer()

# 完整分析
result = analyzer.analyze_hysteresis_loop(
    x_field=H_data,
    y_moment=M_data,
    subtract_background=True,
    background_method=BackgroundMethod.LINEAR,
    saturation_threshold=None,  # 自动计算
)

# 提取关键参数
print(f"矫顽力 Hc: {result['Hc']} A/m")
print(f"正向矫顽力: {result['Hc_positive']} A/m")
print(f"负向矫顽力: {result['Hc_negative']} A/m")
print(f"剩磁 Mr: {result['Mr']} emu")
print(f"饱和磁矩 Ms: {result['Ms']} emu")
print(f"矩形比: {result['squareness']}")

# 获取背景扣除后的数据
H_corrected = result['x_corrected']
M_corrected = result['y_corrected']
```

#### 2.4.3 拟合优度指标

| 指标 | 说明 | 判断标准 |
|------|------|----------|
| R² | 决定系数 | 越接近1越好，>0.95为优秀 |
| RMSE | 均方根误差 | 越小越好 |
| MAE | 平均绝对误差 | 越小越好 |
| AIC | Akaike信息准则 | 越小越好，用于模型比较 |
| BIC | 贝叶斯信息准则 | 越小越好，惩罚复杂模型 |

**AIC权重解释**:

- ΔAIC < 2: 模型效果相近
- ΔAIC 2-10: 有一定优势
- ΔAIC > 10: 明显优势

---

### 2.5 分析报告生成

#### 2.5.1 生成报告

```python
from core.analysis import generate_analysis_report, PhysicsAnalyzer

analyzer = PhysicsAnalyzer()

# 生成报告
report = generate_analysis_report(
    h_data=H_data,
    b_data=B_data,
    fit_results=fit_results,
    experiment_id="exp_001",
    analyzer=analyzer,
)

# 访问报告内容
print(f"实验ID: {report.experiment_id}")
print(f"时间戳: {report.timestamp}")
print(f"最佳模型: {report.best_model}")
print(f"矫顽力: {report.hysteresis_params['Hc']}")

# 获取建议
for rec in report.recommendations:
    print(f"- {rec}")
```

#### 2.5.2 数据导出

```python
from core.analysis import PhysicsAnalyzer, ExportFormat

analyzer = PhysicsAnalyzer()

# 导出为CSV
analyzer.export_data(
    filepath="data.csv",
    x_data=H_data,
    y_data=B_data,
    format=ExportFormat.CSV,
    metadata={"experiment": "exp_001"},
    delimiter=",",
    precision=15,
)

# 导出为HDF5
analyzer.export_data(
    filepath="data.h5",
    x_data=H_data,
    y_data=B_data,
    format=ExportFormat.HDF5,
    metadata={"sample": "FeCo"},
    group_path="/data",
)

# 导出为JSON
analyzer.export_data(
    filepath="data.json",
    x_data=H_data,
    y_data=B_data,
    format=ExportFormat.JSON,
    metadata={"temperature": 300},
    indent=2,
)

# 导出分析结果
analyzer.export_analysis_results(
    filepath="analysis_result.json",
    analysis_results=result,
    format=ExportFormat.JSON,
)
```

---

## 3. API调用示例

### 3.1 健康监控API

**Python示例**:

```python
import requests

# 健康检查
response = requests.get("http://localhost:8000/api/health")
health = response.json()
print(f"系统状态: {health['status']}")

# Prometheus指标
response = requests.get("http://localhost:8000/api/metrics")
print(response.text)

# 设备状态汇总
response = requests.get("http://localhost:8000/api/devices/status")
devices = response.json()
print(f"已连接设备: {devices['connected_devices']}/{devices['total_devices']}")
```

**JavaScript示例**:

```javascript
// 健康检查
async function checkHealth() {
  const response = await fetch('http://localhost:8000/api/health');
  const health = await response.json();
  console.log(`系统状态: ${health.status}`);
  return health;
}

// 设备状态汇总
async function getDeviceStatus() {
  const response = await fetch('http://localhost:8000/api/devices/status');
  const status = await response.json();
  return status;
}
```

### 3.2 多模型拟合API

**Python示例**:

```python
import requests
import numpy as np

# 准备数据
H = np.linspace(-1000, 1000, 500)
B = 1.5 * np.tanh((H - 100) / 50) + np.random.randn(500) * 0.02

# 多模型拟合
response = requests.post(
    "http://localhost:8000/api/v1/analysis/multi-fit",
    json={
        "h_data": H.tolist(),
        "b_data": B.tolist(),
        "models": ["hyperbolic", "arctangent", "braunbeck"],
    }
)

result = response.json()
print(f"最佳模型: {result['best_model']}")
print(f"R²: {result['results'][0]['r_squared']:.4f}")
```

**JavaScript示例**:

```javascript
// 多模型拟合
async function multiModelFit(hData, bData, models) {
  const response = await fetch('http://localhost:8000/api/v1/analysis/multi-fit', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      h_data: hData,
      b_data: bData,
      models: models,
    }),
  });
  return await response.json();
}
```

### 3.3 报告生成与导出API

**Python示例**:

```python
import requests

# 生成报告
response = requests.post(
    "http://localhost:8000/api/v1/analysis/report/generate",
    json={
        "h_data": H.tolist(),
        "b_data": B.tolist(),
        "experiment_id": "exp_20260307_001",
    }
)

report = response.json()
print(f"矫顽力 Hc: {report['hysteresis_params']['Hc']} A/m")
print(f"最佳模型: {report['best_model']}")

# 导出报告为JSON
response = requests.post(
    "http://localhost:8000/api/v1/analysis/report/export?format=json",
    json={
        "h_data": H.tolist(),
        "b_data": B.tolist(),
        "experiment_id": "exp_20260307_001",
        "include_raw_data": True,
    }
)

# 保存文件
with open("report.json", "wb") as f:
    f.write(response.content)

# 导出报告为CSV
response = requests.post(
    "http://localhost:8000/api/v1/analysis/report/export?format=csv",
    json={
        "h_data": H.tolist(),
        "b_data": B.tolist(),
        "experiment_id": "exp_20260307_001",
        "include_raw_data": True,
    }
)

with open("report.csv", "wb") as f:
    f.write(response.content)
```

---

## 4. 性能优化建议

### 4.1 实时调度器优化

#### 4.1.1 定时器精度选择

| 场景 | 推荐精度 | 说明 |
|------|----------|------|
| 普通数据采集 | 10-20ms | 默认精度，系统开销小 |
| 高速数据采集 | 1-5ms | 高精度，增加CPU负载 |
| 实时控制回路 | 1ms | 最高精度，需要管理员权限 |

```python
# 根据场景选择精度
with WindowsRTScheduler(interval_ms=5) as scheduler:
    # 高速数据采集场景
    pass
```

#### 4.1.2 CPU亲和性绑定

```python
# 将实时任务绑定到独立核心，避免干扰
with RealtimeContext(
    priority=THREAD_PRIORITY_HIGHEST,
    cpu_cores=[0],  # 绑定到核心0
    interval_ms=1,
):
    # 执行实时任务
    pass
```

#### 4.1.3 避免频繁创建销毁

```python
# 不推荐：频繁创建销毁
for i in range(100):
    with high_precision_timer(1):
        pass  # 每次都有开销

# 推荐：复用上下文
with high_precision_timer(1):
    for i in range(100):
        pass  # 只有一次开销
```

### 4.2 数据管道优化

#### 4.2.1 缓冲区大小选择

| 数据速率 | 推荐缓冲区大小 | 说明 |
|----------|----------------|------|
| < 1kHz | 1000-5000 | 小缓冲区，低延迟 |
| 1-10kHz | 5000-20000 | 中等缓冲区 |
| > 10kHz | 20000-100000 | 大缓冲区，防溢出 |

```python
# 根据数据速率选择缓冲区大小
pipeline = DataPipeline(buffer_size=20000)  # 适合10kHz数据
```

#### 4.2.2 触发器优化

```python
# 避免复杂条件判断
# 不推荐
processor.add_trigger(
    name="complex",
    trigger_type=TriggerType.THRESHOLD,
    condition=lambda data: np.sum(np.fft.fft(data)) > 100,  # 计算量大
    callback=callback,
)

# 推荐：简化条件
processor.add_trigger(
    name="simple",
    trigger_type=TriggerType.THRESHOLD,
    condition=lambda data: len(data) > 0 and np.max(data) > 10,  # 计算量小
    callback=callback,
)
```

#### 4.2.3 多通道数据处理

```python
# 使用异步处理提高吞吐量
async def process_channels():
    tasks = [
        pipeline.consume_hardware_stream({
            'channel': f'ch_{i}',
            'values': data[i],
        })
        for i in range(4)
    ]
    await asyncio.gather(*tasks)
```

### 4.3 数据分析优化

#### 4.3.1 数据预处理

```python
# 数据量大时，先降采样再拟合
from scipy import signal

# 降采样
downsampled = signal.resample(original_data, len(original_data) // 10)

# 再进行拟合
result = analyzer.fit_model(x_downsampled, y_downsampled, model_type)
```

#### 4.3.2 模型选择策略

```python
# 快速预拟合选择最佳模型类型
quick_result = analyzer.fit_model(x_data[:100], y_data[:100], FitModelType.LINEAR)

if quick_result['r_squared'] > 0.9:
    # 线性模型足够好
    final_model = FitModelType.LINEAR
else:
    # 需要非线性模型
    final_model = FitModelType.BRAUNBECK

# 使用完整数据拟合
result = analyzer.fit_model(x_data, y_data, final_model)
```

#### 4.3.3 内存优化

```python
# 大数据集使用HDF5格式
import h5py

# 直接从HDF5读取数据进行处理
with h5py.File('large_data.h5', 'r') as f:
    # 分块读取
    for i in range(0, len(f['data']), 10000):
        chunk = f['data'][i:i+10000]
        # 处理数据块
        process_chunk(chunk)
```

### 4.4 API性能优化

#### 4.4.1 批量请求

```python
# 不推荐：多次单独请求
for data in data_list:
    requests.post("/api/v1/analysis/smooth", json={"y_data": data})

# 推荐：批量处理
response = requests.post(
    "/api/v1/analysis/smooth",
    json={"y_data": np.concatenate(data_list).tolist()}
)
```

#### 4.4.2 连接复用

```python
import requests
from requests.adapters import HTTPAdapter

# 创建会话并配置连接池
session = requests.Session()
adapter = HTTPAdapter(pool_connections=10, pool_maxsize=20)
session.mount('http://', adapter)

# 复用连接
response1 = session.get("http://localhost:8000/api/health")
response2 = session.get("http://localhost:8000/api/devices/status")
```

---

## 5. 常见问题与解决方案

### 5.1 实时调度器问题

**问题**: 设置实时优先级失败

**原因**: 缺少管理员权限

**解决方案**:

1. 以管理员身份运行程序
2. 或使用较低的优先级

```python
# 使用较低的优先级（不需要管理员权限）
with RealtimeContext(priority=THREAD_PRIORITY_ABOVE_NORMAL):
    pass
```

---

**问题**: 定时器精度不稳定

**原因**: 系统负载过高或CPU核心被其他进程占用

**解决方案**:

1. 绑定到独立CPU核心
2. 关闭不必要的后台程序

```python
# 绑定到独立核心
with RealtimeContext(cpu_cores=[0]):
    pass
```

### 5.2 数据管道问题

**问题**: 缓冲区溢出

**原因**: 数据写入速度超过读取速度

**解决方案**:

1. 增大缓冲区
2. 优化数据处理逻辑
3. 使用多线程处理

```python
# 增大缓冲区
pipeline = DataPipeline(buffer_size=50000)

# 使用独立线程处理
import threading

def process_thread():
    while True:
        data = pipeline.get_channel_data()
        process(data)

thread = threading.Thread(target=process_thread, daemon=True)
thread.start()
```

---

**问题**: 触发器不响应

**原因**: 触发条件不满足或触发器被禁用

**解决方案**:

```python
# 检查触发器状态
processor.enable_trigger("trigger_name", True)

# 调试触发条件
def debug_condition(data):
    result = len(data) > 0 and data[-1] > 10
    print(f"条件结果: {result}, 数据: {data[-1] if len(data) > 0 else 'empty'}")
    return result

processor.add_trigger(
    name="debug_trigger",
    trigger_type=TriggerType.THRESHOLD,
    condition=debug_condition,
    callback=lambda data: print("触发！"),
)
```

### 5.3 数据分析问题

**问题**: 拟合不收敛

**原因**: 初始参数估计不准确或数据质量差

**解决方案**:

1. 提供更好的初始参数
2. 检查数据质量
3. 尝试不同模型

```python
# 提供初始参数
result = analyzer.fit_model(
    x_data, y_data,
    FitModelType.BRAUNBECK,
    initial_params={"Bs": 1.5, "Hc": 100.0, "S": 50.0}
)

# 检查数据质量
print(f"数据点数: {len(x_data)}")
print(f"数据范围: [{np.min(x_data)}, {np.max(x_data)}]")
print(f"NaN数量: {np.sum(np.isnan(y_data))}")
```

---

**问题**: R²值很低

**原因**: 模型选择不当或数据存在异常点

**解决方案**:

```python
# 使用多模型对比
fitter = MultiModelFitter()
# 注册多个模型...
results = fitter.fit_all(x_data, y_data)

# 检查异常点
residuals = y_data - y_predicted
outliers = np.abs(residuals) > 3 * np.std(residuals)
print(f"异常点数量: {np.sum(outliers)}")

# 移除异常点后重新拟合
x_clean = x_data[~outliers]
y_clean = y_data[~outliers]
```

---

**问题**: 导出文件过大

**原因**: 包含了大量原始数据

**解决方案**:

```python
# 不包含原始数据
analyzer.export_analysis_results(
    filepath="report.json",
    analysis_results=result,
    format=ExportFormat.JSON,
)

# 或降采样后导出
downsampled_x = x_data[::10]  # 每10个点取1个
downsampled_y = y_data[::10]
analyzer.export_data(
    filepath="data.csv",
    x_data=downsampled_x,
    y_data=downsampled_y,
    format=ExportFormat.CSV,
)
```

### 5.4 API调用问题

**问题**: 请求超时

**原因**: 数据量大或服务器负载高

**解决方案**:

```python
# 增加超时时间
response = requests.post(
    url,
    json=data,
    timeout=60  # 60秒超时
)

# 或分批处理
batch_size = 1000
for i in range(0, len(data), batch_size):
    batch = data[i:i+batch_size]
    response = requests.post(url, json=batch)
```

---

**问题**: 内存不足

**原因**: 一次性加载大量数据

**解决方案**:

```python
# 使用生成器分批处理
def data_generator(data, batch_size):
    for i in range(0, len(data), batch_size):
        yield data[i:i+batch_size]

for batch in data_generator(large_data, 1000):
    response = requests.post(url, json=batch)
    process_response(response)
```

---

## 附录

### A. 错误代码表

| 错误代码 | 说明 | 解决方案 |
|----------|------|----------|
| E6001 | 实时调度器初始化失败 | 检查Windows API权限 |
| E6002 | 定时器精度设置失败 | 尝试较大的精度值 |
| E6003 | CPU亲和性设置失败 | 检查核心ID是否有效 |
| E6004 | 缓冲区溢出 | 增大缓冲区或优化处理速度 |
| E6005 | 触发器条件错误 | 检查条件函数实现 |
| E6006 | 拟合不收敛 | 检查初始参数和数据质量 |
| E6007 | 数据导出失败 | 检查文件路径和权限 |

### B. 性能基准

| 操作 | 数据量 | 耗时 | 内存占用 |
|------|--------|------|----------|
| 信号平滑 | 10000点 | <10ms | <1MB |
| 单模型拟合 | 1000点 | <50ms | <5MB |
| 多模型拟合(4模型) | 1000点 | <200ms | <10MB |
| 磁滞回线分析 | 1000点 | <100ms | <5MB |
| 报告生成 | 1000点 | <500ms | <10MB |
| JSON导出 | 10000点 | <100ms | <20MB |

### C. 参考资料

1. **Windows Multimedia Timer**: https://docs.microsoft.com/en-us/windows/win32/multimedia/multimedia-timers
2. **lmfit文档**: https://lmfit.github.io/lmfit-py/
3. **Prometheus数据模型**: https://prometheus.io/docs/concepts/data_model/
4. **NumPy性能优化**: https://numpy.org/doc/stable/user/performance.html

---

## 12. 安全加固

### 12.1 安全中间件配置

系统已集成多层安全中间件，确保API安全性：

| 中间件 | 功能 | 配置位置 |
|--------|------|----------|
| TracingMiddleware | 链路追踪，请求监控 | `middleware/tracing.py` |
| RateLimitMiddleware | API访问频率限制 | `middleware/rate_limit.py` |
| SecurityHeadersMiddleware | 安全响应头设置 | `middleware/security.py` |
| AuditMiddleware | 审计日志记录 | `middleware/audit.py` |

### 12.2 CORS安全配置

```python
# 使用环境感知的CORS配置
from middleware.cors_config import get_cors_config, validate_cors_security

# 获取CORS配置
cors_config = get_cors_config()

# 验证安全性
warnings = validate_cors_security(cors_config)
for warning in warnings:
    logger.warning(f"CORS Security: {warning}")
```

### 12.3 输入验证增强

所有API端点使用Pydantic模型进行严格的输入验证：

```python
from pydantic import BaseModel, Field, validator

class MoveRequest(BaseModel):
    """移动请求模型。"""
    position_mm: float = Field(..., description="目标位置(mm)", ge=-100, le=100)
    velocity_mm_s: float = Field(10.0, description="速度(mm/s)", ge=1, le=50)
    
    @validator('position_mm')
    def validate_position(cls, v):
        if abs(v) > 100:
            raise ValueError('位置超出软件限位范围')
        return v
```

### 12.4 敏感信息日志脱敏

日志系统自动脱敏敏感信息：

```python
# 配置日志脱敏
from core.logging_config import setup_logging

logger = setup_logging(
    log_dir="logs",
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    level=logging.INFO,
    json_format=False,
    compress_logs=True,
)
```

### 12.5 API访问频率限制

系统实现了基于IP和用户的访问频率限制：

| 端点类型 | 限制 | 时间窗口 |
|----------|------|----------|
| 普通API | 100次/分钟 | 60秒 |
| 写入操作 | 30次/分钟 | 60秒 |
| WebSocket | 10连接/分钟 | 60秒 |

---

## 13. 性能优化

### 13.1 启动优化

系统启动时自动执行优化：

```python
from core.static_files import optimize_startup

# 启动优化（预加载模块、优化GC等）
startup_result = optimize_startup(
    optimize_numpy=True,
    preload_modules=True,
    optimize_gc=True,
)
```

### 13.2 缓存系统

支持Redis和本地内存缓存双模式：

```python
from core.cache import init_cache_manager, RedisConfig

# 初始化缓存（自动降级到内存缓存）
cache_manager = init_cache_manager(
    config=RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        max_connections=10,
    ),
    fallback_to_memory=True,
    key_prefix="cauc_sep:",
)

# 使用缓存
await cache_manager.set("key", "value", ttl=300)
value = await cache_manager.get("key")
```

### 13.3 WebSocket优化

WebSocket连接支持心跳检测和推送频率控制：

```python
# 前端配置
const { connect } = useWebSocket('ws://localhost:8000/ws/devices', {
  heartbeat: {
    enabled: true,
    interval: 30000,  // 30秒
    timeout: 5000
  },
  reconnect: {
    enabled: true,
    maxAttempts: 5,
    delay: 1000
  }
})
```

### 13.4 数据库优化

- 使用SQLite WAL模式提高并发性能
- 自动清理过期日志（保留30天）
- 支持数据库连接池

### 13.5 前端性能优化

- 路由懒加载
- 虚拟滚动列表
- 数据节流与防抖
- 离线数据缓存

---

## 14. 常见问题

### 14.1 服务启动问题

**问题**: 端口被占用

**解决方案**:
```bash
# Windows - 查找占用端口的进程
netstat -ano | findstr :8000

# 结束进程
taskkill /PID <PID> /F
```

### 14.2 设备连接问题

**问题**: 设备无法连接

**排查步骤**:
1. 检查设备是否上电
2. 确认串口号配置正确
3. 检查波特率设置
4. 尝试重新插拔USB转换器

### 14.3 性能问题

**问题**: 系统响应缓慢

**解决方案**:
1. 查看系统健康状态：`/api/health`
2. 检查CPU/内存使用率
3. 清理历史数据
4. 调整WebSocket推送频率

---

**文档修订历史**

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-07 | 初始版本 | Tech Writer Agent |
| v1.1 | 2026-03-08 | 更新文档日期 | Tech Writer Agent |
| v1.2 | 2026-03-14 | 添加安全加固、性能优化章节，更新项目结构 | Tech Writer Agent |

---

*CAUC-SEP 自旋电子器件实验平台 | 开发者指南*  
*版本 0.3.0 | © 2025-2026 版权所有*
