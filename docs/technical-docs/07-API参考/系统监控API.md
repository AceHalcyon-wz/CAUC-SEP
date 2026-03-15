# 系统监控API

## 概述

系统监控API提供健康检查、性能监控、日志查询和告警管理功能，用于实时监控系统运行状态、诊断问题和优化性能。

**基础路径**: `/api`

**认证方式**: JWT Bearer Token（部分端点无需认证）

---

## 健康检查API

### 基础健康检查

快速检查系统是否正常运行。

**端点**: `GET /api/health`

**认证**: 不需要

**成功响应** (200 OK):

```json
{
    "status": "healthy",
    "timestamp": "2024-03-15T10:30:00Z",
    "version": "1.0.0",
    "uptime": 86400
}
```

**响应字段**:

| 字段 | 类型 | 说明 |
|------|------|------|
| status | string | 健康状态（healthy/degraded/unhealthy） |
| timestamp | string | 检查时间（ISO 8601） |
| version | string | 系统版本号 |
| uptime | integer | 系统运行时间（秒） |

---

### 详细健康检查

获取系统各组件的详细健康状态。

**端点**: `GET /api/health/detailed`

**认证**: 不需要

**成功响应** (200 OK):

```json
{
    "status": "healthy",
    "timestamp": "2024-03-15T10:30:00Z",
    "version": "1.0.0",
    "uptime": 86400,
    "components": {
        "database": {
            "status": "healthy",
            "latency_ms": 5,
            "connections": 10,
            "max_connections": 100,
            "details": {
                "type": "SQLite",
                "size_mb": 256,
                "tables": 15
            }
        },
        "cache": {
            "status": "healthy",
            "latency_ms": 1,
            "memory_used_mb": 128,
            "memory_max_mb": 512,
            "hit_rate": 0.95
        },
        "serial_ports": {
            "status": "healthy",
            "ports": [
                {
                    "name": "COM3",
                    "device": "motor_controller",
                    "status": "connected",
                    "baud_rate": 9600
                },
                {
                    "name": "COM4",
                    "device": "electromagnet",
                    "status": "connected",
                    "baud_rate": 9600
                },
                {
                    "name": "COM5",
                    "device": "temperature_controller",
                    "status": "disconnected",
                    "baud_rate": 9600
                }
            ]
        },
        "devices": {
            "status": "degraded",
            "devices": [
                {
                    "name": "motor",
                    "status": "online",
                    "last_communication": "2024-03-15T10:29:55Z"
                },
                {
                    "name": "electromagnet",
                    "status": "online",
                    "last_communication": "2024-03-15T10:29:58Z"
                },
                {
                    "name": "temperature",
                    "status": "offline",
                    "last_communication": "2024-03-15T09:00:00Z"
                }
            ]
        },
        "storage": {
            "status": "healthy",
            "disk_used_gb": 50,
            "disk_total_gb": 500,
            "disk_usage_percent": 10,
            "data_directory": "D:\\cauc-sep\\data"
        }
    }
}
```

**组件状态说明**:

| 状态 | 说明 |
|------|------|
| healthy | 组件运行正常 |
| degraded | 组件部分功能受限 |
| unhealthy | 组件不可用 |

---

### 数据库健康检查

检查数据库连接和状态。

**端点**: `GET /api/health/database`

**认证**: 需要

**成功响应** (200 OK):

```json
{
    "status": "healthy",
    "timestamp": "2024-03-15T10:30:00Z",
    "details": {
        "type": "SQLite",
        "version": "3.40.0",
        "size_mb": 256,
        "tables": 15,
        "indexes": 25,
        "connections": {
            "active": 5,
            "idle": 5,
            "max": 20
        },
        "integrity_check": "ok",
        "last_vacuum": "2024-03-01T00:00:00Z",
        "last_analyze": "2024-03-10T00:00:00Z"
    }
}
```

---

### 设备连接检查

检查所有实验设备的连接状态。

**端点**: `GET /api/health/devices`

**认证**: 需要

**成功响应** (200 OK):

```json
{
    "status": "degraded",
    "timestamp": "2024-03-15T10:30:00Z",
    "devices": [
        {
            "id": "motor",
            "name": "步进电机",
            "status": "online",
            "port": "COM3",
            "baud_rate": 9600,
            "last_communication": "2024-03-15T10:29:55Z",
            "communication_delay_ms": 15,
            "error_count": 0,
            "details": {
                "position": 5000,
                "speed": 0,
                "is_moving": false
            }
        },
        {
            "id": "electromagnet",
            "name": "电磁铁",
            "status": "online",
            "port": "COM4",
            "baud_rate": 9600,
            "last_communication": "2024-03-15T10:29:58Z",
            "communication_delay_ms": 20,
            "error_count": 2,
            "details": {
                "current": 1.5,
                "field": 0.8,
                "mode": "constant_current"
            }
        },
        {
            "id": "temperature",
            "name": "温度控制器",
            "status": "offline",
            "port": "COM5",
            "baud_rate": 9600,
            "last_communication": "2024-03-15T09:00:00Z",
            "error_count": 50,
            "error_message": "通信超时"
        }
    ],
    "summary": {
        "total": 5,
        "online": 4,
        "offline": 1,
        "error": 0
    }
}
```

---

### 就绪检查

