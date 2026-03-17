"""
文件名: config.py
路径: backend/core/
功能: 应用配置管理，支持环境变量和 .env 文件
版本: v1.0
创建日期: 2026-03-15
"""

from typing import Optional, List
from functools import lru_cache
from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    应用配置类。
    
    支持从环境变量和 .env 文件加载配置。
    环境变量优先级高于 .env 文件。
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
    motor_slave_id: int = 1
    motor_baudrate: int = 115200
    motor_parity: str = "N"
    motor_stopbits: int = 1
    motor_bytesize: int = 8
    motor_timeout: float = 1.0
    motor_steps_per_mm: int = 1600
    motor_positive_limit: float = 50.0
    motor_negative_limit: float = -50.0
    motor_simulation: bool = True
    
    # ==================== 设备配置 - 电磁铁 ====================
    electromagnet_device_id: str = "electromagnet_01"
    electromagnet_port: str = "COM4"
    electromagnet_baudrate: int = 9600
    electromagnet_parity: str = "N"
    electromagnet_stopbits: int = 1
    electromagnet_bytesize: int = 8
    electromagnet_timeout: float = 1.0
    electromagnet_max_current: float = 10.0
    electromagnet_simulation: bool = True
    
    # ==================== 设备配置 - 温控器 ====================
    temperature_device_id: str = "temp_controller_01"
    temperature_port: str = "COM5"
    temperature_baudrate: int = 9600
    temperature_slave_id: int = 1
    temperature_simulation: bool = True
    temperature_pid_kp: float = 1.0
    temperature_pid_ki: float = 0.1
    temperature_pid_kd: float = 0.01
    temperature_max_temp: float = 400.0
    temperature_min_temp: float = -50.0
    
    # ==================== 设备配置 - 压电控制器 ====================
    piezo_device_id: str = "piezo_01"
    piezo_port: str = "COM6"
    piezo_simulation: bool = True
    piezo_max_voltage: float = 150.0
    piezo_max_displacement: float = 100.0
    piezo_channels: int = 3
    
    # ==================== 设备配置 - 皮安表 ====================
    ammeter_device_id: str = "picoammeter_01"
    ammeter_port: str = "COM7"
    ammeter_simulation: bool = True
    ammeter_sample_rate: float = 100.0
    ammeter_current_range: str = "auto"
    
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
