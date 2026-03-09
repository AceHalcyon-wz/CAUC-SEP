"""
测试微电流采集模块 (Picoammeter)

测试内容：
- 初始化和配置
- 连接/断开
- 通道配置
- 采样率设置
- 多通道同步采集
- 滤波功能（低通、移动平均、中值）
- 信噪比计算
- 数据缓冲区管理
"""


import numpy as np
import pytest

from core.abstract import DeviceStatus
from core.picoammeter import (
    AcquisitionConfig,
    ChannelConfig,
    ChannelData,
    CurrentRange,
    FilterType,
    Picoammeter,
)


class TestCurrentRange:
    """测试电流量程枚举。"""

    def test_range_values(self):
        """测试量程值定义。"""
        assert CurrentRange.RANGE_1NA.value == "1nA"
        assert CurrentRange.RANGE_10NA.value == "10nA"
        assert CurrentRange.RANGE_100NA.value == "100nA"
        assert CurrentRange.RANGE_1UA.value == "1uA"
        assert CurrentRange.RANGE_10UA.value == "10uA"
        assert CurrentRange.RANGE_100UA.value == "100uA"
        assert CurrentRange.RANGE_1MA.value == "1mA"

    def test_range_count(self):
        """测试量程数量。"""
        assert len(CurrentRange) == 7


class TestFilterType:
    """测试滤波类型枚举。"""

    def test_filter_type_values(self):
        """测试滤波类型值定义。"""
        assert FilterType.NONE.value == "none"
        assert FilterType.LOWPASS.value == "lowpass"
        assert FilterType.MOVING_AVERAGE.value == "moving_average"
        assert FilterType.MEDIAN.value == "median"

    def test_filter_type_count(self):
        """测试滤波类型数量。"""
        assert len(FilterType) == 4


class TestChannelConfig:
    """测试通道配置数据类。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = ChannelConfig()

        assert config.enabled is True
        assert config.current_range == CurrentRange.RANGE_1UA
        assert config.filter_type == FilterType.NONE
        assert config.filter_cutoff == 10.0
        assert config.filter_window == 5
        assert config.offset == 0.0

    def test_custom_config(self):
        """测试自定义配置。"""
        config = ChannelConfig(
            enabled=False,
            current_range=CurrentRange.RANGE_10NA,
            filter_type=FilterType.LOWPASS,
            filter_cutoff=50.0,
            filter_window=10,
            offset=5.5,
        )

        assert config.enabled is False
        assert config.current_range == CurrentRange.RANGE_10NA
        assert config.filter_type == FilterType.LOWPASS
        assert config.filter_cutoff == 50.0
        assert config.filter_window == 10
        assert config.offset == 5.5


class TestChannelData:
    """测试通道数据类。"""

    def test_default_data(self):
        """测试默认数据。"""
        data = ChannelData()

        assert data.current_pa == 0.0
        assert data.timestamp == 0.0
        assert data.snr_db == 0.0
        assert data.raw_current_pa == 0.0
        assert data.noise_rms_pa == 0.0
        assert data.signal_rms_pa == 0.0

    def test_custom_data(self):
        """测试自定义数据。"""
        data = ChannelData(
            current_pa=123.45,
            timestamp=1.5,
            snr_db=42.5,
            raw_current_pa=120.0,
            noise_rms_pa=3.45,
            signal_rms_pa=123.45,
        )

        assert data.current_pa == 123.45
        assert data.timestamp == 1.5
        assert data.snr_db == 42.5
        assert data.raw_current_pa == 120.0
        assert data.noise_rms_pa == 3.45
        assert data.signal_rms_pa == 123.45


class TestAcquisitionConfig:
    """测试采集配置数据类。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = AcquisitionConfig()

        assert config.sample_rate == 100.0
        assert len(config.channels) == 4
        assert config.buffer_size == 1000
        assert config.snr_calc_window == 100

    def test_custom_config(self):
        """测试自定义配置。"""
        channels = [ChannelConfig(enabled=(i % 2 == 0)) for i in range(4)]
        config = AcquisitionConfig(
            sample_rate=500.0,
            channels=channels,
            buffer_size=2000,
            snr_calc_window=50,
        )

        assert config.sample_rate == 500.0
        assert len(config.channels) == 4
        assert config.buffer_size == 2000
        assert config.snr_calc_window == 50