检查系统是否准备好接收请求（用于Kubernetes就绪探针）。

**端点**: `GET /api/health/ready`

**认证**: 不需要

**成功响应** (200 OK):

```json
{
    "ready": true,
    "timestamp": "2024-03-15T10:30:00Z",
    "checks": {
        "database": true,
        "cache": true,
        "config": true
    }
}
```

**未就绪响应** (503 Service Unavailable):

```json
{
    "ready": false,
    "timestamp": "2024-03-15T10:30:00Z",
    "checks": {
        "database": false,
        "cache": true,
        "config": true
    },
    "reason": "数据库连接失败"
}
```

---

### 存活检查

检查系统进程是否存活（用于Kubernetes存活探针）。

**端点**: `GET /api/health/live`

**认证**: 不需要

**成功响应** (200 OK):

```json
{
    "alive": true,
    "timestamp": "2024-03-15T10:30:00Z"
}
```

---

## 性能监控API

### 获取系统性能指标

获取系统整体性能指标。

**端点**: `GET /api/performance/metrics`

**认证**: 需要（需要 `system:monitor` 权限）

**成功响应** (200 OK):

```json
{
    "timestamp": "2024-03-15T10:30:00Z",
    "cpu": {
        "usage_percent": 25.5,
        "cores": 8,
        "load_average": [1.5, 1.2, 1.0],
        "process_usage_percent": 5.2
    },
    "memory": {
        "total_gb": 24.0,
        "used_gb": 8.5,
        "available_gb": 15.5,
        "usage_percent": 35.4,
        "process_used_mb": 512,
        "process_available_mb": 2048
    },
    "disk": {
        "total_gb": 500.0,
        "used_gb": 50.0,
        "free_gb": 450.0,
        "usage_percent": 10.0,
        "read_speed_mbps": 150.0,
        "write_speed_mbps": 100.0
    },
    "network": {
        "bytes_sent_mb": 1024,
        "bytes_recv_mb": 2048,
        "packets_sent": 1000000,
        "packets_recv": 2000000,
        "errors_in": 0,
        "errors_out": 0
    },
    "process": {
        "pid": 12345,
        "threads": 10,
        "file_descriptors": 50,
        "open_connections": 15
    }
}
```

---

### 获取API性能统计

获取API接口的性能统计数据。

**端点**: `GET /api/performance/api-stats`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| period | string | 否 | 1h | 统计周期（1h/6h/24h/7d） |
| endpoint | string | 否 | - | 筛选特定端点 |

**请求示例**:

```
GET /api/performance/api-stats?period=24h
```

**成功响应** (200 OK):

```json
{
    "period": "24h",
    "timestamp": "2024-03-15T10:30:00Z",
    "summary": {
        "total_requests": 15000,
        "successful_requests": 14850,
        "failed_requests": 150,
        "average_latency_ms": 45,
        "p50_latency_ms": 30,
        "p95_latency_ms": 100,
        "p99_latency_ms": 250,
        "requests_per_second": 0.17
    },
    "endpoints": [
        {
            "path": "/api/motor/status",
            "method": "GET",
            "request_count": 5000,
            "success_rate": 0.99,
            "average_latency_ms": 15,
            "p95_latency_ms": 30,
            "p99_latency_ms": 50
        },
        {
            "path": "/api/analysis/fit",
            "method": "POST",
            "request_count": 500,
            "success_rate": 0.98,
            "average_latency_ms": 250,
            "p95_latency_ms": 500,
            "p99_latency_ms": 1000
        },
        {
            "path": "/api/health",
            "method": "GET",
            "request_count": 8640,
            "success_rate": 1.0,
            "average_latency_ms": 5,
            "p95_latency_ms": 10,
            "p99_latency_ms": 20
        }
    ],
    "errors": [
        {
            "status_code": 500,
            "count": 100,
            "paths": [
                {
                    "path": "/api/analysis/fit",
                    "count": 80
                },
                {
                    "path": "/api/electromagnet/set-current",
                    "count": 20
                }
            ]
        },
        {
            "status_code": 400,
            "count": 50,
            "paths": [
                {
                    "path": "/api/motor/move",
                    "count": 30
                },
                {
                    "path": "/api/temperature/set-pid",
                    "count": 20
                }
            ]
        }
    ]
}
```

---

### 获取设备通信性能

获取设备通信的性能统计。

**端点**: `GET /api/performance/device-communication`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| device_id | string | 否 | - | 筛选特定设备 |
| period | string | 否 | 1h | 统计周期 |

**成功响应** (200 OK):

```json
{
    "period": "1h",
    "timestamp": "2024-03-15T10:30:00Z",
    "devices": [
        {
            "device_id": "motor",
            "device_name": "步进电机",
            "port": "COM3",
            "statistics": {
                "total_commands": 1500,
                "successful_commands": 1495,
                "failed_commands": 5,
                "success_rate": 0.997,
                "average_latency_ms": 15,
                "max_latency_ms": 50,
                "timeout_count": 2,
                "retry_count": 3,
                "bytes_sent": 15000,
                "bytes_received": 30000
            },
            "errors": [
                {
                    "type": "timeout",
                    "count": 2,
                    "last_occurrence": "2024-03-15T10:00:00Z"
                },
                {
                    "type": "crc_error",
                    "count": 3,
                    "last_occurrence": "2024-03-15T09:30:00Z"
                }
            ]
        }
    ]
}
```

