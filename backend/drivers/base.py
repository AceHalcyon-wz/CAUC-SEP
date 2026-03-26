"""
文件名: base.py
路径: backend/drivers/base.py
功能: 设备驱动抽象基类，定义统一的设备接口规范（已废弃）
作者: Backend Engineer Agent
创建日期: 2026-03-25
最后更新: 2026-03-26
依赖: abc, typing, dataclasses, enum, logging

⚠️ 废弃警告：
本模块已废弃，请使用统一的设备抽象基类：
- backend.core.hardware.BaseDevice
- backend.core.hardware.ModbusDeviceBase
- backend.core.hardware.DeviceStatus
- backend.core.hardware.DeviceConfig

迁移指南：backend.core.hardware.migration_guide

废弃时间：2026-03-26
移除时间：2026-05-26

安全约束:
- 所有设备驱动必须继承此抽象基类
- 必须实现connect、disconnect、get_status、emergency_stop通用方法
- 急停相关代码必须保障最高执行优先级
"""

from __future__ import annotations

import logging
import time
import warnings
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Generic, TypeVar

# 发出废弃警告
warnings.warn(
    "backend.drivers.base 模块已废弃，请使用 backend.core.hardware 模块。"
    "迁移指南：backend.core.hardware.migration_guide",
    DeprecationWarning,
    stacklevel=2
)

logger = logging.getLogger(__name__)

# 类型变量，用于泛型设备状态
DeviceStateType = TypeVar("DeviceStateType")


