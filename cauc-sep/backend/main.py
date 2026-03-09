"""
CAUC-SEP 自旋电子实验平台 - FastAPI后端

功能：
- REST API 电机控制
- WebSocket 实时数据推送（支持所有设备）
- 实验数据管理

重构说明：
- 使用 APIRouter 组织路由
- 保持原有 API 端点向后兼容
- 新增 /api/v1/ 前缀的新端点
- 集成完整设备状态推送系统

安全加固：
- SubTask 13.1: 输入验证增强
- SubTask 13.2: 敏感信息日志脱敏
- SubTask 13.3: API访问频率限制
- SubTask 13.4: CORS配置安全性

设备支持：
- 步进电机 (stepper)
- 电磁铁 (electromagnet)
- 温控系统 (temperature)
- 压电陶瓷 (piezo)
- 微电流计 (ammeter)

作者：Backend Engineer Agent
更新日期：2026-03-07
"""

import asyncio
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from api import ammeter, analysis, device, electromagnet, experiment, health, logs, motor, piezo, temperature, user, tracing, crash_report, update, performance
from api import cache_api
from api.websocket import (
    AlarmLevel,
    ConnectionManager,
    DeviceType,
    MessageType,
    create_alarm_message,
    create_device_status_message,
    create_waveform_message,
    manager,
)
from core.abstract import DeviceStatus
from core.data_storage import DataStorage
from core.dm2c_driver import ALARM_CODES, LeadshineDM2C, mm_to_steps
from core.electromagnet_driver import ElectromagnetDriver, ElectromagnetStatus
from core.logging_config import setup_logging, cleanup_old_logs, get_log_stats
from core.picoammeter import Picoammeter
from core.piezo_controller import PiezoController
from core.startup_config import optimize_startup, get_system_info, check_dependencies
from core.temperature_controller import TemperatureController
from core.tracing import init_tracing, TracingMiddleware, tracer
from core.crash_report import init_crash_report_manager, get_crash_report_storage
from middleware.audit import AuditMiddleware, audit_logger
from middleware.security import (
    SecurityHeadersMiddleware,
    validate_device_id,
    validate_experiment_id,
    validate_array_length,
)
from middleware.rate_limit import RateLimitMiddleware, get_rate_limiter
from middleware.cors_config import (
    get_cors_config,
    setup_cors,
    validate_cors_security,
    log_cors_config,
    CORSEnvironment,
)

# ============================================================================
# 启动优化配置
# ============================================================================

# 应用启动优化（预加载模块、优化GC等）
_startup_result = optimize_startup(
    optimize_numpy=True,
    preload_modules=True,
    optimize_gc=True,
)

# 配置日志系统（支持轮转和归档）
logger = setup_logging(
    log_dir="logs",
    max_bytes=10 * 1024 * 1024,  # 10MB
    backup_count=5,
    level=logging.INFO,
    json_format=False,
    compress_logs=True,
)

# 清理过期日志（保留30天）
_deleted_logs = cleanup_old_logs(log_dir="logs", max_age_days=30)
if _deleted_logs > 0:
    logger.info(f"已清理 {_deleted_logs} 个过期日志文件")

# 记录启动优化结果
logger.info(f"启动优化完成: {_startup_result['optimizations']}")

# 全局设备实例
dm2c: LeadshineDM2C | None = None
storage: DataStorage | None = None
electromagnet_driver: ElectromagnetDriver | None = None
picoammeter: Picoammeter | None = None
temp_controller: TemperatureController | None = None
piezo_controller: PiezoController | None = None


class MoveRequest(BaseModel):
    """移动请求模型。"""

    position_mm: float = Field(..., description="目标位置(mm)", ge=-100, le=100)
    velocity_mm_s: float = Field(10.0, description="速度(mm/s)", ge=1, le=50)


class MoveResponse(BaseModel):
    """移动响应模型。"""

    success: bool
    message: str
    target_position_steps: int
    target_position_mm: float


class JogRequest(BaseModel):
    """点动请求模型。"""

    direction: int = Field(..., description="方向 (1=正, -1=负)", ge=-1, le=1)
    velocity_mm_s: float = Field(5.0, description="速度(mm/s)", ge=1, le=20)


