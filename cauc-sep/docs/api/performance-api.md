# 性能分析 API 文档

**版本**: v1.0  
**更新日期**: 2026-03-08  
**基础路径**: `/api`

---

## 概述

性能分析API提供系统性能监控、瓶颈分析、性能报告生成等功能。该模块支持：

- 实时性能数据采集
- 性能瓶颈识别与分析
- 历史性能数据查询
- 性能报告生成与导出
- 性能趋势分析

---

## 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/performance` | GET | 获取当前性能概览 |
| `/api/performance/cpu` | GET | 获取CPU性能详情 |
| `/api/performance/memory` | GET | 获取内存性能详情 |
| `/api/performance/disk` | GET | 获取磁盘IO性能 |
| `/api/performance/network` | GET | 获取网络性能 |
| `/api/performance/bottlenecks` | GET | 识别性能瓶颈 |
| `/api/performance/history` | GET | 获取历史性能数据 |
| `/api/performance/report` | GET | 生成性能报告 |

---

## 性能概览

### 获取当前性能概览

```http
GET /api/performance
```

**功能说明**: 获取系统当前性能的综合概览，包括CPU、内存、磁盘、网络等关键指标。

**响应模型**:

```json
{
  "timestamp": "2026-03-08T10:30:00.000Z",
  "uptime_seconds": 86400,
  "overall_score": 82.5,
  "cpu": {
    "percent": 45.2,
    "load_average": [1.5, 1.2, 1.0],
    "core_count": 16,
    "temperature": 65.0
  },
  "memory": {
    "percent": 62.5,
    "used_gb": 15.0,
    "available_gb": 9.0,
    "swap_percent": 6.25
  },
  "disk": {
    "percent": 35.8,
    "read_mbps": 50.5,
    "write_mbps": 30.2
  },
  "network": {
    "in_mbps": 100.5,
    "out_mbps": 50.2,
    "connections": 25
  },
  "processes": {
    "total": 250,
    "running": 5,
    "sleeping": 240,
    "zombie": 0
  },
  "alerts": [
    {
      "type": "warning",
      "message": "内存使用率较高，建议关注"
    }
  ]
}
```

---

## CPU 性能分析

### 获取CPU性能详情

```http
GET /api/performance/cpu
```

**功能说明**: 获取CPU的详细性能数据，包括各核心使用率、频率、温度等。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `interval` | integer | 采样间隔（秒），默认1 |
| `samples` | integer | 采样次数，默认5 |

**响应模型**:

```json
{
  "timestamp": "2026-03-08T10:30:00.000Z",
  "summary": {
    "total_percent": 45.2,
    "user_percent": 25.0,
    "system_percent": 15.0,
    "idle_percent": 54.8,
    "iowait_percent": 3.0,
    "steal_percent": 2.2
  },
  "cores": [
    {
      "core": 0,
      "percent": 40.0,
      "frequency_mhz": 3200.0,
      "temperature": 62.0
    },
    {
      "core": 1,
      "percent": 50.0,
      "frequency_mhz": 3100.0,
      "temperature": 65.0
    }
  ],
  "load_average": {
    "1min": 1.5,
    "5min": 1.2,
    "15min": 1.0
  },
  "frequency": {
    "current_mhz": 3200.0,
    "min_mhz": 800.0,
    "max_mhz": 4500.0
  },
  "context_switches": 150000,
  "interrupts": 50000,
  "top_processes": [
    {
      "pid": 12345,
      "name": "python",
      "cpu_percent": 15.2,
      "memory_mb": 256.5
    }
  ]
}
```

---

## 内存性能分析

### 获取内存性能详情

```http
GET /api/performance/memory
```

**功能说明**: 获取内存的详细使用情况和性能数据。

**响应模型**:

```json
{
  "timestamp": "2026-03-08T10:30:00.000Z",
  "physical": {
    "total_gb": 24.0,
    "available_gb": 9.0,
    "used_gb": 15.0,
    "percent": 62.5,
    "cached_gb": 4.0,
    "buffers_gb": 1.0,
    "shared_gb": 0.5
  },
  "swap": {
    "total_gb": 32.0,
    "used_gb": 2.0,
    "free_gb": 30.0,
    "percent": 6.25,
    "sin_gb": 0.5,
    "sout_gb": 0.2
  },
  "virtual": {
    "total_gb": 48.0,
    "used_gb": 17.0,
    "free_gb": 31.0,
    "percent": 35.4
  },
  "trend": {
    "direction": "stable",
    "change_rate_percent_per_hour": 2.5
  },
  "top_consumers": [
    {
      "pid": 12345,
      "name": "python",
      "memory_mb": 512.0,
      "percent": 2.1
    }
  ]
}
```

