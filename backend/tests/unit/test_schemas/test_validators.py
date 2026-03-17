"""
Pydantic 数据模型验证器测试

文件名: test_validators.py
路径: backend/tests/unit/schemas/
功能: 测试 schemas 模块中的 Pydantic 数据模型验证器
作者: CAUC-SEP Team
创建日期: 2026-03-16
依赖: pytest, pydantic

测试内容：
- TestMoveRequestValidation: 运动请求验证测试
- TestJogRequestValidation: JOG 请求验证测试
- TestLimitConfigRequestValidation: 限位配置验证测试
- TestPRPathConfigRequestValidation: PR 路径配置验证测试
- TestCommonResponseModels: 通用响应模型测试
- TestErrorCodeEnum: 错误码枚举测试
"""

import pytest
from pydantic import ValidationError

from schemas.motor import (
    AlarmCodeResponse,
    CommunicationConfigRequest,
    CommunicationConfigReadResponse,
    DriverSoftLimitRequest,
    DriverSoftLimitReadResponse,
    HomeRequest,
    JogRequest,
    LimitConfigRequest,
    MoveRequest,
    MoveResponse,
    MotorStatusResponse,
    PRPathConfigRequest,
    PRPathTriggerRequest,
    StatusWordResponse,
)
from schemas.common import (
    ErrorCode,
    ErrorResponse,
    SuccessResponse,
    ValidationErrorDetail,
    ValidationErrorResponse,
)


# ==================== MoveRequest 验证测试 ====================


class TestMoveRequestValidation:
    """运动请求验证测试。"""

    def test_valid_move_request(self):
        """测试有效的运动请求。"""
        request = MoveRequest(
            position_mm=10.0,
            velocity_mm_s=5.0,
            accel_mm_s2=500.0,
            decel_mm_s2=500.0,
        )

        assert request.position_mm == 10.0
        assert request.velocity_mm_s == 5.0
        assert request.accel_mm_s2 == 500.0
        assert request.decel_mm_s2 == 500.0

    def test_valid_move_request_with_defaults(self):
        """测试使用默认值的运动请求。"""
        request = MoveRequest(position_mm=10.0)

        assert request.position_mm == 10.0
        assert request.velocity_mm_s == 10.0  # 默认值
        assert request.accel_mm_s2 == 1000.0  # 默认值
        assert request.decel_mm_s2 == 1000.0  # 默认值

    def test_validate_position_positive_limit(self):
        """测试位置正限位验证。"""
        # 在范围内
        request = MoveRequest(position_mm=100.0)
        assert request.position_mm == 100.0

        # 超出正限位
        with pytest.raises(ValidationError) as exc_info:
            MoveRequest(position_mm=101.0)

        errors = exc_info.value.errors()
        assert any("position_mm" in str(e) for e in errors)

    def test_validate_position_negative_limit(self):
        """测试位置负限位验证。"""
        # 在范围内
        request = MoveRequest(position_mm=-100.0)
        assert request.position_mm == -100.0

        # 超出负限位
        with pytest.raises(ValidationError) as exc_info:
            MoveRequest(position_mm=-101.0)

        errors = exc_info.value.errors()
        assert any("position_mm" in str(e) for e in errors)

    def test_validate_velocity_range(self):
        """测试速度范围验证。"""
        # 在范围内
        request = MoveRequest(position_mm=0.0, velocity_mm_s=25.0)
        assert request.velocity_mm_s == 25.0

        # 超出上限
        with pytest.raises(ValidationError):
            MoveRequest(position_mm=0.0, velocity_mm_s=51.0)

        # 低于下限
        with pytest.raises(ValidationError):
            MoveRequest(position_mm=0.0, velocity_mm_s=0.5)

    def test_validate_acceleration_range(self):
        """测试加速度范围验证。"""
        # 在范围内
        request = MoveRequest(position_mm=0.0, accel_mm_s2=5000.0)
        assert request.accel_mm_s2 == 5000.0

        # 超出上限
        with pytest.raises(ValidationError):
            MoveRequest(position_mm=0.0, accel_mm_s2=10001.0)

        # 低于下限
        with pytest.raises(ValidationError):
            MoveRequest(position_mm=0.0, accel_mm_s2=0.5)

    def test_validate_deceleration_range(self):
        """测试减速度范围验证。"""
        # 在范围内
        request = MoveRequest(position_mm=0.0, decel_mm_s2=5000.0)
        assert request.decel_mm_s2 == 5000.0

        # 超出上限
        with pytest.raises(ValidationError):
            MoveRequest(position_mm=0.0, decel_mm_s2=10001.0)

    def test_missing_required_field(self):
        """测试缺少必填字段。"""
        with pytest.raises(ValidationError) as exc_info:
            MoveRequest()

        errors = exc_info.value.errors()
        assert any("position_mm" in str(e) for e in errors)