class LimitConfigRequest(BaseModel):
    """限位配置请求模型。"""

    positive_mm: float = Field(50.0, description="正向限位(mm)")
    negative_mm: float = Field(-50.0, description="负向限位(mm)")


class ExperimentRequest(BaseModel):
    """实验请求模型。"""

    name: str = Field(..., description="实验名称", min_length=1, max_length=100)
    description: str = Field("", description="实验描述")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理。

    初始化所有设备并建立连接，记录系统信息和启动状态。
    """
    global dm2c, storage, electromagnet_driver, temp_controller, piezo_controller, picoammeter

    # 记录系统信息
    system_info = get_system_info()
    logger.info("=" * 60)
    logger.info("CAUC-SEP 自旋电子实验平台启动中...")
    logger.info(f"Python版本: {system_info.get('python_version', 'unknown')}")
    logger.info(f"CPU核心数: {system_info.get('cpu_count', 'unknown')}")
    if "memory_total_gb" in system_info:
        logger.info(f"内存总量: {system_info['memory_total_gb']:.2f} GB")
    logger.info("=" * 60)
    
    # 检查依赖
    deps_status = check_dependencies()
    missing_deps = [k for k, v in deps_status.items() if v["status"] == "missing"]
    if missing_deps:
        logger.warning(f"缺少依赖包: {missing_deps}")
    
    logger.info("Starting CAUC-SEP Platform...")

    # 初始化数据存储
    storage = DataStorage("experiments.db")
    
    # 初始化缓存系统
    from core.cache import init_cache_manager, RedisConfig
    from core.local_cache import start_all_cache_cleanup_tasks
    
    cache_manager = init_cache_manager(
        config=RedisConfig(
            host="localhost",
            port=6379,
            db=0,
            max_connections=10,
        ),
        fallback_to_memory=True,
        key_prefix="cauc_sep:",
    )
    logger.info(f"Cache system initialized: backend={cache_manager._backend.value}")
    
    # 启动本地缓存自动清理任务
    await start_all_cache_cleanup_tasks()
    logger.info("Local cache cleanup tasks started")
    
    # 初始化链路追踪系统
    init_tracing(db_path="traces.db")
    logger.info("Tracing system initialized")
    
    # 初始化崩溃报告系统
    init_crash_report_manager(
        app_start_time=time.time(),
        app_version="0.3.0",
        db_path="crash_reports.db",
        auto_cleanup=True,
        cleanup_days=30,
        install_hook=True,
    )
    crash_storage = get_crash_report_storage()
    if crash_storage:
        crash_report.set_crash_storage(crash_storage)
    logger.info("Crash report system initialized")

    # 初始化步进电机
    dm2c = LeadshineDM2C("stepper_01", {"port": "COM3", "slave_id": 1, "steps_per_mm": 1600})
    dm2c.set_soft_limits(50.0, -50.0)

    # 初始化电磁铁（仿真模式）
    electromagnet_driver = ElectromagnetDriver(
        "electromagnet_01",
        {
            "simulation": True,
            "port": "COM4",
            "baudrate": 9600,
            "max_current": 10.0,
        },
    )
    await electromagnet_driver.connect()

    # 初始化温控系统（仿真模式）
    temp_controller = TemperatureController(
        "temp_controller_01",
        {
            "simulation": True,
            "pid_params": {
                "kp": 1.0,
                "ki": 0.1,
                "kd": 0.01,
                "setpoint": 300.0,
            },
        },
    )
    await temp_controller.connect()

    # 初始化压电陶瓷控制器（仿真模式）
    piezo_controller = PiezoController(
        "piezo_01",
        {
            "simulation": True,
            "max_voltage_v": 150.0,
            "max_displacement_um": 100.0,
        },
    )
    await piezo_controller.connect()

    # 初始化微电流采集设备（仿真模式）
    picoammeter = Picoammeter(
        "picoammeter_01",
        {
            "simulation": True,
            "sample_rate": 100.0,
            "buffer_size": 1000,
            "snr_calc_window": 100,
        },
    )
    await picoammeter.connect()

    # 设置设备引用
    motor.set_dm2c(dm2c)
    device.set_storage(storage)
    device.set_devices(
        motor=dm2c,
        electromagnet=electromagnet_driver,
        temperature=temp_controller,
        piezo=piezo_controller,
        ammeter=picoammeter,
    )
    experiment.set_storage(storage)
    piezo.set_piezo(piezo_controller)
    ammeter.set_picoammeter(picoammeter)
    electromagnet.set_electromagnet(electromagnet_driver)
    temperature.set_temperature_controller(temp_controller)
    logs.set_storage(storage)
    
    # 设置健康监控设备引用
    health.set_devices(
        motor=dm2c,
        electromagnet=electromagnet_driver,
        temperature=temp_controller,
        piezo=piezo_controller,
        ammeter=picoammeter,
    )
    
    # 设置审计日志记录器的存储实例
    audit_logger.set_storage(storage)
    
    # 初始化用户系统（创建默认管理员）
    user.init_user_system()

    logger.info("All devices initialized successfully")

    yield

    # 清理资源
    logger.info("Shutting down...")
    
    # 停止缓存系统
    from core.local_cache import stop_all_cache_cleanup_tasks
    from core.cache import get_cache_manager
    
    await stop_all_cache_cleanup_tasks()
    logger.info("Local cache cleanup tasks stopped")
    
    cache_mgr = get_cache_manager()
    if cache_mgr:
        await cache_mgr.async_close()
        logger.info("Redis cache manager closed")
    
    if picoammeter:
        await picoammeter.disconnect()
    if piezo_controller:
        await piezo_controller.disconnect()
    if temp_controller:
        await temp_controller.disconnect()
    if electromagnet_driver:
        await electromagnet_driver.disconnect()
    if dm2c:
        await dm2c.disconnect()

    # 记录日志统计信息
    log_stats = get_log_stats("logs")
    logger.info(f"日志统计: {log_stats['file_count']} 个文件, {log_stats['total_size_mb']:.2f} MB")
    
    logger.info("All devices disconnected")
    logger.info("CAUC-SEP Platform shutdown complete")


app = FastAPI(
    title="CAUC-SEP 自旋电子实验平台",
    description="材料物理专业实验控制系统",
    version="0.3.0",
    lifespan=lifespan,
)

# ==================== 安全中间件配置 ====================

# 添加追踪中间件（最先执行，捕获所有请求）
app.add_middleware(TracingMiddleware, tracer=tracer)

# 添加速率限制中间件
app.add_middleware(RateLimitMiddleware)

# 添加安全响应头中间件
app.add_middleware(SecurityHeadersMiddleware)

# 添加审计日志中间件
app.add_middleware(AuditMiddleware, storage=None)  # storage 将在 lifespan 中设置

# ==================== CORS配置 ====================
# SubTask 13.4: 安全的CORS配置
# 使用新的CORS配置模块，支持环境感知和安全验证

# 获取CORS配置
_cors_config = get_cors_config()

# 验证CORS安全性并记录警告
_cors_warnings = validate_cors_security(_cors_config)
for warning in _cors_warnings:
    logger.warning(f"CORS Security: {warning}")

# 记录CORS配置
log_cors_config(_cors_config)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_config.allow_origins,
    allow_origin_regex=_cors_config.allow_origin_regex,
    allow_credentials=_cors_config.allow_credentials,
    allow_methods=_cors_config.allow_methods,
    allow_headers=_cors_config.allow_headers,
    expose_headers=_cors_config.expose_headers,
    max_age=_cors_config.max_age,
)

# 注册路由
app.include_router(motor.router)
app.include_router(device.router)
app.include_router(experiment.router)
app.include_router(analysis.router)
app.include_router(ammeter.router)
app.include_router(electromagnet.router)
app.include_router(temperature.router)
app.include_router(piezo.router)
app.include_router(logs.router)
app.include_router(user.router)
app.include_router(tracing.router)  # 链路追踪API
app.include_router(crash_report.router)  # 崩溃报告API
app.include_router(health.router)
app.include_router(performance.router)  # 性能分析API
app.include_router(cache_api.router)  # 缓存管理API


@app.get("/")
async def root():
    """根路径，返回服务信息。"""
    return {
        "name": "CAUC-SEP 自旋电子实验平台",
        "version": "0.3.0",
        "status": "running",
        "devices": {
            "stepper": dm2c is not None,
            "electromagnet": electromagnet_driver is not None,
            "temperature": temp_controller is not None,
            "piezo": piezo_controller is not None,
            "ammeter": picoammeter is not None,
        },
    }


@app.get("/api/ws/stats")
async def get_websocket_stats():
    """获取 WebSocket 连接统计信息。

    Returns:
        Dict: 连接统计信息，包括连接数、订阅情况等
    """
    return manager.get_connection_stats()


@app.get("/api/system/info")
async def get_system_info_endpoint():
    """获取系统信息。

    Returns:
        Dict: 系统配置信息，包括Python版本、CPU、内存等
    """
    return get_system_info()


@app.get("/api/system/dependencies")
async def get_dependencies_status():
    """获取依赖包状态。

    Returns:
        Dict: 依赖包及其版本信息
    """
    return check_dependencies()


@app.get("/api/logs/stats")
async def get_logs_statistics():
    """获取日志统计信息。

    Returns:
        Dict: 日志文件统计，包括数量、大小等
    """
    return get_log_stats("logs")


# ==================== 步进电机 API（向后兼容） ====================


@app.get("/api/motor/status")
async def get_motor_status_legacy():
    """获取电机状态（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    status = await dm2c.read_status()
    return status