---

## 磁盘IO性能

### 获取磁盘IO性能

```http
GET /api/performance/disk
```

**功能说明**: 获取磁盘IO性能和存储使用情况。

**响应模型**:

```json
{
  "timestamp": "2026-03-08T10:30:00.000Z",
  "storage": {
    "total_gb": 1000.0,
    "used_gb": 358.0,
    "free_gb": 642.0,
    "percent": 35.8
  },
  "io": {
    "read_bytes_per_sec": 52428800,
    "write_bytes_per_sec": 31457280,
    "read_mbps": 50.0,
    "write_mbps": 30.0,
    "read_count": 1500,
    "write_count": 800,
    "read_time_ms": 50,
    "write_time_ms": 30
  },
  "partitions": [
    {
      "device": "C:",
      "mountpoint": "C:\\",
      "fstype": "NTFS",
      "total_gb": 500.0,
      "used_gb": 200.0,
      "free_gb": 300.0,
      "percent": 40.0
    }
  ],
  "iops": {
    "read": 150,
    "write": 80,
    "total": 230
  },
  "latency": {
    "read_ms": 5.2,
    "write_ms": 3.5,
    "average_ms": 4.5
  }
}
```

---

## 网络性能

### 获取网络性能

```http
GET /api/performance/network
```

**功能说明**: 获取网络连接和流量性能数据。

**响应模型**:

```json
{
  "timestamp": "2026-03-08T10:30:00.000Z",
  "interfaces": [
    {
      "name": "Ethernet",
      "bytes_sent": 1234567890,
      "bytes_recv": 9876543210,
      "packets_sent": 1000000,
      "packets_recv": 2000000,
      "errin": 0,
      "errout": 0,
      "dropin": 0,
      "dropout": 0,
      "speed_mbps": 1000,
      "is_up": true
    }
  ],
  "connections": {
    "total": 150,
    "established": 25,
    "listen": 10,
    "time_wait": 50,
    "close_wait": 5
  },
  "bandwidth": {
    "in_mbps": 100.5,
    "out_mbps": 50.2,
    "in_kbps": 102500,
    "out_kbps": 51200
  },
  "latency": {
    "local_ms": 0.5,
    "internet_ms": 15.2
  },
  "dns": {
    "queries_per_sec": 10,
    "avg_response_ms": 5.0
  }
}
```

---

## 性能瓶颈分析

### 识别性能瓶颈

```http
GET /api/performance/bottlenecks
```

**功能说明**: 自动分析系统性能数据，识别潜在的性能瓶颈并提供优化建议。

**响应模型**:

```json
{
  "timestamp": "2026-03-08T10:30:00.000Z",
  "analysis_time_ms": 150,
  "bottlenecks": [
    {
      "id": "bottleneck_001",
      "type": "memory",
      "severity": "warning",
      "title": "内存使用率较高",
      "description": "内存使用率达到62.5%，接近告警阈值",
      "current_value": 62.5,
      "threshold": 80.0,
      "unit": "percent",
      "impact": "可能导致系统响应变慢，建议释放不必要的内存占用",
      "recommendations": [
        "检查内存占用较高的进程",
        "考虑增加系统内存",
        "优化应用程序内存使用"
      ],
      "related_metrics": [
        "memory_percent",
        "swap_percent"
      ]
    },
    {
      "id": "bottleneck_002",
      "type": "cpu",
      "severity": "info",
      "title": "CPU负载均衡良好",
      "description": "CPU各核心负载分布均匀",
      "current_value": 45.2,
      "threshold": 80.0,
      "unit": "percent",
      "impact": "系统CPU资源充足",
      "recommendations": []
    }
  ],
  "summary": {
    "total_issues": 1,
    "critical": 0,
    "warning": 1,
    "info": 0,
    "overall_health": "good"
  },
  "optimization_priority": [
    {
      "priority": 1,
      "area": "memory",
      "action": "监控内存使用趋势",
      "expected_improvement": "预防内存不足问题"
    }
  ]
}
```

