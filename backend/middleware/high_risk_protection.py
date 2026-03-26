"""
文件名: high_risk_protection.py
路径: backend/middleware/
功能: 高危操作防护机制，包含二次确认、审计日志、会话锁定
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: fastapi, datetime, hashlib, secrets, typing

核心功能：
1. 高危操作二次确认机制
2. 操作审计日志记录
3. 会话超时自动锁定
4. 敏感信息脱敏处理

安全特性：
- 确认令牌有效期60秒
- 会话空闲超时300秒自动锁定
- 所有操作记录完整审计日志
- 敏感参数自动脱敏
"""

import hashlib
import json
import logging
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Callable

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from schemas.high_risk import (
    HIGH_RISK_OPERATION_CATEGORIES,
    HIGH_RISK_OPERATION_DESCRIPTIONS,
    HIGH_RISK_OPERATION_RISK_LEVELS,
    ConfirmationRequest,
    ConfirmationResponse,
    HighRiskOperationCategory,
    HighRiskOperationLogCreate,
    HighRiskOperationType,
    SessionLockStatus,
)

logger = logging.getLogger(__name__)


# ==================== 常量配置 ====================

# 确认令牌有效期（秒）
CONFIRMATION_TOKEN_EXPIRE_SECONDS = 60

# 会话空闲超时时间（秒）
SESSION_IDLE_TIMEOUT_SECONDS = 300

# 会话锁定检查间隔（秒）
SESSION_LOCK_CHECK_INTERVAL = 30

# 高危操作路径映射
HIGH_RISK_PATHS: dict[str, HighRiskOperationType] = {
    # 恢复出厂设置
    "/api/v1/motor/factory_reset": HighRiskOperationType.FACTORY_RESET,
    "/api/motor/factory_reset": HighRiskOperationType.FACTORY_RESET,
    # 修改安全限位
    "/api/v1/motor/limit/config": HighRiskOperationType.MODIFY_SAFETY_LIMIT,
    "/api/motor/limit/config": HighRiskOperationType.MODIFY_SAFETY_LIMIT,
    # 设备校准
    "/api/v1/electromagnet/calibrate": HighRiskOperationType.DEVICE_CALIBRATION,
    "/api/electromagnet/calibrate": HighRiskOperationType.DEVICE_CALIBRATION,
    "/api/v1/piezo/calibrate": HighRiskOperationType.DEVICE_CALIBRATION,
    "/api/piezo/calibrate": HighRiskOperationType.DEVICE_CALIBRATION,
    # 清除实验数据
    "/api/v1/experiments/clear": HighRiskOperationType.CLEAR_EXPERIMENT_DATA,
    "/api/experiments/clear": HighRiskOperationType.CLEAR_EXPERIMENT_DATA,
    # 清除报警历史
    "/api/v1/motor/clear_alarm_history": HighRiskOperationType.CLEAR_ALARM_HISTORY,
    "/api/motor/clear_alarm_history": HighRiskOperationType.CLEAR_ALARM_HISTORY,
    # 修改通信配置
    "/api/v1/motor/communication_config": HighRiskOperationType.MODIFY_COMMUNICATION_CONFIG,
    "/api/motor/communication_config": HighRiskOperationType.MODIFY_COMMUNICATION_CONFIG,
    # 急停复位
    "/api/v1/motor/reset": HighRiskOperationType.EMERGENCY_RESET,
    "/api/motor/reset": HighRiskOperationType.EMERGENCY_RESET,
    # 参数初始化
    "/api/v1/motor/param_init": HighRiskOperationType.PARAMETER_INIT,
    "/api/motor/param_init": HighRiskOperationType.PARAMETER_INIT,
}


# ==================== 确认令牌管理 ====================


@dataclass
class ConfirmationToken:
    """
    确认令牌数据类。

    Attributes:
        token: 令牌字符串
        operation_type: 操作类型
        device_id: 设备ID
        operation_params: 操作参数
        user_id: 用户ID
        ip_address: IP地址
        created_at: 创建时间
        expires_at: 过期时间
        used: 是否已使用
    """

    token: str
    operation_type: HighRiskOperationType
    device_id: str | None = None
    operation_params: dict[str, Any] | None = None
    user_id: int | None = None
    ip_address: str | None = None
    created_at: datetime = field(default_factory=datetime.now)
    expires_at: datetime = field(
        default_factory=lambda: datetime.now()
        + timedelta(seconds=CONFIRMATION_TOKEN_EXPIRE_SECONDS)
    )
    used: bool = False

    def is_expired(self) -> bool:
        """检查令牌是否过期。"""
        return datetime.now() > self.expires_at

    def is_valid(self) -> bool:
        """检查令牌是否有效（未过期且未使用）。"""
        return not self.is_expired() and not self.used


