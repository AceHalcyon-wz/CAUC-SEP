"""
测试断言工具模块

文件名: assertions.py
路径: backend/tests/helpers/
功能: 提供语义化的测试断言函数，提高测试可读性
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest

使用方法:
    from tests.helpers import assert_response_success, assert_device_status

    def test_api():
        response = client.get("/api/v1/motor/status")
        assert_response_success(response)
        assert_device_status(response, "ready")
"""

from typing import Any


def assert_response_success(response: Any, message: str = "") -> None:
    """断言API响应成功。

    Args:
        response: HTTP响应对象
        message: 自定义错误消息

    Raises:
        AssertionError: 响应状态码不为200或success不为True
    """
    assert response.status_code == 200, (
        f"期望状态码200，实际为{response.status_code}。{message}"
    )
    data = response.json()
    if "success" in data:
        assert data["success"] is True, (
            f"期望success=True，实际为{data.get('success')}。{message}"
        )


def assert_response_error(
    response: Any, expected_status: int = 400, message: str = ""
) -> None:
    """断言API响应错误。

    Args:
        response: HTTP响应对象
        expected_status: 期望的错误状态码
        message: 自定义错误消息

    Raises:
        AssertionError: 响应状态码不符合预期
    """
    assert response.status_code == expected_status, (
        f"期望状态码{expected_status}，实际为{response.status_code}。{message}"
    )


def assert_response_status(response: Any, expected_status: int, message: str = "") -> None:
    """断言API响应状态码。

    Args:
        response: HTTP响应对象
        expected_status: 期望的状态码
        message: 自定义错误消息

    Raises:
        AssertionError: 响应状态码不符合预期
    """
    assert response.status_code == expected_status, (
        f"期望状态码{expected_status}，实际为{response.status_code}。{message}"
    )


def assert_device_status(response: Any, expected_status: str, message: str = "") -> None:
    """断言设备状态。

    Args:
        response: HTTP响应对象
        expected_status: 期望的设备状态
        message: 自定义错误消息

    Raises:
        AssertionError: 设备状态不符合预期
    """
    data = response.json()
    actual_status = data.get("status", data.get("device_status", data.get("electromagnet_status")))
    assert actual_status == expected_status, (
        f"期望设备状态'{expected_status}'，实际为'{actual_status}'。{message}"
    )


def assert_position_in_range(
    response: Any, min_value: float, max_value: float, message: str = ""
) -> None:
    """断言位置在有效范围内。

    Args:
        response: HTTP响应对象
        min_value: 最小位置值
        max_value: 最大位置值
        message: 自定义错误消息

    Raises:
        AssertionError: 位置超出范围
    """
    data = response.json()
    position = data.get("position_mm", data.get("position", data.get("current_position")))
    assert position is not None, f"响应中未找到位置字段。{message}"
    assert min_value <= position <= max_value, (
        f"位置{position}超出范围[{min_value}, {max_value}]。{message}"
    )


def assert_calibration_valid(response: Any, message: str = "") -> None:
    """断言校准有效。

    Args:
        response: HTTP响应对象
        message: 自定义错误消息

    Raises:
        AssertionError: 校准无效
    """
    data = response.json()
    calibration_valid = data.get("calibration_valid", data.get("valid"))
    assert calibration_valid is True, (
        f"期望校准有效，实际为{calibration_valid}。{message}"
    )


def assert_field_value(response: Any, field: str, expected_value: Any, message: str = "") -> None:
    """断言响应字段值。

    Args:
        response: HTTP响应对象
        field: 字段名
        expected_value: 期望值
        message: 自定义错误消息

    Raises:
        AssertionError: 字段值不符合预期
    """
    data = response.json()
    actual_value = data.get(field)
    assert actual_value == expected_value, (
        f"字段'{field}'期望值{expected_value}，实际为{actual_value}。{message}"
    )


def assert_field_exists(response: Any, field: str, message: str = "") -> None:
    """断言响应包含指定字段。

    Args:
        response: HTTP响应对象
        field: 字段名
        message: 自定义错误消息

    Raises:
        AssertionError: 字段不存在
    """
    data = response.json()
    assert field in data, f"响应中未找到字段'{field}'。{message}"


def assert_fields_exist(response: Any, fields: list[str], message: str = "") -> None:
    """断言响应包含多个指定字段。

    Args:
        response: HTTP响应对象
        fields: 字段名列表
        message: 自定义错误消息

    Raises:
        AssertionError: 任一字段不存在
    """
    data = response.json()
    missing_fields = [f for f in fields if f not in data]
    assert not missing_fields, (
        f"响应中缺少字段: {missing_fields}。{message}"
    )


def assert_list_not_empty(response: Any, list_field: str = "items", message: str = "") -> None:
    """断言列表字段不为空。

    Args:
        response: HTTP响应对象
        list_field: 列表字段名
        message: 自定义错误消息

    Raises:
        AssertionError: 列表为空
    """
    data = response.json()
    items = data.get(list_field, [])
    assert len(items) > 0, f"列表'{list_field}'为空。{message}"


def assert_count_greater_than(
    response: Any, count_field: str = "count", min_count: int = 0, message: str = ""
) -> None:
    """断言计数大于指定值。

    Args:
        response: HTTP响应对象
        count_field: 计数字段名
        min_count: 最小计数
        message: 自定义错误消息

    Raises:
        AssertionError: 计数不符合预期
    """
    data = response.json()
    count = data.get(count_field, 0)
    assert count > min_count, (
        f"计数{count}不大于{min_count}。{message}"
    )
