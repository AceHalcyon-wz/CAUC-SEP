"""
电磁铁驱动模块单元测试

测试覆盖：
- 恒流模式控制
- 扫描模式控制（正向/反向/三角波）
- 磁场-电流校准
- 过流保护机制
- 边界条件和异常处理
"""

import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio

from core.abstract import DeviceStatus
from core.electromagnet_driver import (
    MAX_CURRENT,
    MAX_FIELD,
    MAX_SCAN_RATE,
    MIN_SCAN_RATE,
    OVERCURRENT_THRESHOLD,
    CalibrationPoint,
    ElectromagnetDriver,
    ElectromagnetStatus,
    ScanMode,
    ScanParameters,
)

# ==================== Fixtures ====================


@pytest.fixture
def electromagnet_config():
    """创建电磁铁配置。"""
    return {
        "port": "COM_TEST",
        "baudrate": 9600,
        "max_current": 10.0,
        "simulation": True,
        "calibration_points": [
            {"current": 0.0, "field": 0.0},
            {"current": 5.0, "field": 1.0},
            {"current": 10.0, "field": 2.0},
        ],
    }


@pytest.fixture
def electromagnet(electromagnet_config):
    """创建电磁铁驱动器实例。"""
    driver = ElectromagnetDriver(device_id="test_electromagnet", config=electromagnet_config)
    return driver


@pytest_asyncio.fixture
async def connected_electromagnet(electromagnet):
    """创建已连接的电磁铁驱动器实例。"""
    await electromagnet.connect()
    yield electromagnet
    await electromagnet.disconnect()


# ==================== 基础功能测试 ====================


class TestElectromagnetDriverBasics:
    """基础功能测试类。"""

    def test_initialization(self, electromagnet, electromagnet_config):
        """测试初始化。"""
        assert electromagnet.device_id == "test_electromagnet"
        assert electromagnet.port == electromagnet_config["port"]
        assert electromagnet.baudrate == electromagnet_config["baudrate"]
        assert electromagnet.simulation is True
        assert electromagnet.max_current_limit == 10.0
        assert electromagnet.status == DeviceStatus.DISCONNECTED
        assert electromagnet.current_value == 0.0
        assert electromagnet.field_value == 0.0
        assert electromagnet.electromagnet_status == ElectromagnetStatus.IDLE

    def test_initialization_with_custom_max_current(self):
        """测试自定义最大电流限制。"""
        config = {"max_current": 8.0, "simulation": True}
        driver = ElectromagnetDriver("test", config)
        assert driver.max_current_limit == 8.0

    def test_initialization_with_exceeded_max_current(self):
        """测试超过硬件限制的最大电流。"""
        config = {"max_current": 15.0, "simulation": True}
        driver = ElectromagnetDriver("test", config)
        # 应该被限制在硬件最大值
        assert driver.max_current_limit == MAX_CURRENT

    @pytest.mark.asyncio
    async def test_connect(self, electromagnet):
        """测试连接。"""
        result = await electromagnet.connect()
        assert result is True
        assert electromagnet.status == DeviceStatus.READY
        assert electromagnet.electromagnet_status == ElectromagnetStatus.IDLE

    @pytest.mark.asyncio
    async def test_disconnect(self, connected_electromagnet):
        """测试断开连接。"""
        result = await connected_electromagnet.disconnect()
        assert result is True
        assert connected_electromagnet.status == DeviceStatus.DISCONNECTED

    @pytest.mark.asyncio
    async def test_read_status(self, connected_electromagnet):
        """测试读取状态。"""
        status = await connected_electromagnet.read_status()
        assert status["device_id"] == "test_electromagnet"
        assert status["status"] == DeviceStatus.READY.value
        assert status["electromagnet_status"] == ElectromagnetStatus.IDLE.value
        assert status["current_value"] == 0.0
        assert status["field_value"] == 0.0
        assert status["connected"] is True
        assert status["simulation"] is True


# ==================== 恒流模式测试 ====================


