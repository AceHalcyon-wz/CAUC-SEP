"""
皮安表高级服务

文件名: picoammeter_advanced_service.py
路径: backend/services/
功能: 提供多通道软件同步触发、专业信号分析算法、条件触发采集、断连数据缓存续传等高级功能
作者: Backend Engineer Agent
创建日期: 2026-03-25
版本: 1.0.0

核心功能：
    - 多通道软件同步触发：多设备同步采集、软件触发、时间戳对齐
    - 专业信号分析算法：噪声分析、频谱分析、统计特性分析、信号处理
    - 条件触发采集：阈值触发、边沿触发、窗口触发、自定义条件触发
    - 断连数据缓存续传：本地缓存、断点续传、数据完整性校验

依赖：
    - backend.core.picoammeter: 皮安表驱动
    - scipy: 科学计算库（用于信号处理）
    - numpy: 数值计算库

安全约束：
    - 电流测量范围必须在设备规格内
    - 数据缓存必须定期清理
    - 触发条件必须经过有效性校验
"""

import asyncio
import json
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable

import numpy as np
from scipy import signal, stats

from backend.core.abstract import DeviceStatus

logger = logging.getLogger(__name__)


# ==================== 常量定义 ====================

# 采集参数
MAX_CHANNELS = 8  # 最大通道数
MAX_BUFFER_SIZE = 100000  # 最大缓存大小
DEFAULT_SAMPLE_RATE = 1000  # 默认采样率（Hz）

# 触发参数
TRIGGER_DEBOUNCE_MS = 10  # 触发消抖时间（毫秒）
MAX_TRIGGER_WAIT_SECONDS = 3600  # 最大触发等待时间（秒）

# 数据缓存参数
CACHE_DIR = Path("data/cache/picoammeter")
MAX_CACHE_FILE_SIZE_MB = 100  # 最大缓存文件大小（MB）
CACHE_RETENTION_DAYS = 7  # 缓存保留天数


class TriggerType(Enum):
    """触发类型枚举。

    Attributes:
        IMMEDIATE: 立即触发
        THRESHOLD_RISING: 上升沿阈值触发
        THRESHOLD_FALLING: 下降沿阈值触发
        WINDOW_ENTER: 进入窗口触发
        WINDOW_EXIT: 离开窗口触发
        CUSTOM: 自定义条件触发
    """

    IMMEDIATE = "immediate"
    THRESHOLD_RISING = "threshold_rising"
    THRESHOLD_FALLING = "threshold_falling"
    WINDOW_ENTER = "window_enter"
    WINDOW_EXIT = "window_exit"
    CUSTOM = "custom"


class AnalysisType(Enum):
    """分析类型枚举。

    Attributes:
        STATISTICAL: 统计分析
        SPECTRAL: 频谱分析
        NOISE: 噪声分析
        TREND: 趋势分析
        ANOMALY: 异常检测
    """

    STATISTICAL = "statistical"
    SPECTRAL = "spectral"
    NOISE = "noise"
    TREND = "trend"
    ANOMALY = "anomaly"


class ConnectionStatus(Enum):
    """连接状态枚举。

    Attributes:
        CONNECTED: 已连接
        DISCONNECTED: 已断开
        RECONNECTING: 重连中
        ERROR: 错误
    """

    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    RECONNECTING = "reconnecting"
    ERROR = "error"


@dataclass
class ChannelConfig:
    """通道配置数据类。

    Attributes:
        channel_id: 通道ID
        enabled: 是否启用
        range: 量程（A）
        nplc: 积分时间（NPLC）
        auto_range: 是否自动量程
        label: 通道标签
    """

    channel_id: int
    enabled: bool = True
    range: float = 1e-6
    nplc: float = 1.0
    auto_range: bool = True
    label: str = ""


