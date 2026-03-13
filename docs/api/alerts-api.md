# 告警系统 API 文档

**版本**: v1.1  
**更新日期**: 2026-03-14  
**基础路径**: `/api`
**应用版本**: 0.3.0

---

## 概述

告警系统API提供完整的告警生命周期管理，包括告警规则配置、告警触发与通知、告警确认与处理等功能。该模块支持：

- 多级别告警（info、warning、error、critical）
- 自定义告警规则与阈值
- 告警抑制与静默机制
- 告警历史记录与统计
- WebSocket实时告警推送

---

## 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/alerts` | GET | 获取告警列表 |
| `/api/alerts/active` | GET | 获取活跃告警 |
| `/api/alerts/{alert_id}` | GET | 获取单个告警详情 |
| `/api/alerts/{alert_id}/acknowledge` | POST | 确认告警 |
| `/api/alerts/{alert_id}/resolve` | POST | 解决告警 |
| `/api/alerts/rules` | GET | 获取告警规则列表 |
| `/api/alerts/rules` | POST | 创建告警规则 |
| `/api/alerts/rules/{rule_id}` | PUT | 更新告警规则 |
| `/api/alerts/rules/{rule_id}` | DELETE | 删除告警规则 |
| `/api/alerts/stats` | GET | 获取告警统计信息 |
| `/api/alerts/history` | GET | 获取告警历史 |

---

## 告警级别

系统支持四个告警级别，按严重程度递增：

| 级别 | 说明 | 颜色标识 | 通知方式 |
|------|------|----------|----------|
| `info` | 信息提示 | 蓝色 | 控制台日志 |
| `warning` | 警告 | 黄色 | 控制台日志 + 界面提示 |
| `error` | 错误 | 红色 | 控制台日志 + 界面提示 + 邮件 |
| `critical` | 严重错误 | 深红色 | 全部通知方式 + 短信 |

---

## 告警管理

### 获取告警列表

```http
GET /api/alerts
```

**功能说明**: 获取所有告警，支持分页和过滤。

**查询参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `level` | string | 否 | 按级别过滤：info/warning/error/critical |
| `status` | string | 否 | 按状态过滤：active/acknowledged/resolved |
| `source` | string | 否 | 按来源过滤 |
| `start_time` | string | 否 | 开始时间（ISO格式） |
| `end_time` | string | 否 | 结束时间（ISO格式） |
| `page` | integer | 否 | 页码，默认1 |
| `page_size` | integer | 否 | 每页数量，默认20 |

**响应模型**:

```json
{
  "total": 100,
  "page": 1,
  "page_size": 20,
  "alerts": [
    {
      "id": "alert_001",
      "title": "CPU使用率过高",
      "message": "CPU使用率已达到85%，超过阈值80%",
      "level": "warning",
      "status": "active",
      "source": "system_monitor",
      "labels": {
        "component": "cpu",
        "hostname": "server-01"
      },
      "value": 85.0,
      "threshold": 80.0,
      "created_at": "2026-03-08T10:30:00.000Z",
      "updated_at": "2026-03-08T10:30:00.000Z",
      "acknowledged_at": null,
      "resolved_at": null,
      "acknowledged_by": null
    }
  ]
}
```

---

### 获取活跃告警

```http
GET /api/alerts/active
```

**功能说明**: 获取所有未解决的活跃告警，按严重程度和时间排序。

**响应模型**:

```json
{
  "total": 5,
  "by_level": {
    "critical": 1,
    "error": 1,
    "warning": 2,
    "info": 1
  },
  "alerts": [
    {
      "id": "alert_001",
      "title": "设备连接丢失",
      "message": "步进电机 stepper_01 连接已断开",
      "level": "critical",
      "status": "active",
      "source": "device_monitor",
      "labels": {
        "device_id": "stepper_01",
        "device_type": "stepper_motor"
      },
      "created_at": "2026-03-08T10:30:00.000Z"
    }
  ]
}
```

