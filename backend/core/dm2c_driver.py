"""
DM2C步进驱动器驱动

文件名: dm2c_driver.py
路径: backend/core/
功能: 雷赛DM2C系列步进驱动器Modbus RTU通信驱动
版本: v1.0.0

功能说明：
- Modbus RTU通信
- PR模式支持（16段位置表）
- 状态字完整解析
- 报警代码读取和解析
- 报警描述本地化（中英文）
- 报警清除功能
- 回零操作
- JOG模式
- 参数保存到EEPROM
- 恢复出厂设置
- 报警复位

安全警告：
- 实验时必须有人值守
- 首次使用前验证限位参数

参考文档：DM2C-RS556用户手册 V1.8

作者：CAUC-SEP 开发团队
创建日期：2024-01-15
最后更新：2026-03-14
"""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

try:
    from pymodbus.client import ModbusSerialClient
    from pymodbus.exceptions import ModbusException

    PYMODBUS_AVAILABLE = True
except ImportError:
    PYMODBUS_AVAILABLE = False
    ModbusException = Exception  # 类型别名，用于异常处理
    print("Warning: pymodbus not installed. Running in simulation mode.")

# 向后兼容：PYMUSBUS_AVAILABLE 是 PYMODBUS_AVAILABLE 的别名（修复拼写错误）
PYMUSBUS_AVAILABLE = PYMODBUS_AVAILABLE

from .abstract import AbstractStepper, DeviceStatus, SoftwareLimitConfig

logger = logging.getLogger(__name__)


# 单位换算常量
DEFAULT_STEPS_PER_MM = 1600


def mm_to_steps(mm: float, steps_per_mm: int = DEFAULT_STEPS_PER_MM) -> int:
    """
    毫米转步数

    Args:
        mm: 距离（毫米）
        steps_per_mm: 每毫米步数

    Returns:
        int: 步数
    """
    return int(mm * steps_per_mm)


def steps_to_mm(steps: int, steps_per_mm: int = DEFAULT_STEPS_PER_MM) -> float:
    """
    步数转毫米

    Args:
        steps: 步数
        steps_per_mm: 每毫米步数

    Returns:
        float: 距离（毫米）
    """
    return steps / steps_per_mm


class AlarmSeverity(Enum):
    """
    报警严重程度枚举。

    Attributes:
        CRITICAL: 严重报警，需要立即处理
        WARNING: 警告，需要关注
        INFO: 信息提示
    """

    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"


@dataclass
class AlarmInfo:
    """
    报警信息数据类。

    Attributes:
        code: 报警代码
        name_zh: 中文名称
        name_en: 英文名称
        description_zh: 中文描述
        description_en: 英文描述
        severity: 严重程度
        possible_causes: 可能原因列表
        solutions: 解决方案列表
    """

    code: int
    name_zh: str
    name_en: str
    description_zh: str
    description_en: str
    severity: AlarmSeverity
    possible_causes: list[str]
    solutions: list[str]


# 报警代码映射（向后兼容）
# 根据DM2C-RS556用户手册V1.8定义
ALARM_CODES = {
    0x01: "过流",
    0x02: "过压",
    0x40: "电流采样回路故障",
    0x80: "锁轴（缺相）故障",
    0x100: "参数自整定故障",
    0x200: "EEPROM故障",
    0x210: "输入IO配置重复",
}


# 完整报警信息映射表（基于DM2C-RS556用户手册V1.8）
ALARM_INFO_MAP: dict[int, AlarmInfo] = {
    0x01: AlarmInfo(
        code=0x01,
        name_zh="过流保护",
        name_en="Over Current Protection",
        description_zh="电机电流超过额定值，驱动器自动切断输出以保护电机和驱动器",
        description_en="Motor current exceeds rated value, driver automatically cuts output to protect motor and driver",
        severity=AlarmSeverity.CRITICAL,
        possible_causes=[
            "电机绕组短路或接地",
            "电机相间接线错误",
            "电机负载过大或卡死",
            "驱动器输出短路",
            "加速时间设置过短",
            "电机与驱动器功率不匹配",
        ],
        solutions=[
            "检查电机绕组绝缘，排除短路或接地故障",
            "确认电机接线正确（U-V-W相序）",
            "减小负载或检查机械传动系统",
            "检查驱动器输出端子，排除短路",
            "增大加速时间参数（PA-12）",
            "更换与负载匹配的电机或驱动器",
        ],
    ),
    0x02: AlarmInfo(
        code=0x02,
        name_zh="过压保护",
        name_en="Over Voltage Protection",
        description_zh="直流母线电压超过安全阈值，驱动器自动停机保护",
        description_en="DC bus voltage exceeds safety threshold, driver automatically stops for protection",
        severity=AlarmSeverity.CRITICAL,
        possible_causes=[
            "输入电源电压过高",
            "减速时间过短导致再生能量过大",
            "外接制动电阻未连接或失效",
            "电源变压器容量不足",
        ],
        solutions=[
            "检查输入电源电压是否在允许范围内（AC 24-50V）",
            "增大减速时间参数（PA-13）",
            "连接合适功率的外接制动电阻",
            "增大电源变压器容量或改善供电质量",
        ],
    ),
    0x40: AlarmInfo(
        code=0x40,
        name_zh="电流采样故障",
        name_en="Current Sampling Fault",
        description_zh="驱动器电流采样电路异常，无法正确检测电机电流",
        description_en="Driver current sampling circuit abnormal, unable to correctly detect motor current",
        severity=AlarmSeverity.CRITICAL,
        possible_causes=[
            "驱动器内部电流采样电路损坏",
            "采样电阻开路或短路",
            "ADC芯片故障",
            "驱动器过热导致元件失效",
        ],
        solutions=[
            "断电重启驱动器尝试恢复",
            "检查驱动器散热条件，清理散热片",
            "如故障持续，联系厂家维修或更换驱动器",
        ],
    ),
    0x80: AlarmInfo(
        code=0x80,
        name_zh="锁轴故障",
        name_en="Motor Lock Fault",
        description_zh="电机缺相或堵转，无法正常运转",
        description_en="Motor phase loss or locked rotor, unable to operate normally",
        severity=AlarmSeverity.CRITICAL,
        possible_causes=[
            "电机相线断开或接触不良",
            "电机绕组断路",
            "机械负载卡死",
            "电机功率不足",
            "驱动器输出故障",
        ],
        solutions=[
            "检查电机相线连接是否牢固",
            "用万用表测量电机绕组电阻，确认无断路",
            "手动转动电机轴，检查机械系统是否卡死",
            "更换更大功率的电机",
            "检查驱动器输出电压是否正常",
        ],
    ),
    0x100: AlarmInfo(
        code=0x100,
        name_zh="参数自整定故障",
        name_en="Auto Tuning Fault",
        description_zh="参数自整定过程失败，无法自动优化电机参数",
        description_en="Auto tuning process failed, unable to automatically optimize motor parameters",
        severity=AlarmSeverity.WARNING,
        possible_causes=[
            "电机未连接或连接错误",
            "电机负载过大无法完成整定",
            "整定过程中电机运动受限",
            "电机参数设置错误",
            "驱动器与电机功率不匹配",
        ],
        solutions=[
            "确认电机已正确连接",
            "卸载负载后重新进行整定",
            "确保整定过程中电机可自由运动",
            "核对电机铭牌参数设置",
            "更换匹配的电机或驱动器",
        ],
    ),
    0x200: AlarmInfo(
        code=0x200,
        name_zh="EEPROM故障",
        name_en="EEPROM Fault",
        description_zh="EEPROM读写异常，参数无法保存或读取",
        description_en="EEPROM read/write abnormal, parameters cannot be saved or read",
        severity=AlarmSeverity.WARNING,
        possible_causes=[
            "EEPROM芯片损坏",
            "写入过程中断电",
            "参数保存操作过于频繁",
            "驱动器内部数据总线故障",
        ],
        solutions=[
            "尝试恢复出厂设置后重新配置参数",
            "确保参数保存过程中不断电",
            "减少不必要的参数保存操作",
            "如故障持续，联系厂家维修或更换驱动器",
        ],
    ),
    0x210: AlarmInfo(
        code=0x210,
        name_zh="IO配置重复",
        name_en="IO Configuration Duplicate",
        description_zh="输入IO功能配置重复，多个输入端子分配了相同功能",
        description_en="Input IO function configuration duplicate, multiple input terminals assigned same function",
        severity=AlarmSeverity.WARNING,
        possible_causes=[
            "多个输入端子配置为相同功能",
            "参数设置冲突",
            "参数导入错误",
        ],
        solutions=[
            "检查并修改IO功能分配参数（Pr4.02-Pr4.08）",
            "确保每个功能只分配给一个输入端子",
            "恢复出厂设置后重新配置IO功能",
        ],
    ),
}


def get_alarm_info(alarm_code: int, language: str = "zh") -> dict[str, Any]:
    """
    获取报警详细信息。

    Args:
        alarm_code: 报警代码
        language: 语言选择，"zh"为中文，"en"为英文

    Returns:
        Dict[str, Any]: 包含报警详细信息的字典
    """
    if alarm_code == 0:
        return {
            "code": 0,
            "name": "无报警" if language == "zh" else "No Alarm",
            "description": "设备运行正常" if language == "zh" else "Device operating normally",
            "severity": AlarmSeverity.INFO.value,
            "possible_causes": [],
            "solutions": [],
        }

    info = ALARM_INFO_MAP.get(alarm_code)
    if info is None:
        return {
            "code": alarm_code,
            "name": (
                f"未知报警(0x{alarm_code:04X})"
                if language == "zh"
                else f"Unknown Alarm(0x{alarm_code:04X})"
            ),
            "description": (
                "未定义的报警代码，请参考驱动器手册"
                if language == "zh"
                else "Undefined alarm code, please refer to driver manual"
            ),
            "severity": AlarmSeverity.WARNING.value,
            "possible_causes": [],
            "solutions": ["联系技术支持" if language == "zh" else "Contact technical support"],
        }

    return {
        "code": info.code,
        "name": info.name_zh if language == "zh" else info.name_en,
        "description": info.description_zh if language == "zh" else info.description_en,
        "severity": info.severity.value,
        "possible_causes": info.possible_causes,
        "solutions": info.solutions,
    }


# 状态字位定义（基于DM2C-RS556用户手册V1.8，地址0x1003）
STATUS_FAULT_BIT = 0x01  # Bit0: 故障位（1=故障）
STATUS_ENABLE_BIT = 0x02  # Bit1: 使能状态（1=使能）
STATUS_RUNNING_BIT = 0x04  # Bit2: 运行状态（1=运行中）
STATUS_INVALID_BIT = 0x08  # Bit3: 无效位（1=无效状态）
STATUS_CMD_COMPLETE_BIT = 0x10  # Bit4: 命令完成（1=完成）
STATUS_PATH_COMPLETE_BIT = 0x20  # Bit5: 路径完成（1=完成）
STATUS_HOME_COMPLETE_BIT = 0x40  # Bit6: 回零完成（1=完成）


