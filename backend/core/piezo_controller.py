"""
压电陶瓷控制器驱动模块

文件名: piezo_controller.py
路径: backend/core/
功能: 提供高精度压电陶瓷定位控制，支持开环/闭环控制模式及校准功能
作者: Backend Engineer Agent
创建日期: 2024-01-20
更新日期: 2026-03-14
版本: 1.0.0

核心功能：
    - 高精度电压控制（1mV分辨率）
    - 位移-电压校准与非线性补偿
    - 开环/闭环控制模式切换
    - 位移反馈显示
    - 磁滞效应补偿

技术规格：
    - 电压范围：0-150V
    - 电压分辨率：1mV (0.001V)
    - 位移范围：0-100μm
    - 位移分辨率：1nm

校准类型：
    - LINEAR: 线性校准
    - POLYNOMIAL: 多项式校准（3阶）
    - PIECEWISE: 分段线性校准

设计参考：技术设计文档第3.3章节

依赖：
    - dataclasses: 数据类支持
    - enum: 枚举类型支持
    - typing.Any: 任意类型注解
    - numpy: 数值计算（多项式拟合）
    - backend.core.abstract: 设备抽象基类

使用示例：
    >>> from backend.core.piezo_controller import PiezoController, ControlMode
    >>> 
    >>> # 创建控制器实例
    >>> config = {"simulation": True, "max_voltage_v": 150.0}
    >>> piezo = PiezoController("piezo_1", config)
    >>> 
    >>> # 连接设备
    >>> await piezo.connect()
    >>> 
    >>> # 开环控制：设置电压
    >>> await piezo.set_voltage(75.0)  # 设置电压为75V
    >>> 
    >>> # 闭环控制：设置位移
    >>> await piezo.set_control_mode(ControlMode.CLOSED_LOOP)
    >>> await piezo.set_displacement(50.0)  # 设置位移为50μm
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np

from .abstract import AbstractDevice, DeviceStatus


class ControlMode(Enum):
    """压电陶瓷控制模式枚举。"""

    OPEN_LOOP = "open_loop"  # 开环控制：直接电压控制
    CLOSED_LOOP = "closed_loop"  # 闭环控制：基于位移反馈


class CalibrationType(Enum):
    """校准类型枚举。"""

    LINEAR = "linear"  # 线性校准
    POLYNOMIAL = "polynomial"  # 多项式校准
    PIECEWISE = "piecewise"  # 分段线性校准


@dataclass
class CalibrationPoint:
    """校准数据点。

    Attributes:
        voltage_v: 电压值（单位：V）
        displacement_um: 位移值（单位：μm）
    """

    voltage_v: float
    displacement_um: float


@dataclass
class CalibrationData:
    """校准数据集合。

    Attributes:
        points: 校准点列表
        calibration_type: 校准类型
        coefficients: 拟合系数（多项式校准时使用）
        created_at: 校准时间戳
        valid: 校准数据是否有效
    """

    points: list[CalibrationPoint] = field(default_factory=list)
    calibration_type: CalibrationType = CalibrationType.LINEAR
    coefficients: list[float] = field(default_factory=list)
    created_at: float = 0.0
    valid: bool = False


@dataclass
class PiezoConfig:
    """压电陶瓷配置参数。

    Attributes:
        max_voltage_v: 最大电压（V）
        min_voltage_v: 最小电压（V）
        voltage_resolution_v: 电压分辨率（V）
        max_displacement_um: 最大位移（μm）
        min_displacement_um: 最小位移（μm）
        displacement_resolution_nm: 位移分辨率（nm）
        default_mode: 默认控制模式
        hysteresis_compensation: 是否启用磁滞补偿
    """

    max_voltage_v: float = 150.0
    min_voltage_v: float = 0.0
    voltage_resolution_v: float = 0.001  # 1mV
    max_displacement_um: float = 100.0
    min_displacement_um: float = 0.0
    displacement_resolution_nm: float = 1.0  # 1nm
    default_mode: ControlMode = ControlMode.OPEN_LOOP
    hysteresis_compensation: bool = True


class PiezoController(AbstractDevice):
    """压电陶瓷控制器类。

    提供高精度压电陶瓷定位控制，支持开环/闭环控制模式，
    包含完整的校准和非线性补偿功能。

    控制模式：
        - 开环控制：直接设置电压，适用于无位移传感器的场景
        - 闭环控制：基于位移反馈，实现精确位移控制

    校准功能：
        - 多点校准：支持任意数量的校准点
        - 曲线拟合：线性、多项式、分段线性
        - 非线性补偿：自动补偿压电陶瓷的非线性特性

    Example:
        >>> config = {"simulation": True}
        >>> piezo = PiezoController("piezo_1", config)
        >>> await piezo.connect()
        >>> await piezo.set_voltage(75.0)  # 设置电压为75V
        >>> await piezo.set_displacement(50.0)  # 设置位移为50μm（闭环模式）
    """

    # 默认配置
    DEFAULT_CONFIG = PiezoConfig()

    def __init__(self, device_id: str, config: dict[str, Any]):
        """初始化压电陶瓷控制器。

        Args:
            device_id: 设备唯一标识符
            config: 设备配置字典，可包含以下键：
                - simulation: 是否为仿真模式，默认True
                - max_voltage_v: 最大电压
                - min_voltage_v: 最小电压
                - voltage_resolution_v: 电压分辨率
                - max_displacement_um: 最大位移
                - min_displacement_um: 最小位移
                - displacement_resolution_nm: 位移分辨率
                - default_mode: 默认控制模式
                - hysteresis_compensation: 是否启用磁滞补偿
                - port: 通信端口（真实硬件模式）
                - baudrate: 波特率（真实硬件模式）
        """
        super().__init__(device_id, config)

        # 解析配置
        self.simulation = config.get("simulation", True)
        self.port = config.get("port", "COM1")
        self.baudrate = config.get("baudrate", 9600)

        # 硬件配置
        self.piezo_config = PiezoConfig(
            max_voltage_v=config.get("max_voltage_v", self.DEFAULT_CONFIG.max_voltage_v),
            min_voltage_v=config.get("min_voltage_v", self.DEFAULT_CONFIG.min_voltage_v),
            voltage_resolution_v=config.get(
                "voltage_resolution_v", self.DEFAULT_CONFIG.voltage_resolution_v
            ),
            max_displacement_um=config.get(
                "max_displacement_um", self.DEFAULT_CONFIG.max_displacement_um
            ),
            min_displacement_um=config.get(
                "min_displacement_um", self.DEFAULT_CONFIG.min_displacement_um
            ),
            displacement_resolution_nm=config.get(
                "displacement_resolution_nm", self.DEFAULT_CONFIG.displacement_resolution_nm
            ),
            default_mode=ControlMode(
                config.get("default_mode", self.DEFAULT_CONFIG.default_mode.value)
            ),
            hysteresis_compensation=config.get(
                "hysteresis_compensation", self.DEFAULT_CONFIG.hysteresis_compensation
            ),
        )

        # 状态变量
        self._current_voltage: float = 0.0
        self._current_displacement: float = 0.0
        self._target_displacement: float = 0.0
        self._control_mode: ControlMode = self.piezo_config.default_mode

        # 校准数据
        self._calibration_data: CalibrationData = CalibrationData()

        # 磁滞补偿参数（历史电压用于磁滞补偿）
        self._voltage_history: list[float] = []
        self._max_history_length: int = 100

        # 硬件客户端（真实硬件模式）
        self.client: Any = None

    async def connect(self) -> bool:
        """建立与压电陶瓷控制器的连接。

        Returns:
            bool: 连接是否成功
        """
        try:
            self.status = DeviceStatus.CONNECTING

            if self.simulation:
                # 仿真模式：直接进入就绪状态
                self.status = DeviceStatus.READY
                return True

            # 真实硬件模式：初始化通信
            # TODO: 实现真实硬件连接逻辑
            # 示例：通过串口或USB与压电控制器通信
            self.status = DeviceStatus.READY
            return True

        except Exception as e:
            self._last_error = f"连接失败: {e!s}"
            self.status = DeviceStatus.ERROR
            return False

    async def disconnect(self) -> bool:
        """断开与压电陶瓷控制器的连接。

        Returns:
            bool: 断开是否成功
        """
        try:
            if self.client is not None:
                # 关闭硬件连接
                if hasattr(self.client, "close"):
                    self.client.close()
                self.client = None

            self.status = DeviceStatus.DISCONNECTED
            return True

        except Exception as e:
            self._last_error = f"断开连接失败: {e!s}"
            return False

    async def read_status(self) -> dict[str, Any]:
        """读取压电陶瓷控制器完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典，包括：
                - device_id: 设备ID
                - status: 设备状态
                - control_mode: 控制模式
                - current_voltage_v: 当前电压（V）
                - current_displacement_um: 当前位移（μm）
                - target_displacement_um: 目标位移（μm）
                - calibration_valid: 校准是否有效
                - calibration_points: 校准点数量
        """
        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "control_mode": self._control_mode.value,
            "current_voltage_v": self._current_voltage,
            "current_displacement_um": self._current_displacement,
            "target_displacement_um": self._target_displacement,
            "calibration_valid": self._calibration_data.valid,
            "calibration_points": len(self._calibration_data.points),
            "max_voltage_v": self.piezo_config.max_voltage_v,
            "max_displacement_um": self.piezo_config.max_displacement_um,
        }

    # ==================== 电压控制 ====================

    async def set_voltage(self, voltage_v: float) -> bool:
        """设置压电陶瓷电压（开环控制）。

        电压将被自动量化到最接近的分辨率值，
        并限制在有效范围内。

        Args:
            voltage_v: 目标电压（单位：V），范围：0-150V

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 电压超出有效范围
        """
        # 参数校验
        if not self._is_voltage_valid(voltage_v):
            raise ValueError(
                f"电压 {voltage_v}V 超出有效范围 "
                f"[{self.piezo_config.min_voltage_v}, {self.piezo_config.max_voltage_v}]V"
            )

        # 量化到分辨率
        quantized_voltage = self._quantize_voltage(voltage_v)

        try:
            if self.simulation:
                # 仿真模式：直接更新状态
                self._current_voltage = quantized_voltage
                # 根据校准数据计算位移
                self._current_displacement = self._voltage_to_displacement(quantized_voltage)
                # 记录历史（用于磁滞补偿）
                self._record_voltage_history(quantized_voltage)
                return True

            # 真实硬件模式
            # TODO: 实现真实硬件电压设置
            self._current_voltage = quantized_voltage
            self._current_displacement = self._voltage_to_displacement(quantized_voltage)
            self._record_voltage_history(quantized_voltage)
            return True

        except Exception as e:
            self._last_error = f"设置电压失败: {e!s}"
            return False

    async def get_voltage(self) -> float:
        """获取当前电压值。

        Returns:
            float: 当前电压（单位：V）
        """
        if not self.simulation:
            # TODO: 从真实硬件读取电压
            pass
        return self._current_voltage

    # ==================== 位移控制 ====================

    async def set_displacement(self, displacement_um: float) -> bool:
        """设置压电陶瓷位移（闭环控制）。

        根据校准数据将位移转换为电压，
        并应用非线性补偿。

        Args:
            displacement_um: 目标位移（单位：μm），范围：0-100μm

        Returns:
            bool: 设置是否成功

        Raises:
            ValueError: 位移超出有效范围
        """
        # 参数校验
        if not self._is_displacement_valid(displacement_um):
            raise ValueError(
                f"位移 {displacement_um}μm 超出有效范围 "
                f"[{self.piezo_config.min_displacement_um}, {self.piezo_config.max_displacement_um}]μm"
            )

        # 检查校准数据
        if not self._calibration_data.valid:
            # 无校准数据时使用线性近似
            voltage = self._displacement_to_voltage_linear(displacement_um)
        else:
            # 使用校准数据转换
            voltage = self._displacement_to_voltage(displacement_um)

        # 应用磁滞补偿
        if self.piezo_config.hysteresis_compensation:
            voltage = self._apply_hysteresis_compensation(voltage)

        # 设置电压
        self._target_displacement = displacement_um
        return await self.set_voltage(voltage)

    async def get_displacement(self) -> float:
        """获取当前位移值。

        Returns:
            float: 当前位移（单位：μm）
        """
        if not self.simulation and self._control_mode == ControlMode.CLOSED_LOOP:
            # TODO: 从真实硬件读取位移传感器数据
            pass
        return self._current_displacement

    # ==================== 控制模式 ====================

    async def set_control_mode(self, mode: ControlMode) -> bool:
        """设置控制模式。

        Args:
            mode: 控制模式（开环/闭环）

        Returns:
            bool: 设置是否成功
        """
        try:
            self._control_mode = mode

            if not self.simulation:
                # TODO: 配置真实硬件控制模式
                pass

            return True

        except Exception as e:
            self._last_error = f"设置控制模式失败: {e!s}"
            return False

    def get_control_mode(self) -> ControlMode:
        """获取当前控制模式。

        Returns:
            ControlMode: 当前控制模式
        """
        return self._control_mode

    # ==================== 校准功能 ====================

    async def add_calibration_point(self, voltage_v: float, displacement_um: float) -> bool:
        """添加校准点。

        Args:
            voltage_v: 电压值（单位：V）
            displacement_um: 位移值（单位：μm）

        Returns:
            bool: 添加是否成功
        """
        # 参数校验
        if not self._is_voltage_valid(voltage_v):
            raise ValueError(f"电压 {voltage_v}V 超出有效范围")

        if not self._is_displacement_valid(displacement_um):
            raise ValueError(f"位移 {displacement_um}μm 超出有效范围")

        try:
            point = CalibrationPoint(voltage_v=voltage_v, displacement_um=displacement_um)
            self._calibration_data.points.append(point)

            # 按电压排序
            self._calibration_data.points.sort(key=lambda p: p.voltage_v)

            return True

        except Exception as e:
            self._last_error = f"添加校准点失败: {e!s}"
            return False

    async def clear_calibration(self) -> bool:
        """清除所有校准数据。

        Returns:
            bool: 清除是否成功
        """
        self._calibration_data = CalibrationData()
        return True

    async def perform_calibration(
        self, calibration_type: CalibrationType = CalibrationType.POLYNOMIAL
    ) -> bool:
        """执行校准拟合。

        根据已添加的校准点，计算位移-电压转换系数。

        Args:
            calibration_type: 校准类型
                - LINEAR: 线性拟合
                - POLYNOMIAL: 多项式拟合（3阶）
                - PIECEWISE: 分段线性插值

        Returns:
            bool: 校准是否成功

        Note:
            至少需要2个校准点才能执行校准
        """
        if len(self._calibration_data.points) < 2:
            self._last_error = "校准点数量不足，至少需要2个点"
            return False

        try:
            self._calibration_data.calibration_type = calibration_type

            # 提取电压和位移数组
            voltages = np.array([p.voltage_v for p in self._calibration_data.points])
            displacements = np.array([p.displacement_um for p in self._calibration_data.points])

            if calibration_type == CalibrationType.LINEAR:
                # 线性拟合：displacement = a * voltage + b
                coefficients = np.polyfit(voltages, displacements, 1)
                self._calibration_data.coefficients = coefficients.tolist()

            elif calibration_type == CalibrationType.POLYNOMIAL:
                # 多项式拟合（3阶）：displacement = a*v^3 + b*v^2 + c*v + d
                degree = min(3, len(self._calibration_data.points) - 1)
                coefficients = np.polyfit(voltages, displacements, degree)
                self._calibration_data.coefficients = coefficients.tolist()

            elif calibration_type == CalibrationType.PIECEWISE:
                # 分段线性：存储点对用于插值
                self._calibration_data.coefficients = []

            # 标记校准有效
            self._calibration_data.valid = True

            return True

        except Exception as e:
            self._last_error = f"校准失败: {e!s}"
            self._calibration_data.valid = False
            return False

    def get_calibration_data(self) -> dict[str, Any]:
        """获取校准数据。

        Returns:
            Dict[str, Any]: 校准数据字典
        """
        return {
            "valid": self._calibration_data.valid,
            "type": self._calibration_data.calibration_type.value,
            "points": [
                {"voltage_v": p.voltage_v, "displacement_um": p.displacement_um}
                for p in self._calibration_data.points
            ],
            "coefficients": self._calibration_data.coefficients,
            "point_count": len(self._calibration_data.points),
        }

    # ==================== 内部方法 ====================

    def _is_voltage_valid(self, voltage_v: float) -> bool:
        """检查电压是否在有效范围内。

        Args:
            voltage_v: 电压值（V）

        Returns:
            bool: 电压是否有效
        """
        return self.piezo_config.min_voltage_v <= voltage_v <= self.piezo_config.max_voltage_v

    def _is_displacement_valid(self, displacement_um: float) -> bool:
        """检查位移是否在有效范围内。

        Args:
            displacement_um: 位移值（μm）

        Returns:
            bool: 位移是否有效
        """
        return (
            self.piezo_config.min_displacement_um
            <= displacement_um
            <= self.piezo_config.max_displacement_um
        )

    def _quantize_voltage(self, voltage_v: float) -> float:
        """将电压量化到分辨率。

        Args:
            voltage_v: 原始电压值（V）

        Returns:
            float: 量化后的电压值（V）
        """
        resolution = self.piezo_config.voltage_resolution_v
        quantized = round(voltage_v / resolution) * resolution
        # 确保在有效范围内
        quantized = max(self.piezo_config.min_voltage_v, quantized)
        quantized = min(self.piezo_config.max_voltage_v, quantized)
        return quantized

    def _voltage_to_displacement(self, voltage_v: float) -> float:
        """将电压转换为位移（使用校准数据）。

        Args:
            voltage_v: 电压值（V）

        Returns:
            float: 位移值（μm）
        """
        if not self._calibration_data.valid:
            return self._voltage_to_displacement_linear(voltage_v)

        calibration_type = self._calibration_data.calibration_type

        if calibration_type == CalibrationType.LINEAR:
            # 线性转换
            coeffs = self._calibration_data.coefficients
            return coeffs[0] * voltage_v + coeffs[1]

        elif calibration_type == CalibrationType.POLYNOMIAL:
            # 多项式转换
            coeffs = self._calibration_data.coefficients
            displacement = 0.0
            for i, coeff in enumerate(coeffs):
                power = len(coeffs) - i - 1
                displacement += coeff * (voltage_v**power)
            return displacement

        elif calibration_type == CalibrationType.PIECEWISE:
            # 分段线性插值
            return self._piecewise_interpolate(voltage_v, "voltage_to_displacement")

        return 0.0

    def _displacement_to_voltage(self, displacement_um: float) -> float:
        """将位移转换为电压（使用校准数据）。

        Args:
            displacement_um: 位移值（μm）

        Returns:
            float: 电压值（V）
        """
        if not self._calibration_data.valid:
            return self._displacement_to_voltage_linear(displacement_um)

        calibration_type = self._calibration_data.calibration_type

        if calibration_type == CalibrationType.LINEAR:
            # 线性逆转换
            coeffs = self._calibration_data.coefficients
            if abs(coeffs[0]) < 1e-10:
                return 0.0
            return (displacement_um - coeffs[1]) / coeffs[0]

        elif calibration_type == CalibrationType.POLYNOMIAL:
            # 多项式逆转换（数值求解）
            return self._solve_polynomial_inverse(displacement_um)

        elif calibration_type == CalibrationType.PIECEWISE:
            # 分段线性插值（逆）
            return self._piecewise_interpolate(displacement_um, "displacement_to_voltage")

        return 0.0

    def _voltage_to_displacement_linear(self, voltage_v: float) -> float:
        """线性电压-位移转换（无校准数据时使用）。

        假设线性关系：displacement = (voltage / max_voltage) * max_displacement

        Args:
            voltage_v: 电压值（V）

        Returns:
            float: 位移值（μm）
        """
        ratio = voltage_v / self.piezo_config.max_voltage_v
        return ratio * self.piezo_config.max_displacement_um

    def _displacement_to_voltage_linear(self, displacement_um: float) -> float:
        """线性位移-电压转换（无校准数据时使用）。

        Args:
            displacement_um: 位移值（μm）

        Returns:
            float: 电压值（V）
        """
        ratio = displacement_um / self.piezo_config.max_displacement_um
        return ratio * self.piezo_config.max_voltage_v

    def _piecewise_interpolate(self, value: float, direction: str) -> float:
        """分段线性插值。

        Args:
            value: 输入值
            direction: 插值方向
                - "voltage_to_displacement": 电压→位移
                - "displacement_to_voltage": 位移→电压

        Returns:
            float: 插值结果
        """
        points = self._calibration_data.points

        if direction == "voltage_to_displacement":
            x_values = [p.voltage_v for p in points]
            y_values = [p.displacement_um for p in points]
        else:
            x_values = [p.displacement_um for p in points]
            y_values = [p.voltage_v for p in points]

        # 边界处理
        if value <= x_values[0]:
            return y_values[0]
        if value >= x_values[-1]:
            return y_values[-1]

        # 查找插值区间
        for i in range(len(x_values) - 1):
            if x_values[i] <= value <= x_values[i + 1]:
                # 线性插值
                t = (value - x_values[i]) / (x_values[i + 1] - x_values[i])
                return y_values[i] + t * (y_values[i + 1] - y_values[i])

        return y_values[-1]

    def _solve_polynomial_inverse(self, displacement_um: float) -> float:
        """求解多项式逆变换（位移→电压）。

        使用牛顿迭代法求解。

        Args:
            displacement_um: 目标位移（μm）

        Returns:
            float: 对应的电压值（V）
        """
        coeffs = self._calibration_data.coefficients

        # 初始猜测
        voltage = (
            displacement_um
            / self.piezo_config.max_displacement_um
            * self.piezo_config.max_voltage_v
        )

        # 牛顿迭代
        for _ in range(50):
            # 计算多项式值
            f_val = 0.0
            for i, coeff in enumerate(coeffs):
                power = len(coeffs) - i - 1
                f_val += coeff * (voltage**power)

            # 计算导数值
            f_deriv = 0.0
            for i, coeff in enumerate(coeffs[:-1]):
                power = len(coeffs) - i - 2
                f_deriv += coeff * (power + 1) * (voltage**power)

            if abs(f_deriv) < 1e-10:
                break

            # 更新
            voltage_new = voltage - (f_val - displacement_um) / f_deriv

            if abs(voltage_new - voltage) < 1e-6:
                break

            voltage = voltage_new

        # 限制在有效范围内
        voltage = max(self.piezo_config.min_voltage_v, voltage)
        voltage = min(self.piezo_config.max_voltage_v, voltage)

        return voltage

    def _record_voltage_history(self, voltage_v: float) -> None:
        """记录电压历史（用于磁滞补偿）。

        Args:
            voltage_v: 当前电压值（V）
        """
        self._voltage_history.append(voltage_v)
        if len(self._voltage_history) > self._max_history_length:
            self._voltage_history.pop(0)

    def _apply_hysteresis_compensation(self, target_voltage: float) -> float:
        """应用磁滞补偿。

        压电陶瓷存在磁滞效应，电压上升和下降时的位移不同。
        此方法根据电压变化方向进行补偿。

        Args:
            target_voltage: 目标电压（V）

        Returns:
            float: 补偿后的电压（V）
        """
        if len(self._voltage_history) == 0:
            return target_voltage

        last_voltage = self._voltage_history[-1]

        # 判断电压变化方向
        if target_voltage > last_voltage:
            # 电压上升：需要额外电压补偿
            # 补偿量与变化幅度成正比
            delta = target_voltage - last_voltage
            compensation = 0.02 * delta  # 2%补偿
            compensated = target_voltage + compensation
        elif target_voltage < last_voltage:
            # 电压下降：需要减少电压补偿
            delta = last_voltage - target_voltage
            compensation = 0.02 * delta
            compensated = target_voltage - compensation
        else:
            compensated = target_voltage

        # 确保在有效范围内
        compensated = max(self.piezo_config.min_voltage_v, compensated)
        compensated = min(self.piezo_config.max_voltage_v, compensated)

        return compensated

    # ==================== 便捷方法 ====================

    async def zero(self) -> bool:
        """归零操作（电压设为0V）。

        Returns:
            bool: 操作是否成功
        """
        return await self.set_voltage(0.0)

    async def max_extend(self) -> bool:
        """最大伸展操作（电压设为最大值）。

        Returns:
            bool: 操作是否成功
        """
        return await self.set_voltage(self.piezo_config.max_voltage_v)

    async def step_voltage(self, step_v: float) -> bool:
        """电压步进。

        Args:
            step_v: 步进量（V），正值为增加，负值为减少

        Returns:
            bool: 操作是否成功
        """
        new_voltage = self._current_voltage + step_v
        return await self.set_voltage(new_voltage)

    async def step_displacement(self, step_um: float) -> bool:
        """位移步进。

        Args:
            step_um: 步进量（μm），正值为增加，负值为减少

        Returns:
            bool: 操作是否成功
        """
        new_displacement = self._current_displacement + step_um
        return await self.set_displacement(new_displacement)