---

### 获取单个告警详情

```http
GET /api/alerts/{alert_id}
```

**路径参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `alert_id` | string | 告警唯一标识 |

**响应模型**:

```json
{
  "id": "alert_001",
  "title": "CPU使用率过高",
  "message": "CPU使用率已达到85%，超过阈值80%",
  "level": "warning",
  "status": "active",
  "source": "system_monitor",
  "labels": {
    "component": "cpu",
    "hostname": "server-01"
  },
  "value": 85.0,
  "threshold": 80.0,
  "created_at": "2026-03-08T10:30:00.000Z",
  "updated_at": "2026-03-08T10:30:00.000Z",
  "acknowledged_at": null,
  "resolved_at": null,
  "acknowledged_by": null,
  "history": [
    {
      "action": "created",
      "timestamp": "2026-03-08T10:30:00.000Z",
      "details": "告警首次触发"
    }
  ],
  "related_alerts": []
}
```

---

### 确认告警

```http
POST /api/alerts/{alert_id}/acknowledge
```

**功能说明**: 确认告警，表示已知悉并正在处理。

**请求体**:

```json
{
  "acknowledged_by": "admin",
  "note": "正在排查原因"
}
```

**响应模型**:

```json
{
  "id": "alert_001",
  "status": "acknowledged",
  "acknowledged_at": "2026-03-08T10:35:00.000Z",
  "acknowledged_by": "admin",
  "message": "告警已确认"
}
```

---

### 解决告警

```http
POST /api/alerts/{alert_id}/resolve
```

**功能说明**: 标记告警为已解决。

**请求体**:

```json
{
  "resolved_by": "admin",
  "resolution": "重启了相关服务，CPU使用率已恢复正常"
}
```

**响应模型**:

```json
{
  "id": "alert_001",
  "status": "resolved",
  "resolved_at": "2026-03-08T10:40:00.000Z",
  "resolution": "重启了相关服务，CPU使用率已恢复正常",
  "message": "告警已解决"
}
```

---

## 告警规则管理

### 获取告警规则列表

```http
GET /api/alerts/rules
```

**功能说明**: 获取所有告警规则配置。

**响应模型**:

```json
{
  "total": 10,
  "rules": [
    {
      "id": "rule_001",
      "name": "CPU使用率告警",
      "description": "当CPU使用率超过阈值时触发告警",
      "enabled": true,
      "condition": {
        "metric": "cpu_percent",
        "operator": ">",
        "threshold": 80.0,
        "duration": 60
      },
      "level": "warning",
      "labels": {
        "component": "cpu"
      },
      "notification": {
        "channels": ["console", "ui"],
        "repeat_interval": 300
      },
      "created_at": "2026-03-01T00:00:00.000Z",
      "updated_at": "2026-03-08T10:00:00.000Z"
    }
  ]
}
```

---

### 创建告警规则

```http
POST /api/alerts/rules
```

**功能说明**: 创建新的告警规则。

**请求体**:

```json
{
  "name": "内存使用率告警",
  "description": "当内存使用率超过阈值时触发告警",
  "enabled": true,
  "condition": {
    "metric": "memory_percent",
    "operator": ">",
    "threshold": 85.0,
    "duration": 30
  },
  "level": "warning",
  "labels": {
    "component": "memory"
  },
  "notification": {
    "channels": ["console", "ui"],
    "repeat_interval": 300
  }
}
```

**字段说明**:

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `name` | string | 是 | 规则名称 |
| `description` | string | 否 | 规则描述 |
| `enabled` | boolean | 否 | 是否启用，默认true |
| `condition.metric` | string | 是 | 监控指标名称 |
| `condition.operator` | string | 是 | 比较运算符：>、>=、<、<=、==、!= |
| `condition.threshold` | number | 是 | 阈值 |
| `condition.duration` | integer | 否 | 持续时间（秒），默认0 |
| `level` | string | 是 | 告警级别 |
| `labels` | object | 否 | 标签键值对 |
| `notification.channels` | array | 否 | 通知渠道 |
| `notification.repeat_interval` | integer | 否 | 重复通知间隔（秒） |

