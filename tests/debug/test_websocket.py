"""
测试WebSocket连接到后端的/ws/devices端点
"""
import asyncio
import websockets
import json


async def test_websocket():
    """测试WebSocket连接"""
    uri = "ws://127.0.0.1:8000/ws/devices"
    
    print(f"正在连接到: {uri}")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("✅ 连接成功！")
            
            # 发送ping消息
            ping_msg = {
                "type": "ping",
                "timestamp": "2024-03-14T00:00:00"
            }
            await websocket.send(json.dumps(ping_msg))
            print(f"✅ 发送ping: {ping_msg}")
            
            # 等待响应
            try:
                response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                print(f"✅ 收到响应: {response}")
            except asyncio.TimeoutError:
                print("⚠️  等待响应超时")
            
            print("✅ 测试完成")
            
    except Exception as e:
        print(f"❌ 连接失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_websocket())