---

### 获取数据库性能

获取数据库性能统计。

**端点**: `GET /api/performance/database`

**认证**: 需要（需要 `system:monitor` 权限）

**成功响应** (200 OK):

```json
{
    "timestamp": "2024-03-15T10:30:00Z",
    "statistics": {
        "queries_per_second": 10.5,
        "average_query_time_ms": 2.5,
        "slow_queries": [
            {
                "query": "SELECT * FROM experiment_data WHERE experiment_id = ?",
                "average_time_ms": 150,
                "count": 50,
                "suggestion": "考虑添加索引"
            }
        ],
        "connections": {
            "active": 5,
            "idle": 5,
            "max": 20,
            "wait_count": 0
        },
        "cache": {
            "hit_rate": 0.95,
            "hits": 9500,
            "misses": 500
        },
        "size": {
            "database_mb": 256,
            "log_mb": 10,
            "temp_mb": 5
        }
    }
}
```

---

### 性能分析

对指定操作进行性能分析。

**端点**: `POST /api/performance/profile`

**认证**: 需要（需要 `system:monitor` 权限）

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| operation | string | 是 | 操作类型（device_command/data_analysis/file_export） |
| duration | integer | 否 | 分析时长（秒，默认10，最大60） |
| sample_rate | integer | 否 | 采样率（Hz，默认100） |

**请求示例**:

```json
{
    "operation": "device_command",
    "duration": 30,
    "sample_rate": 100
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "性能分析完成",
    "data": {
        "profile_id": "profile_20240315_103000",
        "operation": "device_command",
        "duration_seconds": 30,
        "sample_count": 3000,
        "summary": {
            "total_cpu_time_ms": 15000,
            "total_memory_peak_mb": 100,
            "average_latency_ms": 15,
            "max_latency_ms": 50
        },
        "breakdown": {
            "serial_communication": {
                "cpu_percent": 45,
                "memory_mb": 20,
                "calls": 300
            },
            "data_processing": {
                "cpu_percent": 30,
                "memory_mb": 30,
                "calls": 300
            },
            "error_handling": {
                "cpu_percent": 5,
                "memory_mb": 5,
                "calls": 10
            }
        },
        "recommendations": [
            {
                "type": "optimization",
                "message": "串口通信可以批量处理以减少延迟",
                "potential_improvement": "20%"
            }
        ]
    }
}
```

---

### 内存追踪

追踪内存使用情况。

**端点**: `GET /api/performance/memory-trace`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| detail | boolean | 否 | false | 是否返回详细内存分配信息 |

**成功响应** (200 OK):

```json
{
    "timestamp": "2024-03-15T10:30:00Z",
    "process": {
        "pid": 12345,
        "memory_mb": 512,
        "memory_percent": 2.1,
        "peak_memory_mb": 600,
        "memory_growth_mb_per_hour": 10
    },
    "breakdown": {
        "code_mb": 50,
        "data_mb": 200,
        "stack_mb": 10,
        "heap_mb": 252
    },
    "objects": {
        "total_count": 100000,
        "by_type": [
            {
                "type": "dict",
                "count": 50000,
                "size_mb": 100
            },
            {
                "type": "list",
                "count": 30000,
                "size_mb": 50
            },
            {
                "type": "str",
                "count": 15000,
                "size_mb": 30
            }
        ]
    },
    "gc": {
        "collections": [100, 50, 10],
        "collected": [5000, 2000, 500],
        "uncollectable": 0
    }
}
```

---

## 日志查询API

### 查询审计日志

查询系统审计日志。

**端点**: `GET /api/logs/audit`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 50 | 每页数量（最大200） |
| start_time | string | 否 | - | 开始时间（ISO 8601） |
| end_time | string | 否 | - | 结束时间（ISO 8601） |
| user_id | integer | 否 | - | 用户ID筛选 |
| action | string | 否 | - | 操作类型筛选 |
| resource_type | string | 否 | - | 资源类型筛选 |
| status | string | 否 | - | 状态筛选（success/failure） |
| keyword | string | 否 | - | 关键词搜索 |

**请求示例**:

```
GET /api/logs/audit?page=1&page_size=50&action=device_control&status=failure
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "logs": [
            {
                "id": 1001,
                "timestamp": "2024-03-15T10:30:00Z",
                "user": {
                    "id": 1,
                    "username": "admin"
                },
                "action": "device_control",
                "resource_type": "motor",
                "resource_id": "motor_1",
                "operation": "move",
                "details": {
                    "target_position": 1000,
                    "actual_position": 1000,
                    "duration_ms": 150
                },
                "status": "success",
                "ip_address": "192.168.1.100",
                "user_agent": "Mozilla/5.0..."
            },
            {
                "id": 1000,
                "timestamp": "2024-03-15T10:25:00Z",
                "user": {
                    "id": 2,
                    "username": "researcher01"
                },
                "action": "data_export",
                "resource_type": "experiment",
                "resource_id": "exp_123",
                "operation": "export_csv",
                "details": {
                    "file_size_mb": 5.2,
                    "record_count": 10000
                },
                "status": "success",
                "ip_address": "192.168.1.101",
                "user_agent": "Mozilla/5.0..."
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 50,
            "total": 1500,
            "total_pages": 30
        }
    }
}
```

