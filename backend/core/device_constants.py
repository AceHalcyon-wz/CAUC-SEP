"""
文件名: device_constants.py
路径: backend/core/
功能: 设备硬件常量配置，Modbus寄存器地址、设备参数范围等
版本: v1.0
创建日期: 2026-03-25
作者: Backend Engineer Agent

依赖:
    - 无外部依赖

安全约束:
    - 所有寄存器地址必须与硬件手册一致
    - 参数范围必须符合设备安全规范
    - 修改寄存器地址前必须验证硬件兼容性
"""

from enum import IntEnum
from typing import Dict, Any


# ==================== DM2C步进驱动器寄存器地址 ====================

class DM2CRegisterAddress(IntEnum):
    """
    DM2C步进驱动器Modbus寄存器地址枚举。
    
    参考文档：DM2C-RS556用户手册 V1.8
    
    注意：
    - 所有地址均为Modbus寄存器地址（非协议地址）
    - 读取使用功能码03（读保持寄存器）
    - 写入使用功能码06（写单个寄存器）或16（写多个寄存器）
    """
    
    # ==================== 基础控制寄存器 ====================
    CONTROL_WORD = 0x0000  # 控制字，用于启动、停止、急停等操作
    STATUS_WORD = 0x0001  # 状态字，反映驱动器当前状态
    OPERATION_MODE = 0x0002  # 运行模式选择：0-位置模式，1-速度模式，2-PR模式
    
    # ==================== 位置控制寄存器 ====================
    TARGET_POSITION_L = 0x0003  # 目标位置低16位
    TARGET_POSITION_H = 0x0004  # 目标位置高16位
    CURRENT_POSITION_L = 0x0005  # 当前位置低16位（只读）
    CURRENT_POSITION_H = 0x0006  # 当前位置高16位（只读）
    
    # ==================== 速度控制寄存器 ====================
    TARGET_SPEED_L = 0x0007  # 目标速度低16位
    TARGET_SPEED_H = 0x0008  # 目标速度高16位
    CURRENT_SPEED_L = 0x0009  # 当前速度低16位（只读）
    CURRENT_SPEED_H = 0x000A  # 当前速度高16位（只读）
    
    # ==================== 加减速控制寄存器 ====================
    ACCELERATION_TIME = 0x000B  # 加速时间（单位：ms）
    DECELERATION_TIME = 0x000C  # 减速时间（单位：ms）
    
    # ==================== 报警与状态寄存器 ====================
    ALARM_CODE = 0x000D  # 报警代码（只读）
    ALARM_CLEAR = 0x000E  # 报警清除（写入1清除报警）
    
    # ==================== 软件限位寄存器 ====================
    POSITIVE_LIMIT_L = 0x0010  # 正向软件限位低16位
    POSITIVE_LIMIT_H = 0x0011  # 正向软件限位高16位
    NEGATIVE_LIMIT_L = 0x0012  # 负向软件限位低16位
    NEGATIVE_LIMIT_H = 0x0013  # 负向软件限位高16位
    
    # ==================== PR模式寄存器（位置表） ====================
    PR_START_SEGMENT = 0x0020  # PR模式起始段号
    PR_CURRENT_SEGMENT = 0x0021  # PR模式当前执行段号（只读）
    PR_TABLE_BASE = 0x0100  # PR位置表基地址（每段占用10个寄存器）
    
    # ==================== JOG控制寄存器 ====================
    JOG_SPEED = 0x0030  # JOG速度
    JOG_DIRECTION = 0x0031  # JOG方向：0-负向，1-正向
    JOG_START = 0x0032  # JOG启动：写入1开始JOG
    
    # ==================== 回零控制寄存器 ====================
    HOME_MODE = 0x0040  # 回零模式
    HOME_SPEED = 0x0041  # 回零速度
    HOME_START = 0x0042  # 回零启动：写入1开始回零
    
    # ==================== 全局急停寄存器 ====================
    EMERGENCY_STOP = 0x0200  # 全局急停寄存器：写入1立即停止所有运动


# ==================== DM2C控制字命令 ====================

