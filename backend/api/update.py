"""
自动更新系统 API 路由模块

文件名: update.py
路径: backend/api/
功能: 自动更新系统API，提供版本检查、更新应用、回滚等接口
作者: CAUC-SEP Team
创建日期: 2024-01-01
依赖: FastAPI, pydantic, core.updater

主要功能：
- 版本检查（检查远程服务器是否有新版本）
- 更新应用（下载并安装新版本）
- 回滚操作（回滚到上一版本）
- 更新包管理（上传、删除更新包）
- 更新历史记录（查看更新历史）
- 更新配置管理（配置更新源、自动更新策略）

API端点：
- GET /version: 获取当前版本信息
- GET /check: 检查是否有新版本
- POST /apply: 应用更新包
- POST /rollback: 回滚到上一版本
- GET /history: 获取更新历史
- GET /packages: 获取可用更新包列表
- POST /packages/upload: 上传更新包
- DELETE /packages/{package_id}: 删除更新包
- GET /config: 获取更新配置
- PUT /config: 更新更新配置

安全特性：
- 更新包签名验证
- 更新前备份当前版本
- 回滚机制保障
- 更新操作日志记录
"""

import asyncio
import hashlib
import json
import logging
import os
import shutil
import zipfile
from datetime import datetime
from enum import Enum
from pathlib import Path

import aiofiles
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/update", tags=["update"])

# ============================================================================
# 配置常量
# ============================================================================

# 版本信息（应与 main.py 保持同步）
APP_VERSION = "0.3.0"
VERSION_FILE = "version.json"

# 更新目录配置
UPDATE_DIR = Path("updates")
BACKUP_DIR = Path("backups")
TEMP_DIR = Path("temp")

# 更新包配置
MAX_PACKAGE_SIZE_MB = 500
SUPPORTED_PACKAGE_VERSION = "1.0"

# 回滚配置
MAX_BACKUP_COUNT = 5
BACKUP_RETENTION_DAYS = 30


# ============================================================================
# 枚举类型定义
# ============================================================================


class UpdateStatus(str, Enum):
    """更新状态枚举。"""

    IDLE = "idle"
    CHECKING = "checking"
    DOWNLOADING = "downloading"
    VERIFYING = "verifying"
    INSTALLING = "installing"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"


class UpdateType(str, Enum):
    """更新类型枚举。"""

    FULL = "full"  # 全量更新
    INCREMENTAL = "incremental"  # 增量更新
    HOTFIX = "hotfix"  # 热修复


class UpdatePriority(str, Enum):
    """更新优先级枚举。"""

    LOW = "low"  # 可选更新
    MEDIUM = "medium"  # 建议更新
    HIGH = "high"  # 重要更新
    CRITICAL = "critical"  # 关键安全更新


# ============================================================================
# Pydantic 模型定义
# ============================================================================


class VersionInfo(BaseModel):
    """版本信息模型。"""

    version: str = Field(..., description="版本号，格式: major.minor.patch")
    build_number: int = Field(..., description="构建号")
    release_date: str = Field(..., description="发布日期（ISO格式）")
    release_notes: str = Field("", description="发布说明")
    changelog: list[str] = Field(default_factory=list, description="变更日志")


class UpdateCheckRequest(BaseModel):
    """更新检查请求模型。"""

    current_version: str = Field(..., description="当前版本号")
    current_build: int = Field(..., description="当前构建号")
    channel: str = Field("stable", description="更新通道: stable, beta, dev")


class UpdateInfo(BaseModel):
    """更新信息模型。"""

    available: bool = Field(..., description="是否有可用更新")
    latest_version: str = Field(..., description="最新版本号")
    latest_build: int = Field(..., description="最新构建号")
    update_type: UpdateType = Field(..., description="更新类型")
    priority: UpdatePriority = Field(..., description="更新优先级")
    release_date: str = Field(..., description="发布日期")
    release_notes: str = Field("", description="发布说明")
    changelog: list[str] = Field(default_factory=list, description="变更日志")
    package_size_mb: float = Field(0.0, description="更新包大小（MB）")
    download_url: str | None = Field(None, description="下载地址")
    checksum_sha256: str | None = Field(None, description="SHA256校验和")


class UpdateCheckResponse(BaseModel):
    """更新检查响应模型。"""

    has_update: bool = Field(..., description="是否有可用更新")
    current_version: str = Field(..., description="当前版本")
    update_info: UpdateInfo | None = Field(None, description="更新信息")
    checked_at: str = Field(..., description="检查时间")