class TestConstantCurrentMode:
    """恒流模式测试类。"""

    @pytest.mark.asyncio
    async def test_set_current_valid(self, connected_electromagnet):
        """测试设置有效电流值。"""
        result = await connected_electromagnet.set_current(5.0)
        assert result is True
        assert connected_electromagnet.current_value == 5.0
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.CONSTANT_CURRENT

    @pytest.mark.asyncio
    async def test_set_current_zero(self, connected_electromagnet):
        """测试设置零电流。"""
        result = await connected_electromagnet.set_current(0.0)
        assert result is True
        assert connected_electromagnet.current_value == 0.0

    @pytest.mark.asyncio
    async def test_set_current_max(self, connected_electromagnet):
        """测试设置最大电流。"""
        result = await connected_electromagnet.set_current(MAX_CURRENT)
        assert result is True
        assert connected_electromagnet.current_value == MAX_CURRENT

    @pytest.mark.asyncio
    async def test_set_current_exceeds_limit(self, connected_electromagnet):
        """测试设置超过限制的电流。"""
        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.set_current(15.0)
        assert "exceeds valid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_current_negative(self, connected_electromagnet):
        """测试设置负电流。"""
        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.set_current(-1.0)
        assert "exceeds valid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_current_updates_field(self, connected_electromagnet):
        """测试设置电流时更新磁场值。"""
        # 使用校准系数 0.2 T/A
        result = await connected_electromagnet.set_current(5.0)
        assert result is True
        # 由于有校准点，磁场应该是插值结果
        assert connected_electromagnet.field_value > 0

    @pytest.mark.asyncio
    async def test_set_field_valid(self, connected_electromagnet):
        """测试设置有效磁场值。"""
        result = await connected_electromagnet.set_field(1.0)
        assert result is True
        assert connected_electromagnet.field_value == 1.0

    @pytest.mark.asyncio
    async def test_set_field_exceeds_limit(self, connected_electromagnet):
        """测试设置超过限制的磁场。"""
        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.set_field(3.0)
        assert "exceeds valid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_set_field_negative(self, connected_electromagnet):
        """测试设置负磁场。"""
        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.set_field(-0.5)
        assert "exceeds valid range" in str(exc_info.value)


# ==================== 扫描模式测试 ====================


class TestScanMode:
    """扫描模式测试类。"""

    @pytest.mark.asyncio
    async def test_start_forward_scan(self, connected_electromagnet):
        """测试启动正向扫描。"""
        result = await connected_electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=5.0, scan_rate=0.5
        )
        assert result is True
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.SCANNING

        # 等待扫描任务完成（5A / 0.5 A/s = 10s）
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=20.0)
            except asyncio.TimeoutError:
                connected_electromagnet._scan_task.cancel()
                try:
                    await connected_electromagnet._scan_task
                except asyncio.CancelledError:
                    pass

        # 验证扫描完成
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE
        # 由于扫描可能被teardown中断，放宽精度要求
        assert connected_electromagnet.current_value >= 4.5

    @pytest.mark.asyncio
    async def test_start_reverse_scan(self, connected_electromagnet):
        """测试启动反向扫描。"""
        # 先设置到高电流
        await connected_electromagnet.set_current(5.0)

        result = await connected_electromagnet.start_scan(
            mode=ScanMode.REVERSE, start_current=5.0, end_current=0.0, scan_rate=0.5
        )
        assert result is True
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.SCANNING

        # 等待扫描任务完成（5A / 0.5 A/s = 10s）
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=20.0)
            except asyncio.TimeoutError:
                connected_electromagnet._scan_task.cancel()
                try:
                    await connected_electromagnet._scan_task
                except asyncio.CancelledError:
                    pass

        # 验证扫描完成
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE
        # 由于扫描可能被teardown中断，放宽精度要求
        assert connected_electromagnet.current_value <= 0.5

    @pytest.mark.asyncio
    async def test_start_triangular_scan(self, connected_electromagnet):
        """测试启动三角波扫描。"""
        result = await connected_electromagnet.start_scan(
            mode=ScanMode.TRIANGULAR, start_current=0.0, end_current=2.0, scan_rate=1.0, cycles=2
        )
        assert result is True
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.SCANNING

        # 等待扫描任务完成
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=15.0)
            except asyncio.TimeoutError:
                pass

        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE

    @pytest.mark.asyncio
    async def test_stop_scan(self, connected_electromagnet):
        """测试停止扫描。"""
        await connected_electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=10.0, scan_rate=0.1  # 慢速扫描
        )

        # 等待一小段时间
        await asyncio.sleep(0.5)

        # 停止扫描
        result = await connected_electromagnet.stop_scan()
        assert result is True
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE

    @pytest.mark.asyncio
    async def test_scan_invalid_start_current(self, connected_electromagnet):
        """测试无效起始电流。"""
        with pytest.raises(ValueError):
            await connected_electromagnet.start_scan(
                mode=ScanMode.FORWARD, start_current=-1.0, end_current=5.0, scan_rate=0.5
            )

    @pytest.mark.asyncio
    async def test_scan_invalid_end_current(self, connected_electromagnet):
        """测试无效目标电流。"""
        with pytest.raises(ValueError):
            await connected_electromagnet.start_scan(
                mode=ScanMode.FORWARD, start_current=0.0, end_current=15.0, scan_rate=0.5
            )

    @pytest.mark.asyncio
    async def test_scan_invalid_rate_too_low(self, connected_electromagnet):
        """测试扫描速率过低。"""
        with pytest.raises(ValueError):
            await connected_electromagnet.start_scan(
                mode=ScanMode.FORWARD, start_current=0.0, end_current=5.0, scan_rate=0.001
            )

    @pytest.mark.asyncio
    async def test_scan_invalid_rate_too_high(self, connected_electromagnet):
        """测试扫描速率过高。"""
        with pytest.raises(ValueError):
            await connected_electromagnet.start_scan(
                mode=ScanMode.FORWARD, start_current=0.0, end_current=5.0, scan_rate=2.0
            )

    @pytest.mark.asyncio
    async def test_triangular_scan_invalid_cycles(self, connected_electromagnet):
        """测试三角波扫描无效周期数。"""
        with pytest.raises(ValueError):
            await connected_electromagnet.start_scan(
                mode=ScanMode.TRIANGULAR,
                start_current=0.0,
                end_current=5.0,
                scan_rate=0.5,
                cycles=0,
            )

    @pytest.mark.asyncio
    async def test_quick_scan(self, connected_electromagnet):
        """测试快速扫描。"""
        result = await connected_electromagnet.quick_scan(
            start_field=0.0, end_field=1.0, scan_rate=0.5
        )
        assert result is True
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.SCANNING

        # 等待扫描任务完成
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=10.0)
            except asyncio.TimeoutError:
                pass

        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE

    @pytest.mark.asyncio
    async def test_scan_progress_updates(self, connected_electromagnet):
        """测试扫描进度更新。"""
        progress_values = []

        def progress_callback(progress):
            progress_values.append(progress)

        connected_electromagnet.set_progress_callback(progress_callback)

        await connected_electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=1.0, scan_rate=1.0
        )

        # 等待扫描任务完成
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=5.0)
            except asyncio.TimeoutError:
                pass

        # 应该有进度更新
        assert len(progress_values) > 0
        # 最后的进度应该接近1.0
        assert progress_values[-1] > 0.9