**响应模型**:

```json
{
  "id": "rule_002",
  "name": "内存使用率告警",
  "description": "当内存使用率超过阈值时触发告警",
  "enabled": true,
  "condition": {
    "metric": "memory_percent",
    "operator": ">",
    "threshold": 85.0,
    "duration": 30
  },
  "level": "warning",
  "labels": {
    "component": "memory"
  },
  "notification": {
    "channels": ["console", "ui"],
    "repeat_interval": 300
  },
  "created_at": "2026-03-08T10:45:00.000Z",
  "updated_at": "2026-03-08T10:45:00.000Z"
}
```

---

### 更新告警规则

```http
PUT /api/alerts/rules/{rule_id}
```

**功能说明**: 更新现有告警规则。

**请求体**: 与创建规则相同，所有字段可选。

**响应模型**: 返回更新后的完整规则对象。

---

### 删除告警规则

```http
DELETE /api/alerts/rules/{rule_id}
```

**功能说明**: 删除指定的告警规则。

**响应模型**:

```json
{
  "message": "规则已删除",
  "rule_id": "rule_002"
}
```

---

## 告警统计

### 获取告警统计信息

```http
GET /api/alerts/stats
```

**功能说明**: 获取告警统计数据，用于仪表板展示。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `period` | string | 统计周期：hour/day/week/month，默认day |

**响应模型**:

```json
{
  "period": "day",
  "total_alerts": 25,
  "by_level": {
    "critical": 2,
    "error": 5,
    "warning": 12,
    "info": 6
  },
  "by_status": {
    "active": 3,
    "acknowledged": 5,
    "resolved": 17
  },
  "by_source": {
    "system_monitor": 15,
    "device_monitor": 8,
    "application": 2
  },
  "trend": [
    {
      "time": "2026-03-08T00:00:00.000Z",
      "count": 5
    },
    {
      "time": "2026-03-08T01:00:00.000Z",
      "count": 3
    }
  ],
  "top_alerts": [
    {
      "title": "CPU使用率过高",
      "count": 8
    }
  ],
  "avg_resolution_time_seconds": 300.5
}
```

---

### 获取告警历史

```http
GET /api/alerts/history
```

**功能说明**: 获取历史告警记录，支持时间范围查询。

**查询参数**:

| 参数 | 类型 | 说明 |
|------|------|------|
| `start_time` | string | 开始时间（ISO格式） |
| `end_time` | string | 结束时间（ISO格式） |
| `limit` | integer | 返回数量限制，默认100 |

**响应模型**:

```json
{
  "start_time": "2026-03-01T00:00:00.000Z",
  "end_time": "2026-03-08T23:59:59.000Z",
  "total": 150,
  "history": [
    {
      "id": "alert_001",
      "title": "CPU使用率过高",
      "level": "warning",
      "status": "resolved",
      "created_at": "2026-03-05T10:30:00.000Z",
      "resolved_at": "2026-03-05T10:40:00.000Z",
      "duration_seconds": 600
    }
  ]
}
```

---

## WebSocket 实时推送

### 连接地址

```
ws://localhost:8000/ws/alerts
```

### 消息格式

**服务端推送消息**:

```json
{
  "type": "alert",
  "action": "created",
  "data": {
    "id": "alert_001",
    "title": "CPU使用率过高",
    "message": "CPU使用率已达到85%",
    "level": "warning",
    "status": "active",
    "created_at": "2026-03-08T10:30:00.000Z"
  },
  "timestamp": "2026-03-08T10:30:00.000Z"
}
```

**消息类型**:

| action | 说明 |
|--------|------|
| `created` | 新告警创建 |
| `updated` | 告警更新 |
| `acknowledged` | 告警已确认 |
| `resolved` | 告警已解决 |
| `deleted` | 告警已删除 |

---

## 预置告警规则

系统预置以下告警规则：

### 系统资源规则

| 规则名称 | 指标 | 阈值 | 级别 |
|----------|------|------|------|
| CPU使用率告警 | cpu_percent | > 80% | warning |
| CPU严重告警 | cpu_percent | > 95% | critical |
| 内存使用率告警 | memory_percent | > 85% | warning |
| 内存严重告警 | memory_percent | > 95% | critical |
| 磁盘使用率告警 | disk_percent | > 85% | warning |
| 磁盘严重告警 | disk_percent | > 95% | critical |

### 设备监控规则

| 规则名称 | 指标 | 阈值 | 级别 |
|----------|------|------|------|
| 设备断开告警 | device_connected | == 0 | error |
| 设备错误告警 | device_error_count | > 5 | warning |
| 设备严重错误 | device_error_count | > 20 | critical |

---

## 使用示例

### JavaScript/TypeScript

```typescript
/**
 * 获取活跃告警
 */
async function fetchActiveAlerts(): Promise<ActiveAlertsResponse> {
  const response = await fetch('/api/alerts/active')
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  return response.json()
}

/**
 * 确认告警
 */
async function acknowledgeAlert(
  alertId: string, 
  acknowledgedBy: string, 
  note?: string
): Promise<AcknowledgeResponse> {
  const response = await fetch(`/api/alerts/${alertId}/acknowledge`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      acknowledged_by: acknowledgedBy,
      note
    })
  })
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return response.json()
}

/**
 * 创建告警规则
 */
async function createAlertRule(rule: AlertRuleCreate): Promise<AlertRule> {
  const response = await fetch('/api/alerts/rules', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(rule)
  })
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`)
  }
  
  return response.json()
}

/**
 * WebSocket实时告警监听
 */
function subscribeToAlerts(
  onAlert: (alert: AlertMessage) => void,
  onError?: (error: Error) => void
): () => void {
  const ws = new WebSocket('ws://localhost:8000/ws/alerts')
  
  ws.onmessage = (event) => {
    const message = JSON.parse(event.data)
    onAlert(message)
  }
  
  ws.onerror = (error) => {
    onError?.(new Error('WebSocket error'))
  }
  
  // 返回取消订阅函数
  return () => {
    ws.close()
  }
}

// 使用示例
const unsubscribe = subscribeToAlerts((message) => {
  if (message.action === 'created') {
    console.log(`新告警: ${message.data.title}`)
    showNotification(message.data)
  }
})
```

### Python

```python
import requests
from typing import Dict, Any, List, Optional