---

### 获取日志统计

获取日志统计数据。

**端点**: `GET /api/logs/statistics`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| period | string | 否 | 24h | 统计周期（1h/6h/24h/7d/30d） |
| group_by | string | 否 | action | 分组方式（action/user/resource_type） |

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "period": "24h",
        "timestamp": "2024-03-15T10:30:00Z",
        "summary": {
            "total_logs": 5000,
            "success_count": 4850,
            "failure_count": 150,
            "unique_users": 10,
            "unique_ips": 5
        },
        "by_action": [
            {
                "action": "device_control",
                "count": 2000,
                "success_rate": 0.98,
                "avg_duration_ms": 50
            },
            {
                "action": "data_read",
                "count": 1500,
                "success_rate": 1.0,
                "avg_duration_ms": 20
            },
            {
                "action": "data_export",
                "count": 500,
                "success_rate": 0.99,
                "avg_duration_ms": 500
            },
            {
                "action": "user_login",
                "count": 100,
                "success_rate": 0.95,
                "avg_duration_ms": 100
            }
        ],
        "by_user": [
            {
                "user_id": 1,
                "username": "admin",
                "count": 1000,
                "success_rate": 0.99
            },
            {
                "user_id": 2,
                "username": "researcher01",
                "count": 2000,
                "success_rate": 0.97
            }
        ],
        "timeline": [
            {
                "hour": "2024-03-15T00:00:00Z",
                "count": 100,
                "success_rate": 0.99
            },
            {
                "hour": "2024-03-15T01:00:00Z",
                "count": 50,
                "success_rate": 1.0
            }
        ]
    }
}
```

---

### 查询系统日志

查询系统运行日志。

**端点**: `GET /api/logs/system`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 100 | 每页数量 |
| level | string | 否 | - | 日志级别（DEBUG/INFO/WARNING/ERROR/CRITICAL） |
| module | string | 否 | - | 模块名称 |
| start_time | string | 否 | - | 开始时间 |
| end_time | string | 否 | - | 结束时间 |
| keyword | string | 否 | - | 关键词搜索 |

**请求示例**:

```
GET /api/logs/system?level=ERROR&module=device&start_time=2024-03-15T00:00:00Z
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "logs": [
            {
                "id": 5001,
                "timestamp": "2024-03-15T10:30:00.123Z",
                "level": "ERROR",
                "module": "device.motor",
                "function": "move_to_position",
                "message": "Motor communication timeout after 3 retries",
                "details": {
                    "device_id": "motor_1",
                    "target_position": 1000,
                    "retry_count": 3,
                    "last_error": "TimeoutError"
                },
                "traceback": "Traceback (most recent call last):\n  File ..."
            },
            {
                "id": 5000,
                "timestamp": "2024-03-15T10:25:00.456Z",
                "level": "WARNING",
                "module": "device.temperature",
                "function": "read_temperature",
                "message": "Temperature reading fluctuation detected",
                "details": {
                    "device_id": "temp_1",
                    "current_value": 25.5,
                    "expected_range": [24.0, 26.0],
                    "fluctuation": 0.8
                }
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 100,
            "total": 500,
            "total_pages": 5
        }
    }
}
```

---

### 导出日志

导出日志数据。

**端点**: `POST /api/logs/export`

**认证**: 需要（需要 `system:monitor` 权限）

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| log_type | string | 是 | 日志类型（audit/system） |
| format | string | 是 | 导出格式（csv/json/xlsx） |
| start_time | string | 否 | 开始时间 |
| end_time | string | 否 | 结束时间 |
| filters | object | 否 | 筛选条件 |

**请求示例**:

```json
{
    "log_type": "audit",
    "format": "xlsx",
    "start_time": "2024-03-01T00:00:00Z",
    "end_time": "2024-03-15T23:59:59Z",
    "filters": {
        "action": "device_control",
        "status": "failure"
    }
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "日志导出成功",
    "data": {
        "file_path": "/exports/audit_20240301_20240315.xlsx",
        "file_size_mb": 2.5,
        "record_count": 500,
        "download_url": "/api/logs/download/audit_20240301_20240315.xlsx"
    }
}
```

---

### 清理日志

清理过期日志。

**端点**: `POST /api/logs/cleanup`

**认证**: 需要（需要 `system:config` 权限）

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| log_type | string | 是 | 日志类型（audit/system/all） |
| before_date | string | 是 | 清理此日期之前的日志 |
| dry_run | boolean | 否 | 是否仅预览（默认true） |

**请求示例**:

```json
{
    "log_type": "system",
    "before_date": "2024-01-01",
    "dry_run": false
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "日志清理完成",
    "data": {
        "deleted_count": 10000,
        "freed_space_mb": 50,
        "remaining_count": 50000
    }
}
```

---

## 告警管理API

### 获取告警列表

获取系统告警列表。

**端点**: `GET /api/alerts`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| status | string | 否 | - | 状态筛选（active/acknowledged/resolved） |
| severity | string | 否 | - | 严重程度（info/warning/critical） |
| category | string | 否 | - | 分类（device/system/performance） |
| page | integer | 否 | 1 | 页码 |
| page_size | integer | 否 | 50 | 每页数量 |

**请求示例**:

```
GET /api/alerts?status=active&severity=critical
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "alerts": [
            {
                "id": "alert_001",
                "timestamp": "2024-03-15T10:30:00Z",
                "severity": "critical",
                "category": "device",
                "title": "温度控制器通信中断",
                "message": "温度控制器（COM5）已失去连接超过30分钟",
                "source": {
                    "type": "device",
                    "id": "temperature_controller",
                    "name": "温度控制器"
                },
                "status": "active",
                "acknowledged_by": null,
                "acknowledged_at": null,
                "resolved_at": null,
                "metadata": {
                    "device_id": "temperature",
                    "port": "COM5",
                    "last_communication": "2024-03-15T09:00:00Z",
                    "error_count": 50
                },
                "actions": [
                    {
                        "type": "retry_connection",
                        "label": "重试连接",
                        "endpoint": "/api/temperature/reconnect"
                    }
                ]
            },
            {
                "id": "alert_002",
                "timestamp": "2024-03-15T09:00:00Z",
                "severity": "warning",
                "category": "performance",
                "title": "磁盘空间不足",
                "message": "数据磁盘使用率已达85%",
                "source": {
                    "type": "system",
                    "id": "storage",
                    "name": "存储系统"
                },
                "status": "acknowledged",
                "acknowledged_by": {
                    "id": 1,
                    "username": "admin"
                },
                "acknowledged_at": "2024-03-15T09:30:00Z",
                "resolved_at": null,
                "metadata": {
                    "disk_usage_percent": 85,
                    "disk_free_gb": 75,
                    "disk_total_gb": 500
                }
            }
        ],
        "pagination": {
            "page": 1,
            "page_size": 50,
            "total": 5,
            "total_pages": 1
        },
        "summary": {
            "total_active": 3,
            "total_acknowledged": 2,
            "total_resolved": 0,
            "by_severity": {
                "critical": 1,
                "warning": 3,
                "info": 1
            }
        }
    }
}
```

---

### 获取告警详情

获取指定告警的详细信息。

**端点**: `GET /api/alerts/{alert_id}`

**认证**: 需要（需要 `system:monitor` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alert_id | string | 告警ID |

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "id": "alert_001",
        "timestamp": "2024-03-15T10:30:00Z",
        "severity": "critical",
        "category": "device",
        "title": "温度控制器通信中断",
        "message": "温度控制器（COM5）已失去连接超过30分钟",
        "source": {
            "type": "device",
            "id": "temperature_controller",
            "name": "温度控制器"
        },
        "status": "active",
        "acknowledged_by": null,
        "acknowledged_at": null,
        "resolved_at": null,
        "metadata": {
            "device_id": "temperature",
            "port": "COM5",
            "last_communication": "2024-03-15T09:00:00Z",
            "error_count": 50
        },
        "history": [
            {
                "timestamp": "2024-03-15T10:30:00Z",
                "event": "created",
                "details": "告警首次触发"
            },
            {
                "timestamp": "2024-03-15T10:35:00Z",
                "event": "escalated",
                "details": "告警升级：30分钟内未确认"
            }
        ],
        "related_alerts": [
            {
                "id": "alert_003",
                "title": "温度控制实验暂停",
                "severity": "warning"
            }
        ]
    }
}
```

