"""
软件限位防护服务

文件名: limit_protection_service.py
路径: backend/services/
功能: 实现完整的软件限位防护体系，包括位置预校验、二次校验、锁止逻辑、超限保护
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: backend.core.dm2c_driver, backend.schemas.motor, backend.schemas.common

安全约束:
- 所有运动指令必须先执行软件限位预校验
- 限位触发后必须锁止运动，禁止继续向限位方向运动
- 限位参数写入后必须自动读取校验，确保参数生效
- 超限检测必须触发安全停机保护
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from backend.schemas.common import ErrorCode
from backend.schemas.motor import (
    LimitConfigWithVerificationRequest,
    LimitConfigWithVerificationResponse,
    LimitLockoutStatus,
    LimitVerificationResult,
)

logger = logging.getLogger(__name__)


class LimitDirection(str, Enum):
    """
    限位方向枚举。

    Attributes:
        POSITIVE: 正向限位（正方向运动受限）
        NEGATIVE: 负向限位（负方向运动受限）
        NONE: 无限位
    """

    POSITIVE = "positive"
    NEGATIVE = "negative"
    NONE = "none"


class OverlimitType(str, Enum):
    """
    超限类型枚举。

    Attributes:
        POSITION: 位置超限
        CURRENT: 电流超限
        TEMPERATURE: 温度超限
        VOLTAGE: 电压超限
    """

    POSITION = "position"
    CURRENT = "current"
    TEMPERATURE = "temperature"
    VOLTAGE = "voltage"


@dataclass
class LockoutState:
    """
    锁止状态数据类。

    用于记录限位触发后的锁止状态。

    Attributes:
        is_locked: 是否处于锁止状态
        direction: 锁止方向
        triggered_position_mm: 触发锁止时的位置(mm)
        triggered_at: 触发时间戳
        auto_unlock_enabled: 是否启用自动解锁
    """

    is_locked: bool = False
    direction: LimitDirection = LimitDirection.NONE
    triggered_position_mm: float | None = None
    triggered_at: str | None = None
    auto_unlock_enabled: bool = True


@dataclass
class DeviceLimitConfig:
    """
    设备限位配置数据类。

    用于存储各设备的限位参数。

    Attributes:
        device_id: 设备唯一标识
        positive_limit: 正向限位
        negative_limit: 负向限位
        enable: 是否启用限位检查
        tolerance: 校验允许误差
    """

    device_id: str
    positive_limit: float = 100.0
    negative_limit: float = -100.0
    enable: bool = True
    tolerance: float = 0.1


@dataclass
class OverlimitRecord:
    """
    超限记录数据类。

    用于记录超限事件。

    Attributes:
        device_id: 设备唯一标识
        overlimit_type: 超限类型
        actual_value: 实际值
        limit_value: 限值
        direction: 超限方向
        timestamp: 时间戳
        action_taken: 采取的保护动作
    """

    device_id: str
    overlimit_type: OverlimitType
    actual_value: float
    limit_value: float
    direction: LimitDirection
    timestamp: str
    action_taken: str


class LimitProtectionService:
    """
    软件限位防护服务类。

    提供完整的软件限位防护功能：
    - 位置预校验：运动指令下发前预判是否超出限位
    - 二次校验：限位参数写入后自动读取校验
    - 锁止逻辑：限位触发后锁止运动，禁止继续向限位方向运动
    - 超限保护：全设备超限自动保护（电磁铁电流、温控器温度、压电控制器电压）

    安全约束:
        - 所有运动指令必须先执行软件限位预校验
        - 异常时必须触发安全停机逻辑
        - 高危操作必须包含二次校验、日志审计逻辑
    """

    def __init__(self) -> None:
        """
        初始化限位防护服务。
        """
        # 设备锁止状态映射 {device_id: LockoutState}
        self._lockout_states: dict[str, LockoutState] = {}

        # 设备限位配置映射 {device_id: DeviceLimitConfig}
        self._limit_configs: dict[str, DeviceLimitConfig] = {}

        # 超限记录历史（最近100条）
        self._overlimit_history: list[OverlimitRecord] = []
        self._max_history_size = 100

        logger.info("LimitProtectionService initialized")

    # ==================== 位置预校验功能 ====================

    def pre_validate_position(
        self,
        device_id: str,
        target_position_mm: float,
        current_position_mm: float | None = None,
    ) -> tuple[bool, str | None, LimitDirection]:
        """
        运动指令下发前的位置预校验。

        Args:
            device_id: 设备唯一标识
            target_position_mm: 目标位置(mm)
            current_position_mm: 当前位置(mm)，用于锁止检查

        Returns:
            Tuple[bool, Optional[str], LimitDirection]:
                - 是否通过校验
                - 错误消息（校验失败时）
                - 限位方向（校验失败时）

        安全约束:
            1. 运动指令下发前必须执行目标位置预校验，超出限位直接拦截
            2. 锁止状态下禁止向锁止方向运动
            3. 所有校验失败必须记录日志
        """
        # 获取设备限位配置
        config = self._limit_configs.get(device_id)
        if config is None or not config.enable:
            logger.debug(f"Device {device_id} limit check disabled or not configured")
            return True, None, LimitDirection.NONE

        # 检查锁止状态
        lockout_state = self._lockout_states.get(device_id, LockoutState())
        if lockout_state.is_locked:
            # 判断运动方向
            if current_position_mm is not None:
                direction = self._determine_direction(current_position_mm, target_position_mm)

                # 检查是否向锁止方向运动
                if direction == lockout_state.direction:
                    error_msg = (
                        f"设备 {device_id} 处于限位锁止状态，"
                        f"禁止向{lockout_state.direction.value}方向运动。"
                        f"当前位置: {current_position_mm:.3f}mm，目标位置: {target_position_mm:.3f}mm"
                    )
                    logger.warning(f"LOCKOUT BLOCKED: {error_msg}")
                    return False, error_msg, lockout_state.direction

                # 自动解锁检查：离开限位区域后自动解锁
                if lockout_state.auto_unlock_enabled:
                    if self._is_within_limits(target_position_mm, config):
                        self._unlock_device(device_id)
                        logger.info(
                            f"Device {device_id} auto-unlocked: "
                            f"target {target_position_mm:.3f}mm within limits"
                        )

        # 检查目标位置是否在限位范围内
        if not self._is_within_limits(target_position_mm, config):
            direction = self._determine_limit_direction(target_position_mm, config)
            error_msg = (
                f"目标位置 {target_position_mm:.3f}mm 超出软件限位范围 "
                f"[{config.negative_limit}mm, {config.positive_limit}mm]"
            )
            logger.warning(f"LIMIT EXCEEDED: {error_msg}")

            # 触发锁止
            self._trigger_lockout(device_id, direction, target_position_mm)

            return False, error_msg, direction

        return True, None, LimitDirection.NONE

    def pre_validate_jog(
        self,
        device_id: str,
        direction: int,
        current_position_mm: float,
    ) -> tuple[bool, str | None]:
        """
        JOG运动前的预校验。

        Args:
            device_id: 设备唯一标识
            direction: JOG方向，1为正向，-1为负向
            current_position_mm: 当前位置(mm)

        Returns:
            Tuple[bool, Optional[str]]: (是否通过校验, 错误消息)

        安全约束:
            JOG运动必须检查锁止状态，禁止向锁止方向运动
        """
        # 获取设备限位配置
        config = self._limit_configs.get(device_id)
        if config is None or not config.enable:
            return True, None

        # 检查锁止状态
        lockout_state = self._lockout_states.get(device_id, LockoutState())
        if lockout_state.is_locked:
            jog_direction = LimitDirection.POSITIVE if direction > 0 else LimitDirection.NEGATIVE

            if jog_direction == lockout_state.direction:
                error_msg = (
                    f"设备 {device_id} 处于限位锁止状态，"
                    f"禁止{lockout_state.direction.value}方向JOG运动"
                )
                logger.warning(f"JOG LOCKOUT BLOCKED: {error_msg}")
                return False, error_msg

        # 检查当前位置是否接近限位
        margin_mm = 1.0  # 安全裕度
        if direction > 0 and current_position_mm >= config.positive_limit - margin_mm:
            error_msg = (
                f"当前位置 {current_position_mm:.3f}mm 接近正向限位 {config.positive_limit}mm，"
                f"禁止正向JOG运动"
            )
            logger.warning(f"JOG LIMIT WARNING: {error_msg}")
            return False, error_msg

        if direction < 0 and current_position_mm <= config.negative_limit + margin_mm:
            error_msg = (
                f"当前位置 {current_position_mm:.3f}mm 接近负向限位 {config.negative_limit}mm，"
                f"禁止负向JOG运动"
            )
            logger.warning(f"JOG LIMIT WARNING: {error_msg}")
            return False, error_msg

        return True, None

    # ==================== 二次校验功能 ====================

    async def verify_limit_parameters(
        self,
        device_id: str,
        expected_positive_mm: float,
        expected_negative_mm: float,
        actual_positive_mm: float,
        actual_negative_mm: float,
        tolerance_mm: float = 0.1,
    ) -> LimitVerificationResult:
        """
        限位参数写入后的二次校验。

        Args:
            device_id: 设备唯一标识
            expected_positive_mm: 预期正向限位(mm)
            expected_negative_mm: 预期负向限位(mm)
            actual_positive_mm: 实际读取的正向限位(mm)
            actual_negative_mm: 实际读取的负向限位(mm)
            tolerance_mm: 允许的误差范围(mm)

        Returns:
            LimitVerificationResult: 校验结果

        安全约束:
            校验失败时，参数可能未正确写入驱动器，需要告警并建议重新写入
        """
        # 检查正向限位匹配
        positive_diff = abs(expected_positive_mm - actual_positive_mm)
        positive_match = positive_diff <= tolerance_mm

        # 检查负向限位匹配
        negative_diff = abs(expected_negative_mm - actual_negative_mm)
        negative_match = negative_diff <= tolerance_mm

        # 构建校验结果消息
        if positive_match and negative_match:
            message = "限位参数校验成功，参数已正确写入"
            success = True
        else:
            issues = []
            if not positive_match:
                issues.append(
                    f"正向限位不匹配: 预期{expected_positive_mm}mm, "
                    f"实际{actual_positive_mm}mm, 差异{positive_diff:.3f}mm"
                )
            if not negative_match:
                issues.append(
                    f"负向限位不匹配: 预期{expected_negative_mm}mm, "
                    f"实际{actual_negative_mm}mm, 差异{negative_diff:.3f}mm"
                )
            message = f"限位参数校验失败: {'; '.join(issues)}"
            success = False

            # 记录告警日志
            logger.error(
                f"LIMIT VERIFICATION FAILED for {device_id}: {message}",
                extra={
                    "device_id": device_id,
                    "expected_positive": expected_positive_mm,
                    "expected_negative": expected_negative_mm,
                    "actual_positive": actual_positive_mm,
                    "actual_negative": actual_negative_mm,
                },
            )

        return LimitVerificationResult(
            success=success,
            expected_positive_mm=expected_positive_mm,
            expected_negative_mm=expected_negative_mm,
            actual_positive_mm=actual_positive_mm,
            actual_negative_mm=actual_negative_mm,
            positive_match=positive_match,
            negative_match=negative_match,
            tolerance_mm=tolerance_mm,
            message=message,
        )

    # ==================== 锁止逻辑功能 ====================

    def _trigger_lockout(
        self,
        device_id: str,
        direction: LimitDirection,
        position_mm: float,
    ) -> None:
        """
        触发限位锁止。

        Args:
            device_id: 设备唯一标识
            direction: 锁止方向
            position_mm: 触发锁止时的位置

        安全约束:
            限位触发后必须锁止运动，禁止继续向限位方向运动
        """
        lockout_state = LockoutState(
            is_locked=True,
            direction=direction,
            triggered_position_mm=position_mm,
            triggered_at=datetime.now().isoformat(),
            auto_unlock_enabled=True,
        )
        self._lockout_states[device_id] = lockout_state

        logger.warning(
            f"LOCKOUT TRIGGERED for {device_id}: "
            f"direction={direction.value}, position={position_mm:.3f}mm",
            extra={
                "device_id": device_id,
                "lockout_direction": direction.value,
                "triggered_position": position_mm,
                "timestamp": lockout_state.triggered_at,
            },
        )

    def _unlock_device(self, device_id: str) -> None:
        """
        解除设备锁止状态。

        Args:
            device_id: 设备唯一标识
        """
        if device_id in self._lockout_states:
            del self._lockout_states[device_id]
            logger.info(f"Device {device_id} unlocked")

    def manual_unlock(self, device_id: str) -> bool:
        """
        手动解除设备锁止状态。

        Args:
            device_id: 设备唯一标识

        Returns:
            bool: 是否成功解除

        Note:
            手动解锁需要谨慎操作，确保设备已离开限位区域
        """
        lockout_state = self._lockout_states.get(device_id)
        if lockout_state is None or not lockout_state.is_locked:
            logger.info(f"Device {device_id} is not locked")
            return True

        self._unlock_device(device_id)
        logger.warning(
            f"MANUAL UNLOCK for {device_id}",
            extra={"device_id": device_id, "action": "manual_unlock"},
        )
        return True

    def get_lockout_status(self, device_id: str) -> LimitLockoutStatus:
        """
        获取设备锁止状态。

        Args:
            device_id: 设备唯一标识

        Returns:
            LimitLockoutStatus: 锁止状态
        """
        lockout_state = self._lockout_states.get(device_id, LockoutState())

        return LimitLockoutStatus(
            is_locked=lockout_state.is_locked,
            lockout_direction=lockout_state.direction.value if lockout_state.direction != LimitDirection.NONE else None,
            triggered_position_mm=lockout_state.triggered_position_mm,
            triggered_at=lockout_state.triggered_at,
            auto_unlock_enabled=lockout_state.auto_unlock_enabled,
        )

    # ==================== 超限保护功能 ====================

    def check_overlimit(
        self,
        device_id: str,
        overlimit_type: OverlimitType,
        actual_value: float,
        limit_value: float,
        direction: LimitDirection = LimitDirection.POSITIVE,
    ) -> tuple[bool, str | None]:
        """
        检查设备参数是否超限。

        Args:
            device_id: 设备唯一标识
            overlimit_type: 超限类型
            actual_value: 实际值
            limit_value: 限值
            direction: 超限方向

        Returns:
            Tuple[bool, Optional[str]]: (是否超限, 告警消息)

        安全约束:
            超限时必须触发安全停机保护
        """
        is_overlimit = False

        if direction == LimitDirection.POSITIVE:
            is_overlimit = actual_value > limit_value
        elif direction == LimitDirection.NEGATIVE:
            is_overlimit = actual_value < limit_value

        if is_overlimit:
            # 记录超限事件
            record = OverlimitRecord(
                device_id=device_id,
                overlimit_type=overlimit_type,
                actual_value=actual_value,
                limit_value=limit_value,
                direction=direction,
                timestamp=datetime.now().isoformat(),
                action_taken="auto_protection_triggered",
            )
            self._add_overlimit_record(record)

            # 构建告警消息
            alarm_msg = (
                f"设备 {device_id} {overlimit_type.value}超限! "
                f"实际值: {actual_value}, 限值: {limit_value}, 方向: {direction.value}"
            )
            logger.error(
                f"OVERLIMIT DETECTED: {alarm_msg}",
                extra={
                    "device_id": device_id,
                    "overlimit_type": overlimit_type.value,
                    "actual_value": actual_value,
                    "limit_value": limit_value,
                    "direction": direction.value,
                },
            )

            return True, alarm_msg

        return False, None

    def check_electromagnet_current(
        self,
        device_id: str,
        current_a: float,
        max_current_a: float,
    ) -> tuple[bool, str | None]:
        """
        检查电磁铁电流是否超限。

        Args:
            device_id: 设备唯一标识
            current_a: 当前电流(A)
            max_current_a: 最大电流限制(A)

        Returns:
            Tuple[bool, Optional[str]]: (是否超限, 告警消息)
        """
        return self.check_overlimit(
            device_id=device_id,
            overlimit_type=OverlimitType.CURRENT,
            actual_value=current_a,
            limit_value=max_current_a,
            direction=LimitDirection.POSITIVE,
        )

    def check_temperature(
        self,
        device_id: str,
        temperature_k: float,
        max_temp_k: float,
        min_temp_k: float,
    ) -> tuple[bool, str | None, LimitDirection | None]:
        """
        检查温度是否超限。

        Args:
            device_id: 设备唯一标识
            temperature_k: 当前温度(K)
            max_temp_k: 最高温度限制(K)
            min_temp_k: 最低温度限制(K)

        Returns:
            Tuple[bool, Optional[str], Optional[LimitDirection]]:
                (是否超限, 告警消息, 超限方向)
        """
        # 检查高温超限
        is_over, msg = self.check_overlimit(
            device_id=device_id,
            overlimit_type=OverlimitType.TEMPERATURE,
            actual_value=temperature_k,
            limit_value=max_temp_k,
            direction=LimitDirection.POSITIVE,
        )
        if is_over:
            return True, msg, LimitDirection.POSITIVE

        # 检查低温超限
        is_over, msg = self.check_overlimit(
            device_id=device_id,
            overlimit_type=OverlimitType.TEMPERATURE,
            actual_value=temperature_k,
            limit_value=min_temp_k,
            direction=LimitDirection.NEGATIVE,
        )
        if is_over:
            return True, msg, LimitDirection.NEGATIVE

        return False, None, None

    def check_piezo_voltage(
        self,
        device_id: str,
        voltage_v: float,
        max_voltage_v: float,
    ) -> tuple[bool, str | None]:
        """
        检查压电控制器电压是否超限。

        Args:
            device_id: 设备唯一标识
            voltage_v: 当前电压(V)
            max_voltage_v: 最大电压限制(V)

        Returns:
            Tuple[bool, Optional[str]]: (是否超限, 告警消息)
        """
        return self.check_overlimit(
            device_id=device_id,
            overlimit_type=OverlimitType.VOLTAGE,
            actual_value=voltage_v,
            limit_value=max_voltage_v,
            direction=LimitDirection.POSITIVE,
        )

    # ==================== 配置管理功能 ====================

    def configure_device_limits(
        self,
        device_id: str,
        positive_limit: float,
        negative_limit: float,
        enable: bool = True,
        tolerance: float = 0.1,
    ) -> None:
        """
        配置设备限位参数。

        Args:
            device_id: 设备唯一标识
            positive_limit: 正向限位
            negative_limit: 负向限位
            enable: 是否启用限位检查
            tolerance: 校验允许误差
        """
        config = DeviceLimitConfig(
            device_id=device_id,
            positive_limit=positive_limit,
            negative_limit=negative_limit,
            enable=enable,
            tolerance=tolerance,
        )
        self._limit_configs[device_id] = config

        logger.info(
            f"Limit config updated for {device_id}: "
            f"[{negative_limit}, {positive_limit}], enabled={enable}",
            extra={
                "device_id": device_id,
                "positive_limit": positive_limit,
                "negative_limit": negative_limit,
                "enabled": enable,
            },
        )

    def get_device_limit_config(self, device_id: str) -> DeviceLimitConfig | None:
        """
        获取设备限位配置。

        Args:
            device_id: 设备唯一标识

        Returns:
            Optional[DeviceLimitConfig]: 限位配置，不存在返回None
        """
        return self._limit_configs.get(device_id)

    # ==================== 历史记录功能 ====================

    def _add_overlimit_record(self, record: OverlimitRecord) -> None:
        """
        添加超限记录到历史。

        Args:
            record: 超限记录
        """
        self._overlimit_history.append(record)

        # 限制历史记录数量
        if len(self._overlimit_history) > self._max_history_size:
            self._overlimit_history.pop(0)

    def get_overlimit_history(
        self,
        device_id: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """
        获取超限历史记录。

        Args:
            device_id: 设备ID过滤，None表示所有设备
            limit: 返回记录数量限制

        Returns:
            List[Dict[str, Any]]: 超限记录列表
        """
        records = self._overlimit_history

        # 按设备ID过滤
        if device_id is not None:
            records = [r for r in records if r.device_id == device_id]

        # 转换为字典并限制数量
        return [
            {
                "device_id": r.device_id,
                "overlimit_type": r.overlimit_type.value,
                "actual_value": r.actual_value,
                "limit_value": r.limit_value,
                "direction": r.direction.value,
                "timestamp": r.timestamp,
                "action_taken": r.action_taken,
            }
            for r in records[-limit:]
        ]

    # ==================== 辅助方法 ====================

    def _is_within_limits(self, position_mm: float, config: DeviceLimitConfig) -> bool:
        """
        检查位置是否在限位范围内。

        Args:
            position_mm: 位置(mm)
            config: 限位配置

        Returns:
            bool: 是否在限位范围内
        """
        return config.negative_limit <= position_mm <= config.positive_limit

    def _determine_direction(
        self,
        current_position_mm: float,
        target_position_mm: float,
    ) -> LimitDirection:
        """
        判断运动方向。

        Args:
            current_position_mm: 当前位置(mm)
            target_position_mm: 目标位置(mm)

        Returns:
            LimitDirection: 运动方向
        """
        if target_position_mm > current_position_mm:
            return LimitDirection.POSITIVE
        elif target_position_mm < current_position_mm:
            return LimitDirection.NEGATIVE
        return LimitDirection.NONE

    def _determine_limit_direction(
        self,
        position_mm: float,
        config: DeviceLimitConfig,
    ) -> LimitDirection:
        """
        判断超限方向。

        Args:
            position_mm: 位置(mm)
            config: 限位配置

        Returns:
            LimitDirection: 超限方向
        """
        if position_mm > config.positive_limit:
            return LimitDirection.POSITIVE
        elif position_mm < config.negative_limit:
            return LimitDirection.NEGATIVE
        return LimitDirection.NONE


# 全局限位防护服务实例
_limit_protection_service: LimitProtectionService | None = None


def get_limit_protection_service() -> LimitProtectionService:
    """
    获取全局限位防护服务实例。

    Returns:
        LimitProtectionService: 限位防护服务实例
    """
    global _limit_protection_service
    if _limit_protection_service is None:
        _limit_protection_service = LimitProtectionService()
    return _limit_protection_service
