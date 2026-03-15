# 设备控制 API

本文档描述 CAUC-SEP 自旋电子器件实验平台的设备控制 API 接口规范。

## 目录

- [概述](#概述)
- [通用规范](#通用规范)
- [电机控制 API](#电机控制-api)
- [电磁铁控制 API](#电磁铁控制-api)
- [温度控制 API](#温度控制-api)
- [压电控制 API](#压电控制-api)
- [皮安表 API](#皮安表-api)
- [错误码说明](#错误码说明)

---

## 概述

设备控制 API 提供对实验平台各类硬件设备的程序化控制接口，支持：

- **步进电机**：定位、JOG运动、PR路径控制
- **电磁铁**：电流/磁场控制、扫描模式、校准管理
- **温度控制器**：温度设定、PID控制、程序控温
- **压电陶瓷**：电压/位移控制、校准管理
- **皮安表**：微电流采集、通道配置、信噪比分析

---

## 通用规范

### 基础 URL

```
http://localhost:8000/api/v1
```

### 认证方式

所有 API 请求需在请求头中携带 JWT 令牌：

```http
Authorization: Bearer <access_token>
```

### 通用响应格式

#### 成功响应

```json
{
  "success": true,
  "message": "操作成功描述",
  "data": { },
  "timestamp": "2026-03-15T10:30:00.000Z"
}
```

#### 错误响应

```json
{
  "success": false,
  "error_code": "DEVICE_NOT_CONNECTED",
  "message": "设备未连接",
  "detail": "请先调用 /api/v1/motor/connect 连接电机",
  "timestamp": "2026-03-15T10:30:00.000Z"
}
```

### HTTP 状态码

| 状态码 | 说明 |
|--------|------|
| 200 | 请求成功 |
| 400 | 请求参数错误或设备状态异常 |
| 401 | 未授权（令牌无效或过期） |
| 403 | 权限不足 |
| 404 | 资源不存在 |
| 422 | 参数验证失败 |
| 500 | 服务器内部错误 |
| 503 | 服务不可用（设备未初始化） |

---

## 电机控制 API

基础路径：`/api/v1/motor`

### 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 获取电机状态 |
| `/connect` | POST | 连接电机 |
| `/disconnect` | POST | 断开电机 |
| `/move` | POST | 绝对定位 |
| `/jog` | POST | JOG点动 |
| `/emergency_stop` | POST | 急停 |
| `/reset` | POST | 复位急停 |
| `/limits` | GET/POST | 获取/设置限位 |
| `/home` | POST | 回零操作 |
| `/reset_alarm` | POST | 报警复位 |
| `/save_params` | POST | 保存参数 |
| `/factory_reset` | POST | 恢复出厂设置 |
| `/status_word` | GET | 读取状态字 |
| `/alarm_code` | GET | 读取报警代码 |
| `/pr/config` | POST | 配置PR路径 |
| `/pr/trigger` | POST | 触发PR路径 |
| `/serial_mode` | GET/POST | 获取/设置串口模式 |
| `/communication/config` | GET/POST | 读取/修改通信参数 |
| `/driver_soft_limit` | GET/POST | 读取/设置驱动器软件限位 |

### 获取电机状态

```http
GET /api/v1/motor/status
```

**响应示例**：

```json
{
  "device_id": "dm2c_main",
  "status": "ready",
  "position_steps": 16000,
  "position_mm": 10.0,
  "alarm_code": 0,
  "alarm_text": "无报警",
  "status_word": {
    "fault": false,
    "enabled": true,
    "running": false,
    "cmd_complete": true,
    "path_complete": true,
    "home_complete": true
  },
  "limit_positive": 50.0,
  "limit_negative": -50.0,
  "connected": true
}
```

**状态字段说明**：

| 字段 | 类型 | 说明 |
|------|------|------|
| `device_id` | string | 设备唯一标识 |
| `status` | string | 设备状态（ready/running/error/disconnected） |
| `position_steps` | integer | 当前位置（步数） |
| `position_mm` | float | 当前位置（毫米） |
| `alarm_code` | integer | 报警代码（0表示无报警） |
| `alarm_text` | string | 报警描述 |
| `connected` | boolean | 是否已连接 |

### 连接电机

```http
POST /api/v1/motor/connect
```

**响应示例**：

```json
{
  "success": true,
  "message": "电机已连接"
}
```

### 断开电机

```http
POST /api/v1/motor/disconnect
```

**响应示例**：

```json
{
  "success": true,
  "message": "电机已断开"
}
```

### 绝对定位

```http
POST /api/v1/motor/move
Content-Type: application/json

{
  "position_mm": 25.0,
  "velocity_mm_s": 10.0,
  "accel_mm_s2": 1000.0,
  "decel_mm_s2": 1000.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `position_mm` | float | 是 | 目标位置（毫米） |
| `velocity_mm_s` | float | 否 | 运动速度（毫米/秒），默认值由驱动器配置 |
| `accel_mm_s2` | float | 否 | 加速度（毫米/秒²） |
| `decel_mm_s2` | float | 否 | 减速度（毫米/秒²） |

**响应示例**：

```json
{
  "success": true,
  "message": "运动已启动",
  "target_position_steps": 40000,
  "target_position_mm": 25.0
}
```

### JOG点动

```http
POST /api/v1/motor/jog
Content-Type: application/json

{
  "direction": 1,
  "velocity_mm_s": 5.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `direction` | integer | 是 | 方向（1=正向，-1=负向） |
| `velocity_mm_s` | float | 是 | 点动速度（毫米/秒） |

**响应示例**：

```json
{
  "success": true,
  "message": "JOG 正向已启动"
}
```

### 急停

```http
POST /api/v1/motor/emergency_stop
```

**响应示例**：

```json
{
  "success": true,
  "message": "急停已触发"
}
```

### 复位急停

```http
POST /api/v1/motor/reset
```

**响应示例**：

```json
{
  "success": true,
  "message": "急停状态已复位"
}
```

### 获取/设置限位

```http
GET /api/v1/motor/limits
```

**响应示例**：

```json
{
  "positive_mm": 50.0,
  "negative_mm": -50.0,
  "enabled": true
}
```

```http
POST /api/v1/motor/limits
Content-Type: application/json

{
  "positive_mm": 100.0,
  "negative_mm": -100.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `positive_mm` | float | 是 | 正向限位（毫米） |
| `negative_mm` | float | 是 | 负向限位（毫米） |

### 回零操作

```http
POST /api/v1/motor/home
Content-Type: application/json

{
  "mode": 1
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | integer | 否 | 回零模式（默认值由驱动器配置） |

**响应示例**：

```json
{
  "success": true,
  "message": "回零已启动"
}
```

### 配置PR路径

```http
POST /api/v1/motor/pr/config
Content-Type: application/json

{
  "path_number": 0,
  "mode": 1,
  "position_mm": 10.0,
  "velocity_mm_s": 1000,
  "accel_time": 100,
  "decel_time": 100,
  "dwell_time": 0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path_number` | integer | 是 | 路径编号（0-15） |
| `mode` | integer | 是 | 运动模式（1=绝对位置，0x41=相对位置） |
| `position_mm` | float | 是 | 目标位置（毫米） |
| `velocity_mm_s` | float | 是 | 运动速度 |
| `accel_time` | integer | 否 | 加速时间（毫秒） |
| `decel_time` | integer | 否 | 减速时间（毫秒） |
| `dwell_time` | integer | 否 | 停顿时间（毫秒） |

**响应示例**：

```json
{
  "success": true,
  "message": "PR路径 0 已配置"
}
```

### 触发PR路径

```http
POST /api/v1/motor/pr/trigger
Content-Type: application/json

{
  "path_number": 0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `path_number` | integer | 是 | 路径编号（0-15） |

### RS232专用通信模式

**设置串口通信模式**：

```http
POST /api/v1/motor/serial_mode
Content-Type: application/json

{
  "mode": "rs232",
  "port": "COM3"
}
```

**响应示例**：

```json
{
  "success": true,
  "message": "已切换到RS232模式并连接到 COM3"
}
```

**RS232模式默认设置**：
- 波特率：9600
- 从站地址：1
- 数据位：8位
- 校验位：无
- 停止位：1位

### 在线修改通信参数

**读取通信参数**：

```http
GET /api/v1/motor/communication/config
```

**响应示例**：

```json
{
  "baudrate": 38400,
  "slave_id": 1,
  "data_type": 4,
  "serial_mode": "rs485"
}
```

**修改通信参数**：

```http
POST /api/v1/motor/communication/config
Content-Type: application/json

{
  "baudrate": 115200,
  "slave_id": 2,
  "data_type": 4
}
```

**响应示例**：

```json
{
  "success": true,
  "baudrate": 115200,
  "slave_id": 2,
  "data_type": 4,
  "warnings": [
    "通信参数已修改，请调用 save_parameters() 保存到EEPROM，并重新上电使参数生效。"
  ],
  "errors": []
}
```

**数据类型代码对照表**：

| 代码 | 数据位 | 校验位 | 停止位 |
|------|--------|--------|--------|
| 0 | 8位 | 偶校验 | 2位 |
| 1 | 8位 | 奇校验 | 2位 |
| 2 | 8位 | 偶校验 | 1位 |
| 3 | 8位 | 奇校验 | 1位 |
| 4 | 8位 | 无校验 | 1位（默认） |
| 5 | 8位 | 无校验 | 2位 |

**注意**： 波特率只能在当前波特率为9600时在线修改。

### 驱动器软件限位

**读取驱动器软件限位**：

```http
GET /api/v1/motor/driver_soft_limit
```

**响应示例**：

```json
{
  "positive_limit": 160000,
  "negative_limit": -160000,
  "positive_limit_mm": 100.0,
  "negative_limit_mm": -100.0
}
```

**设置驱动器软件限位**：

```http
POST /api/v1/motor/driver_soft_limit
Content-Type: application/json

{
  "positive_limit_mm": 100.0,
  "negative_limit_mm": -100.0
}
```

**同步软件限位到驱动器**：

```http
POST /api/v1/motor/driver_soft_limit/sync
```

**注意**： 软件限位在回零时无效。修改后需要保存参数到EEPROM才能永久生效。

---

## 电磁铁控制 API

基础路径：`/api/v1/electromagnet`

### 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 获取电磁铁状态 |
| `/connect` | POST | 连接电磁铁 |
| `/disconnect` | POST | 断开电磁铁 |
| `/current` | POST | 设置电流 |
| `/field` | POST | 设置磁场 |
| `/scan` | POST | 启动扫描 |
| `/scan/validate` | POST | 验证扫描参数 |
| `/scan/stop` | POST | 停止扫描 |
| `/calibrate` | POST | 执行校准 |
| `/calibration` | GET/DELETE | 获取/清除校准数据 |
| `/calibration/validate` | POST | 验证校准数据 |
| `/emergency_stop` | POST | 急停 |
| `/reset_emergency` | POST | 复位急停 |
| `/reset_overcurrent` | POST | 复位过流保护 |

### 获取电磁铁状态

```http
GET /api/v1/electromagnet/status
```

**响应示例**：

```json
{
  "device_id": "electromagnet",
  "electromagnet_status": "ready",
  "current": 2.5,
  "field": 0.5,
  "max_current_limit": 10.0,
  "is_scanning": false,
  "connected": true
}
```

### 设置恒流模式电流值

```http
POST /api/v1/electromagnet/current
Content-Type: application/json

{
  "current": 2.5
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `current` | float | 是 | 目标电流（安培） |

**响应示例**：

```json
{
  "success": true,
  "message": "Current set to 2.5A (limit: 10.0A)"
}
```

### 设置目标磁场值

```http
POST /api/v1/electromagnet/field
Content-Type: application/json

{
  "current": 0.5
}
```

**注意**： 此端点使用 current 字段传递磁场值（T）。

### 启动扫描模式

```http
POST /api/v1/electromagnet/scan
Content-Type: application/json

{
  "mode": "triangular",
  "start_current": 0.0,
  "end_current": 5.0,
  "scan_rate": 0.1,
  "cycles": 3,
  "step_interval_ms": 100
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | string | 是 | 扫描模式（forward/reverse/triangular） |
| `start_current` | float | 是 | 起始电流（安培） |
| `end_current` | float | 是 | 结束电流（安培） |
| `scan_rate` | float | 是 | 扫描速率（安培/秒） |
| `cycles` | integer | 否 | 扫描周期数，默认1 |
| `step_interval_ms` | integer | 否 | 步进间隔（毫秒） |

**响应示例**：

```json
{
  "success": true,
  "message": "Scan started: triangular mode, 0.0A -> 5.0A (limit: 10.0A)"
}
```

### 预验证扫描参数

```http
POST /api/v1/electromagnet/scan/validate
Content-Type: application/json

{
  "mode": "triangular",
  "start_current": 0.0,
  "end_current": 5.0,
  "scan_rate": 0.1,
  "cycles": 3
}
```

**响应示例**：

```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "End current 5.0A is close to limit 10.0A"
  ],
  "estimated_duration_s": 300.0
}
```

### 执行磁场-电流校准

```http
POST /api/v1/electromagnet/calibrate
Content-Type: application/json

{
  "calibration_points": [
    {"current": 0.0, "field": 0.0},
    {"current": 1.0, "field": 0.2},
    {"current": 2.0, "field": 0.4},
    {"current": 5.0, "field": 1.0}
  ]
}
```

**响应示例**：

```json
{
  "success": true,
  "message": "Calibration completed with 4 points"
}
```

---

## 温度控制 API

基础路径：`/api/v1/temperature`

### 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 获取温度状态 |
| `/connect` | POST | 连接温度控制器 |
| `/disconnect` | POST | 断开温度控制器 |
| `/setpoint` | POST | 设置温度设定点 |
| `/pid` | GET/POST | 获取/设置PID参数 |
| `/pid/validate` | POST | 验证PID参数 |
| `/pid/start` | POST | 启动PID控制 |
| `/pid/stop` | POST | 停止PID控制 |
| `/program` | POST | 配置温度程序 |
| `/program/stop` | POST | 停止温度程序 |
| `/protection` | POST | 设置保护限值 |
| `/protection/clear` | POST | 清除保护状态 |
| `/history` | POST | 获取温度历史记录 |
| `/history/clear` | POST | 清除温度历史记录 |
| `/history/export` | GET | 导出温度历史记录 |
| `/emergency_stop` | POST | 紧急停止 |
| `/reset` | POST | 复位急停状态 |

### 获取温度状态

```http
GET /api/v1/temperature/status
```

**响应示例**：

```json
{
  "device_id": "temperature_controller",
  "status": "ready",
  "current_temperature": 298.15,
  "target_temperature": 300.0,
  "heater_power": 25.5,
  "pid_enabled": true,
  "program_running": false,
  "program_segment": 0,
  "protection_active": false,
  "protection_type": null,
  "connected": true,
  "simulation": false
}
```

**温度单位说明**： 所有温度值均使用开尔文（K）单位。

### 设置温度设定点

```http
POST /api/v1/temperature/setpoint
Content-Type: application/json

{
  "temperature": 300.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `temperature` | float | 是 | 目标温度（开尔文），范围：77K-400K |

**响应示例**：

```json
{
  "success": true,
  "message": "Setpoint set to 300.0K (26.9°C)"
}
```

### 设置PID参数

```http
POST /api/v1/temperature/pid
Content-Type: application/json

{
  "kp": 10.0,
  "ki": 0.5,
  "kd": 1.0,
  "setpoint": 300.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `kp` | float | 是 | 比例增益，范围：0.1-100 |
| `ki` | float | 是 | 积分增益，范围：0.001-10 |
| `kd` | float | 是 | 微分增益，范围：0.001-10 |
| `setpoint` | float | 是 | 设定点（开尔文） |

**响应示例**：

```json
{
  "success": true,
  "message": "PID parameters updated: Kp=10.0, Ki=0.5, Kd=1.0, setpoint=300.0K"
}
```

### 验证PID参数

```http
POST /api/v1/temperature/pid/validate
Content-Type: application/json

{
  "kp": 50.0,
  "ki": 5.0,
  "kd": 1.0,
  "setpoint": 300.0
}
```

**响应示例**：

```json
{
  "valid": true,
  "errors": [],
  "warnings": [
    "Kp=50.0 较大，可能导致系统震荡",
    "Ki=5.0 较大，可能导致积分饱和",
    "Kp和Ki同时较大，建议降低其中之一以避免超调"
  ],
  "parameters": {
    "kp": 50.0,
    "ki": 5.0,
    "kd": 1.0,
    "setpoint_k": 300.0,
    "setpoint_c": 26.85
  }
}
```

### 配置温度程序

```http
POST /api/v1/temperature/program
Content-Type: application/json

{
  "segments": [
    {
      "target_temperature": 300.0,
      "ramp_rate": 5.0,
      "hold_time": 600
    },
    {
      "target_temperature": 350.0,
      "ramp_rate": 2.0,
      "hold_time": 1200
    }
  ]
}
```

**程序段参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `target_temperature` | float | 是 | 目标温度（开尔文） |
| `ramp_rate` | float | 是 | 升降温速率（K/min） |
| `hold_time` | integer | 是 | 保持时间（秒） |

**响应示例**：

```json
{
  "success": true,
  "message": "Temperature program started with 2 segments"
}
```

### 设置保护限值

```http
POST /api/v1/temperature/protection
Content-Type: application/json

{
  "max_temperature": 400.0,
  "min_temperature": 77.0,
  "max_deviation": 10.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `max_temperature` | float | 是 | 最高温度限制（开尔文） |
| `min_temperature` | float | 是 | 最低温度限制（开尔文） |
| `max_deviation` | float | 是 | 最大偏差限制（开尔文） |

### 获取温度历史记录

```http
POST /api/v1/temperature/history
Content-Type: application/json

{
  "duration_seconds": 3600
}
```

**响应示例**：

```json
{
  "success": true,
  "message": "Retrieved 3600 records",
  "timestamps": ["2026-03-15T10:00:00.000Z", "2026-03-15T10:00:01.000Z"],
  "temperatures": [298.15, 298.16],
  "setpoints": [300.0, 300.0]
}
```

---

## 压电控制 API

基础路径：`/api/v1/piezo`

### 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 获取压电状态 |
| `/connect` | POST | 连接压电控制器 |
| `/disconnect` | POST | 断开压电控制器 |
| `/voltage` | GET/POST | 获取/设置电压值 |
| `/displacement` | GET/POST | 获取/设置位移值 |
| `/mode` | GET/POST | 获取/设置控制模式 |
| `/calibrate/point` | POST | 添加校准点 |
| `/calibrate/perform` | POST | 执行校准拟合 |
| `/calibrate/data` | GET | 获取校准数据 |
| `/calibrate` | DELETE | 清除校准数据 |
| `/zero` | POST | 归零操作 |
| `/max_extend` | POST | 最大伸展操作 |

### 获取压电状态

```http
GET /api/v1/piezo/status
```

**响应示例**：

```json
{
  "device_id": "piezo",
  "status": "ready",
  "current_voltage_v": 75.0,
  "current_displacement_um": 50.0,
  "control_mode": "open_loop",
  "calibrated": true,
  "connected": true
}
```

### 设置电压值

```http
POST /api/v1/piezo/voltage
Content-Type: application/json

{
  "voltage_v": 100.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `voltage_v` | float | 是 | 目标电压（伏特），范围：0-150V |

**响应示例**：

```json
{
  "success": true,
  "message": "Voltage set to 100.000V",
  "current_voltage_v": 100.0,
  "current_displacement_um": 66.67
}
```

### 设置位移值

```http
POST /api/v1/piezo/displacement
Content-Type: application/json

{
  "displacement_um": 50.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `displacement_um` | float | 是 | 目标位移（微米），范围：0-100μm |

**响应示例**：

```json
{
  "success": true,
  "message": "Displacement set to 50.000μm",
  "current_displacement_um": 50.0,
  "current_voltage_v": 75.0
}
```

### 设置控制模式

```http
POST /api/v1/piezo/mode
Content-Type: application/json

{
  "mode": "closed_loop"
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `mode` | string | 是 | 控制模式（open_loop/closed_loop） |

### 添加校准点

```http
POST /api/v1/piezo/calibrate/point
Content-Type: application/json

{
  "voltage_v": 50.0,
  "displacement_um": 33.33
}
```

**响应示例**：

```json
{
  "success": true,
  "message": "Calibration point added: 50.000V -> 33.330μm",
  "point_count": 3
}
```

### 执行校准拟合

```http
POST /api/v1/piezo/calibrate/perform
Content-Type: application/json

{
  "calibration_type": "linear"
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `calibration_type` | string | 是 | 校准类型（linear/polynomial/piecewise） |

### 归零操作

```http
POST /api/v1/piezo/zero
```

---

## 皮安表 API

基础路径：`/api/v1/ammeter`

### 端点列表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/status` | GET | 获取皮安表状态 |
| `/start` | POST | 开始采集 |
| `/stop` | POST | 停止采集 |
| `/data` | GET | 获取采集数据 |
| `/channel/config` | POST | 配置通道参数 |
| `/clear_buffer` | POST | 清空数据缓冲区 |
| `/snr/{channel}` | GET | 获取指定通道信噪比 |

### 获取皮安表状态

```http
GET /api/v1/ammeter/status
```

**响应示例**：

```json
{
  "device_id": "picoammeter",
  "status": "ready",
  "is_acquiring": true,
  "sample_rate": 100,
  "channels": [
    {
      "channel": 0,
      "enabled": true,
      "current_range": "1uA",
      "filter_type": "lowpass"
    }
  ],
  "connected": true
}
```

### 开始采集

```http
POST /api/v1/ammeter/start
Content-Type: application/json

{
  "sample_rate": 100
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `sample_rate` | integer | 否 | 采样率（Hz） |

**响应示例**：

```json
{
  "success": true,
  "message": "Acquisition started at 100Hz"
}
```

### 停止采集

```http
POST /api/v1/ammeter/stop
```

### 获取采集数据

```http
GET /api/v1/ammeter/data?channel=0&count=100
```

**查询参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `channel` | integer | 否 | 通道号（0-3），不指定则获取所有通道 |
| `count` | integer | 否 | 获取数据点数量，不指定则仅获取最新数据 |

**响应示例**：

```json
{
  "success": true,
  "message": "Retrieved 100 data points",
  "is_acquiring": true,
  "data": [
    {
      "channel": 0,
      "current_pa": 123.45,
      "timestamp": "2026-03-15T10:30:00.000Z",
      "snr_db": 45.2,
      "raw_current_pa": 125.0,
      "noise_rms_pa": 0.5,
      "signal_rms_pa": 120.0
    }
  ]
}
```

### 配置通道参数

```http
POST /api/v1/ammeter/channel/config
Content-Type: application/json

{
  "channel": 0,
  "enabled": true,
  "current_range": "1uA",
  "filter_type": "lowpass",
  "filter_cutoff": 10.0,
  "offset": 0.0
}
```

**请求参数**：

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `channel` | integer | 是 | 通道号（0-3） |
| `enabled` | boolean | 否 | 是否启用 |
| `current_range` | string | 否 | 电流量程（1nA/10nA/100nA/1uA/10uA） |
| `filter_type` | string | 否 | 滤波类型（lowpass/highpass/bandpass/none） |
| `filter_cutoff` | float | 否 | 滤波截止频率（Hz） |
| `offset` | float | 否 | 偏移校准值（pA） |

### 获取信噪比

```http
GET /api/v1/ammeter/snr/0?window_size=100
```

**响应示例**：

```json
{
  "success": true,
  "channel": 0,
  "snr_db": 45.2,
  "window_size": 100
}
```

---

## 错误码说明

### 设备错误码

| 错误码 | 说明 |
|--------|------|
| `DEVICE_NOT_INITIALIZED` | 设备未初始化 |
| `DEVICE_NOT_CONNECTED` | 设备未连接 |
| `DEVICE_IN_EMERGENCY_STOP` | 设备处于急停状态 |
| `DEVICE_ERROR` | 设备错误 |
| `DEVICE_BUSY` | 设备忙 |
| `SOFT_LIMIT_EXCEEDED` | 超出软件限位 |
| `INVALID_PARAMETER` | 参数无效 |
| `PARAM_OUT_OF_RANGE` | 参数超出范围 |

### 通信错误码

| 错误码 | 说明 |
|--------|------|
| `COMMUNICATION_ERROR` | 通信错误 |
| `TIMEOUT_ERROR` | 超时错误 |
| `MODBUS_ERROR` | Modbus通信错误 |

### 安全错误码

| 错误码 | 说明 |
|--------|------|
| `OVERCURRENT_PROTECTION` | 过流保护触发 |
| `OVERTEMPERATURE_PROTECTION` | 过温保护触发 |
| `EMERGENCY_STOP_ACTIVE` | 急停激活 |

---

## WebSocket 实时数据

### 端点列表

| 端点 | 说明 | 推送频率 |
|------|------|----------|
| `/ws/motor` | 电机实时数据 | 100ms |
| `/ws/electromagnet` | 电磁铁实时数据 | 100ms |
| `/ws/temperature` | 温度实时数据 | 500ms |
| `/ws/piezo` | 压电实时数据 | 100ms |
| `/ws/ammeter` | 皮安表实时数据 | 50ms |
| `/ws/devices` | 所有设备状态 | 200ms |

### 统一 WebSocket 端点

```
/ws
```

**支持的消息类型**：
- `device_status` - 设备状态推送
- `waveform_data` - 波形数据推送
- `alarm_event` - 报警事件推送
- `experiment_progress` - 实验进度推送
- `ping/pong` - 心跳检测

---

## 相关文档

- [数据分析 API](./数据分析API.md)
- [用户管理 API](./用户管理API.md)
- [系统监控 API](./系统监控API.md)
- [REST-API设计](../06-通信协议/REST-API设计.md)
