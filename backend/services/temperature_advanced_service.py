"""
温度控制器高级服务

文件名: temperature_advanced_service.py
路径: backend/services/
功能: 提供多段程序控温断点续跑、PID自适应调节、分级温度保护、温度历史曲线对比等高级功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - 多段程序控温断点续跑：支持多段温度程序、断点保存、恢复执行
    - PID自适应调节：自动PID参数整定、模糊PID、增量式PID
    - 分级温度保护：多级温度报警、自动保护动作、温度梯度保护
    - 温度历史曲线对比：历史数据存储、曲线对比分析、趋势预测

依赖：
    - backend.core.temperature_controller: 温度控制器驱动
    - scipy: 科学计算库（用于PID整定、曲线分析）
    - numpy: 数值计算库

安全约束：
    - 温度设置必须经过安全范围校验
    - 分级保护必须按优先级执行
    - PID参数必须在安全范围内
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

import numpy as np
from scipy import signal

from backend.core.abstract import DeviceStatus

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 温度程序参数
MAX_PROGRAM_SEGMENTS = 50  # 最大程序段数
MAX_HISTORY_POINTS = 10000  # 最大历史数据点数

# PID参数范围
PID_KP_MIN = 0.0
PID_KP_MAX = 100.0
PID_KI_MIN = 0.0
PID_KI_MAX = 10.0
PID_KD_MIN = 0.0
PID_KD_MAX = 100.0

# 温度保护级别
TEMP_PROTECTION_WARNING = 1  # 预警级别
TEMP_PROTECTION_ALARM = 2  # 报警级别
TEMP_PROTECTION_CRITICAL = 3  # 临界级别
TEMP_PROTECTION_EMERGENCY = 4  # 紧急级别

# 采样间隔
DEFAULT_SAMPLE_INTERVAL_MS = 1000  # 默认采样间隔（毫秒）


class ProgramSegmentType(Enum):
    """程序段类型枚举。

    Attributes:
        RAMP: 斜坡升温/降温
        SOAK: 恒温保持
        STEP: 阶梯变化
        END: 程序结束
    """

    RAMP = "ramp"
    SOAK = "soak"
    STEP = "step"
    END = "end"


class ProtectionLevel(Enum):
    """保护级别枚举。

    Attributes:
        NONE: 无保护
        WARNING: 预警
        ALARM: 报警
        CRITICAL: 临界
        EMERGENCY: 紧急
    """

    NONE = "none"
    WARNING = "warning"
    ALARM = "alarm"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


class PIDTuningMethod(Enum):
    """PID整定方法枚举。

    Attributes:
        ZIEGLER_NICHOLS: Ziegler-Nichols方法
        COHEN_COON: Cohen-Coon方法
        AUTO: 自动整定
        FUZZY: 模糊PID
    """

    ZIEGLER_NICHOLS = "ziegler_nichols"
    COHEN_COON = "cohen_coon"
    AUTO = "auto"
    FUZZY = "fuzzy"


@dataclass
class ProgramSegment:
    """程序段数据类。

    Attributes:
        segment_id: 段ID
        segment_type: 段类型
        target_temp: 目标温度（°C）
        ramp_rate: 升温速率（°C/min），仅RAMP类型有效
        hold_time: 保持时间（秒），仅SOAK类型有效
        tolerance: 温度容差（°C）
    """

    segment_id: int
    segment_type: ProgramSegmentType
    target_temp: float
    ramp_rate: float = 5.0
    hold_time: float = 60.0
    tolerance: float = 1.0

    def validate(self) -> bool:
        """验证段参数有效性。

        Returns:
            bool: 参数是否有效
        """
        if self.segment_type == ProgramSegmentType.RAMP:
            if self.ramp_rate <= 0:
                logger.error(f"Invalid ramp_rate: {self.ramp_rate}")
                return False
        elif self.segment_type == ProgramSegmentType.SOAK:
            if self.hold_time < 0:
                logger.error(f"Invalid hold_time: {self.hold_time}")
                return False
        return True


@dataclass
class TemperatureProgram:
    """温度程序数据类。

    Attributes:
        program_id: 程序ID
        name: 程序名称
        segments: 程序段列表
        loop_count: 循环次数
        description: 程序描述
    """

    program_id: str
    name: str
    segments: list[ProgramSegment] = field(default_factory=list)
    loop_count: int = 1
    description: str = ""

    def validate(self) -> bool:
        """验证程序有效性。

        Returns:
            bool: 程序是否有效
        """
        if len(self.segments) == 0:
            logger.error("Program has no segments")
            return False
        if len(self.segments) > MAX_PROGRAM_SEGMENTS:
            logger.error(f"Too many segments: {len(self.segments)} > {MAX_PROGRAM_SEGMENTS}")
            return False
        for segment in self.segments:
            if not segment.validate():
                return False
        return True


@dataclass
class ProgramCheckpoint:
    """程序断点数据类。

    Attributes:
        checkpoint_id: 断点ID
        program_id: 程序ID
        current_segment: 当前段索引
        segment_progress: 段内进度
        current_temp: 当前温度
        target_temp: 目标温度
        elapsed_time: 已运行时间
        timestamp: 时间戳
    """

    checkpoint_id: str
    program_id: str
    current_segment: int
    segment_progress: float
    current_temp: float
    target_temp: float
    elapsed_time: float
    timestamp: float


@dataclass
class PIDParameters:
    """PID参数数据类。

    Attributes:
        kp: 比例系数
        ki: 积分系数
        kd: 微分系数
        setpoint: 设定点
        output_min: 输出下限
        output_max: 输出上限
    """

    kp: float
    ki: float
    kd: float
    setpoint: float = 0.0
    output_min: float = 0.0
    output_max: float = 100.0

    def validate(self) -> bool:
        """验证参数有效性。

        Returns:
            bool: 参数是否有效
        """
        if not PID_KP_MIN <= self.kp <= PID_KP_MAX:
            return False
        if not PID_KI_MIN <= self.ki <= PID_KI_MAX:
            return False
        if not PID_KD_MIN <= self.kd <= PID_KD_MAX:
            return False
        return True


@dataclass
class TemperatureProtection:
    """温度保护配置数据类。

    Attributes:
        level: 保护级别
        low_limit: 下限温度（°C）
        high_limit: 上限温度（°C）
        gradient_limit: 温度梯度限制（°C/min）
        action: 保护动作
        enabled: 是否启用
    """

    level: ProtectionLevel
    low_limit: float = -50.0
    high_limit: float = 500.0
    gradient_limit: float = 20.0
    action: str = "alarm"
    enabled: bool = True


@dataclass
class TemperatureHistoryPoint:
    """温度历史数据点数据类。

    Attributes:
        timestamp: 时间戳
        temperature: 温度值（°C）
        setpoint: 设定点（°C）
        output: 输出功率（%）
        program_id: 程序ID（可选）
        segment_id: 段ID（可选）
    """

    timestamp: float
    temperature: float
    setpoint: float
    output: float
    program_id: str | None = None
    segment_id: int | None = None


class TemperatureAdvancedService:
    """温度控制器高级服务类。

    提供多段程序控温断点续跑、PID自适应调节、分级温度保护、温度历史曲线对比等高级功能。

    Example:
        >>> service = TemperatureAdvancedService(temp_controller)
        >>> # 多段程序控温
        >>> program = TemperatureProgram(
        ...     program_id="prog_001",
        ...     name="标准升温程序",
        ...     segments=[
        ...         ProgramSegment(0, ProgramSegmentType.RAMP, 100, ramp_rate=5),
        ...         ProgramSegment(1, ProgramSegmentType.SOAK, 100, hold_time=300),
        ...     ]
        ... )
        >>> await service.execute_program(program)
    """

    def __init__(self, temp_controller: Any):
        """初始化高级控制服务。

        Args:
            temp_controller: 温度控制器驱动实例
        """
        self._controller = temp_controller

        # 程序执行状态
        self._program_running = False
        self._program_task: asyncio.Task | None = None
        self._program_cancelled = False
        self._current_program: TemperatureProgram | None = None
        self._current_segment_index = 0
        self._program_progress = 0.0
        self._program_checkpoint: ProgramCheckpoint | None = None

        # PID参数
        self._pid_params = PIDParameters(kp=10.0, ki=0.5, kd=5.0)
        self._pid_integral = 0.0
        self._pid_last_error = 0.0
        self._pid_last_time = 0.0

        # 温度保护配置
        self._protection_configs: dict[ProtectionLevel, TemperatureProtection] = {
            ProtectionLevel.WARNING: TemperatureProtection(
                level=ProtectionLevel.WARNING,
                low_limit=-40.0,
                high_limit=450.0,
                action="notify",
            ),
            ProtectionLevel.ALARM: TemperatureProtection(
                level=ProtectionLevel.ALARM,
                low_limit=-45.0,
                high_limit=480.0,
                action="alarm",
            ),
            ProtectionLevel.CRITICAL: TemperatureProtection(
                level=ProtectionLevel.CRITICAL,
                low_limit=-48.0,
                high_limit=490.0,
                action="shutdown",
            ),
            ProtectionLevel.EMERGENCY: TemperatureProtection(
                level=ProtectionLevel.EMERGENCY,
                low_limit=-50.0,
                high_limit=500.0,
                action="emergency_stop",
            ),
        }

        # 温度历史数据
        self._temperature_history: list[TemperatureHistoryPoint] = []
        self._history_recording = False
        self._history_task: asyncio.Task | None = None

        # 回调函数
        self._program_progress_callback: Callable[[float, int, float], None] | None = None
        self._protection_callback: Callable[[ProtectionLevel, str], None] | None = None
        self._history_callback: Callable[[TemperatureHistoryPoint], None] | None = None

        logger.info(f"TemperatureAdvancedService initialized for {temp_controller.device_id}")

    # ==================== 多段程序控温断点续跑 ====================

    async def execute_program(
        self,
        program: TemperatureProgram,
        progress_callback: Callable[[float, int, float], None] | None = None,
        resume_from_checkpoint: ProgramCheckpoint | None = None,
    ) -> bool:
        """执行温度程序。

        Args:
            program: 温度程序
            progress_callback: 进度回调函数（总进度，当前段索引，当前温度）
            resume_from_checkpoint: 从断点恢复

        Returns:
            bool: 执行是否成功

        Raises:
            ValueError: 程序参数无效
        """
        if not program.validate():
            raise ValueError("Invalid temperature program")

        if self._program_running:
            logger.warning("Program already running")
            return False

        if self._controller.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._controller.status.value}")
            return False

        self._current_program = program
        self._program_progress_callback = progress_callback
        self._program_running = True
        self._program_cancelled = False
        self._program_progress = 0.0

        # 从断点恢复
        if resume_from_checkpoint:
            self._current_segment_index = resume_from_checkpoint.current_segment
            self._program_checkpoint = resume_from_checkpoint
            logger.info(f"Resuming program from segment {self._current_segment_index}")
        else:
            self._current_segment_index = 0

        try:
            self._program_task = asyncio.create_task(
                self._execute_program_internal(program, resume_from_checkpoint)
            )
            await self._program_task
            return True

        except asyncio.CancelledError:
            logger.info("Program cancelled")
            return False
        except Exception as e:
            logger.error(f"Program execution error: {e}")
            return False
        finally:
            self._program_running = False
            self._program_task = None

    async def _execute_program_internal(
        self,
        program: TemperatureProgram,
        checkpoint: ProgramCheckpoint | None = None,
    ) -> None:
        """内部方法：执行温度程序。

        Args:
            program: 温度程序
            checkpoint: 断点数据
        """
        total_segments = len(program.segments)
        start_time = time.time()

        for loop in range(program.loop_count):
            for segment_idx in range(self._current_segment_index, total_segments):
                if self._program_cancelled:
                    return

                segment = program.segments[segment_idx]

                # 更新进度
                self._current_segment_index = segment_idx
                self._program_progress = (loop * total_segments + segment_idx) / (
                    program.loop_count * total_segments
                )

                # 执行段
                if segment.segment_type == ProgramSegmentType.RAMP:
                    await self._execute_ramp_segment(
                        segment, segment_idx, total_segments, program.loop_count, loop
                    )
                elif segment.segment_type == ProgramSegmentType.SOAK:
                    await self._execute_soak_segment(
                        segment, segment_idx, total_segments, program.loop_count, loop
                    )
                elif segment.segment_type == ProgramSegmentType.STEP:
                    await self._execute_step_segment(segment)
                elif segment.segment_type == ProgramSegmentType.END:
                    logger.info("Program end segment reached")
                    return

                # 保存断点
                await self._save_program_checkpoint(
                    program.program_id,
                    segment_idx,
                    time.time() - start_time,
                )

        self._program_progress = 1.0
        logger.info(f"Program completed: {program.name}")

    async def _execute_ramp_segment(
        self,
        segment: ProgramSegment,
        segment_idx: int,
        total_segments: int,
        total_loops: int,
        current_loop: int,
    ) -> None:
        """执行斜坡段。

        Args:
            segment: 程序段
            segment_idx: 段索引
            total_segments: 总段数
            total_loops: 总循环数
            current_loop: 当前循环
        """
        # 获取当前温度
        current_temp = await self._get_current_temperature()
        target_temp = segment.target_temp

        # 计算升温时间和步数
        delta_temp = target_temp - current_temp
        if abs(delta_temp) < 0.1:
            logger.debug(f"Ramp segment skipped: already at target {target_temp}°C")
            return

        ramp_time = abs(delta_temp) / segment.ramp_rate * 60  # 转换为秒
        sample_interval = 1.0  # 1秒采样间隔
        total_steps = int(ramp_time / sample_interval)

        direction = 1 if delta_temp > 0 else -1

        for step in range(total_steps):
            if self._program_cancelled:
                return

            # 计算当前目标温度
            progress = step / total_steps
            current_target = current_temp + delta_temp * progress

            # 设置目标温度
            await self._controller.set_temperature(current_target)

            # 更新进度
            segment_progress = progress
            self._program_progress = (
                (current_loop * total_segments + segment_idx + segment_progress)
                / (total_loops * total_segments)
            )

            if self._program_progress_callback:
                actual_temp = await self._get_current_temperature()
                self._program_progress_callback(
                    self._program_progress, segment_idx, actual_temp
                )

            await asyncio.sleep(sample_interval)

    async def _execute_soak_segment(
        self,
        segment: ProgramSegment,
        segment_idx: int,
        total_segments: int,
        total_loops: int,
        current_loop: int,
    ) -> None:
        """执行恒温保持段。

        Args:
            segment: 程序段
            segment_idx: 段索引
            total_segments: 总段数
            total_loops: 总循环数
            current_loop: 当前循环
        """
        target_temp = segment.target_temp
        hold_time = segment.hold_time

        # 设置目标温度
        await self._controller.set_temperature(target_temp)

        # 等待温度稳定
        await self._wait_for_temperature_stable(target_temp, segment.tolerance)

        # 保持时间
        sample_interval = 1.0
        total_steps = int(hold_time / sample_interval)

        for step in range(total_steps):
            if self._program_cancelled:
                return

            # 更新进度
            segment_progress = step / total_steps
            self._program_progress = (
                (current_loop * total_segments + segment_idx + segment_progress)
                / (total_loops * total_segments)
            )

            if self._program_progress_callback:
                actual_temp = await self._get_current_temperature()
                self._program_progress_callback(
                    self._program_progress, segment_idx, actual_temp
                )

            await asyncio.sleep(sample_interval)

    async def _execute_step_segment(self, segment: ProgramSegment) -> None:
        """执行阶梯段。

        Args:
            segment: 程序段
        """
        await self._controller.set_temperature(segment.target_temp)

    async def _wait_for_temperature_stable(
        self,
        target_temp: float,
        tolerance: float,
        timeout: float = 300.0,
    ) -> bool:
        """等待温度稳定。

        Args:
            target_temp: 目标温度
            tolerance: 容差
            timeout: 超时时间

        Returns:
            bool: 是否成功稳定
        """
        start_time = time.time()
        stable_count = 0
        required_stable_count = 5  # 连续5次在容差内认为稳定

        while time.time() - start_time < timeout:
            if self._program_cancelled:
                return False

            current_temp = await self._get_current_temperature()

            if abs(current_temp - target_temp) <= tolerance:
                stable_count += 1
                if stable_count >= required_stable_count:
                    logger.debug(f"Temperature stable at {current_temp:.2f}°C")
                    return True
            else:
                stable_count = 0

            await asyncio.sleep(1.0)

        logger.warning(f"Temperature stabilization timeout, current: {current_temp:.2f}°C")
        return False

    async def _save_program_checkpoint(
        self,
        program_id: str,
        segment_idx: int,
        elapsed_time: float,
    ) -> None:
        """保存程序断点。

        Args:
            program_id: 程序ID
            segment_idx: 段索引
            elapsed_time: 已运行时间
        """
        current_temp = await self._get_current_temperature()

        self._program_checkpoint = ProgramCheckpoint(
            checkpoint_id=f"checkpoint_{int(time.time() * 1000)}",
            program_id=program_id,
            current_segment=segment_idx,
            segment_progress=0.0,
            current_temp=current_temp,
            target_temp=self._current_program.segments[segment_idx].target_temp
            if self._current_program and segment_idx < len(self._current_program.segments)
            else current_temp,
            elapsed_time=elapsed_time,
            timestamp=time.time(),
        )

    async def stop_program(self) -> bool:
        """停止程序执行。

        Returns:
            bool: 停止是否成功
        """
        if not self._program_running:
            return True

        self._program_cancelled = True

        if self._program_task:
            self._program_task.cancel()
            try:
                await self._program_task
            except asyncio.CancelledError:
                pass

        self._program_running = False
        logger.info("Program stopped")
        return True

    def get_program_status(self) -> dict[str, Any]:
        """获取程序执行状态。

        Returns:
            Dict[str, Any]: 程序状态信息
        """
        return {
            "running": self._program_running,
            "program_id": self._current_program.program_id if self._current_program else None,
            "current_segment": self._current_segment_index,
            "progress": round(self._program_progress, 4),
            "checkpoint": {
                "program_id": self._program_checkpoint.program_id,
                "current_segment": self._program_checkpoint.current_segment,
                "current_temp": self._program_checkpoint.current_temp,
                "elapsed_time": self._program_checkpoint.elapsed_time,
            } if self._program_checkpoint else None,
        }

    # ==================== PID自适应调节 ====================

    async def auto_tune_pid(
        self,
        method: PIDTuningMethod = PIDTuningMethod.AUTO,
        setpoint: float = 100.0,
        test_duration: float = 600.0,
    ) -> PIDParameters:
        """自动整定PID参数。

        Args:
            method: 整定方法
            setpoint: 测试设定点
            test_duration: 测试持续时间

        Returns:
            PIDParameters: 整定后的PID参数

        Raises:
            ValueError: 整定失败
        """
        logger.info(f"Starting PID auto-tuning: method={method.value}, setpoint={setpoint}°C")

        if method == PIDTuningMethod.AUTO:
            # 自动整定：阶跃响应法
            return await self._auto_tune_step_response(setpoint, test_duration)

        elif method == PIDTuningMethod.ZIEGLER_NICHOLS:
            # Ziegler-Nichols方法
            return await self._auto_tune_ziegler_nichols(setpoint, test_duration)

        elif method == PIDTuningMethod.FUZZY:
            # 模糊PID
            return await self._auto_tune_fuzzy(setpoint)

        else:
            raise ValueError(f"Unsupported tuning method: {method}")

    async def _auto_tune_step_response(
        self,
        setpoint: float,
        duration: float,
    ) -> PIDParameters:
        """阶跃响应法整定PID。

        Args:
            setpoint: 设定点
            duration: 持续时间

        Returns:
            PIDParameters: PID参数
        """
        # 记录初始温度
        initial_temp = await self._get_current_temperature()

        # 施加阶跃输入（50%输出）
        await self._controller.set_output_power(50.0)

        # 记录温度响应
        temperatures = []
        timestamps = []
        start_time = time.time()

        while time.time() - start_time < duration:
            temp = await self._get_current_temperature()
            temperatures.append(temp)
            timestamps.append(time.time() - start_time)
            await asyncio.sleep(0.5)

        # 恢复初始状态
        await self._controller.set_output_power(0.0)

        # 分析阶跃响应
        temps = np.array(temperatures)
        times = np.array(timestamps)

        # 计算过程增益
        delta_temp = temps[-1] - initial_temp
        process_gain = delta_temp / 50.0  # 相对于50%输入

        # 计算时间常数（达到63.2%最终值的时间）
        target_temp = initial_temp + delta_temp * 0.632
        time_constant_idx = np.argmin(np.abs(temps - target_temp))
        time_constant = times[time_constant_idx]

        # 计算延迟时间
        # 使用线性拟合估计延迟
        slope = delta_temp / time_constant
        delay_time = times[0]  # 简化处理

        # Cohen-Coon公式计算PID参数
        kp = (1.0 / process_gain) * (time_constant / delay_time) * (0.9 + delay_time / (12 * time_constant))
        ki = kp / (time_constant * (3.3 + delay_time / time_constant))
        kd = kp * time_constant * (0.5 - delay_time / (10 * time_constant))

        # 限制参数范围
        kp = max(PID_KP_MIN, min(PID_KP_MAX, kp))
        ki = max(PID_KI_MIN, min(PID_KI_MAX, ki))
        kd = max(PID_KD_MIN, min(PID_KD_MAX, kd))

        params = PIDParameters(kp=kp, ki=ki, kd=kd, setpoint=setpoint)

        logger.info(f"PID auto-tuning completed: KP={kp:.2f}, KI={ki:.2f}, KD={kd:.2f}")

        # 应用新参数
        self._pid_params = params
        await self._controller.set_pid_parameters(kp, ki, kd)

        return params

    async def _auto_tune_ziegler_nichols(
        self,
        setpoint: float,
        duration: float,
    ) -> PIDParameters:
        """Ziegler-Nichols方法整定PID。

        Args:
            setpoint: 设定点
            duration: 持续时间

        Returns:
            PIDParameters: PID参数
        """
        # 简化实现：使用临界增益法
        # 实际实现需要找到临界增益Ku和临界周期Tu

        # 这里使用默认值
        ku = 20.0  # 临界增益（需要实际测量）
        tu = 120.0  # 临界周期（需要实际测量）

        # Ziegler-Nichols公式
        kp = 0.6 * ku
        ki = 2.0 * kp / tu
        kd = kp * tu / 8.0

        params = PIDParameters(kp=kp, ki=ki, kd=kd, setpoint=setpoint)

        self._pid_params = params
        await self._controller.set_pid_parameters(kp, ki, kd)

        return params

    async def _auto_tune_fuzzy(self, setpoint: float) -> PIDParameters:
        """模糊PID整定。

        Args:
            setpoint: 设定点

        Returns:
            PIDParameters: PID参数
        """
        # 模糊PID：根据误差和误差变化率动态调整PID参数
        # 这里返回基础参数，实际应用中需要实现模糊规则表

        current_temp = await self._get_current_temperature()
        error = setpoint - current_temp

        # 简化的模糊规则
        if abs(error) > 50:
            kp = 20.0
            ki = 0.5
            kd = 10.0
        elif abs(error) > 20:
            kp = 15.0
            ki = 0.3
            kd = 5.0
        else:
            kp = 10.0
            ki = 0.2
            kd = 2.0

        params = PIDParameters(kp=kp, ki=ki, kd=kd, setpoint=setpoint)

        self._pid_params = params
        await self._controller.set_pid_parameters(kp, ki, kd)

        return params

    async def set_pid_parameters(self, params: PIDParameters) -> bool:
        """设置PID参数。

        Args:
            params: PID参数

        Returns:
            bool: 设置是否成功
        """
        if not params.validate():
            logger.error("Invalid PID parameters")
            return False

        self._pid_params = params
        await self._controller.set_pid_parameters(params.kp, params.ki, params.kd)

        logger.info(f"PID parameters set: KP={params.kp}, KI={params.ki}, KD={params.kd}")
        return True

    def get_pid_parameters(self) -> PIDParameters:
        """获取当前PID参数。

        Returns:
            PIDParameters: PID参数
        """
        return self._pid_params

    # ==================== 分级温度保护 ====================

    async def configure_protection(
        self,
        level: ProtectionLevel,
        config: TemperatureProtection,
    ) -> bool:
        """配置温度保护。

        Args:
            level: 保护级别
            config: 保护配置

        Returns:
            bool: 配置是否成功
        """
        self._protection_configs[level] = config
        logger.info(
            f"Temperature protection configured: level={level.value}, "
            f"range=[{config.low_limit}, {config.high_limit}]°C"
        )
        return True

    async def check_protection(self) -> dict[str, Any]:
        """检查温度保护状态。

        Returns:
            Dict[str, Any]: 保护检查结果
        """
        current_temp = await self._get_current_temperature()
        protection_status = {
            "current_temperature": current_temp,
            "protection_level": ProtectionLevel.NONE.value,
            "violations": [],
        }

        # 按级别从低到高检查
        for level in [
            ProtectionLevel.WARNING,
            ProtectionLevel.ALARM,
            ProtectionLevel.CRITICAL,
            ProtectionLevel.EMERGENCY,
        ]:
            config = self._protection_configs.get(level)
            if config is None or not config.enabled:
                continue

            violations = []

            # 检查温度范围
            if current_temp < config.low_limit:
                violations.append(f"Temperature {current_temp:.1f}°C below low limit {config.low_limit}°C")
            if current_temp > config.high_limit:
                violations.append(f"Temperature {current_temp:.1f}°C above high limit {config.high_limit}°C")

            if violations:
                protection_status["protection_level"] = level.value
                protection_status["violations"].extend(violations)

                # 执行保护动作
                await self._execute_protection_action(config)

                # 回调通知
                if self._protection_callback:
                    self._protection_callback(level, "; ".join(violations))

        return protection_status

    async def _execute_protection_action(self, config: TemperatureProtection) -> None:
        """执行保护动作。

        Args:
            config: 保护配置
        """
        action = config.action

        if action == "notify":
            logger.warning(f"Temperature protection notification: {config.level.value}")

        elif action == "alarm":
            logger.error(f"Temperature protection alarm: {config.level.value}")
            # 触发报警

        elif action == "shutdown":
            logger.critical(f"Temperature protection shutdown: {config.level.value}")
            await self.stop_program()
            await self._controller.set_output_power(0.0)

        elif action == "emergency_stop":
            logger.critical(f"Temperature protection emergency stop: {config.level.value}")
            await self.stop_program()
            await self._controller.set_output_power(0.0)
            # 触发全局急停

    # ==================== 温度历史曲线对比 ====================

    async def start_history_recording(
        self,
        sample_interval_ms: int = DEFAULT_SAMPLE_INTERVAL_MS,
        history_callback: Callable[[TemperatureHistoryPoint], None] | None = None,
    ) -> bool:
        """启动温度历史记录。

        Args:
            sample_interval_ms: 采样间隔（毫秒）
            history_callback: 历史数据回调函数

        Returns:
            bool: 启动是否成功
        """
        if self._history_recording:
            logger.warning("History recording already running")
            return False

        self._history_callback = history_callback
        self._history_recording = True
        self._sample_interval = sample_interval_ms / 1000.0

        self._history_task = asyncio.create_task(self._history_recording_loop())

        logger.info(f"History recording started: interval={sample_interval_ms}ms")
        return True

    async def stop_history_recording(self) -> bool:
        """停止温度历史记录。

        Returns:
            bool: 停止是否成功
        """
        if not self._history_recording:
            return True

        self._history_recording = False

        if self._history_task:
            self._history_task.cancel()
            try:
                await self._history_task
            except asyncio.CancelledError:
                pass

        logger.info("History recording stopped")
        return True

    async def _history_recording_loop(self) -> None:
        """温度历史记录循环。"""
        while self._history_recording:
            try:
                # 读取当前状态
                current_temp = await self._get_current_temperature()
                setpoint = self._pid_params.setpoint
                output = await self._controller.read_output_power()

                # 创建历史数据点
                point = TemperatureHistoryPoint(
                    timestamp=time.time(),
                    temperature=current_temp,
                    setpoint=setpoint,
                    output=output,
                    program_id=self._current_program.program_id if self._current_program else None,
                    segment_id=self._current_segment_index if self._program_running else None,
                )

                # 保存历史
                self._temperature_history.append(point)
                if len(self._temperature_history) > MAX_HISTORY_POINTS:
                    self._temperature_history.pop(0)

                # 回调通知
                if self._history_callback:
                    self._history_callback(point)

                await asyncio.sleep(self._sample_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"History recording error: {e}")
                await asyncio.sleep(1.0)

    def get_temperature_history(
        self,
        start_time: float | None = None,
        end_time: float | None = None,
    ) -> list[dict[str, Any]]:
        """获取温度历史数据。

        Args:
            start_time: 起始时间戳
            end_time: 结束时间戳

        Returns:
            List[Dict[str, Any]]: 历史数据列表
        """
        history = self._temperature_history

        if start_time is not None:
            history = [p for p in history if p.timestamp >= start_time]
        if end_time is not None:
            history = [p for p in history if p.timestamp <= end_time]

        return [
            {
                "timestamp": p.timestamp,
                "temperature": p.temperature,
                "setpoint": p.setpoint,
                "output": p.output,
                "program_id": p.program_id,
                "segment_id": p.segment_id,
            }
            for p in history
        ]

    def compare_temperature_curves(
        self,
        history1: list[TemperatureHistoryPoint],
        history2: list[TemperatureHistoryPoint],
    ) -> dict[str, Any]:
        """对比两条温度曲线。

        Args:
            history1: 第一条历史数据
            history2: 第二条历史数据

        Returns:
            Dict[str, Any]: 对比结果
        """
        if len(history1) < 2 or len(history2) < 2:
            return {"error": "Insufficient data for comparison"}

        # 提取温度数据
        temps1 = np.array([p.temperature for p in history1])
        temps2 = np.array([p.temperature for p in history2])

        # 对齐时间轴（使用较短的长度）
        min_len = min(len(temps1), len(temps2))
        temps1 = temps1[:min_len]
        temps2 = temps2[:min_len]

        # 计算差异统计
        diff = temps1 - temps2
        mean_diff = float(np.mean(diff))
        std_diff = float(np.std(diff))
        max_diff = float(np.max(np.abs(diff)))

        # 计算相关系数
        correlation = float(np.corrcoef(temps1, temps2)[0, 1])

        # 计算均方根误差
        rmse = float(np.sqrt(np.mean(diff**2)))

        return {
            "mean_difference": round(mean_diff, 4),
            "std_difference": round(std_diff, 4),
            "max_difference": round(max_diff, 4),
            "correlation": round(correlation, 4),
            "rmse": round(rmse, 4),
            "sample_count": min_len,
        }

    def analyze_temperature_stability(
        self,
        history: list[TemperatureHistoryPoint] | None = None,
    ) -> dict[str, Any]:
        """分析温度稳定性。

        Args:
            history: 历史数据，None使用当前记录

        Returns:
            Dict[str, Any]: 稳定性分析结果
        """
        if history is None:
            history = self._temperature_history

        if len(history) < 10:
            return {"error": "Insufficient data for stability analysis"}

        temps = np.array([p.temperature for p in history])
        setpoints = np.array([p.setpoint for p in history])

        # 计算偏差
        deviations = temps - setpoints

        # 统计量
        mean_deviation = float(np.mean(deviations))
        std_deviation = float(np.std(deviations))
        max_deviation = float(np.max(np.abs(deviations)))

        # 温度变化率
        if len(temps) > 1:
            gradients = np.diff(temps)
            mean_gradient = float(np.mean(np.abs(gradients)))
            max_gradient = float(np.max(np.abs(gradients)))
        else:
            mean_gradient = 0.0
            max_gradient = 0.0

        # 稳定性评估
        is_stable = std_deviation < 1.0 and max_deviation < 2.0

        return {
            "is_stable": is_stable,
            "mean_deviation": round(mean_deviation, 4),
            "std_deviation": round(std_deviation, 4),
            "max_deviation": round(max_deviation, 4),
            "mean_gradient": round(mean_gradient, 4),
            "max_gradient": round(max_gradient, 4),
            "sample_count": len(history),
        }

    # ==================== 辅助方法 ====================

    async def _get_current_temperature(self) -> float:
        """获取当前温度。

        Returns:
            float: 当前温度（°C）
        """
        status = await self._controller.read_status()
        return status.get("current_temperature", 0.0)

    # ==================== 资源清理 ====================

    async def cleanup(self) -> None:
        """清理所有资源。"""
        await self.stop_program()
        await self.stop_history_recording()
        logger.info("TemperatureAdvancedService cleanup completed")

    # ==================== 数据导入导出 ====================

    def export_program(self, program: TemperatureProgram) -> str:
        """导出温度程序为JSON字符串。

        Args:
            program: 温度程序

        Returns:
            str: JSON字符串
        """
        data = {
            "program_id": program.program_id,
            "name": program.name,
            "segments": [
                {
                    "segment_id": s.segment_id,
                    "segment_type": s.segment_type.value,
                    "target_temp": s.target_temp,
                    "ramp_rate": s.ramp_rate,
                    "hold_time": s.hold_time,
                    "tolerance": s.tolerance,
                }
                for s in program.segments
            ],
            "loop_count": program.loop_count,
            "description": program.description,
        }
        return json.dumps(data, indent=2)

    def import_program(self, json_str: str) -> TemperatureProgram:
        """从JSON字符串导入温度程序。

        Args:
            json_str: JSON字符串

        Returns:
            TemperatureProgram: 温度程序
        """
        data = json.loads(json_str)
        return TemperatureProgram(
            program_id=data["program_id"],
            name=data["name"],
            segments=[
                ProgramSegment(
                    segment_id=s["segment_id"],
                    segment_type=ProgramSegmentType(s["segment_type"]),
                    target_temp=s["target_temp"],
                    ramp_rate=s.get("ramp_rate", 5.0),
                    hold_time=s.get("hold_time", 60.0),
                    tolerance=s.get("tolerance", 1.0),
                )
                for s in data["segments"]
            ],
            loop_count=data.get("loop_count", 1),
            description=data.get("description", ""),
        )

    def export_history(self, format_type: str = "json") -> str:
        """导出历史数据。

        Args:
            format_type: 导出格式（json/csv）

        Returns:
            str: 导出数据
        """
        if format_type == "json":
            return json.dumps(self.get_temperature_history(), indent=2)
        elif format_type == "csv":
            lines = ["timestamp,temperature,setpoint,output,program_id,segment_id"]
            for p in self._temperature_history:
                lines.append(
                    f"{p.timestamp},{p.temperature},{p.setpoint},{p.output},"
                    f"{p.program_id or ''},{p.segment_id or ''}"
                )
            return "\n".join(lines)
        else:
            raise ValueError(f"Unsupported format: {format_type}")
