# Modbus RTU 协议

**版本**: v1.0  
**创建日期**: 2026-03-15  
**最后更新**: 2026-03-15  
**适用设备**: DM2C系列步进驱动器

---

## 概述

CAUC-SEP自旋电子器件实验平台采用Modbus RTU协议与DM2C系列步进驱动器进行通信。Modbus RTU是一种广泛应用于工业自动化领域的串行通信协议，具有简单、可靠、易于实现的特点。

### 协议特点

- **物理层**: RS485/RS232串行通信
- **数据传输**: 二进制格式，高效率
- **错误检测**: CRC-16校验
- **主从架构**: 一主多从，支持多设备组网

---

## 通信参数配置

### 默认通信参数

| 参数 | RS485模式 | RS232模式 |
|------|-----------|-----------|
| 波特率 | 38400 bps（可配置） | 9600 bps（固定） |
| 数据位 | 8位 | 8位 |
| 校验位 | 无校验（可配置） | 无校验 |
| 停止位 | 1位（可配置） | 1位 |
| 从站地址 | 1-127（可配置） | 1（固定） |

### 波特率配置映射

| Pr5.22值 | 波特率 |
|----------|--------|
| 0 | 2400 bps |
| 1 | 4800 bps |
| 2 | 9600 bps |
| 3 | 19200 bps |
| 4 | 38400 bps |
| 5 | 57600 bps |
| 6 | 115200 bps |

### 数据类型配置映射（Pr5.24）

| 值 | 数据位 | 校验位 | 停止位 |
|----|--------|--------|--------|
| 0 | 8位 | 偶校验(E) | 2位 |
| 1 | 8位 | 奇校验(O) | 2位 |
| 2 | 8位 | 偶校验(E) | 1位 |
| 3 | 8位 | 奇校验(O) | 1位 |
| 4 | 8位 | 无校验(N) | 1位 |
| 5 | 8位 | 无校验(N) | 2位 |

---

## 数据帧格式

### 帧结构

```
+--------+----------+----------+----------+
| 从站地址 | 功能码   | 数据域   | CRC校验  |
| 1字节   | 1字节    | N字节    | 2字节    |
+--------+----------+----------+----------+
```

### CRC-16校验

采用Modbus标准CRC-16算法，多项式为0xA001，初始值为0xFFFF。

```python
def calculate_crc16(data: bytes) -> int:
    """
    计算Modbus CRC-16校验值。

    Args:
        data: 待校验数据

    Returns:
        int: CRC-16校验值（低字节在前）
    """
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc
```

---

## 功能码说明

### 支持的功能码

| 功能码 | 名称 | 说明 |
|--------|------|------|
| 0x03 | 读保持寄存器 | 读取状态、位置等参数 |
| 0x06 | 写单个寄存器 | 控制命令、参数设置 |
| 0x10 | 写多个寄存器 | 批量配置PR路径参数 |

### 功能码 0x03 - 读保持寄存器

**请求帧格式**:

```
+--------+--------+----------+----------+
| 从站地址 | 0x03   | 起始地址 | 寄存器数 |
| 1字节   | 1字节  | 2字节    | 2字节    |
+--------+--------+----------+----------+
```

**响应帧格式**:

```
+--------+--------+----------+----------+
| 从站地址 | 0x03   | 字节数   | 数据     |
| 1字节   | 1字节  | 1字节    | N字节    |
+--------+--------+----------+----------+
```

**示例** - 读取状态字（地址0x1003）:

```
请求: 01 03 10 03 00 01 [CRC]
响应: 01 03 02 00 04 [CRC]  // 状态字 = 0x0004（运行中）
```

### 功能码 0x06 - 写单个寄存器

**请求帧格式**:

```
+--------+--------+----------+----------+
| 从站地址 | 0x06   | 寄存器地址| 数据值   |
| 1字节   | 1字节  | 2字节    | 2字节    |
+--------+--------+----------+----------+
```

**响应帧格式**:

```
+--------+--------+----------+----------+
| 从站地址 | 0x06   | 寄存器地址| 数据值   |
| 1字节   | 1字节  | 2字节    | 2字节    |
+--------+--------+----------+----------+
```

**示例** - 写入控制字（地址0x1801）启动正向JOG:

```
请求: 01 06 18 01 40 01 [CRC]
响应: 01 06 18 01 40 01 [CRC]  // 原样返回
```

### 功能码 0x10 - 写多个寄存器

**请求帧格式**:

```
+--------+--------+----------+----------+----------+----------+
| 从站地址 | 0x10   | 起始地址 | 寄存器数 | 字节数   | 数据     |
| 1字节   | 1字节  | 2字节    | 2字节    | 1字节    | N字节    |
+--------+--------+----------+----------+----------+----------+
```

**响应帧格式**:

```
+--------+--------+----------+----------+
| 从站地址 | 0x10   | 起始地址 | 寄存器数 |
| 1字节   | 1字节  | 2字节    | 2字节    |
+--------+--------+----------+----------+
```

---

## DM2C驱动器寄存器映射

### 核心控制寄存器

| 寄存器地址 | 名称 | 读/写 | 说明 |
|------------|------|-------|------|
| 0x1801 | 控制字 | R/W | 控制命令写入 |
| 0x1003 | 状态字 | R | 设备状态读取 |
| 0x6002 | 触发寄存器 | R/W | 运动触发与状态 |
| 0x2203 | 报警代码 | R | 当前报警代码 |

### 位置相关寄存器

| 寄存器地址 | 名称 | 读/写 | 说明 |
|------------|------|-------|------|
| 0x602A | 目标位置高位 | R/W | 目标位置高16位 |
| 0x602B | 目标位置低位 | R/W | 目标位置低16位 |
| 0x602C | 实际位置高位 | R | 实际位置高16位 |
| 0x602D | 实际位置低位 | R | 实际位置低16位 |

### JOG运动寄存器

| 寄存器地址 | 名称 | 读/写 | 说明 |
|------------|------|-------|------|
| 0x01E1 | JOG速度 | R/W | Pr6.00，JOG速度（步/秒） |
| 0x01E7 | JOG加速时间 | R/W | Pr6.03，JOG加速时间 |
| 0x01E8 | JOG减速时间 | R/W | Pr6.04，JOG减速时间 |

### 回零参数寄存器

| 寄存器地址 | 名称 | 读/写 | 说明 |
|------------|------|-------|------|
| 0x0280 | 回零模式 | R/W | Pr8.00，回零模式选择 |
| 0x0281 | 回零速度（高速） | R/W | Pr8.01，回零高速 |
| 0x0282 | 回零速度（低速） | R/W | Pr8.02，回零低速 |
| 0x0283 | 回零偏移 | R/W | Pr8.03，回零偏移量 |
| 0x0284 | 回零方向 | R/W | Pr8.04，回零方向 |

### 软件限位寄存器

| 寄存器地址 | 名称 | 读/写 | 说明 |
|------------|------|-------|------|
| 0x6006 | 正限位高位 | R/W | Pr8.06，正限位高16位 |
| 0x6007 | 正限位低位 | R/W | Pr8.07，正限位低16位 |
| 0x6008 | 负限位高位 | R/W | Pr8.08，负限位高16位 |
| 0x6009 | 负限位低位 | R/W | Pr8.09，负限位低16位 |

### PR路径配置寄存器

每个PR路径占用8个连续寄存器，基地址为0x6200。

| 偏移 | 名称 | 说明 |
|------|------|------|
| +0 | 运动模式 | 运动类型、位置模式等 |
| +1 | 目标位置高位 | 目标位置高16位 |
| +2 | 目标位置低位 | 目标位置低16位 |
| +3 | 运行速度 | 运动速度（步/秒） |
| +4 | 加速时间 | 加速时间单位 |
| +5 | 减速时间 | 减速时间单位 |
| +6 | 停顿时间 | 到位后停顿时间 |
| +7 | 保留 | 保留 |

**路径地址计算公式**:

```
路径N的基地址 = 0x6200 + N * 8  (N = 0~15)
```

---

## 控制字定义

### 控制字命令（地址0x1801）

| 命令值 | 名称 | 说明 |
|--------|------|------|
| 0x4001 | 正向JOG | 需50ms间隔连续发送 |
| 0x4002 | 负向JOG | 需50ms间隔连续发送 |
| 0x4000 | JOG停止 | 停止JOG运动 |
| 0x0001 | 清除报警 | 清除当前报警 |
| 0x1111 | 复位当前报警 | 复位当前报警状态 |
| 0x1122 | 复位历史报警 | 清除历史报警记录 |
| 0x2211 | 保存参数 | 保存参数到EEPROM |
| 0x2222 | 参数初始化 | 参数初始化（不含电机参数） |
| 0x2233 | 恢复出厂设置 | 恢复所有参数为出厂值 |
| 0x2244 | 保存映射参数 | 保存映射参数到EEPROM |

---

## 状态字定义

### 状态字位定义（地址0x1003）

| 位 | 名称 | 说明 |
|----|------|------|
| Bit0 | FAULT | 故障位（1=故障） |
| Bit1 | ENABLE | 使能状态（1=使能） |
| Bit2 | RUNNING | 运行状态（1=运行中） |
| Bit3 | INVALID | 无效位（1=无效状态） |
| Bit4 | CMD_COMPLETE | 命令完成（1=完成） |
| Bit5 | PATH_COMPLETE | 路径完成（1=完成） |
| Bit6 | HOME_COMPLETE | 回零完成（1=完成） |