@app.post("/api/motor/connect")
async def connect_motor_legacy():
    """连接电机（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    result = await dm2c.connect()
    return {
        "success": result,
        "message": "Connected" if result else "Failed to connect",
        "status": dm2c.status.value,
    }


@app.post("/api/motor/disconnect")
async def disconnect_motor_legacy():
    """断开电机连接（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    result = await dm2c.disconnect()
    return {"success": result, "message": "Disconnected", "status": dm2c.status.value}


@app.post("/api/motor/move", response_model=MoveResponse)
async def motor_move_legacy(request: MoveRequest):
    """电机移动（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    if dm2c.status == DeviceStatus.DISCONNECTED:
        raise HTTPException(status_code=400, detail="Motor not connected")

    if dm2c.status == DeviceStatus.EMERGENCY_STOP:
        raise HTTPException(status_code=400, detail="Motor in emergency stop state")

    position_steps = mm_to_steps(request.position_mm)

    result = await dm2c.move_abs(
        request.position_mm,
        request.velocity_mm_s,
        1000.0,
        1000.0,
    )

    return MoveResponse(
        success=result,
        message="Move started" if result else "Move failed (check soft limits)",
        target_position_steps=position_steps,
        target_position_mm=request.position_mm,
    )


@app.post("/api/motor/jog")
async def motor_jog_legacy(request: JogRequest):
    """电机点动（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    if dm2c.status == DeviceStatus.DISCONNECTED:
        raise HTTPException(status_code=400, detail="Motor not connected")

    velocity = int(request.velocity_mm_s * 1600)
    result = await dm2c.jog(request.direction, velocity)

    return {
        "success": result,
        "message": f"JOG {'+' if request.direction > 0 else '-'} started",
        "direction": request.direction,
    }