---

### 确认告警

确认告警，表示已知晓。

**端点**: `POST /api/alerts/{alert_id}/acknowledge`

**认证**: 需要（需要 `system:monitor` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alert_id | string | 告警ID |

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| note | string | 否 | 确认备注 |

**请求示例**:

```json
{
    "note": "已联系设备供应商，等待技术支持"
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "告警已确认",
    "data": {
        "id": "alert_001",
        "status": "acknowledged",
        "acknowledged_by": {
            "id": 1,
            "username": "admin"
        },
        "acknowledged_at": "2024-03-15T11:00:00Z"
    }
}
```

---

### 解决告警

标记告警为已解决。

**端点**: `POST /api/alerts/{alert_id}/resolve`

**认证**: 需要（需要 `system:monitor` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| alert_id | string | 告警ID |

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| resolution | string | 是 | 解决方案描述 |

**请求示例**:

```json
{
    "resolution": "更换了RS485通信线，设备已恢复正常通信"
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "告警已解决",
    "data": {
        "id": "alert_001",
        "status": "resolved",
        "resolved_at": "2024-03-15T12:00:00Z",
        "resolution": "更换了RS485通信线，设备已恢复正常通信",
        "duration_minutes": 90
    }
}
```

---

### 获取告警规则

获取告警规则配置。

**端点**: `GET /api/alerts/rules`