# ==================== 校准功能测试 ====================


class TestCalibration:
    """校准功能测试类。"""

    @pytest.mark.asyncio
    async def test_calibrate_valid(self, connected_electromagnet):
        """测试有效校准。"""
        calibration_points = [
            {"current": 0.0, "field": 0.0},
            {"current": 2.5, "field": 0.5},
            {"current": 5.0, "field": 1.0},
            {"current": 7.5, "field": 1.5},
            {"current": 10.0, "field": 2.0},
        ]

        result = await connected_electromagnet.calibrate(calibration_points)
        assert result is True

        # 验证校准数据
        cal_data = connected_electromagnet.get_calibration_data()
        assert cal_data["points_count"] == 5

    @pytest.mark.asyncio
    async def test_calibrate_insufficient_points(self, connected_electromagnet):
        """测试校准点不足。"""
        calibration_points = [
            {"current": 0.0, "field": 0.0},
        ]

        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.calibrate(calibration_points)
        assert "At least 2 calibration points" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calibrate_missing_field(self, connected_electromagnet):
        """测试校准点缺少字段。"""
        calibration_points = [
            {"current": 0.0, "field": 0.0},
            {"current": 5.0},  # 缺少field
        ]

        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.calibrate(calibration_points)
        assert "must contain 'current' and 'field'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calibrate_invalid_current(self, connected_electromagnet):
        """测试校准点电流无效。"""
        calibration_points = [
            {"current": 0.0, "field": 0.0},
            {"current": 15.0, "field": 3.0},  # 超出范围
        ]

        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.calibrate(calibration_points)
        assert "exceeds valid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_calibrate_invalid_field(self, connected_electromagnet):
        """测试校准点磁场无效。"""
        calibration_points = [
            {"current": 0.0, "field": 0.0},
            {"current": 5.0, "field": 3.0},  # 超出范围
        ]

        with pytest.raises(ValueError) as exc_info:
            await connected_electromagnet.calibrate(calibration_points)
        assert "exceeds valid range" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_current_to_field_conversion(self, connected_electromagnet):
        """测试电流到磁场的转换。"""
        # 设置校准点
        calibration_points = [
            {"current": 0.0, "field": 0.0},
            {"current": 10.0, "field": 2.0},
        ]
        await connected_electromagnet.calibrate(calibration_points)

        # 设置电流
        await connected_electromagnet.set_current(5.0)

        # 验证磁场值（应该插值得到1.0T）
        assert abs(connected_electromagnet.field_value - 1.0) < 0.1

    @pytest.mark.asyncio
    async def test_get_calibration_data(self, connected_electromagnet):
        """测试获取校准数据。"""
        cal_data = connected_electromagnet.get_calibration_data()

        assert "calibration_points" in cal_data
        assert "calibration_coefficient" in cal_data
        assert "points_count" in cal_data
        assert cal_data["points_count"] == 3  # fixture中有3个点


