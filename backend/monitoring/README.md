# ============================================================================
# CAUC-SEP 监控告警系统部署指南
# ============================================================================
#
# 文件名: README.md
# 路径: d:\cauc-sep\backend\monitoring\README.md
# 功能: 监控告警系统部署和使用文档
# 版本: v0.3.0
# 创建日期: 2024-01-20
# 最后更新: 2026-03-14
#
# 说明:
#   本文档介绍如何部署和配置CAUC-SEP监控告警系统，包括：
#   - Prometheus指标采集
#   - Grafana可视化仪表板
#   - 告警规则配置
#   - 常用查询示例
#   - 故障排查指南
# ============================================================================

## 概述

本文档介绍如何部署和配置CAUC-SEP监控告警系统，包括Prometheus指标采集、Grafana可视化仪表板和告警规则配置。

## 架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    CAUC-SEP 监控架构                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │   Backend    │    │  Prometheus  │    │   Grafana    │      │
│  │   :8000      │───▶│    :9090     │───▶│    :3000     │      │
│  │  /api/metrics│    │              │    │              │      │
│  └──────────────┘    └──────────────┘    └──────────────┘      │
│         │                   │                   │               │
│         │                   ▼                   │               │
│         │           ┌──────────────┐           │               │
│         │           │Alertmanager  │           │               │
│         │           │    :9093     │           │               │
│         │           └──────────────┘           │               │
│         │                   │                   │               │
│         ▼                   ▼                   ▼               │
│  ┌─────────────────────────────────────────────────────┐       │
│  │              通知渠道（钉钉/企业微信/邮件）            │       │
│  └─────────────────────────────────────────────────────┘       │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## 快速开始

### 1. 使用Docker Compose部署

```bash
# 进入监控配置目录
cd monitoring

# 启动监控栈
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f prometheus
docker-compose logs -f grafana
```

### 2. 访问监控界面

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - 默认用户名: `admin`
  - 默认密码: `cauc-sep-admin`

### 3. 验证指标采集

```bash
# 检查后端指标端点
curl http://localhost:8000/api/metrics

# 检查Prometheus目标状态
curl http://localhost:9090/api/v1/targets
```

## 指标说明

### 系统资源指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `cpu_usage_percent` | Gauge | % | CPU使用率 |
| `memory_usage_percent` | Gauge | % | 内存使用率 |
| `disk_usage_percent` | Gauge | % | 磁盘使用率 |
| `system_uptime_seconds` | Gauge | s | 系统运行时长 |

### 健康评分指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `health_score_overall` | Gauge | 0-100 | 综合健康评分 |
| `health_score_system` | Gauge | 0-100 | 系统资源评分 |
| `health_score_device` | Gauge | 0-100 | 设备状态评分 |
| `health_score_performance` | Gauge | 0-100 | 性能评分 |
| `health_score_reliability` | Gauge | 0-100 | 可靠性评分 |

### 设备指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `devices_total` | Gauge | - | 设备总数 |
| `devices_connected` | Gauge | - | 已连接设备数 |
| `devices_disconnected` | Gauge | - | 断开设备数 |
| `devices_error` | Gauge | - | 错误状态设备数 |
| `device_connection_rate_percent` | Gauge | % | 设备连接率 |
| `device_connected{device_id, device_type}` | Gauge | 0/1 | 设备连接状态 |
| `device_status{device_id, device_type, status}` | Gauge | 0-9 | 设备状态码 |

### 实验指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `cauc_sep_experiments_total` | Counter | - | 实验总数 |
| `cauc_sep_experiments_running` | Gauge | - | 正在运行的实验数 |
| `cauc_sep_experiments_completed_total` | Counter | - | 已完成的实验总数 |
| `cauc_sep_experiments_failed_total` | Counter | - | 失败的实验总数 |
| `cauc_sep_experiment_duration_seconds` | Histogram | s | 实验持续时间 |

### 设备操作指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `cauc_sep_device_operations_total` | Counter | - | 设备操作总数 |
| `cauc_sep_device_operations_successful_total` | Counter | - | 成功的设备操作数 |
| `cauc_sep_device_operations_failed_total` | Counter | - | 失败的设备操作数 |
| `cauc_sep_device_operation_duration_seconds` | Histogram | s | 设备操作耗时 |

