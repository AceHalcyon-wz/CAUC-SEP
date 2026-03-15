# WebSocket 协议

**版本**: v1.0  
**创建日期**: 2026-03-15  
**最后更新**: 2026-03-15  
**适用范围**: 前后端实时通信

---

## 概述

CAUC-SEP自旋电子器件实验平台采用WebSocket协议实现前后端实时数据通信。WebSocket提供全双工通信能力，支持服务器主动推送设备状态、波形数据、报警事件等实时信息。

### 协议特点

- **全双工通信**: 服务端可主动推送数据
- **低延迟**: 相比HTTP轮询，延迟更低
- **高效传输**: 支持JSON和MessagePack两种格式
- **反压控制**: 防止客户端缓冲区溢出
- **心跳检测**: 自动检测连接状态

---

## 连接管理

### 连接端点

| 端点 | 说明 |
|------|------|
| `/ws/motor` | 步进电机状态推送 |
| `/ws/electromagnet` | 电磁铁状态推送 |
| `/ws/temperature` | 温控系统状态推送 |
| `/ws/piezo` | 压电陶瓷状态推送 |
| `/ws/ammeter` | 微电流计状态推送 |
| `/ws/all` | 所有设备状态推送 |

### 连接参数

通过查询参数配置连接选项：

```
ws://localhost:8000/ws/motor?protocol=msgpack&ack=true
```

| 参数 | 值 | 说明 |
|------|-----|------|
| `protocol` | `json`（默认） | JSON文本协议 |
| `protocol` | `msgpack` | MessagePack二进制协议 |
| `ack` | `true`/`false` | 是否启用消息确认机制 |

### 连接生命周期

```
+----------+     +----------+     +----------+
|  连接建立  | --> |  数据传输  | --> |  连接关闭  |
+----------+     +----------+     +----------+
     |                |                |
     v                v                v
  协议协商         心跳检测         资源清理
  订阅管理         反压控制         统计记录
```

---

## 消息格式定义

### 消息类型枚举

| 类型 | 名称 | 说明 |
|------|------|------|
| `device_status` | 设备状态 | 设备状态推送 |
| `waveform_data` | 波形数据 | 实时波形数据推送 |
| `alarm_event` | 报警事件 | 报警事件推送 |
| `experiment_progress` | 实验进度 | 实验进度推送 |
| `ping` | 心跳请求 | 服务端心跳请求 |
| `pong` | 心跳响应 | 客户端心跳响应 |
| `msg_ack` | 消息确认 | 消息确认响应 |
| `backpressure_warning` | 反压警告 | 反压状态警告 |
| `flow_control` | 流量控制 | 流量控制通知 |

### 设备状态消息

```json
{
    "type": "device_status",
    "timestamp": "2026-03-15T10:30:00.000Z",
    "data": {
        "device_id": "stepper_01",
        "device_type": "stepper",
        "status": "ready",
        "connected": true,
        "simulation": false,
        "position_mm": 10.5,
        "alarm_code": 0
    }
}
```

### 波形数据消息

```json
{
    "type": "waveform_data",
    "timestamp": "2026-03-15T10:30:00.000Z",
    "data": {
        "device_id": "picoammeter_01",
        "device_type": "ammeter",
        "sample_rate": 100.0,
        "data_points": [
            {
                "channel": 0,
                "value": 1.5e-9,
                "timestamp": 1234567890.0
            },
            {
                "channel": 1,
                "value": 2.3e-9,
                "timestamp": 1234567890.0
            }
        ]
    }
}
```

### 报警事件消息

```json
{
    "type": "alarm_event",
    "timestamp": "2026-03-15T10:30:00.000Z",
    "data": {
        "device_id": "temp_01",
        "device_type": "temperature",
        "alarm_level": "warning",
        "alarm_code": "HIGH_TEMP",
        "alarm_message": "温度超过安全阈值",
        "alarm_time": "2026-03-15T10:30:00.000Z",
        "recoverable": true
    }
}
```

### 实验进度消息