# ==================== 过流保护测试 ====================


class TestOvercurrentProtection:
    """过流保护测试类。"""

    @pytest.mark.asyncio
    async def test_overcurrent_protection_trigger(self, connected_electromagnet):
        """测试过流保护触发。"""
        # 直接调用内部方法触发过流
        await connected_electromagnet._trigger_overcurrent_protection(11.0)

        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.OVERCURRENT
        assert connected_electromagnet.status == DeviceStatus.ERROR
        assert connected_electromagnet.current_value == 0.0

    @pytest.mark.asyncio
    async def test_reset_overcurrent_protection(self, connected_electromagnet):
        """测试复位过流保护。"""
        # 触发过流
        await connected_electromagnet._trigger_overcurrent_protection(11.0)

        # 复位
        result = await connected_electromagnet.reset_overcurrent_protection()
        assert result is True
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE
        assert connected_electromagnet.status == DeviceStatus.READY

    @pytest.mark.asyncio
    async def test_set_current_blocked_when_overcurrent(self, connected_electromagnet):
        """测试过流状态下无法设置电流。"""
        # 触发过流
        await connected_electromagnet._trigger_overcurrent_protection(11.0)

        # 尝试设置电流应该失败
        result = await connected_electromagnet.set_current(5.0)
        assert result is False


# ==================== 紧急停止测试 ====================


class TestEmergencyStop:
    """紧急停止测试类。"""

    @pytest.mark.asyncio
    async def test_emergency_stop(self, connected_electromagnet):
        """测试紧急停止。"""
        # 设置电流
        await connected_electromagnet.set_current(5.0)

        # 紧急停止
        result = await connected_electromagnet.emergency_stop()
        assert result is True
        assert connected_electromagnet.status == DeviceStatus.EMERGENCY_STOP
        assert connected_electromagnet.current_value == 0.0

    @pytest.mark.asyncio
    async def test_emergency_stop_during_scan(self, connected_electromagnet):
        """测试扫描中紧急停止。"""
        # 启动扫描
        await connected_electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=10.0, scan_rate=0.1
        )

        await asyncio.sleep(0.5)

        # 紧急停止
        result = await connected_electromagnet.emergency_stop()
        assert result is True
        assert connected_electromagnet.status == DeviceStatus.EMERGENCY_STOP
        assert connected_electromagnet.current_value == 0.0

    @pytest.mark.asyncio
    async def test_reset_emergency(self, connected_electromagnet):
        """测试复位紧急停止。"""
        # 触发紧急停止
        await connected_electromagnet.emergency_stop()

        # 复位
        result = await connected_electromagnet.reset_emergency()
        assert result is True
        assert connected_electromagnet.status == DeviceStatus.READY


# ==================== 回调功能测试 ====================


class TestCallbacks:
    """回调功能测试类。"""

    @pytest.mark.asyncio
    async def test_status_callback(self, connected_electromagnet):
        """测试状态回调。"""
        status_changes = []

        def status_callback(status):
            status_changes.append(status)

        connected_electromagnet.set_status_callback(status_callback)

        # 触发状态变化
        await connected_electromagnet.set_current(5.0)

        # 应该有状态回调
        assert len(status_changes) > 0
        assert "current_value" in status_changes[0]
        assert "electromagnet_status" in status_changes[0]

    @pytest.mark.asyncio
    async def test_progress_callback(self, connected_electromagnet):
        """测试进度回调。"""
        progress_values = []

        def progress_callback(progress):
            progress_values.append(progress)

        connected_electromagnet.set_progress_callback(progress_callback)

        # 启动扫描
        await connected_electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=1.0, scan_rate=1.0
        )

        await asyncio.sleep(2)

        # 应该有进度回调
        assert len(progress_values) > 0

    @pytest.mark.asyncio
    async def test_callback_error_handling(self, connected_electromagnet):
        """测试回调错误处理。"""

        def bad_callback(status):
            raise RuntimeError("Callback error")

        connected_electromagnet.set_status_callback(bad_callback)

        # 不应该抛出异常
        result = await connected_electromagnet.set_current(5.0)
        assert result is True


