"""
硬件抽象层 (Hardware Abstraction Layer, HAL)

文件名: abstract.py
路径: backend/core/
功能: 定义所有硬件设备的统一抽象接口，提供设备状态管理、软件限位等基础功能
作者: Backend Engineer Agent
创建日期: 2024-01-15
更新日期: 2026-03-14
版本: 1.0.0

模块内容：
    - DeviceStatus: 设备状态枚举，定义设备状态机
    - AbstractDevice: 硬件设备抽象基类，所有设备驱动的基类
    - AbstractStepper: 步进电机抽象接口，继承自AbstractDevice
    - SoftwareLimitConfig: 软件限位配置类，提供安全保护功能

设计参考：技术设计文档第3.1章节

依赖：
    - abc: 抽象基类支持
    - enum: 枚举类型支持
    - typing.Any: 任意类型注解
    - math: 数学运算（NaN/无穷大检查）

状态机设计：
    DISCONNECTED → CONNECTING → READY ↔ BUSY
                              ↓         ↓
                           ERROR ← EMERGENCY_STOP

使用示例：
    >>> from backend.core.abstract import AbstractDevice, DeviceStatus
    >>> 
    >>> class MyDevice(AbstractDevice):
    ...     async def connect(self) -> bool:
    ...         self.status = DeviceStatus.CONNECTING
    ...         # 连接逻辑...
    ...         self.status = DeviceStatus.READY
    ...         return True
    ...     
    ...     async def disconnect(self) -> bool:
    ...         self.status = DeviceStatus.DISCONNECTED
    ...         return True
    ...     
    ...     async def read_status(self) -> dict:
    ...         return {"status": self.status.value}
"""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any


class DeviceStatus(Enum):
    """设备状态枚举。

    状态机说明：
        DISCONNECTED → CONNECTING → READY → BUSY → READY
        任何状态都可能转变为 ERROR 或 EMERGENCY_STOP

    状态转换规则：
        - DISCONNECTED: 初始状态，只能转换到 CONNECTING
        - CONNECTING: 连接中，可转换到 READY, ERROR, DISCONNECTED
        - READY: 就绪状态，可转换到 BUSY, ERROR, EMERGENCY_STOP, DISCONNECTED
        - BUSY: 忙碌状态，可转换到 READY, ERROR, EMERGENCY_STOP
        - ERROR: 错误状态，可转换到 DISCONNECTED, READY（复位后）
        - EMERGENCY_STOP: 急停状态，可转换到 DISCONNECTED, READY（复位后）
    """

    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    READY = "ready"
    BUSY = "busy"
    ERROR = "error"
    EMERGENCY_STOP = "emergency_stop"

    @classmethod
    def get_valid_transitions(cls) -> dict["DeviceStatus", set["DeviceStatus"]]:
        """获取合法的状态转换映射。

        Returns:
            Dict[DeviceStatus, Set[DeviceStatus]]: 从每个状态可以转换到的目标状态集合
        """
        return {
            cls.DISCONNECTED: {cls.CONNECTING},
            cls.CONNECTING: {cls.READY, cls.ERROR, cls.DISCONNECTED},
            cls.READY: {cls.BUSY, cls.ERROR, cls.EMERGENCY_STOP, cls.DISCONNECTED},
            cls.BUSY: {cls.READY, cls.ERROR, cls.EMERGENCY_STOP},
            cls.ERROR: {cls.DISCONNECTED, cls.READY},
            cls.EMERGENCY_STOP: {cls.DISCONNECTED, cls.READY},
        }

    def can_transition_to(self, target: "DeviceStatus") -> bool:
        """检查是否可以转换到目标状态。

        Args:
            target: 目标状态

        Returns:
            bool: 是否允许转换
        """
        valid_targets = self.get_valid_transitions().get(self, set())
        return target in valid_targets


