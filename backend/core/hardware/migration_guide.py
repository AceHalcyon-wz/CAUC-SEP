"""
文件名: migration_guide.py
路径: backend/core/hardware/migration_guide.py
功能: 设备基类迁移指南，帮助开发者从旧基类迁移到统一基类
作者: Backend Engineer Agent
创建日期: 2026-03-26
依赖: Python 3.11+

迁移说明：
本模块提供了从以下旧基类迁移到统一BaseDevice的指南：
- backend.devices.base.AbstractDevice
- backend.core.abstract.AbstractDevice
- backend.core.abstract.AbstractStepper
- backend.drivers.base.BaseDevice
"""

# ==================== 迁移指南 ====================

"""
# 设备基类迁移指南

## 概述

CAUC-SEP项目已整合现有3套设备基类实现，建立了统一的设备抽象体系。
新的统一基类位于 `backend.core.hardware` 模块，提供更完善的功能和更好的安全性。

## 新的基类结构

```
backend/core/hardware/
├── __init__.py              # 模块入口，导出所有公共接口
├── base_device.py           # 统一的设备抽象基类 BaseDevice
├── modbus_device.py         # Modbus设备抽象基类 ModbusDeviceBase
├── device_types.py          # 设备类型、状态、配置等数据类
└── software_limit.py        # 软件限位配置类
```

## 核心类映射关系

### 1. 设备状态枚举

**旧实现（3个版本）：**
```python
# backend.devices.base.DeviceStatus
class DeviceStatus(str, Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    MAINTENANCE = "maintenance"

# backend.core.abstract.DeviceStatus
class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"

# backend.drivers.base.DeviceStatus
class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    ALARM = "alarm"
    INITIALIZING = "initializing"
    CALIBRATING = "calibrating"
```

**新实现（统一版本）：**
```python
# backend.core.hardware.device_types.DeviceStatus
class DeviceStatus(Enum):
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    ALARM = "alarm"
    INITIALIZING = "initializing"
    CALIBRATING = "calibrating"
    
    # 新增：状态转换验证
    def can_transition_to(self, target: DeviceStatus) -> bool:
        ...
```

### 2. 设备抽象基类

**旧实现：**
```python
# backend.devices.base.AbstractDevice
class AbstractDevice:
    async def connect(self) -> bool: ...
    async def disconnect(self) -> bool: ...
    async def read_status(self) -> dict[str, Any]: ...
    async def reset_error(self) -> bool: ...

# backend.core.abstract.AbstractDevice
class AbstractDevice(ABC):
    async def connect(self) -> bool: ...
    async def disconnect(self) -> bool: ...
    async def read_status(self) -> dict[str, Any]: ...
    async def reset(self) -> bool: ...

# backend.drivers.base.BaseDevice
class BaseDevice(ABC, Generic[DeviceStateType]):
    async def connect(self) -> bool: ...
    async def disconnect(self) -> bool: ...
    async def get_status(self) -> dict[str, Any]: ...
    async def emergency_stop(self) -> bool: ...
    async def reset_emergency(self) -> bool: ...
```

**新实现（统一版本）：**
```python
# backend.core.hardware.base_device.BaseDevice
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
```

### 3. Modbus设备基类

**旧实现：**
```python
# backend.drivers.base.ModbusDeviceBase
class ModbusDeviceBase(BaseDevice[DeviceStateType]):
    async def read_holding_registers(self, address: int, count: int = 1) -> list[int] | None: ...
    async def write_single_register(self, address: int, value: int) -> bool: ...
    async def write_multiple_registers(self, address: int, values: list[int]) -> bool: ...
```

**新实现（增强版本）：**
```python
# backend.core.hardware.modbus_device.ModbusDeviceBase
class ModbusDeviceBase(BaseDevice[DeviceStateType]):
    # 新增：指令优先级参数（0=最高，9=最低）
    async def read_holding_registers(
        self, address: int, count: int = 1, priority: int = 5
    ) -> list[int] | None: ...
    
    async def write_single_register(
        self, address: int, value: int, priority: int = 5
    ) -> bool: ...
    
    async def write_multiple_registers(
        self, address: int, values: list[int], priority: int = 5
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

## 迁移步骤

### 步骤1：更新导入语句

**旧导入：**
```python
# 方式1：从backend.devices.base导入
from backend.devices.base import AbstractDevice, DeviceStatus

# 方式2：从backend.core.abstract导入
from backend.core.abstract import AbstractDevice, DeviceStatus, SoftwareLimitConfig

# 方式3：从backend.drivers.base导入
from backend.drivers.base import BaseDevice, DeviceStatus, DeviceConfig
```

**新导入：**
```python
# 统一从backend.core.hardware导入
from backend.core.hardware import (
    BaseDevice,           # 统一的设备抽象基类
    ModbusDeviceBase,     # Modbus设备抽象基类
    DeviceStatus,         # 设备状态枚举
    DeviceType,           # 设备类型枚举
    DeviceConfig,         # 设备配置数据类
    DeviceInfo,           # 设备信息数据类
    DeviceAlarm,          # 设备报警数据类
    DeviceParameter,      # 设备参数数据类
    SoftwareLimitConfig,  # 软件限位配置类
)
```

### 步骤2：更新类继承关系

**示例1：普通设备驱动**

旧代码：
```python
from backend.devices.base import AbstractDevice, DeviceStatus

class MyDevice(AbstractDevice):
    async def connect(self) -> bool:
        self.status = DeviceStatus.CONNECTING
        # ...
        self.status = DeviceStatus.READY
        return True
    
    async def disconnect(self) -> bool:
        self.status = DeviceStatus.DISCONNECTED
        return True
    
    async def read_status(self) -> dict[str, Any]:
        return {"status": self.status.value}
    
    async def reset_error(self) -> bool:
        self._error_message = None
        return True
```

新代码：
```python
from backend.core.hardware import BaseDevice, DeviceStatus, DeviceConfig

class MyDevice(BaseDevice[None]):  # 泛型参数，None表示无特殊状态对象
    async def connect(self) -> bool:
        self._set_status(DeviceStatus.CONNECTING)
        try:
            # ...
            self._set_status(DeviceStatus.READY)
            return True
        except Exception as e:
            self._set_error(f"连接失败: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self._set_status(DeviceStatus.DISCONNECTED)
        return True
    
    async def get_status(self) -> dict[str, Any]:
        return self._get_base_status()
    
    async def emergency_stop(self) -> bool:
        self._set_status(DeviceStatus.EMERGENCY_STOP)
        return True
    
    async def reset_alarm(self) -> bool:
        self._alarms.clear()
        self._set_status(DeviceStatus.READY)
        return True
```

**示例2：Modbus设备驱动**

旧代码：
```python
from backend.drivers.base import ModbusDeviceBase, DeviceConfig

class DM2CMotorDevice(ModbusDeviceBase[MotorState]):
    async def connect(self) -> bool:
        # ...
        pass
```

新代码：
```python
from backend.core.hardware import ModbusDeviceBase, DeviceConfig

class DM2CMotorDevice(ModbusDeviceBase[MotorState]):
    async def connect(self) -> bool:
        self._set_status(DeviceStatus.CONNECTING)
        try:
            # 初始化Modbus连接
            self._set_status(DeviceStatus.READY)
            return True
        except Exception as e:
            self._set_error(f"连接失败: {e}")
            return False
    
    async def emergency_stop(self) -> bool:
        # 急停指令使用最高优先级（priority=0）
        success = await self.write_single_register(0x0200, 1, priority=0)
        if success:
            self._set_status(DeviceStatus.EMERGENCY_STOP)
        return success
```

### 步骤3：更新方法名称

| 旧方法名 | 新方法名 | 说明 |
|---------|---------|------|
| `read_status()` | `get_status()` | 统一方法命名 |
| `reset_error()` | `reset_alarm()` | 更准确的方法名 |
| `reset_emergency()` | `reset_alarm()` | 统一复位方法 |
| `status` (直接赋值) | `_set_status()` | 使用内部方法，支持状态转换验证 |

### 步骤4：使用新的安全特性

**1. 状态转换验证：**
```python
# 严格模式：非法转换抛出异常
self._set_status(DeviceStatus.READY, strict=True)

# 非严格模式：非法转换记录警告
self._set_status(DeviceStatus.READY, strict=False)
```

**2. 软件限位配置：**
```python
# 设置软件限位
self.limit_config = SoftwareLimitConfig(
    positive_limit=100.0,  # 正向限位100mm
    negative_limit=-100.0,  # 负向限位-100mm
    enable=True
)

# 检查位置是否在限位范围内
if self.limit_config.is_within_limits(target_position):
    # 执行运动指令
    await self.move_abs(target_position, speed)
else:
    raise ValueError(f"目标位置{target_position}超出软件限位范围")
```

**3. 报警管理：**
```python
# 添加报警
alarm = DeviceAlarm(
    alarm_code=1001,
    alarm_message="电机过流",
    alarm_level=2  # 0=信息, 1=警告, 2=错误, 3=严重
)
self._add_alarm(alarm)

# 获取活动报警
alarms = await self.get_alarms()

# 清除报警
await self.clear_alarms()
```

**4. 回调函数：**
```python
# 设置状态变化回调
def on_status_change(status: dict[str, Any]):
    print(f"设备状态变化: {status}")

device.set_status_callback(on_status_change)

# 设置报警回调
def on_alarm(alarm: DeviceAlarm):
    print(f"设备报警: {alarm.alarm_message}")

device.set_alarm_callback(on_alarm)
```

## 向后兼容性

为了确保向后兼容，旧的基类文件已添加废弃警告，但仍可正常使用。

**废弃警告示例：**
```python
# backend/devices/base.py
import warnings

warnings.warn(
    "backend.devices.base.AbstractDevice 已废弃，请使用 backend.core.hardware.BaseDevice",
    DeprecationWarning,
    stacklevel=2
)
```

**兼容性导入：**
```python
# 旧代码仍可正常运行
from backend.devices.base import AbstractDevice  # 触发废弃警告

# 推荐使用新导入
from backend.core.hardware import BaseDevice  # 无警告
```

## 迁移时间表

- **2026-03-26**: 发布统一基类，旧基类添加废弃警告
- **2026-04-26**: 完成所有设备驱动迁移到新基类
- **2026-05-26**: 移除旧基类文件，仅保留统一基类

## 常见问题

### Q1: 为什么需要迁移到统一基类？

A: 统一基类提供以下优势：
1. **功能更完善**：整合了3套基类的所有功能
2. **安全性更强**：内置状态转换验证、软件限位、报警管理
3. **一致性更好**：统一的方法命名和接口规范
4. **维护性更高**：单一基类，减少重复代码

### Q2: 迁移会破坏现有功能吗？

A: 不会。旧基类已添加废弃警告但仍可正常使用，确保向后兼容。
迁移过程中可以逐步更新，无需一次性修改所有代码。

### Q3: 如何处理自定义的设备状态？

A: 新的DeviceStatus枚举已包含所有常用状态（DISCONNECTED, CONNECTING, READY, BUSY, ERROR, EMERGENCY_STOP, ALARM, INITIALIZING, CALIBRATING）。
如需自定义状态，可在子类中扩展状态属性。

### Q4: Modbus设备迁移需要注意什么？

A: Modbus设备迁移需注意：
1. 新增了`priority`参数，急停指令必须使用`priority=0`
2. 新增了32位数据转换辅助方法
3. 新增了输入寄存器、线圈读写方法

## 技术支持

如有迁移问题，请联系：
- 后端工程师 Agent
- CAUC-SEP 开发团队
"""