# ==================== JogRequest 验证测试 ====================


class TestJogRequestValidation:
    """JOG 请求验证测试。"""

    def test_valid_jog_request_positive(self):
        """测试有效的正向 JOG 请求。"""
        request = JogRequest(direction=1, velocity_mm_s=5.0)

        assert request.direction == 1
        assert request.velocity_mm_s == 5.0

    def test_valid_jog_request_negative(self):
        """测试有效的负向 JOG 请求。"""
        request = JogRequest(direction=-1, velocity_mm_s=5.0)

        assert request.direction == -1

    def test_validate_direction_range(self):
        """测试方向范围验证。"""
        # 有效值：-1, 0, 1 (因为 ge=-1, le=1)
        request1 = JogRequest(direction=1)
        request2 = JogRequest(direction=-1)
        request3 = JogRequest(direction=0)  # 0 在范围内是有效的

        assert request1.direction == 1
        assert request2.direction == -1
        assert request3.direction == 0

        # 无效值：超出范围
        with pytest.raises(ValidationError):
            JogRequest(direction=2)

        with pytest.raises(ValidationError):
            JogRequest(direction=-2)

    def test_validate_velocity_range(self):
        """测试 JOG 速度范围验证。"""
        # 在范围内
        request = JogRequest(direction=1, velocity_mm_s=10.0)
        assert request.velocity_mm_s == 10.0

        # 超出上限
        with pytest.raises(ValidationError):
            JogRequest(direction=1, velocity_mm_s=21.0)

        # 低于下限
        with pytest.raises(ValidationError):
            JogRequest(direction=1, velocity_mm_s=0.5)

    def test_default_velocity(self):
        """测试默认速度。"""
        request = JogRequest(direction=1)

        assert request.velocity_mm_s == 5.0  # 默认值


# ==================== LimitConfigRequest 验证测试 ====================


class TestLimitConfigRequestValidation:
    """限位配置验证测试。"""

    def test_valid_limit_config(self):
        """测试有效的限位配置。"""
        request = LimitConfigRequest(positive_mm=50.0, negative_mm=-50.0)

        assert request.positive_mm == 50.0
        assert request.negative_mm == -50.0

    def test_default_values(self):
        """测试默认值。"""
        request = LimitConfigRequest()

        assert request.positive_mm == 50.0
        assert request.negative_mm == -50.0

    def test_custom_values(self):
        """测试自定义值。"""
        request = LimitConfigRequest(positive_mm=100.0, negative_mm=-100.0)

        assert request.positive_mm == 100.0
        assert request.negative_mm == -100.0


# ==================== PRPathConfigRequest 验证测试 ====================