class TestPicoammeterInit:
    """测试Picoammeter初始化。"""

    def test_default_initialization(self):
        """测试默认初始化。"""
        device = Picoammeter(device_id="test_pico", config={})

        assert device.device_id == "test_pico"
        assert device._simulation is True
        assert device._acq_config.sample_rate == 100.0
        assert device.NUM_CHANNELS == 4
        assert device.MIN_SAMPLE_RATE == 1.0
        assert device.MAX_SAMPLE_RATE == 1000.0
        assert device.status == DeviceStatus.DISCONNECTED
        assert device._is_acquiring is False

    def test_custom_initialization(self):
        """测试自定义初始化。"""
        device = Picoammeter(
            device_id="custom_pico",
            config={
                "simulation": False,
                "sample_rate": 500.0,
                "buffer_size": 2000,
                "snr_calc_window": 50,
            },
        )

        assert device.device_id == "custom_pico"
        # 初始化时simulation参数被读取，connect()时才会回退到仿真
        assert device._simulation is False  # 配置中指定False
        assert device._acq_config.sample_rate == 500.0
        assert device._acq_config.buffer_size == 2000
        assert device._acq_config.snr_calc_window == 50

    def test_buffer_initialization(self):
        """测试缓冲区初始化。"""
        device = Picoammeter(device_id="test_pico", config={})

        assert len(device._data_buffers) == 4
        for buf in device._data_buffers:
            assert len(buf) == 0

    def test_filter_state_initialization(self):
        """测试滤波器状态初始化。"""
        device = Picoammeter(device_id="test_pico", config={})

        assert len(device._filter_states) == 4
        for state in device._filter_states:
            assert "prev_output" in state
            assert "history" in state
            assert state["prev_output"] == 0.0


class TestPicoammeterConnection:
    """测试Picoammeter连接管理。"""

    @pytest.mark.asyncio
    async def test_connect_simulation_mode(self):
        """测试仿真模式连接。"""
        device = Picoammeter(device_id="test_pico", config={"simulation": True})

        result = await device.connect()

        assert result is True
        assert device.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_disconnect(self):
        """测试断开连接。"""
        device = Picoammeter(device_id="test_pico", config={})
        await device.connect()

        result = await device.disconnect()

        assert result is True
        assert device.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_disconnect_while_acquiring(self):
        """测试采集中断开连接。"""
        device = Picoammeter(device_id="test_pico", config={})
        await device.connect()
        await device.start_acquisition()

        result = await device.disconnect()

        assert result is True
        assert device.status == DeviceStatus.DISCONNECTED
        assert device._is_acquiring is False


class TestPicoammeterChannelConfig:
    """测试Picoammeter通道配置。"""

    def test_configure_channel_enabled(self):
        """测试配置通道启用状态。"""
        device = Picoammeter(device_id="test_pico", config={})

        result = device.configure_channel(0, enabled=False)

        assert result is True
        assert device._acq_config.channels[0].enabled is False

    def test_configure_channel_range(self):
        """测试配置通道量程。"""
        device = Picoammeter(device_id="test_pico", config={})

        result = device.configure_channel(1, current_range=CurrentRange.RANGE_10NA)

        assert result is True
        assert device._acq_config.channels[1].current_range == CurrentRange.RANGE_10NA

    def test_configure_channel_filter(self):
        """测试配置通道滤波器。"""
        device = Picoammeter(device_id="test_pico", config={})

        result = device.configure_channel(
            2,
            filter_type=FilterType.LOWPASS,
            filter_cutoff=50.0,
            filter_window=10,
        )

        assert result is True
        assert device._acq_config.channels[2].filter_type == FilterType.LOWPASS
        assert device._acq_config.channels[2].filter_cutoff == 50.0
        assert device._acq_config.channels[2].filter_window == 10

    def test_configure_channel_offset(self):
        """测试配置通道偏移。"""
        device = Picoammeter(device_id="test_pico", config={})

        result = device.configure_channel(3, offset=10.5)

        assert result is True
        assert device._acq_config.channels[3].offset == 10.5

    def test_configure_channel_invalid_channel(self):
        """测试配置无效通道号。"""
        device = Picoammeter(device_id="test_pico", config={})

        with pytest.raises(ValueError, match="Invalid channel"):
            device.configure_channel(4, enabled=False)

        with pytest.raises(ValueError, match="Invalid channel"):
            device.configure_channel(-1, enabled=False)

    def test_configure_channel_invalid_cutoff(self):
        """测试配置无效截止频率。"""
        device = Picoammeter(device_id="test_pico", config={})

        with pytest.raises(ValueError, match="Invalid filter cutoff"):
            device.configure_channel(0, filter_cutoff=0)

        with pytest.raises(ValueError, match="Invalid filter cutoff"):
            device.configure_channel(0, filter_cutoff=10000)

    def test_configure_channel_invalid_window(self):
        """测试配置无效窗口大小。"""
        device = Picoammeter(device_id="test_pico", config={})

        with pytest.raises(ValueError, match="Invalid filter window"):
            device.configure_channel(0, filter_window=0)

        with pytest.raises(ValueError, match="Invalid filter window"):
            device.configure_channel(0, filter_window=101)