class DM2CControlCommand(IntEnum):
    """
    DM2C控制字命令枚举。
    
    用于写入CONTROL_WORD寄存器（0x0000）
    """
    
    STOP = 0x0000  # 停止运动
    START = 0x0001  # 启动运动
    EMERGENCY_STOP = 0x0002  # 急停
    RESET = 0x0003  # 复位
    ENABLE = 0x0004  # 使能
    DISABLE = 0x0005  # 去使能


# ==================== DM2C运行模式 ====================

class DM2COperationMode(IntEnum):
    """
    DM2C运行模式枚举。
    
    用于写入OPERATION_MODE寄存器（0x0002）
    """
    
    POSITION_MODE = 0  # 位置模式
    VELOCITY_MODE = 1  # 速度模式
    PR_MODE = 2  # PR模式（位置表模式）
    JOG_MODE = 3  # JOG模式


# ==================== DM2C状态字标志位 ====================

class DM2CStatusBit(IntEnum):
    """
    DM2C状态字标志位枚举。
    
    用于解析STATUS_WORD寄存器（0x0001）的各个标志位
    """
    
    READY = 0  # 驱动器就绪
    RUNNING = 1  # 运动中
    ALARM = 2  # 报警状态
    LIMIT_POSITIVE = 3  # 正向限位触发
    LIMIT_NEGATIVE = 4  # 负向限位触发
    HOME_COMPLETE = 5  # 回零完成
    PR_COMPLETE = 6  # PR模式执行完成


# ==================== DM2C报警代码映射 ====================

DM2C_ALARM_CODES: Dict[int, Dict[str, Any]] = {
    0x00: {"severity": "info", "zh": "无报警", "en": "No alarm"},
    0x01: {"severity": "critical", "zh": "过流保护", "en": "Overcurrent protection"},
    0x02: {"severity": "critical", "zh": "过压保护", "en": "Overvoltage protection"},
    0x03: {"severity": "critical", "zh": "欠压保护", "en": "Undervoltage protection"},
    0x04: {"severity": "critical", "zh": "过热保护", "en": "Overheat protection"},
    0x05: {"severity": "warning", "zh": "编码器错误", "en": "Encoder error"},
    0x06: {"severity": "critical", "zh": "电机堵转", "en": "Motor stall"},
    0x07: {"severity": "warning", "zh": "通信错误", "en": "Communication error"},
    0x08: {"severity": "warning", "zh": "限位触发", "en": "Limit triggered"},
    0x09: {"severity": "critical", "zh": "EEPROM错误", "en": "EEPROM error"},
}


# ==================== DM2C参数范围约束 ====================

DM2C_PARAMETER_LIMITS: Dict[str, Dict[str, Any]] = {
    "speed": {
        "min": 1,
        "max": 100000,
        "default": 500,
        "unit": "pulse/s",
        "description": "运动速度（脉冲/秒）"
    },
    "acceleration": {
        "min": 10,
        "max": 10000,
        "default": 100,
        "unit": "ms",
        "description": "加减速时间（毫秒）"
    },
    "position": {
        "min": -2147483648,
        "max": 2147483647,
        "default": 0,
        "unit": "pulse",
        "description": "位置（脉冲）"
    },
    "jog_speed": {
        "min": 1,
        "max": 10000,
        "default": 1000,
        "unit": "pulse/s",
        "description": "JOG速度（脉冲/秒）"
    },
}


# ==================== 温控器寄存器地址 ====================

class TemperatureControllerRegister(IntEnum):
    """
    温控器Modbus寄存器地址枚举。
    
    适配标准Modbus温控器协议
    """
    
    # ==================== 温度控制寄存器 ====================
    TARGET_TEMPERATURE = 0x0000  # 目标温度（单位：0.1°C）
    CURRENT_TEMPERATURE = 0x0001  # 当前温度（只读，单位：0.1°C）
    
    # ==================== PID参数寄存器 ====================
    PID_KP = 0x0010  # PID比例系数（单位：0.01）
    PID_KI = 0x0011  # PID积分系数（单位：0.01）
    PID_KD = 0x0012  # PID微分系数（单位：0.01）
    
    # ==================== 报警寄存器 ====================
    ALARM_STATUS = 0x0020  # 报警状态
    ALARM_HIGH_LIMIT = 0x0021  # 高温报警阈值
    ALARM_LOW_LIMIT = 0x0022  # 低温报警阈值
    
    # ==================== 输出控制寄存器 ====================
    OUTPUT_POWER = 0x0030  # 输出功率百分比（只读，0-100）
    OUTPUT_ENABLE = 0x0031  # 输出使能：0-关闭，1-开启


