"""
崩溃报告上传机制模块。

实现崩溃报告的远程上传功能，支持将崩溃报告上传到远程服务器进行分析。

功能：
    - 崩溃报告上传到远程服务器
    - 上传失败重试机制
    - 上传队列管理
    - 上传状态跟踪

技术栈：
    - Python 3.11+
    - httpx 异步HTTP客户端

作者：Backend Engineer Agent
创建日期：2026-03-07
依赖：httpx, asyncio
"""

import asyncio
import gzip
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


# ============================================================================
# 上传状态枚举
# ============================================================================


class UploadStatus(str, Enum):
    """上传状态枚举。"""

    PENDING = "pending"  # 待上传
    UPLOADING = "uploading"  # 上传中
    SUCCESS = "success"  # 上传成功
    FAILED = "failed"  # 上传失败
    CANCELLED = "cancelled"  # 已取消


# ============================================================================
# 上传配置
# ============================================================================


@dataclass
class UploadConfig:
    """上传配置。

    Attributes:
        enabled: 是否启用上传
        server_url: 远程服务器URL
        api_key: API密钥
        timeout_seconds: 请求超时时间（秒）
        max_retries: 最大重试次数
        retry_delay_seconds: 重试延迟时间（秒）
        batch_size: 批量上传数量
        compress: 是否压缩上传
        include_system_info: 是否包含系统信息
        include_traceback: 是否包含异常堆栈
    """

    enabled: bool = False
    server_url: str = ""
    api_key: str = ""
    timeout_seconds: int = 30
    max_retries: int = 3
    retry_delay_seconds: int = 5
    batch_size: int = 10
    compress: bool = True
    include_system_info: bool = True
    include_traceback: bool = True


# ============================================================================
# 上传记录
# ============================================================================


@dataclass
class UploadRecord:
    """上传记录。

    Attributes:
        report_id: 报告ID
        status: 上传状态
        attempts: 尝试次数
        last_attempt_time: 最后尝试时间
        last_error: 最后错误信息
        server_response: 服务器响应
        uploaded_at: 上传成功时间
    """

    report_id: str
    status: UploadStatus = UploadStatus.PENDING
    attempts: int = 0
    last_attempt_time: datetime | None = None
    last_error: str | None = None
    server_response: dict[str, Any] | None = None
    uploaded_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """转换为字典格式。

        Returns:
            dict: 上传记录字典
        """
        return {
            "report_id": self.report_id,
            "status": self.status.value,
            "attempts": self.attempts,
            "last_attempt_time": (
                self.last_attempt_time.isoformat() if self.last_attempt_time else None
            ),
            "last_error": self.last_error,
            "server_response": self.server_response,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
        }


# ============================================================================
# 上传管理器
# ============================================================================


