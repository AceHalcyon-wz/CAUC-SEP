# 健康监控 API 文档

**版本**: v1.0  
**更新日期**: 2026-03-08  
**基础路径**: `/api`

---

## 概述

健康监控API提供系统健康状态检查、性能指标导出、设备状态监控和告警管理功能。该模块支持：

- 系统资源监控（CPU、内存、磁盘）
- 设备健康状态检查
- Prometheus格式指标导出
- 健康评分算法（0-100分）
- 告警规则管理与触发

---

## 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/health` | GET | 获取系统健康状态 |
| `/api/health/score` | GET | 获取健康评分详情 |
| `/api/metrics` | GET | 获取Prometheus格式指标 |
| `/api/devices/status` | GET | 获取设备状态汇总 |
| `/api/resources` | GET | 获取详细系统资源信息 |
| `/api/alerts` | GET | 获取告警信息 |
| `/api/alerts/active` | GET | 获取活跃告警 |
| `/api/alerts/rules` | GET/POST | 获取/添加告警规则 |
| `/api/alerts/{alert_id}/acknowledge` | POST | 确认告警 |

---

## 系统健康检查

### 获取系统健康状态

```http
GET /api/health
```

**功能说明**: 综合检查系统资源（CPU、内存、磁盘）和所有设备状态，返回整体健康评估、健康评分和优化建议。

**响应模型**:

```json
{
  "status": "healthy",
  "timestamp": "2026-03-08T10:30:00.000Z",
  "version": "0.3.0",
  "system": {
    "cpu_percent": 45.2,
    "memory_percent": 62.5,
    "disk_percent": 35.8,
    "uptime_seconds": 3600.5,
    "devices": [
      {
        "device_id": "stepper_01",
        "device_type": "stepper_motor",
        "status": "ready",
        "connected": true,
        "last_update": "2026-03-08T10:30:00.000Z",
        "error_count": 0,
        "uptime_seconds": 3500.0
      }
    ],
    "cpu_temperature": 65.0,
    "load_average": [1.5, 1.2, 1.0],
    "network_connections": 5,
    "process_count": 120,
    "thread_count": 500
  },
  "health_score": {
    "overall_score": 85.5,
    "system_score": 78.2,
    "device_score": 95.0,
    "performance_score": 82.0,
    "reliability_score": 88.0,
    "grade": "B",
    "details": {
      "cpu_score": 54.8,
      "memory_score": 37.5,
      "disk_score": 64.2,
      "device_connection_rate": 100.0,
      "device_error_rate": 0.0,
      "load_balance": 85.0,
      "uptime_hours": 1.0,
      "active_alerts_count": 0
    }
  },
  "active_alerts": 0,
  "recommendations": [
    "系统运行状态良好，继续保持"
  ]
}
```

**健康状态说明**:

| 状态 | 说明 |
|------|------|
| `healthy` | 系统资源正常，所有设备连接正常 |
| `degraded` | 系统资源使用率较高或部分设备断开 |
| `unhealthy` | 系统资源严重不足或多数设备故障 |

**健康等级说明**:

| 等级 | 分数范围 | 说明 |
|------|----------|------|
| A | 90-100 | 优秀，系统运行状态极佳 |
| B | 80-89 | 良好，系统运行正常 |
| C | 70-79 | 一般，需要关注部分指标 |
| D | 60-69 | 较差，需要优化 |
| F | 0-59 | 危险，需要立即处理 |

**示例**:

```bash
curl http://localhost:8000/api/health
```

---

### 获取健康评分详情

```http
GET /api/health/score
```

**功能说明**: 获取健康评分的详细计算过程和建议。

**响应模型**:

```json
{
  "health_score": {
    "overall_score": 85.5,
    "system_score": 78.2,
    "device_score": 95.0,
    "performance_score": 82.0,
    "reliability_score": 88.0,
    "grade": "B",
    "details": {
      "cpu_score": 54.8,
      "memory_score": 37.5,
      "disk_score": 64.2,
      "device_connection_rate": 100.0,
      "device_error_rate": 0.0,
      "load_balance": 85.0,
      "uptime_hours": 1.0,
      "active_alerts_count": 0
    }
  },
  "system_metrics": {
    "cpu_percent": 45.2,
    "memory_percent": 62.5,
    "disk_percent": 35.8,
    "uptime_seconds": 3600.5
  },
  "recommendations": [
    "系统运行状态良好，继续保持"
  ],
  "timestamp": "2026-03-08T10:30:00.000Z"
}
```

---

## Prometheus 指标

### 获取性能指标

```http
GET /api/metrics
```

**功能说明**: 返回Prometheus格式的监控指标，可直接被Prometheus抓取。

**响应格式**: `text/plain`

**输出示例**:

