"""
文件名: param_validator.py
路径: backend/api/
功能: 统一参数校验工具，提供参数范围、格式、合法性校验功能
版本: v1.0
作者: Backend Engineer Agent
创建日期: 2026-03-25
依赖: pydantic, schemas.common, api.response_wrapper

校验规则：
1. 参数范围校验：数值范围、字符串长度、列表元素数量
2. 参数格式校验：正则表达式、枚举值、自定义格式
3. 参数合法性校验：设备ID、实验ID、文件路径
4. 校验失败返回统一格式的错误响应

使用示例：
    >>> from api.param_validator import ParamValidator, validate_params
    >>> # 使用装饰器校验
    >>> @validate_params(
    ...     ParamValidator.range("position_mm", min_val=-50, max_val=50),
    ...     ParamValidator.range("velocity_mm_s", min_val=1, max_val=50)
    ... )
    >>> async def move_motor(request: MoveRequest):
    ...     pass
"""

import re
from typing import Any, Callable
from functools import wraps

from pydantic import ValidationError as PydanticValidationError

from schemas.common import ErrorCode
from api.response_wrapper import error_response, ApiResponse


class ValidationError(Exception):
    """
    参数验证错误异常。

    Attributes:
        field: 错误字段名
        value: 错误值
        constraint: 约束条件
        message: 错误消息
    """

    def __init__(
        self,
        field: str,
        value: Any,
        constraint: str,
        message: str
    ):
        """初始化验证错误。"""
        self.field = field
        self.value = value
        self.constraint = constraint
        self.message = message
        super().__init__(message)