class AlertClient:
    """告警系统客户端。"""
    
    def __init__(self, base_url: str = 'http://localhost:8000'):
        self.base_url = base_url
    
    def get_alerts(
        self,
        level: Optional[str] = None,
        status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """
        获取告警列表。
        
        Args:
            level: 按级别过滤
            status: 按状态过滤
            page: 页码
            page_size: 每页数量
        
        Returns:
            dict: 告警列表响应
        """
        params = {'page': page, 'page_size': page_size}
        if level:
            params['level'] = level
        if status:
            params['status'] = status
        
        response = requests.get(f'{self.base_url}/api/alerts', params=params)
        response.raise_for_status()
        return response.json()
    
    def get_active_alerts(self) -> Dict[str, Any]:
        """
        获取活跃告警。
        
        Returns:
            dict: 活跃告警响应
        """
        response = requests.get(f'{self.base_url}/api/alerts/active')
        response.raise_for_status()
        return response.json()
    
    def acknowledge_alert(
        self,
        alert_id: str,
        acknowledged_by: str,
        note: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        确认告警。
        
        Args:
            alert_id: 告警ID
            acknowledged_by: 确认人
            note: 备注
        
        Returns:
            dict: 确认响应
        """
        response = requests.post(
            f'{self.base_url}/api/alerts/{alert_id}/acknowledge',
            json={'acknowledged_by': acknowledged_by, 'note': note}
        )
        response.raise_for_status()
        return response.json()
    
    def create_rule(
        self,
        name: str,
        metric: str,
        operator: str,
        threshold: float,
        level: str,
        duration: int = 0,
        enabled: bool = True
    ) -> Dict[str, Any]:
        """
        创建告警规则。
        
        Args:
            name: 规则名称
            metric: 监控指标
            operator: 比较运算符
            threshold: 阈值
            level: 告警级别
            duration: 持续时间
            enabled: 是否启用
        
        Returns:
            dict: 创建的规则
        """
        rule = {
            'name': name,
            'enabled': enabled,
            'condition': {
                'metric': metric,
                'operator': operator,
                'threshold': threshold,
                'duration': duration
            },
            'level': level
        }
        
        response = requests.post(
            f'{self.base_url}/api/alerts/rules',
            json=rule
        )
        response.raise_for_status()
        return response.json()


# 使用示例
if __name__ == '__main__':
    client = AlertClient()
    
    # 获取活跃告警
    active = client.get_active_alerts()
    print(f"活跃告警数: {active['total']}")
    
    # 确认告警
    if active['alerts']:
        result = client.acknowledge_alert(
            active['alerts'][0]['id'],
            'admin',
            '正在处理'
        )
        print(f"确认结果: {result['message']}")
    
    # 创建新规则
    new_rule = client.create_rule(
        name='测试规则',
        metric='cpu_percent',
        operator='>',
        threshold=90.0,
        level='error'
    )
    print(f"创建规则: {new_rule['id']}")
```

---

## 最佳实践

### 1. 告警分级处理

根据告警级别采取不同的处理策略：

```javascript
function handleAlert(alert) {
  switch (alert.level) {
    case 'critical':
      // 立即通知所有相关人员
      sendSMS(alert)
      sendEmail(alert)
      showUrgentNotification(alert)
      break
    case 'error':
      // 发送邮件和界面通知
      sendEmail(alert)
      showNotification(alert)
      break
    case 'warning':
      // 仅界面通知
      showNotification(alert)
      break
    case 'info':
      // 记录日志
      console.log(`[INFO] ${alert.title}: ${alert.message}`)
      break
  }
}
```

### 2. 告警抑制

避免告警风暴，对相似告警进行聚合：

```javascript
// 设置告警抑制窗口
const SUPPRESSION_WINDOW = 300000 // 5分钟
const alertCache = new Map()

function shouldSuppress(alert) {
  const key = `${alert.source}:${alert.title}`
  const lastAlert = alertCache.get(key)
  
  if (lastAlert && Date.now() - lastAlert < SUPPRESSION_WINDOW) {
    return true
  }
  
  alertCache.set(key, Date.now())
  return false
}
```

### 3. 自动恢复检测

配置告警自动恢复检测：

```json
{
  "name": "CPU使用率告警",
  "condition": {
    "metric": "cpu_percent",
    "operator": ">",
    "threshold": 80.0,
    "duration": 60
  },
  "recovery_condition": {
    "metric": "cpu_percent",
    "operator": "<",
    "threshold": 70.0,
    "duration": 30
  },
  "auto_resolve": true
}
```

---

## 相关文档

- [健康监控API文档](./health-api.md)
- [性能分析API文档](./performance-api.md)
- [故障排除指南](../troubleshooting.md)

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-08 | 初始版本 | Tech Writer Agent |
| v1.1 | 2026-03-14 | 更新版本号，添加应用版本信息 | Tech Writer Agent |

---

*CAUC-SEP 自旋电子器件实验平台 | 告警系统API文档*  
*版本 0.3.0 | © 2025-2026 版权所有*
