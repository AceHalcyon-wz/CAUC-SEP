"""
文件名: base_service.py
路径: backend/core/services/base_service.py
功能: 设备控制服务抽象基类，定义统一的服务层接口
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: Python 3.11+, backend.drivers.base, backend.core.utils

安全约束:
- 所有服务必须继承此抽象基类
- 业务逻辑必须包含参数校验、异常处理
- 高危操作必须包含日志审计
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

from backend.core.utils.exception_utils import DeviceException, handle_device_exception
from backend.core.utils.validation_utils import ValidationResult

logger = logging.getLogger(__name__)

# 类型变量
DeviceType = TypeVar("DeviceType")


@dataclass
class ServiceResult:
    """
    服务操作结果数据类。

    Attributes:
        success: 是否成功
        data: 返回数据
        message: 消息
        error_code: 错误代码
        timestamp: 时间戳
        execution_time_ms: 执行耗时（毫秒）
    """

    success: bool
    data: Any = None
    message: str = ""
    error_code: int | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式。

        Returns:
            Dict[str, Any]: 字典格式
        """
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "error_code": self.error_code,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
        }


@dataclass
class OperationLog:
    """
    操作日志数据类。

    用于记录高危操作的审计日志。

    Attributes:
        operation: 操作名称
        device_id: 设备ID
        parameters: 操作参数
        result: 操作结果
        operator: 操作者
        timestamp: 时间戳
        execution_time_ms: 执行耗时（毫秒）
    """

    operation: str
    device_id: str
    parameters: dict[str, Any] = field(default_factory=dict)
    result: str = "unknown"
    operator: str = "system"
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """
        转换为字典格式。

        Returns:
            Dict[str, Any]: 字典格式
        """
        return {
            "operation": self.operation,
            "device_id": self.device_id,
            "parameters": self.parameters,
            "result": self.result,
            "operator": self.operator,
            "timestamp": self.timestamp,
            "execution_time_ms": self.execution_time_ms,
        }