class ConfirmationTokenManager:
    """
    确认令牌管理器。

    管理高危操作的确认令牌，支持创建、验证、使用令牌。

    Example:
        >>> manager = ConfirmationTokenManager()
        >>> token = manager.create_token(HighRiskOperationType.FACTORY_RESET, user_id=1)
        >>> is_valid = manager.validate_token(token.token, HighRiskOperationType.FACTORY_RESET)
    """

    def __init__(self, cleanup_interval: int = 300):
        """
        初始化确认令牌管理器。

        Args:
            cleanup_interval: 清理间隔（秒），默认5分钟
        """
        self._tokens: dict[str, ConfirmationToken] = {}
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = datetime.now()

    def create_token(
        self,
        operation_type: HighRiskOperationType,
        device_id: str | None = None,
        operation_params: dict[str, Any] | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> ConfirmationToken:
        """
        创建确认令牌。

        Args:
            operation_type: 操作类型
            device_id: 设备ID
            operation_params: 操作参数
            user_id: 用户ID
            ip_address: IP地址

        Returns:
            ConfirmationToken: 确认令牌对象
        """
        # 生成安全的随机令牌
        token_str = secrets.token_urlsafe(32)

        token = ConfirmationToken(
            token=token_str,
            operation_type=operation_type,
            device_id=device_id,
            operation_params=operation_params,
            user_id=user_id,
            ip_address=ip_address,
        )

        self._tokens[token_str] = token

        logger.info(
            f"Confirmation token created: operation={operation_type.value}, "
            f"user={user_id}, device={device_id}"
        )

        # 自动清理过期令牌
        self._maybe_cleanup()

        return token

    def validate_token(
        self,
        token_str: str,
        operation_type: HighRiskOperationType,
        user_id: int | None = None,
    ) -> bool:
        """
        验证确认令牌。

        Args:
            token_str: 令牌字符串
            operation_type: 操作类型
            user_id: 用户ID

        Returns:
            bool: 令牌是否有效
        """
        token = self._tokens.get(token_str)

        if token is None:
            logger.warning(f"Token not found: {token_str[:8]}...")
            return False

        if not token.is_valid():
            logger.warning(f"Token expired or used: {token_str[:8]}...")
            return False

        if token.operation_type != operation_type:
            logger.warning(
                f"Token operation mismatch: expected={operation_type.value}, "
                f"actual={token.operation_type.value}"
            )
            return False

        if user_id is not None and token.user_id != user_id:
            logger.warning(
                f"Token user mismatch: expected={user_id}, actual={token.user_id}"
            )
            return False

        return True

    def use_token(self, token_str: str) -> ConfirmationToken | None:
        """
        使用确认令牌（标记为已使用）。

        Args:
            token_str: 令牌字符串

        Returns:
            ConfirmationToken | None: 令牌对象，无效时返回None
        """
        token = self._tokens.get(token_str)

        if token is None or not token.is_valid():
            return None

        token.used = True
        logger.info(f"Token used: {token_str[:8]}..., operation={token.operation_type.value}")

        return token

    def _maybe_cleanup(self) -> int:
        """
        如果需要，清理过期令牌。

        Returns:
            int: 清理的令牌数量
        """
        now = datetime.now()

        # 检查是否需要清理
        if (now - self._last_cleanup).total_seconds() < self._cleanup_interval:
            return 0

        self._last_cleanup = now

        # 清理过期令牌
        expired_tokens = [
            token_str
            for token_str, token in self._tokens.items()
            if token.is_expired() or token.used
        ]

        for token_str in expired_tokens:
            del self._tokens[token_str]

        if expired_tokens:
            logger.debug(f"Cleaned up {len(expired_tokens)} expired confirmation tokens")

        return len(expired_tokens)

    def get_stats(self) -> dict[str, Any]:
        """
        获取令牌管理器统计信息。

        Returns:
            dict: 统计信息
        """
        now = datetime.now()
        active_count = sum(1 for token in self._tokens.values() if token.is_valid())

        return {
            "total_tokens": len(self._tokens),
            "active_tokens": active_count,
            "last_cleanup": self._last_cleanup.isoformat(),
        }


# ==================== 会话锁定管理 ====================


@dataclass
class SessionLockState:
    """
    会话锁定状态数据类。

    Attributes:
        session_id: 会话ID
        user_id: 用户ID
        is_locked: 是否锁定
        locked_at: 锁定时间
        lock_reason: 锁定原因
        last_activity_at: 最后活动时间
        ip_address: IP地址
        user_agent: 用户代理
    """

    session_id: str
    user_id: int | None = None
    is_locked: bool = False
    locked_at: datetime | None = None
    lock_reason: str | None = None
    last_activity_at: datetime = field(default_factory=datetime.now)
    ip_address: str | None = None
    user_agent: str | None = None

    def check_and_lock(self, timeout_seconds: int) -> bool:
        """
        检查是否需要锁定并执行锁定。

        Args:
            timeout_seconds: 空闲超时时间（秒）

        Returns:
            bool: 是否执行了锁定
        """
        if self.is_locked:
            return False

        idle_seconds = (datetime.now() - self.last_activity_at).total_seconds()

        if idle_seconds > timeout_seconds:
            self.is_locked = True
            self.locked_at = datetime.now()
            self.lock_reason = "idle_timeout"
            logger.info(
                f"Session locked due to idle timeout: session={self.session_id[:8]}..., "
                f"idle_seconds={int(idle_seconds)}"
            )
            return True

        return False

    def update_activity(self) -> None:
        """更新最后活动时间。"""
        self.last_activity_at = datetime.now()

    def unlock(self) -> None:
        """解锁会话。"""
        self.is_locked = False
        self.locked_at = None
        self.lock_reason = None
        logger.info(f"Session unlocked: session={self.session_id[:8]}...")


class SessionLockManager:
    """
    会话锁定管理器。

    管理用户会话的锁定状态，支持空闲超时自动锁定。

    Example:
        >>> manager = SessionLockManager()
        >>> manager.update_activity("session123")
        >>> status = manager.get_lock_status("session123")
        >>> if status.is_locked:
        ...     manager.unlock("session123", password="user_password")
    """

    def __init__(
        self,
        idle_timeout_seconds: int = SESSION_IDLE_TIMEOUT_SECONDS,
        cleanup_interval: int = 600,
    ):
        """
        初始化会话锁定管理器。

        Args:
            idle_timeout_seconds: 空闲超时时间（秒），默认300秒
            cleanup_interval: 清理间隔（秒），默认10分钟
        """
        self._sessions: dict[str, SessionLockState] = {}
        self._idle_timeout_seconds = idle_timeout_seconds
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = datetime.now()

    def get_or_create_session(
        self,
        session_id: str,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SessionLockState:
        """
        获取或创建会话状态。

        Args:
            session_id: 会话ID
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            SessionLockState: 会话状态
        """
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionLockState(
                session_id=session_id,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            logger.debug(f"Session created: session={session_id[:8]}..., user={user_id}")

        return self._sessions[session_id]

    def update_activity(
        self,
        session_id: str,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> None:
        """
        更新会话活动时间。

        Args:
            session_id: 会话ID
            user_id: 用户ID
            ip_address: IP地址
        """
        session = self.get_or_create_session(session_id, user_id, ip_address)
        session.update_activity()

        # 自动清理不活跃会话
        self._maybe_cleanup()

    def check_and_lock(self, session_id: str) -> bool:
        """
        检查会话是否需要锁定并执行锁定。

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否执行了锁定
        """
        session = self._sessions.get(session_id)
        if session is None:
            return False

        return session.check_and_lock(self._idle_timeout_seconds)

    def get_lock_status(self, session_id: str) -> SessionLockStatus:
        """
        获取会话锁定状态。

        Args:
            session_id: 会话ID

        Returns:
            SessionLockStatus: 锁定状态
        """
        session = self._sessions.get(session_id)

        if session is None:
            return SessionLockStatus(
                is_locked=False,
                idle_timeout_seconds=self._idle_timeout_seconds,
            )

        # 检查是否需要锁定
        session.check_and_lock(self._idle_timeout_seconds)

        # 计算剩余锁定时间
        remaining_seconds = None
        if session.is_locked and session.locked_at:
            # 锁定后需要重新验证才能解锁，无剩余时间概念
            remaining_seconds = 0

        return SessionLockStatus(
            is_locked=session.is_locked,
            locked_at=session.locked_at,
            lock_reason=session.lock_reason,
            idle_timeout_seconds=self._idle_timeout_seconds,
            last_activity_at=session.last_activity_at,
            remaining_seconds=remaining_seconds,
        )

    def unlock(self, session_id: str) -> bool:
        """
        解锁会话。

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功解锁
        """
        session = self._sessions.get(session_id)

        if session is None:
            return False

        if not session.is_locked:
            return True

        session.unlock()
        return True

    def lock_session(self, session_id: str, reason: str = "manual") -> bool:
        """
        手动锁定会话。

        Args:
            session_id: 会话ID
            reason: 锁定原因

        Returns:
            bool: 是否成功锁定
        """
        session = self._sessions.get(session_id)

        if session is None:
            return False

        if session.is_locked:
            return True

        session.is_locked = True
        session.locked_at = datetime.now()
        session.lock_reason = reason

        logger.info(
            f"Session manually locked: session={session_id[:8]}..., reason={reason}"
        )

        return True

    def _maybe_cleanup(self) -> int:
        """
        如果需要，清理不活跃会话。

        Returns:
            int: 清理的会话数量
        """
        now = datetime.now()

        # 检查是否需要清理
        if (now - self._last_cleanup).total_seconds() < self._cleanup_interval:
            return 0

        self._last_cleanup = now

        # 清理超过2倍超时时间未活动的会话
        max_inactive_seconds = self._idle_timeout_seconds * 2
        inactive_sessions = [
            session_id
            for session_id, session in self._sessions.items()
            if (now - session.last_activity_at).total_seconds() > max_inactive_seconds
        ]

        for session_id in inactive_sessions:
            del self._sessions[session_id]

        if inactive_sessions:
            logger.debug(f"Cleaned up {len(inactive_sessions)} inactive sessions")

        return len(inactive_sessions)

    def get_stats(self) -> dict[str, Any]:
        """
        获取会话管理器统计信息。

        Returns:
            dict: 统计信息
        """
        now = datetime.now()
        locked_count = sum(1 for s in self._sessions.values() if s.is_locked)
        active_count = sum(
            1
            for s in self._sessions.values()
            if not s.is_locked
            and (now - s.last_activity_at).total_seconds() < self._idle_timeout_seconds
        )

        return {
            "total_sessions": len(self._sessions),
            "active_sessions": active_count,
            "locked_sessions": locked_count,
            "idle_timeout_seconds": self._idle_timeout_seconds,
            "last_cleanup": self._last_cleanup.isoformat(),
        }


# ==================== 高危操作审计日志 ====================


class HighRiskOperationAuditLogger:
    """
    高危操作审计日志记录器。

    记录所有高危操作的详细审计日志，包括操作类型、参数、结果等。

    Example:
        >>> logger = HighRiskOperationAuditLogger(storage)
        >>> logger.log_operation(
        ...     operation_type=HighRiskOperationType.FACTORY_RESET,
        ...     user_id=1,
        ...     execution_result="success"
        ... )
    """

    def __init__(self, storage=None):
        """
        初始化审计日志记录器。

        Args:
            storage: 数据存储实例
        """
        self._storage = storage
        self._log_buffer: list[dict[str, Any]] = []
        self._buffer_size = 20

    def set_storage(self, storage) -> None:
        """
        设置数据存储实例。

        Args:
            storage: 数据存储实例
        """
        self._storage = storage

    def log_operation(
        self,
        operation_type: HighRiskOperationType,
        operation_category: HighRiskOperationCategory | None = None,
        device_id: str | None = None,
        operation_params: dict[str, Any] | None = None,
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        confirmation_token: str | None = None,
        execution_result: str = "pending",
        error_message: str | None = None,
        duration_ms: int | None = None,
    ) -> None:
        """
        记录高危操作日志。

        Args:
            operation_type: 操作类型
            operation_category: 操作类别
            device_id: 设备ID
            operation_params: 操作参数（会自动脱敏）
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理
            confirmation_token: 确认令牌
            execution_result: 执行结果
            error_message: 错误消息
            duration_ms: 执行耗时（毫秒）
        """
        # 获取操作类别
        if operation_category is None:
            operation_category = HIGH_RISK_OPERATION_CATEGORIES.get(
                operation_type, HighRiskOperationCategory.SYSTEM
            )

        # 脱敏操作参数
        sanitized_params = self._sanitize_params(operation_params)

        # 构建日志记录
        log_entry = {
            "timestamp": datetime.now(),
            "operation_type": operation_type.value,
            "operation_category": operation_category.value,
            "device_id": device_id,
            "operation_params": json.dumps(sanitized_params, ensure_ascii=False)
            if sanitized_params
            else None,
            "user_id": user_id,
            "ip_address": ip_address,
            "user_agent": user_agent[:255] if user_agent else None,
            "confirmation_token": confirmation_token[:16] + "..."
            if confirmation_token
            else None,
            "execution_result": execution_result,
            "error_message": error_message,
            "duration_ms": duration_ms,
        }

        self._log_buffer.append(log_entry)

        # 记录到应用日志
        log_level = logging.INFO if execution_result == "success" else logging.WARNING
        logger.log(
            log_level,
            f"High-risk operation: type={operation_type.value}, "
            f"user={user_id}, device={device_id}, result={execution_result}",
        )

        # 缓冲区满时写入数据库
        if len(self._log_buffer) >= self._buffer_size:
            self._flush_buffer()

    def _sanitize_params(self, params: dict[str, Any] | None) -> dict[str, Any] | None:
        """
        脱敏操作参数。

        Args:
            params: 原始参数

        Returns:
            dict | None: 脱敏后的参数
        """
        if params is None:
            return None

        from middleware.security import sanitize_dict

        return sanitize_dict(params)

    def _flush_buffer(self) -> None:
        """
        将缓冲区日志写入数据库。
        """
        if not self._storage or not self._log_buffer:
            return

        try:
            from models import AuditLog

            session = self._storage.Session()
            try:
                for entry in self._log_buffer:
                    log_record = AuditLog(
                        timestamp=entry["timestamp"],
                        user_id=entry["user_id"],
                        device_id=entry["device_id"],
                        operation_type=entry["operation_type"],
                        operation_category=entry["operation_category"],
                        request_method="POST",
                        request_path=f"/high_risk/{entry['operation_type']}",
                        request_params=entry["operation_params"],
                        response_status=200 if entry["execution_result"] == "success" else 500,
                        response_message=entry["error_message"],
                        ip_address=entry["ip_address"],
                        user_agent=entry["user_agent"],
                        duration_ms=entry["duration_ms"],
                        extra_data=json.dumps(
                            {
                                "confirmation_token": entry["confirmation_token"],
                                "execution_result": entry["execution_result"],
                            },
                            ensure_ascii=False,
                        ),
                    )
                    session.add(log_record)
                session.commit()
                logger.debug(
                    f"Flushed {len(self._log_buffer)} high-risk operation logs to database"
                )
            except Exception as e:
                session.rollback()
                logger.error(f"Failed to commit high-risk operation logs: {e}")
                raise
            finally:
                session.close()
            self._log_buffer = []
        except ImportError:
            logger.warning("AuditLog model not found, skipping database write")
        except Exception as e:
            logger.error(f"Failed to flush high-risk operation logs: {e}")

    def flush(self) -> None:
        """
        手动刷新缓冲区。
        """
        self._flush_buffer()


# ==================== 高危操作防护服务 ====================


class HighRiskProtectionService:
    """
    高危操作防护服务。

    整合二次确认、审计日志、会话锁定功能。

    Example:
        >>> service = HighRiskProtectionService()
        >>> response = service.request_confirmation(
        ...     operation_type=HighRiskOperationType.FACTORY_RESET,
        ...     user_id=1
        ... )
        >>> if response.requires_confirmation:
        ...     # 用户确认后，使用令牌执行操作
        ...     service.execute_with_confirmation(token, callback)
    """

    def __init__(
        self,
        storage=None,
        idle_timeout_seconds: int = SESSION_IDLE_TIMEOUT_SECONDS,
    ):
        """
        初始化高危操作防护服务。

        Args:
            storage: 数据存储实例
            idle_timeout_seconds: 空闲超时时间（秒）
        """
        self._token_manager = ConfirmationTokenManager()
        self._session_manager = SessionLockManager(idle_timeout_seconds)
        self._audit_logger = HighRiskOperationAuditLogger(storage)

    def set_storage(self, storage) -> None:
        """
        设置数据存储实例。

        Args:
            storage: 数据存储实例
        """
        self._audit_logger.set_storage(storage)

    def request_confirmation(
        self,
        request: ConfirmationRequest,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> ConfirmationResponse:
        """
        请求高危操作二次确认。

        Args:
            request: 确认请求
            user_id: 用户ID
            ip_address: IP地址

        Returns:
            ConfirmationResponse: 确认响应
        """
        operation_type = request.operation_type

        # 获取操作描述和风险等级
        description = HIGH_RISK_OPERATION_DESCRIPTIONS.get(
            operation_type, "未知高危操作"
        )
        risk_level = HIGH_RISK_OPERATION_RISK_LEVELS.get(operation_type, "medium")

        # 如果已提供确认令牌，验证令牌
        if request.confirmation_token:
            is_valid = self._token_manager.validate_token(
                request.confirmation_token, operation_type, user_id
            )

            if is_valid:
                return ConfirmationResponse(
                    requires_confirmation=False,
                    confirmation_token=request.confirmation_token,
                    operation_type=operation_type,
                    operation_description=description,
                    risk_level=risk_level,
                    warning_message="令牌验证通过，可以执行操作",
                )
            else:
                return ConfirmationResponse(
                    requires_confirmation=True,
                    operation_type=operation_type,
                    operation_description=description,
                    risk_level=risk_level,
                    warning_message="确认令牌无效或已过期，请重新确认",
                )

        # 创建新的确认令牌
        token = self._token_manager.create_token(
            operation_type=operation_type,
            device_id=request.device_id,
            operation_params=request.operation_params,
            user_id=user_id,
            ip_address=ip_address,
        )

        # 构建警告消息
        warning_message = (
            f"⚠️ 高危操作警告\n\n"
            f"操作类型：{operation_type.value}\n"
            f"风险等级：{risk_level}\n\n"
            f"描述：{description}\n\n"
            f"请确认是否继续执行此操作。"
        )

        return ConfirmationResponse(
            requires_confirmation=True,
            confirmation_token=token.token,
            operation_type=operation_type,
            operation_description=description,
            risk_level=risk_level,
            warning_message=warning_message,
            token_expires_at=token.expires_at,
        )

    def execute_with_confirmation(
        self,
        confirmation_token: str,
        operation_type: HighRiskOperationType,
        callback: Callable[[], bool],
        user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> dict[str, Any]:
        """
        使用确认令牌执行高危操作。

        Args:
            confirmation_token: 确认令牌
            operation_type: 操作类型
            callback: 实际执行操作的回调函数
            user_id: 用户ID
            ip_address: IP地址
            user_agent: 用户代理

        Returns:
            dict: 执行结果
        """
        start_time = time.time()

        # 验证并使用令牌
        token = self._token_manager.use_token(confirmation_token)

        if token is None:
            self._audit_logger.log_operation(
                operation_type=operation_type,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                confirmation_token=confirmation_token,
                execution_result="failed",
                error_message="确认令牌无效或已过期",
            )
            return {
                "success": False,
                "error": "确认令牌无效或已过期",
                "error_code": "INVALID_CONFIRMATION_TOKEN",
            }

        # 执行操作
        try:
            result = callback()
            duration_ms = int((time.time() - start_time) * 1000)

            # 记录审计日志
            self._audit_logger.log_operation(
                operation_type=operation_type,
                device_id=token.device_id,
                operation_params=token.operation_params,
                user_id=user_id or token.user_id,
                ip_address=ip_address or token.ip_address,
                user_agent=user_agent,
                confirmation_token=confirmation_token,
                execution_result="success" if result else "failed",
                duration_ms=duration_ms,
            )

            return {
                "success": result,
                "message": "操作执行成功" if result else "操作执行失败",
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            error_message = str(e)

            # 记录失败日志
            self._audit_logger.log_operation(
                operation_type=operation_type,
                device_id=token.device_id,
                operation_params=token.operation_params,
                user_id=user_id or token.user_id,
                ip_address=ip_address or token.ip_address,
                user_agent=user_agent,
                confirmation_token=confirmation_token,
                execution_result="failed",
                error_message=error_message,
                duration_ms=duration_ms,
            )

            logger.error(
                f"High-risk operation failed: type={operation_type.value}, "
                f"error={error_message}",
                exc_info=True,
            )

            return {
                "success": False,
                "error": error_message,
                "error_code": "OPERATION_FAILED",
            }

    def update_session_activity(
        self,
        session_id: str,
        user_id: int | None = None,
        ip_address: str | None = None,
    ) -> SessionLockStatus:
        """
        更新会话活动并返回锁定状态。

        Args:
            session_id: 会话ID
            user_id: 用户ID
            ip_address: IP地址

        Returns:
            SessionLockStatus: 会话锁定状态
        """
        self._session_manager.update_activity(session_id, user_id, ip_address)
        return self._session_manager.get_lock_status(session_id)

    def check_session_lock(self, session_id: str) -> bool:
        """
        检查会话是否被锁定。

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否被锁定
        """
        status = self._session_manager.get_lock_status(session_id)
        return status.is_locked

    def unlock_session(self, session_id: str) -> bool:
        """
        解锁会话。

        Args:
            session_id: 会话ID

        Returns:
            bool: 是否成功解锁
        """
        return self._session_manager.unlock(session_id)

    def get_session_status(self, session_id: str) -> SessionLockStatus:
        """
        获取会话锁定状态。

        Args:
            session_id: 会话ID

        Returns:
            SessionLockStatus: 会话锁定状态
        """
        return self._session_manager.get_lock_status(session_id)

    def get_stats(self) -> dict[str, Any]:
        """
        获取服务统计信息。

        Returns:
            dict: 统计信息
        """
        return {
            "token_manager": self._token_manager.get_stats(),
            "session_manager": self._session_manager.get_stats(),
        }


# ==================== 全局实例 ====================

_global_service: HighRiskProtectionService | None = None


def get_high_risk_protection_service() -> HighRiskProtectionService:
    """
    获取全局高危操作防护服务实例。

    Returns:
        HighRiskProtectionService: 服务实例
    """
    global _global_service
    if _global_service is None:
        _global_service = HighRiskProtectionService()
    return _global_service


def init_high_risk_protection_service(
    storage=None,
    idle_timeout_seconds: int = SESSION_IDLE_TIMEOUT_SECONDS,
) -> HighRiskProtectionService:
    """
    初始化全局高危操作防护服务实例。

    Args:
        storage: 数据存储实例
        idle_timeout_seconds: 空闲超时时间（秒）

    Returns:
        HighRiskProtectionService: 服务实例
    """
    global _global_service
    _global_service = HighRiskProtectionService(storage, idle_timeout_seconds)
    return _global_service


# ==================== 中间件 ====================


class HighRiskProtectionMiddleware(BaseHTTPMiddleware):
    """
    高危操作防护中间件。

    拦截高危操作请求，检查会话锁定状态。

    Example:
        >>> app.add_middleware(HighRiskProtectionMiddleware)
    """

    def __init__(
        self,
        app: ASGIApp,
        service: HighRiskProtectionService | None = None,
    ):
        """
        初始化中间件。

        Args:
            app: ASGI应用实例
            service: 高危操作防护服务实例
        """
        super().__init__(app)
        self._service = service or get_high_risk_protection_service()

    async def dispatch(self, request: Request, call_next: Callable):
        """
        处理请求。

        Args:
            request: FastAPI请求对象
            call_next: 下一个处理器

        Returns:
            Response: 响应对象
        """
        path = request.url.path

        # 获取会话ID（从请求头或Cookie）
        session_id = self._get_session_id(request)

        # 更新会话活动
        if session_id:
            self._service.update_session_activity(session_id)

        # 检查是否为高危操作路径
        if path in HIGH_RISK_PATHS:
            # 检查会话锁定状态
            if session_id and self._service.check_session_lock(session_id):
                return self._create_locked_response()

        # 调用下一个处理器
        response = await call_next(request)

        return response

    def _get_session_id(self, request: Request) -> str | None:
        """
        从请求中获取会话ID。

        Args:
            request: FastAPI请求对象

        Returns:
            str | None: 会话ID
        """
        # 从Authorization头获取
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            # 使用token的哈希作为会话ID
            return hashlib.sha256(token.encode()).hexdigest()[:32]

        # 从Cookie获取
        session_cookie = request.cookies.get("session_id")
        if session_cookie:
            return session_cookie

        return None

    def _create_locked_response(self):
        """
        创建会话锁定响应。

        Returns:
            Response: JSON响应
        """
        from fastapi.responses import JSONResponse

        return JSONResponse(
            status_code=status.HTTP_423_LOCKED,
            content={
                "success": False,
                "error_code": "SESSION_LOCKED",
                "message": "会话已锁定，请重新验证身份",
                "detail": "由于长时间未操作，会话已自动锁定。请重新输入密码解锁。",
            },
        )
