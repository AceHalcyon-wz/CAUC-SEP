"""
文件名: config.py
路径: backend/core/
功能: 应用配置管理，支持环境变量和 .env 文件，统一配置管理
版本: v2.0
创建日期: 2026-03-15
最后更新: 2026-03-25
作者: Backend Engineer Agent

依赖:
    - pydantic>=2.5.0
    - pydantic-settings>=2.0.0

安全约束:
    - 生产环境必须设置安全的JWT密钥
    - 敏感信息必须通过环境变量配置
    - 设备参数范围必须经过合法性校验
"""

from typing import Optional, List, Dict, Any
from functools import lru_cache
from enum import Enum
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Environment(str, Enum):
    """运行环境枚举。"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


class LogLevel(str, Enum):
    """日志级别枚举。"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class Settings(BaseSettings):
    """
    应用配置类。
    
    支持从环境变量和 .env 文件加载配置。
    环境变量优先级高于 .env 文件。
    
    配置分类：
    1. 应用基础配置 - 应用名称、版本、环境
    2. 数据库配置 - SQLite连接、连接池
    3. Redis配置 - 缓存、会话管理
    4. 设备配置 - 串口、Modbus参数、设备参数范围
    5. 安全配置 - JWT、密码策略
    6. 日志配置 - 日志级别、输出格式
    7. CORS配置 - 跨域访问控制
    8. WebSocket配置 - 实时通信
    9. 实验配置 - 并发控制、数据采集
    """
    
    model_config = SettingsConfigDict(
        env_file='.env',
        env_file_encoding='utf-8',
        env_nested_delimiter='__',
        case_sensitive=False,
        extra='ignore',
    )
    
    # ==================== 应用配置 ====================
    app_name: str = "CAUC-SEP"
    app_version: str = "0.4.0"
    app_env: str = Field(
        default="development", 
        pattern="^(development|staging|production)$"
    )
    debug: bool = False
    host: str = "127.0.0.1"
    port: int = 8000
    
    # ==================== 数据库配置 ====================
    database_url: str = "sqlite:///experiments.db"
    database_pool_size: int = 5
    database_max_overflow: int = 10
    database_echo: bool = False
    
    # ==================== Redis 配置 ====================
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None
    redis_max_connections: int = 10
    redis_socket_timeout: int = 5
    redis_socket_connect_timeout: int = 5
    
    @property
    def redis_url(self) -> str:
        """构建 Redis 连接 URL。"""
        if self.redis_password:
            return (
                f"redis://:{self.redis_password}@"
                f"{self.redis_host}:{self.redis_port}/{self.redis_db}"
            )
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"
    
    # ==================== 设备配置 - 步进电机 ====================
    motor_device_id: str = "stepper_01"
    motor_port: str = "COM3"
    motor_slave_id: int = Field(default=1, ge=1, le=247, description="Modbus从站ID，范围1-247")
    motor_baudrate: int = Field(default=115200, description="串口波特率")
    motor_parity: str = Field(default="N", pattern="^[NEOM]$", description="校验位：N-无，E-偶，O-奇，M-标记")
    motor_stopbits: int = Field(default=1, ge=1, le=2, description="停止位：1或2")
    motor_bytesize: int = Field(default=8, ge=5, le=9, description="数据位：5-9位")
    motor_timeout: float = Field(default=1.0, gt=0, le=30, description="通信超时时间（秒）")
    motor_steps_per_mm: int = Field(default=1600, gt=0, description="每毫米步数")
    motor_positive_limit: float = Field(default=50.0, description="正向软件限位（毫米）")
    motor_negative_limit: float = Field(default=-50.0, description="负向软件限位（毫米）")
    motor_simulation: bool = True
    
    # 步进电机参数范围约束
    motor_speed_min: int = Field(default=100, ge=1, description="最小速度（脉冲/秒）")
    motor_speed_max: int = Field(default=5000, le=100000, description="最大速度（脉冲/秒）")
    motor_speed_default: int = Field(default=500, description="默认速度（脉冲/秒）")
    motor_acceleration_min: int = Field(default=10, ge=1, description="最小加速度（ms）")
    motor_acceleration_max: int = Field(default=10000, description="最大加速度（ms）")
    motor_acceleration_default: int = Field(default=100, description="默认加速度（ms）")
    motor_position_min: int = Field(default=-1000000, description="最小位置（脉冲）")
    motor_position_max: int = Field(default=1000000, description="最大位置（脉冲）")
    
    # ==================== 设备配置 - 电磁铁 ====================
    electromagnet_device_id: str = "electromagnet_01"
    electromagnet_port: str = "COM4"
    electromagnet_baudrate: int = Field(default=9600, description="串口波特率")
    electromagnet_parity: str = Field(default="N", pattern="^[NEOM]$", description="校验位")
    electromagnet_stopbits: int = Field(default=1, ge=1, le=2, description="停止位")
    electromagnet_bytesize: int = Field(default=8, ge=5, le=9, description="数据位")
    electromagnet_timeout: float = Field(default=1.0, gt=0, le=30, description="通信超时时间（秒）")
    electromagnet_max_current: float = Field(default=10.0, gt=0, le=100, description="最大电流（安培）")
    electromagnet_simulation: bool = True
    
    # 电磁铁参数范围约束
    electromagnet_current_min: float = Field(default=0.0, ge=0, description="最小电流（安培）")
    electromagnet_current_max: float = Field(default=10.0, le=100, description="最大电流（安培）")
    electromagnet_current_default: float = Field(default=5.0, description="默认电流（安培）")
    
    # ==================== 设备配置 - 温控器 ====================
    temperature_device_id: str = "temp_controller_01"
    temperature_port: str = "COM5"
    temperature_baudrate: int = Field(default=9600, description="串口波特率")
    temperature_slave_id: int = Field(default=1, ge=1, le=247, description="Modbus从站ID")
    temperature_simulation: bool = True
    temperature_pid_kp: float = Field(default=1.0, ge=0, description="PID比例系数")
    temperature_pid_ki: float = Field(default=0.1, ge=0, description="PID积分系数")
    temperature_pid_kd: float = Field(default=0.01, ge=0, description="PID微分系数")
    temperature_max_temp: float = Field(default=400.0, description="最高温度（摄氏度）")
    temperature_min_temp: float = Field(default=-50.0, description="最低温度（摄氏度）")
    
    # 温控器参数范围约束
    temperature_target_min: float = Field(default=-50.0, description="目标温度下限（摄氏度）")
    temperature_target_max: float = Field(default=400.0, description="目标温度上限（摄氏度）")
    temperature_tolerance: float = Field(default=0.5, gt=0, description="温度容差（摄氏度）")
    
    # ==================== 设备配置 - 压电控制器 ====================
    piezo_device_id: str = "piezo_01"
    piezo_port: str = "COM6"
    piezo_simulation: bool = True
    piezo_max_voltage: float = Field(default=150.0, gt=0, le=200, description="最大电压（伏特）")
    piezo_max_displacement: float = Field(default=100.0, gt=0, description="最大位移（微米）")
    piezo_channels: int = Field(default=3, ge=1, le=8, description="通道数")
    
    # 压电控制器参数范围约束
    piezo_voltage_min: float = Field(default=0.0, ge=0, description="最小电压（伏特）")
    piezo_voltage_max: float = Field(default=150.0, le=200, description="最大电压（伏特）")
    piezo_voltage_default: float = Field(default=0.0, description="默认电压（伏特）")
    
    # ==================== 设备配置 - 皮安表 ====================
    ammeter_device_id: str = "picoammeter_01"
    ammeter_port: str = "COM7"
    ammeter_simulation: bool = True
    ammeter_sample_rate: float = Field(default=100.0, gt=0, le=10000, description="采样率（Hz）")
    ammeter_current_range: str = Field(default="auto", description="电流量程：auto或具体值")
    
    # 皮安表参数范围约束
    ammeter_current_min: float = Field(default=-1e-6, description="最小电流（安培）")
    ammeter_current_max: float = Field(default=1e-6, description="最大电流（安培）")
    
    # ==================== 安全配置 ====================
    jwt_secret_key: str = Field(
        default="change-me-in-production-use-secure-key"
    )
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7
    password_min_length: int = 8
    password_require_uppercase: bool = True
    password_require_lowercase: bool = True
    password_require_digit: bool = True
    password_require_special: bool = False
    
    # ==================== CORS 配置 ====================
    cors_allow_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173", 
            "http://127.0.0.1:5173"
        ]
    )
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = Field(default_factory=lambda: ["*"])
    cors_allow_headers: list[str] = Field(default_factory=lambda: ["*"])
    
    # ==================== 日志配置 ====================
    log_level: str = Field(
        default="INFO", 
        pattern="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"
    )
    log_dir: str = "logs"
    log_max_bytes: int = 10 * 1024 * 1024
    log_backup_count: int = 5
    log_compress: bool = True
    log_json_format: bool = False
    log_include_timestamp: bool = True
    log_include_caller: bool = True
    
    # ==================== 缓存配置 ====================
    cache_default_ttl: int = 300
    cache_max_memory_items: int = 1000
    cache_key_prefix: str = "cauc_sep:"
    
    # ==================== WebSocket 配置 ====================
    ws_heartbeat_interval: int = 30
    ws_max_connections: int = 100
    ws_message_queue_size: int = 1000
    
    # ==================== 实验配置 ====================
    experiment_max_concurrent: int = 5
    experiment_data_batch_size: int = 1000
    experiment_auto_save_interval: int = 60
    
    # ==================== 验证器 ====================
    
    @field_validator('jwt_secret_key')
    @classmethod
    def validate_jwt_secret(cls, v: str, info) -> str:
        """验证 JWT 密钥安全性。"""
        app_env = info.data.get('app_env', 'development')
        if v == "change-me-in-production-use-secure-key":
            if app_env == 'production':
                raise ValueError(
                    "生产环境必须设置安全的 JWT_SECRET_KEY 环境变量"
                )
        return v
    
    @field_validator('port')
    @classmethod
    def validate_port(cls, v: int) -> int:
        """验证端口号范围。"""
        if not 1 <= v <= 65535:
            raise ValueError(f"端口号必须在 1-65535 范围内，当前: {v}")
        return v
    
    @field_validator('cors_allow_origins', mode='before')
    @classmethod
    def parse_cors_origins(cls, v) -> list[str]:
        """解析 CORS 源配置。"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(',')]
        return v
    
    @model_validator(mode='after')
    def validate_limits(self) -> 'Settings':
        """验证软限位配置。"""
        if self.motor_negative_limit >= self.motor_positive_limit:
            raise ValueError(
                f"电机负向限位 ({self.motor_negative_limit}) 必须"
                f"小于正向限位 ({self.motor_positive_limit})"
            )
        return self
    
    @property
    def is_production(self) -> bool:
        """是否为生产环境。"""
        return self.app_env == 'production'
    
    @property
    def is_development(self) -> bool:
        """是否为开发环境。"""
        return self.app_env == 'development'


@lru_cache
def get_settings() -> Settings:
    """
    获取配置单例。
    
    使用 lru_cache 确保配置只加载一次。
    
    Returns:
        Settings: 配置实例
    """
    return Settings()


settings = get_settings()