class DeviceStatus(Enum):
    """
    设备状态枚举（已废弃）。

    ⚠️ 请使用 backend.core.hardware.DeviceStatus
    
    废弃时间：2026-03-26
    移除时间：2026-05-26

    Attributes:
        DISCONNECTED: 未连接状态
        CONNECTING: 连接中状态
        READY: 就绪状态，可接收指令
        BUSY: 忙碌状态，正在执行指令
        ERROR: 错误状态
        EMERGENCY_STOP: 急停状态
        ALARM: 报警状态
        INITIALIZING: 初始化中状态
        CALIBRATING: 校准中状态
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"
    ALARM = "alarm"
    INITIALIZING = "initializing"
    CALIBRATING = "calibrating"


class DeviceType(Enum):
    """
    设备类型枚举。

    定义系统中支持的设备类型。

    Attributes:
        MOTOR: 步进电机
        ELECTROMAGNET: 电磁铁
        TEMPERATURE_CONTROLLER: 温控器
        PIEZO_CONTROLLER: 压电控制器
        POWER_SUPPLY: 电源
        SENSOR: 传感器
        UNKNOWN: 未知设备
    """

    MOTOR = "motor"
    ELECTROMAGNET = "electromagnet"
    TEMPERATURE_CONTROLLER = "temperature_controller"
    PIEZO_CONTROLLER = "piezo_controller"
    POWER_SUPPLY = "power_supply"
    SENSOR = "sensor"
    UNKNOWN = "unknown"


class ConnectionType(Enum):
    """
    连接类型枚举。

    Attributes:
        SERIAL: 串口连接（RS232/RS485）
        ETHERNET: 以太网连接（TCP/IP）
        USB: USB连接
        GPIB: GPIB连接
        SIMULATION: 仿真模式
    """

    SERIAL = "serial"
    ETHERNET = "ethernet"
    USB = "usb"
    GPIB = "gpib"
    SIMULATION = "simulation"


@dataclass
class DeviceInfo:
    """
    设备信息数据类。

    存储设备的基本信息。

    Attributes:
        device_id: 设备唯一标识
        device_name: 设备名称
        device_type: 设备类型
        manufacturer: 制造商
        model: 型号
        serial_number: 序列号
        firmware_version: 固件版本
        connection_type: 连接类型
    """

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
    """
    设备配置数据类。

    存储设备的配置参数。

    Attributes:
        device_id: 设备唯一标识
        connection_params: 连接参数字典
        simulation: 是否仿真模式
        auto_reconnect: 是否自动重连
        reconnect_interval: 重连间隔（秒）
        timeout: 通信超时时间（秒）
        max_retries: 最大重试次数
    """

    device_id: str
    connection_params: dict[str, Any] = field(default_factory=dict)
    simulation: bool = True
    auto_reconnect: bool = True
    reconnect_interval: float = 5.0
    timeout: float = 1.0
    max_retries: int = 3


@dataclass
class DeviceAlarm:
    """
    设备报警数据类。

    存储设备的报警信息。

    Attributes:
        alarm_code: 报警代码
        alarm_message: 报警消息
        alarm_level: 报警级别（0=信息, 1=警告, 2=错误, 3=严重）
        timestamp: 报警时间戳
        is_active: 是否活动报警
    """

    alarm_code: int
    alarm_message: str
    alarm_level: int = 1
    timestamp: float = field(default_factory=time.time)
    is_active: bool = True


@dataclass
class DeviceParameter:
    """
    设备参数数据类。

    存储设备的可配置参数。

    Attributes:
        name: 参数名称
        value: 参数值
        min_value: 最小值
        max_value: 最大值
        unit: 单位
        description: 描述
        is_readonly: 是否只读
    """

    name: str
    value: Any
    min_value: Any | None = None
    max_value: Any | None = None
    unit: str = ""
    description: str = ""
    is_readonly: bool = False


class BaseDevice(ABC, Generic[DeviceStateType]):
    """
    设备驱动抽象基类。

    所有设备驱动必须继承此基类，并实现所有抽象方法。
    提供统一的设备接口规范，确保所有设备驱动具有一致的行为。

    Attributes:
        device_id: 设备唯一标识
        config: 设备配置
        status: 设备状态
        info: 设备信息
        _last_error: 最后一次错误信息
        _status_callback: 状态变化回调函数
        _alarm_callback: 报警回调函数

    安全约束:
        - 所有设备控制相关代码必须包含异常兜底逻辑、参数合法性校验
        - 急停相关代码必须保障最高执行优先级
        - 高危操作必须包含二次校验、日志审计逻辑

    Example:
        >>> class MotorDevice(BaseDevice[MotorState]):
        ...     async def connect(self) -> bool:
        ...         # 实现连接逻辑
        ...         pass
        ...     async def disconnect(self) -> bool:
        ...         # 实现断开逻辑
        ...         pass
    """

    def __init__(self, device_id: str, config: DeviceConfig | dict[str, Any]) -> None:
        """
        初始化设备驱动。

        Args:
            device_id: 设备唯一标识
            config: 设备配置，可以是DeviceConfig对象或字典
        """
        self.device_id = device_id

        # 处理配置参数
        if isinstance(config, DeviceConfig):
            self.config = config
        else:
            self.config = DeviceConfig(device_id=device_id, **config)

        # 设备状态
        self.status = DeviceStatus.DISCONNECTED
        self._state: DeviceStateType | None = None

        # 设备信息
        self.info = DeviceInfo(device_id=device_id)

        # 错误和报警
        self._last_error: str | None = None
        self._alarms: list[DeviceAlarm] = []

        # 回调函数
        self._status_callback: Callable[[dict[str, Any]], None] | None = None
        self._alarm_callback: Callable[[DeviceAlarm], None] | None = None

        # 连接时间戳
        self._connected_at: float | None = None
        self._last_activity: float = time.time()

        logger.info(f"BaseDevice初始化: device_id={device_id}")

    # ==================== 抽象方法（必须实现） ====================

    @abstractmethod
    async def connect(self) -> bool:
        """
        建立与设备的连接。

        Returns:
            bool: 连接是否成功

        安全约束:
            - 连接失败时必须设置正确的错误状态
            - 必须记录连接日志
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """
        断开与设备的连接。

        Returns:
            bool: 断开是否成功

        安全约束:
            - 断开前应停止所有正在执行的操作
            - 必须释放所有占用的资源
        """
        pass

    @abstractmethod
    async def get_status(self) -> dict[str, Any]:
        """
        获取设备完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典

        安全约束:
            - 状态获取失败时必须返回包含错误信息的字典
            - 不得抛出异常
        """
        pass

    @abstractmethod
    async def emergency_stop(self) -> bool:
        """
        执行紧急停止。

        立即停止设备所有操作，进入安全状态。

        Returns:
            bool: 急停是否成功

        安全约束:
            - 急停指令必须具有最高执行优先级
            - 急停失败时必须记录严重错误日志
            - 必须包含异常兜底逻辑
        """
        pass

    @abstractmethod
    async def reset_emergency(self) -> bool:
        """
        复位紧急停止状态。

        Returns:
            bool: 复位是否成功

        安全约束:
            - 复位前应检查设备状态，确保安全
            - 必须清除所有活动报警
        """
        pass

    # ==================== 可选方法（建议实现） ====================

    async def initialize(self) -> bool:
        """
        初始化设备。

        执行设备初始化流程，如回零、参数加载等。

        Returns:
            bool: 初始化是否成功
        """
        logger.info(f"设备初始化: device_id={self.device_id}")
        self.status = DeviceStatus.INITIALIZING
        try:
            # 子类可重写此方法实现具体的初始化逻辑
            self.status = DeviceStatus.READY
            return True
        except Exception as e:
            self._last_error = str(e)
            self.status = DeviceStatus.ERROR
            logger.error(f"设备初始化失败: device_id={self.device_id}, error={e}")
            return False

    async def reset(self) -> bool:
        """
        复位设备。

        将设备恢复到初始状态。

        Returns:
            bool: 复位是否成功
        """
        logger.info(f"设备复位: device_id={self.device_id}")
        try:
            # 清除报警
            self._alarms.clear()
            self._last_error = None

            # 子类可重写此方法实现具体的复位逻辑
            if self.status == DeviceStatus.ERROR:
                self.status = DeviceStatus.READY

            return True
        except Exception as e:
            self._last_error = str(e)
            logger.error(f"设备复位失败: device_id={self.device_id}, error={e}")
            return False

    async def get_parameters(self) -> list[DeviceParameter]:
        """
        获取设备所有可配置参数。

        Returns:
            List[DeviceParameter]: 参数列表
        """
        # 子类应重写此方法返回实际的参数列表
        return []

    async def set_parameter(self, name: str, value: Any) -> bool:
        """
        设置设备参数。

        Args:
            name: 参数名称
            value: 参数值

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 参数名称无效或值超出范围
        """
        logger.info(f"设置参数: device_id={self.device_id}, name={name}, value={value}")
        # 子类应重写此方法实现具体的参数设置逻辑
        raise NotImplementedError(f"参数设置未实现: {name}")

    async def get_alarms(self) -> list[DeviceAlarm]:
        """
        获取设备所有活动报警。

        Returns:
            List[DeviceAlarm]: 报警列表
        """
        return [alarm for alarm in self._alarms if alarm.is_active]

    async def clear_alarms(self) -> bool:
        """
        清除所有活动报警。

        Returns:
            bool: 清除是否成功
        """
        logger.info(f"清除报警: device_id={self.device_id}")
        for alarm in self._alarms:
            alarm.is_active = False

        if self.status == DeviceStatus.ALARM:
            self.status = DeviceStatus.READY

        return True

    async def self_test(self) -> dict[str, Any]:
        """
        执行设备自检。

        Returns:
            Dict[str, Any]: 自检结果，包含各项测试结果
        """
        logger.info(f"设备自检: device_id={self.device_id}")
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "connected": self.is_connected,
            "alarms_count": len(await self.get_alarms()),
            "last_error": self._last_error,
            "test_result": "pass" if self.is_connected else "not_connected",
        }

    # ==================== 属性访问器 ====================

    @property
    def is_connected(self) -> bool:
        """
        检查设备是否已连接。

        Returns:
            bool: 是否已连接
        """
        return self.status not in (
            DeviceStatus.DISCONNECTED,
            DeviceStatus.CONNECTING,
        )

    @property
    def is_ready(self) -> bool:
        """
        检查设备是否就绪。

        Returns:
            bool: 是否就绪（可接收指令）
        """
        return self.status == DeviceStatus.READY

    @property
    def is_busy(self) -> bool:
        """
        检查设备是否忙碌。

        Returns:
            bool: 是否正在执行指令
        """
        return self.status == DeviceStatus.BUSY

    @property
    def is_error(self) -> bool:
        """
        检查设备是否处于错误状态。

        Returns:
            bool: 是否处于错误状态
        """
        return self.status == DeviceStatus.ERROR

    @property
    def is_emergency_stop(self) -> bool:
        """
        检查设备是否处于急停状态。

        Returns:
            bool: 是否处于急停状态
        """
        return self.status == DeviceStatus.EMERGENCY_STOP

    @property
    def is_alarm(self) -> bool:
        """
        检查设备是否处于报警状态。

        Returns:
            bool: 是否处于报警状态
        """
        return self.status == DeviceStatus.ALARM or len(self._alarms) > 0

    @property
    def last_error(self) -> str | None:
        """
        获取最后一次错误信息。

        Returns:
            Optional[str]: 错误信息，无错误返回None
        """
        return self._last_error

    @property
    def state(self) -> DeviceStateType | None:
        """
        获取设备状态对象。

        Returns:
            Optional[DeviceStateType]: 设备状态对象
        """
        return self._state

    # ==================== 回调函数设置 ====================

    def set_status_callback(
        self, callback: Callable[[dict[str, Any]], None] | None
    ) -> None:
        """
        设置状态变化回调函数。

        Args:
            callback: 回调函数，接收状态字典
        """
        self._status_callback = callback

    def set_alarm_callback(
        self, callback: Callable[[DeviceAlarm], None] | None
    ) -> None:
        """
        设置报警回调函数。

        Args:
            callback: 回调函数，接收报警对象
        """
        self._alarm_callback = callback

    # ==================== 内部方法 ====================

    def _set_status(self, status: DeviceStatus) -> None:
        """
        设置设备状态并触发回调。

        Args:
            status: 新状态
        """
        old_status = self.status
        self.status = status
        self._last_activity = time.time()

        if old_status != status:
            logger.debug(
                f"设备状态变化: device_id={self.device_id}, "
                f"old={old_status.value}, new={status.value}"
            )
            self._notify_status_change()

    def _add_alarm(self, alarm: DeviceAlarm) -> None:
        """
        添加报警。

        Args:
            alarm: 报警对象
        """
        self._alarms.append(alarm)
        logger.warning(
            f"设备报警: device_id={self.device_id}, "
            f"code={alarm.alarm_code}, message={alarm.alarm_message}"
        )

        if self._alarm_callback:
            try:
                self._alarm_callback(alarm)
            except Exception as e:
                logger.error(f"报警回调函数异常: {e}")

    def _set_error(self, error: str) -> None:
        """
        设置错误信息。

        Args:
            error: 错误信息
        """
        self._last_error = error
        logger.error(f"设备错误: device_id={self.device_id}, error={error}")

    def _notify_status_change(self) -> None:
        """
        通知状态变化。
        """
        if self._status_callback:
            try:
                status_data = self._get_base_status()
                self._status_callback(status_data)
            except Exception as e:
                logger.error(f"状态回调函数异常: {e}")

    def _get_base_status(self) -> dict[str, Any]:
        """
        获取基础状态信息。

        Returns:
            Dict[str, Any]: 基础状态字典
        """
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "is_connected": self.is_connected,
            "is_ready": self.is_ready,
            "is_busy": self.is_busy,
            "is_error": self.is_error,
            "is_emergency_stop": self.is_emergency_stop,
            "is_alarm": self.is_alarm,
            "last_error": self._last_error,
            "alarms_count": len(self._alarms),
            "connected_at": self._connected_at,
            "last_activity": self._last_activity,
        }

    def __repr__(self) -> str:
        """
        返回设备对象的字符串表示。

        Returns:
            str: 字符串表示
        """
        return (
            f"{self.__class__.__name__}("
            f"device_id='{self.device_id}', "
            f"status={self.status.value}, "
            f"connected={self.is_connected})"
        )


