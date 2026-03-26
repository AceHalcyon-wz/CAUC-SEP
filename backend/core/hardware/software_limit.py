"""
文件名: software_limit.py
路径: backend/core/hardware/software_limit.py
功能: 软件限位配置类，提供安全保护功能
作者: Backend Engineer Agent
创建日期: 2026-03-26
依赖: Python 3.11+, math

安全约束:
- 所有运动设备必须配置软件限位
- 限位参数必须经过有效性验证
- 位置检查必须在运动指令下发前执行
"""

from __future__ import annotations

import math
from typing import Any


class SoftwareLimitConfig:
    """
    软件限位配置类。

    用于定义设备的软件限位，提供安全保护功能。
    支持配置验证、序列化和反序列化。

    安全约束:
        - 所有运动设备必须配置软件限位
        - 限位参数必须经过有效性验证
        - 位置检查必须在运动指令下发前执行

    Example:
        >>> limit_config = SoftwareLimitConfig(
        ...     positive_limit=100.0,
        ...     negative_limit=-100.0,
        ...     enable=True
        ... )
        >>> if limit_config.is_within_limits(50.0):
        ...     # 执行运动指令
        ...     pass
    """

    def __init__(
        self,
        positive_limit: float = 100.0,
        negative_limit: float = -100.0,
        enable: bool = True,
    ) -> None:
        """
        初始化软件限位配置。

        Args:
            positive_limit: 正向限位（单位：毫米），默认为100.0mm
            negative_limit: 负向限位（单位：毫米），默认为-100.0mm
            enable: 是否启用限位检查，默认为True

        Raises:
            ValueError: 当限位参数无效时抛出
        """
        self._positive_limit = positive_limit
        self._negative_limit = negative_limit
        self._enable = enable

        # 验证配置有效性
        self._validate()

    @property
    def positive_limit(self) -> float:
        """获取正向限位。"""
        return self._positive_limit

    @positive_limit.setter
    def positive_limit(self, value: float) -> None:
        """
        设置正向限位。

        Args:
            value: 正向限位值

        Raises:
            ValueError: 当值无效时抛出
        """
        if not isinstance(value, (int, float)):
            raise ValueError(f"正向限位必须是数值类型，当前类型: {type(value)}")
        self._positive_limit = float(value)
        self._validate()

    @property
    def negative_limit(self) -> float:
        """获取负向限位。"""
        return self._negative_limit

    @negative_limit.setter
    def negative_limit(self, value: float) -> None:
        """
        设置负向限位。

        Args:
            value: 负向限位值

        Raises:
            ValueError: 当值无效时抛出
        """
        if not isinstance(value, (int, float)):
            raise ValueError(f"负向限位必须是数值类型，当前类型: {type(value)}")
        self._negative_limit = float(value)
        self._validate()

    @property
    def enable(self) -> bool:
        """获取是否启用限位检查。"""
        return self._enable

    @enable.setter
    def enable(self, value: bool) -> None:
        """
        设置是否启用限位检查。

        Args:
            value: 是否启用

        Raises:
            ValueError: 当值无效时抛出
        """
        if not isinstance(value, bool):
            raise ValueError(f"enable必须是布尔类型，当前类型: {type(value)}")
        self._enable = value

    def _validate(self) -> None:
        """
        验证限位配置的有效性。

        Raises:
            ValueError: 当配置无效时抛出
        """
        # 检查数值有效性
        if not isinstance(self._positive_limit, (int, float)):
            raise ValueError(f"正向限位必须是数值类型，当前类型: {type(self._positive_limit)}")

        if not isinstance(self._negative_limit, (int, float)):
            raise ValueError(f"负向限位必须是数值类型，当前类型: {type(self._negative_limit)}")

        # 检查NaN和无穷大
        if math.isnan(self._positive_limit) or math.isinf(self._positive_limit):
            raise ValueError("正向限位不能是NaN或无穷大")

        if math.isnan(self._negative_limit) or math.isinf(self._negative_limit):
            raise ValueError("负向限位不能是NaN或无穷大")

        # 检查逻辑关系：负向限位必须小于正向限位
        if self._negative_limit >= self._positive_limit:
            raise ValueError(
                f"负向限位({self._negative_limit})必须小于正向限位({self._positive_limit})"
            )

    def is_within_limits(self, position: float) -> bool:
        """
        检查位置是否在限位范围内。

        Args:
            position: 待检查的位置（单位：毫米）

        Returns:
            bool: 位置是否在限位范围内
        """
        if not self._enable:
            return True
        return self._negative_limit <= position <= self._positive_limit

    def clamp_position(self, position: float) -> float:
        """
        将位置限制在有效范围内。

        Args:
            position: 待限制的位置（单位：毫米）

        Returns:
            float: 限制后的位置，如果禁用限位则返回原值
        """
        if not self._enable:
            return position
        return max(self._negative_limit, min(self._positive_limit, position))

    def get_range(self) -> float:
        """
        获取限位范围大小。

        Returns:
            float: 正向限位与负向限位的差值
        """
        return self._positive_limit - self._negative_limit

    def to_dict(self) -> dict[str, Any]:
        """
        将配置序列化为字典。

        Returns:
            Dict[str, Any]: 包含配置信息的字典
        """
        return {
            "positive_limit": self._positive_limit,
            "negative_limit": self._negative_limit,
            "enable": self._enable,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> SoftwareLimitConfig:
        """
        从字典反序列化配置。

        Args:
            data: 包含配置信息的字典

        Returns:
            SoftwareLimitConfig: 配置实例

        Raises:
            ValueError: 当数据无效时抛出
        """
        if not isinstance(data, dict):
            raise ValueError(f"配置数据必须是字典类型，当前类型: {type(data)}")

        return cls(
            positive_limit=data.get("positive_limit", 100.0),
            negative_limit=data.get("negative_limit", -100.0),
            enable=data.get("enable", True),
        )

    def __repr__(self) -> str:
        """返回配置的字符串表示。"""
        return (
            f"SoftwareLimitConfig(positive_limit={self._positive_limit}, "
            f"negative_limit={self._negative_limit}, enable={self._enable})"
        )

    def __eq__(self, other: object) -> bool:
        """判断两个配置是否相等。"""
        if not isinstance(other, SoftwareLimitConfig):
            return False
        return (
            self._positive_limit == other._positive_limit
            and self._negative_limit == other._negative_limit
            and self._enable == other._enable
        )