### API请求指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `cauc_sep_api_requests_total` | Counter | - | API请求总数 |
| `cauc_sep_api_request_duration_seconds` | Histogram | s | API请求耗时 |
| `cauc_sep_api_requests_in_progress` | Gauge | - | 正在处理的请求数 |

### WebSocket指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `cauc_sep_websocket_connections` | Gauge | - | WebSocket连接数 |
| `cauc_sep_websocket_messages_total` | Counter | - | WebSocket消息总数 |
| `cauc_sep_websocket_errors_total` | Counter | - | WebSocket错误总数 |

### 存储指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `cauc_sep_storage_used_bytes` | Gauge | bytes | 已用存储空间 |
| `cauc_sep_storage_total_bytes` | Gauge | bytes | 总存储空间 |
| `cauc_sep_storage_usage_percent` | Gauge | % | 存储使用率 |
| `cauc_sep_data_records_total` | Counter | - | 数据记录总数 |

### 告警指标

| 指标名称 | 类型 | 单位 | 说明 |
|---------|------|------|------|
| `alerts_active` | Gauge | - | 活跃告警数量 |
| `alerts_by_level{level}` | Gauge | - | 按级别统计告警数 |

## 告警规则

### 告警级别

| 级别 | 说明 | 响应时间 |
|------|------|---------|
| `info` | 信息提示 | 24小时 |
| `warning` | 警告 | 4小时 |
| `critical` | 严重 | 30分钟 |
| `error` | 错误 | 1小时 |

### 主要告警规则

#### 系统资源告警

1. **HighCPUUsage**: CPU使用率 > 80%，持续5分钟
2. **CriticalCPUUsage**: CPU使用率 > 95%，持续2分钟
3. **HighMemoryUsage**: 内存使用率 > 80%，持续5分钟
4. **CriticalMemoryUsage**: 内存使用率 > 95%，持续2分钟
5. **HighDiskUsage**: 磁盘使用率 > 85%，持续10分钟
6. **CriticalDiskUsage**: 磁盘使用率 > 95%，持续5分钟

#### 设备状态告警

1. **DeviceDisconnected**: 有设备断开连接
2. **DeviceError**: 有设备处于错误状态
3. **LowDeviceConnectionRate**: 设备连接率 < 50%

#### 实验状态告警

1. **HighExperimentFailureRate**: 实验失败率 > 10%
2. **LongRunningExperiment**: 实验运行时间 > 24小时

#### API性能告警

1. **HighAPILatency**: API P95响应时间 > 1秒
2. **HighAPIErrorRate**: API 5xx错误率 > 5%

#### 健康评分告警

1. **LowHealthScore**: 健康评分 < 70
2. **CriticalHealthScore**: 健康评分 < 50

## Grafana仪表板

### 系统概览仪表板

**文件**: `grafana/dashboards/system-overview.json`

**功能**:
- 综合健康评分仪表盘
- CPU/内存/磁盘使用率监控
- 系统资源趋势图
- 健康评分趋势图
- 告警状态统计

### 设备监控仪表板

**文件**: `grafana/dashboards/device-monitoring.json`

**功能**:
- 设备状态概览
- 设备连接状态表
- 设备类型分布
- 设备操作统计
- 设备操作延迟分布
- 设备连接率趋势

### 实验分析仪表板

**文件**: `grafana/dashboards/experiment-analysis.json`

**功能**:
- 实验统计概览
- 实验趋势分析
- 实验持续时间分布
- 数据存储统计
- API请求统计
- WebSocket统计

## 配置说明

### Prometheus配置

**文件**: `prometheus/prometheus.yml`

```yaml
global:
  scrape_interval: 15s      # 抓取间隔
  evaluation_interval: 15s  # 规则评估间隔
  scrape_timeout: 10s       # 抓取超时

scrape_configs:
  - job_name: 'cauc-sep-backend'
    static_configs:
      - targets: ['host.docker.internal:8000']
    metrics_path: /api/metrics
```

### 告警规则配置

**文件**: `prometheus/alert_rules.yml`

包含所有告警规则定义，可根据实际需求调整阈值。

### Grafana数据源配置

**文件**: `grafana/datasources.yml`

自动配置Prometheus数据源。

### Grafana仪表板配置

**文件**: `grafana/dashboard_provisioning.yml`

自动加载仪表板JSON文件。

## 常用查询示例

### PromQL查询