class CrashReportUploader:
    """崩溃报告上传管理器。

    管理崩溃报告的上传队列和上传过程。

    Example:
        >>> config = UploadConfig(
        ...     enabled=True,
        ...     server_url="https://crash-reports.example.com/api/upload",
        ...     api_key="your-api-key",
        ... )
        >>> uploader = CrashReportUploader(config)
        >>> await uploader.start()
        >>> await uploader.queue_report(report_id, report_data)
    """

    def __init__(self, config: UploadConfig):
        """初始化上传管理器。

        Args:
            config: 上传配置
        """
        self.config = config
        self._upload_queue: asyncio.Queue = asyncio.Queue()
        self._upload_records: dict[str, UploadRecord] = {}
        self._running = False
        self._upload_task: asyncio.Task | None = None

        logger.info(f"[CrashUploader] Initialized (enabled={config.enabled})")

    async def start(self) -> None:
        """启动上传管理器。

        开始处理上传队列。
        """
        if not self.config.enabled:
            logger.info("[CrashUploader] Upload disabled, not starting")
            return

        if self._running:
            logger.warning("[CrashUploader] Already running")
            return

        self._running = True
        self._upload_task = asyncio.create_task(self._process_queue())

        logger.info("[CrashUploader] Started")

    async def stop(self) -> None:
        """停止上传管理器。

        等待当前上传完成后停止。
        """
        if not self._running:
            return

        self._running = False

        # 等待队列处理完成
        if self._upload_task:
            try:
                await asyncio.wait_for(self._upload_task, timeout=10.0)
            except TimeoutError:
                self._upload_task.cancel()

        logger.info("[CrashUploader] Stopped")

    async def queue_report(
        self,
        report_id: str,
        report_data: dict[str, Any],
    ) -> bool:
        """将崩溃报告加入上传队列。

        Args:
            report_id: 报告ID
            report_data: 报告数据

        Returns:
            bool: 是否成功加入队列
        """
        if not self.config.enabled:
            logger.debug(f"[CrashUploader] Upload disabled, skipping report: {report_id}")
            return False

        # 创建上传记录
        record = UploadRecord(report_id=report_id)
        self._upload_records[report_id] = record

        # 加入队列
        await self._upload_queue.put(
            {
                "report_id": report_id,
                "report_data": report_data,
            }
        )

        logger.info(f"[CrashUploader] Queued report: {report_id}")
        return True

    async def _process_queue(self) -> None:
        """处理上传队列。

        从队列中取出报告并上传。
        """
        while self._running:
            try:
                # 非阻塞获取队列项
                try:
                    item = await asyncio.wait_for(self._upload_queue.get(), timeout=1.0)
                except TimeoutError:
                    continue

                # 上传报告
                await self._upload_report(
                    report_id=item["report_id"],
                    report_data=item["report_data"],
                )

            except Exception as e:
                logger.error(f"[CrashUploader] Queue processing error: {e}")
                await asyncio.sleep(1.0)

    async def _upload_report(
        self,
        report_id: str,
        report_data: dict[str, Any],
    ) -> bool:
        """上传单个崩溃报告。

        Args:
            report_id: 报告ID
            report_data: 报告数据

        Returns:
            bool: 是否上传成功
        """
        record = self._upload_records.get(report_id)
        if not record:
            logger.error(f"[CrashUploader] No upload record found: {report_id}")
            return False

        # 更新状态
        record.status = UploadStatus.UPLOADING
        record.attempts += 1
        record.last_attempt_time = datetime.now()

        try:
            # 准备上传数据
            upload_data = self._prepare_upload_data(report_data)

            # 执行上传（带重试）
            response = await self._do_upload_with_retry(upload_data)

            # 更新成功状态
            record.status = UploadStatus.SUCCESS
            record.server_response = response
            record.uploaded_at = datetime.now()

            logger.info(f"[CrashUploader] Upload success: {report_id}")
            return True

        except Exception as e:
            # 更新失败状态
            record.status = UploadStatus.FAILED
            record.last_error = str(e)

            logger.error(f"[CrashUploader] Upload failed: {report_id} - {e}")
            return False

    def _prepare_upload_data(self, report_data: dict[str, Any]) -> dict[str, Any]:
        """准备上传数据。

        根据配置过滤敏感信息。

        Args:
            report_data: 原始报告数据

        Returns:
            dict: 准备上传的数据
        """
        upload_data = {
            "report_id": report_data.get("report_id"),
            "timestamp": report_data.get("timestamp"),
            "severity": report_data.get("severity"),
            "exception_type": report_data.get("exception_type"),
            "exception_message": report_data.get("exception_message"),
            "exception_module": report_data.get("exception_module"),
            "exception_function": report_data.get("exception_function"),
            "exception_line": report_data.get("exception_line"),
            "device_id": report_data.get("device_id"),
            "experiment_id": report_data.get("experiment_id"),
            "user_id": report_data.get("user_id"),
            "tags": report_data.get("tags", []),
        }

        # 可选：包含系统信息
        if self.config.include_system_info:
            upload_data["system_info"] = report_data.get("system_info", {})

        # 可选：包含异常堆栈
        if self.config.include_traceback:
            upload_data["exception_traceback"] = report_data.get("exception_traceback")

        # 可选：包含上下文数据
        upload_data["context_data"] = report_data.get("context_data", {})

        return upload_data

    async def _do_upload_with_retry(self, data: dict[str, Any]) -> dict[str, Any]:
        """执行上传（带重试机制）。

        Args:
            data: 上传数据

        Returns:
            dict: 服务器响应

        Raises:
            Exception: 上传失败时抛出异常
        """
        import httpx

        last_error = None

        for attempt in range(self.config.max_retries):
            try:
                # 准备请求
                headers = {
                    "Authorization": f"Bearer {self.config.api_key}",
                    "Content-Type": "application/json",
                }

                # 压缩数据（可选）
                if self.config.compress:
                    content = gzip.compress(json.dumps(data, ensure_ascii=False).encode("utf-8"))
                    headers["Content-Encoding"] = "gzip"
                else:
                    content = json.dumps(data, ensure_ascii=False).encode("utf-8")

                # 发送请求
                async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                    response = await client.post(
                        self.config.server_url,
                        content=content,
                        headers=headers,
                    )

                    # 检查响应
                    if response.status_code == 200:
                        return response.json()
                    else:
                        raise Exception(
                            f"Server returned status {response.status_code}: {response.text}"
                        )

            except Exception as e:
                last_error = e
                logger.warning(f"[CrashUploader] Upload attempt {attempt + 1} failed: {e}")

                # 延迟后重试
                if attempt < self.config.max_retries - 1:
                    await asyncio.sleep(self.config.retry_delay_seconds)

        raise last_error or Exception("Upload failed after retries")

    def get_upload_status(self, report_id: str) -> dict[str, Any] | None:
        """获取上传状态。

        Args:
            report_id: 报告ID

        Returns:
            Optional[dict]: 上传状态，不存在时返回None
        """
        record = self._upload_records.get(report_id)
        if record:
            return record.to_dict()
        return None

    def get_pending_count(self) -> int:
        """获取待上传数量。

        Returns:
            int: 待上传数量
        """
        return self._upload_queue.qsize()

    def get_statistics(self) -> dict[str, Any]:
        """获取上传统计信息。

        Returns:
            dict: 统计信息
        """
        total = len(self._upload_records)
        by_status: dict[str, int] = {}

        for record in self._upload_records.values():
            status = record.status.value
            by_status[status] = by_status.get(status, 0) + 1

        return {
            "total_reports": total,
            "pending_count": self.get_pending_count(),
            "by_status": by_status,
            "config": {
                "enabled": self.config.enabled,
                "server_url": self.config.server_url,
                "max_retries": self.config.max_retries,
            },
        }