# 控制字命令（地址0x1801）
# 根据DM2C-RS556用户手册V1.8定义
CMD_JOG_POS = 0x4001  # 正向JOG（需50ms间隔连续发送）
CMD_JOG_NEG = 0x4002  # 负向JOG（需50ms间隔连续发送）
CMD_JOG_STOP = 0x4000  # JOG停止
CMD_CLEAR_ALARM = 0x0001  # 清除报警（别名）
CMD_RESET_ALARM = 0x1111  # 复位当前报警
CMD_RESET_HISTORY_ALARM = 0x1122  # 复位历史报警
CMD_SAVE_PARAM = 0x2211  # 保存参数到EEPROM
CMD_PARAM_INIT = 0x2222  # 参数初始化（不含电机参数）
CMD_FACTORY_RESET = 0x2233  # 恢复出厂设置
CMD_SAVE_MAPPING = 0x2244  # 保存映射参数到EEPROM


# 触发寄存器命令（地址0x6002，Pr8.02）
# 根据DM2C-RS556用户手册V1.8定义
TRIGGER_PATH_BASE = 0x0100  # 路径触发基址：0x01P (P为路径号0~15)
TRIGGER_HOME = 0x020  # 回零触发（边沿触发）
TRIGGER_SET_ZERO = 0x021  # 当前位置手动设零
TRIGGER_EMERGENCY_STOP = 0x040  # 急停触发

# 触发寄存器读值定义
TRIGGER_STATUS_IDLE = 0x0000  # 定位完成，可接收新数据
TRIGGER_STATUS_RUNNING = 0x1000  # 路径运行中（0x10P，P为路径号）
TRIGGER_STATUS_WAITING = 0x200  # 指令完成等待定位


# PR路径配置寄存器基地址
PR_PATH_BASE_ADDR = 0x6200
PR_PATH_ENTRY_SIZE = 8  # 每个路径占8个寄存器


# PR路径运动模式定义（根据DM2C-RS556用户手册V1.8）
# 运动模式寄存器(Pr9.00等)的位定义：
# Bit0-3: TYPE - 运动类型
# Bit4: INS - 插断控制 (0=可插断, 1=屏蔽插断)
# Bit5: OVLP - 重叠功能 (0=不重叠, 1=重叠)
# Bit6: POS - 位置模式 (0=绝对位置, 1=相对位置)
# Bit8-13: JUMP_ADDR - 跳转目标路径号(0-15)
# Bit14: JUMP - 跳转使能 (0=不跳转, 1=跳转)
PR_MODE_TYPE_MASK = 0x000F  # Bit0-3: 运动类型掩码
PR_MODE_INS_MASK = 0x0010  # Bit4: 插断控制掩码
PR_MODE_OVLP_MASK = 0x0020  # Bit5: 重叠功能掩码
PR_MODE_POS_MASK = 0x0040  # Bit6: 位置模式掩码
PR_MODE_JUMP_ADDR_MASK = 0x3F00  # Bit8-13: 跳转地址掩码
PR_MODE_JUMP_MASK = 0x4000  # Bit14: 跳转使能掩码

# 运动类型常量
PR_TYPE_NO_ACTION = 0  # 无动作
PR_TYPE_POSITION = 1  # 位置定位
PR_TYPE_VELOCITY = 2  # 速度运行
PR_TYPE_HOME = 3  # 回零

# 插断控制常量
PR_INS_INTERRUPTIBLE = 0  # 可插断（默认）
PR_INS_NON_INTERRUPTIBLE = 1  # 屏蔽插断

# 重叠功能常量
PR_OVLP_DISABLE = 0  # 不重叠
PR_OVLP_ENABLE = 1  # 重叠

# 位置模式常量
PR_POS_ABSOLUTE = 0  # 绝对位置
PR_POS_RELATIVE = 1  # 相对位置


# 数字输入配置寄存器地址（Pr4.02-Pr4.08）
DI_CONFIG_ADDRS = {
    1: 0x0145,  # DI1: Pr4.02
    2: 0x0147,  # DI2: Pr4.03
    3: 0x0149,  # DI3: Pr4.04
    4: 0x014B,  # DI4: Pr4.05
    5: 0x014D,  # DI5: Pr4.06
    6: 0x014F,  # DI6: Pr4.07
    7: 0x0151,  # DI7: Pr4.08
}


# 数字输出配置寄存器地址（Pr4.11-Pr4.13）
# 修正：根据DM2C-RS556用户手册V1.8，DO配置地址为Pr4.11-Pr4.13
DO_CONFIG_ADDRS = {
    1: 0x0157,  # DO1: Pr4.11
    2: 0x0159,  # DO2: Pr4.12
    3: 0x015B,  # DO3: Pr4.13
}


# DI功能代码定义（根据DM2C-RS556用户手册V1.8）
# 常开模式：低8位为功能代码
# 常闭模式：功能代码 + 0x80
DI_FUNCTIONS = {
    0x00: "无效输入",
    0x07: "报警清除",
    0x08: "使能",
    0x20: "触发命令(CTRG)",
    0x21: "回零触发(HOME)",
    0x22: "强制急停(STP)",
    0x23: "正向JOG(PJOG)",
    0x24: "反向JOG(NJOG)",
    0x25: "正向限位(POT)",
    0x26: "反向限位(NOT)",
    0x27: "原点信号(ORG)",
    0x28: "路径地址0(ADDR0)",
    0x29: "路径地址1(ADDR1)",
    0x2A: "路径地址2(ADDR2)",
    0x2B: "路径地址3(ADDR3)",
    0x2C: "JOG速度2",
}


# DO功能代码定义（根据DM2C-RS556用户手册V1.8）
DO_FUNCTIONS = {
    0x00: "无效输出",
    0x20: "指令完成(CMD_OK)",
    0x21: "路径完成(MC_OK)",
    0x22: "回零完成(HOME_OK)",
    0x23: "到位完成(INP)",
    0x24: "抱闸输出(BRK)",
    0x25: "报警输出(ALM)",
}


# IO状态寄存器地址
REG_DI_STATUS = 0x0179  # DI状态（Pr4.28）
REG_DO_STATUS = 0x017B  # DO状态（Pr4.29）


# 回零参数寄存器地址（Pr8组）
REG_HOME_MODE = 0x0280  # Pr8.00: 回零模式
REG_HOME_SPEED_HIGH = 0x0281  # Pr8.01: 回零速度（高速）
REG_HOME_SPEED_LOW = 0x0282  # Pr8.02: 回零速度（低速）
REG_HOME_OFFSET = 0x0283  # Pr8.03: 回零偏移
REG_HOME_DIRECTION = 0x0284  # Pr8.04: 回零方向


# 通信参数寄存器地址（Pr5组）- 用于在线修改通信参数
REG_485_BAUDRATE = 0x01BD  # Pr5.22: 485波特率 (0-6: 2400-115200)
REG_485_ID = 0x01BF  # Pr5.23: 485从站地址 (0-127)
REG_485_DATA_TYPE = 0x01C1  # Pr5.24: 485数据类型选择 (0-5: 数据位/校验位/停止位组合)
REG_485_CMD_WORD = 0x01C3  # Pr5.25: 485控制命令字
REG_485_BIT_DELAY = 0x01C4  # Pr5.26: 485通讯位延时


# 软件限位寄存器地址（Pr8组）- 用于驱动器内部软件限位
REG_SOFT_LIMIT_POS_H = 0x6006  # Pr8.06: 正限位高位
REG_SOFT_LIMIT_POS_L = 0x6007  # Pr8.07: 正限位低位
REG_SOFT_LIMIT_NEG_H = 0x6008  # Pr8.08: 负限位高位
REG_SOFT_LIMIT_NEG_L = 0x6009  # Pr8.09: 负限位低位


# 波特率映射表（Pr5.22值 -> 实际波特率）
BAUDRATE_MAP = {
    0: 2400,
    1: 4800,
    2: 9600,
    3: 19200,
    4: 38400,
    5: 57600,
    6: 115200,
}

# 波特率反向映射表（实际波特率 -> Pr5.22值）
BAUDRATE_REVERSE_MAP = {v: k for k, v in BAUDRATE_MAP.items()}


# 数据类型映射表（Pr5.24值 -> 数据位/校验位/停止位组合）
# 0: 8位数据，偶校验，2个停止位
# 1: 8位数据，奇校验，2个停止位
# 2: 8位数据，偶校验，1个停止位
# 3: 8位数据，奇校验，1个停止位
# 4: 8位数据，无校验，1个停止位
# 5: 8位数据，无校验，2个停止位
DATA_TYPE_MAP = {
    0: {"bytesize": 8, "parity": "E", "stopbits": 2},
    1: {"bytesize": 8, "parity": "O", "stopbits": 2},
    2: {"bytesize": 8, "parity": "E", "stopbits": 1},
    3: {"bytesize": 8, "parity": "O", "stopbits": 1},
    4: {"bytesize": 8, "parity": "N", "stopbits": 1},
    5: {"bytesize": 8, "parity": "N", "stopbits": 2},
}


class SerialMode(Enum):
    """
    串口通信模式枚举。

    Attributes:
        RS485: RS485模式，需要配置波特率、从站地址等参数
        RS232: RS232模式，使用默认设置，无需配置从站地址
    """

    RS485 = "rs485"
    RS232 = "rs232"


@dataclass
class CommunicationConfig:
    """
    通信配置数据类。

    Attributes:
        baudrate: 波特率 (2400-115200)
        slave_id: 从站地址 (0-127)
        data_type: 数据类型 (0-5)
        serial_mode: 串口模式 (RS485/RS232)
    """

    baudrate: int = 38400
    slave_id: int = 1
    data_type: int = 4  # 默认：8位数据，无校验，1个停止位
    serial_mode: SerialMode = SerialMode.RS485

# 回零模式定义
HOME_MODE_SINGLE_LIMIT = 0  # 单边限位回零
HOME_MODE_DOUBLE_LIMIT = 1  # 双边限位回零
HOME_MODE_EXTERNAL_SIGNAL = 2  # 外部回零信号
HOME_MODE_ENCODER_Z = 3  # 编码器Z信号

# 回零方向定义
HOME_DIRECTION_POSITIVE = 0  # 正向回零
HOME_DIRECTION_NEGATIVE = 1  # 负向回零

# 回零触发控制字
CMD_TRIGGER_HOME = 0x0008  # 回零触发命令