```json
{
    "type": "experiment_progress",
    "timestamp": "2026-03-15T10:30:00.000Z",
    "data": {
        "experiment_id": 1,
        "experiment_name": "磁场扫描实验",
        "progress": 0.5,
        "current_step": 5,
        "total_steps": 10,
        "elapsed_time": 300.0,
        "estimated_remaining": 300.0,
        "status": "running"
    }
}
```

---

## 心跳机制

### 心跳配置

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 心跳间隔 | 10秒 | 服务端发送ping间隔 |
| 心跳超时 | 30秒 | 无响应超时时间 |

### 心跳流程

```
服务端                              客户端
   |                                   |
   |-------- ping --------->          |
   |                                   |
   |          <-------- pong --------|
   |                                   |
```

### 心跳请求消息

```json
{
    "type": "ping",
    "timestamp": "2026-03-15T10:30:00.000Z"
}
```

### 心跳响应消息

```json
{
    "type": "pong",
    "timestamp": "2026-03-15T10:30:00.000Z"
}
```

### 超时处理

当客户端超过30秒未响应心跳，服务端将主动断开连接：

```python
async def _heartbeat_monitor(self, websocket: WebSocket) -> None:
    """心跳监控任务。"""
    while websocket in self._active_connections:
        await asyncio.sleep(HEARTBEAT_INTERVAL)

        time_since_last_msg = time.time() - connection_info.last_message_time

        if time_since_last_msg > HEARTBEAT_TIMEOUT:
            logger.warning(f"Heartbeat timeout ({time_since_last_msg:.1f}s)")
            await self._close_connection(websocket, reason="heartbeat_timeout")
            break
```

---

## 实时数据推送

### 推送频率控制

| 设备类型 | 默认间隔 | 说明 |
|----------|----------|------|
| stepper | 100ms | 步进电机 |
| electromagnet | 100ms | 电磁铁 |
| temperature | 500ms | 温控系统 |
| piezo | 100ms | 压电陶瓷 |
| ammeter | 100ms | 微电流计 |
| all_devices | 200ms | 统一设备 |

### 客户端频率控制

客户端可发送控制消息调整推送频率：

```json
{
    "type": "frequency_update",
    "mode": "slow",
    "interval": 500
}
```

| 模式 | 说明 |
|------|------|
| `fast` | 快速模式，100ms间隔 |
| `normal` | 正常模式，200ms间隔 |
| `slow` | 慢速模式，500ms间隔 |

### 订阅机制

客户端可订阅特定消息类型：

```json
{
    "action": "subscribe",
    "types": ["device_status", "alarm_event"]
}
```

订阅确认响应：

```json
{
    "type": "subscription_confirmed",
    "timestamp": "2026-03-15T10:30:00.000Z",
    "subscribed_types": ["device_status", "alarm_event"]
}
```

取消订阅：

```json
{
    "action": "unsubscribe",
    "types": ["waveform_data"]
}
```

---

## 反压控制机制

### 概述

反压控制机制用于防止客户端缓冲区溢出，确保在高频数据传输场景下的系统稳定性。

### 配置参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 队列大小 | 100条 | 每个客户端的消息队列容量 |
| 高水位线 | 0.8 | 队列使用率80%时启动节流 |
| 低水位线 | 0.5 | 队列使用率50%时恢复正常 |
| 节流延迟 | 50ms | 节流状态下的发送延迟 |

### 水位线控制

```
队列使用率
    |
1.0 |                    +-- 节流区域 --+
    |                    |              |
0.8 |-------- 高水位线 --+              |
    |                    |              |
    |                    |              |
0.5 |-------- 低水位线 --+-- 正常区域 --+
    |
0.0 +-----------------------------------> 时间
```

### 反压警告消息

当队列使用率超过高水位线时，服务端发送警告：

```json
{
    "type": "backpressure_warning",
    "timestamp": "2026-03-15T10:30:00.000Z",
    "data": {
        "queue_usage": 0.85,
        "is_throttled": true,
        "queue_size": 100,
        "queued_messages": 85,
        "total_messages_sent": 1500,
        "total_messages_dropped": 5,
        "unacked_count": 3,
        "ack_enabled": true
    }
}
```

