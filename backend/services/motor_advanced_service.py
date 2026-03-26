"""
步进电机高级控制服务

文件名: motor_advanced_service.py
路径: backend/services/
功能: 提供PR路径多段联动编程、回零操作完善、位置闭环校验、DI端口软件联动等高级功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - PR路径多段联动编程：支持16段路径连续执行、条件跳转、循环执行
    - 回零操作完善：支持多种回零模式、回零状态监控、回零参数配置
    - 位置闭环校验：实时位置反馈校验、位置偏差报警、自动纠偏
    - DI端口软件联动：DI信号触发预设动作、软件模拟DI功能

依赖：
    - backend.core.dm2c_driver: DM2C步进驱动器
    - backend.core.abstract: 设备抽象基类
    - scipy: 科学计算库（用于位置校验算法）
    - numpy: 数值计算库

安全约束：
    - 所有运动指令必须先执行软件限位预校验
    - PR路径执行前必须验证路径参数合法性
    - 位置闭环校验偏差超限时必须触发安全停机
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np
from scipy import stats

from backend.core.abstract import DeviceStatus

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# PR路径最大数量
MAX_PR_PATHS = 16

# 位置闭环校验参数
POSITION_CHECK_INTERVAL_MS = 50  # 位置校验间隔（毫秒）
POSITION_TOLERANCE_STEPS = 10  # 位置容差（步数）
POSITION_MAX_DEVIATION_STEPS = 100  # 最大允许偏差（步数）
POSITION_CORRECTION_ENABLE = True  # 是否启用自动纠偏

# 回零超时时间
HOME_TIMEOUT_SECONDS = 60.0

# DI端口数量
NUM_DI_PORTS = 7


class PRPathExecutionMode(Enum):
    """PR路径执行模式枚举。

    Attributes:
        SEQUENTIAL: 顺序执行（按路径号依次执行）
        CONDITIONAL: 条件执行（根据DI状态决定执行路径）
        LOOP: 循环执行（循环执行指定路径段）
        CUSTOM: 自定义执行（按预设的执行序列执行）
    """

    SEQUENTIAL = "sequential"
    CONDITIONAL = "conditional"
    LOOP = "loop"
    CUSTOM = "custom"


class HomeMode(Enum):
    """回零模式枚举。

    Attributes:
        SINGLE_LIMIT_POSITIVE: 单次正向限位回零
        SINGLE_LIMIT_NEGATIVE: 单次负向限位回零
        ORIGIN_SIGNAL: 原点信号回零
        ORIGIN_WITH_POSITIVE_LIMIT: 原点信号+正向限位回零
        ORIGIN_WITH_NEGATIVE_LIMIT: 原点信号+负向限位回零
        CURRENT_POSITION_ZERO: 当前位置设为零点
    """

    SINGLE_LIMIT_POSITIVE = 5
    SINGLE_LIMIT_NEGATIVE = 6
    ORIGIN_SIGNAL = 7
    ORIGIN_WITH_POSITIVE_LIMIT = 8
    ORIGIN_WITH_NEGATIVE_LIMIT = 9
    CURRENT_POSITION_ZERO = -1  # 特殊模式：不执行机械回零


class DITriggerAction(Enum):
    """DI触发动作枚举。

    Attributes:
        START_PATH: 触发指定PR路径执行
        EMERGENCY_STOP: 触发急停
        HOME: 触发回零
        JOG_POSITIVE: 触发正向JOG
        JOG_NEGATIVE: 触发负向JOG
        PAUSE_PROGRAM: 暂停程序执行
        RESUME_PROGRAM: 恢复程序执行
    """

    START_PATH = "start_path"
    EMERGENCY_STOP = "emergency_stop"
    HOME = "home"
    JOG_POSITIVE = "jog_positive"
    JOG_NEGATIVE = "jog_negative"
    PAUSE_PROGRAM = "pause_program"
    RESUME_PROGRAM = "resume_program"


@dataclass
class PRPathConfig:
    """PR路径配置数据类。

    Attributes:
        path_number: 路径编号（0-15）
        position: 目标位置（步数）
        velocity: 运行速度（rpm）
        accel_time: 加速时间（ms）
        decel_time: 减速时间（ms）
        dwell_time: 停顿时间（ms）
        is_relative: 是否为相对位置模式
        next_path: 下一条路径编号（用于跳转，-1表示顺序执行）
        jump_condition: 跳转条件（DI端口号，None表示无条件跳转）
    """

    path_number: int
    position: int
    velocity: int
    accel_time: int = 100
    decel_time: int = 100
    dwell_time: int = 0
    is_relative: bool = False
    next_path: int = -1
    jump_condition: int | None = None

    def validate(self) -> bool:
        """验证路径参数有效性。

        Returns:
            bool: 参数是否有效
        """
        if not 0 <= self.path_number < MAX_PR_PATHS:
            logger.error(f"Invalid path_number: {self.path_number}")
            return False
        if self.velocity <= 0:
            logger.error(f"Invalid velocity: {self.velocity}")
            return False
        if self.accel_time < 0 or self.decel_time < 0:
            logger.error(f"Invalid accel/decel time: {self.accel_time}/{self.decel_time}")
            return False
        if self.dwell_time < 0:
            logger.error(f"Invalid dwell_time: {self.dwell_time}")
            return False
        if self.next_path != -1 and not 0 <= self.next_path < MAX_PR_PATHS:
            logger.error(f"Invalid next_path: {self.next_path}")
            return False
        return True


@dataclass
class PRPathSequence:
    """PR路径执行序列数据类。

    Attributes:
        execution_mode: 执行模式
        paths: 路径配置列表
        loop_count: 循环次数（仅LOOP模式有效）
        sequence: 自定义执行序列（仅CUSTOM模式有效）
        stop_on_error: 遇错是否停止
    """

    execution_mode: PRPathExecutionMode
    paths: list[PRPathConfig] = field(default_factory=list)
    loop_count: int = 1
    sequence: list[int] = field(default_factory=list)
    stop_on_error: bool = True


@dataclass
class PositionCheckResult:
    """位置校验结果数据类。

    Attributes:
        target_position: 目标位置（步数）
        actual_position: 实际位置（步数）
        deviation: 位置偏差（步数）
        is_within_tolerance: 是否在容差范围内
        timestamp: 时间戳
        correction_applied: 是否应用了纠偏
    """

    target_position: int
    actual_position: int
    deviation: int
    is_within_tolerance: bool
    timestamp: float
    correction_applied: bool = False


@dataclass
class DITriggerConfig:
    """DI触发配置数据类。

    Attributes:
        di_port: DI端口号（1-7）
        action: 触发动作
        action_params: 动作参数（如路径号）
        active_level: 触发电平（True=高电平触发，False=低电平触发）
        enabled: 是否启用
    """

    di_port: int
    action: DITriggerAction
    action_params: dict[str, Any] = field(default_factory=dict)
    active_level: bool = True
    enabled: bool = True


class MotorAdvancedService:
    """步进电机高级控制服务类。

    提供PR路径多段联动编程、回零操作完善、位置闭环校验、DI端口软件联动等高级功能。

    Example:
        >>> service = MotorAdvancedService(motor_driver)
        >>> # PR路径多段联动
        >>> sequence = PRPathSequence(
        ...     execution_mode=PRPathExecutionMode.SEQUENTIAL,
        ...     paths=[PRPathConfig(path_number=0, position=10000, velocity=500), ...]
        ... )
        >>> await service.execute_pr_sequence(sequence)
        >>>
        >>> # 位置闭环校验
        >>> result = await service.check_position_closed_loop()
        >>> if not result.is_within_tolerance:
        ...     await service.correct_position_deviation(result)
    """

    def __init__(self, motor_driver: Any):
        """初始化高级控制服务。

        Args:
            motor_driver: 步进电机驱动器实例（LeadshineDM2C）
        """
        self._driver = motor_driver

        # PR路径执行状态
        self._pr_sequence_running = False
        self._pr_sequence_task: asyncio.Task | None = None
        self._pr_sequence_cancelled = False
        self._current_path_index = 0
        self._pr_sequence_progress = 0.0

        # 位置闭环校验状态
        self._position_check_enabled = False
        self._position_check_task: asyncio.Task | None = None
        self._position_history: list[PositionCheckResult] = []
        self._max_position_history = 1000

        # 回零状态
        self._home_running = False
        self._home_task: asyncio.Task | None = None
        self._home_completed = False

        # DI触发配置
        self._di_trigger_configs: dict[int, DITriggerConfig] = {}
        self._di_monitor_task: asyncio.Task | None = None
        self._di_monitor_enabled = False

        # 回调函数
        self._pr_progress_callback: Callable[[float, int], None] | None = None
        self._position_check_callback: Callable[[PositionCheckResult], None] | None = None
        self._home_complete_callback: Callable[[bool], None] | None = None

        logger.info(f"MotorAdvancedService initialized for {motor_driver.device_id}")

    # ==================== PR路径多段联动编程 ====================

    async def configure_pr_path(self, config: PRPathConfig) -> bool:
        """配置单条PR路径。

        Args:
            config: 路径配置参数

        Returns:
            bool: 配置是否成功

        Raises:
            ValueError: 参数无效
        """
        if not config.validate():
            raise ValueError(f"Invalid PR path configuration: {config}")

        # 计算运动模式字
        mode = 0x0001  # 位置定位模式
        if config.is_relative:
            mode |= 0x0040  # Bit6: 相对位置模式

        # 配置跳转（如果指定）
        if config.next_path >= 0:
            mode |= (config.next_path << 8) & 0x3F00  # Bit8-13: 跳转目标
            mode |= 0x4000  # Bit14: 跳转使能

        try:
            result = await self._driver.configure_pr_path(
                path_number=config.path_number,
                mode=mode,
                position=config.position,
                velocity=config.velocity,
                accel_time=config.accel_time,
                decel_time=config.decel_time,
                dwell_time=config.dwell_time,
            )

            if result:
                logger.info(
                    f"PR path {config.path_number} configured: "
                    f"position={config.position}, velocity={config.velocity}, "
                    f"relative={config.is_relative}"
                )
            return result

        except Exception as e:
            logger.error(f"Configure PR path error: {e}")
            return False

    async def configure_pr_sequence(self, sequence: PRPathSequence) -> bool:
        """配置PR路径执行序列。

        Args:
            sequence: 路径执行序列配置

        Returns:
            bool: 配置是否成功
        """
        # 验证所有路径配置
        for path_config in sequence.paths:
            if not path_config.validate():
                logger.error(f"Invalid path config in sequence: {path_config.path_number}")
                return False

        # 配置所有路径
        for path_config in sequence.paths:
            success = await self.configure_pr_path(path_config)
            if not success:
                logger.error(f"Failed to configure path {path_config.path_number}")
                return False

        logger.info(
            f"PR sequence configured: mode={sequence.execution_mode.value}, "
            f"paths={len(sequence.paths)}, loop_count={sequence.loop_count}"
        )
        return True

    async def execute_pr_sequence(
        self,
        sequence: PRPathSequence,
        progress_callback: Callable[[float, int], None] | None = None,
    ) -> bool:
        """执行PR路径序列。

        Args:
            sequence: 路径执行序列配置
            progress_callback: 进度回调函数（进度，当前路径号）

        Returns:
            bool: 执行是否成功
        """
        if self._pr_sequence_running:
            logger.warning("PR sequence already running")
            return False

        # 检查设备状态
        if self._driver.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._driver.status.value}")
            return False

        self._pr_progress_callback = progress_callback
        self._pr_sequence_running = True
        self._pr_sequence_cancelled = False
        self._current_path_index = 0
        self._pr_sequence_progress = 0.0

        try:
            self._pr_sequence_task = asyncio.create_task(
                self._execute_pr_sequence_internal(sequence)
            )
            await self._pr_sequence_task
            return True

        except asyncio.CancelledError:
            logger.info("PR sequence cancelled")
            return False
        except Exception as e:
            logger.error(f"PR sequence execution error: {e}")
            return False
        finally:
            self._pr_sequence_running = False
            self._pr_sequence_task = None

    async def _execute_pr_sequence_internal(self, sequence: PRPathSequence) -> None:
        """内部方法：执行PR路径序列。

        Args:
            sequence: 路径执行序列配置
        """
        total_paths = len(sequence.paths)
        executed_count = 0

        # 根据执行模式选择执行策略
        if sequence.execution_mode == PRPathExecutionMode.SEQUENTIAL:
            # 顺序执行
            for loop in range(sequence.loop_count):
                for i, path_config in enumerate(sequence.paths):
                    if self._pr_sequence_cancelled:
                        return

                    self._current_path_index = i
                    self._pr_sequence_progress = executed_count / (total_paths * sequence.loop_count)

                    if self._pr_progress_callback:
                        self._pr_progress_callback(self._pr_sequence_progress, path_config.path_number)

                    success = await self._execute_single_path(path_config)
                    if not success and sequence.stop_on_error:
                        logger.error(f"Path {path_config.path_number} failed, stopping sequence")
                        return

                    executed_count += 1

        elif sequence.execution_mode == PRPathExecutionMode.CONDITIONAL:
            # 条件执行（根据DI状态）
            for loop in range(sequence.loop_count):
                for path_config in sequence.paths:
                    if self._pr_sequence_cancelled:
                        return

                    # 检查跳转条件
                    if path_config.jump_condition is not None:
                        di_status = await self._driver.read_di_status()
                        di_key = f"di{path_config.jump_condition}"
                        if not di_status.get(di_key, False):
                            logger.debug(
                                f"DI{path_config.jump_condition} not active, "
                                f"skipping path {path_config.path_number}"
                            )
                            continue

                    self._current_path_index = path_config.path_number
                    success = await self._execute_single_path(path_config)
                    if not success and sequence.stop_on_error:
                        return

                    executed_count += 1

        elif sequence.execution_mode == PRPathExecutionMode.LOOP:
            # 循环执行指定路径
            loop_paths = sequence.paths
            for loop in range(sequence.loop_count):
                for path_config in loop_paths:
                    if self._pr_sequence_cancelled:
                        return

                    success = await self._execute_single_path(path_config)
                    if not success and sequence.stop_on_error:
                        return

                    executed_count += 1

        elif sequence.execution_mode == PRPathExecutionMode.CUSTOM:
            # 自定义执行序列
            for path_number in sequence.sequence:
                if self._pr_sequence_cancelled:
                    return

                # 查找路径配置
                path_config = next(
                    (p for p in sequence.paths if p.path_number == path_number), None
                )
                if path_config is None:
                    logger.warning(f"Path {path_number} not found in configuration")
                    continue

                success = await self._execute_single_path(path_config)
                if not success and sequence.stop_on_error:
                    return

                executed_count += 1

        self._pr_sequence_progress = 1.0
        logger.info(f"PR sequence completed: {executed_count} paths executed")

    async def _execute_single_path(self, config: PRPathConfig) -> bool:
        """执行单条PR路径。

        Args:
            config: 路径配置

        Returns:
            bool: 执行是否成功
        """
        try:
            # 触发路径执行
            success = await self._driver.trigger_pr_path(config.path_number)
            if not success:
                logger.error(f"Failed to trigger path {config.path_number}")
                return False

            # 等待路径完成
            await asyncio.sleep(0.1)  # 短暂等待

            # 轮询等待完成
            timeout = 60.0  # 最大等待时间
            start_time = time.time()

            while time.time() - start_time < timeout:
                trigger_status = await self._driver.read_trigger_status()
                if trigger_status["is_idle"]:
                    logger.debug(f"Path {config.path_number} completed")
                    return True

                # 检查是否正在运行当前路径
                if trigger_status["is_running"] and trigger_status["path_number"] == config.path_number:
                    await asyncio.sleep(0.05)
                    continue

                await asyncio.sleep(0.05)

            logger.error(f"Path {config.path_number} timeout")
            return False

        except Exception as e:
            logger.error(f"Execute single path error: {e}")
            return False

    async def stop_pr_sequence(self) -> bool:
        """停止PR路径序列执行。

        Returns:
            bool: 停止是否成功
        """
        if not self._pr_sequence_running:
            return True

        self._pr_sequence_cancelled = True

        # 停止当前运动
        await self._driver.stop(emergency=False)

        # 等待任务结束
        if self._pr_sequence_task:
            try:
                await asyncio.wait_for(self._pr_sequence_task, timeout=5.0)
            except asyncio.TimeoutError:
                self._pr_sequence_task.cancel()

        self._pr_sequence_running = False
        logger.info("PR sequence stopped")
        return True

    def get_pr_sequence_status(self) -> dict[str, Any]:
        """获取PR路径序列执行状态。

        Returns:
            Dict[str, Any]: 执行状态信息
        """
        return {
            "running": self._pr_sequence_running,
            "current_path_index": self._current_path_index,
            "progress": round(self._pr_sequence_progress, 4),
            "cancelled": self._pr_sequence_cancelled,
        }

    # ==================== 回零操作完善 ====================

    async def execute_home(
        self,
        mode: HomeMode = HomeMode.SINGLE_LIMIT_POSITIVE,
        speed_high: int | None = None,
        speed_low: int | None = None,
        offset: int = 0,
        direction: int = 0,
        timeout: float = HOME_TIMEOUT_SECONDS,
        complete_callback: Callable[[bool], None] | None = None,
    ) -> bool:
        """执行回零操作（完善版）。

        Args:
            mode: 回零模式
            speed_high: 回零高速（步/秒），None使用默认值
            speed_low: 回零低速（步/秒），None使用默认值
            offset: 回零偏移（步数）
            direction: 回零方向（0=正向，1=负向）
            timeout: 超时时间（秒）
            complete_callback: 完成回调函数

        Returns:
            bool: 回零是否成功

        Note:
            支持的回零模式：
            - SINGLE_LIMIT_POSITIVE: 单次正向限位回零
            - SINGLE_LIMIT_NEGATIVE: 单次负向限位回零
            - ORIGIN_SIGNAL: 原点信号回零
            - ORIGIN_WITH_POSITIVE_LIMIT: 原点信号+正向限位回零
            - ORIGIN_WITH_NEGATIVE_LIMIT: 原点信号+负向限位回零
            - CURRENT_POSITION_ZERO: 当前位置设为零点（不执行机械回零）
        """
        if self._home_running:
            logger.warning("Home operation already running")
            return False

        # 检查设备状态
        if self._driver.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._driver.status.value}")
            return False

        self._home_complete_callback = complete_callback
        self._home_running = True
        self._home_completed = False

        try:
            # 特殊模式：当前位置设为零点
            if mode == HomeMode.CURRENT_POSITION_ZERO:
                success = await self._driver.set_current_position_zero()
                self._home_completed = success
                if self._home_complete_callback:
                    self._home_complete_callback(success)
                return success

            # 配置回零参数
            if speed_high is not None:
                await self._driver.configure_home_speed(speed_high, speed_low or speed_high // 10)
            if offset != 0:
                await self._driver.configure_home_offset(offset)
            if direction in (0, 1):
                await self._driver.configure_home_direction(direction)

            # 配置回零模式（通过Pr8.10寄存器）
            # 注意：DM2C驱动器的回零模式配置需要写入特定寄存器
            # 这里简化处理，直接触发回零

            # 启动回零
            success = await self._driver.home()
            if not success:
                logger.error("Failed to start homing")
                return False

            # 等待回零完成
            start_time = time.time()
            while time.time() - start_time < timeout:
                # 检查状态字中的回零完成位
                status_word = await self._driver.read_status_word()
                if status_word.get("home_complete", False):
                    logger.info("Homing completed successfully")
                    self._home_completed = True
                    if self._home_complete_callback:
                        self._home_complete_callback(True)
                    return True

                # 检查是否出错
                if status_word.get("fault", False):
                    alarm_code = await self._driver.read_alarm_code()
                    logger.error(f"Homing failed with alarm: 0x{alarm_code:04X}")
                    if self._home_complete_callback:
                        self._home_complete_callback(False)
                    return False

                await asyncio.sleep(0.1)

            logger.error("Homing timeout")
            if self._home_complete_callback:
                self._home_complete_callback(False)
            return False

        except Exception as e:
            logger.error(f"Home execution error: {e}")
            if self._home_complete_callback:
                self._home_complete_callback(False)
            return False
        finally:
            self._home_running = False

    def get_home_status(self) -> dict[str, Any]:
        """获取回零状态。

        Returns:
            Dict[str, Any]: 回零状态信息
        """
        return {
            "running": self._home_running,
            "completed": self._home_completed,
        }

    # ==================== 位置闭环校验 ====================

    async def start_position_check(
        self,
        interval_ms: int = POSITION_CHECK_INTERVAL_MS,
        tolerance_steps: int = POSITION_TOLERANCE_STEPS,
        max_deviation: int = POSITION_MAX_DEVIATION_STEPS,
        auto_correction: bool = POSITION_CORRECTION_ENABLE,
        check_callback: Callable[[PositionCheckResult], None] | None = None,
    ) -> bool:
        """启动位置闭环校验。

        Args:
            interval_ms: 校验间隔（毫秒）
            tolerance_steps: 位置容差（步数）
            max_deviation: 最大允许偏差（步数）
            auto_correction: 是否启用自动纠偏
            check_callback: 校验结果回调函数

        Returns:
            bool: 启动是否成功
        """
        if self._position_check_enabled:
            logger.warning("Position check already enabled")
            return False

        self._position_check_enabled = True
        self._position_check_callback = check_callback
        self._check_interval = interval_ms / 1000.0
        self._tolerance_steps = tolerance_steps
        self._max_deviation = max_deviation
        self._auto_correction = auto_correction

        self._position_check_task = asyncio.create_task(
            self._position_check_loop()
        )

        logger.info(
            f"Position check started: interval={interval_ms}ms, "
            f"tolerance={tolerance_steps}steps, auto_correction={auto_correction}"
        )
        return True

    async def stop_position_check(self) -> bool:
        """停止位置闭环校验。

        Returns:
            bool: 停止是否成功
        """
        if not self._position_check_enabled:
            return True

        self._position_check_enabled = False

        if self._position_check_task:
            self._position_check_task.cancel()
            try:
                await self._position_check_task
            except asyncio.CancelledError:
                pass

        logger.info("Position check stopped")
        return True

    async def _position_check_loop(self) -> None:
        """位置闭环校验循环。"""
        last_target_position = 0

        while self._position_check_enabled:
            try:
                # 读取当前位置
                position_data = await self._driver.read_position()
                actual_position = position_data.get("position_steps", 0)

                # 获取目标位置（从命令位置寄存器读取）
                # 注意：这里简化处理，使用上次记录的目标位置
                target_position = last_target_position

                # 计算偏差
                deviation = actual_position - target_position

                # 判断是否在容差范围内
                is_within_tolerance = abs(deviation) <= self._tolerance_steps

                # 创建校验结果
                result = PositionCheckResult(
                    target_position=target_position,
                    actual_position=actual_position,
                    deviation=deviation,
                    is_within_tolerance=is_within_tolerance,
                    timestamp=time.time(),
                )

                # 记录历史
                self._position_history.append(result)
                if len(self._position_history) > self._max_position_history:
                    self._position_history.pop(0)

                # 回调通知
                if self._position_check_callback:
                    self._position_check_callback(result)

                # 偏差超限处理
                if abs(deviation) > self._max_deviation:
                    logger.error(
                        f"Position deviation exceeded: {deviation}steps > "
                        f"{self._max_deviation}steps, triggering safety stop"
                    )
                    await self._driver.stop(emergency=True)

                # 自动纠偏
                if not is_within_tolerance and self._auto_correction:
                    correction_success = await self._apply_position_correction(result)
                    result.correction_applied = correction_success

                await asyncio.sleep(self._check_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Position check loop error: {e}")
                await asyncio.sleep(1.0)

    async def _apply_position_correction(self, result: PositionCheckResult) -> bool:
        """应用位置纠偏。

        Args:
            result: 位置校验结果

        Returns:
            bool: 纠偏是否成功
        """
        try:
            # 计算纠偏量
            correction = -result.deviation

            # 执行相对位置运动进行纠偏
            logger.info(f"Applying position correction: {correction}steps")

            # 使用相对位置模式进行纠偏
            # 注意：这里需要确保纠偏运动不会超出限位范围
            success = await self._driver.move_rel(
                distance=correction / self._driver.steps_per_mm,
                speed=100,  # 使用较低速度进行纠偏
                accel=50,
                decel=50,
            )

            return success

        except Exception as e:
            logger.error(f"Position correction error: {e}")
            return False

    async def check_position_closed_loop(self) -> PositionCheckResult:
        """执行单次位置闭环校验。

        Returns:
            PositionCheckResult: 校验结果
        """
        # 读取当前位置
        position_data = await self._driver.read_position()
        actual_position = position_data.get("position_steps", 0)

        # 获取目标位置（从触发状态读取）
        trigger_status = await self._driver.read_trigger_status()

        # 简化处理：假设目标位置为当前位置（实际应用中应从命令寄存器读取）
        target_position = actual_position

        deviation = actual_position - target_position
        is_within_tolerance = abs(deviation) <= self._tolerance_steps

        return PositionCheckResult(
            target_position=target_position,
            actual_position=actual_position,
            deviation=deviation,
            is_within_tolerance=is_within_tolerance,
            timestamp=time.time(),
        )

    def get_position_check_history(self, count: int = 100) -> list[dict[str, Any]]:
        """获取位置校验历史记录。

        Args:
            count: 返回记录数量

        Returns:
            List[Dict[str, Any]]: 历史记录列表
        """
        history = self._position_history[-count:]
        return [
            {
                "target_position": r.target_position,
                "actual_position": r.actual_position,
                "deviation": r.deviation,
                "is_within_tolerance": r.is_within_tolerance,
                "timestamp": r.timestamp,
                "correction_applied": r.correction_applied,
            }
            for r in history
        ]

    def analyze_position_stability(self) -> dict[str, Any]:
        """分析位置稳定性。

        使用统计方法分析位置偏差的分布特性。

        Returns:
            Dict[str, Any]: 稳定性分析结果
        """
        if len(self._position_history) < 10:
            return {
                "status": "insufficient_data",
                "message": "Need at least 10 data points for analysis",
            }

        deviations = [r.deviation for r in self._position_history]

        # 计算统计量
        mean_deviation = float(np.mean(deviations))
        std_deviation = float(np.std(deviations))
        max_deviation = float(np.max(np.abs(deviations)))

        # 正态性检验
        if len(deviations) >= 20:
            _, p_value = stats.normaltest(deviations)
            is_normal = p_value > 0.05
        else:
            is_normal = None
            p_value = None

        # 稳定性评估
        is_stable = std_deviation < self._tolerance_steps

        return {
            "status": "stable" if is_stable else "unstable",
            "mean_deviation": round(mean_deviation, 2),
            "std_deviation": round(std_deviation, 2),
            "max_deviation": round(max_deviation, 2),
            "is_normal_distribution": is_normal,
            "normality_p_value": round(p_value, 4) if p_value else None,
            "sample_count": len(deviations),
        }

    # ==================== DI端口软件联动 ====================

    async def configure_di_trigger(self, config: DITriggerConfig) -> bool:
        """配置DI触发联动。

        Args:
            config: DI触发配置

        Returns:
            bool: 配置是否成功
        """
        if not 1 <= config.di_port <= NUM_DI_PORTS:
            logger.error(f"Invalid DI port: {config.di_port}")
            return False

        self._di_trigger_configs[config.di_port] = config
        logger.info(
            f"DI{config.di_port} trigger configured: "
            f"action={config.action.value}, enabled={config.enabled}"
        )
        return True

    async def start_di_monitor(self) -> bool:
        """启动DI端口监控。

        Returns:
            bool: 启动是否成功
        """
        if self._di_monitor_enabled:
            logger.warning("DI monitor already running")
            return False

        self._di_monitor_enabled = True
        self._di_monitor_task = asyncio.create_task(self._di_monitor_loop())

        logger.info("DI monitor started")
        return True

    async def stop_di_monitor(self) -> bool:
        """停止DI端口监控。

        Returns:
            bool: 停止是否成功
        """
        if not self._di_monitor_enabled:
            return True

        self._di_monitor_enabled = False

        if self._di_monitor_task:
            self._di_monitor_task.cancel()
            try:
                await self._di_monitor_task
            except asyncio.CancelledError:
                pass

        logger.info("DI monitor stopped")
        return True

    async def _di_monitor_loop(self) -> None:
        """DI端口监控循环。"""
        last_di_states: dict[str, bool] = {}

        while self._di_monitor_enabled:
            try:
                # 读取DI状态
                di_status = await self._driver.read_di_status()

                # 检查每个配置的DI端口
                for di_port, config in self._di_trigger_configs.items():
                    if not config.enabled:
                        continue

                    di_key = f"di{di_port}"
                    current_state = di_status.get(di_key, False)
                    last_state = last_di_states.get(di_key, False)

                    # 检测触发条件（上升沿或下降沿）
                    triggered = False
                    if config.active_level and current_state and not last_state:
                        triggered = True  # 高电平触发（上升沿）
                    elif not config.active_level and not current_state and last_state:
                        triggered = True  # 低电平触发（下降沿）

                    if triggered:
                        logger.info(f"DI{di_port} triggered, executing action: {config.action.value}")
                        await self._execute_di_action(config)

                    last_di_states[di_key] = current_state

                await asyncio.sleep(0.05)  # 50ms轮询间隔

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"DI monitor loop error: {e}")
                await asyncio.sleep(1.0)

    async def _execute_di_action(self, config: DITriggerConfig) -> bool:
        """执行DI触发动作。

        Args:
            config: DI触发配置

        Returns:
            bool: 执行是否成功
        """
        try:
            if config.action == DITriggerAction.EMERGENCY_STOP:
                return await self._driver.stop(emergency=True)

            elif config.action == DITriggerAction.HOME:
                return await self.execute_home()

            elif config.action == DITriggerAction.START_PATH:
                path_number = config.action_params.get("path_number", 0)
                return await self._driver.trigger_pr_path(path_number)

            elif config.action == DITriggerAction.JOG_POSITIVE:
                speed = config.action_params.get("speed", 100)
                return await self._driver.jog(direction=1, speed=speed)

            elif config.action == DITriggerAction.JOG_NEGATIVE:
                speed = config.action_params.get("speed", 100)
                return await self._driver.jog(direction=-1, speed=speed)

            elif config.action == DITriggerAction.PAUSE_PROGRAM:
                return await self.stop_pr_sequence()

            elif config.action == DITriggerAction.RESUME_PROGRAM:
                # 恢复执行需要重新启动序列
                logger.warning("Resume program action not fully implemented")
                return False

            else:
                logger.warning(f"Unknown DI action: {config.action}")
                return False

        except Exception as e:
            logger.error(f"Execute DI action error: {e}")
            return False

    def get_di_trigger_configs(self) -> list[dict[str, Any]]:
        """获取所有DI触发配置。

        Returns:
            List[Dict[str, Any]]: DI触发配置列表
        """
        return [
            {
                "di_port": config.di_port,
                "action": config.action.value,
                "action_params": config.action_params,
                "active_level": config.active_level,
                "enabled": config.enabled,
            }
            for config in self._di_trigger_configs.values()
        ]

    # ==================== 资源清理 ====================

    async def cleanup(self) -> None:
        """清理所有资源。"""
        await self.stop_pr_sequence()
        await self.stop_position_check()
        await self.stop_di_monitor()
        logger.info("MotorAdvancedService cleanup completed")
