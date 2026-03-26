"""
文件名: exception_protection.py
路径: backend/core/
功能: 设备异常分级保护机制，实现异常等级定义、自动保护逻辑、通信中断保护、告警日志
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+, asyncio, logging, dataclasses
安全约束: 所有保护动作必须包含异常兜底逻辑，高危操作必须包含二次校验、日志审计逻辑

异常等级体系：
    - WARNING（预警）：告警提示，不影响设备运行
    - ALARM（报警）：需要降额运行或单设备停机
    - FATAL（致命故障）：触发全局急停

分级保护动作：
    - 告警（WARNING）：记录日志，发送通知
    - 降额（ALARM）：降低设备运行参数
    - 单设备停机（ALARM）：停止当前设备
    - 全局急停（FATAL）：停止所有设备
"""

import asyncio
import json
import logging
import sqlite3
import time
import traceback
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from .abstract import AbstractDevice, DeviceStatus

logger = logging.getLogger(__name__)


# ==================== 异常等级定义 ====================

class ExceptionLevel(Enum):
    """
    异常等级枚举。
    
    定义设备异常的严重程度，对应不同的保护动作。
    
    Attributes:
        WARNING: 预警等级，需要关注但不影响设备运行
        ALARM: 报警等级，需要采取保护措施（降额/停机）
        FATAL: 致命故障等级，触发全局急停
    """
    
    WARNING = "warning"
    ALARM = "alarm"
    FATAL = "fatal"
    
    @classmethod
    def from_string(cls, level_str: str) -> "ExceptionLevel":
        """
        从字符串创建异常等级。
        
        Args:
            level_str: 异常等级字符串（不区分大小写）
        
        Returns:
            ExceptionLevel: 异常等级枚举值
        
        Raises:
            ValueError: 无效的异常等级字符串
        """
        level_map = {
            "warning": cls.WARNING,
            "alarm": cls.ALARM,
            "fatal": cls.FATAL,
        }
        level_lower = level_str.lower()
        if level_lower not in level_map:
            raise ValueError(
                f"无效的异常等级: {level_str}，有效值: {list(level_map.keys())}"
            )
        return level_map[level_lower]


class ProtectionAction(Enum):
    """
    保护动作枚举。
    
    定义异常触发时执行的保护动作类型。
    
    Attributes:
        LOG_ONLY: 仅记录日志，不执行其他动作
        NOTIFY: 发送告警通知
        DERATE: 降额运行（降低设备参数）
        SINGLE_STOP: 单设备停机
        GLOBAL_ESTOP: 全局急停（停止所有设备）
    """
    
    LOG_ONLY = "log_only"
    NOTIFY = "notify"
    DERATE = "derate"
    SINGLE_STOP = "single_stop"
    GLOBAL_ESTOP = "global_estop"
    
    @classmethod
    def get_actions_for_level(cls, level: ExceptionLevel) -> list["ProtectionAction"]:
        """
        根据异常等级获取对应的保护动作列表。
        
        Args:
            level: 异常等级
        
        Returns:
            List[ProtectionAction]: 保护动作列表（按执行顺序）
        """
        action_map = {
            ExceptionLevel.WARNING: [cls.LOG_ONLY, cls.NOTIFY],
            ExceptionLevel.ALARM: [cls.LOG_ONLY, cls.NOTIFY, cls.DERATE, cls.SINGLE_STOP],
            ExceptionLevel.FATAL: [cls.LOG_ONLY, cls.NOTIFY, cls.GLOBAL_ESTOP],
        }
        return action_map.get(level, [cls.LOG_ONLY])


class ExceptionType(Enum):
    """
    异常类型枚举。
    
    定义设备可能出现的异常类型。
    
    Attributes:
        MOTOR_ALARM: 步进电机报警
        ELECTROMAGNET_OVERCURRENT: 电磁铁过流
        ELECTROMAGNET_OVERTEMPERATURE: 电磁铁过温
        TEMPERATURE_CONTROLLER_OVERTEMP: 温控器超温
        PICOAMMETER_COMM_ERROR: 皮安表通信异常
        PIEZO_CONTROLLER_FAULT: 压电控制器故障
        COMMUNICATION_INTERRUPT: 通信中断
        SERIAL_DISCONNECT: 串口断连
        DEVICE_TIMEOUT: 设备超时
        UNKNOWN: 未知异常
    """
    
    MOTOR_ALARM = "motor_alarm"
    ELECTROMAGNET_OVERCURRENT = "electromagnet_overcurrent"
    ELECTROMAGNET_OVERTEMPERATURE = "electromagnet_overtemperature"
    TEMPERATURE_CONTROLLER_OVERTEMP = "temperature_controller_overtemp"
    PICOAMMETER_COMM_ERROR = "picoammeter_comm_error"
    PIEZO_CONTROLLER_FAULT = "piezo_controller_fault"
    COMMUNICATION_INTERRUPT = "communication_interrupt"
    SERIAL_DISCONNECT = "serial_disconnect"
    DEVICE_TIMEOUT = "device_timeout"
    UNKNOWN = "unknown"
    
    @classmethod
    def get_default_level(cls, exception_type: "ExceptionType") -> ExceptionLevel:
        """
        获取异常类型的默认等级。
        
        Args:
            exception_type: 异常类型
        
        Returns:
            ExceptionLevel: 默认异常等级
        """
        level_map = {
            cls.MOTOR_ALARM: ExceptionLevel.ALARM,
            cls.ELECTROMAGNET_OVERCURRENT: ExceptionLevel.ALARM,
            cls.ELECTROMAGNET_OVERTEMPERATURE: ExceptionLevel.ALARM,
            cls.TEMPERATURE_CONTROLLER_OVERTEMP: ExceptionLevel.ALARM,
            cls.PICOAMMETER_COMM_ERROR: ExceptionLevel.WARNING,
            cls.PIEZO_CONTROLLER_FAULT: ExceptionLevel.ALARM,
            cls.COMMUNICATION_INTERRUPT: ExceptionLevel.ALARM,
            cls.SERIAL_DISCONNECT: ExceptionLevel.ALARM,
            cls.DEVICE_TIMEOUT: ExceptionLevel.WARNING,
            cls.UNKNOWN: ExceptionLevel.WARNING,
        }
        return level_map.get(exception_type, ExceptionLevel.WARNING)