# ==================== 压电控制器寄存器地址 ====================

class PiezoControllerRegister(IntEnum):
    """
    压电控制器Modbus寄存器地址枚举。
    """
    
    # ==================== 电压控制寄存器 ====================
    CHANNEL_1_VOLTAGE = 0x0000  # 通道1电压（单位：mV）
    CHANNEL_2_VOLTAGE = 0x0001  # 通道2电压（单位：mV）
    CHANNEL_3_VOLTAGE = 0x0002  # 通道3电压（单位：mV）
    
    # ==================== 位移反馈寄存器 ====================
    CHANNEL_1_DISPLACEMENT = 0x0010  # 通道1位移（只读，单位：nm）
    CHANNEL_2_DISPLACEMENT = 0x0011  # 通道2位移（只读，单位：nm）
    CHANNEL_3_DISPLACEMENT = 0x0012  # 通道3位移（只读，单位：nm）
    
    # ==================== 控制寄存器 ====================
    OUTPUT_ENABLE = 0x0020  # 输出使能：0-关闭，1-开启
    ZERO_ALL_CHANNELS = 0x0021  # 所有通道归零


# ==================== 皮安表寄存器地址 ====================

class PicoammeterRegister(IntEnum):
    """
    皮安表Modbus寄存器地址枚举。
    """
    
    # ==================== 测量寄存器 ====================
    CURRENT_VALUE = 0x0000  # 当前电流值（单位：nA）
    CURRENT_RANGE = 0x0001  # 电流量程
    
    # ==================== 配置寄存器 ====================
    SAMPLE_RATE = 0x0010  # 采样率（单位：Hz）
    FILTER_ENABLE = 0x0011  # 滤波使能：0-关闭，1-开启
    FILTER_TIME_CONSTANT = 0x0012  # 滤波时间常数（单位：ms）


# ==================== 电磁铁控制器寄存器地址 ====================

class ElectromagnetRegister(IntEnum):
    """
    电磁铁控制器Modbus寄存器地址枚举。
    """
    
    # ==================== 电流控制寄存器 ====================
    TARGET_CURRENT = 0x0000  # 目标电流（单位：mA）
    CURRENT_CURRENT = 0x0001  # 当前电流（只读，单位：mA）
    
    # ==================== 状态寄存器 ====================
    OUTPUT_STATUS = 0x0010  # 输出状态：0-关闭，1-开启
    ALARM_STATUS = 0x0011  # 报警状态
    
    # ==================== 配置寄存器 ====================
    MAX_CURRENT_LIMIT = 0x0020  # 最大电流限制（单位：mA）
    RAMP_TIME = 0x0021  # 电流爬升时间（单位：ms）


# ==================== 通用Modbus通信参数 ====================

MODBUS_COMMON_PARAMS: Dict[str, Any] = {
    "timeout": {
        "default": 1.0,
        "min": 0.1,
        "max": 30.0,
        "description": "通信超时时间（秒）"
    },
    "retry_count": {
        "default": 3,
        "min": 1,
        "max": 10,
        "description": "通信失败重试次数"
    },
    "retry_delay": {
        "default": 0.1,
        "min": 0.01,
        "max": 5.0,
        "description": "重试延迟时间（秒）"
    },
    "baudrate_options": [9600, 19200, 38400, 57600, 115200],
    "parity_options": ["N", "E", "O", "M"],
    "stopbits_options": [1, 2],
    "bytesize_options": [5, 6, 7, 8],
}


# ==================== 设备安全参数 ====================

DEVICE_SAFETY_PARAMS: Dict[str, Any] = {
    "emergency_stop_priority": 0,  # 急停指令最高优先级
    "position_check_enabled": True,  # 启用位置预校验
    "limit_check_enabled": True,  # 启用限位校验
    "alarm_check_enabled": True,  # 启用报警状态检查
    "auto_disconnect_on_alarm": False,  # 报警时是否自动断开连接
    "max_continuous_operation_time": 3600,  # 最大连续运行时间（秒）
}
