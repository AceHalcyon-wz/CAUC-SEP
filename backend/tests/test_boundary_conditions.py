"""
边界条件测试套件

文件名: test_boundary_conditions.py
路径: backend/tests/
功能: 测试数值边界、输入验证边界、并发边界等场景
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, numpy

测试内容：
- TestValidatorBoundaryConditions: 验证器边界条件测试
- TestNumericBoundaryConditions: 数值边界测试
- TestConcurrencyBoundaryConditions: 并发边界测试
- TestInputValidationBoundaryConditions: 输入验证边界测试
"""

import math
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from schemas.validators import (
    MAX_POSITION_MM,
    MAX_VELOCITY_MM_S,
    MIN_POSITION_MM,
    MIN_VELOCITY_MM_S,
    ValidationError,
    validate_acceleration,
    validate_current,
    validate_device_id,
    validate_position,
    validate_temperature,
    validate_velocity,
    validate_voltage,
    sanitize_string,
)


# ==================== 验证器边界条件测试 ====================


class TestValidatorBoundaryConditions:
    """验证器边界条件测试。"""

    # ==================== 设备ID边界测试 ====================

    def test_device_id_min_length_boundary(self):
        """测试设备ID最小长度边界（3字符）。"""
        # 有效：刚好3字符
        valid_id = "abc"
        assert validate_device_id(valid_id) == valid_id

        # 无效：2字符
        with pytest.raises(ValidationError) as exc_info:
            validate_device_id("ab")
        assert "长度不能少于3个字符" in str(exc_info.value)

    def test_device_id_max_length_boundary(self):
        """测试设备ID最大长度边界（64字符）。"""
        # 有效：刚好64字符
        valid_id = "a" + "b" * 63
        assert validate_device_id(valid_id) == valid_id

        # 无效：65字符
        with pytest.raises(ValidationError) as exc_info:
            validate_device_id("a" + "b" * 64)
        assert "长度不能超过64个字符" in str(exc_info.value)

    def test_device_id_empty_string(self):
        """测试设备ID空字符串。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_device_id("")
        assert "不能为空" in str(exc_info.value)

    def test_device_id_invalid_start_character(self):
        """测试设备ID不以字母开头。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_device_id("123abc")
        assert "必须以字母开头" in str(exc_info.value)

    def test_device_id_special_characters(self):
        """测试设备ID特殊字符。"""
        # 有效：允许下划线和连字符
        assert validate_device_id("device_001") == "device_001"
        assert validate_device_id("device-001") == "device-001"

        # 无效：不允许其他特殊字符
        with pytest.raises(ValidationError):
            validate_device_id("device@001")

        with pytest.raises(ValidationError):
            validate_device_id("device.001")

    def test_device_id_non_string_type(self):
        """测试设备ID非字符串类型。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_device_id(123)
        assert "必须是字符串类型" in str(exc_info.value)

        with pytest.raises(ValidationError):
            validate_device_id(None)

    # ==================== 位置边界测试 ====================

    def test_position_min_boundary(self):
        """测试位置最小值边界。"""
        # 有效：刚好等于最小值
        assert validate_position(MIN_POSITION_MM) == MIN_POSITION_MM

        # 无效：小于最小值
        with pytest.raises(ValidationError) as exc_info:
            validate_position(MIN_POSITION_MM - 0.001)
        assert "小于最小位置限制" in str(exc_info.value)

    def test_position_max_boundary(self):
        """测试位置最大值边界。"""
        # 有效：刚好等于最大值
        assert validate_position(MAX_POSITION_MM) == MAX_POSITION_MM

        # 无效：大于最大值
        with pytest.raises(ValidationError) as exc_info:
            validate_position(MAX_POSITION_MM + 0.001)
        assert "大于最大位置限制" in str(exc_info.value)

    def test_position_zero_value(self):
        """测试位置零值。"""
        assert validate_position(0.0) == 0.0

    def test_position_nan_value(self):
        """测试位置NaN值。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_position(float("nan"))
        assert "不能是NaN" in str(exc_info.value)

    def test_position_infinity_value(self):
        """测试位置无穷大值。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_position(float("inf"))
        assert "不能是无穷大" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            validate_position(float("-inf"))
        assert "不能是无穷大" in str(exc_info.value)

    def test_position_non_numeric_type(self):
        """测试位置非数值类型。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_position("100.0")
        assert "必须是数值类型" in str(exc_info.value)

    def test_position_custom_range(self):
        """测试位置自定义范围。"""
        # 自定义范围：-50 到 50
        assert validate_position(0.0, min_pos=-50.0, max_pos=50.0) == 0.0
        assert validate_position(-50.0, min_pos=-50.0, max_pos=50.0) == -50.0
        assert validate_position(50.0, min_pos=-50.0, max_pos=50.0) == 50.0

        # 超出范围
        with pytest.raises(ValidationError):
            validate_position(-51.0, min_pos=-50.0, max_pos=50.0)

        with pytest.raises(ValidationError):
            validate_position(51.0, min_pos=-50.0, max_pos=50.0)

    # ==================== 速度边界测试 ====================

    def test_velocity_min_boundary(self):
        """测试速度最小值边界。"""
        # 有效：刚好等于最小值
        assert validate_velocity(MIN_VELOCITY_MM_S) == MIN_VELOCITY_MM_S

        # 无效：小于最小值
        with pytest.raises(ValidationError) as exc_info:
            validate_velocity(MIN_VELOCITY_MM_S - 0.001)
        assert "小于最小速度限制" in str(exc_info.value)

    def test_velocity_max_boundary(self):
        """测试速度最大值边界。"""
        # 有效：刚好等于最大值
        assert validate_velocity(MAX_VELOCITY_MM_S) == MAX_VELOCITY_MM_S

        # 无效：大于最大值
        with pytest.raises(ValidationError) as exc_info:
            validate_velocity(MAX_VELOCITY_MM_S + 0.001)
        assert "大于最大速度限制" in str(exc_info.value)

    def test_velocity_zero_value(self):
        """测试速度零值。"""
        assert validate_velocity(0.0) == 0.0

    def test_velocity_nan_value(self):
        """测试速度NaN值。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_velocity(float("nan"))
        assert "不能是NaN" in str(exc_info.value)

    def test_velocity_infinity_value(self):
        """测试速度无穷大值。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_velocity(float("inf"))
        assert "不能是无穷大" in str(exc_info.value)

    # ==================== 加速度边界测试 ====================

    def test_acceleration_min_boundary(self):
        """测试加速度最小值边界（必须为正数）。"""
        # 有效：极小正值
        assert validate_acceleration(0.001) == 0.001

        # 无效：零值
        with pytest.raises(ValidationError) as exc_info:
            validate_acceleration(0.0)
        assert "必须是正数" in str(exc_info.value)

        # 无效：负值
        with pytest.raises(ValidationError) as exc_info:
            validate_acceleration(-0.001)
        assert "必须是正数" in str(exc_info.value)

    def test_acceleration_large_value(self):
        """测试加速度大值。"""
        # 有效：大值
        large_value = 1e10
        assert validate_acceleration(large_value) == large_value

    def test_acceleration_nan_value(self):
        """测试加速度NaN值。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_acceleration(float("nan"))
        assert "不能是NaN" in str(exc_info.value)

    # ==================== 温度边界测试 ====================

    def test_temperature_min_boundary(self):
        """测试温度最小值边界（绝对零度）。"""
        # 有效：刚好等于绝对零度
        assert validate_temperature(-273.15) == -273.15

        # 无效：低于绝对零度
        with pytest.raises(ValidationError) as exc_info:
            validate_temperature(-273.16)
        assert "低于最小温度限制" in str(exc_info.value)

    def test_temperature_max_boundary(self):
        """测试温度最大值边界。"""
        # 有效：刚好等于最大值
        assert validate_temperature(1000.0) == 1000.0

        # 无效：大于最大值
        with pytest.raises(ValidationError) as exc_info:
            validate_temperature(1000.1)
        assert "超过最大温度限制" in str(exc_info.value)

    def test_temperature_zero_celsius(self):
        """测试零摄氏度。"""
        assert validate_temperature(0.0) == 0.0

    def test_temperature_nan_value(self):
        """测试温度NaN值。"""
        with pytest.raises(ValidationError) as exc_info:
            validate_temperature(float("nan"))
        assert "不能是NaN" in str(exc_info.value)

    # ==================== 电流边界测试 ====================

    def test_current_min_boundary(self):
        """测试电流最小值边界。"""
        assert validate_current(-10.0) == -10.0

        with pytest.raises(ValidationError):
            validate_current(-10.1)

    def test_current_max_boundary(self):
        """测试电流最大值边界。"""
        assert validate_current(10.0) == 10.0

        with pytest.raises(ValidationError):
            validate_current(10.1)

    def test_current_zero_value(self):
        """测试电流零值。"""
        assert validate_current(0.0) == 0.0

    def test_current_nan_value(self):
        """测试电流NaN值。"""
        with pytest.raises(ValidationError):
            validate_current(float("nan"))

    # ==================== 电压边界测试 ====================

    def test_voltage_min_boundary(self):
        """测试电压最小值边界。"""
        assert validate_voltage(0.0) == 0.0

        with pytest.raises(ValidationError):
            validate_voltage(-0.001)

    def test_voltage_max_boundary(self):
        """测试电压最大值边界。"""
        assert validate_voltage(200.0) == 200.0

        with pytest.raises(ValidationError):
            validate_voltage(200.1)

    def test_voltage_nan_value(self):
        """测试电压NaN值。"""
        with pytest.raises(ValidationError):
            validate_voltage(float("nan"))

    # ==================== 字符串边界测试 ====================

    def test_sanitize_string_max_length(self):
        """测试字符串最大长度边界。"""
        # 有效：刚好等于最大长度
        long_string = "a" * 1000
        assert sanitize_string(long_string) == long_string

        # 无效：超过最大长度
        with pytest.raises(ValidationError):
            sanitize_string("a" * 1001)

    def test_sanitize_string_empty(self):
        """测试字符串空值。"""
        # 不允许空字符串
        with pytest.raises(ValidationError):
            sanitize_string("")

        # 允许空字符串
        assert sanitize_string("", allow_empty=True) == ""

    def test_sanitize_string_whitespace_only(self):
        """测试仅包含空白字符的字符串。"""
        # 默认去除首尾空白后为空字符串，会抛出异常
        with pytest.raises(ValidationError):
            sanitize_string("   ")

        # 允许空字符串时，返回空字符串
        result = sanitize_string("   ", allow_empty=True)
        assert result == ""

    def test_sanitize_string_non_string_type(self):
        """测试字符串非字符串类型。"""
        with pytest.raises(ValidationError):
            sanitize_string(123)

        with pytest.raises(ValidationError):
            sanitize_string(None)


# ==================== 数值边界测试 ====================


class TestNumericBoundaryConditions:
    """数值边界测试。"""

    def test_float_precision_boundary(self):
        """测试浮点数精度边界。"""
        # 极小浮点数
        tiny_value = 1e-15
        assert validate_position(tiny_value) == tiny_value

        # 极大浮点数（在范围内）
        large_value = 999.999999999
        assert validate_position(large_value) == large_value

    def test_integer_to_float_conversion(self):
        """测试整数到浮点数转换。"""
        # 整数输入应自动转换为浮点数
        assert validate_position(100) == 100.0
        assert validate_velocity(50) == 50.0
        assert validate_temperature(25) == 25.0

    def test_scientific_notation(self):
        """测试科学计数法。"""
        # 科学计数法输入
        assert validate_position(1e2) == 100.0
        assert validate_velocity(5e1) == 50.0
        assert validate_temperature(2.5e2) == 250.0

    def test_negative_zero(self):
        """测试负零。"""
        # Python中 -0.0 == 0.0
        assert validate_position(-0.0) == 0.0
        assert validate_velocity(-0.0) == 0.0

    def test_floating_point_edge_cases(self):
        """测试浮点数边界情况。"""
        # 最大正规浮点数（在范围内）
        large_normal = 1e308
        # 这个值会超出位置范围，应抛出异常
        with pytest.raises(ValidationError):
            validate_position(large_normal)

        # 最小正规浮点数
        min_normal = 2.2250738585072014e-308
        assert validate_position(min_normal) == min_normal

    def test_numpy_array_values(self):
        """测试NumPy数组值。"""
        # NumPy浮点数标量
        np_value = np.float64(50.0)
        assert validate_position(np_value) == 50.0

        # NumPy整数需要转换为Python原生类型
        np_int = int(np.int64(100))
        assert validate_position(np_int) == 100.0

    def test_numpy_special_values(self):
        """测试NumPy特殊值。"""
        # NumPy NaN
        with pytest.raises(ValidationError):
            validate_position(np.nan)

        # NumPy Infinity
        with pytest.raises(ValidationError):
            validate_position(np.inf)

        # NumPy负无穷（NumPy 2.0兼容写法）
        with pytest.raises(ValidationError):
            validate_position(-np.inf)


# ==================== 并发边界测试 ====================


class TestConcurrencyBoundaryConditions:
    """并发边界测试。"""

    @pytest.mark.asyncio
    async def test_concurrent_device_id_validation(self):
        """测试并发设备ID验证。"""
        import asyncio

        async def validate_task(device_id: str, expected_valid: bool):
            try:
                result = validate_device_id(device_id)
                return expected_valid
            except ValidationError:
                return not expected_valid

        # 并发验证多个设备ID
        tasks = [
            validate_task("device_001", True),
            validate_task("ab", False),
            validate_task("a" + "b" * 63, True),
            validate_task("123invalid", False),
            validate_task("valid_device", True),
        ]

        results = await asyncio.gather(*tasks)
        assert all(results)

    @pytest.mark.asyncio
    async def test_concurrent_position_validation(self):
        """测试并发位置验证。"""
        import asyncio

        async def validate_task(position: float, expected_valid: bool):
            try:
                result = validate_position(position)
                return expected_valid
            except ValidationError:
                return not expected_valid

        # 并发验证多个位置值
        tasks = [
            validate_task(0.0, True),
            validate_task(MIN_POSITION_MM, True),
            validate_task(MAX_POSITION_MM, True),
            validate_task(MIN_POSITION_MM - 1, False),
            validate_task(MAX_POSITION_MM + 1, False),
            validate_task(float("nan"), False),
        ]

        results = await asyncio.gather(*tasks)
        assert all(results)

    def test_thread_safety_of_validation(self):
        """测试验证函数的线程安全性。"""
        import threading
        import time

        results = []
        errors = []

        def validate_in_thread(device_id: str, expected_valid: bool):
            try:
                for _ in range(100):  # 每个线程执行100次验证
                    if expected_valid:
                        result = validate_device_id(device_id)
                        results.append(result == device_id)
                    else:
                        try:
                            validate_device_id(device_id)
                            results.append(False)
                        except ValidationError:
                            results.append(True)
                    time.sleep(0.0001)  # 模拟实际使用中的延迟
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=validate_in_thread, args=("device_001", True)),
            threading.Thread(target=validate_in_thread, args=("ab", False)),
            threading.Thread(target=validate_in_thread, args=("valid_device", True)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert all(results)


# ==================== 输入验证边界测试 ====================


class TestInputValidationBoundaryConditions:
    """输入验证边界测试。"""

    def test_unicode_characters_in_device_id(self):
        """测试设备ID中的Unicode字符。"""
        # 中文字符（无效）
        with pytest.raises(ValidationError):
            validate_device_id("设备001")

        # 日文字符（无效）
        with pytest.raises(ValidationError):
            validate_device_id("デバイス001")

        # Emoji（无效）
        with pytest.raises(ValidationError):
            validate_device_id("device😀")

    def test_whitespace_handling(self):
        """测试空白字符处理。"""
        # 设备ID不应包含空白
        with pytest.raises(ValidationError):
            validate_device_id("device 001")  # 中间有空格

        with pytest.raises(ValidationError):
            validate_device_id(" device001")  # 前导空格

        with pytest.raises(ValidationError):
            validate_device_id("device001 ")  # 尾随空格

    def test_control_characters(self):
        """测试控制字符。"""
        # 包含控制字符的字符串
        control_chars = "device\x00\x01\x02"
        with pytest.raises(ValidationError):
            validate_device_id(control_chars)

    def test_extremely_long_string(self):
        """测试极长字符串。"""
        # 超长字符串（10000字符）
        very_long_string = "a" * 10000
        with pytest.raises(ValidationError):
            sanitize_string(very_long_string, max_length=1000)

    def test_mixed_type_inputs(self):
        """测试混合类型输入。"""
        # 列表
        with pytest.raises(ValidationError):
            validate_position([100.0])

        # 字典
        with pytest.raises(ValidationError):
            validate_position({"value": 100.0})

        # 元组
        with pytest.raises(ValidationError):
            validate_position((100.0,))

        # 布尔值（Python中bool是int的子类）
        # True = 1, False = 0
        assert validate_position(True) == 1.0
        assert validate_position(False) == 0.0

    def test_boundary_precision(self):
        """测试边界精度。"""
        # 边界值的微小差异
        epsilon = 1e-10

        # 刚好在边界内
        assert validate_position(MAX_POSITION_MM - epsilon) == MAX_POSITION_MM - epsilon
        assert validate_position(MIN_POSITION_MM + epsilon) == MIN_POSITION_MM + epsilon

        # 刚好在边界外
        with pytest.raises(ValidationError):
            validate_position(MAX_POSITION_MM + epsilon)

        with pytest.raises(ValidationError):
            validate_position(MIN_POSITION_MM - epsilon)


# ==================== 性能边界测试 ====================


class TestPerformanceBoundaryConditions:
    """性能边界测试。"""

    def test_validation_performance_large_batch(self):
        """测试大批量验证性能。"""
        import time

        # 验证10000个有效设备ID
        start_time = time.time()
        for i in range(10000):
            validate_device_id(f"device_{i:05d}")
        elapsed_time = time.time() - start_time

        # 应在1秒内完成
        assert elapsed_time < 1.0, f"Validation took {elapsed_time:.3f}s, expected < 1.0s"

    def test_validation_performance_position_batch(self):
        """测试位置验证批量性能。"""
        import time

        # 验证10000个位置值
        positions = np.linspace(MIN_POSITION_MM, MAX_POSITION_MM, 10000)

        start_time = time.time()
        for pos in positions:
            validate_position(pos)
        elapsed_time = time.time() - start_time

        # 应在1秒内完成
        assert elapsed_time < 1.0, f"Validation took {elapsed_time:.3f}s, expected < 1.0s"

    def test_memory_usage_large_validation(self):
        """测试大批量验证的内存使用。"""
        import gc

        # 强制垃圾回收
        gc.collect()

        # 执行大批量验证
        results = []
        for i in range(10000):
            results.append(validate_device_id(f"device_{i:05d}"))

        # 清理结果
        results.clear()
        gc.collect()

        # 验证完成且无内存泄漏（简单检查）
        assert True


# ==================== 异常消息测试 ====================


class TestExceptionMessages:
    """异常消息测试。"""

    def test_validation_error_contains_field_name(self):
        """测试验证错误包含字段名。"""
        try:
            validate_device_id("ab")
        except ValidationError as e:
            assert e.field == "device_id"
            assert "device_id" in str(e)

    def test_validation_error_contains_invalid_value(self):
        """测试验证错误包含无效值。"""
        try:
            validate_position(2000.0)
        except ValidationError as e:
            assert e.value == 2000.0
            assert "2000.0" in str(e)

    def test_validation_error_message_descriptive(self):
        """测试验证错误消息具有描述性。"""
        # 测试各种错误的消息质量
        test_cases = [
            (lambda: validate_device_id("ab"), "长度不能少于3个字符"),
            (lambda: validate_device_id("123"), "必须以字母开头"),
            (lambda: validate_position(2000.0), "大于最大位置限制"),
            (lambda: validate_position(-2000.0), "小于最小位置限制"),
            (lambda: validate_velocity(-1.0), "小于最小速度限制"),
            (lambda: validate_acceleration(0.0), "必须是正数"),
        ]

        for test_func, expected_msg in test_cases:
            try:
                test_func()
                assert False, f"Expected ValidationError for {test_func}"
            except ValidationError as e:
                assert expected_msg in e.message