# ==================== 示例代码 ====================

# 示例1：普通设备驱动迁移
"""
旧代码：
```python
from backend.devices.base import AbstractDevice, DeviceStatus

class TemperatureSensor(AbstractDevice):
    def __init__(self, device_id: str, config: dict):
        super().__init__(device_id, config)
        self._temperature = 0.0
    
    async def connect(self) -> bool:
        self.status = DeviceStatus.CONNECTING
        # 连接逻辑...
        self.status = DeviceStatus.READY
        return True
    
    async def disconnect(self) -> bool:
        self.status = DeviceStatus.DISCONNECTED
        return True
    
    async def read_status(self) -> dict:
        return {
            "status": self.status.value,
            "temperature": self._temperature
        }
```

新代码：
```python
from backend.core.hardware import BaseDevice, DeviceStatus, DeviceConfig

class TemperatureSensor(BaseDevice[None]):
    def __init__(self, device_id: str, config: DeviceConfig | dict):
        super().__init__(device_id, config)
        self._temperature = 0.0
    
    async def connect(self) -> bool:
        self._set_status(DeviceStatus.CONNECTING)
        try:
            # 连接逻辑...
            self._set_status(DeviceStatus.READY)
            return True
        except Exception as e:
            self._set_error(f"连接失败: {e}")
            return False
    
    async def disconnect(self) -> bool:
        self._set_status(DeviceStatus.DISCONNECTED)
        return True
    
    async def get_status(self) -> dict:
        status = self._get_base_status()
        status["temperature"] = self._temperature
        return status
    
    async def emergency_stop(self) -> bool:
        # 传感器无需急停，直接返回成功
        return True
    
    async def reset_alarm(self) -> bool:
        self._alarms.clear()
        return True
```
"""

# 示例2：Modbus设备驱动迁移
"""
旧代码：
```python
from backend.drivers.base import ModbusDeviceBase, DeviceConfig

class DM2CMotorDevice(ModbusDeviceBase[MotorState]):
    async def connect(self) -> bool:
        # 连接逻辑...
        pass
    
    async def emergency_stop(self) -> bool:
        # 急停逻辑...
        return await self.write_single_register(0x0200, 1)
```

新代码：
```python
from backend.core.hardware import ModbusDeviceBase, DeviceConfig, DeviceStatus

class DM2CMotorDevice(ModbusDeviceBase[MotorState]):
    async def connect(self) -> bool:
        self._set_status(DeviceStatus.CONNECTING)
        try:
            # 连接逻辑...
            self._set_status(DeviceStatus.READY)
            return True
        except Exception as e:
            self._set_error(f"连接失败: {e}")
            return False
    
    async def emergency_stop(self) -> bool:
        # 急停指令使用最高优先级（priority=0）
        success = await self.write_single_register(0x0200, 1, priority=0)
        if success:
            self._set_status(DeviceStatus.EMERGENCY_STOP)
        return success
```
"""