### 状态字解析示例

```python
def parse_status_word(status: int) -> dict:
    """
    解析状态字。

    Args:
        status: 状态字值

    Returns:
        dict: 解析后的状态信息
    """
    return {
        "fault": bool(status & 0x01),
        "enabled": bool(status & 0x02),
        "running": bool(status & 0x04),
        "invalid": bool(status & 0x08),
        "cmd_complete": bool(status & 0x10),
        "path_complete": bool(status & 0x20),
        "home_complete": bool(status & 0x40),
    }
```

---

## 触发寄存器定义

### 触发命令（地址0x6002）

| 命令值 | 名称 | 说明 |
|--------|------|------|
| 0x0100 + N | 触发路径N | 触发路径0~15执行 |
| 0x020 | 回零触发 | 边沿触发回零 |
| 0x021 | 设当前位置为零 | 手动设置零点 |
| 0x040 | 急停触发 | 紧急停止 |

### 触发状态读取

| 读值 | 状态说明 |
|------|----------|
| 0x0000 | 定位完成，可接收新数据 |
| 0x1000 + N | 路径N运行中 |
| 0x0200 | 指令完成等待定位 |

---

## 报警代码

### 报警代码定义

| 代码 | 名称 | 严重程度 |
|------|------|----------|
| 0x01 | 过流保护 | 严重 |
| 0x02 | 过压保护 | 严重 |
| 0x40 | 电流采样故障 | 严重 |
| 0x80 | 锁轴故障 | 严重 |
| 0x100 | 参数自整定故障 | 警告 |
| 0x200 | EEPROM故障 | 警告 |
| 0x210 | IO配置重复 | 警告 |

### 报警处理流程

```python
async def handle_alarm(driver: LeadshineDM2C) -> dict:
    """
    处理驱动器报警。

    Args:
        driver: DM2C驱动器实例

    Returns:
        dict: 报警信息
    """
    # 读取报警代码
    alarm_code = await driver.read_alarm_code()

    # 获取报警详情
    alarm_info = get_alarm_info(alarm_code, language="zh")

    # 记录日志
    if alarm_code != 0:
        logger.error(
            f"Alarm detected: code=0x{alarm_code:04X}, "
            f"name={alarm_info['name']}, "
            f"severity={alarm_info['severity']}"
        )

    return alarm_info
```

---

## 错误处理

### 异常响应帧格式

当从站检测到错误时，返回异常响应：

```
+--------+------------+----------+
| 从站地址 | 功能码+0x80| 异常码   |
| 1字节   | 1字节      | 1字节    |
+--------+------------+----------+
```

### 异常代码

| 异常码 | 名称 | 说明 |
|--------|------|------|
| 0x01 | 非法功能码 | 设备不支持该功能码 |
| 0x02 | 非法数据地址 | 寄存器地址无效 |
| 0x03 | 非法数据值 | 数据值超出范围 |
| 0x04 | 从站设备故障 | 设备内部错误 |

### 通信超时处理

```python
async def read_with_retry(
    client: ModbusSerialClient,
    address: int,
    count: int,
    max_retries: int = 3,
    timeout: float = 1.0
) -> list[int]:
    """
    带重试的寄存器读取。

    Args:
        client: Modbus客户端
        address: 起始地址
        count: 寄存器数量
        max_retries: 最大重试次数
        timeout: 超时时间

    Returns:
        list[int]: 寄存器值列表

    Raises:
        ModbusException: 通信失败
    """
    for attempt in range(max_retries):
        try:
            result = client.read_holding_registers(address, count)
            if not result.isError():
                return result.registers
        except Exception as e:
            logger.warning(f"Read attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(0.1 * (attempt + 1))

    raise ModbusException(f"Failed after {max_retries} retries")
```

---

## 代码示例

### Python连接示例

```python
import asyncio
from pymodbus.client import ModbusSerialClient

async def connect_dm2c():
    """
    连接DM2C驱动器示例。
    """
    # 创建Modbus客户端
    client = ModbusSerialClient(
        port="COM3",
        baudrate=38400,
        bytesize=8,
        parity="N",
        stopbits=1,
        timeout=1.0,
    )

    # 建立连接
    if client.connect():
        print("Connected to DM2C driver")

        # 读取状态字
        result = client.read_holding_registers(0x1003, 1, slave=1)
        if not result.isError():
            status = result.registers[0]
            print(f"Status word: 0x{status:04X}")

        # 关闭连接
        client.close()
    else:
        print("Failed to connect")
```

### 绝对位置运动示例