### 流量恢复消息

当队列使用率降低到低水位线以下时：

```json
{
    "type": "flow_control",
    "timestamp": "2026-03-15T10:30:05.000Z",
    "data": {
        "status": "resumed",
        "message": "Flow control status changed to resumed"
    }
}
```

---

## 消息确认机制

### 启用确认机制

连接时通过查询参数启用：

```
ws://localhost:8000/ws/motor?ack=true
```

### 工作流程

```
服务端                              客户端
   |                                   |
   |--- message (with message_id) --->|
   |                                   |
   |          <--- msg_ack -----------|
   |                                   |
```

### 确认参数

| 参数 | 默认值 | 说明 |
|------|--------|------|
| 确认超时 | 5秒 | 未确认消息超时时间 |
| 最大未确认数 | 10条 | 最大未确认消息数量 |

### 消息确认响应

```json
{
    "type": "msg_ack",
    "message_id": "abc123"
}
```

---

## 重连策略

### 客户端重连建议

```javascript
class WebSocketClient {
    constructor(url, options = {}) {
        this.url = url;
        this.maxRetries = options.maxRetries || 5;
        this.retryDelay = options.retryDelay || 1000;
        this.maxRetryDelay = options.maxRetryDelay || 30000;
        this.retryCount = 0;
    }

    connect() {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
            console.log('Connected');
            this.retryCount = 0;
            this.retryDelay = 1000;
        };

        this.ws.onclose = (event) => {
            console.log(`Disconnected: ${event.reason}`);
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    scheduleReconnect() {
        if (this.retryCount >= this.maxRetries) {
            console.error('Max retries reached');
            return;
        }

        const delay = Math.min(
            this.retryDelay * Math.pow(2, this.retryCount),
            this.maxRetryDelay
        );

        console.log(`Reconnecting in ${delay}ms...`);

        setTimeout(() => {
            this.retryCount++;
            this.connect();
        }, delay);
    }
}
```

### 指数退避算法

```
重连延迟 = min(base_delay * 2^retry_count, max_delay)

示例：
- 第1次重连: 1秒
- 第2次重连: 2秒
- 第3次重连: 4秒
- 第4次重连: 8秒
- 第5次重连: 16秒
- 最大延迟: 30秒
```

---

## 协议类型

### JSON协议

默认协议，兼容性好：

```json
{
    "type": "device_status",
    "timestamp": "2026-03-15T10:30:00.000Z",
    "data": {...}
}
```

### MessagePack协议

高性能二进制协议，适合高频数据传输：

**优势**:
- 序列化体积减少30-50%
- 序列化/反序列化速度提升2-5倍
- 适合波形数据等高频传输场景

**使用方式**:

```
ws://localhost:8000/ws/motor?protocol=msgpack
```

**Python示例**:

```python
import msgpack

# 序列化
data = {"type": "pong", "timestamp": "2026-03-15T10:30:00.000Z"}
binary_data = msgpack.packb(data, use_bin_type=True)

# 反序列化
decoded = msgpack.unpackb(binary_data, raw=False)
```

---

## 代码示例

### JavaScript客户端示例