class TestPRPathConfigRequestValidation:
    """PR 路径配置验证测试。"""

    def test_valid_pr_path_config(self):
        """测试有效的 PR 路径配置。"""
        request = PRPathConfigRequest(
            path_number=0,
            mode=1,
            position_mm=10.0,
            velocity_mm_s=1000,
            accel_time=100,
            decel_time=100,
            dwell_time=0,
            special_param=0,
        )

        assert request.path_number == 0
        assert request.mode == 1
        assert request.position_mm == 10.0

    def test_validate_path_number_range(self):
        """测试路径编号范围验证。"""
        # 有效范围：0-15
        for i in range(16):
            request = PRPathConfigRequest(path_number=i, position_mm=0.0)
            assert request.path_number == i

        # 超出上限
        with pytest.raises(ValidationError):
            PRPathConfigRequest(path_number=16, position_mm=0.0)

        # 低于下限
        with pytest.raises(ValidationError):
            PRPathConfigRequest(path_number=-1, position_mm=0.0)

    def test_validate_accel_time_non_negative(self):
        """测试加速时间非负验证。"""
        # 有效值
        request = PRPathConfigRequest(
            path_number=0,
            position_mm=0.0,
            accel_time=100,
        )
        assert request.accel_time == 100

        # 无效值：负数
        with pytest.raises(ValidationError):
            PRPathConfigRequest(
                path_number=0,
                position_mm=0.0,
                accel_time=-1,
            )

    def test_validate_decel_time_non_negative(self):
        """测试减速时间非负验证。"""
        # 有效值
        request = PRPathConfigRequest(
            path_number=0,
            position_mm=0.0,
            decel_time=100,
        )
        assert request.decel_time == 100

        # 无效值：负数
        with pytest.raises(ValidationError):
            PRPathConfigRequest(
                path_number=0,
                position_mm=0.0,
                decel_time=-1,
            )

    def test_validate_dwell_time_non_negative(self):
        """测试停留时间非负验证。"""
        # 有效值
        request = PRPathConfigRequest(
            path_number=0,
            position_mm=0.0,
            dwell_time=100,
        )
        assert request.dwell_time == 100

        # 无效值：负数
        with pytest.raises(ValidationError):
            PRPathConfigRequest(
                path_number=0,
                position_mm=0.0,
                dwell_time=-1,
            )

    def test_default_values(self):
        """测试默认值。"""
        request = PRPathConfigRequest(path_number=0, position_mm=0.0)

        assert request.mode == 1
        assert request.velocity_mm_s == 1000
        assert request.accel_time == 100
        assert request.decel_time == 100
        assert request.dwell_time == 0
        assert request.special_param == 0


# ==================== PRPathTriggerRequest 验证测试 ====================


class TestPRPathTriggerRequestValidation:
    """PR 路径触发验证测试。"""

    def test_valid_trigger_request(self):
        """测试有效的触发请求。"""
        request = PRPathTriggerRequest(path_number=0)

        assert request.path_number == 0

    def test_validate_path_number_range(self):
        """测试路径编号范围验证。"""
        # 有效范围：0-15
        for i in range(16):
            request = PRPathTriggerRequest(path_number=i)
            assert request.path_number == i

        # 超出上限
        with pytest.raises(ValidationError):
            PRPathTriggerRequest(path_number=16)

        # 低于下限
        with pytest.raises(ValidationError):
            PRPathTriggerRequest(path_number=-1)


# ==================== HomeRequest 验证测试 ====================


class TestHomeRequestValidation:
    """回零请求验证测试。"""

    def test_valid_home_request(self):
        """测试有效的回零请求。"""
        request = HomeRequest(mode="origin")

        assert request.mode == "origin"

    def test_default_mode(self):
        """测试默认回零模式。"""
        request = HomeRequest()

        assert request.mode == "origin"


# ==================== CommunicationConfigRequest 验证测试 ====================


