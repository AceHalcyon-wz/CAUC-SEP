# CAUC-SEP 设备基类整合摘要

## 整合概述

根据CAUC-SEP项目架构重构与Agent驱动开发专属提示词文件的要求，已成功整合项目现有的3套设备基类实现，建立了统一的设备抽象体系。

## 整合前状态

### 现有3套设备基类

1. **backend/devices/base.py - AbstractDevice**
   - 功能：基础设备抽象类
   - 状态管理：DeviceStatus枚举（6个状态）
   - 核心方法：connect(), disconnect(), read_status(), reset_error()

2. **backend/core/abstract.py - AbstractDevice (ABC)**
   - 功能：硬件抽象层基类
   - 状态管理：DeviceStatus枚举（带状态转换验证）
   - 软件限位：SoftwareLimitConfig类
   - 核心方法：connect(), disconnect(), read_status(), reset()
   - 步进电机专用：AbstractStepper类

3. **backend/drivers/base.py - BaseDevice (ABC, Generic)**
   - 功能：设备驱动抽象基类
   - 状态管理：DeviceStatus枚举（扩展状态：ALARM, INITIALIZING, CALIBRATING）
   - 设备信息：DeviceInfo, DeviceConfig, DeviceAlarm, DeviceParameter数据类
   - 核心方法：connect(), disconnect(), get_status(), emergency_stop(), reset_emergency()
   - Modbus专用：ModbusDeviceBase类
   - 异步支持：AsyncDeviceBase类

## 整合后状态

### 新的统一基类结构

```
backend/core/hardware/
├── __init__.py              # 模块入口，导出所有公共接口
├── base_device.py           # 统一的设备抽象基类 BaseDevice
├── modbus_device.py         # Modbus设备抽象基类 ModbusDeviceBase
├── device_types.py          # 设备类型、状态、配置等数据类
├── software_limit.py        # 软件限位配置类
└── migration_guide.py       # 迁移指南文档
```

### 核心功能整合

#### 1. DeviceStatus枚举（统一版本）

```python
class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    ALARM = "alarm"              # 新增
    INITIALIZING = "initializing"  # 新增
    CALIBRATING = "calibrating"    # 新增
    
    # 新增：状态转换验证
    def can_transition_to(self, target: DeviceStatus) -> bool:
        ...
```

#### 2. BaseDevice抽象基类（统一版本）

```python
class BaseDevice(ABC, Generic[DeviceStateType]):
    # 必须实现的抽象方法
    async def connect(self) -> bool: ...
    async def disconnect(self) -> bool: ...
    async def get_status(self) -> dict[str, Any]: ...
    async def emergency_stop(self) -> bool: ...
    async def reset_alarm(self) -> bool: ...
    
    # 可选方法
    async def initialize(self) -> bool: ...
    async def reset(self) -> bool: ...
    async def self_test(self) -> dict[str, Any]: ...
    
    # 内部方法
    def _set_status(self, status: DeviceStatus, strict: bool = False): ...
    def _add_alarm(self, alarm: DeviceAlarm): ...
    def _set_error(self, error: str): ...
```

#### 3. ModbusDeviceBase抽象基类（增强版本）

```python
class ModbusDeviceBase(BaseDevice[DeviceStateType]):
    # 新增：指令优先级参数（0=最高，9=最低）
    async def read_holding_registers(
        self, address: int, count: int = 1, priority: int = 5
    ) -> list[int] | None: ...
    
    async def write_single_register(
        self, address: int, value: int, priority: int = 5
    ) -> bool: ...
    
    # 新增：输入寄存器、线圈读写方法
    async def read_input_registers(...): ...
    async def read_coils(...): ...
    async def write_single_coil(...): ...
    
    # 新增：32位数据转换辅助方法
    @staticmethod
    def _convert_signed_32bit(high: int, low: int) -> int: ...
    
    @staticmethod
    def _split_32bit_to_registers(value: int) -> tuple[int, int]: ...
```

#### 4. 数据类（保留并增强）

```python
@dataclass
class DeviceInfo:
    device_id: str
    device_name: str = "Unknown Device"
    device_type: DeviceType = DeviceType.UNKNOWN
    manufacturer: str = "Unknown"
    model: str = "Unknown"
    serial_number: str | None = None
    firmware_version: str | None = None
    connection_type: ConnectionType = ConnectionType.SIMULATION

@dataclass
class DeviceConfig:
    device_id: str
    connection_params: dict[str, Any] = field(default_factory=dict)
    simulation: bool = True
    auto_reconnect: bool = True
    reconnect_interval: float = 5.0
    timeout: float = 1.0
    max_retries: int = 3

@dataclass
class DeviceAlarm:
    alarm_code: int
    alarm_message: str
    alarm_level: int = 1
    timestamp: float = field(default_factory=time.time)
    is_active: bool = True

@dataclass
class DeviceParameter:
    name: str
    value: Any
    min_value: Any | None = None
    max_value: Any | None = None
    unit: str = ""
    description: str = ""
    is_readonly: bool = False
```