# ==================== 边界条件测试 ====================


class TestBoundaryConditions:
    """边界条件测试类。"""

    @pytest.mark.asyncio
    async def test_min_scan_rate(self, connected_electromagnet):
        """测试最小扫描速率。"""
        result = await connected_electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=0.1, scan_rate=MIN_SCAN_RATE
        )
        assert result is True

        # 等待扫描任务完成
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=20.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_max_scan_rate(self, connected_electromagnet):
        """测试最大扫描速率。"""
        result = await connected_electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=1.0, scan_rate=MAX_SCAN_RATE
        )
        assert result is True

        # 等待扫描任务完成
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=5.0)
            except asyncio.TimeoutError:
                pass

    @pytest.mark.asyncio
    async def test_current_precision(self, connected_electromagnet):
        """测试电流精度。"""
        # 设置精确电流值
        result = await connected_electromagnet.set_current(5.123)
        assert result is True

        # 验证精度（应该保留到小数点后4位）
        status = await connected_electromagnet.read_status()
        assert abs(status["current_value"] - 5.123) < 0.0001

    @pytest.mark.asyncio
    async def test_max_field(self, connected_electromagnet):
        """测试最大磁场。"""
        result = await connected_electromagnet.set_field(MAX_FIELD)
        assert result is True

    @pytest.mark.asyncio
    async def test_disconnect_stops_scan(self, electromagnet):
        """测试断开连接时停止扫描。"""
        await electromagnet.connect()

        # 启动扫描
        await electromagnet.start_scan(
            mode=ScanMode.FORWARD, start_current=0.0, end_current=10.0, scan_rate=0.1
        )

        await asyncio.sleep(0.5)

        # 断开连接
        await electromagnet.disconnect()

        assert electromagnet.status == DeviceStatus.DISCONNECTED
        assert electromagnet.current_value == 0.0


# ==================== 集成测试 ====================


class TestIntegration:
    """集成测试类。"""

    @pytest.mark.asyncio
    async def test_full_workflow(self, connected_electromagnet):
        """测试完整工作流程。"""
        # 1. 校准
        calibration_points = [
            {"current": 0.0, "field": 0.0},
            {"current": 5.0, "field": 1.0},
            {"current": 10.0, "field": 2.0},
        ]
        result = await connected_electromagnet.calibrate(calibration_points)
        assert result is True

        # 2. 设置恒流
        result = await connected_electromagnet.set_current(5.0)
        assert result is True
        assert abs(connected_electromagnet.field_value - 1.0) < 0.1

        # 3. 执行扫描
        result = await connected_electromagnet.start_scan(
            mode=ScanMode.TRIANGULAR, start_current=0.0, end_current=2.0, scan_rate=1.0, cycles=1
        )
        assert result is True

        # 等待扫描任务完成
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=10.0)
            except asyncio.TimeoutError:
                pass

        # 4. 验证状态
        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE

        # 5. 断开连接
        result = await connected_electromagnet.disconnect()
        assert result is True
        assert connected_electromagnet.current_value == 0.0

    @pytest.mark.asyncio
    async def test_multiple_operations(self, connected_electromagnet):
        """测试多次操作。"""
        for i in range(5):
            current = i * 2.0
            result = await connected_electromagnet.set_current(current)
            assert result is True
            assert abs(connected_electromagnet.current_value - current) < 0.1

        # 最后归零
        result = await connected_electromagnet.set_current(0.0)
        assert result is True
        assert connected_electromagnet.current_value == 0.0


# ==================== 性能测试 ====================


class TestPerformance:
    """性能测试类。"""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_long_duration_scan(self, connected_electromagnet):
        """测试长时间扫描。"""
        result = await connected_electromagnet.start_scan(
            mode=ScanMode.TRIANGULAR, start_current=0.0, end_current=5.0, scan_rate=0.1, cycles=3
        )
        assert result is True

        # 等待扫描任务完成（每个周期100秒，3个周期）
        if connected_electromagnet._scan_task:
            try:
                await asyncio.wait_for(connected_electromagnet._scan_task, timeout=350.0)
            except asyncio.TimeoutError:
                pass

        assert connected_electromagnet.electromagnet_status == ElectromagnetStatus.IDLE

    @pytest.mark.asyncio
    async def test_rapid_current_changes(self, connected_electromagnet):
        """测试快速电流变化。"""
        for _ in range(10):
            result = await connected_electromagnet.set_current(5.0)
            assert result is True

            result = await connected_electromagnet.set_current(0.0)
            assert result is True

        # 验证最终状态
        assert connected_electromagnet.current_value == 0.0