class ModbusDeviceBase(BaseDevice[DeviceStateType]):
    """
    Modbus设备驱动抽象基类。

    继承自BaseDevice，提供Modbus通信相关的通用功能。
    所有Modbus设备驱动应继承此基类。

    Attributes:
        slave_id: Modbus从站地址
        port: 串口号
        baudrate: 波特率

    Example:
        >>> class DM2CMotorDevice(ModbusDeviceBase[MotorState]):
        ...     async def connect(self) -> bool:
        ...         # 实现Modbus连接逻辑
        ...         pass
    """

    def __init__(
        self,
        device_id: str,
        config: DeviceConfig | dict[str, Any],
        slave_id: int = 1,
    ) -> None:
        """
        初始化Modbus设备驱动。

        Args:
            device_id: 设备唯一标识
            config: 设备配置
            slave_id: Modbus从站地址，默认1
        """
        super().__init__(device_id, config)

        # Modbus参数
        self.slave_id = slave_id
        self.port = self.config.connection_params.get("port", "COM1")
        self.baudrate = self.config.connection_params.get("baudrate", 38400)

        # 更新设备信息
        self.info.connection_type = ConnectionType.SERIAL

        logger.info(
            f"ModbusDeviceBase初始化: device_id={device_id}, "
            f"slave_id={slave_id}, port={self.port}, baudrate={self.baudrate}"
        )

    async def read_holding_registers(
        self, address: int, count: int = 1
    ) -> list[int] | None:
        """
        读取保持寄存器。

        Args:
            address: 起始地址
            count: 读取数量，默认1

        Returns:
            Optional[List[int]]: 寄存器值列表，失败返回None
        """
        # 子类应重写此方法实现具体的Modbus读取逻辑
        raise NotImplementedError("read_holding_registers未实现")

    async def write_single_register(self, address: int, value: int) -> bool:
        """
        写入单个寄存器。

        Args:
            address: 寄存器地址
            value: 写入值

        Returns:
            bool: 写入是否成功
        """
        # 子类应重写此方法实现具体的Modbus写入逻辑
        raise NotImplementedError("write_single_register未实现")

    async def write_multiple_registers(
        self, address: int, values: list[int]
    ) -> bool:
        """
        写入多个寄存器。

        Args:
            address: 起始地址
            values: 写入值列表

        Returns:
            bool: 写入是否成功
        """
        # 子类应重写此方法实现具体的Modbus写入逻辑
        raise NotImplementedError("write_multiple_registers未实现")