**认证**: 需要（需要 `system:config` 权限）

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "rules": [
            {
                "id": "rule_001",
                "name": "设备离线告警",
                "description": "当设备失去连接超过指定时间时触发",
                "enabled": true,
                "category": "device",
                "severity": "critical",
                "conditions": {
                    "metric": "device_status",
                    "operator": "equals",
                    "value": "offline",
                    "duration_minutes": 5
                },
                "actions": [
                    {
                        "type": "notification",
                        "config": {
                            "channels": ["email", "browser"],
                            "recipients": ["admin", "operator"]
                        }
                    },
                    {
                        "type": "webhook",
                        "config": {
                            "url": "https://hooks.example.com/alert",
                            "method": "POST"
                        }
                    }
                ],
                "cooldown_minutes": 30
            },
            {
                "id": "rule_002",
                "name": "磁盘空间告警",
                "description": "当磁盘使用率超过阈值时触发",
                "enabled": true,
                "category": "system",
                "severity": "warning",
                "conditions": {
                    "metric": "disk_usage_percent",
                    "operator": "greater_than",
                    "value": 80
                },
                "actions": [
                    {
                        "type": "notification",
                        "config": {
                            "channels": ["email"],
                            "recipients": ["admin"]
                        }
                    }
                ],
                "cooldown_minutes": 60
            },
            {
                "id": "rule_003",
                "name": "API响应时间告警",
                "description": "当API平均响应时间超过阈值时触发",
                "enabled": true,
                "category": "performance",
                "severity": "warning",
                "conditions": {
                    "metric": "api_latency_p95_ms",
                    "operator": "greater_than",
                    "value": 500,
                    "evaluation_period_minutes": 5
                },
                "actions": [
                    {
                        "type": "notification",
                        "config": {
                            "channels": ["browser"],
                            "recipients": ["admin"]
                        }
                    }
                ],
                "cooldown_minutes": 15
            }
        ]
    }
}
```

---

### 创建告警规则

创建新的告警规则。

**端点**: `POST /api/alerts/rules`

**认证**: 需要（需要 `system:config` 权限）

**请求体**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 规则名称 |
| description | string | 否 | 规则描述 |
| category | string | 是 | 分类（device/system/performance） |
| severity | string | 是 | 严重程度（info/warning/critical） |
| conditions | object | 是 | 触发条件 |
| actions | array | 是 | 触发动作 |
| cooldown_minutes | integer | 否 | 冷却时间（默认30） |
| enabled | boolean | 否 | 是否启用（默认true） |

**请求示例**:

```json
{
    "name": "温度异常告警",
    "description": "当温度超出安全范围时触发",
    "category": "device",
    "severity": "critical",
    "conditions": {
        "metric": "temperature_value",
        "operator": "outside_range",
        "min_value": 10,
        "max_value": 100,
        "duration_minutes": 2
    },
    "actions": [
        {
            "type": "notification",
            "config": {
                "channels": ["email", "browser"],
                "recipients": ["admin", "operator"]
            }
        },
        {
            "type": "device_action",
            "config": {
                "device": "heater",
                "action": "emergency_stop"
            }
        }
    ],
    "cooldown_minutes": 10,
    "enabled": true
}
```

**成功响应** (201 Created):

```json
{
    "success": true,
    "message": "告警规则创建成功",
    "data": {
        "id": "rule_004",
        "name": "温度异常告警",
        "enabled": true,
        "created_at": "2024-03-15T10:30:00Z"
    }
}
```

---

### 更新告警规则

更新现有告警规则。

**端点**: `PUT /api/alerts/rules/{rule_id}`

**认证**: 需要（需要 `system:config` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| rule_id | string | 规则ID |

**请求示例**:

```json
{
    "severity": "warning",
    "conditions": {
        "metric": "temperature_value",
        "operator": "outside_range",
        "min_value": 5,
        "max_value": 120,
        "duration_minutes": 5
    },
    "enabled": true
}
```

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "告警规则更新成功",
    "data": {
        "id": "rule_004",
        "name": "温度异常告警",
        "severity": "warning",
        "enabled": true,
        "updated_at": "2024-03-15T11:00:00Z"
    }
}
```

---

### 删除告警规则

删除告警规则。

**端点**: `DELETE /api/alerts/rules/{rule_id}`

**认证**: 需要（需要 `system:config` 权限）

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| rule_id | string | 规则ID |

**成功响应** (200 OK):

```json
{
    "success": true,
    "message": "告警规则删除成功"
}
```

---

### 获取告警统计

获取告警统计数据。

**端点**: `GET /api/alerts/statistics`

**认证**: 需要（需要 `system:monitor` 权限）

**查询参数**:

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| period | string | 否 | 7d | 统计周期（24h/7d/30d） |

**成功响应** (200 OK):

```json
{
    "success": true,
    "data": {
        "period": "7d",
        "timestamp": "2024-03-15T10:30:00Z",
        "summary": {
            "total_alerts": 50,
            "active": 3,
            "acknowledged": 5,
            "resolved": 42,
            "average_resolution_time_minutes": 45
        },
        "by_severity": {
            "critical": 10,
            "warning": 30,
            "info": 10
        },
        "by_category": {
            "device": 25,
            "system": 15,
            "performance": 10
        },
        "by_status": {
            "active": 3,
            "acknowledged": 5,
            "resolved": 42
        },
        "timeline": [
            {
                "date": "2024-03-09",
                "total": 5,
                "critical": 1,
                "resolved": 5
            },
            {
                "date": "2024-03-10",
                "total": 8,
                "critical": 2,
                "resolved": 7
            }
        ],
        "top_sources": [
            {
                "source": "temperature_controller",
                "count": 15,
                "name": "温度控制器"
            },
            {
                "source": "storage",
                "count": 10,
                "name": "存储系统"
            }
        ]
    }
}
```

---

## Prometheus指标

### 获取Prometheus格式指标

获取兼容Prometheus格式的监控指标。

**端点**: `GET /api/metrics`

**认证**: 不需要

**响应格式**: text/plain

