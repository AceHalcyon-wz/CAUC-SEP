"""
MessagePack协议使用指南

本文档演示如何在WebSocket通信中使用MessagePack协议。

作者：Backend Engineer Agent
创建日期：2026-03-07
"""

# ============================================================================
# 1. 协议协商机制
# ============================================================================

"""
客户端可以通过WebSocket连接URL的查询参数指定协议类型：

# 使用JSON协议（默认）
ws://localhost:8000/ws/motor

# 使用MessagePack协议
ws://localhost:8000/ws/motor?protocol=msgpack

# 协议参数大小写不敏感
ws://localhost:8000/ws/motor?protocol=MSGPACK
ws://localhost:8000/ws/motor?protocol=MsgPack
"""

# ============================================================================
# 2. 服务端使用示例
# ============================================================================

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from api.websocket import (
    ConnectionManager,
    DeviceType,
    ProtocolType,
    create_device_status_message,
    parse_protocol_from_query,
)

app = FastAPI()
manager = ConnectionManager()


@app.websocket("/ws/device")
async def websocket_device_endpoint(websocket: WebSocket):
    """
    WebSocket设备端点示例。

    支持协议协商：
    - 默认使用JSON协议
    - 客户端可通过查询参数指定MessagePack协议
    """
    # 解析协议类型
    query_params = dict(websocket.query_params)
    protocol = parse_protocol_from_query(query_params)

    # 建立连接
    connection_id = await manager.connect(
        websocket,
        endpoint="/ws/device",
        client_ip=websocket.client.host if websocket.client else "unknown",
        protocol=protocol,
    )

    try:
        while True:
            # 接收消息（支持JSON和MessagePack两种格式）
            # FastAPI的WebSocket会自动处理text和bytes
            try:
                # 尝试接收文本消息（JSON）
                data = await websocket.receive_text()
            except Exception:
                # 如果失败，尝试接收二进制消息（MessagePack）
                data = await websocket.receive_bytes()

            # 处理客户端消息
            is_control = await manager.handle_client_message(websocket, data)

            if not is_control:
                # 处理业务消息
                # ...
                pass

    except WebSocketDisconnect:
        manager.disconnect(websocket)


# ============================================================================
# 3. 客户端使用示例（JavaScript）
# ============================================================================

"""
// JavaScript客户端示例

// 3.1 使用JSON协议（默认）
const wsJson = new WebSocket('ws://localhost:8000/ws/device');

wsJson.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('Received JSON message:', message);
};

wsJson.send(JSON.stringify({
    type: 'ping',
    timestamp: new Date().toISOString()
}));


// 3.2 使用MessagePack协议
import msgpack from 'msgpack-lite';

const wsMsgpack = new WebSocket('ws://localhost:8000/ws/device?protocol=msgpack');
wsMsgpack.binaryType = 'arraybuffer';

wsMsgpack.onmessage = (event) => {
    const message = msgpack.decode(new Uint8Array(event.data));
    console.log('Received MessagePack message:', message);
};

// 发送MessagePack消息
const message = {
    type: 'ping',
    timestamp: new Date().toISOString()
};
wsMsgpack.send(msgpack.encode(message));


// 3.3 心跳响应示例
wsMsgpack.onmessage = (event) => {
    const message = msgpack.decode(new Uint8Array(event.data));
    
    if (message.type === 'ping') {
        // 响应心跳
        wsMsgpack.send(msgpack.encode({
            type: 'pong',
            timestamp: new Date().toISOString()
        }));
    }
};
"""

# ============================================================================
# 4. Python客户端示例
# ============================================================================

import asyncio
import json

import msgpack
import websockets


async def json_client():
    """JSON协议客户端示例。"""
    uri = "ws://localhost:8000/ws/device"

    async with websockets.connect(uri) as websocket:
        # 发送消息
        message = {"type": "ping", "timestamp": "2026-03-07T12:00:00"}
        await websocket.send(json.dumps(message))

        # 接收消息
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Received: {data}")


async def msgpack_client():
    """MessagePack协议客户端示例。"""
    uri = "ws://localhost:8000/ws/device?protocol=msgpack"

    async with websockets.connect(uri) as websocket:
        # 发送消息
        message = {"type": "ping", "timestamp": "2026-03-07T12:00:00"}
        await websocket.send(msgpack.packb(message, use_bin_type=True))

        # 接收消息
        response = await websocket.recv()
        data = msgpack.unpackb(response, raw=False)
        print(f"Received: {data}")