# ==================== 异常事件数据类 ====================

@dataclass
class ExceptionEvent:
    """
    异常事件数据类。
    
    记录异常发生的完整信息，用于日志记录和追溯。
    
    Attributes:
        event_id: 事件唯一标识（时间戳+随机数）
        exception_type: 异常类型
        exception_level: 异常等级
        device_id: 设备ID
        message: 异常消息
        details: 异常详情字典
        timestamp: 事件时间戳
        protection_actions: 执行的保护动作列表
        resolved: 是否已解决
        resolved_at: 解决时间
        resolved_by: 解决方式
    """
    
    exception_type: ExceptionType
    exception_level: ExceptionLevel
    device_id: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"{int(time.time() * 1000)}_{id(object())}")
    timestamp: float = field(default_factory=time.time)
    protection_actions: list[ProtectionAction] = field(default_factory=list)
    resolved: bool = False
    resolved_at: float | None = None
    resolved_by: str | None = None
    
    def to_dict(self) -> dict[str, Any]:
        """
        序列化为字典。
        
        Returns:
            Dict[str, Any]: 序列化后的字典
        """
        return {
            "event_id": self.event_id,
            "exception_type": self.exception_type.value,
            "exception_level": self.exception_level.value,
            "device_id": self.device_id,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp,
            "timestamp_iso": datetime.fromtimestamp(self.timestamp).isoformat(),
            "protection_actions": [action.value for action in self.protection_actions],
            "resolved": self.resolved,
            "resolved_at": self.resolved_at,
            "resolved_at_iso": (
                datetime.fromtimestamp(self.resolved_at).isoformat() 
                if self.resolved_at else None
            ),
            "resolved_by": self.resolved_by,
        }
    
    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ExceptionEvent":
        """
        从字典反序列化。
        
        Args:
            data: 字典数据
        
        Returns:
            ExceptionEvent: 异常事件实例
        """
        return cls(
            event_id=data.get("event_id", ""),
            exception_type=ExceptionType(data.get("exception_type", "unknown")),
            exception_level=ExceptionLevel(data.get("exception_level", "warning")),
            device_id=data.get("device_id", ""),
            message=data.get("message", ""),
            details=data.get("details", {}),
            timestamp=data.get("timestamp", time.time()),
            protection_actions=[
                ProtectionAction(action) 
                for action in data.get("protection_actions", [])
            ],
            resolved=data.get("resolved", False),
            resolved_at=data.get("resolved_at"),
            resolved_by=data.get("resolved_by"),
        )


@dataclass
class DeviceExceptionConfig:
    """
    设备异常配置数据类。
    
    定义单个设备的异常检测和保护配置。
    
    Attributes:
        device_id: 设备ID
        device_type: 设备类型
        enabled: 是否启用异常保护
        warning_thresholds: 预警阈值字典
        alarm_thresholds: 报警阈值字典
        fatal_thresholds: 致命故障阈值字典
        auto_recovery: 是否启用自动恢复
        recovery_delay: 恢复延迟时间（秒）
        max_recovery_attempts: 最大恢复尝试次数
    """
    
    device_id: str
    device_type: str
    enabled: bool = True
    warning_thresholds: dict[str, float] = field(default_factory=dict)
    alarm_thresholds: dict[str, float] = field(default_factory=dict)
    fatal_thresholds: dict[str, float] = field(default_factory=dict)
    auto_recovery: bool = True
    recovery_delay: float = 5.0
    max_recovery_attempts: int = 3
    
    def to_dict(self) -> dict[str, Any]:
        """
        序列化为字典。
        
        Returns:
            Dict[str, Any]: 序列化后的字典
        """
        return {
            "device_id": self.device_id,
            "device_type": self.device_type,
            "enabled": self.enabled,
            "warning_thresholds": self.warning_thresholds,
            "alarm_thresholds": self.alarm_thresholds,
            "fatal_thresholds": self.fatal_thresholds,
            "auto_recovery": self.auto_recovery,
            "recovery_delay": self.recovery_delay,
            "max_recovery_attempts": self.max_recovery_attempts,
        }


# ==================== 异常日志记录器 ====================