# ============================================================================
# 全局实例
# ============================================================================

# 全局上传管理器实例
_crash_uploader: CrashReportUploader | None = None


def init_crash_uploader(config: UploadConfig) -> CrashReportUploader:
    """初始化全局崩溃报告上传管理器。

    Args:
        config: 上传配置

    Returns:
        CrashReportUploader: 上传管理器实例

    Example:
        >>> config = UploadConfig(
        ...     enabled=True,
        ...     server_url="https://crash-reports.example.com/api/upload",
        ...     api_key="your-api-key",
        ... )
        >>> uploader = init_crash_uploader(config)
    """
    global _crash_uploader

    _crash_uploader = CrashReportUploader(config)
    logger.info("[CrashUploader] Global uploader initialized")
    return _crash_uploader


def get_crash_uploader() -> CrashReportUploader | None:
    """获取全局崩溃报告上传管理器实例。

    Returns:
        Optional[CrashReportUploader]: 上传管理器实例
    """
    return _crash_uploader


# ============================================================================
# 便捷函数
# ============================================================================


async def upload_crash_report(
    report_id: str,
    report_data: dict[str, Any],
) -> bool:
    """上传崩溃报告（便捷函数）。

    Args:
        report_id: 报告ID
        report_data: 报告数据

    Returns:
        bool: 是否成功加入上传队列
    """
    uploader = get_crash_uploader()
    if not uploader:
        logger.warning("[CrashUploader] No uploader initialized")
        return False

    return await uploader.queue_report(report_id, report_data)