**瓶颈类型说明**:

| 类型 | 说明 | 关键指标 |
|------|------|----------|
| `cpu` | CPU瓶颈 | 使用率、负载、温度 |
| `memory` | 内存瓶颈 | 使用率、交换分区 |
| `disk` | 磁盘瓶颈 | IO速率、延迟、空间 |
| `network` | 网络瓶颈 | 带宽、延迟、连接数 |
| `process` | 进程瓶颈 | 进程数、线程数 |

**严重程度说明**:

| 级别 | 说明 | 处理建议 |
|------|------|----------|
| `critical` | 严重瓶颈，需立即处理 | 立即采取行动 |
| `warning` | 潜在瓶颈，需关注 | 尽快优化 |
| `info` | 信息提示 | 可选优化 |

---

## 历史性能数据

### 获取历史性能数据

```http
GET /api/performance/history
```

**功能说明**: 获取历史性能数据，支持时间范围查询和聚合。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `metric` | string | 指标名称：cpu/memory/disk/network |
| `start_time` | string | 开始时间（ISO格式） |
| `end_time` | string | 结束时间（ISO格式） |
| `interval` | string | 聚合间隔：1m/5m/1h/1d |
| `limit` | integer | 返回数据点数量限制 |

**响应模型**:

```json
{
  "metric": "cpu",
  "start_time": "2026-03-07T00:00:00.000Z",
  "end_time": "2026-03-08T00:00:00.000Z",
  "interval": "1h",
  "data_points": [
    {
      "timestamp": "2026-03-07T00:00:00.000Z",
      "value": 35.2,
      "min": 20.0,
      "max": 50.0,
      "avg": 35.2
    },
    {
      "timestamp": "2026-03-07T01:00:00.000Z",
      "value": 30.5,
      "min": 15.0,
      "max": 45.0,
      "avg": 30.5
    }
  ],
  "statistics": {
    "min": 15.0,
    "max": 85.0,
    "avg": 42.5,
    "median": 40.0,
    "std_dev": 12.5,
    "percentile_95": 75.0,
    "percentile_99": 82.0
  },
  "trend": {
    "direction": "increasing",
    "slope": 0.5,
    "r_squared": 0.85
  }
}
```

---

## 性能报告

### 生成性能报告

```http
GET /api/performance/report
```

**功能说明**: 生成综合性能分析报告，包含系统状态、瓶颈分析和优化建议。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `format` | string | 输出格式：json/html/pdf，默认json |
| `period` | string | 报告周期：hour/day/week/month |
| `include_recommendations` | boolean | 是否包含优化建议 |

**响应模型**:

```json
{
  "report_id": "report_20260308_103000",
  "generated_at": "2026-03-08T10:30:00.000Z",
  "period": {
    "start": "2026-03-07T10:30:00.000Z",
    "end": "2026-03-08T10:30:00.000Z",
    "duration_hours": 24
  },
  "executive_summary": {
    "overall_health": "good",
    "health_score": 82.5,
    "grade": "B",
    "key_findings": [
      "系统整体运行状态良好",
      "内存使用率偏高，建议关注",
      "CPU和磁盘性能正常"
    ]
  },
  "system_overview": {
    "hostname": "SERVER-01",
    "os": "Windows 11",
    "uptime_hours": 24.0,
    "cpu_cores": 16,
    "memory_gb": 24.0,
    "disk_gb": 1000.0
  },
  "performance_analysis": {
    "cpu": {
      "avg_percent": 42.5,
      "max_percent": 85.0,
      "score": 85
    },
    "memory": {
      "avg_percent": 60.0,
      "max_percent": 75.0,
      "score": 75
    },
    "disk": {
      "avg_io_mbps": 40.0,
      "max_io_mbps": 100.0,
      "score": 90
    },
    "network": {
      "avg_bandwidth_mbps": 75.0,
      "max_bandwidth_mbps": 200.0,
      "score": 88
    }
  },
  "bottlenecks_found": 1,
  "recommendations": [
    {
      "priority": "high",
      "area": "memory",
      "title": "优化内存使用",
      "description": "内存使用率持续偏高，建议检查内存泄漏或增加物理内存",
      "steps": [
        "使用任务管理器检查内存占用高的进程",
        "考虑关闭不必要的后台程序",
        "如问题持续，建议增加系统内存"
      ],
      "expected_impact": "提升系统响应速度和稳定性"
    }
  ],
  "alerts_generated": 5,
  "sla_compliance": {
    "uptime_percent": 99.9,
    "response_time_avg_ms": 50,
    "error_rate_percent": 0.1
  }
}
```

