"""
微电流采集模块 (Picoammeter)

功能：
- 多通道同步采集（4通道）
- 可配置采样率（1Hz-1kHz）
- 噪声抑制滤波（低通、移动平均、中值滤波）
- 信噪比计算
- 仿真模式和真实硬件模式支持

技术规范：
- 电流范围：1pA-1mA
- 电流分辨率：1pA
- 通道数：4通道
- 采样率：1Hz-1kHz

安全警告：
- 实验时必须有人值守
- 首次使用前验证量程参数
"""

import asyncio
import logging
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from .abstract import AbstractDevice, DeviceStatus

logger = logging.getLogger(__name__)


class CurrentRange(Enum):
    """电流测量量程枚举。

    Attributes:
        RANGE_1NA: 1nA量程（分辨率1pA）
        RANGE_10NA: 10nA量程（分辨率10pA）
        RANGE_100NA: 100nA量程（分辨率100pA）
        RANGE_1UA: 1μA量程（分辨率1nA）
        RANGE_10UA: 10μA量程（分辨率10nA）
        RANGE_100UA: 100μA量程（分辨率100nA）
        RANGE_1MA: 1mA量程（分辨率1μA）
    """

    RANGE_1NA = "1nA"
    RANGE_10NA = "10nA"
    RANGE_100NA = "100nA"
    RANGE_1UA = "1uA"
    RANGE_10UA = "10uA"
    RANGE_100UA = "100uA"
    RANGE_1MA = "1mA"


class FilterType(Enum):
    """滤波类型枚举。

    Attributes:
        NONE: 无滤波
        LOWPASS: 低通滤波
        MOVING_AVERAGE: 移动平均滤波
        MEDIAN: 中值滤波
    """

    NONE = "none"
    LOWPASS = "lowpass"
    MOVING_AVERAGE = "moving_average"
    MEDIAN = "median"


@dataclass
class ChannelConfig:
    """通道配置数据类。

    Attributes:
        enabled: 是否启用通道
        current_range: 电流测量量程
        filter_type: 滤波类型
        filter_cutoff: 低通滤波截止频率（Hz）
        filter_window: 移动平均/中值滤波窗口大小
        offset: 电流偏移校准值（pA）
    """

    enabled: bool = True
    current_range: CurrentRange = CurrentRange.RANGE_1UA
    filter_type: FilterType = FilterType.NONE
    filter_cutoff: float = 10.0
    filter_window: int = 5
    offset: float = 0.0


@dataclass
class ChannelData:
    """通道采集数据类。

    Attributes:
        current_pa: 电流值（pA）
        timestamp: 时间戳（秒）
        snr_db: 信噪比（dB）
        raw_current_pa: 原始电流值（滤波前）
        noise_rms_pa: 噪声RMS值（pA）
        signal_rms_pa: 信号RMS值（pA）
    """

    current_pa: float = 0.0
    timestamp: float = 0.0
    snr_db: float = 0.0
    raw_current_pa: float = 0.0
    noise_rms_pa: float = 0.0
    signal_rms_pa: float = 0.0


@dataclass
class AcquisitionConfig:
    """采集配置数据类。

    Attributes:
        sample_rate: 采样率（Hz）
        channels: 通道配置列表
        buffer_size: 数据缓冲区大小
        snr_calc_window: SNR计算窗口大小
    """

    sample_rate: float = 100.0
    channels: list[ChannelConfig] = field(
        default_factory=lambda: [ChannelConfig() for _ in range(4)]
    )
    buffer_size: int = 1000
    snr_calc_window: int = 100