@app.post("/api/motor/emergency_stop")
async def emergency_stop_legacy():
    """电机急停（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    result = await dm2c.emergency_stop()
    return {"success": result, "message": "Emergency stop triggered", "status": dm2c.status.value}


@app.post("/api/motor/reset")
async def reset_emergency_legacy():
    """复位急停（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    result = await dm2c.reset_emergency()
    return {"success": result, "message": "Emergency stop reset", "status": dm2c.status.value}


@app.get("/api/motor/limits")
async def get_limits_legacy():
    """获取限位配置（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    return {
        "positive_mm": dm2c.limit_config.positive_limit,
        "negative_mm": dm2c.limit_config.negative_limit,
        "enabled": dm2c.limit_config.enable,
    }


@app.post("/api/motor/limits")
async def set_limits_legacy(request: LimitConfigRequest):
    """设置限位配置（旧版 API）。"""
    if not dm2c:
        raise HTTPException(status_code=503, detail="Motor not initialized")

    dm2c.set_soft_limits(request.positive_mm, request.negative_mm)

    return {
        "success": True,
        "message": "Limits updated",
        "positive_mm": request.positive_mm,
        "negative_mm": request.negative_mm,
    }


# ==================== 实验 API（向后兼容） ====================


@app.post("/api/experiments/start")
async def start_experiment_legacy(request: ExperimentRequest):
    """开始实验（旧版 API）。"""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    exp_id = storage.start_experiment(name=request.name, description=request.description)

    return {
        "success": True,
        "experiment_id": exp_id,
        "message": f"Experiment '{request.name}' started",
    }


@app.post("/api/experiments/{exp_id}/stop")
async def stop_experiment_legacy(exp_id: int):
    """停止实验（旧版 API）。"""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    storage.stop_experiment()

    return {"success": True, "experiment_id": exp_id, "message": "Experiment stopped"}


@app.get("/api/experiments")
async def list_experiments_legacy(limit: int = 100):
    """列出实验（旧版 API）。"""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    experiments = storage.list_experiments(limit)
    return {"count": len(experiments), "experiments": experiments}


@app.get("/api/experiments/{exp_id}")
async def get_experiment_legacy(exp_id: int):
    """获取实验详情（旧版 API）。"""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    experiment_data = storage.get_experiment(exp_id)
    if not experiment_data:
        raise HTTPException(status_code=404, detail="Experiment not found")

    return experiment_data


@app.get("/api/experiments/{exp_id}/export")
async def export_experiment_legacy(exp_id: int):
    """导出实验数据（旧版 API）。"""
    if not storage:
        raise HTTPException(status_code=503, detail="Storage not initialized")

    export_dir = "exports"
    os.makedirs(export_dir, exist_ok=True)

    filepath = f"{export_dir}/experiment_{exp_id}.csv"
    result = storage.export_to_csv(exp_id, filepath)

    if result:
        return {"success": True, "filepath": filepath, "message": f"Exported to {filepath}"}
    else:
        raise HTTPException(status_code=500, detail="Export failed")


# ==================== WebSocket 端点 ====================


def get_client_ip(websocket: WebSocket) -> str:
    """获取客户端IP地址。

    Args:
        websocket: WebSocket 连接对象

    Returns:
        str: 客户端IP地址
    """
    if websocket.client:
        return f"{websocket.client.host}:{websocket.client.port}"
    return "unknown"


async def websocket_receive_loop(
    websocket: WebSocket,
    device_type: str,
) -> None:
    """WebSocket 消息接收循环。

    处理客户端消息（心跳响应、订阅请求等）。

    Args:
        websocket: WebSocket 连接对象
        device_type: 设备类型（用于日志）
    """
    try:
        while True:
            try:
                # 非阻塞接收消息
                data = await asyncio.wait_for(
                    websocket.receive_text(), timeout=1.0
                )
                await manager.handle_client_message(websocket, data)
            except asyncio.TimeoutError:
                pass
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.debug(f"[{device_type}] Receive loop ended: {e}")


@app.websocket("/ws/motor")
async def motor_websocket(websocket: WebSocket):
    """步进电机 WebSocket 端点（向后兼容）。

    推送步进电机实时状态数据。
    支持心跳检测和推送频率控制。
    """
    client_ip = get_client_ip(websocket)
    connection_id = await manager.connect(
        websocket, endpoint="/ws/motor", client_ip=client_ip
    )
    logger.info(f"[WS-{connection_id}] Motor WebSocket client connected from {client_ip}")

    # 启动消息接收任务
    receive_task = asyncio.create_task(
        websocket_receive_loop(websocket, "motor")
    )

    try:
        push_interval = manager.get_push_interval("stepper")
        while True:
            if dm2c:
                position = await dm2c.read_position()
                status_word = await dm2c.read_status_word()
                alarm_code = await dm2c.read_alarm_code()

                # 使用新的消息格式
                message = create_device_status_message(
                    device_id=dm2c.device_id,
                    device_type=DeviceType.STEPPER,
                    status=dm2c.status.value,
                    connected=dm2c.status != DeviceStatus.DISCONNECTED,
                    simulation=dm2c.simulation,
                    position_steps=position["position_steps"],
                    position_mm=round(position["position_mm"], 3),
                    status_word=status_word,
                    alarm_code=alarm_code,
                    alarm_text=ALARM_CODES.get(alarm_code, "未知故障"),
                )

                await manager.send_personal_message(message.to_json(), websocket)
            else:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Motor not initialized",
                    }),
                    websocket,
                )

            await asyncio.sleep(push_interval)

    except WebSocketDisconnect:
        logger.info(f"[WS-{connection_id}] Motor WebSocket client disconnected")
    except Exception as e:
        logger.error(f"[WS-{connection_id}] Motor WebSocket error: {e}")
    finally:
        receive_task.cancel()
        manager.disconnect(websocket)


@app.websocket("/ws/electromagnet")
async def electromagnet_websocket(websocket: WebSocket):
    """电磁铁 WebSocket 端点。

    推送电磁铁实时状态数据，包括电流、磁场和扫描进度。
    支持心跳检测和推送频率控制。
    """
    client_ip = get_client_ip(websocket)
    connection_id = await manager.connect(
        websocket, endpoint="/ws/electromagnet", client_ip=client_ip
    )
    logger.info(f"[WS-{connection_id}] Electromagnet WebSocket client connected from {client_ip}")

    # 启动消息接收任务
    receive_task = asyncio.create_task(
        websocket_receive_loop(websocket, "electromagnet")
    )

    try:
        push_interval = manager.get_push_interval("electromagnet")
        while True:
            if electromagnet_driver:
                status_data = await electromagnet_driver.read_status()

                message = create_device_status_message(
                    device_id=electromagnet_driver.device_id,
                    device_type=DeviceType.ELECTROMAGNET,
                    status=status_data["electromagnet_status"],
                    connected=status_data["connected"],
                    simulation=status_data["simulation"],
                    current_value_a=status_data["current_value"],
                    field_value_t=status_data["field_value"],
                    scan_progress=status_data["scan_progress"],
                    max_current_limit=status_data["max_current_limit"],
                )

                await manager.send_personal_message(message.to_json(), websocket)
            else:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Electromagnet not initialized",
                    }),
                    websocket,
                )

            await asyncio.sleep(push_interval)

    except WebSocketDisconnect:
        logger.info(f"[WS-{connection_id}] Electromagnet WebSocket client disconnected")
    except Exception as e:
        logger.error(f"[WS-{connection_id}] Electromagnet WebSocket error: {e}")
    finally:
        receive_task.cancel()
        manager.disconnect(websocket)


@app.websocket("/ws/temperature")
async def temperature_websocket(websocket: WebSocket):
    """温控系统 WebSocket 端点。

    推送温控系统实时状态数据，包括当前温度、输出功率和程序进度。
    支持心跳检测和推送频率控制。
    """
    client_ip = get_client_ip(websocket)
    connection_id = await manager.connect(
        websocket, endpoint="/ws/temperature", client_ip=client_ip
    )
    logger.info(f"[WS-{connection_id}] Temperature WebSocket client connected from {client_ip}")

    # 启动消息接收任务
    receive_task = asyncio.create_task(
        websocket_receive_loop(websocket, "temperature")
    )

    try:
        push_interval = manager.get_push_interval("temperature")
        while True:
            if temp_controller:
                status_data = await temp_controller.read_status()

                message = create_device_status_message(
                    device_id=temp_controller.device_id,
                    device_type=DeviceType.TEMPERATURE,
                    status=status_data["status"],
                    connected=status_data["connected"],
                    simulation=True,
                    current_temperature_k=status_data["current_temperature"],
                    current_output_percent=status_data["current_output"],
                    setpoint_k=status_data["setpoint"],
                    mode=status_data["mode"],
                    pid_running=status_data["pid_running"],
                    program_running=status_data["program"]["running"],
                    protection_triggered=status_data["protection"]["triggered"],
                )

                await manager.send_personal_message(message.to_json(), websocket)
            else:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Temperature controller not initialized",
                    }),
                    websocket,
                )

            await asyncio.sleep(push_interval)

    except WebSocketDisconnect:
        logger.info(f"[WS-{connection_id}] Temperature WebSocket client disconnected")
    except Exception as e:
        logger.error(f"[WS-{connection_id}] Temperature WebSocket error: {e}")
    finally:
        receive_task.cancel()
        manager.disconnect(websocket)


@app.websocket("/ws/piezo")
async def piezo_websocket(websocket: WebSocket):
    """压电陶瓷 WebSocket 端点。

    推送压电陶瓷控制器实时状态数据，包括电压、位移和校准状态。
    支持心跳检测和推送频率控制。
    """
    client_ip = get_client_ip(websocket)
    connection_id = await manager.connect(
        websocket, endpoint="/ws/piezo", client_ip=client_ip
    )
    logger.info(f"[WS-{connection_id}] Piezo WebSocket client connected from {client_ip}")

    # 启动消息接收任务
    receive_task = asyncio.create_task(
        websocket_receive_loop(websocket, "piezo")
    )

    try:
        push_interval = manager.get_push_interval("piezo")
        while True:
            if piezo_controller:
                status_data = await piezo_controller.read_status()

                message = create_device_status_message(
                    device_id=piezo_controller.device_id,
                    device_type=DeviceType.PIEZO,
                    status=status_data["status"],
                    connected=True,
                    simulation=piezo_controller.simulation,
                    current_voltage_v=status_data["current_voltage_v"],
                    current_displacement_um=status_data["current_displacement_um"],
                    target_displacement_um=status_data["target_displacement_um"],
                    control_mode=status_data["control_mode"],
                    calibration_valid=status_data["calibration_valid"],
                )

                await manager.send_personal_message(message.to_json(), websocket)
            else:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Piezo controller not initialized",
                    }),
                    websocket,
                )

            await asyncio.sleep(push_interval)

    except WebSocketDisconnect:
        logger.info(f"[WS-{connection_id}] Piezo WebSocket client disconnected")
    except Exception as e:
        logger.error(f"[WS-{connection_id}] Piezo WebSocket error: {e}")
    finally:
        receive_task.cancel()
        manager.disconnect(websocket)


@app.websocket("/ws/ammeter")
async def ammeter_websocket(websocket: WebSocket):
    """微电流计 WebSocket 端点。

    推送微电流计实时采集数据，支持多通道同步推送。
    支持心跳检测和推送频率控制。
    """
    client_ip = get_client_ip(websocket)
    connection_id = await manager.connect(
        websocket, endpoint="/ws/ammeter", client_ip=client_ip
    )
    logger.info(f"[WS-{connection_id}] Ammeter WebSocket client connected from {client_ip}")

    # 启动消息接收任务
    receive_task = asyncio.create_task(
        websocket_receive_loop(websocket, "ammeter")
    )

    try:
        push_interval = manager.get_push_interval("ammeter")
        while True:
            if picoammeter:
                # 读取所有通道数据
                channel_data = await picoammeter.read_all_channels()

                # 构建波形数据点
                data_points = []
                for ch, data in enumerate(channel_data):
                    if data:
                        data_points.append(
                            {
                                "channel": ch,
                                "value": data.current_pa,
                                "timestamp": data.timestamp,
                                "snr_db": data.snr_db,
                            }
                        )

                # 创建波形数据消息
                message = create_waveform_message(
                    device_id=picoammeter.device_id,
                    device_type=DeviceType.AMMETER,
                    sample_rate=picoammeter._acq_config.sample_rate,
                    data_points=data_points,
                )

                await manager.send_personal_message(message.to_json(), websocket)
            else:
                await manager.send_personal_message(
                    json.dumps({
                        "type": "error",
                        "timestamp": datetime.now().isoformat(),
                        "message": "Picoammeter not initialized",
                    }),
                    websocket,
                )

            await asyncio.sleep(push_interval)

    except WebSocketDisconnect:
        logger.info(f"[WS-{connection_id}] Ammeter WebSocket client disconnected")
    except Exception as e:
        logger.error(f"[WS-{connection_id}] Ammeter WebSocket error: {e}")
    finally:
        receive_task.cancel()
        manager.disconnect(websocket)


@app.websocket("/ws/devices")
async def all_devices_websocket(websocket: WebSocket):
    """统一设备状态 WebSocket 端点。

    推送所有设备的实时状态数据，支持消息类型订阅。
    支持心跳检测和推送频率控制。
    """
    client_ip = get_client_ip(websocket)
    connection_id = await manager.connect(
        websocket, endpoint="/ws/devices", client_ip=client_ip
    )
    logger.info(f"[WS-{connection_id}] All devices WebSocket client connected from {client_ip}")

    try:
        push_interval = manager.get_push_interval("all_devices")
        while True:
            try:
                # 非阻塞接收消息
                data = await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
                await manager.handle_client_message(websocket, data)
            except asyncio.TimeoutError:
                pass

            # 推送所有设备状态
            messages = []

            # 步进电机状态
            if dm2c:
                position = await dm2c.read_position()
                status_word = await dm2c.read_status_word()
                alarm_code = await dm2c.read_alarm_code()

                messages.append(
                    create_device_status_message(
                        device_id=dm2c.device_id,
                        device_type=DeviceType.STEPPER,
                        status=dm2c.status.value,
                        connected=dm2c.status != DeviceStatus.DISCONNECTED,
                        simulation=dm2c.simulation,
                        position_mm=round(position["position_mm"], 3),
                        alarm_code=alarm_code,
                    )
                )

            # 电磁铁状态
            if electromagnet_driver:
                status_data = await electromagnet_driver.read_status()
                messages.append(
                    create_device_status_message(
                        device_id=electromagnet_driver.device_id,
                        device_type=DeviceType.ELECTROMAGNET,
                        status=status_data["electromagnet_status"],
                        connected=status_data["connected"],
                        current_value_a=status_data["current_value"],
                        field_value_t=status_data["field_value"],
                    )
                )

            # 温控状态
            if temp_controller:
                status_data = await temp_controller.read_status()
                messages.append(
                    create_device_status_message(
                        device_id=temp_controller.device_id,
                        device_type=DeviceType.TEMPERATURE,
                        status=status_data["status"],
                        connected=status_data["connected"],
                        current_temperature_k=status_data["current_temperature"],
                        setpoint_k=status_data["setpoint"],
                    )
                )

            # 压电陶瓷状态
            if piezo_controller:
                status_data = await piezo_controller.read_status()
                messages.append(
                    create_device_status_message(
                        device_id=piezo_controller.device_id,
                        device_type=DeviceType.PIEZO,
                        status=status_data["status"],
                        connected=True,
                        current_voltage_v=status_data["current_voltage_v"],
                        current_displacement_um=status_data["current_displacement_um"],
                    )
                )

            # 微电流计数据
            if picoammeter:
                channel_data = await picoammeter.read_all_channels()
                data_points = [
                    {
                        "channel": ch,
                        "value": data.current_pa if data else 0.0,
                        "timestamp": data.timestamp if data else time.time(),
                    }
                    for ch, data in enumerate(channel_data)
                ]

                messages.append(
                    create_waveform_message(
                        device_id=picoammeter.device_id,
                        device_type=DeviceType.AMMETER,
                        sample_rate=picoammeter.sample_rate,
                        data_points=data_points,
                    )
                )

            # 发送所有消息
            for msg in messages:
                await manager.send_personal_message(msg.to_json(), websocket)

            await asyncio.sleep(push_interval)

    except WebSocketDisconnect:
        logger.info(f"[WS-{connection_id}] All devices WebSocket client disconnected")
    except Exception as e:
        logger.error(f"[WS-{connection_id}] All devices WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)


# 静态文件服务
if os.path.exists("frontend/dist"):
    app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")


if __name__ == "__main__":
    import uvicorn

    logger.info("Starting server...")
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