---

## 使用示例

### JavaScript/TypeScript

```typescript
/**
 * 获取性能概览
 */
async function fetchPerformanceOverview(): Promise<PerformanceOverview> {
  const response = await fetch('/api/performance')
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

/**
 * 识别性能瓶颈
 */
async function analyzeBottlenecks(): Promise<BottleneckAnalysis> {
  const response = await fetch('/api/performance/bottlenecks')
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

/**
 * 获取CPU历史数据
 */
async function fetchCpuHistory(
  startTime: Date,
  endTime: Date,
  interval: string = '1h'
): Promise<PerformanceHistory> {
  const params = new URLSearchParams({
    metric: 'cpu',
    start_time: startTime.toISOString(),
    end_time: endTime.toISOString(),
    interval
  })
  
  const response = await fetch(`/api/performance/history?${params}`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

/**
 * 生成性能报告
 */
async function generatePerformanceReport(
  period: string = 'day',
  format: 'json' | 'html' | 'pdf' = 'json'
): Promise<PerformanceReport> {
  const params = new URLSearchParams({
    period,
    format,
    include_recommendations: 'true'
  })
  
  const response = await fetch(`/api/performance/report?${params}`)
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

/**
 * 性能监控类
 */
class PerformanceMonitor {
  private intervalId: number | null = null
  private onMetrics: (data: PerformanceOverview) => void
  private onBottleneck: (bottleneck: Bottleneck) => void
  
  constructor(
    onMetrics: (data: PerformanceOverview) => void,
    onBottleneck: (bottleneck: Bottleneck) => void
  ) {
    this.onMetrics = onMetrics
    this.onBottleneck = onBottleneck
  }
  
  /**
   * 启动监控
   */
  start(intervalMs: number = 5000): void {
    this.intervalId = window.setInterval(async () => {
      try {
        const data = await fetchPerformanceOverview()
        this.onMetrics(data)
        
        // 检查是否有告警
        if (data.alerts && data.alerts.length > 0) {
          const analysis = await analyzeBottlenecks()
          analysis.bottlenecks.forEach(b => this.onBottleneck(b))
        }
      } catch (error) {
        console.error('性能监控失败:', error)
      }
    }, intervalMs)
  }
  
  /**
   * 停止监控
   */
  stop(): void {
    if (this.intervalId) {
      clearInterval(this.intervalId)
      this.intervalId = null
    }
  }
}

// 使用示例
const monitor = new PerformanceMonitor(
  (data) => console.log('性能数据:', data),
  (bottleneck) => console.warn('发现瓶颈:', bottleneck.title)
)

monitor.start(10000) // 每10秒采集一次
```

### Python