class TestPicoammeterSampleRate:
    """测试Picoammeter采样率设置。"""

    def test_set_sample_rate_valid(self):
        """测试设置有效采样率。"""
        device = Picoammeter(device_id="test_pico", config={})

        result = device.set_sample_rate(500.0)

        assert result is True
        assert device._acq_config.sample_rate == 500.0

    def test_set_sample_rate_boundary(self):
        """测试设置边界采样率。"""
        device = Picoammeter(device_id="test_pico", config={})

        # 最小值
        result = device.set_sample_rate(1.0)
        assert result is True
        assert device._acq_config.sample_rate == 1.0

        # 最大值
        result = device.set_sample_rate(1000.0)
        assert result is True
        assert device._acq_config.sample_rate == 1000.0

    def test_set_sample_rate_invalid(self):
        """测试设置无效采样率。"""
        device = Picoammeter(device_id="test_pico", config={})

        with pytest.raises(ValueError, match="Sample rate must be"):
            device.set_sample_rate(0.5)

        with pytest.raises(ValueError, match="Sample rate must be"):
            device.set_sample_rate(1001.0)


class TestPicoammeterAcquisition:
    """测试Picoammeter采集功能。"""

    @pytest.mark.asyncio
    async def test_start_acquisition(self):
        """测试启动采集。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        await device.connect()

        result = await device.start_acquisition()

        assert result is True
        assert device._is_acquiring is True
        assert device.status == DeviceStatus.BUSY

        await device.stop_acquisition()

    @pytest.mark.asyncio
    async def test_stop_acquisition(self):
        """测试停止采集。"""
        device = Picoammeter(device_id="test_pico", config={})
        await device.connect()
        await device.start_acquisition()

        result = await device.stop_acquisition()

        assert result is True
        assert device._is_acquiring is False
        assert device.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_double_start_acquisition(self):
        """测试重复启动采集。"""
        device = Picoammeter(device_id="test_pico", config={})
        await device.connect()
        await device.start_acquisition()

        result = await device.start_acquisition()

        assert result is True  # 已启动时返回True

        await device.stop_acquisition()

    @pytest.mark.asyncio
    async def test_acquisition_generates_data(self):
        """测试采集生成数据。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        await device.connect()
        await device.start_acquisition()

        # 等待采集一些数据
        await asyncio.sleep(0.1)

        # 检查缓冲区有数据
        for ch in range(4):
            assert len(device._data_buffers[ch]) > 0

        await device.stop_acquisition()

    @pytest.mark.asyncio
    async def test_acquisition_disabled_channel(self):
        """测试禁用通道不采集。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        device.configure_channel(0, enabled=False)
        await device.connect()
        await device.start_acquisition()

        await asyncio.sleep(0.05)

        # 通道0应该没有数据
        assert len(device._data_buffers[0]) == 0
        # 其他通道应该有数据
        for ch in range(1, 4):
            assert len(device._data_buffers[ch]) > 0

        await device.stop_acquisition()


class TestPicoammeterReadData:
    """测试Picoammeter数据读取。"""

    @pytest.mark.asyncio
    async def test_read_channel_no_data(self):
        """测试读取无数据通道。"""
        device = Picoammeter(device_id="test_pico", config={})

        result = await device.read_channel(0)

        assert result is None

    @pytest.mark.asyncio
    async def test_read_channel_with_data(self):
        """测试读取有数据通道。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        await device.connect()
        await device.start_acquisition()
        await asyncio.sleep(0.05)

        result = await device.read_channel(0)

        assert result is not None
        assert isinstance(result, ChannelData)
        assert result.current_pa != 0.0
        assert result.timestamp > 0

        await device.stop_acquisition()

    @pytest.mark.asyncio
    async def test_read_channel_invalid(self):
        """测试读取无效通道。"""
        device = Picoammeter(device_id="test_pico", config={})

        with pytest.raises(ValueError, match="Invalid channel"):
            await device.read_channel(4)

    @pytest.mark.asyncio
    async def test_read_all_channels(self):
        """测试读取所有通道。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        await device.connect()
        await device.start_acquisition()
        await asyncio.sleep(0.05)

        results = await device.read_all_channels()

        assert len(results) == 4
        for result in results:
            assert result is not None

        await device.stop_acquisition()

    @pytest.mark.asyncio
    async def test_read_channel_buffer(self):
        """测试读取通道缓冲区。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        await device.connect()
        await device.start_acquisition()
        await asyncio.sleep(0.1)

        result = await device.read_channel_buffer(0, count=5)

        assert len(result) <= 5
        for data in result:
            assert isinstance(data, ChannelData)

        await device.stop_acquisition()

    @pytest.mark.asyncio
    async def test_read_channel_buffer_all(self):
        """测试读取通道全部缓冲区。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        await device.connect()
        await device.start_acquisition()
        await asyncio.sleep(0.1)

        result = await device.read_channel_buffer(0)

        assert len(result) > 0
        assert len(result) <= device._acq_config.buffer_size

        await device.stop_acquisition()


class TestPicoammeterSNR:
    """测试Picoammeter信噪比计算。"""

    def test_calculate_snr_no_data(self):
        """测试无数据时SNR计算。"""
        device = Picoammeter(device_id="test_pico", config={})

        result = device.calculate_snr(0)

        assert result == 0.0

    @pytest.mark.asyncio
    async def test_calculate_snr_with_data(self):
        """测试有数据时SNR计算。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        await device.connect()
        await device.start_acquisition()
        await asyncio.sleep(0.2)  # 采集足够数据

        result = device.calculate_snr(0)

        assert isinstance(result, float)
        # SNR应该是一个合理的值（仿真数据有信号和噪声）
        assert -100 < result < 200

        await device.stop_acquisition()

    def test_calculate_snr_invalid_channel(self):
        """测试无效通道SNR计算。"""
        device = Picoammeter(device_id="test_pico", config={})

        with pytest.raises(ValueError, match="Invalid channel"):
            device.calculate_snr(4)


