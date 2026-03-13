# CAUC-SEP 故障排除指南

<!--
文件名: troubleshooting.md
路径: docs/
功能: 故障排除指南，常见问题解决方案
版本: v1.1
项目版本: v0.3.0

作者: CAUC-SEP 开发团队
创建日期: 2024-03-01
最后更新: 2026-03-14
-->

**版本**: v1.1  
**更新日期**: 2026-03-14  
**应用版本**: 0.3.0

---

## 目录

1. [常见问题](#常见问题)
2. [错误代码参考](#错误代码参考)
3. [系统诊断](#系统诊断)
4. [性能问题排查](#性能问题排查)
5. [网络问题排查](#网络问题排查)
6. [设备问题排查](#设备问题排查)
7. [日志分析](#日志分析)

---

## 常见问题

### 后端服务

#### Q1: 服务启动失败 - 端口被占用

**错误信息**:
```
OSError: [Errno 10048] error while attempting to bind on address ('0.0.0.0', 8000)
```

**解决方案**:
```bash
# Windows - 查找占用端口的进程
netstat -ano | findstr :8000

# 结束进程（替换PID为实际进程ID）
taskkill /PID <PID> /F

# 或修改配置使用其他端口
python -m uvicorn main:app --port 8001
```

---

#### Q2: 数据库连接失败

**错误信息**:
```
sqlalchemy.exc.OperationalError: (sqlite3.OperationalError) unable to open database file
```

**解决方案**:
```bash
# 检查数据库文件路径
ls -la data/

# 创建数据目录
mkdir -p data

# 检查文件权限
chmod 755 data/

# 如果数据库损坏，重新初始化
rm data/cauc_sep.db
python scripts/init_db.py
```

---

#### Q3: 依赖安装失败

**错误信息**:
```
ERROR: Could not find a version that satisfies the requirement xxx
```

**解决方案**:
```bash
# 更新pip
python -m pip install --upgrade pip

# 使用国内镜像源
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple

# 清除缓存重新安装
pip cache purge
pip install -r requirements.txt --no-cache-dir
```

---

### 前端服务

#### Q4: npm install 失败

**错误信息**:
```
npm ERR! network request to https://registry.npmjs.org/xxx failed
```

**解决方案**:
```bash
# 使用国内镜像源
npm config set registry https://registry.npmmirror.com

# 清除缓存
npm cache clean --force

# 删除node_modules重新安装
rm -rf node_modules package-lock.json
npm install
```

---

#### Q5: Vite 构建失败

**错误信息**:
```
Error: ENOENT: no such file or directory, open 'xxx'
```

**解决方案**:
```bash
# 清除构建缓存
rm -rf node_modules/.vite

# 检查文件是否存在
ls -la src/

# 重新启动开发服务器
npm run dev -- --force
```

---

#### Q6: WebSocket 连接失败

**错误信息**:
```
WebSocket connection to 'ws://localhost:8000/ws' failed
```

**解决方案**:
```javascript
// 检查后端服务是否运行
fetch('http://localhost:8000/api/health')
  .then(r => console.log('后端服务正常'))
  .catch(e => console.error('后端服务未启动'))

// 检查WebSocket URL配置
const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000/ws'

// 检查代理配置 (vite.config.js)
export default defineConfig({
  server: {
    proxy: {
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
    }
  }
})
```

---

### 设备通信

#### Q7: 步进电机无响应

**症状**: 发送命令后设备无反应

**排查步骤**:
```bash
# 1. 检查设备连接状态
curl http://localhost:8000/api/devices/status

# 2. 检查串口连接
# Windows
mode
# Linux
ls -la /dev/ttyUSB* /dev/ttyACM*

# 3. 检查设备日志
tail -f logs/device.log

# 4. 重启设备服务
curl -X POST http://localhost:8000/api/devices/stepper_01/restart
```

**解决方案**:
- 检查物理连接（USB线、电源）
- 确认设备驱动已安装
- 检查波特率配置是否正确
- 尝试重新插拔设备

---

#### Q8: 电磁铁控制异常

**症状**: 电磁铁无法正常吸合/释放

**排查步骤**:
```bash
# 检查GPIO状态
curl http://localhost:8000/api/devices/electromagnet_01/status

# 手动测试
curl -X POST http://localhost:8000/api/devices/electromagnet_01/command \
  -H "Content-Type: application/json" \
  -d '{"action": "activate"}'
```

**解决方案**:
- 检查电源电压是否正常
- 确认GPIO引脚配置正确
- 检查电磁铁是否过热保护
- 验证控制信号电平

---

## 错误代码参考

### HTTP 状态码

| 状态码 | 说明 | 常见原因 |
|--------|------|----------|
| 400 | 请求参数错误 | 参数格式不正确、缺少必填参数 |
| 401 | 未授权 | Token过期、未登录 |
| 403 | 禁止访问 | 权限不足、IP被封禁 |
| 404 | 资源不存在 | URL错误、资源已删除 |
| 409 | 资源冲突 | 重复创建、版本冲突 |
| 422 | 验证失败 | 数据验证不通过 |
| 429 | 请求过多 | 触发限流 |
| 500 | 服务器错误 | 代码异常、配置错误 |
| 502 | 网关错误 | 上游服务不可用 |
| 503 | 服务不可用 | 服务过载、维护中 |

### 业务错误码

| 错误码 | 说明 | 解决方案 |
|--------|------|----------|
| E001 | 设备未连接 | 检查设备物理连接 |
| E002 | 设备通信超时 | 检查通信线路、重试 |
| E003 | 设备响应错误 | 检查设备状态、重启设备 |
| E004 | 命令执行失败 | 检查命令参数、设备状态 |
| E101 | 任务不存在 | 检查任务ID是否正确 |
| E102 | 任务已取消 | 任务已被用户取消 |
| E103 | 任务执行超时 | 增加超时时间或优化任务 |
| E201 | 文件不存在 | 检查文件路径 |
| E202 | 文件格式错误 | 验证文件格式 |
| E203 | 文件过大 | 压缩文件或分块上传 |
| E301 | 参数验证失败 | 检查参数格式和范围 |
| E302 | 数据库操作失败 | 检查数据完整性约束 |
| E303 | 缓存操作失败 | 检查Redis连接 |

### WebSocket 错误码

| 错误码 | 说明 | 处理方式 |
|--------|------|----------|
| 1000 | 正常关闭 | 无需处理 |
| 1001 | 端点离开 | 自动重连 |
| 1002 | 协议错误 | 检查消息格式 |
| 1003 | 不支持的数据类型 | 检查消息编码 |
| 1006 | 异常关闭 | 检查网络、重连 |
| 1007 | 数据不一致 | 检查消息内容 |
| 1008 | 策略违规 | 检查请求频率 |
| 1009 | 消息过大 | 分块发送 |
| 1011 | 服务器错误 | 检查服务器日志 |
| 1012 | 服务重启 | 等待后重连 |
| 1013 | 稍后重试 | 延迟重连 |

---

## 系统诊断

### 健康检查脚本

```bash
#!/bin/bash
# diagnose.sh - 系统诊断脚本

echo "=== CAUC-SEP 系统诊断 ==="
echo ""

# 1. 检查后端服务
echo "1. 检查后端服务..."
if curl -s http://localhost:8000/api/health > /dev/null; then
    echo "   [OK] 后端服务正常"
else
    echo "   [ERROR] 后端服务异常"
fi

# 2. 检查前端服务
echo "2. 检查前端服务..."
if curl -s http://localhost:5173 > /dev/null; then
    echo "   [OK] 前端服务正常"
else
    echo "   [ERROR] 前端服务异常"
fi

# 3. 检查数据库
echo "3. 检查数据库..."
if [ -f "data/cauc_sep.db" ]; then
    echo "   [OK] 数据库文件存在"
    SIZE=$(stat -f%z "data/cauc_sep.db" 2>/dev/null || stat -c%s "data/cauc_sep.db")
    echo "   数据库大小: $SIZE bytes"
else
    echo "   [ERROR] 数据库文件不存在"
fi

# 4. 检查设备连接
echo "4. 检查设备连接..."
DEVICES=$(curl -s http://localhost:8000/api/devices/status | grep -o '"connected_devices":[0-9]*' | grep -o '[0-9]*')
echo "   已连接设备数: $DEVICES"

# 5. 检查系统资源
echo "5. 检查系统资源..."
echo "   CPU使用率: $(top -bn1 | grep "Cpu(s)" | awk '{print $2}')%"
echo "   内存使用率: $(free | grep Mem | awk '{printf "%.1f", $3/$2 * 100}')%"
echo "   磁盘使用率: $(df -h . | tail -1 | awk '{print $5}')"

echo ""
echo "=== 诊断完成 ==="
```

### 使用诊断API

```bash
# 获取完整健康状态
curl http://localhost:8000/api/health | jq

# 获取性能瓶颈分析
curl http://localhost:8000/api/performance/bottlenecks | jq

# 获取设备状态
curl http://localhost:8000/api/devices/status | jq

# 获取活跃告警
curl http://localhost:8000/api/alerts/active | jq
```

---

## 性能问题排查

### CPU 使用率过高

**诊断步骤**:
```bash
# 1. 查看进程CPU使用
top -p $(pgrep -f "uvicorn|python")

# 2. 查看线程详情
ps -eLf | grep python

# 3. 使用性能分析
python -m cProfile -o profile.stats main.py
```

**常见原因与解决方案**:

| 原因 | 解决方案 |
|------|----------|
| 无限循环 | 检查代码逻辑，添加退出条件 |
| 频繁GC | 优化对象创建，使用对象池 |
| 大量计算 | 使用异步处理或任务队列 |
| 死锁 | 检查锁的使用，使用超时机制 |

### 内存泄漏

**诊断步骤**:
```bash
# 1. 监控内存使用
watch -n 1 'ps aux | grep python | grep -v grep'

# 2. 使用内存分析工具
pip install memory_profiler
python -m memory_profiler main.py

# 3. 检查对象引用
python -c "import gc; gc.collect(); print(len(gc.get_objects()))"
```

**解决方案**:
```python
# 1. 及时释放资源
def process_data():
    data = load_large_file()
    try:
        result = process(data)
    finally:
        del data  # 显式释放
    return result

# 2. 使用生成器
def read_large_file(path):
    with open(path) as f:
        for line in f:
            yield line

# 3. 限制缓存大小
from functools import lru_cache

@lru_cache(maxsize=1000)
def expensive_function(param):
    return compute(param)
```

### 响应时间过长

**诊断步骤**:
```bash
# 1. 检查API响应时间
curl -w "Time: %{time_total}s\n" http://localhost:8000/api/health

# 2. 分析慢查询
# 启用SQL日志
export SQLALCHEMY_ECHO=true

# 3. 检查数据库索引
sqlite3 data/cauc_sep.db ".indexes"
```

**解决方案**:
```python
# 1. 添加数据库索引
CREATE INDEX idx_device_status ON devices(status);

# 2. 使用分页查询
@app.get("/api/devices")
async def list_devices(page: int = 1, size: int = 20):
    offset = (page - 1) * size
    return db.query(Device).offset(offset).limit(size).all()

# 3. 启用响应压缩
from fastapi.middleware.gzip import GZipMiddleware
app.add_middleware(GZipMiddleware, minimum_size=1000)
```

---

## 网络问题排查

### 连接超时

**诊断步骤**:
```bash
# 1. 测试网络连通性
ping -c 4 localhost
ping -c 4 8.8.8.8

# 2. 检查端口监听
netstat -tlnp | grep 8000

# 3. 测试API响应
curl -v --connect-timeout 5 http://localhost:8000/api/health
```

**解决方案**:
```python
# 调整超时配置
HTTP_TIMEOUT = 30  # 秒
WEBSOCKET_TIMEOUT = 60  # 秒

# 添加重试机制
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=10))
async def fetch_with_retry(url):
    async with httpx.AsyncClient(timeout=HTTP_TIMEOUT) as client:
        return await client.get(url)
```

### WebSocket 断开

**诊断步骤**:
```javascript
// 前端诊断
const ws = new WebSocket('ws://localhost:8000/ws')

ws.onopen = () => console.log('WebSocket 已连接')
ws.onclose = (e) => console.log('WebSocket 已断开', e.code, e.reason)
ws.onerror = (e) => console.error('WebSocket 错误', e)
```

**解决方案**:
```javascript
// 配置心跳保活
const { connect } = useWebSocket('ws://localhost:8000/ws', {
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

---

## 设备问题排查

### 设备通信故障

**诊断流程**:

```
1. 物理连接检查
   ├── 电源是否正常
   ├── 数据线是否连接
   └── 指示灯状态

2. 驱动检查
   ├── 驱动是否安装
   ├── 设备是否识别
   └── 端口是否正确

3. 通信测试
   ├── 波特率是否匹配
   ├── 数据格式是否正确
   └── 校验位配置

4. 功能测试
   ├── 基本命令响应
   ├── 状态查询
   └── 错误日志分析
```

**常见设备错误**:

| 错误现象 | 可能原因 | 解决方案 |
|----------|----------|----------|
| 设备无响应 | 通信断开 | 检查连接、重启设备 |
| 响应延迟 | 波特率过低 | 提高波特率 |
| 数据错误 | 校验失败 | 检查数据格式 |
| 命令拒绝 | 设备忙 | 等待设备空闲 |
| 过热保护 | 温度过高 | 停机冷却 |

---

## 日志分析

### 日志位置

```
cauc-sep/
├── logs/
│   ├── app.log          # 应用日志
│   ├── device.log       # 设备日志
│   ├── access.log       # 访问日志
│   └── error.log        # 错误日志
└── data/
    └── error_logs       # 前端错误日志(localStorage)
```

### 日志级别

| 级别 | 说明 | 使用场景 |
|------|------|----------|
| DEBUG | 调试信息 | 开发调试 |
| INFO | 一般信息 | 正常操作 |
| WARNING | 警告信息 | 潜在问题 |
| ERROR | 错误信息 | 功能异常 |
| CRITICAL | 严重错误 | 系统故障 |

### 日志分析命令

```bash
# 查看最近错误
tail -100 logs/error.log

# 搜索特定错误
grep "DeviceError" logs/device.log

# 统计错误类型
grep -o "ERROR.*" logs/app.log | sort | uniq -c | sort -rn

# 查看时间范围内的日志
awk '/2026-03-08 10:00/,/2026-03-08 11:00/' logs/app.log

# 实时监控日志
tail -f logs/app.log | grep --color=auto "ERROR\|WARNING"
```

### 常见日志模式

```
# 设备连接错误
[ERROR] Device connection failed: stepper_01 - Timeout waiting for response

# 数据库错误
[ERROR] Database error: UNIQUE constraint failed: devices.device_id

# API错误
[ERROR] API request failed: POST /api/tasks - 422 Unprocessable Entity

# WebSocket错误
[ERROR] WebSocket error: Connection closed unexpectedly (code: 1006)
```

---

## 联系支持

如果以上方法无法解决问题，请提供以下信息联系技术支持：

1. **系统信息**
   - 操作系统版本
   - Python 版本
   - Node.js 版本

2. **错误信息**
   - 完整错误堆栈
   - 错误发生时间
   - 复现步骤

3. **日志文件**
   - logs/error.log
   - logs/device.log
   - 浏览器控制台日志

4. **配置信息**
   - 环境变量配置
   - 设备配置
   - 网络配置

---

## 相关文档

- [健康监控API文档](./api/health-api.md)
- [告警系统API文档](./api/alerts-api.md)
- [性能分析API文档](./api/performance-api.md)

---

## 文档修订历史

| 版本 | 日期 | 修订内容 | 作者 |
|------|------|----------|------|
| v1.0 | 2026-03-08 | 初始版本 | Tech Writer Agent |
| v1.1 | 2026-03-14 | 更新版本号，添加应用版本信息 | Tech Writer Agent |

---

*CAUC-SEP 自旋电子器件实验平台 | 故障排除指南*  
*版本 0.3.0 | © 2025-2026 版权所有*