class ParamValidator:
    """
    参数校验器基类。

    提供静态方法创建各种类型的校验规则。

    Example:
        >>> validator = ParamValidator.range("position_mm", -50, 50)
        >>> result = validator.validate({"position_mm": 100})
        >>> assert result is False
    """

    @staticmethod
    def range(
        field: str,
        min_val: float | int | None = None,
        max_val: float | int | None = None,
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建数值范围校验规则。

        Args:
            field: 字段名
            min_val: 最小值，None表示不限制
            max_val: 最大值，None表示不限制
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.range("position_mm", -50, 50)
        """
        def validate(data: dict) -> None:
            value = data.get(field)
            if value is None:
                return

            if min_val is not None and value < min_val:
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint=f"ge={min_val}",
                    message=message or f"{field} 不能小于 {min_val}"
                )

            if max_val is not None and value > max_val:
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint=f"le={max_val}",
                    message=message or f"{field} 不能大于 {max_val}"
                )

        return validate

    @staticmethod
    def length(
        field: str,
        min_len: int | None = None,
        max_len: int | None = None,
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建字符串长度校验规则。

        Args:
            field: 字段名
            min_len: 最小长度，None表示不限制
            max_len: 最大长度，None表示不限制
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.length("name", 1, 100)
        """
        def validate(data: dict) -> None:
            value = data.get(field)
            if value is None:
                return

            if not isinstance(value, str):
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint="type=str",
                    message=message or f"{field} 必须是字符串类型"
                )

            if min_len is not None and len(value) < min_len:
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint=f"min_length={min_len}",
                    message=message or f"{field} 长度不能小于 {min_len}"
                )

            if max_len is not None and len(value) > max_len:
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint=f"max_length={max_len}",
                    message=message or f"{field} 长度不能大于 {max_len}"
                )

        return validate

    @staticmethod
    def regex(
        field: str,
        pattern: str,
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建正则表达式校验规则。

        Args:
            field: 字段名
            pattern: 正则表达式
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.regex("device_id", r"^[a-zA-Z0-9_-]+$")
        """
        compiled = re.compile(pattern)

        def validate(data: dict) -> None:
            value = data.get(field)
            if value is None:
                return

            if not compiled.match(str(value)):
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint=f"pattern={pattern}",
                    message=message or f"{field} 格式不正确"
                )

        return validate

    @staticmethod
    def enum(
        field: str,
        allowed_values: list[Any],
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建枚举值校验规则。

        Args:
            field: 字段名
            allowed_values: 允许的值列表
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.enum("direction", [1, -1])
        """
        def validate(data: dict) -> None:
            value = data.get(field)
            if value is None:
                return

            if value not in allowed_values:
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint=f"allowed_values={allowed_values}",
                    message=message or f"{field} 必须是以下值之一: {allowed_values}"
                )

        return validate

    @staticmethod
    def required(
        field: str,
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建必填字段校验规则。

        Args:
            field: 字段名
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.required("name")
        """
        def validate(data: dict) -> None:
            value = data.get(field)
            if value is None or (isinstance(value, str) and value.strip() == ""):
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint="required",
                    message=message or f"{field} 不能为空"
                )

        return validate

    @staticmethod
    def device_id(
        field: str = "device_id",
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建设备ID格式校验规则。

        设备ID只能包含字母、数字、下划线和连字符。

        Args:
            field: 字段名，默认为"device_id"
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.device_id()
        """
        return ParamValidator.regex(
            field=field,
            pattern=r"^[a-zA-Z0-9_-]+$",
            message=message or f"{field} 格式无效，只能包含字母、数字、下划线和连字符"
        )

    @staticmethod
    def positive_int(
        field: str,
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建正整数校验规则。

        Args:
            field: 字段名
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.positive_int("experiment_id")
        """
        def validate(data: dict) -> None:
            value = data.get(field)
            if value is None:
                return

            if not isinstance(value, int) or value <= 0:
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint="positive_int",
                    message=message or f"{field} 必须是正整数"
                )

        return validate

    @staticmethod
    def file_path(
        field: str,
        allowed_extensions: list[str] | None = None,
        message: str | None = None
    ) -> Callable[[dict], None]:
        """
        创建文件路径安全校验规则。

        检查路径是否包含危险字符和路径遍历。

        Args:
            field: 字段名
            allowed_extensions: 允许的文件扩展名列表，如 [".csv", ".txt"]
            message: 自定义错误消息

        Returns:
            Callable: 校验函数

        Example:
            >>> validator = ParamValidator.file_path("filepath", [".csv"])
        """
        def validate(data: dict) -> None:
            value = data.get(field)
            if value is None:
                return

            # 检查路径遍历
            if ".." in str(value) or str(value).startswith("/"):
                raise ValidationError(
                    field=field,
                    value=value,
                    constraint="no_path_traversal",
                    message=message or f"{field} 包含非法路径"
                )

            # 检查扩展名
            if allowed_extensions:
                ext = "." + str(value).rsplit(".", 1)[-1] if "." in str(value) else ""
                if ext.lower() not in [e.lower() for e in allowed_extensions]:
                    raise ValidationError(
                        field=field,
                        value=value,
                        constraint=f"allowed_extensions={allowed_extensions}",
                        message=message or f"{field} 文件类型不支持"
                    )

        return validate


def validate_params(*validators: Callable[[dict], None]) -> Callable:
    """
    参数校验装饰器。

    Args:
        *validators: 校验函数列表

    Returns:
        Callable: 装饰器函数

    Example:
        >>> @validate_params(
        ...     ParamValidator.required("name"),
        ...     ParamValidator.range("position_mm", -50, 50)
        ... )
        >>> async def move_motor(request: MoveRequest):
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> ApiResponse | Any:
            # 从参数中提取数据（假设第一个参数是Pydantic模型）
            data = {}
            if args and hasattr(args[0], "model_dump"):
                data = args[0].model_dump()
            elif args and isinstance(args[0], dict):
                data = args[0]

            # 执行所有校验
            for validator in validators:
                try:
                    validator(data)
                except ValidationError as e:
                    return error_response(
                        message=e.message,
                        error_code=ErrorCode.INVALID_PARAMETER,
                        details={
                            "field": e.field,
                            "value": str(e.value),
                            "constraint": e.constraint
                        }
                    )

            # 所有校验通过，执行原函数
            return await func(*args, **kwargs)

        return wrapper
    return decorator


def validate_pydantic_model(model_class: type) -> Callable:
    """
    Pydantic模型校验装饰器。

    自动捕获Pydantic验证错误并转换为统一格式。

    Args:
        model_class: Pydantic模型类

    Returns:
        Callable: 装饰器函数

    Example:
        >>> @validate_pydantic_model(MoveRequest)
        >>> async def move_motor(request: dict):
        ...     pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> ApiResponse | Any:
            try:
                # 从参数中提取数据
                data = args[0] if args else kwargs

                # 验证模型
                if isinstance(data, dict):
                    validated = model_class(**data)
                else:
                    validated = data

                # 执行原函数
                return await func(validated, *args[1:], **kwargs)

            except PydanticValidationError as e:
                # 转换Pydantic错误为统一格式
                errors = e.errors()
                first_error = errors[0] if errors else {}

                return error_response(
                    message=first_error.get("msg", "参数验证失败"),
                    error_code=ErrorCode.INVALID_PARAMETER,
                    details={
                        "field": ".".join(str(loc) for loc in first_error.get("loc", [])),
                        "value": str(first_error.get("input", "")),
                        "constraint": first_error.get("type", ""),
                        "all_errors": errors
                    }
                )

        return wrapper
    return decorator