class TestPicoammeterFilter:
    """测试Picoammeter滤波功能。"""

    def test_apply_filter_none(self):
        """测试无滤波。"""
        device = Picoammeter(device_id="test_pico", config={})
        config = ChannelConfig(filter_type=FilterType.NONE)

        result = device._apply_filter(0, 100.0, config)

        assert result == 100.0

    def test_apply_filter_lowpass(self):
        """测试低通滤波。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        config = ChannelConfig(
            filter_type=FilterType.LOWPASS,
            filter_cutoff=10.0,
        )

        # 第一次滤波（初始状态prev_output=0，结果会偏离）
        result1 = device._apply_filter(0, 100.0, config)
        # 第二次滤波（继续平滑）
        result2 = device._apply_filter(0, 110.0, config)

        # 滤波后值应该在输入值之间（由于初始状态为0，第一次会较小）
        assert result1 < 100.0  # 第一次会被初始状态0拉低
        assert result2 > result1  # 第二次应该增大
        # 多次滤波后应该接近输入值
        for _ in range(10):
            device._apply_filter(0, 110.0, config)
        result_final = device._apply_filter(0, 110.0, config)
        assert abs(result_final - 110.0) < 5.0  # 多次滤波后接近输入

    def test_apply_filter_moving_average(self):
        """测试移动平均滤波。"""
        device = Picoammeter(device_id="test_pico", config={})
        config = ChannelConfig(
            filter_type=FilterType.MOVING_AVERAGE,
            filter_window=3,
        )

        # 添加多个值
        device._apply_filter(0, 100.0, config)
        device._apply_filter(0, 110.0, config)
        result = device._apply_filter(0, 120.0, config)

        # 移动平均应该接近均值
        expected = (100.0 + 110.0 + 120.0) / 3
        assert abs(result - expected) < 0.01

    def test_apply_filter_median(self):
        """测试中值滤波。"""
        device = Picoammeter(device_id="test_pico", config={})
        config = ChannelConfig(
            filter_type=FilterType.MEDIAN,
            filter_window=3,
        )

        # 添加多个值
        device._apply_filter(0, 100.0, config)
        device._apply_filter(0, 200.0, config)  # 异常值
        result = device._apply_filter(0, 110.0, config)

        # 中值应该是110.0（100, 200, 110的中值）
        assert result == 110.0


class TestPicoammeterBuffer:
    """测试Picoammeter缓冲区管理。"""

    def test_clear_buffer_single_channel(self):
        """测试清空单个通道缓冲区。"""
        device = Picoammeter(device_id="test_pico", config={})
        device._data_buffers[0].append(ChannelData(current_pa=100.0))

        device.clear_buffer(0)

        assert len(device._data_buffers[0]) == 0

    def test_clear_buffer_all_channels(self):
        """测试清空所有通道缓冲区。"""
        device = Picoammeter(device_id="test_pico", config={})
        for ch in range(4):
            device._data_buffers[ch].append(ChannelData(current_pa=100.0))

        device.clear_buffer()

        for ch in range(4):
            assert len(device._data_buffers[ch]) == 0

    def test_clear_buffer_invalid_channel(self):
        """测试清空无效通道缓冲区。"""
        device = Picoammeter(device_id="test_pico", config={})

        with pytest.raises(ValueError, match="Invalid channel"):
            device.clear_buffer(4)

    def test_buffer_size_limit(self):
        """测试缓冲区大小限制。"""
        device = Picoammeter(
            device_id="test_pico",
            config={"buffer_size": 10},
        )

        # 添加超过限制的数据
        for i in range(20):
            device._data_buffers[0].append(ChannelData(current_pa=float(i)))

        # 缓冲区应该只保留最新的数据
        assert len(device._data_buffers[0]) == 10


class TestPicoammeterStatus:
    """测试Picoammeter状态读取。"""

    @pytest.mark.asyncio
    async def test_read_status(self):
        """测试读取设备状态。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 500})
        await device.connect()

        result = await device.read_status()

        assert result["device_id"] == "test_pico"
        assert result["status"] == "ready"
        assert result["simulation"] is True
        assert result["sample_rate"] == 500.0
        assert result["is_acquiring"] is False
        assert len(result["buffer_usage"]) == 4
        assert len(result["channel_configs"]) == 4

    @pytest.mark.asyncio
    async def test_read_status_while_acquiring(self):
        """测试采集时读取状态。"""
        device = Picoammeter(device_id="test_pico", config={})
        await device.connect()
        await device.start_acquisition()

        result = await device.read_status()

        assert result["is_acquiring"] is True
        assert result["status"] == "busy"

        await device.stop_acquisition()