#### 5. SoftwareLimitConfig类（保留）

```python
class SoftwareLimitConfig:
    def __init__(
        self,
        positive_limit: float = 100.0,
        negative_limit: float = -100.0,
        enable: bool = True,
    ): ...
    
    def is_within_limits(self, position: float) -> bool: ...
    def clamp_position(self, position: float) -> float: ...
    def to_dict(self) -> dict[str, Any]: ...
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoftwareLimitConfig: ...
```

## 新增安全特性

### 1. 状态转换验证

```python
# 严格模式：非法转换抛出异常
self._set_status(DeviceStatus.READY, strict=True)

# 非严格模式：非法转换记录警告
self._set_status(DeviceStatus.READY, strict=False)
```

### 2. 软件限位集成

```python
# 设置软件限位
self.limit_config = SoftwareLimitConfig(
    positive_limit=100.0,
    negative_limit=-100.0,
    enable=True
)

# 检查位置是否在限位范围内
if self.limit_config.is_within_limits(target_position):
    await self.move_abs(target_position, speed)
```

### 3. 报警管理

```python
# 添加报警
alarm = DeviceAlarm(
    alarm_code=1001,
    alarm_message="电机过流",
    alarm_level=2
)
self._add_alarm(alarm)

# 获取活动报警
alarms = await self.get_alarms()

# 清除报警
await self.clear_alarms()
```

### 4. 回调函数

```python
# 设置状态变化回调
device.set_status_callback(on_status_change)

# 设置报警回调
device.set_alarm_callback(on_alarm)
```

### 5. Modbus指令优先级

```python
# 急停指令使用最高优先级（priority=0）
success = await self.write_single_register(0x0200, 1, priority=0)
```

## 向后兼容性

### 废弃警告

所有旧基类文件已添加废弃警告，但仍可正常使用：

- `backend.devices.base` - 已添加DeprecationWarning
- `backend.core.abstract` - 已添加DeprecationWarning
- `backend.drivers.base` - 已添加DeprecationWarning

### 兼容性导入

```python
# 旧代码仍可正常运行（触发废弃警告）
from backend.devices.base import AbstractDevice

# 推荐使用新导入（无警告）
from backend.core.hardware import BaseDevice
```

## 迁移时间表

- **2026-03-26**: 发布统一基类，旧基类添加废弃警告
- **2026-04-26**: 完成所有设备驱动迁移到新基类
- **2026-05-26**: 移除旧基类文件，仅保留统一基类

## 文件变更摘要

### 新增文件

1. `backend/core/hardware/__init__.py` - 模块入口
2. `backend/core/hardware/base_device.py` - 统一设备抽象基类
3. `backend/core/hardware/modbus_device.py` - Modbus设备抽象基类
4. `backend/core/hardware/device_types.py` - 设备类型、状态、配置数据类
5. `backend/core/hardware/software_limit.py` - 软件限位配置类
6. `backend/core/hardware/migration_guide.py` - 迁移指南文档

### 修改文件

1. `backend/devices/base.py` - 添加废弃警告
2. `backend/core/abstract.py` - 添加废弃警告
3. `backend/drivers/base.py` - 添加废弃警告

### 待迁移文件

以下设备驱动需要更新继承关系：

1. `backend/core/dm2c_driver.py` - DM2C步进驱动器驱动
   - 旧基类：`backend.core.abstract.AbstractStepper`
   - 新基类：`backend.core.hardware.ModbusDeviceBase`

2. `backend/core/electromagnet_driver.py` - 电磁铁驱动
   - 旧基类：`backend.core.abstract.AbstractDevice`
   - 新基类：`backend.core.hardware.BaseDevice`

3. 其他设备驱动（根据实际情况迁移）

## 技术栈

- Python 3.11+
- abc (抽象基类)
- dataclasses (数据类)
- enum (枚举)
- typing (类型注解)
- logging (日志)

## 安全约束

所有设备基类实现必须遵守以下安全约束：

1. **硬件改动绝对禁止**：所有代码100%限制在软件层面
2. **安全优先原则**：所有设备控制代码必须包含异常兜底逻辑、参数合法性校验
3. **急停优先级**：急停相关代码必须保障最高执行优先级
4. **二次校验**：高危操作必须包含二次校验、日志审计逻辑
5. **软件限位**：所有运动设备必须配置软件限位

## 参考文档

- CAUC-SEP项目架构重构与Agent驱动开发专属提示词文件
- CAUC-SEP项目专属多栈代码编写规则 (Python + Vue + TS/JS)
- DM2C-RS556用户手册 V1.8

## 联系方式

如有问题或建议，请联系：
- 后端工程师 Agent
- CAUC-SEP 开发团队