class TestCommunicationConfigRequestValidation:
    """通信配置请求验证测试。"""

    def test_valid_config_request(self):
        """测试有效的通信配置请求。"""
        request = CommunicationConfigRequest(
            baudrate=9600,
            slave_id=1,
            data_type=4,
        )

        assert request.baudrate == 9600
        assert request.slave_id == 1
        assert request.data_type == 4

    def test_validate_slave_id_range(self):
        """测试从站地址范围验证。"""
        # 有效范围：0-127
        request = CommunicationConfigRequest(slave_id=0)
        assert request.slave_id == 0

        request = CommunicationConfigRequest(slave_id=127)
        assert request.slave_id == 127

        # 超出上限
        with pytest.raises(ValidationError):
            CommunicationConfigRequest(slave_id=128)

        # 低于下限
        with pytest.raises(ValidationError):
            CommunicationConfigRequest(slave_id=-1)

    def test_validate_data_type_range(self):
        """测试数据类型范围验证。"""
        # 有效范围：0-5
        for i in range(6):
            request = CommunicationConfigRequest(data_type=i)
            assert request.data_type == i

        # 超出上限
        with pytest.raises(ValidationError):
            CommunicationConfigRequest(data_type=6)

        # 低于下限
        with pytest.raises(ValidationError):
            CommunicationConfigRequest(data_type=-1)

    def test_optional_fields(self):
        """测试可选字段。"""
        request = CommunicationConfigRequest()

        assert request.baudrate is None
        assert request.slave_id is None
        assert request.data_type is None


# ==================== DriverSoftLimitRequest 验证测试 ====================


class TestDriverSoftLimitRequestValidation:
    """驱动器软件限位请求验证测试。"""

    def test_valid_request_with_mm(self):
        """测试使用毫米单位的有效请求。"""
        request = DriverSoftLimitRequest(
            positive_limit_mm=100.0,
            negative_limit_mm=-100.0,
        )

        assert request.positive_limit_mm == 100.0
        assert request.negative_limit_mm == -100.0

    def test_valid_request_with_steps(self):
        """测试使用步数单位的有效请求。"""
        request = DriverSoftLimitRequest(
            positive_limit_steps=160000,
            negative_limit_steps=-160000,
        )

        assert request.positive_limit_steps == 160000
        assert request.negative_limit_steps == -160000

    def test_optional_fields(self):
        """测试可选字段。"""
        request = DriverSoftLimitRequest()

        assert request.positive_limit_mm is None
        assert request.negative_limit_mm is None
        assert request.positive_limit_steps is None
        assert request.negative_limit_steps is None


# ==================== 响应模型测试 ====================


class TestResponseModels:
    """响应模型测试。"""

    def test_success_response(self):
        """测试成功响应模型。"""
        response = SuccessResponse(success=True, message="操作成功")

        assert response.success is True
        assert response.message == "操作成功"

    def test_error_response(self):
        """测试错误响应模型。"""
        response = ErrorResponse(
            error_code="E1001",
            detail="设备未初始化",
            suggestions=["检查设备连接", "重启系统"],
        )

        assert response.error_code == "E1001"
        assert response.detail == "设备未初始化"
        assert len(response.suggestions) == 2

    def test_validation_error_detail(self):
        """测试验证错误详情模型。"""
        detail = ValidationErrorDetail(
            field="position_mm",
            value=150.0,
            constraint="le=100",
            message="位置超出限位",
        )

        assert detail.field == "position_mm"
        assert detail.value == 150.0
        assert detail.constraint == "le=100"
        assert detail.message == "位置超出限位"

    def test_validation_error_response(self):
        """测试验证错误响应模型。"""
        response = ValidationErrorResponse(
            detail="参数验证失败",
            errors=[
                ValidationErrorDetail(
                    field="position_mm",
                    value=150.0,
                    constraint="le=100",
                    message="位置超出限位",
                )
            ],
        )

        assert response.error_code == "VALIDATION_ERROR"
        assert response.detail == "参数验证失败"
        assert len(response.errors) == 1

    def test_move_response(self):
        """测试运动响应模型。"""
        response = MoveResponse(
            success=True,
            message="运动已启动",
            target_position_steps=16000,
            target_position_mm=10.0,
        )

        assert response.success is True
        assert response.target_position_steps == 16000
        assert response.target_position_mm == 10.0

    def test_status_word_response(self):
        """测试状态字响应模型。"""
        response = StatusWordResponse(
            fault=False,
            enabled=True,
            running=False,
            cmd_complete=True,
            path_complete=True,
            home_complete=True,
            raw_value=0x72,
        )

        assert response.fault is False
        assert response.enabled is True
        assert response.raw_value == 0x72

    def test_alarm_code_response(self):
        """测试报警代码响应模型。"""
        response = AlarmCodeResponse(alarm_code=0, alarm_text="无报警")

        assert response.alarm_code == 0
        assert response.alarm_text == "无报警"