class SoftwareLimitConfig:
    """软件限位配置类。

    用于定义设备的软件限位，提供安全保护功能。
    支持配置验证、序列化和反序列化。
    """

    def __init__(
        self, positive_limit: float = 100.0, negative_limit: float = -100.0, enable: bool = True
    ):
        """初始化软件限位配置。

        Args:
            positive_limit: 正向限位（单位：毫米），默认为100.0mm
            negative_limit: 负向限位（单位：毫米），默认为-100.0mm
            enable: 是否启用限位检查，默认为True

        Raises:
            ValueError: 当限位参数无效时抛出
        """
        self._positive_limit = positive_limit
        self._negative_limit = negative_limit
        self._enable = enable

        # 验证配置有效性
        self._validate()

    @property
    def positive_limit(self) -> float:
        """获取正向限位。"""
        return self._positive_limit

    @positive_limit.setter
    def positive_limit(self, value: float):
        """设置正向限位。

        Args:
            value: 正向限位值

        Raises:
            ValueError: 当值无效时抛出
        """
        if not isinstance(value, (int, float)):
            raise ValueError(f"正向限位必须是数值类型，当前类型: {type(value)}")
        self._positive_limit = float(value)
        self._validate()

    @property
    def negative_limit(self) -> float:
        """获取负向限位。"""
        return self._negative_limit

    @negative_limit.setter
    def negative_limit(self, value: float):
        """设置负向限位。

        Args:
            value: 负向限位值

        Raises:
            ValueError: 当值无效时抛出
        """
        if not isinstance(value, (int, float)):
            raise ValueError(f"负向限位必须是数值类型，当前类型: {type(value)}")
        self._negative_limit = float(value)
        self._validate()

    @property
    def enable(self) -> bool:
        """获取是否启用限位检查。"""
        return self._enable

    @enable.setter
    def enable(self, value: bool):
        """设置是否启用限位检查。

        Args:
            value: 是否启用

        Raises:
            ValueError: 当值无效时抛出
        """
        if not isinstance(value, bool):
            raise ValueError(f"enable必须是布尔类型，当前类型: {type(value)}")
        self._enable = value

    def _validate(self) -> None:
        """验证限位配置的有效性。

        Raises:
            ValueError: 当配置无效时抛出
        """
        # 检查数值有效性
        if not isinstance(self._positive_limit, (int, float)):
            raise ValueError(f"正向限位必须是数值类型，当前类型: {type(self._positive_limit)}")

        if not isinstance(self._negative_limit, (int, float)):
            raise ValueError(f"负向限位必须是数值类型，当前类型: {type(self._negative_limit)}")

        # 检查NaN和无穷大
        import math

        if math.isnan(self._positive_limit) or math.isinf(self._positive_limit):
            raise ValueError("正向限位不能是NaN或无穷大")

        if math.isnan(self._negative_limit) or math.isinf(self._negative_limit):
            raise ValueError("负向限位不能是NaN或无穷大")

        # 检查逻辑关系：负向限位必须小于正向限位
        if self._negative_limit >= self._positive_limit:
            raise ValueError(
                f"负向限位({self._negative_limit})必须小于正向限位({self._positive_limit})"
            )

    def is_within_limits(self, position: float) -> bool:
        """检查位置是否在限位范围内。

        Args:
            position: 待检查的位置（单位：毫米）

        Returns:
            bool: 位置是否在限位范围内
        """
        if not self._enable:
            return True
        return self._negative_limit <= position <= self._positive_limit

    def clamp_position(self, position: float) -> float:
        """将位置限制在有效范围内。

        Args:
            position: 待限制的位置（单位：毫米）

        Returns:
            float: 限制后的位置，如果禁用限位则返回原值
        """
        if not self._enable:
            return position
        return max(self._negative_limit, min(self._positive_limit, position))

    def get_range(self) -> float:
        """获取限位范围大小。

        Returns:
            float: 正向限位与负向限位的差值
        """
        return self._positive_limit - self._negative_limit

    def to_dict(self) -> dict[str, Any]:
        """将配置序列化为字典。

        Returns:
            Dict[str, Any]: 包含配置信息的字典
        """
        return {
            "positive_limit": self._positive_limit,
            "negative_limit": self._negative_limit,
            "enable": self._enable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SoftwareLimitConfig":
        """从字典反序列化配置。

        Args:
            data: 包含配置信息的字典

        Returns:
            SoftwareLimitConfig: 配置实例

        Raises:
            ValueError: 当数据无效时抛出
        """
        if not isinstance(data, dict):
            raise ValueError(f"配置数据必须是字典类型，当前类型: {type(data)}")

        return cls(
            positive_limit=data.get("positive_limit", 100.0),
            negative_limit=data.get("negative_limit", -100.0),
            enable=data.get("enable", True),
        )

    def __repr__(self) -> str:
        """返回配置的字符串表示。"""
        return (
            f"SoftwareLimitConfig(positive_limit={self._positive_limit}, "
            f"negative_limit={self._negative_limit}, enable={self._enable})"
        )

    def __eq__(self, other: object) -> bool:
        """判断两个配置是否相等。"""
        if not isinstance(other, SoftwareLimitConfig):
            return False
        return (
            self._positive_limit == other._positive_limit
            and self._negative_limit == other._negative_limit
            and self._enable == other._enable
        )


class AbstractDevice(ABC):
    """硬件设备抽象基类。

    所有硬件设备驱动都必须继承此类并实现所有抽象方法。
    提供状态管理、错误处理和连接管理的基础功能。
    """

    def __init__(self, device_id: str, config: dict[str, Any]):
        """初始化抽象设备。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典
        """
        self.device_id = device_id
        self.config = config
        self._status = DeviceStatus.DISCONNECTED
        self._last_error: str | None = None

    @property
    def status(self) -> DeviceStatus:
        """获取设备当前状态。

        Returns:
            DeviceStatus: 当前设备状态
        """
        return self._status

    @status.setter
    def status(self, value: DeviceStatus):
        """设置设备状态（带状态转换验证）。

        Args:
            value: 新的设备状态

        Raises:
            ValueError: 当状态转换不合法时抛出（仅在严格模式下）
        """
        # 允许任何状态转换（向后兼容），但记录警告
        if not self._status.can_transition_to(value):
            import logging

            logger = logging.getLogger(__name__)
            logger.warning(
                f"非标准状态转换: {self._status.value} -> {value.value} "
                f"(设备: {self.device_id})"
            )
        self._status = value

    def set_status_strict(self, value: DeviceStatus) -> None:
        """严格设置设备状态（带状态转换验证，非法转换会抛出异常）。

        Args:
            value: 新的设备状态

        Raises:
            ValueError: 当状态转换不合法时抛出
        """
        if not self._status.can_transition_to(value):
            raise ValueError(
                f"非法状态转换: {self._status.value} -> {value.value} " f"(设备: {self.device_id})"
            )
        self._status = value

    @property
    def is_connected(self) -> bool:
        """检查设备是否已连接。

        Returns:
            bool: 设备是否已连接（状态不为DISCONNECTED）
        """
        return self._status != DeviceStatus.DISCONNECTED

    @property
    def is_ready(self) -> bool:
        """检查设备是否就绪。

        Returns:
            bool: 设备是否处于就绪状态
        """
        return self._status == DeviceStatus.READY

    @property
    def is_busy(self) -> bool:
        """检查设备是否忙碌。

        Returns:
            bool: 设备是否处于忙碌状态
        """
        return self._status == DeviceStatus.BUSY

    @property
    def is_error(self) -> bool:
        """检查设备是否处于错误状态。

        Returns:
            bool: 设备是否处于错误状态
        """
        return self._status == DeviceStatus.ERROR

    @property
    def is_emergency_stop(self) -> bool:
        """检查设备是否处于急停状态。

        Returns:
            bool: 设备是否处于急停状态
        """
        return self._status == DeviceStatus.EMERGENCY_STOP

    @property
    def last_error(self) -> str | None:
        """获取设备最后一次错误信息。

        Returns:
            Optional[str]: 最后一次错误信息，无错误时返回None
        """
        return self._last_error

    def set_error(self, error_message: str) -> None:
        """设置错误状态和错误信息。

        Args:
            error_message: 错误信息描述
        """
        self._last_error = error_message
        self._status = DeviceStatus.ERROR

    def clear_error(self) -> None:
        """清除错误信息（不改变状态）。"""
        self._last_error = None

    @abstractmethod
    async def connect(self) -> bool:
        """建立与设备的连接。

        实现要求：
        1. 连接开始时应设置状态为 CONNECTING
        2. 连接成功时应设置状态为 READY
        3. 连接失败时应设置状态为 ERROR 并记录错误信息

        Returns:
            bool: 连接是否成功
        """
        pass

    @abstractmethod
    async def disconnect(self) -> bool:
        """断开与设备的连接。

        实现要求：
        1. 断开成功后应设置状态为 DISCONNECTED
        2. 应释放所有占用的资源

        Returns:
            bool: 断开是否成功
        """
        pass

    @abstractmethod
    async def read_status(self) -> dict[str, Any]:
        """读取设备完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典，至少包含：
                - status: 设备状态字符串
                - connected: 连接状态布尔值
        """
        pass

    async def reset(self) -> bool:
        """复位设备（从错误或急停状态恢复）。

        默认实现：清除错误信息，断开连接后重新连接。
        子类可重写此方法实现特定的复位逻辑。

        Returns:
            bool: 复位是否成功
        """
        if self._status not in (DeviceStatus.ERROR, DeviceStatus.EMERGENCY_STOP):
            return False

        try:
            # 清除错误信息
            self.clear_error()

            # 断开连接
            await self.disconnect()

            # 重新连接
            return await self.connect()
        except Exception as e:
            self.set_error(f"复位失败: {str(e)}")
            return False

    def get_status_info(self) -> dict[str, Any]:
        """获取设备状态信息（非异步方法，用于快速查询）。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典
        """
        return {
            "device_id": self.device_id,
            "status": self._status.value,
            "is_connected": self.is_connected,
            "is_ready": self.is_ready,
            "is_busy": self.is_busy,
            "is_error": self.is_error,
            "is_emergency_stop": self.is_emergency_stop,
            "last_error": self._last_error,
        }


class AbstractStepper(AbstractDevice, ABC):
    """步进电机抽象接口。

    所有步进电机驱动都必须继承此类并实现所有抽象方法。
    继承自AbstractDevice，包含基础设备功能和步进电机专用功能。

    设计参考：技术设计文档第3.1.2章节

    实现要求：
        1. 所有运动方法应在执行前检查设备状态（非BUSY状态）
        2. 运动开始时应设置状态为BUSY
        3. 运动完成或失败时应设置状态为READY或ERROR
        4. 应支持软件限位检查（通过limit_config属性）
    """

    def __init__(self, device_id: str, config: dict[str, Any]):
        """初始化步进电机。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典
        """
        super().__init__(device_id, config)
        self._limit_config = SoftwareLimitConfig()

    @property
    def limit_config(self) -> SoftwareLimitConfig:
        """获取软件限位配置。

        Returns:
            SoftwareLimitConfig: 软件限位配置实例
        """
        return self._limit_config

    @limit_config.setter
    def limit_config(self, value: SoftwareLimitConfig) -> None:
        """设置软件限位配置。

        Args:
            value: 软件限位配置实例

        Raises:
            ValueError: 当配置无效时抛出
        """
        if not isinstance(value, SoftwareLimitConfig):
            raise ValueError(f"limit_config必须是SoftwareLimitConfig类型，当前类型: {type(value)}")
        self._limit_config = value

    def set_limits(self, positive: float, negative: float, enable: bool = True) -> None:
        """设置软件限位（便捷方法）。

        Args:
            positive: 正向限位（毫米）
            negative: 负向限位（毫米）
            enable: 是否启用限位检查
        """
        self._limit_config = SoftwareLimitConfig(
            positive_limit=positive, negative_limit=negative, enable=enable
        )

    def check_position_limit(self, position: float) -> bool:
        """检查位置是否在软件限位范围内。

        Args:
            position: 待检查的位置（毫米）

        Returns:
            bool: 位置是否有效
        """
        return self._limit_config.is_within_limits(position)

    @abstractmethod
    async def move_abs(self, position: float, speed: float, accel: float, decel: float) -> bool:
        """绝对位置定位。

        Args:
            position: 目标绝对位置（单位：毫米）
            speed: 运动速度（单位：毫米/秒）
            accel: 加速度（单位：毫米/秒²）
            decel: 减速度（单位：毫米/秒²）

        Returns:
            bool: 运动是否成功启动

        Raises:
            ValueError: 当位置超出软件限位范围时抛出
            RuntimeError: 当设备状态不允许运动时抛出
        """
        pass

    @abstractmethod
    async def move_rel(self, distance: float, speed: float, accel: float, decel: float) -> bool:
        """相对位置定位。

        Args:
            distance: 相对运动距离（单位：毫米）
            speed: 运动速度（单位：毫米/秒）
            accel: 加速度（单位：毫米/秒²）
            decel: 减速度（单位：毫米/秒²）

        Returns:
            bool: 运动是否成功启动

        Raises:
            RuntimeError: 当设备状态不允许运动时抛出
        """
        pass

    @abstractmethod
    async def jog(self, direction: int, speed: float) -> bool:
        """JOG点动模式。

        Args:
            direction: 运动方向，1为正方向，-1为负方向
            speed: 运动速度（单位：毫米/秒）

        Returns:
            bool: 点动是否成功启动

        Raises:
            ValueError: 当方向参数无效时抛出
            RuntimeError: 当设备状态不允许运动时抛出
        """
        pass

    @abstractmethod
    async def home(self, mode: str = "origin") -> bool:
        """回零操作。

        Args:
            mode: 回零模式，默认为"origin"
                - "origin": 回到原点
                - "positive": 回到正向限位
                - "negative": 回到负向限位

        Returns:
            bool: 回零是否成功启动

        Raises:
            RuntimeError: 当设备状态不允许运动时抛出
        """
        pass

    @abstractmethod
    async def read_position(self) -> dict[str, float]:
        """读取当前位置。

        Returns:
            Dict[str, float]: 包含位置信息的字典，至少包含：
                - position_mm: 位置（毫米）
                - position_steps: 位置（步数，可选）
        """
        pass

    @abstractmethod
    async def stop(self, emergency: bool = False) -> bool:
        """停止运动。

        Args:
            emergency: 是否为紧急停止，默认为False
                - True: 立即停止，设备进入EMERGENCY_STOP状态
                - False: 正常减速停止

        Returns:
            bool: 停止是否成功
        """
        pass

    async def wait_for_motion_complete(self, timeout: float = 30.0) -> bool:
        """等待运动完成。

        默认实现：轮询设备状态直到非BUSY状态。
        子类可重写此方法实现更高效的等待机制。

        Args:
            timeout: 超时时间（秒），默认30秒

        Returns:
            bool: 运动是否在超时前完成
        """
        import asyncio

        start_time = asyncio.get_event_loop().time()

        while self._status == DeviceStatus.BUSY:
            if asyncio.get_event_loop().time() - start_time > timeout:
                return False
            await asyncio.sleep(0.1)

        return self._status == DeviceStatus.READY

    def get_position_info(self) -> dict[str, Any]:
        """获取位置信息（非异步方法，返回缓存的位置）。

        Returns:
            Dict[str, Any]: 包含位置和限位信息的字典
        """
        return {
            "device_id": self.device_id,
            "limits": self._limit_config.to_dict(),
        }