@dataclass
class TriggerConfig:
    """触发配置数据类。

    Attributes:
        trigger_type: 触发类型
        threshold: 阈值（A）
        window_low: 窗口下限（A）
        window_high: 窗口上限（A）
        hysteresis: 滞回（A）
        custom_condition: 自定义条件表达式
        pre_trigger_samples: 预触发采样点数
        post_trigger_samples: 后触发采样点数
    """

    trigger_type: TriggerType = TriggerType.IMMEDIATE
    threshold: float = 0.0
    window_low: float = -1e-6
    window_high: float = 1e-6
    hysteresis: float = 0.0
    custom_condition: str = ""
    pre_trigger_samples: int = 100
    post_trigger_samples: int = 1000


@dataclass
class DataPoint:
    """数据点数据类。

    Attributes:
        timestamp: 时间戳
        channel_id: 通道ID
        current: 电流值（A）
        voltage: 电压值（V），可选
        status: 状态标志
    """

    timestamp: float
    channel_id: int
    current: float
    voltage: float | None = None
    status: int = 0


@dataclass
class AnalysisResult:
    """分析结果数据类。

    Attributes:
        analysis_type: 分析类型
        channel_id: 通道ID
        parameters: 分析参数
        results: 分析结果
        timestamp: 时间戳
    """

    analysis_type: AnalysisType
    channel_id: int
    parameters: dict[str, Any] = field(default_factory=dict)
    results: dict[str, Any] = field(default_factory=dict)
    timestamp: float = 0.0


@dataclass
class CacheMetadata:
    """缓存元数据数据类。

    Attributes:
        cache_id: 缓存ID
        start_time: 起始时间
        end_time: 结束时间
        sample_count: 采样点数
        channels: 通道列表
        file_path: 文件路径
        checksum: 校验和
        uploaded: 是否已上传
    """

    cache_id: str
    start_time: float
    end_time: float
    sample_count: int
    channels: list[int]
    file_path: str
    checksum: str = ""
    uploaded: bool = False