class ExceptionLogger:
    """
    异常日志记录器。
    
    提供异常事件的持久化存储和查询功能。
    使用SQLite数据库存储异常日志，支持按时间、设备、等级等条件查询。
    
    Attributes:
        db_path: 数据库文件路径
        max_records: 最大记录数（超过后自动清理旧记录）
    """
    
    # 数据库表结构
    CREATE_TABLE_SQL = """
    CREATE TABLE IF NOT EXISTS exception_events (
        event_id TEXT PRIMARY KEY,
        exception_type TEXT NOT NULL,
        exception_level TEXT NOT NULL,
        device_id TEXT NOT NULL,
        message TEXT NOT NULL,
        details TEXT,
        timestamp REAL NOT NULL,
        protection_actions TEXT,
        resolved INTEGER DEFAULT 0,
        resolved_at REAL,
        resolved_by TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_timestamp ON exception_events(timestamp);
    CREATE INDEX IF NOT EXISTS idx_device_id ON exception_events(device_id);
    CREATE INDEX IF NOT EXISTS idx_exception_level ON exception_events(exception_level);
    CREATE INDEX IF NOT EXISTS idx_resolved ON exception_events(resolved);
    """
    
    def __init__(self, db_path: str | Path = "data/exception_logs.db", max_records: int = 10000):
        """
        初始化异常日志记录器。
        
        Args:
            db_path: 数据库文件路径，默认为 data/exception_logs.db
            max_records: 最大记录数，默认为10000
        """
        self.db_path = Path(db_path)
        self.max_records = max_records
        
        # 确保目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 初始化数据库
        self._init_database()
        
        logger.info(
            f"ExceptionLogger initialized (db_path={self.db_path}, "
            f"max_records={self.max_records})"
        )
    
    def _init_database(self) -> None:
        """初始化数据库表结构。"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.executescript(self.CREATE_TABLE_SQL)
            conn.commit()
            conn.close()
            logger.debug("Database initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise
    
    def log_event(self, event: ExceptionEvent) -> bool:
        """
        记录异常事件。
        
        Args:
            event: 异常事件实例
        
        Returns:
            bool: 记录是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 插入事件记录
            cursor.execute(
                """
                INSERT OR REPLACE INTO exception_events 
                (event_id, exception_type, exception_level, device_id, message, 
                 details, timestamp, protection_actions, resolved, resolved_at, resolved_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.event_id,
                    event.exception_type.value,
                    event.exception_level.value,
                    event.device_id,
                    event.message,
                    json.dumps(event.details),
                    event.timestamp,
                    json.dumps([action.value for action in event.protection_actions]),
                    1 if event.resolved else 0,
                    event.resolved_at,
                    event.resolved_by,
                )
            )
            
            conn.commit()
            
            # 检查记录数，超过限制时清理旧记录
            cursor.execute("SELECT COUNT(*) FROM exception_events")
            count = cursor.fetchone()[0]
            if count > self.max_records:
                self._cleanup_old_records(conn, count - self.max_records)
            
            conn.close()
            
            logger.debug(
                f"Exception event logged: {event.event_id} "
                f"[{event.exception_level.value}] {event.device_id}: {event.message}"
            )
            return True
            
        except Exception as e:
            logger.error(f"Failed to log exception event: {e}")
            return False
    
    def _cleanup_old_records(self, conn: sqlite3.Connection, delete_count: int) -> None:
        """
        清理旧记录。
        
        Args:
            conn: 数据库连接
            delete_count: 需要删除的记录数
        """
        try:
            cursor = conn.cursor()
            cursor.execute(
                """
                DELETE FROM exception_events 
                WHERE event_id IN (
                    SELECT event_id FROM exception_events 
                    ORDER BY timestamp ASC 
                    LIMIT ?
                )
                """,
                (delete_count,)
            )
            conn.commit()
            logger.info(f"Cleaned up {delete_count} old exception records")
        except Exception as e:
            logger.error(f"Failed to cleanup old records: {e}")
    
    def query_events(
        self,
        device_id: str | None = None,
        exception_level: ExceptionLevel | None = None,
        exception_type: ExceptionType | None = None,
        resolved: bool | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExceptionEvent]:
        """
        查询异常事件。
        
        Args:
            device_id: 设备ID过滤，None表示不过滤
            exception_level: 异常等级过滤，None表示不过滤
            exception_type: 异常类型过滤，None表示不过滤
            resolved: 是否已解决过滤，None表示不过滤
            start_time: 开始时间过滤，None表示不过滤
            end_time: 结束时间过滤，None表示不过滤
            limit: 返回记录数限制，默认为100
            offset: 偏移量，默认为0
        
        Returns:
            List[ExceptionEvent]: 异常事件列表
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建查询条件
            conditions = []
            params = []
            
            if device_id is not None:
                conditions.append("device_id = ?")
                params.append(device_id)
            
            if exception_level is not None:
                conditions.append("exception_level = ?")
                params.append(exception_level.value)
            
            if exception_type is not None:
                conditions.append("exception_type = ?")
                params.append(exception_type.value)
            
            if resolved is not None:
                conditions.append("resolved = ?")
                params.append(1 if resolved else 0)
            
            if start_time is not None:
                conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time is not None:
                conditions.append("timestamp <= ?")
                params.append(end_time)
            
            where_clause = " AND ".join(conditions) if conditions else "1=1"
            
            # 执行查询
            query = f"""
                SELECT event_id, exception_type, exception_level, device_id, message,
                       details, timestamp, protection_actions, resolved, resolved_at, resolved_by
                FROM exception_events
                WHERE {where_clause}
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """
            params.extend([limit, offset])
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            conn.close()
            
            # 解析结果
            events = []
            for row in rows:
                event = ExceptionEvent(
                    event_id=row[0],
                    exception_type=ExceptionType(row[1]),
                    exception_level=ExceptionLevel(row[2]),
                    device_id=row[3],
                    message=row[4],
                    details=json.loads(row[5]) if row[5] else {},
                    timestamp=row[6],
                    protection_actions=[
                        ProtectionAction(action) 
                        for action in json.loads(row[7])
                    ] if row[7] else [],
                    resolved=bool(row[8]),
                    resolved_at=row[9],
                    resolved_by=row[10],
                )
                events.append(event)
            
            return events
            
        except Exception as e:
            logger.error(f"Failed to query exception events: {e}")
            return []
    
    def resolve_event(self, event_id: str, resolved_by: str) -> bool:
        """
        标记异常事件为已解决。
        
        Args:
            event_id: 事件ID
            resolved_by: 解决方式描述
        
        Returns:
            bool: 是否成功
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                """
                UPDATE exception_events
                SET resolved = 1, resolved_at = ?, resolved_by = ?
                WHERE event_id = ?
                """,
                (time.time(), resolved_by, event_id)
            )
            
            conn.commit()
            affected_rows = cursor.rowcount
            conn.close()
            
            if affected_rows > 0:
                logger.info(f"Exception event resolved: {event_id} by {resolved_by}")
                return True
            else:
                logger.warning(f"Exception event not found: {event_id}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to resolve exception event: {e}")
            return False
    
    def get_statistics(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> dict[str, Any]:
        """
        获取异常统计信息。
        
        Args:
            start_time: 开始时间，None表示从最早记录开始
            end_time: 结束时间，None表示到当前时间
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # 构建时间条件
            time_conditions = []
            params = []
            
            if start_time is not None:
                time_conditions.append("timestamp >= ?")
                params.append(start_time)
            
            if end_time is not None:
                time_conditions.append("timestamp <= ?")
                params.append(end_time)
            
            where_clause = " AND ".join(time_conditions) if time_conditions else "1=1"
            
            # 总数统计
            cursor.execute(
                f"SELECT COUNT(*) FROM exception_events WHERE {where_clause}",
                params
            )
            total_count = cursor.fetchone()[0]
            
            # 按等级统计
            cursor.execute(
                f"""
                SELECT exception_level, COUNT(*) 
                FROM exception_events 
                WHERE {where_clause}
                GROUP BY exception_level
                """,
                params
            )
            level_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 按类型统计
            cursor.execute(
                f"""
                SELECT exception_type, COUNT(*) 
                FROM exception_events 
                WHERE {where_clause}
                GROUP BY exception_type
                """,
                params
            )
            type_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 按设备统计
            cursor.execute(
                f"""
                SELECT device_id, COUNT(*) 
                FROM exception_events 
                WHERE {where_clause}
                GROUP BY device_id
                ORDER BY COUNT(*) DESC
                LIMIT 10
                """,
                params
            )
            device_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # 未解决数量
            cursor.execute(
                f"""
                SELECT COUNT(*) FROM exception_events 
                WHERE {where_clause} AND resolved = 0
                """,
                params
            )
            unresolved_count = cursor.fetchone()[0]
            
            conn.close()
            
            return {
                "total_count": total_count,
                "unresolved_count": unresolved_count,
                "resolved_count": total_count - unresolved_count,
                "by_level": level_stats,
                "by_type": type_stats,
                "by_device": device_stats,
                "query_time": time.time(),
            }
            
        except Exception as e:
            logger.error(f"Failed to get statistics: {e}")
            return {
                "total_count": 0,
                "unresolved_count": 0,
                "resolved_count": 0,
                "by_level": {},
                "by_type": {},
                "by_device": {},
                "query_time": time.time(),
                "error": str(e),
            }


# ==================== 异常保护管理器 ====================

class ExceptionProtectionManager:
    """
    异常保护管理器。
    
    提供设备异常的统一检测、分级、保护和恢复功能。
    支持多种设备类型的异常检测，自动执行分级保护动作。
    
    Features:
        - 异常等级自动判定
        - 分级保护动作执行
        - 通信中断自动保护
        - 断连自动重连机制
        - 异常事件日志记录
        - 实时告警通知
    
    Example:
        >>> manager = ExceptionProtectionManager()
        >>> manager.register_device("motor_01", "stepper", device_instance)
        >>> manager.register_device("em_01", "electromagnet", device_instance)
        >>> 
        >>> # 触发异常
        >>> await manager.trigger_exception(
        ...     device_id="motor_01",
        ...     exception_type=ExceptionType.MOTOR_ALARM,
        ...     message="电机过流报警",
        ...     details={"alarm_code": 0x01, "current": 12.5}
        ... )
        >>> 
        >>> # 查询异常
        >>> events = manager.query_events(device_id="motor_01", limit=10)
    """
    
    def __init__(
        self,
        db_path: str | Path = "data/exception_logs.db",
        enable_notification: bool = True,
        notification_callback: Callable[[ExceptionEvent], None] | None = None,
    ):
        """
        初始化异常保护管理器。
        
        Args:
            db_path: 数据库文件路径
            enable_notification: 是否启用告警通知
            notification_callback: 告警通知回调函数
        """
        # 设备注册表
        self._devices: dict[str, AbstractDevice] = {}
        self._device_configs: dict[str, DeviceExceptionConfig] = {}
        
        # 异常日志记录器
        self._logger = ExceptionLogger(db_path)
        
        # 通知配置
        self._enable_notification = enable_notification
        self._notification_callback = notification_callback
        
        # 全局急停回调
        self._global_estop_callback: Callable[[], None] | None = None
        
        # 恢复任务跟踪
        self._recovery_tasks: dict[str, asyncio.Task] = {}
        
        # 通信监控任务
        self._comm_monitor_task: asyncio.Task | None = None
        self._comm_monitor_interval = 1.0  # 监控间隔（秒）
        self._comm_timeout_threshold = 5.0  # 通信超时阈值（秒）
        
        # 运行状态
        self._running = False
        
        logger.info(
            f"ExceptionProtectionManager initialized "
            f"(db_path={db_path}, enable_notification={enable_notification})"
        )
    
    # ==================== 设备注册管理 ====================
    
    def register_device(
        self,
        device_id: str,
        device_type: str,
        device: AbstractDevice,
        config: DeviceExceptionConfig | None = None,
    ) -> bool:
        """
        注册设备到异常保护管理器。
        
        Args:
            device_id: 设备ID
            device_type: 设备类型（stepper, electromagnet, temperature_controller等）
            device: 设备实例
            config: 设备异常配置，None则使用默认配置
        
        Returns:
            bool: 注册是否成功
        
        Raises:
            ValueError: 设备ID已存在
        """
        if device_id in self._devices:
            raise ValueError(f"设备ID '{device_id}' 已存在")
        
        self._devices[device_id] = device
        
        # 使用提供的配置或创建默认配置
        if config is None:
            config = DeviceExceptionConfig(device_id=device_id, device_type=device_type)
        
        self._device_configs[device_id] = config
        
        logger.info(
            f"设备已注册到异常保护管理器: {device_id} (type={device_type}, "
            f"auto_recovery={config.auto_recovery})"
        )
        return True
    
    def unregister_device(self, device_id: str) -> bool:
        """
        注销设备。
        
        Args:
            device_id: 设备ID
        
        Returns:
            bool: 注销是否成功
        
        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"设备 '{device_id}' 不存在")
        
        # 取消恢复任务
        if device_id in self._recovery_tasks:
            self._recovery_tasks[device_id].cancel()
            del self._recovery_tasks[device_id]
        
        del self._devices[device_id]
        del self._device_configs[device_id]
        
        logger.info(f"设备已从异常保护管理器注销: {device_id}")
        return True
    
    def get_device(self, device_id: str) -> AbstractDevice | None:
        """
        获取设备实例。
        
        Args:
            device_id: 设备ID
        
        Returns:
            Optional[AbstractDevice]: 设备实例，不存在则返回None
        """
        return self._devices.get(device_id)
    
    def get_device_config(self, device_id: str) -> DeviceExceptionConfig | None:
        """
        获取设备异常配置。
        
        Args:
            device_id: 设备ID
        
        Returns:
            Optional[DeviceExceptionConfig]: 设备配置，不存在则返回None
        """
        return self._device_configs.get(device_id)
    
    def set_global_estop_callback(self, callback: Callable[[], None] | None) -> None:
        """
        设置全局急停回调函数。
        
        Args:
            callback: 回调函数，None表示取消
        """
        self._global_estop_callback = callback
        logger.info("全局急停回调函数已设置" if callback else "全局急停回调函数已取消")
    
    # ==================== 异常触发与处理 ====================
    
    async def trigger_exception(
        self,
        device_id: str,
        exception_type: ExceptionType,
        message: str,
        details: dict[str, Any] | None = None,
        exception_level: ExceptionLevel | None = None,
    ) -> ExceptionEvent:
        """
        触发异常并执行保护动作。
        
        这是异常保护的核心方法，执行以下步骤：
        1. 判定异常等级（如果未指定）
        2. 创建异常事件
        3. 记录日志
        4. 执行分级保护动作
        5. 发送告警通知
        
        Args:
            device_id: 设备ID
            exception_type: 异常类型
            message: 异常消息
            details: 异常详情字典
            exception_level: 异常等级，None则自动判定
        
        Returns:
            ExceptionEvent: 创建的异常事件
        
        Raises:
            KeyError: 设备不存在
        """
        if device_id not in self._devices:
            raise KeyError(f"设备 '{device_id}' 不存在")
        
        # 判定异常等级
        if exception_level is None:
            exception_level = ExceptionType.get_default_level(exception_type)
        
        # 创建异常事件
        event = ExceptionEvent(
            exception_type=exception_type,
            exception_level=exception_level,
            device_id=device_id,
            message=message,
            details=details or {},
        )
        
        # 记录日志
        self._logger.log_event(event)
        
        # 输出分级日志
        self._log_exception(event)
        
        # 执行保护动作
        await self._execute_protection_actions(event)
        
        # 发送告警通知
        if self._enable_notification:
            self._send_notification(event)
        
        return event
    
    def _log_exception(self, event: ExceptionEvent) -> None:
        """
        输出分级日志。
        
        根据异常等级选择不同的日志级别。
        
        Args:
            event: 异常事件
        """
        log_message = (
            f"[{event.exception_level.value.upper()}] "
            f"{event.device_id}: {event.message} "
            f"(type={event.exception_type.value}, event_id={event.event_id})"
        )
        
        if event.exception_level == ExceptionLevel.FATAL:
            logger.critical(log_message)
        elif event.exception_level == ExceptionLevel.ALARM:
            logger.error(log_message)
        else:
            logger.warning(log_message)
        
        # 输出详细信息
        if event.details:
            logger.debug(f"Exception details: {json.dumps(event.details, ensure_ascii=False)}")
    
    async def _execute_protection_actions(self, event: ExceptionEvent) -> None:
        """
        执行分级保护动作。
        
        根据异常等级执行对应的保护动作列表。
        
        Args:
            event: 异常事件
        """
        # 获取保护动作列表
        actions = ProtectionAction.get_actions_for_level(event.exception_level)
        event.protection_actions = actions
        
        device = self._devices.get(event.device_id)
        config = self._device_configs.get(event.device_id)
        
        for action in actions:
            try:
                if action == ProtectionAction.LOG_ONLY:
                    # 日志已在 _log_exception 中记录
                    pass
                
                elif action == ProtectionAction.NOTIFY:
                    # 通知已在 _send_notification 中处理
                    pass
                
                elif action == ProtectionAction.DERATE:
                    # 降额运行
                    await self._execute_derate(event, device, config)
                
                elif action == ProtectionAction.SINGLE_STOP:
                    # 单设备停机
                    await self._execute_single_stop(event, device, config)
                
                elif action == ProtectionAction.GLOBAL_ESTOP:
                    # 全局急停
                    await self._execute_global_estop(event)
                
            except Exception as e:
                logger.error(
                    f"保护动作执行失败: {action.value} for {event.device_id}: {e}"
                )
    
    async def _execute_derate(
        self,
        event: ExceptionEvent,
        device: AbstractDevice | None,
        config: DeviceExceptionConfig | None,
    ) -> None:
        """
        执行降额运行。
        
        根据异常类型降低设备运行参数。
        
        Args:
            event: 异常事件
            device: 设备实例
            config: 设备配置
        """
        if device is None:
            logger.warning(f"设备不存在，无法执行降额: {event.device_id}")
            return
        
        logger.info(f"执行降额运行: {event.device_id}")
        
        # 根据异常类型执行不同的降额策略
        if event.exception_type == ExceptionType.ELECTROMAGNET_OVERTEMPERATURE:
            # 电磁铁过温：降低电流
            if hasattr(device, "_current_value"):
                current_value = device._current_value
                derated_value = current_value * 0.5  # 降低到50%
                logger.info(
                    f"电磁铁降额: {event.device_id} "
                    f"电流 {current_value}A -> {derated_value}A"
                )
                # 实际降额操作由设备驱动实现
        
        elif event.exception_type == ExceptionType.TEMPERATURE_CONTROLLER_OVERTEMP:
            # 温控器超温：降低加热功率
            logger.info(f"温控器降额: {event.device_id}")
        
        else:
            logger.info(f"降额策略未定义: {event.exception_type.value}")
    
    async def _execute_single_stop(
        self,
        event: ExceptionEvent,
        device: AbstractDevice | None,
        config: DeviceExceptionConfig | None,
    ) -> None:
        """
        执行单设备停机。
        
        安全停止指定设备，不触发全局急停。
        
        Args:
            event: 异常事件
            device: 设备实例
            config: 设备配置
        """
        if device is None:
            logger.warning(f"设备不存在，无法执行停机: {event.device_id}")
            return
        
        logger.warning(f"执行单设备停机: {event.device_id}")
        
        try:
            # 调用设备的停止方法
            if hasattr(device, "stop"):
                await device.stop(emergency=False)
            elif hasattr(device, "emergency_stop"):
                await device.emergency_stop()
            
            # 更新设备状态
            device.status = DeviceStatus.ERROR
            device._last_error = event.message
            
            logger.info(f"设备已安全停机: {event.device_id}")
            
        except Exception as e:
            logger.error(f"设备停机失败: {event.device_id}: {e}")
    
    async def _execute_global_estop(self, event: ExceptionEvent) -> None:
        """
        执行全局急停。
        
        停止所有设备，触发全局急停回调。
        
        Args:
            event: 异常事件
        """
        logger.critical(
            f"执行全局急停！触发设备: {event.device_id}, "
            f"原因: {event.message}"
        )
        
        # 停止所有设备
        stop_tasks = []
        for device_id, device in self._devices.items():
            try:
                if hasattr(device, "stop"):
                    stop_tasks.append(device.stop(emergency=True))
                elif hasattr(device, "emergency_stop"):
                    stop_tasks.append(device.emergency_stop())
            except Exception as e:
                logger.error(f"全局急停时设备停止失败: {device_id}: {e}")
        
        # 并行执行所有停止操作
        if stop_tasks:
            await asyncio.gather(*stop_tasks, return_exceptions=True)
        
        # 触发全局急停回调
        if self._global_estop_callback:
            try:
                self._global_estop_callback()
            except Exception as e:
                logger.error(f"全局急停回调执行失败: {e}")
        
        logger.critical("全局急停执行完成")
    
    def _send_notification(self, event: ExceptionEvent) -> None:
        """
        发送告警通知。
        
        调用通知回调函数发送告警。
        
        Args:
            event: 异常事件
        """
        if self._notification_callback is None:
            logger.debug("通知回调未设置，跳过告警通知")
            return
        
        try:
            self._notification_callback(event)
            logger.debug(f"告警通知已发送: {event.event_id}")
        except Exception as e:
            logger.error(f"告警通知发送失败: {e}")
    
    # ==================== 通信中断保护 ====================
    
    async def start_communication_monitor(self) -> None:
        """启动通信监控任务。"""
        if self._comm_monitor_task is not None and not self._comm_monitor_task.done():
            logger.warning("通信监控任务已在运行")
            return
        
        self._running = True
        self._comm_monitor_task = asyncio.create_task(self._communication_monitor_loop())
        logger.info("通信监控任务已启动")
    
    async def stop_communication_monitor(self) -> None:
        """停止通信监控任务。"""
        self._running = False
        
        if self._comm_monitor_task is not None and not self._comm_monitor_task.done():
            self._comm_monitor_task.cancel()
            try:
                await self._comm_monitor_task
            except asyncio.CancelledError:
                pass
        
        logger.info("通信监控任务已停止")
    
    async def _communication_monitor_loop(self) -> None:
        """
        通信监控循环。
        
        定期检查设备通信状态，检测通信中断并触发保护。
        """
        logger.info("通信监控循环开始运行")
        
        # 记录上次成功通信时间
        last_comm_times: dict[str, float] = {}
        
        while self._running:
            try:
                current_time = time.time()
                
                for device_id, device in self._devices.items():
                    config = self._device_configs.get(device_id)
                    if config is None or not config.enabled:
                        continue
                    
                    # 检查设备连接状态
                    if device.status == DeviceStatus.DISCONNECTED:
                        # 设备已断开连接
                        if device_id in last_comm_times:
                            # 触发通信中断异常
                            await self.trigger_exception(
                                device_id=device_id,
                                exception_type=ExceptionType.COMMUNICATION_INTERRUPT,
                                message=f"设备通信中断，已断开连接",
                                details={
                                    "last_comm_time": last_comm_times.get(device_id),
                                    "downtime": current_time - last_comm_times.get(device_id, current_time),
                                }
                            )
                            del last_comm_times[device_id]
                        continue
                    
                    # 检查通信超时
                    if device_id in last_comm_times:
                        time_since_last_comm = current_time - last_comm_times[device_id]
                        if time_since_last_comm > self._comm_timeout_threshold:
                            # 触发通信超时异常
                            await self.trigger_exception(
                                device_id=device_id,
                                exception_type=ExceptionType.DEVICE_TIMEOUT,
                                message=f"设备通信超时 ({time_since_last_comm:.1f}s)",
                                details={
                                    "last_comm_time": last_comm_times[device_id],
                                    "timeout_threshold": self._comm_timeout_threshold,
                                }
                            )
                    
                    # 尝试读取设备状态以更新通信时间
                    try:
                        if hasattr(device, "read_status"):
                            await device.read_status()
                            last_comm_times[device_id] = current_time
                    except Exception as e:
                        logger.debug(f"设备状态读取失败: {device_id}: {e}")
                        # 不立即触发异常，等待超时检测
                
                await asyncio.sleep(self._comm_monitor_interval)
                
            except asyncio.CancelledError:
                logger.info("通信监控循环被取消")
                break
            except Exception as e:
                logger.error(f"通信监控循环异常: {e}")
                await asyncio.sleep(1.0)
        
        logger.info("通信监控循环已退出")
    
    # ==================== 自动重连机制 ====================
    
    async def attempt_reconnect(self, device_id: str) -> bool:
        """
        尝试重新连接设备。
        
        执行自动重连逻辑，包括延迟等待和重试机制。
        
        Args:
            device_id: 设备ID
        
        Returns:
            bool: 重连是否成功
        """
        device = self._devices.get(device_id)
        config = self._device_configs.get(device_id)
        
        if device is None or config is None:
            logger.warning(f"设备不存在或配置缺失，无法重连: {device_id}")
            return False
        
        if not config.auto_recovery:
            logger.info(f"设备自动恢复已禁用: {device_id}")
            return False
        
        logger.info(f"开始尝试重连设备: {device_id}")
        
        for attempt in range(1, config.max_recovery_attempts + 1):
            try:
                logger.info(
                    f"重连尝试 {attempt}/{config.max_recovery_attempts}: {device_id}"
                )
                
                # 延迟等待
                if attempt > 1:
                    await asyncio.sleep(config.recovery_delay)
                
                # 尝试连接
                success = await device.connect()
                
                if success:
                    logger.info(f"设备重连成功: {device_id}")
                    
                    # 标记通信中断异常为已解决
                    events = self._logger.query_events(
                        device_id=device_id,
                        exception_type=ExceptionType.COMMUNICATION_INTERRUPT,
                        resolved=False,
                        limit=1,
                    )
                    for event in events:
                        self._logger.resolve_event(
                            event.event_id,
                            f"自动重连成功 (尝试 {attempt} 次)"
                        )
                    
                    return True
                else:
                    logger.warning(f"重连尝试失败: {device_id} (attempt {attempt})")
                    
            except Exception as e:
                logger.error(f"重连尝试异常: {device_id} (attempt {attempt}): {e}")
        
        logger.error(
            f"设备重连失败，已达到最大尝试次数: {device_id} "
            f"({config.max_recovery_attempts} attempts)"
        )
        return False
    
    async def schedule_reconnect(self, device_id: str, delay: float = 0.0) -> None:
        """
        调度设备重连任务。
        
        异步执行重连，不阻塞当前操作。
        
        Args:
            device_id: 设备ID
            delay: 延迟时间（秒）
        """
        if device_id in self._recovery_tasks:
            logger.warning(f"设备重连任务已存在: {device_id}")
            return
        
        async def reconnect_task():
            if delay > 0:
                await asyncio.sleep(delay)
            await self.attempt_reconnect(device_id)
            if device_id in self._recovery_tasks:
                del self._recovery_tasks[device_id]
        
        self._recovery_tasks[device_id] = asyncio.create_task(reconnect_task())
        logger.info(f"设备重连任务已调度: {device_id} (delay={delay}s)")
    
    # ==================== 异常查询与统计 ====================
    
    def query_events(
        self,
        device_id: str | None = None,
        exception_level: ExceptionLevel | None = None,
        exception_type: ExceptionType | None = None,
        resolved: bool | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> list[ExceptionEvent]:
        """
        查询异常事件。
        
        Args:
            device_id: 设备ID过滤
            exception_level: 异常等级过滤
            exception_type: 异常类型过滤
            resolved: 是否已解决过滤
            start_time: 开始时间过滤
            end_time: 结束时间过滤
            limit: 返回记录数限制
            offset: 偏移量
        
        Returns:
            List[ExceptionEvent]: 异常事件列表
        """
        return self._logger.query_events(
            device_id=device_id,
            exception_level=exception_level,
            exception_type=exception_type,
            resolved=resolved,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
    
    def get_statistics(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> dict[str, Any]:
        """
        获取异常统计信息。
        
        Args:
            start_time: 开始时间
            end_time: 结束时间
        
        Returns:
            Dict[str, Any]: 统计信息字典
        """
        return self._logger.get_statistics(start_time, end_time)
    
    def resolve_event(self, event_id: str, resolved_by: str) -> bool:
        """
        标记异常事件为已解决。
        
        Args:
            event_id: 事件ID
            resolved_by: 解决方式描述
        
        Returns:
            bool: 是否成功
        """
        return self._logger.resolve_event(event_id, resolved_by)
    
    # ==================== 便捷方法 ====================
    
    async def check_motor_alarm(
        self,
        device_id: str,
        alarm_code: int,
        alarm_message: str,
    ) -> ExceptionEvent:
        """
        检查并触发步进电机报警。
        
        根据报警代码自动判定异常等级。
        
        Args:
            device_id: 设备ID
            alarm_code: 报警代码
            alarm_message: 报警消息
        
        Returns:
            ExceptionEvent: 创建的异常事件
        """
        # 根据报警代码判定等级
        # DM2C驱动器报警代码：0x01过流、0x02过压为严重报警
        critical_codes = {0x01, 0x02, 0x40, 0x80}
        
        if alarm_code in critical_codes:
            level = ExceptionLevel.ALARM
        else:
            level = ExceptionLevel.WARNING
        
        return await self.trigger_exception(
            device_id=device_id,
            exception_type=ExceptionType.MOTOR_ALARM,
            message=f"步进电机报警: {alarm_message}",
            details={
                "alarm_code": alarm_code,
                "alarm_code_hex": f"0x{alarm_code:04X}",
            },
            exception_level=level,
        )
    
    async def check_electromagnet_overcurrent(
        self,
        device_id: str,
        current: float,
        threshold: float,
    ) -> ExceptionEvent | None:
        """
        检查电磁铁过流。
        
        当电流超过阈值时触发过流异常。
        
        Args:
            device_id: 设备ID
            current: 当前电流值（A）
            threshold: 过流阈值（A）
        
        Returns:
            Optional[ExceptionEvent]: 如果触发异常则返回事件，否则返回None
        """
        if current <= threshold:
            return None
        
        # 判定异常等级
        overcurrent_ratio = current / threshold
        if overcurrent_ratio > 1.5:
            level = ExceptionLevel.FATAL
        elif overcurrent_ratio > 1.2:
            level = ExceptionLevel.ALARM
        else:
            level = ExceptionLevel.WARNING
        
        return await self.trigger_exception(
            device_id=device_id,
            exception_type=ExceptionType.ELECTROMAGNET_OVERCURRENT,
            message=f"电磁铁过流: {current:.2f}A > {threshold:.2f}A",
            details={
                "current": current,
                "threshold": threshold,
                "overcurrent_ratio": overcurrent_ratio,
            },
            exception_level=level,
        )
    
    async def check_electromagnet_overtemperature(
        self,
        device_id: str,
        temperature: float,
        threshold: float,
    ) -> ExceptionEvent | None:
        """
        检查电磁铁过温。
        
        当温度超过阈值时触发过温异常。
        
        Args:
            device_id: 设备ID
            temperature: 当前温度（°C）
            threshold: 过温阈值（°C）
        
        Returns:
            Optional[ExceptionEvent]: 如果触发异常则返回事件，否则返回None
        """
        if temperature <= threshold:
            return None
        
        # 判定异常等级
        overtemp_ratio = temperature / threshold
        if overtemp_ratio > 1.1:
            level = ExceptionLevel.ALARM
        else:
            level = ExceptionLevel.WARNING
        
        return await self.trigger_exception(
            device_id=device_id,
            exception_type=ExceptionType.ELECTROMAGNET_OVERTEMPERATURE,
            message=f"电磁铁过温: {temperature:.1f}°C > {threshold:.1f}°C",
            details={
                "temperature": temperature,
                "threshold": threshold,
                "overtemp_ratio": overtemp_ratio,
            },
            exception_level=level,
        )
    
    async def check_temperature_controller_overtemp(
        self,
        device_id: str,
        temperature: float,
        threshold: float,
    ) -> ExceptionEvent | None:
        """
        检查温控器超温。
        
        当温度超过阈值时触发超温异常。
        
        Args:
            device_id: 设备ID
            temperature: 当前温度（°C）
            threshold: 超温阈值（°C）
        
        Returns:
            Optional[ExceptionEvent]: 如果触发异常则返回事件，否则返回None
        """
        if temperature <= threshold:
            return None
        
        return await self.trigger_exception(
            device_id=device_id,
            exception_type=ExceptionType.TEMPERATURE_CONTROLLER_OVERTEMP,
            message=f"温控器超温: {temperature:.1f}°C > {threshold:.1f}°C",
            details={
                "temperature": temperature,
                "threshold": threshold,
            },
            exception_level=ExceptionLevel.ALARM,
        )
    
    async def report_communication_error(
        self,
        device_id: str,
        error_type: str,
        error_message: str,
    ) -> ExceptionEvent:
        """
        报告通信异常。
        
        用于设备驱动主动报告通信错误。
        
        Args:
            device_id: 设备ID
            error_type: 错误类型（serial_disconnect, timeout, protocol_error等）
            error_message: 错误消息
        
        Returns:
            ExceptionEvent: 创建的异常事件
        """
        # 根据错误类型选择异常类型
        type_map = {
            "serial_disconnect": ExceptionType.SERIAL_DISCONNECT,
            "timeout": ExceptionType.DEVICE_TIMEOUT,
            "protocol_error": ExceptionType.COMMUNICATION_INTERRUPT,
        }
        exception_type = type_map.get(error_type, ExceptionType.COMMUNICATION_INTERRUPT)
        
        return await self.trigger_exception(
            device_id=device_id,
            exception_type=exception_type,
            message=f"通信异常: {error_message}",
            details={
                "error_type": error_type,
            },
        )
    
    # ==================== 生命周期管理 ====================
    
    async def start(self) -> None:
        """启动异常保护管理器。"""
        await self.start_communication_monitor()
        logger.info("ExceptionProtectionManager 已启动")
    
    async def stop(self) -> None:
        """停止异常保护管理器。"""
        await self.stop_communication_monitor()
        
        # 取消所有恢复任务
        for task in self._recovery_tasks.values():
            task.cancel()
        self._recovery_tasks.clear()
        
        logger.info("ExceptionProtectionManager 已停止")
    
    async def __aenter__(self) -> "ExceptionProtectionManager":
        """异步上下文管理器入口。"""
        await self.start()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """异步上下文管理器退出。"""
        await self.stop()


# ==================== 工厂函数 ====================

def create_exception_protection_manager(
    db_path: str | Path = "data/exception_logs.db",
    enable_notification: bool = True,
    notification_callback: Callable[[ExceptionEvent], None] | None = None,
) -> ExceptionProtectionManager:
    """
    创建异常保护管理器实例。
    
    Args:
        db_path: 数据库文件路径
        enable_notification: 是否启用告警通知
        notification_callback: 告警通知回调函数
    
    Returns:
        ExceptionProtectionManager: 管理器实例
    
    Example:
        >>> def my_notification_handler(event: ExceptionEvent):
        ...     print(f"Alert: {event.message}")
        ...
        >>> manager = create_exception_protection_manager(
        ...     notification_callback=my_notification_handler
        ... )
    """
    return ExceptionProtectionManager(
        db_path=db_path,
        enable_notification=enable_notification,
        notification_callback=notification_callback,
    )
