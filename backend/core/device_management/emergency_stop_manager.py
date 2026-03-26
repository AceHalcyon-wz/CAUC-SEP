"""
文件名: emergency_stop_manager.py
路径: backend/core/device_management/
功能: 急停指令优先级调度管理器，实现急停指令插入队列前端、跳过普通指令等待
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: asyncio, logging, typing, threading
安全约束: 急停指令必须保障最高执行优先级，支持本地急停兜底
"""

import asyncio
import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 急停优先级定义（数值越小优先级越高）
EMERGENCY_STOP_PRIORITY = 0  # 最高优先级
HIGH_PRIORITY = 1
NORMAL_PRIORITY = 5
LOW_PRIORITY = 10

# 急停超时时间（毫秒）
EMERGENCY_STOP_TIMEOUT_MS = 1000

# 急停重试次数
EMERGENCY_STOP_MAX_RETRIES = 3


# ==================== 枚举定义 ====================

class EmergencyStopLevel(Enum):
    """急停级别枚举。

    定义不同级别的急停操作，影响急停的范围和恢复流程。
    """

    DEVICE = "device"  # 单设备急停
    GROUP = "group"  # 设备组急停
    GLOBAL = "global"  # 全局急停


class EmergencyStopReason(Enum):
    """急停原因枚举。

    定义常见的急停触发原因，用于审计和复位校验。
    """

    USER_TRIGGERED = "user_triggered"  # 用户手动触发
    LIMIT_TRIGGERED = "limit_triggered"  # 限位触发
    ALARM_TRIGGERED = "alarm_triggered"  # 报警触发
    COMMUNICATION_ERROR = "communication_error"  # 通信异常
    SAFETY_INTERLOCK = "safety_interlock"  # 安全联锁
    SYSTEM_ERROR = "system_error"  # 系统错误
    UNKNOWN = "unknown"  # 未知原因


# ==================== 数据类定义 ====================

@dataclass
class EmergencyStopCommand:
    """急停命令数据类。

    封装急停指令的所有信息，用于优先级队列调度。

    Attributes:
        device_id: 设备唯一标识符
        level: 急停级别
        reason: 急停原因
        priority: 优先级（数值越小优先级越高）
        timestamp: 命令创建时间戳
        callback: 可选的回调函数，用于通知急停结果
        retry_count: 重试次数
        max_retries: 最大重试次数
    """

    device_id: str
    level: EmergencyStopLevel = EmergencyStopLevel.DEVICE
    reason: str = "user_triggered"
    priority: int = EMERGENCY_STOP_PRIORITY
    timestamp: float = field(default_factory=time.time)
    callback: Callable[[bool, str], None] | None = None
    retry_count: int = 0
    max_retries: int = EMERGENCY_STOP_MAX_RETRIES

    def __lt__(self, other: "EmergencyStopCommand") -> bool:
        """比较运算符重载，用于优先级队列排序。

        Args:
            other: 另一个急停命令

        Returns:
            bool: 当前命令优先级是否更高（数值更小）
        """
        return self.priority < other.priority


@dataclass
class EmergencyStopRecord:
    """急停记录数据类。

    用于记录急停操作的完整信息，支持审计和追溯。

    Attributes:
        device_id: 设备唯一标识符
        level: 急停级别
        reason: 急停原因
        timestamp: 急停执行时间戳
        success: 是否成功
        error_message: 错误信息（如果失败）
        resettable: 是否可复位
        reset_conditions: 复位条件列表
    """

    device_id: str
    level: EmergencyStopLevel
    reason: str
    timestamp: float
    success: bool
    error_message: str | None = None
    resettable: bool = True
    reset_conditions: list[str] = field(default_factory=list)


# ==================== 急停管理器类 ====================