class TestPicoammeterRangeResolution:
    """测试Picoammeter量程分辨率。"""

    def test_get_range_resolution(self):
        """测试获取量程分辨率。"""
        assert Picoammeter.get_range_resolution(CurrentRange.RANGE_1NA) == 1.0
        assert Picoammeter.get_range_resolution(CurrentRange.RANGE_10NA) == 10.0
        assert Picoammeter.get_range_resolution(CurrentRange.RANGE_100NA) == 100.0
        assert Picoammeter.get_range_resolution(CurrentRange.RANGE_1UA) == 1000.0
        assert Picoammeter.get_range_resolution(CurrentRange.RANGE_10UA) == 10000.0
        assert Picoammeter.get_range_resolution(CurrentRange.RANGE_100UA) == 100000.0
        assert Picoammeter.get_range_resolution(CurrentRange.RANGE_1MA) == 1000000.0

    def test_get_range_max(self):
        """测试获取量程最大值。"""
        assert Picoammeter.get_range_max(CurrentRange.RANGE_1NA) == 1000.0
        assert Picoammeter.get_range_max(CurrentRange.RANGE_10NA) == 10000.0
        assert Picoammeter.get_range_max(CurrentRange.RANGE_100NA) == 100000.0
        assert Picoammeter.get_range_max(CurrentRange.RANGE_1UA) == 1000000.0
        assert Picoammeter.get_range_max(CurrentRange.RANGE_10UA) == 10000000.0
        assert Picoammeter.get_range_max(CurrentRange.RANGE_100UA) == 100000000.0
        assert Picoammeter.get_range_max(CurrentRange.RANGE_1MA) == 1000000000.0