```javascript
/**
 * WebSocket客户端类
 */
class DeviceWebSocket {
    /**
     * 创建WebSocket客户端
     * @param {string} endpoint - 端点路径
     * @param {Object} options - 配置选项
     */
    constructor(endpoint, options = {}) {
        this.url = `ws://${window.location.host}${endpoint}`;
        this.protocol = options.protocol || 'json';
        this.ackEnabled = options.ackEnabled || false;
        this.ws = null;
        this.handlers = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    /**
     * 建立连接
     */
    connect() {
        const params = new URLSearchParams({
            protocol: this.protocol,
            ack: this.ackEnabled.toString()
        });

        this.ws = new WebSocket(`${this.url}?${params}`);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
        };

        this.ws.onmessage = (event) => {
            this.handleMessage(event.data);
        };

        this.ws.onclose = (event) => {
            console.log(`Disconnected: ${event.reason}`);
            this.scheduleReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };
    }

    /**
     * 处理消息
     * @param {string|ArrayBuffer} data - 消息数据
     */
    handleMessage(data) {
        let message;

        if (this.protocol === 'msgpack' && data instanceof ArrayBuffer) {
            message = msgpack.decode(new Uint8Array(data));
        } else {
            message = JSON.parse(data);
        }

        // 处理心跳
        if (message.type === 'ping') {
            this.send({ type: 'pong', timestamp: new Date().toISOString() });
            return;
        }

        // 处理消息确认
        if (message.message_id && this.ackEnabled) {
            this.send({ type: 'msg_ack', message_id: message.message_id });
        }

        // 调用注册的处理器
        const handler = this.handlers.get(message.type);
        if (handler) {
            handler(message.data);
        }
    }

    /**
     * 发送消息
     * @param {Object} data - 消息数据
     */
    send(data) {
        if (this.ws.readyState === WebSocket.OPEN) {
            if (this.protocol === 'msgpack') {
                const encoded = msgpack.encode(data);
                this.ws.send(encoded);
            } else {
                this.ws.send(JSON.stringify(data));
            }
        }
    }

    /**
     * 订阅消息类型
     * @param {string} type - 消息类型
     * @param {Function} handler - 处理函数
     */
    on(type, handler) {
        this.handlers.set(type, handler);
    }

    /**
     * 订阅特定消息类型
     * @param {string[]} types - 消息类型列表
     */
    subscribe(types) {
        this.send({ action: 'subscribe', types });
    }

    /**
     * 计划重连
     */
    scheduleReconnect() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnect attempts reached');
            return;
        }

        const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);

        setTimeout(() => {
            this.reconnectAttempts++;
            this.connect();
        }, delay);
    }
}

// 使用示例
const client = new DeviceWebSocket('/ws/motor', { protocol: 'json' });

client.on('device_status', (data) => {
    console.log('Device status:', data);
    updateUI(data);
});

client.on('alarm_event', (data) => {
    console.log('Alarm:', data);
    showAlarmNotification(data);
});

client.connect();
```

### Python客户端示例

```python
import asyncio
import json
import logging
from typing import Callable

import websockets

logger = logging.getLogger(__name__)


class WebSocketClient:
    """
    WebSocket客户端。

    支持JSON和MessagePack协议，自动重连，心跳检测。

    Example:
        >>> client = WebSocketClient("ws://localhost:8000/ws/motor")
        >>> client.on("device_status", handle_status)
        >>> await client.connect()
    """

    def __init__(
        self,
        url: str,
        protocol: str = "json",
        ack_enabled: bool = False,
    ):
        """
        初始化WebSocket客户端。

        Args:
            url: WebSocket URL
            protocol: 协议类型（json/msgpack）
            ack_enabled: 是否启用消息确认
        """
        self.url = url
        self.protocol = protocol
        self.ack_enabled = ack_enabled
        self.ws = None
        self.handlers: dict[str, Callable] = {}
        self._running = False

    async def connect(self) -> None:
        """建立WebSocket连接。"""
        params = f"?protocol={self.protocol}&ack={str(self.ack_enabled).lower()}"
        self.ws = await websockets.connect(self.url + params)
        self._running = True

        logger.info(f"Connected to {self.url}")

        # 启动消息接收循环
        await self._receive_loop()

    async def _receive_loop(self) -> None:
        """消息接收循环。"""
        try:
            async for message in self.ws:
                await self._handle_message(message)
        except websockets.ConnectionClosed as e:
            logger.warning(f"Connection closed: {e}")
            self._running = False

    async def _handle_message(self, message: str | bytes) -> None:
        """
        处理接收到的消息。

        Args:
            message: 消息内容
        """
        # 解析消息
        if isinstance(message, bytes) and self.protocol == "msgpack":
            import msgpack
            data = msgpack.unpackb(message, raw=False)
        else:
            data = json.loads(message)

        msg_type = data.get("type")

        # 处理心跳
        if msg_type == "ping":
            await self.send({"type": "pong", "timestamp": data["timestamp"]})
            return

        # 处理消息确认
        if data.get("message_id") and self.ack_enabled:
            await self.send({"type": "msg_ack", "message_id": data["message_id"]})

        # 调用处理器
        handler = self.handlers.get(msg_type)
        if handler:
            await handler(data.get("data", data))

    async def send(self, data: dict) -> None:
        """
        发送消息。

        Args:
            data: 消息数据
        """
        if self.ws and self._running:
            if self.protocol == "msgpack":
                import msgpack
                await self.ws.send(msgpack.packb(data, use_bin_type=True))
            else:
                await self.ws.send(json.dumps(data))

    def on(self, msg_type: str, handler: Callable) -> None:
        """
        注册消息处理器。

        Args:
            msg_type: 消息类型
            handler: 处理函数
        """
        self.handlers[msg_type] = handler

    async def subscribe(self, types: list[str]) -> None:
        """
        订阅消息类型。

        Args:
            types: 消息类型列表
        """
        await self.send({"action": "subscribe", "types": types})

    async def close(self) -> None:
        """关闭连接。"""
        self._running = False
        if self.ws:
            await self.ws.close()