```python
import requests
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

class PerformanceClient:
    """性能分析客户端。"""
    
    def __init__(self, base_url: str = 'http://localhost:8000'):
        self.base_url = base_url
    
    def get_overview(self) -> Dict[str, Any]:
        """
        获取性能概览。
        
        Returns:
            dict: 性能概览数据
        """
        response = requests.get(f'{self.base_url}/api/performance')
        response.raise_for_status()
        return response.json()
    
    def get_cpu_details(
        self,
        interval: int = 1,
        samples: int = 5
    ) -> Dict[str, Any]:
        """
        获取CPU性能详情。
        
        Args:
            interval: 采样间隔（秒）
            samples: 采样次数
        
        Returns:
            dict: CPU性能数据
        """
        params = {'interval': interval, 'samples': samples}
        response = requests.get(
            f'{self.base_url}/api/performance/cpu',
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def get_memory_details(self) -> Dict[str, Any]:
        """
        获取内存性能详情。
        
        Returns:
            dict: 内存性能数据
        """
        response = requests.get(f'{self.base_url}/api/performance/memory')
        response.raise_for_status()
        return response.json()
    
    def analyze_bottlenecks(self) -> Dict[str, Any]:
        """
        分析性能瓶颈。
        
        Returns:
            dict: 瓶颈分析结果
        """
        response = requests.get(
            f'{self.base_url}/api/performance/bottlenecks'
        )
        response.raise_for_status()
        return response.json()
    
    def get_history(
        self,
        metric: str,
        start_time: datetime,
        end_time: datetime,
        interval: str = '1h'
    ) -> Dict[str, Any]:
        """
        获取历史性能数据。
        
        Args:
            metric: 指标名称
            start_time: 开始时间
            end_time: 结束时间
            interval: 聚合间隔
        
        Returns:
            dict: 历史性能数据
        """
        params = {
            'metric': metric,
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'interval': interval
        }
        response = requests.get(
            f'{self.base_url}/api/performance/history',
            params=params
        )
        response.raise_for_status()
        return response.json()
    
    def generate_report(
        self,
        period: str = 'day',
        format: str = 'json'
    ) -> Dict[str, Any]:
        """
        生成性能报告。
        
        Args:
            period: 报告周期
            format: 输出格式
        
        Returns:
            dict: 性能报告
        """
        params = {
            'period': period,
            'format': format,
            'include_recommendations': 'true'
        }
        response = requests.get(
            f'{self.base_url}/api/performance/report',
            params=params
        )
        response.raise_for_status()
        return response.json()


# 使用示例
if __name__ == '__main__':
    client = PerformanceClient()
    
    # 获取性能概览
    overview = client.get_overview()
    print(f"系统健康评分: {overview['overall_score']}")
    
    # 分析瓶颈
    bottlenecks = client.analyze_bottlenecks()
    print(f"发现 {bottlenecks['summary']['total_issues']} 个问题")
    
    for b in bottlenecks['bottlenecks']:
        if b['severity'] in ['critical', 'warning']:
            print(f"  - {b['title']}: {b['description']}")
    
    # 获取历史数据
    history = client.get_history(
        metric='cpu',
        start_time=datetime.now() - timedelta(hours=24),
        end_time=datetime.now()
    )
    print(f"CPU平均使用率: {history['statistics']['avg']}%")
    
    # 生成报告
    report = client.generate_report(period='day')
    print(f"报告摘要: {report['executive_summary']['key_findings']}")
```

---

## 最佳实践

### 1. 定期性能采集

建议建立定期性能采集机制，用于趋势分析：

```python
import schedule
import time

def collect_performance_metrics():
    """定期采集性能指标。"""
    client = PerformanceClient()
    overview = client.get_overview()
    
    # 存储到数据库或时序数据库
    save_to_database(overview)
    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] 采集完成")

# 每5分钟采集一次
schedule.every(5).minutes.do(collect_performance_metrics)

while True:
    schedule.run_pending()
    time.sleep(1)
```

### 2. 性能阈值监控

设置性能阈值，自动触发告警：

```python
THRESHOLDS = {
    'cpu_percent': {'warning': 70, 'critical': 90},
    'memory_percent': {'warning': 80, 'critical': 95},
    'disk_percent': {'warning': 85, 'critical': 95}
}

def check_thresholds(overview):
    """检查性能阈值。"""
    alerts = []
    
    for metric, thresholds in THRESHOLDS.items():
        value = overview.get(metric.replace('_percent', ''), {}).get('percent', 0)
        
        if value >= thresholds['critical']:
            alerts.append({
                'metric': metric,
                'level': 'critical',
                'value': value,
                'threshold': thresholds['critical']
            })
        elif value >= thresholds['warning']:
            alerts.append({
                'metric': metric,
                'level': 'warning',
                'value': value,
                'threshold': thresholds['warning']
            })
    
    return alerts
```

### 3. 性能报告自动化

定期生成性能报告并发送通知：

```python
def generate_weekly_report():
    """生成周报。"""
    client = PerformanceClient()
    report = client.generate_report(period='week', format='html')
    
    # 发送邮件
    send_email(
        to='admin@example.com',
        subject='每周性能报告',
        body=report['html_content']
    )
```

---

## 相关文档

- [健康监控API文档](./health-api.md)
- [告警系统API文档](./alerts-api.md)
- [故障排除指南](../troubleshooting.md)