**响应示例**:

```
# HELP cauc_sep_http_requests_total Total HTTP requests
# TYPE cauc_sep_http_requests_total counter
cauc_sep_http_requests_total{method="GET",endpoint="/api/health",status="200"} 8640
cauc_sep_http_requests_total{method="POST",endpoint="/api/motor/move",status="200"} 1500
cauc_sep_http_requests_total{method="POST",endpoint="/api/motor/move",status="400"} 50

# HELP cauc_sep_http_request_duration_seconds HTTP request duration
# TYPE cauc_sep_http_request_duration_seconds histogram
cauc_sep_http_request_duration_seconds_bucket{method="GET",endpoint="/api/health",le="0.01"} 8000
cauc_sep_http_request_duration_seconds_bucket{method="GET",endpoint="/api/health",le="0.05"} 8500
cauc_sep_http_request_duration_seconds_bucket{method="GET",endpoint="/api/health",le="0.1"} 8600
cauc_sep_http_request_duration_seconds_bucket{method="GET",endpoint="/api/health",le="+Inf"} 8640
cauc_sep_http_request_duration_seconds_sum{method="GET",endpoint="/api/health"} 43.2
cauc_sep_http_request_duration_seconds_count{method="GET",endpoint="/api/health"} 8640

# HELP cauc_sep_device_status Device connection status
# TYPE cauc_sep_device_status gauge
cauc_sep_device_status{device="motor"} 1
cauc_sep_device_status{device="electromagnet"} 1
cauc_sep_device_status{device="temperature"} 0
cauc_sep_device_status{device="piezo"} 1
cauc_sep_device_status{device="ammeter"} 1

# HELP cauc_sep_device_communication_latency_ms Device communication latency
# TYPE cauc_sep_device_communication_latency_ms gauge
cauc_sep_device_communication_latency_ms{device="motor"} 15
cauc_sep_device_communication_latency_ms{device="electromagnet"} 20
cauc_sep_device_communication_latency_ms{device="piezo"} 10
cauc_sep_device_communication_latency_ms{device="ammeter"} 5

# HELP cauc_sep_active_experiments Number of active experiments
# TYPE cauc_sep_active_experiments gauge
cauc_sep_active_experiments 2

# HELP cauc_sep_database_connections Database connection pool status
# TYPE cauc_sep_database_connections gauge
cauc_sep_database_connections{state="active"} 5
cauc_sep_database_connections{state="idle"} 5

# HELP cauc_sep_alerts_active Number of active alerts
# TYPE cauc_sep_alerts_active gauge
cauc_sep_alerts_active{severity="critical"} 1
cauc_sep_alerts_active{severity="warning"} 2
cauc_sep_alerts_active{severity="info"} 0
```

---

## WebSocket实时监控

### 连接监控WebSocket

**端点**: `WS /api/ws/monitor`

**认证**: 需要（通过查询参数传递token）

**连接URL**:
```
ws://localhost:8000/api/ws/monitor?token=<access_token>
```

**订阅消息格式**:

```json
{
    "action": "subscribe",
    "channels": ["health", "performance", "alerts", "devices"]
}
```

**推送消息格式**:

```json
{
    "channel": "performance",
    "timestamp": "2024-03-15T10:30:00Z",
    "data": {
        "cpu_usage": 25.5,
        "memory_usage": 35.4,
        "active_requests": 5
    }
}
```

**告警推送**:

```json
{
    "channel": "alerts",
    "timestamp": "2024-03-15T10:30:00Z",
    "data": {
        "event": "created",
        "alert": {
            "id": "alert_005",
            "severity": "critical",
            "title": "新告警",
            "message": "检测到新问题"
        }
    }
}
```

---

## 错误码参考

### 健康检查错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| HEALTH_CHECK_FAILED | 503 | 健康检查失败 |
| COMPONENT_UNHEALTHY | 503 | 组件不健康 |
| DATABASE_ERROR | 503 | 数据库连接失败 |

### 性能监控错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| PROFILING_FAILED | 500 | 性能分析失败 |
| METRICS_UNAVAILABLE | 503 | 指标不可用 |
| INVALID_PROFILE_OPERATION | 400 | 无效的分析操作 |

### 日志错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| LOG_EXPORT_FAILED | 500 | 日志导出失败 |
| LOG_CLEANUP_FAILED | 500 | 日志清理失败 |
| INVALID_LOG_TYPE | 400 | 无效的日志类型 |

### 告警错误

| 错误码 | HTTP状态码 | 说明 |
|--------|------------|------|
| ALERT_NOT_FOUND | 404 | 告警不存在 |
| RULE_NOT_FOUND | 404 | 规则不存在 |
| INVALID_ALERT_STATUS | 400 | 无效的告警状态 |
| RULE_ALREADY_EXISTS | 400 | 规则已存在 |

---

## 数据模型

### HealthStatus 健康状态模型

```typescript
interface HealthStatus {
    status: 'healthy' | 'degraded' | 'unhealthy';
    timestamp: string;
    version: string;
    uptime: number;
    components?: Record<string, ComponentHealth>;
}

interface ComponentHealth {
    status: 'healthy' | 'degraded' | 'unhealthy';
    latency_ms?: number;
    details?: Record<string, any>;
}
```

### PerformanceMetrics 性能指标模型

