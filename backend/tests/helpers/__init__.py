"""
测试辅助工具模块

文件名: __init__.py
路径: backend/tests/helpers/
功能: 提供测试辅助工具的统一导出
作者: CAUC-SEP Team
创建日期: 2026-03-16
"""

from .assertions import (
    assert_response_success,
    assert_response_error,
    assert_device_status,
    assert_position_in_range,
    assert_calibration_valid,
    assert_response_status,
)
from .mock_factories import (
    create_mock_motor_status,
    create_mock_piezo_status,
    create_mock_electromagnet_status,
    create_mock_temperature_status,
    create_mock_ammeter_status,
    create_mock_device_response,
)
from .test_data import (
    create_test_user,
    create_test_experiment,
    create_test_device_config,
    generate_test_hysteresis_data,
    generate_test_temperature_ramp,
)

__all__ = [
    # 断言工具
    "assert_response_success",
    "assert_response_error",
    "assert_device_status",
    "assert_position_in_range",
    "assert_calibration_valid",
    "assert_response_status",
    # Mock工厂
    "create_mock_motor_status",
    "create_mock_piezo_status",
    "create_mock_electromagnet_status",
    "create_mock_temperature_status",
    "create_mock_ammeter_status",
    "create_mock_device_response",
    # 测试数据生成
    "create_test_user",
    "create_test_experiment",
    "create_test_device_config",
    "generate_test_hysteresis_data",
    "generate_test_temperature_ramp",
]
