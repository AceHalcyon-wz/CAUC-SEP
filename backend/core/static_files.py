"""
静态文件服务处理模块

功能：
- 兼容开发环境和Nuitka打包环境
- 动态检测前端静态文件路径
- 提供静态文件挂载配置

作者：Backend Engineer Agent
日期：2026-03-11
"""

import logging
import sys
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def get_base_path() -> Path:
    """
    获取应用基础路径。

    兼容以下环境：
    - 开发环境：直接运行Python脚本（返回项目根目录）
    - Nuitka打包：frozen可执行文件所在目录
    - PyInstaller打包：frozen可执行文件所在目录

    Returns:
        Path: 应用基础路径（项目根目录或EXE所在目录）
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    else:
        return Path(__file__).parent.parent.parent.resolve()


def get_frontend_path() -> Optional[str]:
    """
    获取前端静态文件路径。

    按优先级检测以下路径：
    1. EXE同级目录的frontend/dist
    2. EXE同级目录的dist/frontend/dist
    3. 项目根目录的frontend/dist（开发环境）

    Returns:
        str | None: 前端静态文件目录路径
    """
    base_path = get_base_path()

    possible_paths = [
        base_path / "frontend" / "dist",
        base_path / "dist" / "frontend" / "dist",
        base_path.parent / "frontend" / "dist",
        base_path / "frontend",
    ]

    for path in possible_paths:
        if path.exists() and list(path.iterdir()):
            logger.info(f"Found frontend static files at: {path}")
            return str(path)

    logger.warning("Frontend static files not found, checked paths:")
    for path in possible_paths:
        logger.warning(f"  - {path}: {'EXISTS' if path.exists() else 'NOT FOUND'}")

    return None


def get_assets_path() -> Optional[Path]:
    """
    获取资源文件路径（图标、配置等）。

    Returns:
        Path | None: 资源文件目录路径
    """
    base_path = get_base_path()

    possible_paths = [
        base_path / "assets",
        base_path.parent / "backend" / "assets",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def get_data_path() -> Path:
    """
    获取数据存储路径。

    优先使用EXE同级目录的data文件夹，
    不存在则自动创建。

    Returns:
        Path: 数据存储路径
    """
    base_path = get_base_path()
    data_path = base_path / "data"

    if not data_path.exists():
        data_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created data directory: {data_path}")

    return data_path


def get_config_path() -> Path:
    """
    获取配置文件路径。

    Returns:
        Path: 配置文件目录路径
    """
    base_path = get_base_path()
    config_path = base_path / "config"

    if not config_path.exists():
        config_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created config directory: {config_path}")

    return config_path


def get_logs_path() -> Path:
    """
    获取日志文件路径。

    Returns:
        Path: 日志文件目录路径
    """
    base_path = get_base_path()
    logs_path = base_path / "logs"

    if not logs_path.exists():
        logs_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created logs directory: {logs_path}")

    return logs_path


def get_db_path(db_name: str = "experiments.db") -> Path:
    """
    获取数据库文件路径。

    Args:
        db_name: 数据库文件名

    Returns:
        Path: 数据库文件完整路径
    """
    data_path = get_data_path()
    return data_path / db_name


def mount_static_files(app, frontend_path: Optional[str] = None):
    """
    挂载静态文件服务到FastAPI应用。

    Args:
        app: FastAPI应用实例
        frontend_path: 前端静态文件路径（可选，自动检测）

    Returns:
        bool: 是否成功挂载
    """
    from fastapi.staticfiles import StaticFiles

    if frontend_path is None:
        frontend_path = get_frontend_path()

    if frontend_path:
        try:
            app.mount("/", StaticFiles(directory=frontend_path, html=True), name="static")
            logger.info(f"Static files mounted from: {frontend_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to mount static files: {e}")
            return False
    else:
        logger.warning("Frontend static files not found - web UI will not be available")
        return False


def print_environment_info():
    """打印环境信息，用于调试。"""
    print("=" * 60)
    print("Environment Information")
    print("=" * 60)
    print(f"Frozen: {getattr(sys, 'frozen', False)}")
    print(f"Executable: {sys.executable}")
    print(f"Base path: {get_base_path()}")
    print(f"Frontend path: {get_frontend_path()}")
    print(f"Assets path: {get_assets_path()}")
    print(f"Data path: {get_data_path()}")
    print(f"Config path: {get_config_path()}")
    print(f"Logs path: {get_logs_path()}")
    print("=" * 60)


if __name__ == "__main__":
    print_environment_info()