```
# HELP cpu_usage_percent CPU使用率百分比
# TYPE cpu_usage_percent gauge
cpu_usage_percent 45.2

# HELP memory_usage_percent 内存使用率百分比
# TYPE memory_usage_percent gauge
memory_usage_percent 62.5

# HELP disk_usage_percent 磁盘使用率百分比
# TYPE disk_usage_percent gauge
disk_usage_percent 35.8

# HELP system_uptime_seconds 系统运行时长（秒）
# TYPE system_uptime_seconds gauge
system_uptime_seconds 3600.5

# HELP health_score_overall 综合健康评分（0-100）
# TYPE health_score_overall gauge
health_score_overall 85.5

# HELP health_score_system 系统资源评分（0-100）
# TYPE health_score_system gauge
health_score_system 78.2

# HELP health_score_device 设备状态评分（0-100）
# TYPE health_score_device gauge
health_score_device 95.0

# HELP devices_total 设备总数
# TYPE devices_total gauge
devices_total 5

# HELP devices_connected 已连接设备数
# TYPE devices_connected gauge
devices_connected 4

# HELP device_connected 设备连接状态（1=已连接，0=已断开）
# TYPE device_connected gauge
device_connected{device_id="stepper_01",device_type="stepper_motor"} 1
device_connected{device_id="electromagnet_01",device_type="electromagnet"} 1

# HELP device_status 设备状态码
# TYPE device_status gauge
device_status{device_id="stepper_01",device_type="stepper_motor",status="ready"} 2

# HELP alerts_active 活跃告警数量
# TYPE alerts_active gauge
alerts_active 0

# HELP alerts_by_level 按级别统计告警数量
# TYPE alerts_by_level gauge
alerts_by_level{level="info"} 0
alerts_by_level{level="warning"} 0
alerts_by_level{level="critical"} 0
alerts_by_level{level="error"} 0

# HELP app_info 应用信息
# TYPE app_info gauge
app_info{version="0.3.0"} 1
```

**设备状态码映射**:

| 状态 | 状态码 |
|------|--------|
| idle | 0 |
| running | 1 |
| ready | 2 |
| busy | 3 |
| warning | 4 |
| error | 5 |
| fault | 6 |
| disconnected | 7 |
| disabled | 8 |
| unknown | 9 |

---

## 设备状态监控

### 获取设备状态汇总

```http
GET /api/devices/status
```

**功能说明**: 获取所有设备的连接状态汇总统计。

**响应模型**:

```json
{
  "total_devices": 5,
  "connected_devices": 4,
  "disconnected_devices": 1,
  "error_devices": 0,
  "avg_uptime_seconds": 3500.0,
  "total_errors": 0,
  "devices": [
    {
      "device_id": "stepper_01",
      "device_type": "stepper_motor",
      "status": "ready",
      "connected": true,
      "last_update": "2026-03-08T10:30:00.000Z",
      "error_count": 0,
      "uptime_seconds": 3500.0
    },
    {
      "device_id": "electromagnet_01",
      "device_type": "electromagnet",
      "status": "ready",
      "connected": true,
      "last_update": "2026-03-08T10:30:00.000Z",
      "error_count": 0,
      "uptime_seconds": 3400.0
    }
  ]
}
```

---

### 获取详细系统资源信息

```http
GET /api/resources
```

**功能说明**: 返回CPU、内存、磁盘、网络IO和当前进程的详细信息。

**响应模型**:

```json
{
  "cpu": {
    "count_logical": 16,
    "count_physical": 8,
    "percent_total": 45.2,
    "percent_per_cpu": [40.0, 50.0, 45.0, 46.0],
    "freq_current_mhz": 3200.0,
    "freq_min_mhz": 800.0,
    "freq_max_mhz": 4500.0
  },
  "memory": {
    "total_gb": 24.0,
    "available_gb": 9.0,
    "used_gb": 15.0,
    "percent": 62.5,
    "swap_total_gb": 32.0,
    "swap_used_gb": 2.0,
    "swap_percent": 6.25
  },
  "disk": {
    "total_gb": 1000.0,
    "used_gb": 358.0,
    "free_gb": 642.0,
    "percent": 35.8,
    "read_bytes": 1234567890,
    "write_bytes": 987654321
  },
  "network": {
    "bytes_sent": 12345678,
    "bytes_recv": 87654321,
    "packets_sent": 100000,
    "packets_recv": 150000,
    "errin": 0,
    "errout": 0,
    "dropin": 0,
    "dropout": 0
  },
  "process": {
    "pid": 12345,
    "name": "python",
    "cpu_percent": 5.2,
    "memory_mb": 256.5,
    "num_threads": 15,
    "num_handles": 250,
    "create_time": 1678262400.0
  },
  "system_load": {
    "1min": 1.5,
    "5min": 1.2,
    "15min": 1.0
  },
  "temperatures": {
    "cpu_core_0": 65.0,
    "cpu_core_1": 63.0
  }
}
```

---

## 健康评分算法

### 评分维度