```typescript
interface PerformanceMetrics {
    timestamp: string;
    cpu: CPUMetrics;
    memory: MemoryMetrics;
    disk: DiskMetrics;
    network: NetworkMetrics;
    process: ProcessMetrics;
}

interface CPUMetrics {
    usage_percent: number;
    cores: number;
    load_average: number[];
    process_usage_percent: number;
}

interface MemoryMetrics {
    total_gb: number;
    used_gb: number;
    available_gb: number;
    usage_percent: number;
    process_used_mb: number;
}
```

### Alert 告警模型

```typescript
interface Alert {
    id: string;
    timestamp: string;
    severity: 'info' | 'warning' | 'critical';
    category: 'device' | 'system' | 'performance';
    title: string;
    message: string;
    source: AlertSource;
    status: 'active' | 'acknowledged' | 'resolved';
    acknowledged_by?: User;
    acknowledged_at?: string;
    resolved_at?: string;
    metadata?: Record<string, any>;
    history?: AlertEvent[];
}

interface AlertSource {
    type: string;
    id: string;
    name: string;
}

interface AlertRule {
    id: string;
    name: string;
    description?: string;
    enabled: boolean;
    category: string;
    severity: string;
    conditions: AlertCondition;
    actions: AlertAction[];
    cooldown_minutes: number;
}
```

### AuditLog 审计日志模型

```typescript
interface AuditLog {
    id: number;
    timestamp: string;
    user: {
        id: number;
        username: string;
    };
    action: string;
    resource_type: string;
    resource_id: string;
    operation: string;
    details?: Record<string, any>;
    status: 'success' | 'failure';
    ip_address: string;
    user_agent: string;
}
```

---

## 使用示例

### 健康检查集成

```python
import requests
import time

def check_system_health():
    """定期检查系统健康状态"""
    while True:
        try:
            response = requests.get('http://localhost:8000/api/health/detailed')
            data = response.json()
            
            if data['status'] != 'healthy':
                # 发送告警通知
                send_alert(f"系统状态异常: {data['status']}")
                
                # 检查具体组件
                for component, health in data['components'].items():
                    if health['status'] != 'healthy':
                        print(f"组件 {component} 异常")
                        
        except Exception as e:
            print(f"健康检查失败: {e}")
            
        time.sleep(60)  # 每分钟检查一次
```

### 性能监控仪表板

```python
import requests

def get_dashboard_data():
    """获取仪表板数据"""
    headers = {'Authorization': f'Bearer {token}'}
    
    # 获取系统指标
    metrics = requests.get(
        'http://localhost:8000/api/performance/metrics',
        headers=headers
    ).json()
    
    # 获取设备状态
    devices = requests.get(
        'http://localhost:8000/api/health/devices',
        headers=headers
    ).json()
    
    # 获取活跃告警
    alerts = requests.get(
        'http://localhost:8000/api/alerts?status=active',
        headers=headers
    ).json()
    
    return {
        'cpu_usage': metrics['cpu']['usage_percent'],
        'memory_usage': metrics['memory']['usage_percent'],
        'devices_online': devices['summary']['online'],
        'devices_total': devices['summary']['total'],
        'active_alerts': alerts['data']['summary']['total_active']
    }
```

### 告警处理流程

```python
def handle_alerts():
    """处理活跃告警"""
    headers = {'Authorization': f'Bearer {token}'}
    
    # 获取活跃告警
    response = requests.get(
        'http://localhost:8000/api/alerts?status=active&severity=critical',
        headers=headers
    )
    
    alerts = response.json()['data']['alerts']
    
    for alert in alerts:
        print(f"处理告警: {alert['title']}")
        
        # 根据告警类型采取不同措施
        if alert['category'] == 'device':
            # 尝试重新连接设备
            device_id = alert['metadata']['device_id']
            reconnect_device(device_id)
            
        elif alert['category'] == 'system':
            # 确认告警
            requests.post(
                f"http://localhost:8000/api/alerts/{alert['id']}/acknowledge",
                headers=headers,
                json={'note': '正在处理'}
            )
```

### WebSocket实时监控

```javascript
// JavaScript WebSocket连接示例
const ws = new WebSocket('ws://localhost:8000/api/ws/monitor?token=' + token);

ws.onopen = function() {
    // 订阅监控频道
    ws.send(JSON.stringify({
        action: 'subscribe',
        channels: ['health', 'performance', 'alerts', 'devices']
    }));
};

ws.onmessage = function(event) {
    const message = JSON.parse(event.data);
    
    switch(message.channel) {
        case 'performance':
            updatePerformanceChart(message.data);
            break;
        case 'alerts':
            showAlertNotification(message.data);
            break;
        case 'devices':
            updateDeviceStatus(message.data);
            break;
    }
};
```

---

## 注意事项

1. **健康检查频率**: 建议每30-60秒进行一次健康检查，避免过于频繁
2. **性能影响**: 详细健康检查和性能分析可能对系统有一定影响，生产环境谨慎使用
3. **日志存储**: 定期清理过期日志，避免占用过多磁盘空间
4. **告警冷却**: 设置合理的告警冷却时间，避免告警风暴
5. **权限控制**: 监控数据可能包含敏感信息，确保适当的访问控制
6. **Prometheus集成**: 使用标准Prometheus格式便于与现有监控系统集成