# ==================== ErrorCode 枚举测试 ====================


class TestErrorCodeEnum:
    """错误码枚举测试。"""

    def test_device_error_codes(self):
        """测试设备错误码。"""
        assert ErrorCode.DEVICE_NOT_INITIALIZED.value == "E1001"
        assert ErrorCode.DEVICE_NOT_CONNECTED.value == "E1002"
        assert ErrorCode.DEVICE_IN_EMERGENCY_STOP.value == "E1003"
        assert ErrorCode.DEVICE_BUSY.value == "E1004"
        assert ErrorCode.DEVICE_ERROR.value == "E1005"

    def test_parameter_error_codes(self):
        """测试参数错误码。"""
        assert ErrorCode.INVALID_PARAMETER.value == "E2001"
        assert ErrorCode.PARAM_OUT_OF_RANGE.value == "E2002"
        assert ErrorCode.MISSING_PARAMETER.value == "E2003"

    def test_limit_error_codes(self):
        """测试限位错误码。"""
        assert ErrorCode.SOFT_LIMIT_EXCEEDED.value == "E3001"
        assert ErrorCode.HARDWARE_LIMIT_TRIGGERED.value == "E3002"

    def test_operation_error_codes(self):
        """测试操作错误码。"""
        assert ErrorCode.OPERATION_FAILED.value == "E4001"
        assert ErrorCode.MOTION_FAILED.value == "E4002"
        assert ErrorCode.CONNECTION_FAILED.value == "E4003"

    def test_system_error_codes(self):
        """测试系统错误码。"""
        assert ErrorCode.INTERNAL_ERROR.value == "E5001"
        assert ErrorCode.COMMUNICATION_ERROR.value == "E5002"
        assert ErrorCode.TIMEOUT_ERROR.value == "E5003"

    def test_error_code_count(self):
        """测试错误码数量。"""
        # 当前有16个错误码
        assert len(ErrorCode) == 16

    def test_error_code_comparison(self):
        """测试错误码比较。"""
        assert ErrorCode.DEVICE_NOT_INITIALIZED != ErrorCode.DEVICE_NOT_CONNECTED
        assert ErrorCode.DEVICE_NOT_INITIALIZED == ErrorCode.DEVICE_NOT_INITIALIZED


# ==================== 模型序列化测试 ====================


class TestModelSerialization:
    """模型序列化测试。"""

    def test_move_request_to_dict(self):
        """测试运动请求序列化。"""
        request = MoveRequest(position_mm=10.0, velocity_mm_s=5.0)
        data = request.model_dump()

        assert data["position_mm"] == 10.0
        assert data["velocity_mm_s"] == 5.0

    def test_move_request_from_dict(self):
        """测试运动请求反序列化。"""
        data = {"position_mm": 10.0, "velocity_mm_s": 5.0}
        request = MoveRequest.model_validate(data)

        assert request.position_mm == 10.0
        assert request.velocity_mm_s == 5.0

    def test_success_response_json(self):
        """测试成功响应 JSON 序列化。"""
        response = SuccessResponse(success=True, message="操作成功")
        json_str = response.model_dump_json()

        assert "success" in json_str
        assert "操作成功" in json_str

    def test_error_response_json(self):
        """测试错误响应 JSON 序列化。"""
        response = ErrorResponse(
            error_code="E1001",
            detail="设备未初始化",
        )
        json_str = response.model_dump_json()

        assert "E1001" in json_str
        assert "设备未初始化" in json_str