```python
async def move_absolute(
    client: ModbusSerialClient,
    position_mm: float,
    steps_per_mm: int = 1600
) -> bool:
    """
    执行绝对位置运动。

    Args:
        client: Modbus客户端
        position_mm: 目标位置（毫米）
        steps_per_mm: 每毫米步数

    Returns:
        bool: 是否成功
    """
    # 转换为步数
    position_steps = int(position_mm * steps_per_mm)

    # 分解为高低字
    pos_high = (position_steps >> 16) & 0xFFFF
    pos_low = position_steps & 0xFFFF

    # 写入目标位置
    client.write_register(0x602A, pos_high, slave=1)
    client.write_register(0x602B, pos_low, slave=1)

    # 触发运动
    client.write_register(0x6002, 0x0100, slave=1)

    return True
```

### PR路径配置示例

```python
async def configure_pr_path(
    client: ModbusSerialClient,
    path_number: int,
    position: int,
    velocity: int,
    acceleration: int,
    deceleration: int
) -> bool:
    """
    配置PR路径参数。

    Args:
        client: Modbus客户端
        path_number: 路径号（0-15）
        position: 目标位置（步）
        velocity: 运行速度（步/秒）
        acceleration: 加速时间
        deceleration: 减速时间

    Returns:
        bool: 是否成功
    """
    # 计算基地址
    base_addr = 0x6200 + path_number * 8

    # 准备数据
    pos_high = (position >> 16) & 0xFFFF
    pos_low = position & 0xFFFF

    values = [
        0x0001,         # 运动模式：位置定位
        pos_high,       # 目标位置高位
        pos_low,        # 目标位置低位
        velocity,       # 运行速度
        acceleration,   # 加速时间
        deceleration,   # 减速时间
        0,              # 停顿时间
        0,              # 保留
    ]

    # 写入多个寄存器
    result = client.write_registers(base_addr, values, slave=1)

    return not result.isError()
```

---

## 通信故障排除指南

### 常见问题诊断

#### 1. 无法连接设备

**症状**: 连接超时或失败

**排查步骤**:

1. 检查串口号是否正确
2. 确认波特率与驱动器设置一致
3. 检查RS485接线（A+、B-极性）
4. 确认从站地址配置正确
5. 检查终端电阻（长距离通信需要）

**解决方案**:

```python
# 尝试不同波特率
for baudrate in [9600, 19200, 38400, 57600, 115200]:
    client = ModbusSerialClient(port="COM3", baudrate=baudrate)
    if client.connect():
        print(f"Connected at {baudrate} bps")
        break
```

#### 2. 数据读取错误

**症状**: 读取数据为0或异常值

**排查步骤**:

1. 检查寄存器地址是否正确
2. 确认从站地址
3. 检查CRC校验
4. 验证数据帧格式

**解决方案**:

```python
# 添加详细日志
def read_register_debug(client, address, slave_id):
    result = client.read_holding_registers(address, 1, slave=slave_id)
    print(f"Address: 0x{address:04X}")
    print(f"Response: {result}")
    if not result.isError():
        print(f"Value: {result.registers[0]}")
    return result
```

#### 3. 运动命令无响应

**症状**: 写入命令后设备无动作

**排查步骤**:

1. 检查驱动器使能状态
2. 确认无报警状态
3. 验证目标位置在限位范围内
4. 检查触发命令是否正确发送

**解决方案**:

```python
async def safe_move(client, position, slave_id=1):
    # 检查状态
    status = client.read_holding_registers(0x1003, 1, slave=slave_id)
    if status.isError():
        raise Exception("Failed to read status")

    status_word = status.registers[0]

    # 检查故障位
    if status_word & 0x01:
        alarm = client.read_holding_registers(0x2203, 1, slave=slave_id)
        raise Exception(f"Device in alarm: 0x{alarm.registers[0]:04X}")

    # 检查运行状态
    if status_word & 0x04:
        raise Exception("Device is running, wait for completion")

    # 执行运动...
```

#### 4. CRC校验错误

**症状**: 通信频繁失败，CRC错误

**排查步骤**:

1. 检查通信线缆屏蔽
2. 确认接地良好
3. 检查波特率是否过高
4. 增加通信超时时间

**解决方案**:

```python
# 降低波特率，增加超时
client = ModbusSerialClient(
    port="COM3",
    baudrate=9600,      # 降低波特率
    timeout=2.0,        # 增加超时
    retries=3,          # 增加重试次数
)
```

### 性能优化建议

1. **批量读写**: 使用功能码0x10批量写入多个寄存器
2. **合理轮询**: 避免过于频繁的状态查询
3. **错误重试**: 实现指数退避重试机制
4. **连接复用**: 保持长连接，避免频繁断开重连

---

## 参考资料

- DM2C-RS556用户手册 V1.8
- Modbus协议规范（PI-MBUS-300）
- pymodbus库文档

---

## 更新日志

### v1.0 (2026-03-15)
- 初始版本
- 完整的寄存器映射文档
- 控制字和状态字定义
- 报警代码说明
- 代码示例
- 故障排除指南