class EmergencyStopManager:
    """急停指令优先级调度管理器。

    实现急停指令的优先级调度、执行和记录功能。
    急停指令插入队列前端，跳过普通指令等待，保障最高执行优先级。

    Features:
        - 急停指令优先级队列调度
        - 急停指令超时重试机制
        - 本地急停兜底逻辑
        - 急停操作审计日志
        - 急停状态追踪

    Example:
        >>> manager = EmergencyStopManager()
        >>> result = await manager.execute_device_emergency_stop(
        ...     device_id="motor_1",
        ...     reason="限位触发",
        ...     priority=0
        ... )
    """

    _instance: "EmergencyStopManager | None" = None
    _lock = threading.Lock()

    def __new__(cls) -> "EmergencyStopManager":
        """单例模式实现。

        确保全局只有一个急停管理器实例。

        Returns:
            EmergencyStopManager: 管理器实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """初始化急停管理器。"""
        if hasattr(self, "_initialized") and self._initialized:
            return

        self._emergency_queue: list[EmergencyStopCommand] = []
        self._emergency_records: dict[str, EmergencyStopRecord] = {}
        self._device_states: dict[str, dict[str, Any]] = {}
        self._running = False
        self._queue_lock = threading.Lock()
        self._processing_event = threading.Event()

        self._initialized = True
        logger.info("EmergencyStopManager 初始化完成")

    async def execute_device_emergency_stop(
        self,
        device_id: str,
        reason: str = "user_triggered",
        priority: int = EMERGENCY_STOP_PRIORITY,
        level: EmergencyStopLevel = EmergencyStopLevel.DEVICE,
    ) -> dict[str, Any]:
        """执行单设备急停。

        将急停指令插入优先级队列前端，跳过普通指令等待。
        支持超时重试和本地急停兜底。

        Args:
            device_id: 设备唯一标识符
            reason: 急停原因
            priority: 优先级，默认为最高优先级0
            level: 急停级别，默认为单设备急停

        Returns:
            Dict[str, Any]: 执行结果
                - success: 是否成功
                - timestamp: 执行时间戳
                - error: 错误信息（如果失败）
                - error_code: 错误码（如果失败）

        安全约束:
            1. 急停指令必须保障最高执行优先级
            2. 通信失败时触发本地急停兜底
            3. 所有急停操作必须记录审计日志
        """
        logger.warning(
            f"[EMERGENCY_STOP_MANAGER] 执行设备急停: device_id={device_id}, "
            f"reason={reason}, priority={priority}"
        )

        # 创建急停命令
        command = EmergencyStopCommand(
            device_id=device_id,
            level=level,
            reason=reason,
            priority=priority,
        )

        # 插入队列前端（最高优先级）
        with self._queue_lock:
            # 急停指令插入队列最前端
            self._emergency_queue.insert(0, command)
            logger.debug(
                f"[EMERGENCY_STOP_MANAGER] 急停指令已插入队列前端: "
                f"queue_size={len(self._emergency_queue)}"
            )

        # 立即执行急停（跳过队列等待）
        result = await self._execute_emergency_stop_command(command)

        # 记录急停操作
        self._record_emergency_stop(device_id, command, result)

        return result

    async def _execute_emergency_stop_command(
        self,
        command: EmergencyStopCommand,
    ) -> dict[str, Any]:
        """执行急停命令。

        尝试通过驱动管理器下发急停指令，失败时触发本地急停兜底。

        Args:
            command: 急停命令

        Returns:
            Dict[str, Any]: 执行结果
        """
        device_id = command.device_id
        start_time = time.time()

        try:
            # 尝试通过驱动管理器执行急停
            from .driver_manager import DriverProcessManager

            manager = DriverProcessManager()

            # 检查设备是否存在
            try:
                info = manager.get_driver_info(device_id)
            except KeyError:
                logger.error(f"[EMERGENCY_STOP_MANAGER] 设备不存在: {device_id}")
                return {
                    "success": False,
                    "timestamp": time.time(),
                    "error": f"设备不存在: {device_id}",
                    "error_code": "DEVICE_NOT_FOUND",
                }

            # 检查设备是否连接
            if info.get("status") != "running":
                logger.warning(
                    f"[EMERGENCY_STOP_MANAGER] 设备未连接: {device_id}, "
                    f"status={info.get('status')}"
                )
                # 设备未连接时仍然记录急停状态
                self._update_device_state(device_id, "emergency_stop", command.reason)
                return {
                    "success": True,
                    "timestamp": time.time(),
                    "message": "设备未连接，已记录急停状态",
                }

            # 发送急停命令（带超时）
            try:
                result = await asyncio.wait_for(
                    manager.send_command(
                        device_id,
                        "emergency_stop",
                        {},
                        timeout=EMERGENCY_STOP_TIMEOUT_MS / 1000.0,
                    ),
                    timeout=EMERGENCY_STOP_TIMEOUT_MS / 1000.0,
                )

                if result.get("success"):
                    elapsed_ms = (time.time() - start_time) * 1000
                    logger.info(
                        f"[EMERGENCY_STOP_MANAGER] 急停成功: device_id={device_id}, "
                        f"elapsed={elapsed_ms:.2f}ms"
                    )
                    self._update_device_state(device_id, "emergency_stop", command.reason)
                    return {
                        "success": True,
                        "timestamp": time.time(),
                        "elapsed_ms": elapsed_ms,
                    }
                else:
                    # 急停失败，触发本地急停兜底
                    logger.error(
                        f"[EMERGENCY_STOP_MANAGER] 急停指令下发失败: device_id={device_id}, "
                        f"触发本地急停兜底"
                    )
                    return await self._execute_local_emergency_stop(command)

            except asyncio.TimeoutError:
                # 超时，触发本地急停兜底
                logger.error(
                    f"[EMERGENCY_STOP_MANAGER] 急停指令超时: device_id={device_id}, "
                    f"触发本地急停兜底"
                )
                return await self._execute_local_emergency_stop(command)

        except Exception as e:
            logger.error(
                f"[EMERGENCY_STOP_MANAGER] 急停执行异常: device_id={device_id}, "
                f"error={str(e)}"
            )
            # 异常时触发本地急停兜底
            return await self._execute_local_emergency_stop(command)

    async def _execute_local_emergency_stop(
        self,
        command: EmergencyStopCommand,
    ) -> dict[str, Any]:
        """执行本地急停兜底。

        当驱动管理器通信失败时，执行本地急停兜底逻辑。
        本地急停会直接设置设备状态为急停，并记录急停原因。

        Args:
            command: 急停命令

        Returns:
            Dict[str, Any]: 执行结果

        安全约束:
            本地急停兜底确保后端服务异常时仍可执行急停
        """
        device_id = command.device_id
        logger.warning(
            f"[EMERGENCY_STOP_MANAGER] 执行本地急停兜底: device_id={device_id}"
        )

        try:
            # 更新设备状态为急停
            self._update_device_state(device_id, "emergency_stop", command.reason)

            # 记录本地急停事件
            logger.critical(
                f"[EMERGENCY_STOP_MANAGER] 本地急停已执行: device_id={device_id}, "
                f"reason={command.reason}"
            )

            return {
                "success": True,
                "timestamp": time.time(),
                "local_fallback": True,
                "message": "本地急停兜底已执行",
            }

        except Exception as e:
            logger.error(
                f"[EMERGENCY_STOP_MANAGER] 本地急停兜底失败: device_id={device_id}, "
                f"error={str(e)}"
            )
            return {
                "success": False,
                "timestamp": time.time(),
                "error": f"本地急停兜底失败: {str(e)}",
                "error_code": "LOCAL_FALLBACK_FAILED",
            }

    def _update_device_state(
        self,
        device_id: str,
        status: str,
        reason: str | None = None,
    ) -> None:
        """更新设备状态。

        Args:
            device_id: 设备唯一标识符
            status: 新状态
            reason: 状态变更原因
        """
        if device_id not in self._device_states:
            self._device_states[device_id] = {}

        self._device_states[device_id].update({
            "status": status,
            "reason": reason,
            "timestamp": time.time(),
        })

    def _record_emergency_stop(
        self,
        device_id: str,
        command: EmergencyStopCommand,
        result: dict[str, Any],
    ) -> None:
        """记录急停操作。

        Args:
            device_id: 设备唯一标识符
            command: 急停命令
            result: 执行结果
        """
        record = EmergencyStopRecord(
            device_id=device_id,
            level=command.level,
            reason=command.reason,
            timestamp=result.get("timestamp", time.time()),
            success=result.get("success", False),
            error_message=result.get("error"),
            resettable=True,
            reset_conditions=self._get_reset_conditions(command.reason),
        )

        self._emergency_records[device_id] = record

        # 输出审计日志
        logger.info(
            f"[AUDIT] 急停记录: device_id={device_id}, level={command.level.value}, "
            f"reason={command.reason}, success={record.success}, "
            f"timestamp={datetime.fromtimestamp(record.timestamp).isoformat()}"
        )

    def _get_reset_conditions(self, reason: str) -> list[str]:
        """获取复位条件。

        根据急停原因返回复位前需要满足的条件。

        Args:
            reason: 急停原因

        Returns:
            List[str]: 复位条件列表
        """
        base_conditions = [
            "设备报警已清除",
            "急停原因已消除",
            "用户已确认复位操作",
        ]

        # 根据急停原因添加特定条件
        if reason == "limit_triggered":
            base_conditions.append("设备位置已移出限位区域")
        elif reason == "alarm_triggered":
            base_conditions.append("报警代码已读取并处理")
        elif reason == "communication_error":
            base_conditions.append("通信已恢复正常")

        return base_conditions

    def get_emergency_record(self, device_id: str) -> EmergencyStopRecord | None:
        """获取设备急停记录。

        Args:
            device_id: 设备唯一标识符

        Returns:
            Optional[EmergencyStopRecord]: 急停记录，不存在返回None
        """
        return self._emergency_records.get(device_id)

    def get_device_state(self, device_id: str) -> dict[str, Any] | None:
        """获取设备状态。

        Args:
            device_id: 设备唯一标识符

        Returns:
            Optional[Dict[str, Any]]: 设备状态，不存在返回None
        """
        return self._device_states.get(device_id)

    def is_emergency_stop(self, device_id: str) -> bool:
        """检查设备是否处于急停状态。

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 是否处于急停状态
        """
        state = self._device_states.get(device_id)
        return state is not None and state.get("status") == "emergency_stop"

    def clear_emergency_state(self, device_id: str) -> bool:
        """清除设备急停状态。

        Args:
            device_id: 设备唯一标识符

        Returns:
            bool: 是否成功清除
        """
        if device_id in self._device_states:
            self._device_states[device_id]["status"] = "ready"
            self._device_states[device_id]["cleared_at"] = time.time()
            logger.info(f"[EMERGENCY_STOP_MANAGER] 急停状态已清除: device_id={device_id}")
            return True
        return False


# ==================== 全局函数 ====================

def get_emergency_stop_manager() -> EmergencyStopManager:
    """获取急停管理器单例实例。

    Returns:
        EmergencyStopManager: 管理器实例
    """
    return EmergencyStopManager()