# ============================================================================
# 5. 性能对比
# ============================================================================

"""
MessagePack协议相比JSON协议的优势：

1. 体积优化
   - MessagePack体积比JSON小30-50%
   - 适合高频数据传输场景（如波形数据）
   - 降低网络带宽消耗

2. 性能提升
   - 序列化速度提升2-5倍
   - 反序列化速度提升2-5倍
   - 降低CPU使用率

3. 使用场景推荐
   - JSON协议：
     * 调试和开发阶段
     * 低频数据传输
     * 需要人类可读的场景
   
   - MessagePack协议：
     * 生产环境
     * 高频数据传输（波形数据、实时状态）
     * 大量数据批量传输
     * 网络带宽受限场景

4. 性能测试结果（示例）
   - 1000个数据点的波形数据：
     * JSON size: 45,678 bytes
     * MessagePack size: 28,901 bytes
     * Size reduction: 36.7%
   
   - 序列化性能（100次迭代）：
     * JSON: 0.1234s
     * MessagePack: 0.0456s
     * Speed improvement: 63.0%
"""

# ============================================================================
# 6. 向后兼容性
# ============================================================================

"""
系统完全向后兼容：

1. 默认协议
   - 不指定协议参数时，默认使用JSON协议
   - 现有客户端无需修改即可继续使用

2. 协议回退
   - 指定无效协议时，自动回退到JSON协议
   - 确保系统稳定性

3. 混合协议支持
   - 同一服务端同时支持JSON和MessagePack客户端
   - 根据连接时的协议协商自动选择格式
   - 不同协议的客户端可以共存

4. 迁移建议
   - 第一阶段：服务端升级，支持双协议
   - 第二阶段：新客户端使用MessagePack协议
   - 第三阶段：逐步迁移旧客户端（可选）
"""

# ============================================================================
# 7. 完整示例：设备状态推送
# ============================================================================


async def broadcast_device_status_example():
    """
    设备状态推送示例。

    演示如何向不同协议的客户端推送消息。
    """
    # 创建设备状态消息
    message = create_device_status_message(
        device_id="stepper_01",
        device_type=DeviceType.STEPPER,
        status="ready",
        position_mm=25.5,
        velocity_mm_s=5.0,
    )

    # 广播消息（自动适配每个客户端的协议）
    await manager.broadcast(message)

    # ConnectionManager会自动处理：
    # - JSON协议客户端：发送JSON文本
    # - MessagePack协议客户端：发送二进制数据


# ============================================================================
# 8. 错误处理
# ============================================================================


async def handle_client_message_example(websocket: WebSocket, data: str | bytes):
    """
    处理客户端消息示例。

    支持JSON和MessagePack两种格式的消息解析。
    """
    try:
        # ConnectionManager会自动识别消息格式
        is_control = await manager.handle_client_message(websocket, data)

        if is_control:
            # 心跳或订阅消息，已处理
            return

        # 业务消息处理
        # ...

    except (json.JSONDecodeError, msgpack.UnpackException) as e:
        # 消息格式错误
        print(f"Invalid message format: {e}")
    except Exception as e:
        # 其他错误
        print(f"Error handling message: {e}")


# ============================================================================
# 9. 监控和调试
# ============================================================================


def get_connection_stats():
    """
    获取连接统计信息。

    包含每个连接使用的协议类型。
    """
    stats = manager.get_connection_stats()

    print(f"Total connections: {stats['total_connections']}")

    for conn in stats["connections"]:
        print(
            f"Connection {conn['connection_id']}: "
            f"protocol={conn['protocol']}, "
            f"messages_sent={conn['messages_sent']}, "
            f"messages_received={conn['messages_received']}"
        )


# ============================================================================
# 10. 最佳实践
# ============================================================================

"""
1. 协议选择建议
   - 开发环境：使用JSON协议，便于调试
   - 生产环境：使用MessagePack协议，提升性能
   - 混合环境：根据客户端能力动态选择

2. 错误处理
   - 捕获JSONDecodeError和UnpackException
   - 记录错误日志，便于排查问题
   - 提供友好的错误提示

3. 性能优化
   - 高频数据使用MessagePack协议
   - 批量传输数据时使用MessagePack
   - 定期监控连接状态和性能指标

4. 安全考虑
   - 验证消息格式和内容
   - 限制消息大小，防止内存溢出
   - 实现消息频率限制，防止DoS攻击

5. 测试建议
   - 编写单元测试覆盖两种协议
   - 进行性能测试对比
   - 测试向后兼容性
"""