健康评分采用多维度加权计算，总分0-100分：

| 维度 | 权重 | 说明 |
|------|------|------|
| 系统资源评分 | 40% | CPU、内存、磁盘使用率 |
| 设备状态评分 | 30% | 设备连接率、错误率 |
| 性能评分 | 15% | 系统负载均衡性 |
| 可靠性评分 | 15% | 运行时长、告警数量 |

### 计算公式

**系统资源评分**:
```
system_score = cpu_score * 0.4 + memory_score * 0.4 + disk_score * 0.2
cpu_score = max(0, 100 - cpu_percent)
memory_score = max(0, 100 - memory_percent)
disk_score = max(0, 100 - disk_percent)
```

**设备状态评分**:
```
connection_score = (connected_devices / total_devices) * 100
error_penalty = (error_devices / total_devices) * 50
device_score = max(0, connection_score - error_penalty)
```

**性能评分**:
```
load_balance = 1 - abs(cpu_percent - memory_percent) / 100
performance_score = (100 - (cpu_percent + memory_percent) / 2) * 0.7 + load_balance * 30
```

**可靠性评分**:
```
uptime_bonus = min(uptime_hours / 24 * 100, 100)
stability_penalty = min(active_alerts * 5, 50)
reliability_score = max(0, uptime_bonus - stability_penalty)
```

**综合评分**:
```
overall_score = system_score * 0.4 + device_score * 0.3 + performance_score * 0.15 + reliability_score * 0.15
```

---

## 错误响应

所有端点在发生错误时返回统一格式：

```json
{
  "detail": "错误描述信息"
}
```

**常见HTTP状态码**:

| 状态码 | 说明 |
|--------|------|
| 200 | 成功 |
| 400 | 请求参数错误 |
| 404 | 资源不存在 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用 |

---

## 使用示例

### JavaScript/TypeScript

```typescript
/**
 * 获取系统健康状态
 */
async function fetchHealthStatus(): Promise<HealthResponse> {
  const response = await fetch('/api/health')
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

/**
 * 检查系统是否健康
 */
async function checkSystemHealth(): Promise<boolean> {
  const health = await fetchHealthStatus()
  return health.status === 'healthy' && health.health_score.overall_score >= 80
}

/**
 * 获取健康评分并显示建议
 */
async function showHealthRecommendations(): Promise<void> {
  const health = await fetchHealthStatus()
  
  console.log(`系统健康评分: ${health.health_score.overall_score} (${health.health_score.grade})`)
  
  health.recommendations.forEach(rec => {
    console.log(`- ${rec}`)
  })
}
```

### Python

```python
import requests
from typing import Dict, Any

def get_health_status() -> Dict[str, Any]:
    """
    获取系统健康状态。
    
    Returns:
        dict: 健康状态响应
    """
    response = requests.get('http://localhost:8000/api/health')
    response.raise_for_status()
    return response.json()

def check_system_healthy() -> bool:
    """
    检查系统是否健康。
    
    Returns:
        bool: 系统是否健康
    """
    health = get_health_status()
    return (
        health['status'] == 'healthy' and 
        health['health_score']['overall_score'] >= 80
    )

def get_prometheus_metrics() -> str:
    """
    获取Prometheus格式的指标。
    
    Returns:
        str: Prometheus指标文本
    """
    response = requests.get('http://localhost:8000/api/metrics')
    response.raise_for_status()
    return response.text
```

---

## 最佳实践

### 1. 定期健康检查

建议每30秒进行一次健康检查，监控趋势变化：

```javascript
// 设置定时健康检查
const healthCheckInterval = setInterval(async () => {
  try {
    const health = await fetch('/api/health').then(r => r.json())
    
    // 根据健康状态采取行动
    if (health.status === 'unhealthy') {
      console.error('系统状态异常，请检查')
      notifyAdmin(health)
    } else if (health.status === 'degraded') {
      console.warn('系统状态降级，建议关注')
    }
  } catch (error) {
    console.error('健康检查失败:', error)
  }
}, 30000) // 每30秒
```

### 2. Prometheus集成

在Prometheus配置文件中添加抓取目标：

```yaml
scrape_configs:
  - job_name: 'cauc-sep'
    scrape_interval: 15s
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/api/metrics'
```

### 3. 健康评分监控

设置健康评分阈值告警：

```javascript
const HEALTH_THRESHOLD = 70

async function monitorHealthScore() {
  const score = await fetch('/api/health/score').then(r => r.json())
  
  if (score.health_score.overall_score < HEALTH_THRESHOLD) {
    // 触发告警
    triggerAlert({
      level: 'warning',
      message: `健康评分过低: ${score.health_score.overall_score}`,
      recommendations: score.recommendations
    })
  }
}
```

---

## 相关文档

- [告警系统API文档](./alerts-api.md)
- [性能分析API文档](./performance-api.md)
- [故障排除指南](../troubleshooting.md)