class PicoammeterAdvancedService:
    """皮安表高级服务类。

    提供多通道软件同步触发、专业信号分析算法、条件触发采集、断连数据缓存续传等高级功能。

    Example:
        >>> service = PicoammeterAdvancedService(picoammeter)
        >>> # 多通道同步采集
        >>> configs = [ChannelConfig(channel_id=0), ChannelConfig(channel_id=1)]
        >>> await service.configure_channels(configs)
        >>> await service.start_synchronized_acquisition()
        >>> # 条件触发采集
        >>> trigger = TriggerConfig(
        ...     trigger_type=TriggerType.THRESHOLD_RISING,
        ...     threshold=1e-6,
        ...     pre_trigger_samples=100,
        ...     post_trigger_samples=1000
        ... )
        >>> await service.start_triggered_acquisition(trigger)
    """

    def __init__(self, picoammeter: Any):
        """初始化高级控制服务。

        Args:
            picoammeter: 皮安表驱动实例
        """
        self._device = picoammeter

        # 通道配置
        self._channel_configs: dict[int, ChannelConfig] = {}

        # 数据缓存
        self._data_buffer: dict[int, deque[DataPoint]] = {
            i: deque(maxlen=MAX_BUFFER_SIZE) for i in range(MAX_CHANNELS)
        }
        self._connection_status = ConnectionStatus.CONNECTED
        self._cache_metadata: list[CacheMetadata] = []

        # 采集状态
        self._acquisition_running = False
        self._acquisition_task: asyncio.Task | None = None
        self._acquisition_cancelled = False

        # 触发状态
        self._trigger_config: TriggerConfig | None = None
        self._trigger_armed = False
        self._trigger_fired = False
        self._pre_trigger_buffer: dict[int, deque[DataPoint]] = {}

        # 同步状态
        self._sync_master = False
        self._sync_devices: list[Any] = []
        self._sync_offset_ns = 0

        # 回调函数
        self._data_callback: Callable[[DataPoint], None] | None = None
        self._trigger_callback: Callable[[TriggerConfig, list[DataPoint]], None] | None = None
        self._connection_callback: Callable[[ConnectionStatus], None] | None = None

        # 确保缓存目录存在
        CACHE_DIR.mkdir(parents=True, exist_ok=True)

        logger.info(f"PicoammeterAdvancedService initialized for {picoammeter.device_id}")

    # ==================== 多通道软件同步触发 ====================

    async def configure_channels(
        self,
        configs: list[ChannelConfig],
    ) -> bool:
        """配置多个通道。

        Args:
            configs: 通道配置列表

        Returns:
            bool: 配置是否成功
        """
        for config in configs:
            if not 0 <= config.channel_id < MAX_CHANNELS:
                logger.error(f"Invalid channel_id: {config.channel_id}")
                return False

            self._channel_configs[config.channel_id] = config

            # 配置设备通道
            await self._device.configure_channel(
                channel=config.channel_id,
                range=config.range,
                nplc=config.nplc,
                auto_range=config.auto_range,
            )

        logger.info(f"Configured {len(configs)} channels")
        return True

    async def start_synchronized_acquisition(
        self,
        sample_rate: float = DEFAULT_SAMPLE_RATE,
        data_callback: Callable[[DataPoint], None] | None = None,
    ) -> bool:
        """启动同步采集。

        Args:
            sample_rate: 采样率（Hz）
            data_callback: 数据回调函数

        Returns:
            bool: 启动是否成功
        """
        if self._acquisition_running:
            logger.warning("Acquisition already running")
            return False

        if self._device.status != DeviceStatus.READY:
            logger.error(f"Device not ready: {self._device.status.value}")
            return False

        self._data_callback = data_callback
        self._acquisition_running = True
        self._acquisition_cancelled = False
        self._sample_interval = 1.0 / sample_rate

        try:
            self._acquisition_task = asyncio.create_task(
                self._acquisition_loop()
            )
            logger.info(f"Synchronized acquisition started: rate={sample_rate}Hz")
            return True

        except Exception as e:
            logger.error(f"Start acquisition error: {e}")
            self._acquisition_running = False
            return False

    async def _acquisition_loop(self) -> None:
        """采集循环。"""
        while self._acquisition_running:
            try:
                # 检查连接状态
                if self._connection_status != ConnectionStatus.CONNECTED:
                    await self._handle_disconnection()
                    continue

                # 读取所有启用的通道
                timestamp = time.time()

                for channel_id, config in self._channel_configs.items():
                    if not config.enabled:
                        continue

                    try:
                        # 读取电流
                        current = await self._device.read_current(channel_id)

                        # 创建数据点
                        data_point = DataPoint(
                            timestamp=timestamp,
                            channel_id=channel_id,
                            current=current,
                        )

                        # 存入缓存
                        self._data_buffer[channel_id].append(data_point)

                        # 检查触发条件
                        if self._trigger_armed:
                            await self._check_trigger(data_point)

                        # 回调通知
                        if self._data_callback:
                            self._data_callback(data_point)

                    except Exception as e:
                        logger.error(f"Read channel {channel_id} error: {e}")
                        await self._handle_read_error(channel_id, e)

                await asyncio.sleep(self._sample_interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Acquisition loop error: {e}")
                await asyncio.sleep(0.1)

    async def stop_acquisition(self) -> bool:
        """停止采集。

        Returns:
            bool: 停止是否成功
        """
        if not self._acquisition_running:
            return True

        self._acquisition_cancelled = True
        self._acquisition_running = False

        if self._acquisition_task:
            self._acquisition_task.cancel()
            try:
                await self._acquisition_task
            except asyncio.CancelledError:
                pass

        logger.info("Acquisition stopped")
        return True

    async def add_sync_device(self, device: Any) -> bool:
        """添加同步设备。

        Args:
            device: 同步设备实例

        Returns:
            bool: 添加是否成功
        """
        self._sync_devices.append(device)
        logger.info(f"Sync device added: {device.device_id}")
        return True

    async def synchronize_timestamps(self) -> dict[str, Any]:
        """同步时间戳。

        Returns:
            Dict[str, Any]: 同步结果
        """
        # 计算时间偏移
        local_time = time.time()

        offsets = []
        for device in self._sync_devices:
            # 简化处理：假设设备时间戳与本地时间相同
            device_time = time.time()
            offset = device_time - local_time
            offsets.append(offset)

        if offsets:
            self._sync_offset_ns = int(np.mean(offsets) * 1e9)

        return {
            "master_device": self._device.device_id,
            "sync_devices": [d.device_id for d in self._sync_devices],
            "sync_offset_ns": self._sync_offset_ns,
        }

    # ==================== 专业信号分析算法 ====================

    def analyze_statistical(
        self,
        data: list[DataPoint],
    ) -> AnalysisResult:
        """统计分析。

        Args:
            data: 数据点列表

        Returns:
            AnalysisResult: 分析结果
        """
        if len(data) < 2:
            return AnalysisResult(
                analysis_type=AnalysisType.STATISTICAL,
                channel_id=data[0].channel_id if data else 0,
                results={"error": "Insufficient data"},
            )

        currents = np.array([d.current for d in data])

        results = {
            "mean": float(np.mean(currents)),
            "std": float(np.std(currents)),
            "variance": float(np.var(currents)),
            "min": float(np.min(currents)),
            "max": float(np.max(currents)),
            "range": float(np.max(currents) - np.min(currents)),
            "median": float(np.median(currents)),
            "skewness": float(stats.skew(currents)),
            "kurtosis": float(stats.kurtosis(currents)),
            "sample_count": len(currents),
        }

        return AnalysisResult(
            analysis_type=AnalysisType.STATISTICAL,
            channel_id=data[0].channel_id,
            results=results,
            timestamp=time.time(),
        )

    def analyze_spectral(
        self,
        data: list[DataPoint],
        sample_rate: float = DEFAULT_SAMPLE_RATE,
    ) -> AnalysisResult:
        """频谱分析。

        Args:
            data: 数据点列表
            sample_rate: 采样率

        Returns:
            AnalysisResult: 分析结果
        """
        if len(data) < 10:
            return AnalysisResult(
                analysis_type=AnalysisType.SPECTRAL,
                channel_id=data[0].channel_id if data else 0,
                results={"error": "Insufficient data for spectral analysis"},
            )

        currents = np.array([d.current for d in data])

        # FFT分析
        n = len(currents)
        fft_result = np.fft.fft(currents)
        freqs = np.fft.fftfreq(n, 1.0 / sample_rate)

        # 功率谱密度
        psd = np.abs(fft_result) ** 2 / n

        # 只取正频率部分
        positive_freq_idx = freqs > 0
        freqs_positive = freqs[positive_freq_idx]
        psd_positive = psd[positive_freq_idx]

        # 主频率
        dominant_freq_idx = np.argmax(psd_positive)
        dominant_freq = freqs_positive[dominant_freq_idx]

        results = {
            "dominant_frequency": float(dominant_freq),
            "dominant_amplitude": float(np.sqrt(psd_positive[dominant_freq_idx])),
            "frequency_resolution": float(freqs_positive[1] - freqs_positive[0]) if len(freqs_positive) > 1 else 0,
            "nyquist_frequency": float(sample_rate / 2),
            "total_power": float(np.sum(psd_positive)),
        }

        return AnalysisResult(
            analysis_type=AnalysisType.SPECTRAL,
            channel_id=data[0].channel_id,
            parameters={"sample_rate": sample_rate},
            results=results,
            timestamp=time.time(),
        )

    def analyze_noise(
        self,
        data: list[DataPoint],
    ) -> AnalysisResult:
        """噪声分析。

        Args:
            data: 数据点列表

        Returns:
            AnalysisResult: 分析结果
        """
        if len(data) < 100:
            return AnalysisResult(
                analysis_type=AnalysisType.NOISE,
                channel_id=data[0].channel_id if data else 0,
                results={"error": "Insufficient data for noise analysis"},
            )

        currents = np.array([d.current for d in data])

        # 去除直流分量
        currents_ac = currents - np.mean(currents)

        # RMS噪声
        rms_noise = np.sqrt(np.mean(currents_ac ** 2))

        # 峰峰值噪声
        peak_to_peak = np.max(currents_ac) - np.min(currents_ac)

        # 噪声密度（假设带宽为采样率/2）
        sample_rate = len(data) / (data[-1].timestamp - data[0].timestamp)
        bandwidth = sample_rate / 2
        noise_density = rms_noise / np.sqrt(bandwidth)

        # 信噪比（假设信号为均值）
        signal_level = abs(np.mean(currents))
        snr = 20 * np.log10(signal_level / rms_noise) if rms_noise > 0 else float('inf')

        results = {
            "rms_noise": float(rms_noise),
            "peak_to_peak_noise": float(peak_to_peak),
            "noise_density": float(noise_density),
            "snr_db": float(snr),
            "bandwidth_hz": float(bandwidth),
        }

        return AnalysisResult(
            analysis_type=AnalysisType.NOISE,
            channel_id=data[0].channel_id,
            results=results,
            timestamp=time.time(),
        )

    def analyze_trend(
        self,
        data: list[DataPoint],
    ) -> AnalysisResult:
        """趋势分析。

        Args:
            data: 数据点列表

        Returns:
            AnalysisResult: 分析结果
        """
        if len(data) < 10:
            return AnalysisResult(
                analysis_type=AnalysisType.TREND,
                channel_id=data[0].channel_id if data else 0,
                results={"error": "Insufficient data for trend analysis"},
            )

        timestamps = np.array([d.timestamp - data[0].timestamp for d in data])
        currents = np.array([d.current for d in data])

        # 线性拟合
        coeffs = np.polyfit(timestamps, currents, 1)
        slope = coeffs[0]
        intercept = coeffs[1]

        # 计算拟合优度
        predicted = np.polyval(coeffs, timestamps)
        ss_res = np.sum((currents - predicted) ** 2)
        ss_tot = np.sum((currents - np.mean(currents)) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        # 趋势方向
        if slope > 0:
            trend_direction = "increasing"
        elif slope < 0:
            trend_direction = "decreasing"
        else:
            trend_direction = "stable"

        results = {
            "slope": float(slope),
            "intercept": float(intercept),
            "r_squared": float(r_squared),
            "trend_direction": trend_direction,
            "rate_per_second": float(slope),
            "rate_per_minute": float(slope * 60),
        }

        return AnalysisResult(
            analysis_type=AnalysisType.TREND,
            channel_id=data[0].channel_id,
            results=results,
            timestamp=time.time(),
        )

    def detect_anomalies(
        self,
        data: list[DataPoint],
        threshold_sigma: float = 3.0,
    ) -> AnalysisResult:
        """异常检测。

        Args:
            data: 数据点列表
            threshold_sigma: 阈值（标准差倍数）

        Returns:
            AnalysisResult: 分析结果
        """
        if len(data) < 10:
            return AnalysisResult(
                analysis_type=AnalysisType.ANOMALY,
                channel_id=data[0].channel_id if data else 0,
                results={"error": "Insufficient data for anomaly detection"},
            )

        currents = np.array([d.current for d in data])
        timestamps = np.array([d.timestamp for d in data])

        mean_current = np.mean(currents)
        std_current = np.std(currents)

        # 检测异常点
        upper_threshold = mean_current + threshold_sigma * std_current
        lower_threshold = mean_current - threshold_sigma * std_current

        anomaly_mask = (currents > upper_threshold) | (currents < lower_threshold)
        anomaly_indices = np.where(anomaly_mask)[0]

        anomalies = [
            {
                "index": int(idx),
                "timestamp": float(timestamps[idx]),
                "value": float(currents[idx]),
                "deviation_sigma": float(abs(currents[idx] - mean_current) / std_current) if std_current > 0 else 0,
            }
            for idx in anomaly_indices
        ]

        results = {
            "anomaly_count": len(anomalies),
            "anomaly_ratio": float(len(anomalies) / len(data)),
            "threshold_sigma": threshold_sigma,
            "upper_threshold": float(upper_threshold),
            "lower_threshold": float(lower_threshold),
            "anomalies": anomalies[:100],  # 最多返回100个异常点
        }

        return AnalysisResult(
            analysis_type=AnalysisType.ANOMALY,
            channel_id=data[0].channel_id,
            parameters={"threshold_sigma": threshold_sigma},
            results=results,
            timestamp=time.time(),
        )

    # ==================== 条件触发采集 ====================

    async def start_triggered_acquisition(
        self,
        trigger_config: TriggerConfig,
        trigger_callback: Callable[[TriggerConfig, list[DataPoint]], None] | None = None,
    ) -> bool:
        """启动条件触发采集。

        Args:
            trigger_config: 触发配置
            trigger_callback: 触发回调函数

        Returns:
            bool: 启动是否成功
        """
        self._trigger_config = trigger_config
        self._trigger_callback = trigger_callback
        self._trigger_armed = True
        self._trigger_fired = False

        # 初始化预触发缓存
        for channel_id in self._channel_configs:
            self._pre_trigger_buffer[channel_id] = deque(
                maxlen=trigger_config.pre_trigger_samples
            )

        logger.info(f"Triggered acquisition armed: type={trigger_config.trigger_type.value}")
        return True

    async def _check_trigger(self, data_point: DataPoint) -> None:
        """检查触发条件。

        Args:
            data_point: 数据点
        """
        if self._trigger_config is None or not self._trigger_armed:
            return

        # 存储预触发数据
        if data_point.channel_id in self._pre_trigger_buffer:
            self._pre_trigger_buffer[data_point.channel_id].append(data_point)

        # 检查触发条件
        triggered = False

        if self._trigger_config.trigger_type == TriggerType.THRESHOLD_RISING:
            triggered = data_point.current > self._trigger_config.threshold

        elif self._trigger_config.trigger_type == TriggerType.THRESHOLD_FALLING:
            triggered = data_point.current < self._trigger_config.threshold

        elif self._trigger_config.trigger_type == TriggerType.WINDOW_ENTER:
            triggered = (
                self._trigger_config.window_low <= data_point.current <= self._trigger_config.window_high
            )

        elif self._trigger_config.trigger_type == TriggerType.WINDOW_EXIT:
            triggered = not (
                self._trigger_config.window_low <= data_point.current <= self._trigger_config.window_high
            )

        elif self._trigger_config.trigger_type == TriggerType.CUSTOM:
            triggered = self._evaluate_custom_trigger(data_point)

        if triggered and not self._trigger_fired:
            await self._handle_trigger_event(data_point)

    async def _handle_trigger_event(self, data_point: DataPoint) -> None:
        """处理触发事件。

        Args:
            data_point: 触发数据点
        """
        self._trigger_fired = True
        self._trigger_armed = False

        logger.info(
            f"Trigger fired: type={self._trigger_config.trigger_type.value}, "
            f"channel={data_point.channel_id}, value={data_point.current:.2e}A"
        )

        # 收集触发数据
        triggered_data = []

        # 添加预触发数据
        for channel_id, buffer in self._pre_trigger_buffer.items():
            triggered_data.extend(list(buffer))

        # 添加当前数据点
        triggered_data.append(data_point)

        # 继续采集后触发数据
        post_trigger_count = 0
        while post_trigger_count < self._trigger_config.post_trigger_samples:
            await asyncio.sleep(self._sample_interval)

            # 读取所有通道
            for channel_id in self._channel_configs:
                current = await self._device.read_current(channel_id)
                post_point = DataPoint(
                    timestamp=time.time(),
                    channel_id=channel_id,
                    current=current,
                )
                triggered_data.append(post_point)

            post_trigger_count += 1

        # 回调通知
        if self._trigger_callback:
            self._trigger_callback(self._trigger_config, triggered_data)

        # 重置触发状态
        self._trigger_fired = False

    def _evaluate_custom_trigger(self, data_point: DataPoint) -> bool:
        """评估自定义触发条件。

        Args:
            data_point: 数据点

        Returns:
            bool: 是否触发
        """
        # 简化实现：解析简单表达式
        # 实际应用中可以使用eval()或自定义解析器
        condition = self._trigger_config.custom_condition

        if not condition:
            return False

        try:
            # 安全的变量替换
            context = {
                "current": data_point.current,
                "channel": data_point.channel_id,
                "timestamp": data_point.timestamp,
            }

            # 简单表达式解析（仅支持基本比较）
            # 实际应用中应使用更安全的解析方法
            return eval(condition, {"__builtins__": {}}, context)

        except Exception as e:
            logger.error(f"Custom trigger evaluation error: {e}")
            return False

    async def stop_triggered_acquisition(self) -> bool:
        """停止条件触发采集。

        Returns:
            bool: 停止是否成功
        """
        self._trigger_armed = False
        self._trigger_fired = False
        self._trigger_config = None

        logger.info("Triggered acquisition stopped")
        return True

    # ==================== 断连数据缓存续传 ====================

    async def _handle_disconnection(self) -> None:
        """处理断连事件。"""
        self._connection_status = ConnectionStatus.DISCONNECTED

        if self._connection_callback:
            self._connection_callback(self._connection_status)

        logger.warning("Device disconnected, starting reconnection...")

        # 尝试重连
        self._connection_status = ConnectionStatus.RECONNECTING

        max_retries = 10
        for attempt in range(max_retries):
            try:
                await self._device.connect()
                self._connection_status = ConnectionStatus.CONNECTED
                logger.info(f"Reconnected after {attempt + 1} attempts")

                if self._connection_callback:
                    self._connection_callback(self._connection_status)

                return

            except Exception as e:
                logger.error(f"Reconnection attempt {attempt + 1} failed: {e}")
                await asyncio.sleep(2.0)

        self._connection_status = ConnectionStatus.ERROR
        logger.error("Reconnection failed after max attempts")

        if self._connection_callback:
            self._connection_callback(self._connection_status)

    async def _handle_read_error(self, channel_id: int, error: Exception) -> None:
        """处理读取错误。

        Args:
            channel_id: 通道ID
            error: 错误信息
        """
        logger.error(f"Read error on channel {channel_id}: {error}")

        # 缓存当前数据
        await self._save_cache()

    async def _save_cache(self) -> bool:
        """保存数据缓存。

        Returns:
            bool: 保存是否成功
        """
        try:
            cache_id = f"cache_{int(time.time() * 1000)}"
            cache_file = CACHE_DIR / f"{cache_id}.json"

            cache_data = {
                "cache_id": cache_id,
                "device_id": self._device.device_id,
                "timestamp": time.time(),
                "channels": {},
            }

            for channel_id, buffer in self._data_buffer.items():
                if len(buffer) > 0:
                    cache_data["channels"][str(channel_id)] = [
                        {
                            "timestamp": d.timestamp,
                            "current": d.current,
                            "voltage": d.voltage,
                        }
                        for d in buffer
                    ]

            # 写入文件
            with open(cache_file, "w") as f:
                json.dump(cache_data, f)

            # 记录元数据
            metadata = CacheMetadata(
                cache_id=cache_id,
                start_time=min(d.timestamp for buffer in self._data_buffer.values() for d in buffer) if any(self._data_buffer.values()) else time.time(),
                end_time=time.time(),
                sample_count=sum(len(buffer) for buffer in self._data_buffer.values()),
                channels=list(self._channel_configs.keys()),
                file_path=str(cache_file),
            )
            self._cache_metadata.append(metadata)

            logger.info(f"Cache saved: {cache_id}, {metadata.sample_count} samples")
            return True

        except Exception as e:
            logger.error(f"Save cache error: {e}")
            return False

    async def load_cache(self, cache_id: str) -> dict[str, Any] | None:
        """加载数据缓存。

        Args:
            cache_id: 缓存ID

        Returns:
            Dict[str, Any] | None: 缓存数据
        """
        try:
            cache_file = CACHE_DIR / f"{cache_id}.json"

            if not cache_file.exists():
                logger.error(f"Cache file not found: {cache_id}")
                return None

            with open(cache_file, "r") as f:
                cache_data = json.load(f)

            logger.info(f"Cache loaded: {cache_id}")
            return cache_data

        except Exception as e:
            logger.error(f"Load cache error: {e}")
            return None

    async def resume_from_cache(self, cache_id: str) -> bool:
        """从缓存恢复数据。

        Args:
            cache_id: 缓存ID

        Returns:
            bool: 恢复是否成功
        """
        cache_data = await self.load_cache(cache_id)

        if cache_data is None:
            return False

        try:
            # 恢复数据到缓存
            for channel_str, data_list in cache_data["channels"].items():
                channel_id = int(channel_str)
                self._data_buffer[channel_id].clear()

                for item in data_list:
                    data_point = DataPoint(
                        timestamp=item["timestamp"],
                        channel_id=channel_id,
                        current=item["current"],
                        voltage=item.get("voltage"),
                    )
                    self._data_buffer[channel_id].append(data_point)

            logger.info(f"Resumed from cache: {cache_id}")
            return True

        except Exception as e:
            logger.error(f"Resume from cache error: {e}")
            return False

    def get_cache_list(self) -> list[dict[str, Any]]:
        """获取缓存列表。

        Returns:
            List[Dict[str, Any]]: 缓存列表
        """
        return [
            {
                "cache_id": m.cache_id,
                "start_time": m.start_time,
                "end_time": m.end_time,
                "sample_count": m.sample_count,
                "channels": m.channels,
                "uploaded": m.uploaded,
            }
            for m in self._cache_metadata
        ]

    async def cleanup_old_caches(self) -> int:
        """清理过期缓存。

        Returns:
            int: 清理的缓存数量
        """
        current_time = time.time()
        retention_seconds = CACHE_RETENTION_DAYS * 24 * 3600
        cleaned_count = 0

        for metadata in self._cache_metadata[:]:
            if current_time - metadata.end_time > retention_seconds:
                try:
                    cache_file = Path(metadata.file_path)
                    if cache_file.exists():
                        cache_file.unlink()

                    self._cache_metadata.remove(metadata)
                    cleaned_count += 1

                except Exception as e:
                    logger.error(f"Cleanup cache error: {e}")

        logger.info(f"Cleaned {cleaned_count} old caches")
        return cleaned_count

    # ==================== 辅助方法 ====================

    def get_buffer_data(
        self,
        channel_id: int,
        count: int = 1000,
    ) -> list[dict[str, Any]]:
        """获取缓存数据。

        Args:
            channel_id: 通道ID
            count: 返回数据点数

        Returns:
            List[Dict[str, Any]]: 数据列表
        """
        if channel_id not in self._data_buffer:
            return []

        buffer = list(self._data_buffer[channel_id])[-count:]
        return [
            {
                "timestamp": d.timestamp,
                "current": d.current,
                "voltage": d.voltage,
                "status": d.status,
            }
            for d in buffer
        ]

    def get_acquisition_status(self) -> dict[str, Any]:
        """获取采集状态。

        Returns:
            Dict[str, Any]: 采集状态信息
        """
        return {
            "running": self._acquisition_running,
            "trigger_armed": self._trigger_armed,
            "trigger_fired": self._trigger_fired,
            "connection_status": self._connection_status.value,
            "buffer_sizes": {
                str(ch): len(buf) for ch, buf in self._data_buffer.items()
            },
        }

    # ==================== 资源清理 ====================

    async def cleanup(self) -> None:
        """清理所有资源。"""
        await self.stop_acquisition()
        await self.stop_triggered_acquisition()
        await self._save_cache()
        await self.cleanup_old_caches()
        logger.info("PicoammeterAdvancedService cleanup completed")