# 使用示例
async def main():
    client = WebSocketClient("ws://localhost:8000/ws/motor")

    async def handle_status(data):
        print(f"Device status: {data}")

    async def handle_alarm(data):
        print(f"Alarm: {data}")

    client.on("device_status", handle_status)
    client.on("alarm_event", handle_alarm)

    await client.connect()


if __name__ == "__main__":
    asyncio.run(main())
```

---

## 通信故障排除指南

### 常见问题诊断

#### 1. 连接失败

**症状**: 无法建立WebSocket连接

**排查步骤**:

1. 检查服务端是否启动
2. 确认端点路径正确
3. 检查防火墙设置
4. 查看浏览器控制台错误

**解决方案**:

```javascript
// 检查连接状态
const ws = new WebSocket(url);
ws.onerror = (error) => {
    console.error('Connection error:', error);
};
```

#### 2. 频繁断开重连

**症状**: 连接不稳定，频繁断开

**排查步骤**:

1. 检查网络稳定性
2. 确认心跳响应正常
3. 查看服务端日志
4. 检查反压状态

**解决方案**:

```javascript
// 增加心跳超时时间
const client = new DeviceWebSocket('/ws/motor');
client.heartbeatTimeout = 60000; // 60秒
```

#### 3. 消息丢失

**症状**: 部分消息未收到

**排查步骤**:

1. 检查是否触发反压
2. 确认订阅了正确的消息类型
3. 查看丢弃消息统计

**解决方案**:

```javascript
// 监听反压警告
client.on('backpressure_warning', (data) => {
    console.warn('Backpressure detected:', data);
    // 降低处理频率或启用消息确认
});
```

#### 4. 高延迟

**症状**: 消息接收延迟明显

**排查步骤**:

1. 检查网络延迟
2. 确认服务端负载
3. 查看队列积压情况

**解决方案**:

```javascript
// 使用MessagePack协议减少传输时间
const client = new DeviceWebSocket('/ws/motor', { protocol: 'msgpack' });
```

### 性能监控

```javascript
// 监控连接统计
class WebSocketMonitor {
    constructor(client) {
        this.client = client;
        this.stats = {
            messagesReceived: 0,
            messagesSent: 0,
            reconnectCount: 0,
            lastLatency: 0,
        };
    }

    start() {
        this.client.on('device_status', () => {
            this.stats.messagesReceived++;
        });

        // 定期打印统计
        setInterval(() => {
            console.log('WebSocket Stats:', this.stats);
        }, 10000);
    }
}
```

---

## 参考资料

- WebSocket RFC 6455
- MessagePack规范
- Reactive Streams规范（反压控制参考）

---

## 更新日志

### v1.0 (2026-03-15)
- 初始版本
- 完整的消息格式定义
- 心跳机制说明
- 反压控制机制
- 消息确认机制
- 重连策略
- 代码示例
- 故障排除指南