class BaseDeviceService(ABC, Generic[DeviceType]):
    """
    设备控制服务抽象基类。

    所有设备控制服务必须继承此基类，并实现所有抽象方法。
    提供统一的服务层接口规范，确保所有服务具有一致的行为。

    Attributes:
        service_name: 服务名称
        _operation_logs: 操作日志列表
        _max_log_size: 最大日志数量

    安全约束:
        - 所有服务必须继承此抽象基类
        - 业务逻辑必须包含参数校验、异常处理
        - 高危操作必须包含日志审计

    Example:
        >>> class MotorControlService(BaseDeviceService[MotorDevice]):
        ...     async def execute_command(self, command: str, params: dict) -> ServiceResult:
        ...         # 实现业务逻辑
        ...         pass
    """

    def __init__(self, service_name: str = "BaseDeviceService") -> None:
        """
        初始化设备控制服务。

        Args:
            service_name: 服务名称
        """
        self.service_name = service_name
        self._operation_logs: list[OperationLog] = []
        self._max_log_size = 1000  # 最大日志数量

        logger.info(f"{self.service_name}初始化完成")

    # ==================== 抽象方法（必须实现） ====================

    @abstractmethod
    async def get_device_status(self, device_id: str) -> ServiceResult:
        """
        获取设备状态。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        pass

    @abstractmethod
    async def execute_command(
        self,
        device_id: str,
        command: str,
        params: dict[str, Any],
    ) -> ServiceResult:
        """
        执行设备命令。

        Args:
            device_id: 设备ID
            command: 命令名称
            params: 命令参数

        Returns:
            ServiceResult: 服务操作结果

        安全约束:
            - 必须校验参数合法性
            - 必须记录操作日志
            - 必须处理异常情况
        """
        pass

    @abstractmethod
    async def emergency_stop(self, device_id: str) -> ServiceResult:
        """
        执行紧急停止。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果

        安全约束:
            - 急停指令必须具有最高执行优先级
            - 必须记录急停日志
            - 必须处理异常情况
        """
        pass

    # ==================== 可选方法（建议实现） ====================

    async def initialize_device(self, device_id: str) -> ServiceResult:
        """
        初始化设备。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        logger.info(f"初始化设备: device_id={device_id}")
        return ServiceResult(
            success=True,
            message=f"设备 {device_id} 初始化成功",
        )

    async def reset_device(self, device_id: str) -> ServiceResult:
        """
        复位设备。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        logger.info(f"复位设备: device_id={device_id}")
        return ServiceResult(
            success=True,
            message=f"设备 {device_id} 复位成功",
        )

    async def get_device_parameters(self, device_id: str) -> ServiceResult:
        """
        获取设备参数。

        Args:
            device_id: 设备ID

        Returns:
            ServiceResult: 服务操作结果
        """
        logger.info(f"获取设备参数: device_id={device_id}")
        return ServiceResult(
            success=True,
            data={},
            message=f"设备 {device_id} 参数获取成功",
        )

    async def set_device_parameter(
        self,
        device_id: str,
        parameter_name: str,
        parameter_value: Any,
    ) -> ServiceResult:
        """
        设置设备参数。

        Args:
            device_id: 设备ID
            parameter_name: 参数名称
            parameter_value: 参数值

        Returns:
            ServiceResult: 服务操作结果
        """
        logger.info(
            f"设置设备参数: device_id={device_id}, "
            f"parameter={parameter_name}, value={parameter_value}"
        )
        return ServiceResult(
            success=True,
            message=f"设备 {device_id} 参数 {parameter_name} 设置成功",
        )

    # ==================== 日志记录方法 ====================

    def log_operation(
        self,
        operation: str,
        device_id: str,
        parameters: dict[str, Any],
        result: str,
        execution_time_ms: float = 0.0,
        operator: str = "system",
    ) -> None:
        """
        记录操作日志。

        Args:
            operation: 操作名称
            device_id: 设备ID
            parameters: 操作参数
            result: 操作结果
            execution_time_ms: 执行耗时（毫秒）
            operator: 操作者
        """
        log_entry = OperationLog(
            operation=operation,
            device_id=device_id,
            parameters=parameters,
            result=result,
            operator=operator,
            execution_time_ms=execution_time_ms,
        )

        self._operation_logs.append(log_entry)

        # 限制日志数量
        if len(self._operation_logs) > self._max_log_size:
            self._operation_logs.pop(0)

        logger.debug(
            f"操作日志: operation={operation}, device_id={device_id}, "
            f"result={result}, time={execution_time_ms:.2f}ms"
        )

    def get_operation_logs(
        self,
        device_id: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """
        获取操作日志。

        Args:
            device_id: 设备ID过滤，None表示所有设备
            limit: 返回数量限制

        Returns:
            List[Dict[str, Any]]: 操作日志列表
        """
        logs = self._operation_logs

        # 按设备ID过滤
        if device_id is not None:
            logs = [log for log in logs if log.device_id == device_id]

        # 返回最近的日志
        return [log.to_dict() for log in logs[-limit:]]

    # ==================== 异常处理方法 ====================

    def handle_exception(
        self,
        exception: Exception,
        device_id: str,
        operation: str,
    ) -> ServiceResult:
        """
        统一处理异常。

        Args:
            exception: 异常对象
            device_id: 设备ID
            operation: 操作名称

        Returns:
            ServiceResult: 服务操作结果
        """
        error_info = handle_device_exception(
            exception,
            device_id=device_id,
            operation=operation,
        )

        return ServiceResult(
            success=False,
            message=error_info.get("message", str(exception)),
            error_code=error_info.get("error_code"),
            data=error_info,
        )

    # ==================== 参数校验方法 ====================

    def validate_parameters(
        self,
        params: dict[str, Any],
        required_fields: list[str],
        validations: dict[str, Callable[[Any], ValidationResult]] | None = None,
    ) -> ValidationResult:
        """
        校验参数。

        Args:
            params: 参数字典
            required_fields: 必填字段列表
            validations: 字段校验函数字典

        Returns:
            ValidationResult: 校验结果
        """
        # 检查必填字段
        from backend.core.utils.validation_utils import validate_required_fields

        result = validate_required_fields(params, required_fields)
        if not result:
            return result

        # 执行字段校验
        if validations:
            for field_name, validation_func in validations.items():
                if field_name in params:
                    result = validation_func(params[field_name])
                    if not result:
                        return result

        return ValidationResult(is_valid=True)

    def __repr__(self) -> str:
        """
        返回字符串表示。

        Returns:
            str: 字符串表示
        """
        return f"{self.__class__.__name__}(service_name='{self.service_name}')"