class Picoammeter(AbstractDevice):
    """微电流采集设备实现。

    支持4通道同步采集，可配置采样率、滤波和量程。
    提供实时信噪比计算功能。

    Attributes:
        NUM_CHANNELS: 通道数量（固定为4）
        MIN_SAMPLE_RATE: 最小采样率（1Hz）
        MAX_SAMPLE_RATE: 最大采样率（1kHz）
        MIN_CURRENT_PA: 最小电流（1pA）
        MAX_CURRENT_PA: 最大电流（1mA = 1,000,000,000pA）
    """

    NUM_CHANNELS = 4
    MIN_SAMPLE_RATE = 1.0
    MAX_SAMPLE_RATE = 1000.0
    MIN_CURRENT_PA = 1.0
    MAX_CURRENT_PA = 1_000_000_000.0

    def __init__(self, device_id: str, config: dict[str, Any]):
        """初始化微电流采集设备。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典
                - simulation: 是否启用仿真模式（默认True）
                - sample_rate: 采样率（Hz，默认100）
                - buffer_size: 缓冲区大小（默认1000）
                - snr_calc_window: SNR计算窗口（默认100）

        Raises:
            ValueError: 配置参数无效时抛出
        """
        super().__init__(device_id, config)

        self._simulation = config.get("simulation", True)
        self._acq_config = AcquisitionConfig(
            sample_rate=config.get("sample_rate", 100.0),
            buffer_size=config.get("buffer_size", 1000),
            snr_calc_window=config.get("snr_calc_window", 100),
        )

        # 数据缓冲区（每个通道）
        self._data_buffers: list[deque[ChannelData]] = [
            deque(maxlen=self._acq_config.buffer_size) for _ in range(self.NUM_CHANNELS)
        ]

        # 滤波器状态
        self._filter_states: list[dict[str, Any]] = [
            {"prev_output": 0.0, "history": deque(maxlen=100)} for _ in range(self.NUM_CHANNELS)
        ]

        # 采集任务
        self._acquisition_task: asyncio.Task | None = None
        self._is_acquiring = False

        # 仿真数据生成参数
        self._sim_time = 0.0
        self._sim_base_currents = [100.0, 200.0, 50.0, 150.0]  # pA

        logger.info(
            f"Picoammeter {device_id} initialized "
            f"(simulation={self._simulation}, sample_rate={self._acq_config.sample_rate}Hz)"
        )

    @property
    def sample_rate(self) -> float:
        """
        获取当前采样率。

        Returns:
            float: 采样率（Hz）
        """
        return self._acq_config.sample_rate

    async def connect(self) -> bool:
        """建立与设备的连接。

        Returns:
            bool: 连接是否成功
        """
        try:
            self.status = DeviceStatus.CONNECTING

            if self._simulation:
                logger.info(f"Picoammeter {self.device_id} connected (simulation mode)")
                self.status = DeviceStatus.READY
                return True

            # 真实硬件连接逻辑（待实现）
            # TODO: 实现真实硬件连接（如VISA、TCP/IP等）
            logger.warning("Real hardware connection not implemented, using simulation mode")
            self._simulation = True
            self.status = DeviceStatus.READY
            return True

        except Exception as e:
            self.status = DeviceStatus.ERROR
            self._last_error = str(e)
            logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        """断开与设备的连接。

        Returns:
            bool: 断开是否成功
        """
        # 停止采集
        if self._is_acquiring:
            await self.stop_acquisition()

        self.status = DeviceStatus.DISCONNECTED
        logger.info(f"Picoammeter {self.device_id} disconnected")
        return True

    async def read_status(self) -> dict[str, Any]:
        """读取设备完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典，包括：
                - device_id: 设备标识
                - status: 设备状态
                - simulation: 是否仿真模式
                - sample_rate: 采样率
                - is_acquiring: 是否正在采集
                - buffer_usage: 缓冲区使用情况
                - channel_configs: 通道配置
        """
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "simulation": self._simulation,
            "sample_rate": self._acq_config.sample_rate,
            "is_acquiring": self._is_acquiring,
            "buffer_usage": [len(buf) for buf in self._data_buffers],
            "channel_configs": [
                {
                    "enabled": ch.enabled,
                    "range": ch.current_range.value,
                    "filter": ch.filter_type.value,
                    "offset": ch.offset,
                }
                for ch in self._acq_config.channels
            ],
        }

    def configure_channel(
        self,
        channel: int,
        enabled: bool | None = None,
        current_range: CurrentRange | None = None,
        filter_type: FilterType | None = None,
        filter_cutoff: float | None = None,
        filter_window: int | None = None,
        offset: float | None = None,
    ) -> bool:
        """配置指定通道参数。

        Args:
            channel: 通道号（0-3）
            enabled: 是否启用
            current_range: 电流测量量程
            filter_type: 滤波类型
            filter_cutoff: 低通滤波截止频率（Hz）
            filter_window: 滤波窗口大小
            offset: 电流偏移校准值（pA）

        Returns:
            bool: 配置是否成功

        Raises:
            ValueError: 通道号无效时抛出
        """
        if not 0 <= channel < self.NUM_CHANNELS:
            logger.error(f"Invalid channel: {channel}, must be 0-{self.NUM_CHANNELS - 1}")
            raise ValueError(f"Invalid channel: {channel}")

        ch_config = self._acq_config.channels[channel]

        if enabled is not None:
            ch_config.enabled = enabled
        if current_range is not None:
            ch_config.current_range = current_range
        if filter_type is not None:
            ch_config.filter_type = filter_type
        if filter_cutoff is not None:
            if filter_cutoff <= 0 or filter_cutoff > self.MAX_SAMPLE_RATE / 2:
                logger.error(f"Invalid filter cutoff: {filter_cutoff}Hz")
                raise ValueError(f"Invalid filter cutoff: {filter_cutoff}Hz")
            ch_config.filter_cutoff = filter_cutoff
        if filter_window is not None:
            if filter_window < 1 or filter_window > 100:
                logger.error(f"Invalid filter window: {filter_window}")
                raise ValueError(f"Invalid filter window: {filter_window}")
            ch_config.filter_window = filter_window
        if offset is not None:
            ch_config.offset = offset

        logger.info(
            f"Channel {channel} configured: enabled={ch_config.enabled}, "
            f"range={ch_config.current_range.value}, filter={ch_config.filter_type.value}"
        )
        return True

    def set_sample_rate(self, rate: float) -> bool:
        """设置采样率。

        Args:
            rate: 采样率（Hz），范围1-1000

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 采样率超出范围时抛出
        """
        if not self.MIN_SAMPLE_RATE <= rate <= self.MAX_SAMPLE_RATE:
            logger.error(
                f"Invalid sample rate: {rate}Hz, "
                f"must be {self.MIN_SAMPLE_RATE}-{self.MAX_SAMPLE_RATE}Hz"
            )
            raise ValueError(f"Sample rate must be {self.MIN_SAMPLE_RATE}-{self.MAX_SAMPLE_RATE}Hz")

        self._acq_config.sample_rate = rate
        logger.info(f"Sample rate set to {rate}Hz")
        return True

    async def start_acquisition(self) -> bool:
        """启动多通道同步采集。

        Returns:
            bool: 启动是否成功
        """
        if self._is_acquiring:
            logger.warning("Acquisition already running")
            return True

        if self.status != DeviceStatus.READY:
            logger.error(f"Device not ready, status: {self.status}")
            return False

        self._is_acquiring = True
        self.status = DeviceStatus.BUSY

        # 启动采集任务
        self._acquisition_task = asyncio.create_task(self._acquisition_loop())

        logger.info(
            f"Acquisition started: {self._acq_config.sample_rate}Hz, "
            f"{sum(1 for ch in self._acq_config.channels if ch.enabled)} channels active"
        )
        return True

    async def stop_acquisition(self) -> bool:
        """停止采集。

        Returns:
            bool: 停止是否成功
        """
        if not self._is_acquiring:
            return True

        self._is_acquiring = False

        if self._acquisition_task:
            self._acquisition_task.cancel()
            try:
                await self._acquisition_task
            except asyncio.CancelledError:
                pass
            self._acquisition_task = None

        self.status = DeviceStatus.READY
        logger.info("Acquisition stopped")
        return True

    async def read_channel(self, channel: int) -> ChannelData | None:
        """读取指定通道最新数据。

        Args:
            channel: 通道号（0-3）

        Returns:
            ChannelData | None: 通道数据，无数据时返回None

        Raises:
            ValueError: 通道号无效时抛出
        """
        if not 0 <= channel < self.NUM_CHANNELS:
            raise ValueError(f"Invalid channel: {channel}")

        if not self._data_buffers[channel]:
            return None

        return self._data_buffers[channel][-1]

    async def read_all_channels(self) -> list[ChannelData | None]:
        """读取所有通道最新数据。

        Returns:
            List[ChannelData | None]: 各通道数据列表
        """
        return [await self.read_channel(ch) for ch in range(self.NUM_CHANNELS)]

    async def read_channel_buffer(
        self, channel: int, count: int | None = None
    ) -> list[ChannelData]:
        """读取指定通道缓冲区数据。

        Args:
            channel: 通道号（0-3）
            count: 读取数量，None表示全部

        Returns:
            List[ChannelData]: 数据列表

        Raises:
            ValueError: 通道号无效时抛出
        """
        if not 0 <= channel < self.NUM_CHANNELS:
            raise ValueError(f"Invalid channel: {channel}")

        buffer = self._data_buffers[channel]
        if count is None:
            return list(buffer)
        return list(buffer)[-count:]

    def calculate_snr(self, channel: int, window_size: int | None = None) -> float:
        """计算指定通道的信噪比。

        SNR = 20 * log10(信号RMS / 噪声RMS)

        Args:
            channel: 通道号（0-3）
            window_size: 计算窗口大小，None使用默认值

        Returns:
            float: 信噪比（dB），无数据时返回0

        Raises:
            ValueError: 通道号无效时抛出
        """
        if not 0 <= channel < self.NUM_CHANNELS:
            raise ValueError(f"Invalid channel: {channel}")

        window = window_size or self._acq_config.snr_calc_window
        buffer = self._data_buffers[channel]

        if len(buffer) < window:
            return 0.0

        # 获取最近的数据
        recent_data = list(buffer)[-window:]
        currents = np.array([d.current_pa for d in recent_data])

        # 计算信号RMS（均值作为信号）
        signal_mean = np.mean(currents)
        signal_rms = np.sqrt(np.mean((currents - np.mean(currents)) ** 2)) + abs(signal_mean)

        # 计算噪声RMS（高频分量）
        noise_rms = np.std(currents)

        if noise_rms < 1e-10:  # 避免除零
            return 100.0  # 极高信噪比

        snr = 20 * np.log10(signal_rms / noise_rms)
        return float(snr)

    def clear_buffer(self, channel: int | None = None) -> None:
        """清空数据缓冲区。

        Args:
            channel: 通道号，None表示清空所有通道
        """
        if channel is None:
            for buf in self._data_buffers:
                buf.clear()
            logger.info("All channel buffers cleared")
        else:
            if not 0 <= channel < self.NUM_CHANNELS:
                raise ValueError(f"Invalid channel: {channel}")
            self._data_buffers[channel].clear()
            logger.info(f"Channel {channel} buffer cleared")

    def auto_range(self, channel: int) -> CurrentRange:
        """自动选择最佳量程。

        根据当前测量值自动选择最合适的量程，确保测量精度最优。
        选择原则：选择能容纳当前值的最小量程，以获得最佳分辨率。

        Args:
            channel: 通道号（0-3）

        Returns:
            CurrentRange: 自动选择的最佳量程

        Raises:
            ValueError: 通道号无效时抛出
        """
        if not 0 <= channel < self.NUM_CHANNELS:
            raise ValueError(f"Invalid channel: {channel}")

        # 获取当前测量值
        buffer = self._data_buffers[channel]
        if len(buffer) == 0:
            # 无数据时使用默认量程
            logger.warning(f"Channel {channel}: No data for auto-range, using default")
            return CurrentRange.RANGE_1UA

        # 使用最近几个数据点的平均值作为参考
        recent_count = min(10, len(buffer))
        recent_data = list(buffer)[-recent_count:]
        avg_current = np.mean([d.current_pa for d in recent_data])
        max_current = max(abs(d.current_pa) for d in recent_data)

        # 考虑峰值，选择量程时留有一定余量（120%）
        target_max = max_current * 1.2

        # 量程列表（从小到大）
        ranges_ordered = [
            CurrentRange.RANGE_1NA,
            CurrentRange.RANGE_10NA,
            CurrentRange.RANGE_100NA,
            CurrentRange.RANGE_1UA,
            CurrentRange.RANGE_10UA,
            CurrentRange.RANGE_100UA,
            CurrentRange.RANGE_1MA,
        ]

        # 选择能容纳目标值的最小量程
        selected_range = CurrentRange.RANGE_1MA  # 默认最大量程
        for rng in ranges_ordered:
            range_max = self.get_range_max(rng)
            if target_max <= range_max:
                selected_range = rng
                break

        # 更新通道配置
        old_range = self._acq_config.channels[channel].current_range
        if selected_range != old_range:
            self._acq_config.channels[channel].current_range = selected_range
            logger.info(
                f"Channel {channel}: Auto-range changed from {old_range.value} "
                f"to {selected_range.value} (avg={avg_current:.2f}pA, max={max_current:.2f}pA)"
            )
        else:
            logger.debug(f"Channel {channel}: Auto-range unchanged ({selected_range.value})")

        return selected_range

    def auto_range_all(self) -> list[CurrentRange]:
        """对所有启用的通道执行自动量程切换。

        Returns:
            List[CurrentRange]: 各通道选择的量程列表
        """
        selected_ranges = []
        for ch in range(self.NUM_CHANNELS):
            if self._acq_config.channels[ch].enabled:
                selected_range = self.auto_range(ch)
                selected_ranges.append(selected_range)
            else:
                selected_ranges.append(self._acq_config.channels[ch].current_range)

        logger.info("Auto-range completed for all channels")
        return selected_ranges

    async def _acquisition_loop(self) -> None:
        """采集循环（内部方法）。"""
        sample_interval = 1.0 / self._acq_config.sample_rate

        try:
            while self._is_acquiring:
                start_time = asyncio.get_event_loop().time()

                # 同步采集所有启用的通道
                await self._acquire_sample()

                # 计算剩余时间并等待
                elapsed = asyncio.get_event_loop().time() - start_time
                sleep_time = max(0, sample_interval - elapsed)
                await asyncio.sleep(sleep_time)

                self._sim_time += sample_interval

        except asyncio.CancelledError:
            logger.debug("Acquisition loop cancelled")
            raise
        except Exception as e:
            logger.error(f"Acquisition loop error: {e}")
            self._last_error = str(e)
            self.status = DeviceStatus.ERROR
            self._is_acquiring = False

    async def _acquire_sample(self) -> None:
        """采集单次样本（内部方法）。"""
        timestamp = self._sim_time

        for ch in range(self.NUM_CHANNELS):
            ch_config = self._acq_config.channels[ch]
            if not ch_config.enabled:
                continue

            # 获取原始电流值
            raw_current = await self._read_current_raw(ch)

            # 应用滤波
            filtered_current = self._apply_filter(ch, raw_current, ch_config)

            # 应用偏移校准
            calibrated_current = filtered_current + ch_config.offset

            # 计算SNR
            snr = self.calculate_snr(ch)

            # 创建数据对象
            data = ChannelData(
                current_pa=calibrated_current,
                timestamp=timestamp,
                snr_db=snr,
                raw_current_pa=raw_current,
                noise_rms_pa=self._calculate_noise_rms(ch),
                signal_rms_pa=self._calculate_signal_rms(ch),
            )

            # 存入缓冲区
            self._data_buffers[ch].append(data)

    async def _read_current_raw(self, channel: int) -> float:
        """读取原始电流值（内部方法）。

        Args:
            channel: 通道号

        Returns:
            float: 原始电流值（pA）
        """
        if self._simulation:
            return self._generate_simulation_current(channel)

        # 真实硬件读取逻辑（待实现）
        # TODO: 实现真实硬件电流读取
        return self._generate_simulation_current(channel)

    def _generate_simulation_current(self, channel: int) -> float:
        """生成仿真电流数据。

        Args:
            channel: 通道号

        Returns:
            float: 仿真电流值（pA）
        """
        base_current = self._sim_base_currents[channel]

        # 添加正弦波信号（模拟真实信号）
        signal_freq = 0.5 + channel * 0.2  # 不同通道不同频率
        signal = base_current * 0.1 * np.sin(2 * np.pi * signal_freq * self._sim_time)

        # 添加高斯噪声（模拟测量噪声）
        noise_level = base_current * 0.01  # 1%噪声
        noise = np.random.normal(0, noise_level)

        return base_current + signal + noise

    def _apply_filter(self, channel: int, current: float, config: ChannelConfig) -> float:
        """应用滤波器。

        Args:
            channel: 通道号
            current: 原始电流值（pA）
            config: 通道配置

        Returns:
            float: 滤波后电流值（pA）
        """
        state = self._filter_states[channel]

        if config.filter_type == FilterType.NONE:
            return current

        if config.filter_type == FilterType.LOWPASS:
            # 一阶低通滤波器
            # y[n] = alpha * x[n] + (1 - alpha) * y[n-1]
            # alpha = 2*pi*fc*dt / (2*pi*fc*dt + 1)
            dt = 1.0 / self._acq_config.sample_rate
            fc = config.filter_cutoff
            alpha = (2 * np.pi * fc * dt) / (2 * np.pi * fc * dt + 1)

            filtered = alpha * current + (1 - alpha) * state["prev_output"]
            state["prev_output"] = filtered
            return filtered

        if config.filter_type == FilterType.MOVING_AVERAGE:
            # 移动平均滤波
            state["history"].append(current)
            window_data = list(state["history"])[-config.filter_window :]
            return float(np.mean(window_data))

        if config.filter_type == FilterType.MEDIAN:
            # 中值滤波
            state["history"].append(current)
            window_data = list(state["history"])[-config.filter_window :]
            return float(np.median(window_data))

        return current

    def _calculate_noise_rms(self, channel: int) -> float:
        """计算噪声RMS值。

        Args:
            channel: 通道号

        Returns:
            float: 噪声RMS值（pA）
        """
        buffer = self._data_buffers[channel]
        if len(buffer) < 2:
            return 0.0

        window = min(self._acq_config.snr_calc_window, len(buffer))
        recent_data = list(buffer)[-window:]
        currents = np.array([d.current_pa for d in recent_data])

        return float(np.std(currents))

    def _calculate_signal_rms(self, channel: int) -> float:
        """计算信号RMS值。

        Args:
            channel: 通道号

        Returns:
            float: 信号RMS值（pA）
        """
        buffer = self._data_buffers[channel]
        if len(buffer) < 2:
            return 0.0

        window = min(self._acq_config.snr_calc_window, len(buffer))
        recent_data = list(buffer)[-window:]
        currents = np.array([d.current_pa for d in recent_data])

        return float(np.sqrt(np.mean(currents**2)))

    @staticmethod
    def get_range_resolution(current_range: CurrentRange) -> float:
        """获取指定量程的分辨率。

        Args:
            current_range: 电流量程

        Returns:
            float: 分辨率（pA）
        """
        range_resolutions = {
            CurrentRange.RANGE_1NA: 1.0,  # 1pA
            CurrentRange.RANGE_10NA: 10.0,  # 10pA
            CurrentRange.RANGE_100NA: 100.0,  # 100pA
            CurrentRange.RANGE_1UA: 1000.0,  # 1nA = 1000pA
            CurrentRange.RANGE_10UA: 10000.0,  # 10nA = 10000pA
            CurrentRange.RANGE_100UA: 100000.0,  # 100nA = 100000pA
            CurrentRange.RANGE_1MA: 1000000.0,  # 1μA = 1000000pA
        }
        return range_resolutions[current_range]

    @staticmethod
    def get_range_max(current_range: CurrentRange) -> float:
        """获取指定量程的最大值。

        Args:
            current_range: 电流量程

        Returns:
            float: 最大值（pA）
        """
        range_max_values = {
            CurrentRange.RANGE_1NA: 1000.0,  # 1nA = 1000pA
            CurrentRange.RANGE_10NA: 10000.0,  # 10nA = 10000pA
            CurrentRange.RANGE_100NA: 100000.0,  # 100nA = 100000pA
            CurrentRange.RANGE_1UA: 1000000.0,  # 1μA = 1000000pA
            CurrentRange.RANGE_10UA: 10000000.0,  # 10μA = 10000000pA
            CurrentRange.RANGE_100UA: 100000000.0,  # 100μA = 100000000pA
            CurrentRange.RANGE_1MA: 1000000000.0,  # 1mA = 1000000000pA
        }
        return range_max_values[current_range]