class LeadshineDM2C(AbstractStepper):
    """
    雷赛DM2C步进驱动器实现

    寄存器地址（根据DM2C手册V1.8）：
    - 0x1801: 控制字
    - 0x1003: 状态字
    - 0x6002: 触发寄存器
    - 0x602A/0x602B: 目标位置（高/低字）
    - 0x602C/0x602D: 实际位置（高/低字）
    - 0x2203: 报警代码
    - 0x6200+: PR路径配置

    安全警告：
    - 实验时必须有人值守
    - 首次使用前验证限位参数
    """

    # 寄存器地址定义
    REG_CONTROL_WORD = 0x1801
    REG_STATUS_WORD = 0x1003
    REG_TRIGGER = 0x6002
    REG_CMD_POSITION_H = 0x602A
    REG_CMD_POSITION_L = 0x602B
    REG_ACT_POSITION_H = 0x602C
    REG_ACT_POSITION_L = 0x602D
    REG_ALARM_CODE = 0x2203

    # JOG相关寄存器地址（基于DM2C手册V1.8）
    REG_JOG_SPEED = 0x01E1  # Pr6.00: JOG速度
    REG_JOG_ACCEL_TIME = 0x01E7  # Pr6.03: JOG加速时间
    REG_JOG_DECEL_TIME = 0x01E8  # Pr6.04: JOG减速时间

    def __init__(self, device_id: str, config: dict[str, Any]):
        """
        初始化DM2C驱动器

        Args:
            device_id: 设备标识
            config: 配置字典
                - port: 串口号 (默认 "COM1")
                - slave_id: 从站地址 (默认 1)
                - baudrate: 波特率 (默认 38400，RS232模式忽略此参数)
                - steps_per_mm: 每毫米步数 (默认 1600)
                - serial_mode: 串口模式 ("rs485" 或 "rs232"，默认 "rs485")
        """
        super().__init__(device_id, config)
        self.client: ModbusSerialClient | None = None

        # 解析串口模式
        serial_mode_str = config.get("serial_mode", "rs485").lower()
        self.serial_mode = (
            SerialMode.RS232 if serial_mode_str == "rs232" else SerialMode.RS485
        )

        # RS232模式使用默认设置
        if self.serial_mode == SerialMode.RS232:
            self.slave_id = 1  # RS232模式固定从站地址为1
            self.baudrate = 9600  # RS232模式默认波特率9600
            logger.info(
                f"DM2C {device_id} initialized in RS232 mode "
                f"(port={config.get('port', 'COM1')}, using default settings)"
            )
        else:
            # RS485模式使用配置参数
            self.slave_id = config.get("slave_id", 1)
            self.baudrate = config.get("baudrate", 38400)

        self.port = config.get("port", "COM1")
        self.steps_per_mm = config.get("steps_per_mm", DEFAULT_STEPS_PER_MM)

        # 状态
        self._current_position = 0
        self._alarm_code = 0

        # 软件限位配置
        self.limit_config = SoftwareLimitConfig()

        # 仿真模式标志（当pymodbus不可用时自动启用）
        self._simulation = not PYMODBUS_AVAILABLE

        logger.info(
            f"DM2C {device_id} initialized (port={self.port}, slave={self.slave_id}, "
            f"baudrate={self.baudrate}, mode={self.serial_mode.value})"
        )

    @property
    def simulation(self) -> bool:
        """
        获取仿真模式状态。

        Returns:
            bool: 是否处于仿真模式
        """
        return self._simulation

    async def connect(self) -> bool:
        """
        建立Modbus连接

        Returns:
            bool: 连接是否成功

        Note:
            RS232模式使用默认设置（9600波特率，从站地址1）
            RS485模式使用配置的波特率和从站地址
        """
        if not PYMODBUS_AVAILABLE:
            logger.warning("pymodbus not available, running in simulation mode")
            self.status = DeviceStatus.READY
            return True

        try:
            self.status = DeviceStatus.CONNECTING

            # 根据串口模式选择连接参数
            if self.serial_mode == SerialMode.RS232:
                # RS232模式：使用默认设置（根据DM2C-RS556用户手册V1.8）
                # RS232通讯无需选择波特率和设备号，使用默认设置即可
                connect_baudrate = 9600
                connect_parity = "N"
                connect_stopbits = 1
                logger.info(
                    f"Connecting in RS232 mode with default settings "
                    f"(baudrate={connect_baudrate}, parity={connect_parity}, stopbits={connect_stopbits})"
                )
            else:
                # RS485模式：使用配置参数
                connect_baudrate = self.baudrate
                # 根据数据类型确定校验位和停止位
                data_type_config = DATA_TYPE_MAP.get(4, {"parity": "N", "stopbits": 1})
                connect_parity = data_type_config["parity"]
                connect_stopbits = data_type_config["stopbits"]

            self.client = ModbusSerialClient(
                port=self.port,
                baudrate=connect_baudrate,
                bytesize=8,
                parity=connect_parity,
                stopbits=connect_stopbits,
                timeout=1,
            )

            if self.client.connect():
                self.status = DeviceStatus.READY
                logger.info(
                    f"DM2C {self.device_id} connected on {self.port} "
                    f"(mode={self.serial_mode.value}, baudrate={connect_baudrate})"
                )
                return True
            else:
                self.status = DeviceStatus.ERROR
                logger.error(f"Failed to connect to DM2C on {self.port}")
                return False

        except Exception as e:
            self.status = DeviceStatus.ERROR
            self._last_error = str(e)
            logger.error(f"Connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        """
        断开与设备的连接

        Returns:
            bool: 断开是否成功
        """
        if self.client:
            self.client.close()
        self.status = DeviceStatus.DISCONNECTED
        logger.info(f"DM2C {self.device_id} disconnected")
        return True

    def _check_soft_limit(self, position: int) -> bool:
        """
        检查软件限位

        Args:
            position: 目标位置（步数）

        Returns:
            bool: 是否在限位范围内
        """
        position_mm = steps_to_mm(position, self.steps_per_mm)
        return self.limit_config.is_within_limits(position_mm)

    async def move_abs(self, position: float, speed: float, accel: float, decel: float) -> bool:
        """
        绝对位置定位

        Args:
            position: 目标绝对位置（单位：毫米）
            speed: 运动速度（单位：毫米/秒）
            accel: 加速度（单位：毫米/秒²）
            decel: 减速度（单位：毫米/秒²）

        Returns:
            bool: 运动是否成功启动
        """
        position_steps = mm_to_steps(position, self.steps_per_mm)

        if not self._check_soft_limit(position_steps):
            logger.error(
                f"SOFT LIMIT REJECTED: position={position}mm "
                f"exceeds limits [{self.limit_config.negative_limit}, "
                f"{self.limit_config.positive_limit}]"
            )
            return False

        if not PYMODBUS_AVAILABLE:
            logger.info(
                f"[SIMULATION] Move to {position}mm ({position_steps} steps) " f"at {speed}mm/s"
            )
            self._current_position = position_steps
            return True

        try:
            self.status = DeviceStatus.BUSY

            pos_high = (position_steps >> 16) & 0xFFFF
            pos_low = position_steps & 0xFFFF

            result1 = await self._write_register(self.REG_CMD_POSITION_H, pos_high)
            result2 = await self._write_register(self.REG_CMD_POSITION_L, pos_low)

            if not (result1 and result2):
                logger.error("Failed to write target position")
                self.status = DeviceStatus.ERROR
                return False

            trigger_value = 0x0100
            result3 = await self._write_register(self.REG_TRIGGER, trigger_value)

            if result3:
                logger.info(
                    f"Move started: target={position}mm ({position_steps} steps), "
                    f"speed={speed}mm/s"
                )
                return True
            else:
                logger.error("Failed to trigger move")
                return False

        except Exception as e:
            logger.error(f"Move error: {e}")
            self._last_error = str(e)
            return False
        finally:
            self.status = DeviceStatus.READY

    async def move_rel(self, distance: float, speed: float, accel: float, decel: float) -> bool:
        """
        相对位置定位

        Args:
            distance: 相对运动距离（单位：毫米）
            speed: 运动速度（单位：毫米/秒）
            accel: 加速度（单位：毫米/秒²）
            decel: 减速度（单位：毫米/秒²）

        Returns:
            bool: 运动是否成功启动
        """
        current_data = await self.read_position()
        current_pos = current_data["position_mm"]
        target_pos = current_pos + distance
        return await self.move_abs(target_pos, speed, accel, decel)

    async def jog(self, direction: int, speed: float) -> bool:
        """
        JOG点动模式

        Args:
            direction: 运动方向，1为正方向，-1为负方向
            speed: 运动速度（单位：毫米/秒）

        Returns:
            bool: 点动是否成功启动

        Note:
            JOG控制字（写入0x1801）：
            - 正向JOG: 0x4001
            - 反向JOG: 0x4002
            - 停止JOG: 0x4000
        """
        if not PYMODBUS_AVAILABLE:
            logger.info(f"[SIMULATION] JOG direction={direction}, speed={speed}mm/s")
            jog_distance = 1.0 if direction > 0 else -1.0
            self._current_position += mm_to_steps(jog_distance, self.steps_per_mm)
            return True

        try:
            # 设置JOG速度（步/秒）
            speed_steps = int(speed * self.steps_per_mm)
            if not await self._write_register(self.REG_JOG_SPEED, speed_steps):
                logger.error("Failed to set JOG speed")
                return False

            # 选择控制字
            cmd = CMD_JOG_POS if direction > 0 else CMD_JOG_NEG
            result = await self._write_register(self.REG_CONTROL_WORD, cmd)

            if result:
                logger.info(
                    f"JOG started: direction={'positive' if direction > 0 else 'negative'}, "
                    f"speed={speed}mm/s ({speed_steps} steps/s)"
                )
                return True
            else:
                logger.error("Failed to start JOG")
                return False

        except Exception as e:
            logger.error(f"JOG error: {e}")
            self._last_error = str(e)
            return False

    async def jog_stop(self) -> bool:
        """
        停止JOG运动

        Returns:
            bool: 是否成功停止
        """
        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] JOG stopped")
            return True

        try:
            result = await self._write_register(self.REG_CONTROL_WORD, CMD_JOG_STOP)

            if result:
                logger.info("JOG stopped")
                return True
            else:
                logger.error("Failed to stop JOG")
                return False
        except Exception as e:
            logger.error(f"JOG stop error: {e}")
            self._last_error = str(e)
            return False

    async def set_jog_speed(self, speed: float) -> bool:
        """
        设置JOG速度

        Args:
            speed: JOG速度（单位：毫米/秒）

        Returns:
            bool: 是否成功设置

        Note:
            写入寄存器Pr6.00 (地址0x01E1)，单位：步/秒
        """
        if not PYMODBUS_AVAILABLE:
            logger.info(f"[SIMULATION] JOG speed set to {speed}mm/s")
            return True

        try:
            speed_steps = int(speed * self.steps_per_mm)
            result = await self._write_register(self.REG_JOG_SPEED, speed_steps)

            if result:
                logger.info(f"JOG speed set: {speed}mm/s ({speed_steps} steps/s)")
                return True
            else:
                logger.error("Failed to set JOG speed")
                return False
        except Exception as e:
            logger.error(f"Set JOG speed error: {e}")
            self._last_error = str(e)
            return False

    async def set_jog_acceleration(self, accel_time: int, decel_time: int) -> bool:
        """
        设置JOG加减速时间

        Args:
            accel_time: 加速时间（单位：毫秒）
            decel_time: 减速时间（单位：毫秒）

        Returns:
            bool: 是否成功设置

        Note:
            加速时间写入Pr6.03 (地址0x01E7)
            减速时间写入Pr6.04 (地址0x01E8)
        """
        if not PYMODBUS_AVAILABLE:
            logger.info(
                f"[SIMULATION] JOG acceleration set: " f"accel={accel_time}ms, decel={decel_time}ms"
            )
            return True

        try:
            # 设置加速时间
            result1 = await self._write_register(self.REG_JOG_ACCEL_TIME, accel_time)
            if not result1:
                logger.error("Failed to set JOG acceleration time")
                return False

            # 设置减速时间
            result2 = await self._write_register(self.REG_JOG_DECEL_TIME, decel_time)
            if not result2:
                logger.error("Failed to set JOG deceleration time")
                return False

            logger.info(f"JOG acceleration set: accel={accel_time}ms, decel={decel_time}ms")
            return True
        except Exception as e:
            logger.error(f"Set JOG acceleration error: {e}")
            self._last_error = str(e)
            return False

    async def configure_home_mode(self, mode: int) -> bool:
        """
        配置回零模式（Pr8.00）

        Args:
            mode: 回零模式
                - 0: 单边限位回零
                - 1: 双边限位回零
                - 2: 外部回零信号
                - 3: 编码器Z信号

        Returns:
            bool: 配置是否成功

        Raises:
            ValueError: 模式值无效
        """
        if mode not in [
            HOME_MODE_SINGLE_LIMIT,
            HOME_MODE_DOUBLE_LIMIT,
            HOME_MODE_EXTERNAL_SIGNAL,
            HOME_MODE_ENCODER_Z,
        ]:
            logger.error(f"Invalid home mode: {mode}, must be 0-3")
            raise ValueError(f"Invalid home mode: {mode}, must be 0-3")

        if not PYMODBUS_AVAILABLE:
            logger.info(f"[SIMULATION] Home mode set to {mode}")
            return True

        try:
            result = await self._write_register(REG_HOME_MODE, mode)

            if result:
                logger.info(f"Home mode configured: {mode}")
                return True
            else:
                logger.error("Failed to configure home mode")
                return False

        except Exception as e:
            logger.error(f"Configure home mode error: {e}")
            self._last_error = str(e)
            return False

    async def configure_home_speed(self, speed_high: int, speed_low: int) -> bool:
        """
        配置回零速度（Pr8.01, Pr8.02）

        Args:
            speed_high: 回零高速（步/秒），范围: 1-10000
            speed_low: 回零低速（步/秒），范围: 1-10000

        Returns:
            bool: 配置是否成功

        Raises:
            ValueError: 速度值超出范围
        """
        # 参数范围检查
        if not (1 <= speed_high <= 10000):
            logger.error(f"Invalid high speed: {speed_high}, must be 1-10000")
            raise ValueError(f"Invalid high speed: {speed_high}, must be 1-10000")

        if not (1 <= speed_low <= 10000):
            logger.error(f"Invalid low speed: {speed_low}, must be 1-10000")
            raise ValueError(f"Invalid low speed: {speed_low}, must be 1-10000")

        if not PYMODBUS_AVAILABLE:
            logger.info(
                f"[SIMULATION] Home speed configured: " f"high={speed_high}, low={speed_low}"
            )
            return True

        try:
            result1 = await self._write_register(REG_HOME_SPEED_HIGH, speed_high)
            result2 = await self._write_register(REG_HOME_SPEED_LOW, speed_low)

            if result1 and result2:
                logger.info(f"Home speed configured: high={speed_high}, low={speed_low}")
                return True
            else:
                logger.error("Failed to configure home speed")
                return False

        except Exception as e:
            logger.error(f"Configure home speed error: {e}")
            self._last_error = str(e)
            return False

    async def configure_home_offset(self, offset: int) -> bool:
        """
        配置回零偏移（Pr8.03）

        Args:
            offset: 回零偏移量（步数），范围: -2147483648 ~ 2147483647

        Returns:
            bool: 配置是否成功
        """
        if not PYMODBUS_AVAILABLE:
            logger.info(f"[SIMULATION] Home offset set to {offset} steps")
            return True

        try:
            # 处理32位有符号整数
            if offset < 0:
                offset_value = offset & 0xFFFFFFFF
            else:
                offset_value = offset

            # 写入32位值（高字和低字）
            offset_high = (offset_value >> 16) & 0xFFFF
            offset_low = offset_value & 0xFFFF

            result1 = await self._write_register(REG_HOME_OFFSET, offset_low)
            # 注意：根据手册，可能需要写入高字寄存器（地址+1）
            # 这里假设偏移量是16位，如果实际是32位需要调整

            if result1:
                logger.info(f"Home offset configured: {offset} steps")
                return True
            else:
                logger.error("Failed to configure home offset")
                return False

        except Exception as e:
            logger.error(f"Configure home offset error: {e}")
            self._last_error = str(e)
            return False

    async def configure_home_direction(self, direction: int) -> bool:
        """
        配置回零方向（Pr8.04）

        Args:
            direction: 回零方向
                - 0: 正向回零
                - 1: 负向回零

        Returns:
            bool: 配置是否成功

        Raises:
            ValueError: 方向值无效
        """
        if direction not in [HOME_DIRECTION_POSITIVE, HOME_DIRECTION_NEGATIVE]:
            logger.error(f"Invalid home direction: {direction}, must be 0 or 1")
            raise ValueError(f"Invalid home direction: {direction}, must be 0 or 1")

        if not PYMODBUS_AVAILABLE:
            direction_text = "positive" if direction == HOME_DIRECTION_POSITIVE else "negative"
            logger.info(f"[SIMULATION] Home direction set to {direction_text}")
            return True

        try:
            result = await self._write_register(REG_HOME_DIRECTION, direction)

            if result:
                direction_text = "positive" if direction == HOME_DIRECTION_POSITIVE else "negative"
                logger.info(f"Home direction configured: {direction_text}")
                return True
            else:
                logger.error("Failed to configure home direction")
                return False

        except Exception as e:
            logger.error(f"Configure home direction error: {e}")
            self._last_error = str(e)
            return False

    async def home(self, mode: str = "origin") -> bool:
        """
        回零操作（根据DM2C-RS556用户手册V1.8）。

        通过向触发寄存器(0x6002)写入0x020触发回零。

        Args:
            mode: 回零模式，默认为"origin"

        Returns:
            bool: 回零是否成功启动

        Note:
            根据DM2C-RS556用户手册V1.8，回零触发通过向触发寄存器(0x6002)
            写入0x020实现，而非控制字寄存器。

            回零模式通过Pr8.10配置，支持以下模式：
            - 0: 单次正向限位回零
            - 1: 单次负向限位回零
            - 2: 单次原点信号回零
            - 3: 单次原点信号+正向限位回零
            - 4: 单次原点信号+负向限位回零
            - 5: 正向限位回零
            - 6: 负向限位回零
            - 7: 原点信号回零
            - 8: 原点信号+正向限位回零
            - 9: 原点信号+负向限位回零
        """
        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] Homing...")
            self._current_position = 0
            return True

        try:
            self.status = DeviceStatus.BUSY

            # 根据手册V1.8：向触发寄存器0x6002写入0x020触发回零
            result = await self._write_register(self.REG_TRIGGER, TRIGGER_HOME)

            if result:
                logger.info("Homing started (wrote 0x020 to 0x6002)")
                return True
            else:
                logger.error("Failed to start homing")
                return False

        except Exception as e:
            logger.error(f"Homing error: {e}")
            self._last_error = str(e)
            return False
        finally:
            self.status = DeviceStatus.READY

    async def set_current_position_zero(self) -> bool:
        """
        将当前位置设置为零点（根据DM2C-RS556用户手册V1.8）。

        通过向触发寄存器(0x6002)写入0x021实现。

        Returns:
            bool: 是否成功

        Note:
            此方法不会执行机械回零动作，仅将当前位置坐标清零。
            适用于不需要物理原点的应用场景。
        """
        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] Current position set to zero")
            self._current_position = 0
            return True

        try:
            result = await self._write_register(self.REG_TRIGGER, TRIGGER_SET_ZERO)

            if result:
                logger.info("Current position set to zero (wrote 0x021 to 0x6002)")
                self._current_position = 0
                return True
            else:
                logger.error("Failed to set current position to zero")
                return False

        except Exception as e:
            logger.error(f"Set position zero error: {e}")
            self._last_error = str(e)
            return False

    async def read_trigger_status(self) -> dict[str, Any]:
        """
        读取触发寄存器状态（根据DM2C-RS556用户手册V1.8）。

        Returns:
            Dict[str, Any]: 触发状态信息
                - raw_value: 原始读值
                - status: 状态描述
                - path_number: 运行中的路径号（如果正在运行）
                - is_idle: 是否空闲（可接收新命令）
                - is_running: 是否正在运行

        Note:
            触发寄存器(0x6002)读值定义：
            - 0x0000：定位完成，可接收新数据
            - 0x10P：路径P运行中（P为路径号0~15）
            - 0x200：指令完成等待定位
        """
        if not PYMODBUS_AVAILABLE:
            return {
                "raw_value": 0,
                "status": "idle",
                "path_number": None,
                "is_idle": True,
                "is_running": False,
            }

        try:
            raw_value = await self._read_register(self.REG_TRIGGER)

            if raw_value == TRIGGER_STATUS_IDLE:
                return {
                    "raw_value": raw_value,
                    "status": "idle",
                    "path_number": None,
                    "is_idle": True,
                    "is_running": False,
                }
            elif raw_value == TRIGGER_STATUS_WAITING:
                return {
                    "raw_value": raw_value,
                    "status": "waiting",
                    "path_number": None,
                    "is_idle": False,
                    "is_running": False,
                }
            elif (raw_value & 0xFF00) == 0x1000:
                # 路径运行中：0x10P
                path_number = raw_value & 0x000F
                return {
                    "raw_value": raw_value,
                    "status": "running",
                    "path_number": path_number,
                    "is_idle": False,
                    "is_running": True,
                }
            else:
                return {
                    "raw_value": raw_value,
                    "status": "unknown",
                    "path_number": None,
                    "is_idle": False,
                    "is_running": False,
                }

        except Exception as e:
            logger.error(f"Read trigger status error: {e}")
            self._last_error = str(e)
            return {
                "raw_value": -1,
                "status": "error",
                "path_number": None,
                "is_idle": False,
                "is_running": False,
                "error": str(e),
            }

    async def read_position(self) -> dict[str, float]:
        """
        读取当前位置

        Returns:
            Dict[str, float]: 包含位置信息的字典，至少包含"position_mm"键
        """
        if not PYMODBUS_AVAILABLE:
            position_mm = steps_to_mm(self._current_position, self.steps_per_mm)
            return {"position_steps": self._current_position, "position_mm": round(position_mm, 3)}

        try:
            if not self.client:
                logger.warning("Client not connected")
                position_mm = steps_to_mm(self._current_position, self.steps_per_mm)
                return {
                    "position_steps": self._current_position,
                    "position_mm": round(position_mm, 3),
                }

            result = self.client.read_holding_registers(
                self.REG_ACT_POSITION_H, 2, slave=self.slave_id
            )

            if result and not result.isError():
                position = (result.registers[0] << 16) | result.registers[1]

                if position >= 0x80000000:
                    position -= 0x100000000

                self._current_position = position
                position_mm = steps_to_mm(position, self.steps_per_mm)

                return {"position_steps": position, "position_mm": round(position_mm, 3)}
            else:
                logger.warning("Failed to read position")
                position_mm = steps_to_mm(self._current_position, self.steps_per_mm)
                return {
                    "position_steps": self._current_position,
                    "position_mm": round(position_mm, 3),
                }

        except Exception as e:
            logger.error(f"Read position error: {e}")
            self._last_error = str(e)
            position_mm = steps_to_mm(self._current_position, self.steps_per_mm)
            return {"position_steps": self._current_position, "position_mm": round(position_mm, 3)}

    async def stop(self, emergency: bool = False) -> bool:
        """
        停止运动

        Args:
            emergency: 是否为紧急停止，默认为False

        Returns:
            bool: 停止是否成功
        """
        if emergency:
            logger.warning("EMERGENCY STOP triggered!")
        else:
            logger.info("Stop triggered")

        if not PYMODBUS_AVAILABLE:
            if emergency:
                self.status = DeviceStatus.EMERGENCY_STOP
            return True

        try:
            if emergency:
                result = await self._write_register(self.REG_TRIGGER, TRIGGER_EMERGENCY_STOP)
                self.status = DeviceStatus.EMERGENCY_STOP
            else:
                result = await self._write_register(self.REG_CONTROL_WORD, 0)

            return result

        except Exception as e:
            logger.error(f"Stop error: {e}")
            self._last_error = str(e)
            return False

    async def read_status(self) -> dict[str, Any]:
        """
        读取设备完整状态信息。

        Returns:
            Dict[str, Any]: 包含设备状态信息的字典，包括：
                - device_id: 设备标识
                - status: 设备状态
                - position_steps: 位置（步数）
                - position_mm: 位置（毫米）
                - alarm_code: 报警代码
                - alarm_text: 报警文本（简短描述，向后兼容）
                - alarm_info: 报警详细信息（包含原因和解决方案）
                - status_word: 状态字信息
                - limit_positive: 正向限位
                - limit_negative: 负向限位
                - connected: 连接状态
        """
        position_data = await self.read_position()
        status_word = await self.read_status_word()
        alarm_code = await self.read_alarm_code()
        alarm_info = get_alarm_info(alarm_code, language="zh")

        return {
            "device_id": self.device_id,
            "status": self.status.value,
            "position_steps": position_data["position_steps"],
            "position_mm": position_data["position_mm"],
            "alarm_code": alarm_code,
            "alarm_text": ALARM_CODES.get(alarm_code, "未知故障"),  # 向后兼容
            "alarm_info": alarm_info,  # 新增：详细报警信息
            "status_word": status_word,
            "limit_positive": self.limit_config.positive_limit,
            "limit_negative": self.limit_config.negative_limit,
            "connected": self.status != DeviceStatus.DISCONNECTED,
        }

    async def read_status_word(self) -> dict[str, Any]:
        """
        读取状态字(0x1003)

        状态字位定义（DM2C-RS556用户手册V1.8）：
        - Bit0: 故障位（1=故障）
        - Bit1: 使能位（1=使能）
        - Bit2: 运行位（1=运行中）
        - Bit3: 无效位（1=无效状态）
        - Bit4: 指令完成位（1=指令执行完成）
        - Bit5: 路径完成位（1=PR路径执行完成）
        - Bit6: 回零完成位（1=回零完成）

        Returns:
            Dict[str, Any]: 解析后的状态信息
        """
        if not PYMODBUS_AVAILABLE:
            return {
                "fault": False,
                "enabled": True,
                "running": False,
                "invalid": False,
                "cmd_complete": True,
                "path_complete": True,
                "home_complete": True,
                "raw_value": 0x02,
            }

        try:
            if not self.client:
                return {
                    "fault": False,
                    "enabled": False,
                    "running": False,
                    "invalid": True,
                    "cmd_complete": False,
                    "path_complete": False,
                    "home_complete": False,
                    "raw_value": 0,
                }

            result = self.client.read_holding_registers(
                self.REG_STATUS_WORD, 1, slave=self.slave_id
            )

            if result and not result.isError():
                status = result.registers[0]
                return {
                    "fault": bool(status & STATUS_FAULT_BIT),
                    "enabled": bool(status & STATUS_ENABLE_BIT),
                    "running": bool(status & STATUS_RUNNING_BIT),
                    "invalid": bool(status & STATUS_INVALID_BIT),
                    "cmd_complete": bool(status & STATUS_CMD_COMPLETE_BIT),
                    "path_complete": bool(status & STATUS_PATH_COMPLETE_BIT),
                    "home_complete": bool(status & STATUS_HOME_COMPLETE_BIT),
                    "raw_value": status,
                }
            else:
                logger.warning("Failed to read status word")
                return {
                    "fault": False,
                    "enabled": False,
                    "running": False,
                    "invalid": True,
                    "cmd_complete": False,
                    "path_complete": False,
                    "home_complete": False,
                    "raw_value": 0,
                }

        except Exception as e:
            logger.error(f"Read status word error: {e}")
            self._last_error = str(e)
            return {
                "fault": False,
                "enabled": False,
                "running": False,
                "invalid": True,
                "cmd_complete": False,
                "path_complete": False,
                "home_complete": False,
                "raw_value": 0,
            }

    async def read_alarm_code(self) -> int:
        """
        读取报警代码(0x2203)

        Returns:
            int: 报警代码
        """
        if not PYMODBUS_AVAILABLE:
            return self._alarm_code

        try:
            if not self.client:
                return self._alarm_code

            result = self.client.read_holding_registers(self.REG_ALARM_CODE, 1, slave=self.slave_id)

            if result and not result.isError():
                alarm_code = result.registers[0]
                self._alarm_code = alarm_code
                return alarm_code
            else:
                logger.warning("Failed to read alarm code")
                return self._alarm_code

        except Exception as e:
            logger.error(f"Read alarm code error: {e}")
            self._last_error = str(e)
            return self._alarm_code

    async def get_alarm_details(self, language: str = "zh") -> dict[str, Any]:
        """
        获取当前报警的详细信息。

        Args:
            language: 语言选择，"zh"为中文，"en"为英文

        Returns:
            Dict[str, Any]: 包含报警详细信息的字典，包括：
                - code: 报警代码
                - name: 报警名称
                - description: 报警描述
                - severity: 严重程度
                - possible_causes: 可能原因列表
                - solutions: 解决方案列表

        Example:
            >>> alarm_info = await driver.get_alarm_details("zh")
            >>> print(alarm_info["name"])
            "过流保护"
        """
        alarm_code = await self.read_alarm_code()
        return get_alarm_info(alarm_code, language)

    async def clear_alarm(self) -> bool:
        """
        清除报警（写入控制字0x1111到0x1801）。

        根据DM2C-RS556用户手册V1.8，报警清除通过向控制字寄存器(0x1801)
        写入0x1111实现。

        Returns:
            bool: 是否成功

        Note:
            此方法仅清除报警状态，不修复导致报警的硬件问题。
            清除报警前应先排除故障原因。
        """
        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] Alarm cleared")
            self._alarm_code = 0
            self.status = DeviceStatus.READY
            return True

        try:
            # 写入0x1111到控制字寄存器0x1801清除报警
            result = await self._write_register(self.REG_CONTROL_WORD, CMD_RESET_ALARM)

            if result:
                logger.info("Alarm cleared successfully (wrote 0x1111 to 0x1801)")
                self._alarm_code = 0
                self.status = DeviceStatus.READY
                return True
            else:
                logger.error("Failed to clear alarm")
                return False

        except Exception as e:
            logger.error(f"Clear alarm error: {e}")
            self._last_error = str(e)
            return False

    async def reset_alarm(self) -> bool:
        """
        复位报警（向后兼容方法）。

        此方法为向后兼容保留，内部调用clear_alarm()。
        新代码建议使用clear_alarm()方法。

        Returns:
            bool: 是否成功
        """
        return await self.clear_alarm()

    async def save_parameters(self) -> bool:
        """
        保存参数到EEPROM

        Returns:
            bool: 是否成功
        """
        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] Parameters saved to EEPROM")
            return True

        try:
            result = await self._write_register(self.REG_CONTROL_WORD, CMD_SAVE_PARAM)

            if result:
                logger.info("Parameters saved to EEPROM")
                return True
            else:
                logger.error("Failed to save parameters")
                return False

        except Exception as e:
            logger.error(f"Save parameters error: {e}")
            self._last_error = str(e)
            return False

    async def factory_reset(self) -> bool:
        """
        恢复出厂设置

        Returns:
            bool: 是否成功
        """
        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] Factory reset")
            return True

        try:
            result = await self._write_register(self.REG_CONTROL_WORD, CMD_FACTORY_RESET)

            if result:
                logger.warning("Factory reset executed")
                return True
            else:
                logger.error("Failed to execute factory reset")
                return False

        except Exception as e:
            logger.error(f"Factory reset error: {e}")
            self._last_error = str(e)
            return False

    async def configure_pr_path(
        self,
        path_number: int,
        mode: int,
        position: int,
        velocity: int,
        accel_time: int = 100,
        decel_time: int = 100,
        dwell_time: int = 0,
        special_param: int = 0,
    ) -> bool:
        """
        配置PR路径（根据DM2C-RS556用户手册V1.8）。

        Args:
            path_number: 路径编号 (0-15)，共支持16段路径
            mode: 运动模式（位组合）：
                Bit0-3: TYPE - 运动类型
                    - 0: 无动作
                    - 1: 位置定位
                    - 2: 速度运行
                    - 3: 回零
                Bit4: INS - 插断控制 (0=可插断, 1=屏蔽插断)
                Bit5: OVLP - 重叠功能 (0=不重叠, 1=重叠)
                Bit6: POS - 位置模式 (0=绝对位置, 1=相对位置)
                Bit8-13: JUMP_ADDR - 跳转目标路径号(0-15)
                Bit14: JUMP - 跳转使能 (0=不跳转, 1=跳转)
                示例：
                - 0x0001: 位置定位，绝对位置，可插断
                - 0x0041: 位置定位，相对位置，可插断
                - 0x0002: 速度运行
                - 0x0003: 回零
            position: 目标位置（步数，32位有符号整数）
                - 对于位置定位：目标位置或位移量
                - 对于速度运行：无效
                - 对于回零：回零模式（参考Pr8.10）
            velocity: 运行速度（rpm）
                - 对于位置定位：定位速度
                - 对于速度运行：运行速度
                - 对于回零：回零速度
            accel_time: 加速时间（单位：ms/1000rpm，默认100）
            decel_time: 减速时间（单位：ms/1000rpm，默认100）
            dwell_time: 停顿时间（毫秒，默认0）
                指令完成后等待时间，用于连续路径运行
            special_param: 特殊参数（默认0）
                - 路径0: 直接映射到Pr8.02
                - 其他路径: 保留

        Returns:
            bool: 配置是否成功

        Note:
            寄存器映射（每个路径占8个连续寄存器）：
            - 路径0: 0x6200-0x6207 (Pr9.00-Pr9.07)
            - 路径1: 0x6208-0x620F (Pr9.08-Pr9.15)
            - 路径2: 0x6210-0x6217 (Pr9.16-Pr9.23)
            - ...以此类推

        Example:
            >>> # 配置路径0为绝对位置定位，目标10000步，速度500rpm
            >>> await driver.configure_pr_path(0, PR_TYPE_POSITION, 10000, 500)
            >>> # 配置路径1为相对位置定位，目标-5000步，速度300rpm
            >>> await driver.configure_pr_path(1, PR_TYPE_POSITION | PR_POS_RELATIVE << 6, -5000, 300)
            >>> # 配置路径2为速度运行，速度800rpm
            >>> await driver.configure_pr_path(2, PR_TYPE_VELOCITY, 0, 800)
        """
        if not 0 <= path_number <= 15:
            logger.error(f"Invalid path number: {path_number}, must be 0-15")
            return False

        if not PYMODBUS_AVAILABLE:
            logger.info(
                f"[SIMULATION] PR path {path_number} configured: "
                f"mode=0x{mode:04X}, position={position}, velocity={velocity}"
            )
            return True

        try:
            if not self.client:
                logger.warning("Client not connected")
                return False

            base_addr = PR_PATH_BASE_ADDR + path_number * PR_PATH_ENTRY_SIZE
            pos_high = (position >> 16) & 0xFFFF
            pos_low = position & 0xFFFF

            values = [
                mode,
                pos_high,
                pos_low,
                velocity,
                accel_time,
                decel_time,
                dwell_time,
                special_param,
            ]

            result = self.client.write_registers(base_addr, values, slave=self.slave_id)

            if result and not result.isError():
                logger.info(f"PR path {path_number} configured successfully")
                return True
            else:
                logger.error(f"Failed to configure PR path {path_number}")
                return False

        except Exception as e:
            logger.error(f"Configure PR path error: {e}")
            self._last_error = str(e)
            return False

    async def trigger_pr_path(self, path_number: int) -> bool:
        """
        触发PR路径运行（根据DM2C-RS556用户手册V1.8）。

        通过向触发寄存器(0x6002)写入0x01P来触发指定路径运行，
        其中P为路径号(0~15)。

        Args:
            path_number: 路径编号 (0-15)

        Returns:
            bool: 触发是否成功

        Note:
            触发寄存器(0x6002)命令格式：
            - 写入0x01P：触发P段定位（P为路径号0~15）
            - 写入0x020：回零触发
            - 写入0x021：当前位置手动设零
            - 写入0x040：急停

            触发寄存器读值：
            - 0x0000：定位完成，可接收新数据
            - 0x10P：路径P运行中
            - 0x200：指令完成等待定位

        Example:
            >>> await driver.trigger_pr_path(0)  # 触发路径0
            >>> await driver.trigger_pr_path(5)  # 触发路径5
        """
        if not 0 <= path_number <= 15:
            logger.error(f"Invalid path number: {path_number}, must be 0-15")
            return False

        if not PYMODBUS_AVAILABLE:
            logger.info(f"[SIMULATION] PR path {path_number} triggered")
            return True

        try:
            # 触发命令：0x01P (P为路径号)
            trigger_value = TRIGGER_PATH_BASE | path_number
            result = await self._write_register(self.REG_TRIGGER, trigger_value)

            if result:
                logger.info(
                    f"PR path {path_number} triggered " f"(wrote 0x{trigger_value:03X} to 0x6002)"
                )
                return True
            else:
                logger.error(f"Failed to trigger PR path {path_number}")
                return False

        except Exception as e:
            logger.error(f"Trigger PR path error: {e}")
            self._last_error = str(e)
            return False

    async def reset_emergency(self) -> bool:
        """
        复位急停状态（向后兼容）

        Returns:
            bool: 是否成功
        """
        logger.info("Emergency stop reset")
        self.status = DeviceStatus.READY
        return True

    async def emergency_stop(self) -> bool:
        """
        软件急停（向后兼容）

        Returns:
            bool: 是否成功
        """
        return await self.stop(emergency=True)

    def set_soft_limits(self, positive_mm: float, negative_mm: float):
        """
        设置软件限位（毫米）（向后兼容）

        Args:
            positive_mm: 正向限位（毫米）
            negative_mm: 负向限位（毫米）
        """
        self.limit_config.positive_limit = positive_mm
        self.limit_config.negative_limit = negative_mm
        self.limit_config.enable = True
        logger.info(f"Soft limits set: [{negative_mm}mm, {positive_mm}mm]")

    # ==================== IO端口配置功能 ====================

    async def configure_di(self, di_number: int, function: int) -> bool:
        """
        配置数字输入端口功能。

        Args:
            di_number: DI端口号 (1-7)
            function: 功能代码（根据DM2C-RS556用户手册V1.8）
                常开模式功能代码：
                - 0x00: 无效输入
                - 0x07: 报警清除
                - 0x08: 使能
                - 0x20: 触发命令(CTRG)
                - 0x21: 回零触发(HOME)
                - 0x22: 强制急停(STP)
                - 0x23: 正向JOG(PJOG)
                - 0x24: 反向JOG(NJOG)
                - 0x25: 正向限位(POT)
                - 0x26: 反向限位(NOT)
                - 0x27: 原点信号(ORG)
                - 0x28: 路径地址0(ADDR0)
                - 0x29: 路径地址1(ADDR1)
                - 0x2A: 路径地址2(ADDR2)
                - 0x2B: 路径地址3(ADDR3)
                - 0x2C: JOG速度2
                常闭模式：功能代码 + 0x80

        Returns:
            bool: 配置是否成功

        Example:
            >>> await driver.configure_di(1, 0x88)  # DI1配置为使能，常闭
            >>> await driver.configure_di(4, 0x25)  # DI4配置为正限位，常开
        """
        # 参数校验
        if di_number not in DI_CONFIG_ADDRS:
            logger.error(f"Invalid DI number: {di_number}, must be 1-7")
            return False

        # 功能代码校验：允许常开模式(0x00-0x2C)和常闭模式(0x80-0xAC)
        base_function = function & 0x7F  # 获取基础功能代码（去除常闭位）
        if base_function not in DI_FUNCTIONS:
            logger.error(
                f"Invalid DI function: 0x{function:02X}, "
                f"base function 0x{base_function:02X} not in valid range"
            )
            return False

        if not PYMODBUS_AVAILABLE:
            func_name = DI_FUNCTIONS.get(base_function, "Unknown")
            polarity = "常闭" if function & 0x80 else "常开"
            logger.info(f"[SIMULATION] DI{di_number} configured: {func_name} ({polarity})")
            return True

        try:
            address = DI_CONFIG_ADDRS[di_number]
            result = await self._write_register(address, function)

            if result:
                func_name = DI_FUNCTIONS.get(base_function, "Unknown")
                polarity = "常闭" if function & 0x80 else "常开"
                logger.info(
                    f"DI{di_number} configured: function=0x{function:02X} "
                    f"({func_name}, {polarity})"
                )
                return True
            else:
                logger.error(f"Failed to configure DI{di_number}")
                return False

        except Exception as e:
            logger.error(f"Configure DI error: {e}")
            self._last_error = str(e)
            return False

    async def configure_do(self, do_number: int, function: int) -> bool:
        """
        配置数字输出端口功能。

        Args:
            do_number: DO端口号 (1-3)
            function: 功能代码（根据DM2C-RS556用户手册V1.8）
                常开模式功能代码：
                - 0x00: 无效输出
                - 0x20: 指令完成(CMD_OK)
                - 0x21: 路径完成(MC_OK)
                - 0x22: 回零完成(HOME_OK)
                - 0x23: 到位完成(INP)
                - 0x24: 抱闸输出(BRK)
                - 0x25: 报警输出(ALM)
                常闭模式：功能代码 + 0x80

        Returns:
            bool: 配置是否成功

        Example:
            >>> await driver.configure_do(1, 0x25)  # DO1配置为报警输出，常开
            >>> await driver.configure_do(2, 0xA3)  # DO2配置为到位信号，常闭
        """
        # 参数校验
        if do_number not in DO_CONFIG_ADDRS:
            logger.error(f"Invalid DO number: {do_number}, must be 1-3")
            return False

        # 功能代码校验：允许常开模式(0x00-0x25)和常闭模式(0x80-0xA5)
        base_function = function & 0x7F  # 获取基础功能代码（去除常闭位）
        if base_function not in DO_FUNCTIONS:
            logger.error(
                f"Invalid DO function: 0x{function:02X}, "
                f"base function 0x{base_function:02X} not in valid range"
            )
            return False

        if not PYMODBUS_AVAILABLE:
            func_name = DO_FUNCTIONS.get(base_function, "Unknown")
            polarity = "常闭" if function & 0x80 else "常开"
            logger.info(f"[SIMULATION] DO{do_number} configured: {func_name} ({polarity})")
            return True

        try:
            address = DO_CONFIG_ADDRS[do_number]
            result = await self._write_register(address, function)

            if result:
                func_name = DO_FUNCTIONS.get(base_function, "Unknown")
                polarity = "常闭" if function & 0x80 else "常开"
                logger.info(
                    f"DO{do_number} configured: function=0x{function:02X} "
                    f"({func_name}, {polarity})"
                )
                return True
            else:
                logger.error(f"Failed to configure DO{do_number}")
                return False

        except Exception as e:
            logger.error(f"Configure DO error: {e}")
            self._last_error = str(e)
            return False

    async def read_di_config(self, di_number: int) -> int:
        """
        读取数字输入端口配置。

        Args:
            di_number: DI端口号 (1-7)

        Returns:
            int: 功能代码，失败返回-1

        Example:
            >>> function = await driver.read_di_config(1)
            >>> print(DI_FUNCTIONS.get(function, "Unknown"))
        """
        if di_number not in DI_CONFIG_ADDRS:
            logger.error(f"Invalid DI number: {di_number}, must be 1-7")
            return -1

        if not PYMODBUS_AVAILABLE:
            logger.info(f"[SIMULATION] Read DI{di_number} config: 0 (无功能)")
            return 0

        try:
            if not self.client:
                logger.warning("Client not connected")
                return -1

            address = DI_CONFIG_ADDRS[di_number]
            result = self.client.read_holding_registers(address, 1, slave=self.slave_id)

            if result and not result.isError():
                function = result.registers[0]
                logger.debug(
                    f"DI{di_number} config read: {function} "
                    f"({DI_FUNCTIONS.get(function, 'Unknown')})"
                )
                return function
            else:
                logger.warning(f"Failed to read DI{di_number} config")
                return -1

        except Exception as e:
            logger.error(f"Read DI config error: {e}")
            self._last_error = str(e)
            return -1

    async def read_do_config(self, do_number: int) -> int:
        """
        读取数字输出端口配置。

        Args:
            do_number: DO端口号 (1-3)

        Returns:
            int: 功能代码，失败返回-1

        Example:
            >>> function = await driver.read_do_config(1)
            >>> print(DO_FUNCTIONS.get(function, "Unknown"))
        """
        if do_number not in DO_CONFIG_ADDRS:
            logger.error(f"Invalid DO number: {do_number}, must be 1-3")
            return -1

        if not PYMODBUS_AVAILABLE:
            logger.info(f"[SIMULATION] Read DO{do_number} config: 0 (无功能)")
            return 0

        try:
            if not self.client:
                logger.warning("Client not connected")
                return -1

            address = DO_CONFIG_ADDRS[do_number]
            result = self.client.read_holding_registers(address, 1, slave=self.slave_id)

            if result and not result.isError():
                function = result.registers[0]
                logger.debug(
                    f"DO{do_number} config read: {function} "
                    f"({DO_FUNCTIONS.get(function, 'Unknown')})"
                )
                return function
            else:
                logger.warning(f"Failed to read DO{do_number} config")
                return -1

        except Exception as e:
            logger.error(f"Read DO config error: {e}")
            self._last_error = str(e)
            return -1

    async def read_di_status(self) -> dict[str, Any]:
        """
        读取所有数字输入端口状态。

        读取Pr4.08寄存器，返回DI1-DI7的实时状态。

        Returns:
            Dict[str, Any]: 包含以下字段：
                - raw_value: 原始寄存器值
                - di1-di7: 各端口状态（True=高电平，False=低电平）
                - active: 当前激活的DI列表

        Example:
            >>> status = await driver.read_di_status()
            >>> if status["di1"]:
            ...     print("DI1 is active")
        """
        if not PYMODBUS_AVAILABLE:
            return {
                "raw_value": 0,
                "di1": False,
                "di2": False,
                "di3": False,
                "di4": False,
                "di5": False,
                "di6": False,
                "di7": False,
                "active": [],
            }

        try:
            if not self.client:
                logger.warning("Client not connected")
                return {
                    "raw_value": 0,
                    "di1": False,
                    "di2": False,
                    "di3": False,
                    "di4": False,
                    "di5": False,
                    "di6": False,
                    "di7": False,
                    "active": [],
                }

            result = self.client.read_holding_registers(REG_DI_STATUS, 1, slave=self.slave_id)

            if result and not result.isError():
                raw_value = result.registers[0]

                # 解析各DI位状态
                status = {
                    "raw_value": raw_value,
                    "di1": bool(raw_value & 0x01),
                    "di2": bool(raw_value & 0x02),
                    "di3": bool(raw_value & 0x04),
                    "di4": bool(raw_value & 0x08),
                    "di5": bool(raw_value & 0x10),
                    "di6": bool(raw_value & 0x20),
                    "di7": bool(raw_value & 0x40),
                }

                # 统计激活的DI
                status["active"] = [f"DI{i}" for i in range(1, 8) if status[f"di{i}"]]

                logger.debug(f"DI status: {status['active']}")
                return status
            else:
                logger.warning("Failed to read DI status")
                return {
                    "raw_value": 0,
                    "di1": False,
                    "di2": False,
                    "di3": False,
                    "di4": False,
                    "di5": False,
                    "di6": False,
                    "di7": False,
                    "active": [],
                }

        except Exception as e:
            logger.error(f"Read DI status error: {e}")
            self._last_error = str(e)
            return {
                "raw_value": 0,
                "di1": False,
                "di2": False,
                "di3": False,
                "di4": False,
                "di5": False,
                "di6": False,
                "di7": False,
                "active": [],
            }

    async def read_do_status(self) -> dict[str, Any]:
        """
        读取所有数字输出端口状态。

        读取Pr4.29寄存器，返回DO1-DO3的实时状态。

        Returns:
            Dict[str, Any]: 包含以下字段：
                - raw_value: 原始寄存器值
                - do1-do3: 各端口状态（True=输出高，False=输出低）
                - active: 当前激活的DO列表

        Example:
            >>> status = await driver.read_do_status()
            >>> if status["do1"]:
            ...     print("DO1 is outputting")
        """
        if not PYMODBUS_AVAILABLE:
            return {
                "raw_value": 0,
                "do1": False,
                "do2": False,
                "do3": False,
                "active": [],
            }

        try:
            if not self.client:
                logger.warning("Client not connected")
                return {
                    "raw_value": 0,
                    "do1": False,
                    "do2": False,
                    "do3": False,
                    "active": [],
                }

            result = self.client.read_holding_registers(REG_DO_STATUS, 1, slave=self.slave_id)

            if result and not result.isError():
                raw_value = result.registers[0]

                # 解析各DO位状态
                status = {
                    "raw_value": raw_value,
                    "do1": bool(raw_value & 0x01),
                    "do2": bool(raw_value & 0x02),
                    "do3": bool(raw_value & 0x04),
                }

                # 统计激活的DO
                status["active"] = [f"DO{i}" for i in range(1, 4) if status[f"do{i}"]]

                logger.debug(f"DO status: {status['active']}")
                return status
            else:
                logger.warning("Failed to read DO status")
                return {
                    "raw_value": 0,
                    "do1": False,
                    "do2": False,
                    "do3": False,
                    "active": [],
                }

        except Exception as e:
            logger.error(f"Read DO status error: {e}")
            self._last_error = str(e)
            return {
                "raw_value": 0,
                "do1": False,
                "do2": False,
                "do3": False,
                "active": [],
            }

    async def read_io_status(self) -> dict[str, Any]:
        """
        读取所有IO端口状态。

        Returns:
            Dict[str, Any]: 包含DI和DO状态的综合信息

        Example:
            >>> io_status = await driver.read_io_status()
            >>> print(f"Active DI: {io_status['di']['active']}")
            >>> print(f"Active DO: {io_status['do']['active']}")
        """
        di_status = await self.read_di_status()
        do_status = await self.read_do_status()

        return {
            "di": di_status,
            "do": do_status,
        }

    async def configure_all_di(self, config: dict[int, int]) -> dict[int, bool]:
        """
        批量配置所有数字输入端口。

        Args:
            config: 配置字典，键为DI端口号(1-7)，值为功能代码

        Returns:
            Dict[int, bool]: 各端口配置结果

        Example:
            >>> config = {
            ...     1: 1,  # DI1: 使能
            ...     2: 2,  # DI2: JOG+
            ...     3: 3,  # DI3: JOG-
            ...     4: 4,  # DI4: 正限位
            ...     5: 5,  # DI5: 负限位
            ... }
            >>> results = await driver.configure_all_di(config)
        """
        results = {}
        for di_num, function in config.items():
            results[di_num] = await self.configure_di(di_num, function)
        return results

    async def configure_all_do(self, config: dict[int, int]) -> dict[int, bool]:
        """
        批量配置所有数字输出端口。

        Args:
            config: 配置字典，键为DO端口号(1-3)，值为功能代码

        Returns:
            Dict[int, bool]: 各端口配置结果

        Example:
            >>> config = {
            ...     1: 1,  # DO1: 报警输出
            ...     2: 3,  # DO2: 到位信号
            ... }
            >>> results = await driver.configure_all_do(config)
        """
        results = {}
        for do_num, function in config.items():
            results[do_num] = await self.configure_do(do_num, function)
        return results

    async def _read_register(self, address: int) -> int:
        """
        读取单个保持寄存器。

        Args:
            address: 寄存器地址

        Returns:
            int: 寄存器值，失败返回-1

        Raises:
            RuntimeError: 客户端未连接
        """
        if not self.client:
            raise RuntimeError("Modbus client not connected")

        try:
            result = self.client.read_holding_registers(address, 1, slave=self.slave_id)
            if result and not result.isError():
                return result.registers[0]
            else:
                logger.error(f"Failed to read register 0x{address:04X}")
                return -1
        except ModbusException as e:
            logger.error(f"Read register 0x{address:04X} error: {e}")
            return -1
        except Exception as e:
            logger.error(f"Unexpected error reading register: {e}")
            return -1

    async def _write_register(self, address: int, value: int) -> bool:
        """
        写入单个保持寄存器

        Args:
            address: 寄存器地址
            value: 写入值

        Returns:
            bool: 是否成功
        """
        if not self.client:
            return False

        try:
            result = self.client.write_register(address, value, slave=self.slave_id)
            return result and not result.isError()
        except ModbusException as e:
            logger.error(f"Write register 0x{address:04X} error: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error writing register: {e}")
            return False

    # ==================== RS232专用通信模式功能 ====================

    async def connect_rs232(self, port: str) -> bool:
        """
        使用RS232模式连接驱动器。

        根据DM2C-RS556用户手册V1.8，RS232通讯无需选择波特率和设备号，
        使用默认设置即可。

        Args:
            port: 串口号（如 "COM3"）

        Returns:
            bool: 连接是否成功

        Note:
            RS232模式默认设置：
            - 波特率：9600
            - 从站地址：1
            - 数据位：8位
            - 校验位：无
            - 停止位：1位
        """
        self.port = port
        self.serial_mode = SerialMode.RS232
        self.slave_id = 1
        self.baudrate = 9600

        logger.info(f"Connecting in RS232 mode on {port} with default settings")
        return await self.connect()

    def get_serial_mode(self) -> SerialMode:
        """
        获取当前串口通信模式。

        Returns:
            SerialMode: 当前串口模式（RS485或RS232）
        """
        return self.serial_mode

    def is_rs232_mode(self) -> bool:
        """
        检查是否为RS232模式。

        Returns:
            bool: 是否为RS232模式
        """
        return self.serial_mode == SerialMode.RS232

    # ==================== 在线修改通信参数功能 ====================

    async def read_communication_config(self) -> CommunicationConfig:
        """
        读取当前通信参数配置。

        读取Pr5.22-Pr5.24寄存器获取当前通信参数。

        Returns:
            CommunicationConfig: 通信配置对象

        Note:
            寄存器映射：
            - Pr5.22 (0x01BD): 波特率 (0-6)
            - Pr5.23 (0x01BF): 从站地址 (0-127)
            - Pr5.24 (0x01C1): 数据类型 (0-5)
        """
        if not PYMODBUS_AVAILABLE:
            return CommunicationConfig()

        try:
            baudrate_val = await self._read_register(REG_485_BAUDRATE)
            slave_id_val = await self._read_register(REG_485_ID)
            data_type_val = await self._read_register(REG_485_DATA_TYPE)

            config = CommunicationConfig(
                baudrate=BAUDRATE_MAP.get(baudrate_val, 38400),
                slave_id=slave_id_val if slave_id_val >= 0 else 1,
                data_type=data_type_val if 0 <= data_type_val <= 5 else 4,
                serial_mode=self.serial_mode,
            )

            logger.info(
                f"Communication config read: baudrate={config.baudrate}, "
                f"slave_id={config.slave_id}, data_type={config.data_type}"
            )
            return config

        except Exception as e:
            logger.error(f"Failed to read communication config: {e}")
            return CommunicationConfig()

    async def write_communication_config(
        self,
        baudrate: int | None = None,
        slave_id: int | None = None,
        data_type: int | None = None,
    ) -> dict[str, Any]:
        """
        在线修改通信参数。

        写入Pr5.22-Pr5.24寄存器修改通信参数。
        注意：波特率修改仅在当前波特率为9600时生效。

        Args:
            baudrate: 波特率 (2400, 4800, 9600, 19200, 38400, 57600, 115200)
            slave_id: 从站地址 (0-127)
            data_type: 数据类型 (0-5)
                - 0: 8位数据，偶校验，2个停止位
                - 1: 8位数据，奇校验，2个停止位
                - 2: 8位数据，偶校验，1个停止位
                - 3: 8位数据，奇校验，1个停止位
                - 4: 8位数据，无校验，1个停止位（默认）
                - 5: 8位数据，无校验，2个停止位

        Returns:
            Dict[str, Any]: 包含各参数写入结果和警告信息

        Warning:
            根据DM2C-RS556用户手册V1.8，波特率只能在当前波特率为9600时在线修改。
            修改后需要保存参数到EEPROM并重新上电才能生效。

        Example:
            >>> result = await driver.write_communication_config(
            ...     baudrate=115200,
            ...     slave_id=2,
            ...     data_type=4
            ... )
            >>> if result["success"]:
            ...     print("Config updated, please save and restart")
        """
        results = {
            "success": True,
            "baudrate": None,
            "slave_id": None,
            "data_type": None,
            "warnings": [],
            "errors": [],
        }

        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] Communication config updated")
            return results

        try:
            # 检查当前波特率是否为9600（只有9600下才能修改波特率）
            current_baudrate_val = await self._read_register(REG_485_BAUDRATE)
            if current_baudrate_val != 2:  # 2 = 9600
                warning_msg = (
                    f"当前波特率不是9600 (当前值: {current_baudrate_val})，"
                    "波特率修改可能不会生效。请在9600波特率下修改。"
                )
                results["warnings"].append(warning_msg)
                logger.warning(warning_msg)

            # 写入波特率
            if baudrate is not None:
                if baudrate not in BAUDRATE_REVERSE_MAP:
                    error_msg = f"无效的波特率: {baudrate}，有效值: {list(BAUDRATE_REVERSE_MAP.keys())}"
                    results["errors"].append(error_msg)
                    results["success"] = False
                else:
                    baudrate_val = BAUDRATE_REVERSE_MAP[baudrate]
                    if await self._write_register(REG_485_BAUDRATE, baudrate_val):
                        results["baudrate"] = baudrate
                        logger.info(f"Baudrate set to {baudrate} (value: {baudrate_val})")
                    else:
                        results["errors"].append("波特率写入失败")
                        results["success"] = False

            # 写入从站地址
            if slave_id is not None:
                if not 0 <= slave_id <= 127:
                    error_msg = f"无效的从站地址: {slave_id}，有效范围: 0-127"
                    results["errors"].append(error_msg)
                    results["success"] = False
                else:
                    if await self._write_register(REG_485_ID, slave_id):
                        results["slave_id"] = slave_id
                        logger.info(f"Slave ID set to {slave_id}")
                    else:
                        results["errors"].append("从站地址写入失败")
                        results["success"] = False

            # 写入数据类型
            if data_type is not None:
                if not 0 <= data_type <= 5:
                    error_msg = f"无效的数据类型: {data_type}，有效范围: 0-5"
                    results["errors"].append(error_msg)
                    results["success"] = False
                else:
                    if await self._write_register(REG_485_DATA_TYPE, data_type):
                        results["data_type"] = data_type
                        logger.info(f"Data type set to {data_type}")
                    else:
                        results["errors"].append("数据类型写入失败")
                        results["success"] = False

            if results["success"] and (baudrate or slave_id is not None or data_type is not None):
                results["warnings"].append(
                    "通信参数已修改，请调用 save_parameters() 保存到EEPROM，"
                    "并重新上电使参数生效。"
                )

            return results

        except Exception as e:
            logger.error(f"Failed to write communication config: {e}")
            results["errors"].append(str(e))
            results["success"] = False
            return results

    async def get_supported_baudrates(self) -> list[int]:
        """
        获取支持的波特率列表。

        Returns:
            List[int]: 支持的波特率列表
        """
        return list(BAUDRATE_MAP.values())

    async def get_supported_data_types(self) -> dict[int, str]:
        """
        获取支持的数据类型列表。

        Returns:
            Dict[int, str]: 数据类型代码到描述的映射
        """
        return {
            0: "8位数据，偶校验，2个停止位",
            1: "8位数据，奇校验，2个停止位",
            2: "8位数据，偶校验，1个停止位",
            3: "8位数据，奇校验，1个停止位",
            4: "8位数据，无校验，1个停止位",
            5: "8位数据，无校验，2个停止位",
        }

    # ==================== 软件限位寄存器写入功能 ====================

    async def read_driver_soft_limits(self) -> dict[str, Any]:
        """
        读取驱动器内部软件限位设置。

        读取Pr8.06-Pr8.09寄存器获取驱动器内部软件限位值。

        Returns:
            Dict[str, Any]: 包含正负限位信息
                - positive_limit: 正向限位（步数）
                - negative_limit: 负向限位（步数）
                - positive_limit_mm: 正向限位（毫米）
                - negative_limit_mm: 负向限位（毫米）

        Note:
            寄存器映射：
            - Pr8.06 (0x6006): 正限位高位
            - Pr8.07 (0x6007): 正限位低位
            - Pr8.08 (0x6008): 负限位高位
            - Pr8.09 (0x6009): 负限位低位

            软件限位为32位有符号整数，由高16位和低16位组成。
        """
        if not PYMODBUS_AVAILABLE:
            return {
                "positive_limit": 0,
                "negative_limit": 0,
                "positive_limit_mm": 0.0,
                "negative_limit_mm": 0.0,
            }

        try:
            pos_h = await self._read_register(REG_SOFT_LIMIT_POS_H)
            pos_l = await self._read_register(REG_SOFT_LIMIT_POS_L)
            neg_h = await self._read_register(REG_SOFT_LIMIT_NEG_H)
            neg_l = await self._read_register(REG_SOFT_LIMIT_NEG_L)

            # 组合32位有符号整数
            positive_limit = (pos_h << 16) | pos_l
            negative_limit = (neg_h << 16) | neg_l

            # 处理负数
            if positive_limit >= 0x80000000:
                positive_limit -= 0x100000000
            if negative_limit >= 0x80000000:
                negative_limit -= 0x100000000

            return {
                "positive_limit": positive_limit,
                "negative_limit": negative_limit,
                "positive_limit_mm": steps_to_mm(positive_limit, self.steps_per_mm),
                "negative_limit_mm": steps_to_mm(negative_limit, self.steps_per_mm),
            }

        except Exception as e:
            logger.error(f"Failed to read driver soft limits: {e}")
            return {
                "positive_limit": 0,
                "negative_limit": 0,
                "positive_limit_mm": 0.0,
                "negative_limit_mm": 0.0,
            }

    async def write_driver_soft_limits(
        self,
        positive_limit_mm: float | None = None,
        negative_limit_mm: float | None = None,
        positive_limit_steps: int | None = None,
        negative_limit_steps: int | None = None,
    ) -> dict[str, Any]:
        """
        写入驱动器内部软件限位。

        写入Pr8.06-Pr8.09寄存器设置驱动器内部软件限位。
        可以使用毫米或步数作为单位。

        Args:
            positive_limit_mm: 正向限位（毫米），与positive_limit_steps二选一
            negative_limit_mm: 负向限位（毫米），与negative_limit_steps二选一
            positive_limit_steps: 正向限位（步数），优先于positive_limit_mm
            negative_limit_steps: 负向限位（步数），优先于negative_limit_mm

        Returns:
            Dict[str, Any]: 包含写入结果

        Note:
            软件限位在回零时无效。
            修改后需要保存参数到EEPROM才能永久生效。

        Example:
            >>> # 使用毫米设置
            >>> result = await driver.write_driver_soft_limits(
            ...     positive_limit_mm=100.0,
            ...     negative_limit_mm=-100.0
            ... )
            >>> # 使用步数设置
            >>> result = await driver.write_driver_soft_limits(
            ...     positive_limit_steps=160000,
            ...     negative_limit_steps=-160000
            ... )
        """
        results = {
            "success": True,
            "positive_limit": None,
            "negative_limit": None,
            "errors": [],
        }

        if not PYMODBUS_AVAILABLE:
            logger.info("[SIMULATION] Driver soft limits updated")
            return results

        try:
            # 计算正向限位步数
            if positive_limit_steps is not None:
                pos_limit = positive_limit_steps
            elif positive_limit_mm is not None:
                pos_limit = mm_to_steps(positive_limit_mm, self.steps_per_mm)
            else:
                pos_limit = None

            # 计算负向限位步数
            if negative_limit_steps is not None:
                neg_limit = negative_limit_steps
            elif negative_limit_mm is not None:
                neg_limit = mm_to_steps(negative_limit_mm, self.steps_per_mm)
            else:
                neg_limit = None

            # 写入正向限位
            if pos_limit is not None:
                # 处理负数（转换为无符号32位）
                if pos_limit < 0:
                    pos_limit = pos_limit & 0xFFFFFFFF

                pos_h = (pos_limit >> 16) & 0xFFFF
                pos_l = pos_limit & 0xFFFF

                result_h = await self._write_register(REG_SOFT_LIMIT_POS_H, pos_h)
                result_l = await self._write_register(REG_SOFT_LIMIT_POS_L, pos_l)

                if result_h and result_l:
                    results["positive_limit"] = pos_limit
                    logger.info(f"Positive soft limit set to {pos_limit} steps")
                else:
                    results["errors"].append("正向限位写入失败")
                    results["success"] = False

            # 写入负向限位
            if neg_limit is not None:
                # 处理负数（转换为无符号32位）
                if neg_limit < 0:
                    neg_limit = neg_limit & 0xFFFFFFFF

                neg_h = (neg_limit >> 16) & 0xFFFF
                neg_l = neg_limit & 0xFFFF

                result_h = await self._write_register(REG_SOFT_LIMIT_NEG_H, neg_h)
                result_l = await self._write_register(REG_SOFT_LIMIT_NEG_L, neg_l)

                if result_h and result_l:
                    results["negative_limit"] = neg_limit
                    logger.info(f"Negative soft limit set to {neg_limit} steps")
                else:
                    results["errors"].append("负向限位写入失败")
                    results["success"] = False

            if results["success"]:
                logger.info(
                    "Driver soft limits updated. Call save_parameters() to persist to EEPROM."
                )

            return results

        except Exception as e:
            logger.error(f"Failed to write driver soft limits: {e}")
            results["errors"].append(str(e))
            results["success"] = False
            return results

    async def sync_soft_limits_to_driver(self) -> bool:
        """
        将本地软件限位配置同步到驱动器。

        将self.limit_config中的软件限位值写入驱动器寄存器。

        Returns:
            bool: 是否成功

        Example:
            >>> driver.set_soft_limits(100.0, -100.0)
            >>> await driver.sync_soft_limits_to_driver()
        """
        if not self.limit_config.enable:
            logger.warning("Soft limits are not enabled, skipping sync")
            return False

        result = await self.write_driver_soft_limits(
            positive_limit_mm=self.limit_config.positive_limit,
            negative_limit_mm=self.limit_config.negative_limit,
        )

        return result["success"]


# 向后兼容：保留旧类名
LeadshineDM2C_Deprecated = LeadshineDM2C