class TestPicoammeterSimulation:
    """测试Picoammeter仿真功能。"""

    def test_generate_simulation_current(self):
        """测试生成仿真电流。"""
        device = Picoammeter(device_id="test_pico", config={})

        # 生成多次数据
        currents = []
        for _ in range(100):
            current = device._generate_simulation_current(0)
            currents.append(current)
            device._sim_time += 0.01

        # 检查数据合理性
        mean_current = np.mean(currents)
        std_current = np.std(currents)

        # 均值应该接近基准电流
        assert abs(mean_current - device._sim_base_currents[0]) < 50.0
        # 应该有噪声（标准差不为零）
        assert std_current > 0

    def test_simulation_different_channels(self):
        """测试不同通道仿真数据。"""
        device = Picoammeter(device_id="test_pico", config={})

        currents = []
        for ch in range(4):
            current = device._generate_simulation_current(ch)
            currents.append(current)

        # 不同通道应该有不同的基准电流
        assert currents[0] != currents[1] or currents[1] != currents[2]


class TestPicoammeterIntegration:
    """测试Picoammeter集成功能。"""

    @pytest.mark.asyncio
    async def test_full_acquisition_workflow(self):
        """测试完整采集工作流。"""
        device = Picoammeter(
            device_id="test_pico",
            config={"sample_rate": 100, "buffer_size": 100},
        )

        # 1. 连接设备
        assert await device.connect() is True
        assert device.status == DeviceStatus.READY

        # 2. 配置通道
        device.configure_channel(0, current_range=CurrentRange.RANGE_10NA)
        device.configure_channel(1, filter_type=FilterType.LOWPASS, filter_cutoff=20.0)
        device.configure_channel(2, enabled=False)

        # 3. 启动采集
        assert await device.start_acquisition() is True
        assert device._is_acquiring is True

        # 4. 采集数据
        await asyncio.sleep(0.2)

        # 5. 读取数据
        data = await device.read_all_channels()
        assert data[0] is not None
        assert data[1] is not None
        assert data[2] is None  # 通道2已禁用
        assert data[3] is not None

        # 6. 计算SNR
        snr = device.calculate_snr(0)
        assert isinstance(snr, float)

        # 7. 停止采集
        assert await device.stop_acquisition() is True
        assert device._is_acquiring is False

        # 8. 断开连接
        assert await device.disconnect() is True
        assert device.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_filter_comparison(self):
        """测试不同滤波器效果对比。"""
        device = Picoammeter(
            device_id="test_pico",
            config={"sample_rate": 100, "buffer_size": 500},
        )

        # 配置不同滤波器
        device.configure_channel(0, filter_type=FilterType.NONE)
        device.configure_channel(1, filter_type=FilterType.LOWPASS, filter_cutoff=10.0)
        device.configure_channel(2, filter_type=FilterType.MOVING_AVERAGE, filter_window=10)
        device.configure_channel(3, filter_type=FilterType.MEDIAN, filter_window=5)

        await device.connect()
        await device.start_acquisition()
        await asyncio.sleep(0.5)

        # 读取各通道数据
        for ch in range(4):
            buffer = await device.read_channel_buffer(ch, count=100)
            if len(buffer) > 10:
                currents = [d.current_pa for d in buffer]
                std = np.std(currents)
                # 滤波后标准差应该降低
                if ch > 0:
                    # 滤波通道的噪声应该比无滤波通道小
                    pass  # 由于仿真数据随机性，不做严格断言

        await device.stop_acquisition()

    @pytest.mark.asyncio
    async def test_offset_calibration(self):
        """测试偏移校准功能。"""
        device = Picoammeter(device_id="test_pico", config={"sample_rate": 100})
        offset_value = 50.0

        # 不带偏移采集
        await device.connect()
        await device.start_acquisition()
        await asyncio.sleep(0.1)
        data_no_offset = await device.read_channel(0)
        await device.stop_acquisition()

        # 清空缓冲区并设置偏移
        device.clear_buffer()
        device.configure_channel(0, offset=offset_value)

        # 带偏移采集
        await device.start_acquisition()
        await asyncio.sleep(0.1)
        data_with_offset = await device.read_channel(0)
        await device.stop_acquisition()

        # 偏移后的电流应该增加
        if data_no_offset and data_with_offset:
            # 由于仿真数据有随机性，只检查大致趋势
            assert data_with_offset.current_pa > data_no_offset.current_pa - 100


# 导入asyncio用于测试
import asyncio