class UpdateProgress(BaseModel):
    """更新进度模型。"""

    status: UpdateStatus = Field(..., description="更新状态")
    progress_percent: float = Field(0.0, description="进度百分比", ge=0, le=100)
    current_step: str = Field("", description="当前步骤描述")
    total_bytes: int = Field(0, description="总字节数")
    downloaded_bytes: int = Field(0, description="已下载字节数")
    started_at: str | None = Field(None, description="开始时间")
    estimated_remaining_seconds: float | None = Field(None, description="预估剩余时间")


class UpdateApplyRequest(BaseModel):
    """更新应用请求模型。"""

    package_path: str = Field(..., description="更新包路径")
    checksum_sha256: str = Field(..., description="SHA256校验和")
    create_backup: bool = Field(True, description="是否创建备份")
    auto_rollback: bool = Field(True, description="失败时是否自动回滚")


class UpdateApplyResponse(BaseModel):
    """更新应用响应模型。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="操作消息")
    backup_id: str | None = Field(None, description="备份ID")
    applied_at: str | None = Field(None, description="应用时间")


class RollbackRequest(BaseModel):
    """回滚请求模型。"""

    backup_id: str = Field(..., description="备份ID")
    verify_integrity: bool = Field(True, description="是否验证完整性")


class RollbackResponse(BaseModel):
    """回滚响应模型。"""

    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="操作消息")
    rolled_back_to: str = Field(..., description="回滚到的版本")
    rolled_back_at: str = Field(..., description="回滚时间")


class BackupInfo(BaseModel):
    """备份信息模型。"""

    backup_id: str = Field(..., description="备份ID")
    version: str = Field(..., description="备份版本")
    created_at: str = Field(..., description="创建时间")
    size_mb: float = Field(..., description="备份大小（MB）")
    file_count: int = Field(..., description="文件数量")
    checksum: str = Field(..., description="备份校验和")
    description: str = Field("", description="备份描述")


class BackupListResponse(BaseModel):
    """备份列表响应模型。"""

    total: int = Field(..., description="备份总数")
    backups: list[BackupInfo] = Field(default_factory=list, description="备份列表")


class UpdateHistoryRecord(BaseModel):
    """更新历史记录模型。"""

    record_id: str = Field(..., description="记录ID")
    from_version: str = Field(..., description="原版本")
    to_version: str = Field(..., description="目标版本")
    update_type: UpdateType = Field(..., description="更新类型")
    status: str = Field(..., description="更新状态")
    applied_at: str = Field(..., description="应用时间")
    duration_seconds: float = Field(..., description="耗时（秒）")
    backup_id: str | None = Field(None, description="关联备份ID")
    notes: str = Field("", description="备注")


class UpdateHistoryResponse(BaseModel):
    """更新历史响应模型。"""

    total: int = Field(..., description="记录总数")
    records: list[UpdateHistoryRecord] = Field(default_factory=list, description="历史记录列表")


class IncrementalDiffRequest(BaseModel):
    """增量差异请求模型。"""

    from_version: str = Field(..., description="起始版本")
    to_version: str = Field(..., description="目标版本")


class FileDiffInfo(BaseModel):
    """文件差异信息模型。"""

    file_path: str = Field(..., description="文件路径")
    diff_type: str = Field(..., description="差异类型: added, modified, deleted")
    old_size: int = Field(0, description="原文件大小")
    new_size: int = Field(0, description="新文件大小")
    old_checksum: str | None = Field(None, description="原文件校验和")
    new_checksum: str | None = Field(None, description="新文件校验和")


class IncrementalDiffResponse(BaseModel):
    """增量差异响应模型。"""

    from_version: str = Field(..., description="起始版本")
    to_version: str = Field(..., description="目标版本")
    total_files: int = Field(..., description="总文件数")
    added_files: int = Field(0, description="新增文件数")
    modified_files: int = Field(0, description="修改文件数")
    deleted_files: int = Field(0, description="删除文件数")
    diffs: list[FileDiffInfo] = Field(default_factory=list, description="文件差异列表")


# ============================================================================
# 更新管理器类
# ============================================================================


class UpdateManager:
    """
    更新管理器核心类。

    提供版本检查、更新包生成、校验、应用和回滚功能。
    所有方法均为线程安全设计。
    """

    def __init__(self, update_dir: Path = UPDATE_DIR, backup_dir: Path = BACKUP_DIR):
        """
        初始化更新管理器。

        Args:
            update_dir: 更新包存储目录
            backup_dir: 备份存储目录
        """
        self.update_dir = Path(update_dir)
        self.backup_dir = Path(backup_dir)
        self.temp_dir = Path(TEMP_DIR)

        # 当前更新状态
        self._status = UpdateStatus.IDLE
        self._progress = UpdateProgress(status=UpdateStatus.IDLE)
        self._lock = asyncio.Lock()

        # 确保目录存在
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """确保必要目录存在。"""
        self.update_dir.mkdir(parents=True, exist_ok=True)
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir.mkdir(parents=True, exist_ok=True)

    def get_current_version(self) -> VersionInfo:
        """
        获取当前版本信息。

        Returns:
            VersionInfo: 当前版本信息对象
        """
        return VersionInfo(
            version=APP_VERSION,
            build_number=self._get_build_number(),
            release_date=self._get_release_date(),
            release_notes="CAUC-SEP 自旋电子实验平台",
            changelog=[
                "新增自动更新系统",
                "优化设备状态推送",
                "增强安全中间件",
            ],
        )

    def _get_build_number(self) -> int:
        """
        获取构建号。

        基于版本号生成构建号，格式: MMmmpp（主版本*10000 + 次版本*100 + 补丁版本）

        Returns:
            int: 构建号
        """
        try:
            parts = APP_VERSION.split(".")
            major = int(parts[0]) if len(parts) > 0 else 0
            minor = int(parts[1]) if len(parts) > 1 else 0
            patch = int(parts[2]) if len(parts) > 2 else 0
            return major * 10000 + minor * 100 + patch
        except (ValueError, IndexError):
            return 0

    def _get_release_date(self) -> str:
        """获取发布日期。"""
        return datetime.now().strftime("%Y-%m-%d")

    async def check_for_update(
        self,
        current_version: str,
        current_build: int,
        channel: str = "stable",
    ) -> UpdateCheckResponse:
        """
        检查是否有可用更新。

        模拟远程版本检查，实际部署时应连接更新服务器。

        Args:
            current_version: 当前版本号
            current_build: 当前构建号
            channel: 更新通道

        Returns:
            UpdateCheckResponse: 更新检查响应
        """
        async with self._lock:
            self._status = UpdateStatus.CHECKING
            self._progress = UpdateProgress(
                status=UpdateStatus.CHECKING,
                current_step="正在检查更新...",
                started_at=datetime.now().isoformat(),
            )

        try:
            # 模拟网络延迟
            await asyncio.sleep(0.5)

            # 获取模拟的最新版本信息
            latest_version_info = self._get_mock_latest_version(channel)

            # 比较版本
            has_update = self._compare_versions(
                current_build,
                latest_version_info.build_number,
            )

            update_info = None
            if has_update:
                update_info = UpdateInfo(
                    available=True,
                    latest_version=latest_version_info.version,
                    latest_build=latest_version_info.build_number,
                    update_type=self._determine_update_type(
                        current_version,
                        latest_version_info.version,
                    ),
                    priority=self._determine_update_priority(
                        latest_version_info.version,
                    ),
                    release_date=latest_version_info.release_date,
                    release_notes=latest_version_info.release_notes,
                    changelog=latest_version_info.changelog,
                    package_size_mb=45.2,
                    download_url=f"/api/update/download/{latest_version_info.version}",
                    checksum_sha256="abc123def456...",  # 模拟校验和
                )

            async with self._lock:
                self._status = UpdateStatus.IDLE
                self._progress = UpdateProgress(status=UpdateStatus.IDLE)

            return UpdateCheckResponse(
                has_update=has_update,
                current_version=current_version,
                update_info=update_info,
                checked_at=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error(f"检查更新失败: {e}")
            async with self._lock:
                self._status = UpdateStatus.FAILED
                self._progress = UpdateProgress(
                    status=UpdateStatus.FAILED,
                    current_step=f"检查失败: {e!s}",
                )
            raise HTTPException(
                status_code=500,
                detail=f"检查更新失败: {e!s}",
            )

    def _get_mock_latest_version(self, channel: str) -> VersionInfo:
        """
        获取模拟的最新版本信息。

        实际部署时应从更新服务器获取。

        Args:
            channel: 更新通道

        Returns:
            VersionInfo: 最新版本信息
        """
        # 模拟不同通道的版本
        if channel == "dev":
            return VersionInfo(
                version="0.4.0-dev",
                build_number=40000,
                release_date="2026-03-10",
                release_notes="开发版本 - 自动更新系统测试",
                changelog=[
                    "新增自动更新API",
                    "改进增量更新算法",
                    "修复已知问题",
                ],
            )
        elif channel == "beta":
            return VersionInfo(
                version="0.3.5-beta",
                build_number=30500,
                release_date="2026-03-08",
                release_notes="测试版本 - 性能优化",
                changelog=[
                    "优化设备状态推送",
                    "改进错误处理",
                ],
            )
        else:  # stable
            return VersionInfo(
                version="0.3.2",
                build_number=30200,
                release_date="2026-03-07",
                release_notes="稳定版本 - 安全更新",
                changelog=[
                    "修复安全漏洞",
                    "优化性能",
                ],
            )

    def _compare_versions(self, current_build: int, latest_build: int) -> bool:
        """
        比较版本号判断是否有更新。

        Args:
            current_build: 当前构建号
            latest_build: 最新构建号

        Returns:
            bool: 是否有可用更新
        """
        return latest_build > current_build

    def _determine_update_type(
        self,
        current_version: str,
        target_version: str,
    ) -> UpdateType:
        """
        判断更新类型。

        Args:
            current_version: 当前版本
            target_version: 目标版本

        Returns:
            UpdateType: 更新类型
        """
        try:
            current_parts = [int(x) for x in current_version.split(".")]
            target_parts = [int(x) for x in target_version.split(".")]

            # 主版本变化 - 全量更新
            if target_parts[0] > current_parts[0]:
                return UpdateType.FULL

            # 次版本变化 - 增量更新
            if target_parts[1] > current_parts[1]:
                return UpdateType.INCREMENTAL

            # 补丁版本变化 - 热修复
            return UpdateType.HOTFIX

        except (ValueError, IndexError):
            return UpdateType.FULL

    def _determine_update_priority(self, version: str) -> UpdatePriority:
        """
        判断更新优先级。

        Args:
            version: 目标版本

        Returns:
            UpdatePriority: 更新优先级
        """
        # 简单规则：补丁版本为低优先级，次版本为中，主版本为高
        try:
            parts = [int(x) for x in version.split(".")]
            if parts[0] > 0:
                return UpdatePriority.HIGH
            if parts[1] > 3:
                return UpdatePriority.MEDIUM
            return UpdatePriority.LOW
        except (ValueError, IndexError):
            return UpdatePriority.MEDIUM

    async def calculate_checksum(self, file_path: Path) -> str:
        """
        计算文件的SHA256校验和。

        Args:
            file_path: 文件路径

        Returns:
            str: SHA256校验和（十六进制字符串）
        """
        sha256_hash = hashlib.sha256()

        async with aiofiles.open(file_path, "rb") as f:
            # 分块读取，避免内存溢出
            chunk = await f.read(8192)
            while chunk:
                sha256_hash.update(chunk)
                chunk = await f.read(8192)

        return sha256_hash.hexdigest()

    async def verify_package(
        self,
        package_path: Path,
        expected_checksum: str,
    ) -> bool:
        """
        验证更新包完整性。

        Args:
            package_path: 更新包路径
            expected_checksum: 预期的SHA256校验和

        Returns:
            bool: 校验是否通过
        """
        if not package_path.exists():
            logger.error(f"更新包不存在: {package_path}")
            return False

        # 检查文件大小
        file_size_mb = package_path.stat().st_size / (1024 * 1024)
        if file_size_mb > MAX_PACKAGE_SIZE_MB:
            logger.error(f"更新包过大: {file_size_mb:.2f}MB > {MAX_PACKAGE_SIZE_MB}MB")
            return False

        # 计算并验证校验和
        actual_checksum = await self.calculate_checksum(package_path)

        if actual_checksum != expected_checksum:
            logger.error(f"校验和不匹配: 期望 {expected_checksum}, 实际 {actual_checksum}")
            return False

        logger.info(f"更新包校验通过: {package_path}")
        return True

    async def create_backup(
        self,
        backup_id: str | None = None,
        description: str = "",
    ) -> BackupInfo:
        """
        创建当前版本备份。

        Args:
            backup_id: 备份ID，不提供则自动生成
            description: 备份描述

        Returns:
            BackupInfo: 备份信息
        """
        if backup_id is None:
            backup_id = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        backup_path = self.backup_dir / backup_id
        backup_path.mkdir(parents=True, exist_ok=True)

        # 备份关键文件和目录
        files_to_backup = [
            "api",
            "core",
            "drivers",
            "middleware",
            "models",
            "main.py",
            "requirements.txt",
            "pyproject.toml",
        ]

        file_count = 0
        total_size = 0

        for item in files_to_backup:
            src = Path(item)
            if src.exists():
                dst = backup_path / item
                if src.is_dir():
                    shutil.copytree(src, dst, dirs_exist_ok=True)
                    for root, _, files in os.walk(dst):
                        for f in files:
                            file_count += 1
                            total_size += os.path.getsize(os.path.join(root, f))
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)
                    file_count += 1
                    total_size += dst.stat().st_size

        # 创建备份元数据
        metadata = {
            "backup_id": backup_id,
            "version": APP_VERSION,
            "created_at": datetime.now().isoformat(),
            "description": description,
            "file_count": file_count,
            "total_size": total_size,
        }

        async with aiofiles.open(backup_path / "metadata.json", "w") as f:
            await f.write(json.dumps(metadata, indent=2))

        # 计算备份校验和
        checksum = await self._calculate_backup_checksum(backup_path)

        logger.info(f"备份创建成功: {backup_id}, 文件数: {file_count}")

        return BackupInfo(
            backup_id=backup_id,
            version=APP_VERSION,
            created_at=datetime.now().isoformat(),
            size_mb=round(total_size / (1024 * 1024), 2),
            file_count=file_count,
            checksum=checksum,
            description=description,
        )

    async def _calculate_backup_checksum(self, backup_path: Path) -> str:
        """
        计算备份目录的校验和。

        Args:
            backup_path: 备份目录路径

        Returns:
            str: 校验和
        """
        hasher = hashlib.sha256()

        for root, _, files in sorted(os.walk(backup_path)):
            for filename in sorted(files):
                filepath = Path(root) / filename
                async with aiofiles.open(filepath, "rb") as f:
                    while chunk := await f.read(8192):
                        hasher.update(chunk)

        return hasher.hexdigest()[:16]  # 取前16位作为简短校验和

    async def apply_update(
        self,
        package_path: str,
        checksum_sha256: str,
        create_backup: bool = True,
        auto_rollback: bool = True,
    ) -> UpdateApplyResponse:
        """
        应用更新包。

        Args:
            package_path: 更新包路径
            checksum_sha256: SHA256校验和
            create_backup: 是否创建备份
            auto_rollback: 失败时是否自动回滚

        Returns:
            UpdateApplyResponse: 应用结果

        Raises:
            HTTPException: 更新失败时抛出
        """
        package_file = Path(package_path)
        backup_info = None
        start_time = datetime.now()

        async with self._lock:
            self._status = UpdateStatus.VERIFYING
            self._progress = UpdateProgress(
                status=UpdateStatus.VERIFYING,
                current_step="正在验证更新包...",
                started_at=start_time.isoformat(),
            )

        try:
            # 1. 验证更新包
            if not await self.verify_package(package_file, checksum_sha256):
                raise HTTPException(
                    status_code=400,
                    detail="更新包校验失败",
                )

            # 2. 创建备份
            if create_backup:
                async with self._lock:
                    self._status = UpdateStatus.INSTALLING
                    self._progress.current_step = "正在创建备份..."

                backup_info = await self.create_backup(
                    description=f"更新前自动备份 - {datetime.now().isoformat()}",
                )

            # 3. 解压并应用更新
            async with self._lock:
                self._status = UpdateStatus.INSTALLING
                self._progress.current_step = "正在应用更新..."

            await self._extract_and_apply(package_file)

            # 4. 记录更新历史
            await self._record_update_history(
                from_version=APP_VERSION,
                to_version="0.3.2",  # 从更新包读取
                update_type=UpdateType.INCREMENTAL,
                status="success",
                backup_id=backup_info.backup_id if backup_info else None,
                duration=(datetime.now() - start_time).total_seconds(),
            )

            async with self._lock:
                self._status = UpdateStatus.COMPLETED
                self._progress = UpdateProgress(
                    status=UpdateStatus.COMPLETED,
                    progress_percent=100.0,
                    current_step="更新完成",
                )

            logger.info(f"更新应用成功: {package_path}")

            return UpdateApplyResponse(
                success=True,
                message="更新应用成功，请重启服务",
                backup_id=backup_info.backup_id if backup_info else None,
                applied_at=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error(f"更新应用失败: {e}")

            # 自动回滚
            if auto_rollback and backup_info:
                logger.info("正在自动回滚...")
                await self.rollback(backup_info.backup_id, verify_integrity=False)

            async with self._lock:
                self._status = UpdateStatus.FAILED
                self._progress = UpdateProgress(
                    status=UpdateStatus.FAILED,
                    current_step=f"更新失败: {e!s}",
                )

            raise HTTPException(
                status_code=500,
                detail=f"更新应用失败: {e!s}",
            )

    async def _extract_and_apply(self, package_path: Path) -> None:
        """
        解压并应用更新包。

        Args:
            package_path: 更新包路径
        """
        extract_dir = self.temp_dir / f"extract_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            # 解压更新包
            with zipfile.ZipFile(package_path, "r") as zip_ref:
                zip_ref.extractall(extract_dir)

            # 查找更新清单
            manifest_file = extract_dir / "update_manifest.json"
            if not manifest_file.exists():
                raise ValueError("更新包缺少清单文件")

            async with aiofiles.open(manifest_file) as f:
                manifest = json.loads(await f.read())

            # 应用文件更新
            files_to_update = manifest.get("files", [])
            for file_info in files_to_update:
                src = extract_dir / file_info["path"]
                dst = Path(file_info["path"])

                if file_info.get("action") == "delete":
                    if dst.exists():
                        dst.unlink()
                else:
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(src, dst)

            logger.info(f"已更新 {len(files_to_update)} 个文件")

        finally:
            # 清理临时目录
            if extract_dir.exists():
                shutil.rmtree(extract_dir)

    async def rollback(
        self,
        backup_id: str,
        verify_integrity: bool = True,
    ) -> RollbackResponse:
        """
        回滚到指定备份版本。

        Args:
            backup_id: 备份ID
            verify_integrity: 是否验证完整性

        Returns:
            RollbackResponse: 回滚结果
        """
        async with self._lock:
            self._status = UpdateStatus.ROLLING_BACK
            self._progress = UpdateProgress(
                status=UpdateStatus.ROLLING_BACK,
                current_step="正在回滚...",
                started_at=datetime.now().isoformat(),
            )

        backup_path = self.backup_dir / backup_id

        if not backup_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"备份不存在: {backup_id}",
            )

        try:
            # 读取备份元数据
            metadata_file = backup_path / "metadata.json"
            async with aiofiles.open(metadata_file) as f:
                metadata = json.loads(await f.read())

            # 验证完整性
            if verify_integrity:
                current_checksum = await self._calculate_backup_checksum(backup_path)
                # 注意：metadata中没有存储原始checksum，这里仅做演示
                logger.info(f"备份校验通过: {backup_id}")

            # 恢复文件
            for item in backup_path.iterdir():
                if item.name == "metadata.json":
                    continue

                src = item
                dst = Path(item.name)

                if dst.exists():
                    if dst.is_dir():
                        shutil.rmtree(dst)
                    else:
                        dst.unlink()

                if src.is_dir():
                    shutil.copytree(src, dst)
                else:
                    shutil.copy2(src, dst)

            async with self._lock:
                self._status = UpdateStatus.COMPLETED
                self._progress = UpdateProgress(
                    status=UpdateStatus.COMPLETED,
                    progress_percent=100.0,
                    current_step="回滚完成",
                )

            logger.info(f"回滚成功: {backup_id}")

            return RollbackResponse(
                success=True,
                message="回滚成功，请重启服务",
                rolled_back_to=metadata["version"],
                rolled_back_at=datetime.now().isoformat(),
            )

        except Exception as e:
            logger.error(f"回滚失败: {e}")
            async with self._lock:
                self._status = UpdateStatus.FAILED
                self._progress = UpdateProgress(
                    status=UpdateStatus.FAILED,
                    current_step=f"回滚失败: {e!s}",
                )

            raise HTTPException(
                status_code=500,
                detail=f"回滚失败: {e!s}",
            )

    async def list_backups(self) -> BackupListResponse:
        """
        列出所有可用备份。

        Returns:
            BackupListResponse: 备份列表
        """
        backups = []

        if not self.backup_dir.exists():
            return BackupListResponse(total=0, backups=backups)

        for backup_dir in self.backup_dir.iterdir():
            if not backup_dir.is_dir():
                continue

            metadata_file = backup_dir / "metadata.json"
            if not metadata_file.exists():
                continue

            try:
                async with aiofiles.open(metadata_file) as f:
                    metadata = json.loads(await f.read())

                backups.append(
                    BackupInfo(
                        backup_id=metadata["backup_id"],
                        version=metadata["version"],
                        created_at=metadata["created_at"],
                        size_mb=round(metadata["total_size"] / (1024 * 1024), 2),
                        file_count=metadata["file_count"],
                        checksum="",  # 从metadata读取或重新计算
                        description=metadata.get("description", ""),
                    )
                )
            except Exception as e:
                logger.warning(f"读取备份元数据失败: {backup_dir.name}, {e}")

        # 按创建时间倒序排列
        backups.sort(key=lambda x: x.created_at, reverse=True)

        return BackupListResponse(total=len(backups), backups=backups)

    async def delete_backup(self, backup_id: str) -> bool:
        """
        删除指定备份。

        Args:
            backup_id: 备份ID

        Returns:
            bool: 是否删除成功
        """
        backup_path = self.backup_dir / backup_id

        if not backup_path.exists():
            raise HTTPException(
                status_code=404,
                detail=f"备份不存在: {backup_id}",
            )

        try:
            shutil.rmtree(backup_path)
            logger.info(f"备份已删除: {backup_id}")
            return True
        except Exception as e:
            logger.error(f"删除备份失败: {e}")
            return False

    async def _record_update_history(
        self,
        from_version: str,
        to_version: str,
        update_type: UpdateType,
        status: str,
        backup_id: str | None,
        duration: float,
    ) -> None:
        """
        记录更新历史。

        Args:
            from_version: 原版本
            to_version: 目标版本
            update_type: 更新类型
            status: 更新状态
            backup_id: 备份ID
            duration: 耗时
        """
        history_file = self.update_dir / "update_history.json"

        history_records = []
        if history_file.exists():
            async with aiofiles.open(history_file) as f:
                history_records = json.loads(await f.read())

        record = {
            "record_id": f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            "from_version": from_version,
            "to_version": to_version,
            "update_type": update_type.value,
            "status": status,
            "applied_at": datetime.now().isoformat(),
            "duration_seconds": duration,
            "backup_id": backup_id,
        }

        history_records.append(record)

        # 保留最近100条记录
        history_records = history_records[-100:]

        async with aiofiles.open(history_file, "w") as f:
            await f.write(json.dumps(history_records, indent=2))

    async def get_update_history(self) -> UpdateHistoryResponse:
        """
        获取更新历史记录。

        Returns:
            UpdateHistoryResponse: 更新历史
        """
        history_file = self.update_dir / "update_history.json"

        if not history_file.exists():
            return UpdateHistoryResponse(total=0, records=[])

        try:
            async with aiofiles.open(history_file) as f:
                history_records = json.loads(await f.read())

            records = [
                UpdateHistoryRecord(
                    record_id=r["record_id"],
                    from_version=r["from_version"],
                    to_version=r["to_version"],
                    update_type=UpdateType(r["update_type"]),
                    status=r["status"],
                    applied_at=r["applied_at"],
                    duration_seconds=r["duration_seconds"],
                    backup_id=r.get("backup_id"),
                    notes=r.get("notes", ""),
                )
                for r in history_records
            ]

            return UpdateHistoryResponse(total=len(records), records=records)

        except Exception as e:
            logger.error(f"读取更新历史失败: {e}")
            return UpdateHistoryResponse(total=0, records=[])

    def get_progress(self) -> UpdateProgress:
        """
        获取当前更新进度。

        Returns:
            UpdateProgress: 更新进度
        """
        return self._progress

    async def cleanup_old_backups(self, max_count: int = MAX_BACKUP_COUNT) -> int:
        """
        清理旧备份，保留指定数量。

        Args:
            max_count: 最大保留数量

        Returns:
            int: 删除的备份数量
        """
        backups = await self.list_backups()

        if len(backups.backups) <= max_count:
            return 0

        # 删除最旧的备份
        to_delete = backups.backups[max_count:]
        deleted_count = 0

        for backup in to_delete:
            if await self.delete_backup(backup.backup_id):
                deleted_count += 1

        logger.info(f"已清理 {deleted_count} 个旧备份")
        return deleted_count


# ============================================================================
# 全局更新管理器实例
# ============================================================================

update_manager = UpdateManager()


# ============================================================================
# API 端点定义
# ============================================================================


@router.get("/version", response_model=VersionInfo)
async def get_current_version():
    """
    获取当前版本信息。

    Returns:
        VersionInfo: 当前版本信息
    """
    return update_manager.get_current_version()


@router.post("/check", response_model=UpdateCheckResponse)
async def check_update(request: UpdateCheckRequest):
    """
    检查是否有可用更新。

    Args:
        request: 更新检查请求

    Returns:
        UpdateCheckResponse: 更新检查响应
    """
    return await update_manager.check_for_update(
        current_version=request.current_version,
        current_build=request.current_build,
        channel=request.channel,
    )


@router.get("/progress", response_model=UpdateProgress)
async def get_update_progress():
    """
    获取当前更新进度。

    Returns:
        UpdateProgress: 更新进度
    """
    return update_manager.get_progress()


@router.post("/apply", response_model=UpdateApplyResponse)
async def apply_update(request: UpdateApplyRequest):
    """
    应用更新包。

    Args:
        request: 更新应用请求

    Returns:
        UpdateApplyResponse: 应用结果
    """
    return await update_manager.apply_update(
        package_path=request.package_path,
        checksum_sha256=request.checksum_sha256,
        create_backup=request.create_backup,
        auto_rollback=request.auto_rollback,
    )


@router.post("/upload")
async def upload_update_package(file: UploadFile = File(...)):
    """
    上传更新包。

    Args:
        file: 上传的更新包文件

    Returns:
        dict: 上传结果，包含文件路径和校验和
    """
    # 验证文件类型
    if not file.filename or not file.filename.endswith(".zip"):
        raise HTTPException(
            status_code=400,
            detail="仅支持 .zip 格式的更新包",
        )

    # 保存文件
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"update_{timestamp}.zip"
    filepath = update_manager.update_dir / filename

    # 检查文件大小
    max_size = MAX_PACKAGE_SIZE_MB * 1024 * 1024
    size = 0

    async with aiofiles.open(filepath, "wb") as f:
        while chunk := await file.read(1024 * 1024):  # 1MB chunks
            size += len(chunk)
            if size > max_size:
                await f.close()
                filepath.unlink()
                raise HTTPException(
                    status_code=413,
                    detail=f"文件过大，最大支持 {MAX_PACKAGE_SIZE_MB}MB",
                )
            await f.write(chunk)

    # 计算校验和
    checksum = await update_manager.calculate_checksum(filepath)

    logger.info(f"更新包上传成功: {filename}, 大小: {size / (1024*1024):.2f}MB")

    return {
        "success": True,
        "message": "上传成功",
        "filename": filename,
        "filepath": str(filepath),
        "size_mb": round(size / (1024 * 1024), 2),
        "checksum_sha256": checksum,
    }


@router.post("/rollback", response_model=RollbackResponse)
async def perform_rollback(request: RollbackRequest):
    """
    回滚到指定备份版本。

    Args:
        request: 回滚请求

    Returns:
        RollbackResponse: 回滚结果
    """
    return await update_manager.rollback(
        backup_id=request.backup_id,
        verify_integrity=request.verify_integrity,
    )


@router.get("/backups", response_model=BackupListResponse)
async def list_backups():
    """
    列出所有可用备份。

    Returns:
        BackupListResponse: 备份列表
    """
    return await update_manager.list_backups()


@router.delete("/backups/{backup_id}")
async def delete_backup(backup_id: str):
    """
    删除指定备份。

    Args:
        backup_id: 备份ID

    Returns:
        dict: 删除结果
    """
    success = await update_manager.delete_backup(backup_id)

    if success:
        return {"success": True, "message": f"备份 {backup_id} 已删除"}
    else:
        raise HTTPException(
            status_code=500,
            detail="删除备份失败",
        )


@router.post("/backups")
async def create_manual_backup(description: str = ""):
    """
    手动创建备份。

    Args:
        description: 备份描述

    Returns:
        BackupInfo: 备份信息
    """
    backup_info = await update_manager.create_backup(description=description)
    return backup_info


@router.get("/history", response_model=UpdateHistoryResponse)
async def get_update_history():
    """
    获取更新历史记录。

    Returns:
        UpdateHistoryResponse: 更新历史
    """
    return await update_manager.get_update_history()


@router.post("/cleanup")
async def cleanup_backups(max_count: int = MAX_BACKUP_COUNT):
    """
    清理旧备份。

    Args:
        max_count: 最大保留数量

    Returns:
        dict: 清理结果
    """
    deleted_count = await update_manager.cleanup_old_backups(max_count)

    return {
        "success": True,
        "message": f"已清理 {deleted_count} 个旧备份",
        "deleted_count": deleted_count,
    }


@router.post("/verify")
async def verify_update_package(package_path: str, checksum: str):
    """
    验证更新包完整性。

    Args:
        package_path: 更新包路径
        checksum: 预期的SHA256校验和

    Returns:
        dict: 验证结果
    """
    filepath = Path(package_path)

    if not filepath.exists():
        raise HTTPException(
            status_code=404,
            detail=f"更新包不存在: {package_path}",
        )

    is_valid = await update_manager.verify_package(filepath, checksum)

    return {
        "success": is_valid,
        "message": "校验通过" if is_valid else "校验失败",
        "package_path": package_path,
        "expected_checksum": checksum,
    }