class AsyncDeviceBase(BaseDevice[DeviceStateType]):
    """
    异步设备驱动抽象基类。

    继承自BaseDevice，提供异步操作相关的通用功能。
    支持后台任务、定时刷新等异步特性。

    Attributes:
        _background_tasks: 后台任务列表
        _refresh_interval: 状态刷新间隔（秒）
    """

    def __init__(
        self,
        device_id: str,
        config: DeviceConfig | dict[str, Any],
        refresh_interval: float = 0.1,
    ) -> None:
        """
        初始化异步设备驱动。

        Args:
            device_id: 设备唯一标识
            config: 设备配置
            refresh_interval: 状态刷新间隔（秒），默认0.1秒
        """
        super().__init__(device_id, config)

        self._background_tasks: list[Any] = []
        self._refresh_interval = refresh_interval
        self._is_refreshing = False

    async def start_refresh(self) -> None:
        """
        启动状态定时刷新。
        """
        if self._is_refreshing:
            return

        self._is_refreshing = True
        logger.info(f"启动状态刷新: device_id={self.device_id}")

    async def stop_refresh(self) -> None:
        """
        停止状态定时刷新。
        """
        self._is_refreshing = False
        logger.info(f"停止状态刷新: device_id={self.device_id}")

    async def cancel_background_tasks(self) -> None:
        """
        取消所有后台任务。
        """
        for task in self._background_tasks:
            if not task.done():
                task.cancel()

        self._background_tasks.clear()
        logger.info(f"取消后台任务: device_id={self.device_id}")


# ==================== 便捷函数 ====================


def create_device_config(
    device_id: str,
    port: str = "COM1",
    baudrate: int = 38400,
    simulation: bool = True,
    **kwargs: Any,
) -> DeviceConfig:
    """
    创建设备配置的便捷函数。

    Args:
        device_id: 设备唯一标识
        port: 串口号
        baudrate: 波特率
        simulation: 是否仿真模式
        **kwargs: 其他配置参数

    Returns:
        DeviceConfig: 设备配置对象

    Example:
        >>> config = create_device_config("motor_1", port="COM1", baudrate=38400)
    """
    return DeviceConfig(
        device_id=device_id,
        connection_params={"port": port, "baudrate": baudrate, **kwargs},
        simulation=simulation,
    )