```promql
# CPU使用率
cpu_usage_percent

# 内存使用率趋势（5分钟平均）
avg_over_time(memory_usage_percent[5m])

# 设备连接率
device_connection_rate_percent

# API请求速率（每秒）
rate(cauc_sep_api_requests_total[5m])

# API P95响应时间
histogram_quantile(0.95, rate(cauc_sep_api_request_duration_seconds_bucket[5m]))

# 实验成功率（过去1小时）
(
  sum(rate(cauc_sep_experiments_completed_total[1h]))
  /
  (sum(rate(cauc_sep_experiments_completed_total[1h])) + sum(rate(cauc_sep_experiments_failed_total[1h])))
) * 100

# 设备操作错误率
(
  sum(rate(cauc_sep_device_operations_failed_total[5m]))
  /
  sum(rate(cauc_sep_device_operations_total[5m]))
) * 100

# 存储增长速率（每小时）
rate(cauc_sep_data_records_total[1h]) * 3600
```

## 维护操作

### 重启服务

```bash
# 重启Prometheus
docker-compose restart prometheus

# 重启Grafana
docker-compose restart grafana

# 重启所有服务
docker-compose restart
```

### 更新配置

```bash
# 更新Prometheus配置
docker-compose exec prometheus kill -HUP 1

# 或重启服务
docker-compose restart prometheus
```

### 数据备份

```bash
# 备份Prometheus数据
docker run --rm -v cauc-sep_prometheus_data:/data -v $(pwd):/backup alpine tar czf /backup/prometheus_backup.tar.gz /data

# 备份Grafana数据
docker run --rm -v cauc-sep_grafana_data:/data -v $(pwd):/backup alpine tar czf /backup/grafana_backup.tar.gz /data
```

### 数据恢复

```bash
# 恢复Prometheus数据
docker run --rm -v cauc-sep_prometheus_data:/data -v $(pwd):/backup alpine tar xzf /backup/prometheus_backup.tar.gz -C /

# 恢复Grafana数据
docker run --rm -v cauc-sep_grafana_data:/data -v $(pwd):/backup alpine tar xzf /backup/grafana_backup.tar.gz -C /
```

## 故障排查

### Prometheus无法采集指标

1. 检查后端服务是否运行: `curl http://localhost:8000/api/health`
2. 检查指标端点: `curl http://localhost:8000/api/metrics`
3. 检查Prometheus目标状态: http://localhost:9090/targets
4. 检查网络连接: `docker network inspect cauc-sep-monitoring`

### Grafana无法显示数据

1. 检查数据源配置: Grafana -> Configuration -> Data Sources
2. 测试数据源连接
3. 检查Prometheus是否正常采集数据
4. 检查仪表板时间范围设置

### 告警不触发

1. 检查告警规则文件是否正确加载
2. 检查Prometheus规则状态: http://localhost:9090/rules
3. 检查告警条件是否满足
4. 检查Alertmanager配置（如已启用）

## 扩展配置

### 配置告警通知

1. 编辑 `prometheus/prometheus.yml`，启用Alertmanager配置
2. 创建 `alertmanager/alertmanager.yml` 配置文件
3. 配置通知渠道（钉钉、企业微信、邮件等）

### 添加自定义指标

1. 在 `core/metrics.py` 中添加新的指标定义
2. 在业务代码中调用指标记录方法
3. 重启后端服务使配置生效

### 添加自定义仪表板

1. 在Grafana中创建新仪表板
2. 导出JSON配置
3. 保存到 `grafana/dashboards/` 目录
4. 仪表板将自动加载

## 最佳实践

1. **指标命名**: 遵循Prometheus命名规范，使用snake_case，添加单位后缀
2. **标签使用**: 合理使用标签区分不同维度，但避免高基数标签
3. **告警阈值**: 根据实际业务场景调整告警阈值，避免告警风暴
4. **数据保留**: 根据存储容量和查询需求设置合理的数据保留时间
5. **仪表板组织**: 按功能模块组织仪表板，便于快速定位问题

---

## 版本信息

- **文档版本**: v0.3.0
- **更新日期**: 2026-03-14
- **作者**: CAUC-SEP Team

## 参考资源

- [Prometheus官方文档](https://prometheus.io/docs/)
- [Grafana官方文档](https://grafana.com/docs/)
- [PromQL查询语言](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [告警最佳实践](https://prometheus.io/docs/practices/alerting/)
