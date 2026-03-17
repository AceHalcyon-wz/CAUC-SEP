"""
文件上传验证模块

文件名: upload.py
路径: backend/api/
功能: 文件上传处理与验证，防止恶意文件上传
作者: Backend Engineer Agent
创建日期: 2026-03-16
依赖: fastapi, pydantic, hashlib

安全特性：
- 文件类型白名单验证
- 文件大小限制（10MB）
- 文件名安全处理（防止路径遍历）
- 文件内容校验和计算
- 防止文件覆盖

支持的文件类型：
- PDF (application/pdf)
- JSON (application/json)
- CSV (text/csv, application/vnd.ms-excel)

注意事项：
- 上传的文件存储在临时目录
- 生产环境应配置专用存储路径
- 需要定期清理过期上传文件
"""

import hashlib
import logging
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/upload", tags=["upload"])

# 允许的文件类型映射（MIME类型 -> 扩展名）
ALLOWED_EXTENSIONS: dict[str, str] = {
    "application/pdf": ".pdf",
    "application/json": ".json",
    "text/csv": ".csv",
    "application/vnd.ms-excel": ".csv",  # Excel 有时使用此 MIME 类型
}

# 最大文件大小 (10MB)
MAX_FILE_SIZE: int = 10 * 1024 * 1024

# 允许的文件扩展名（用于双重验证）
ALLOWED_FILE_EXTENSIONS: set[str] = {".pdf", ".json", ".csv"}

# 危险文件扩展名（禁止上传）
DANGEROUS_EXTENSIONS: set[str] = {
    ".exe", ".bat", ".cmd", ".com", ".pif", ".scr", ".vbs", ".js",
    ".jar", ".msi", ".dll", ".sh", ".bash", ".ps1", ".psm1",
    ".php", ".asp", ".aspx", ".jsp", ".py", ".pl", ".rb",
}


class UploadResponse(BaseModel):
    """
    上传响应模型。

    Attributes:
        success: 上传是否成功
        filename: 保存的文件名
        size: 文件大小（字节）
        checksum: 文件 SHA256 校验和（前16位）
        message: 响应消息
    """

    success: bool = Field(..., description="上传是否成功")
    filename: str = Field(..., description="保存的文件名")
    size: int = Field(..., ge=0, description="文件大小（字节）")
    checksum: str = Field(..., description="文件 SHA256 校验和（前16位）")
    message: str = Field(default="", description="响应消息")


class UploadError(BaseModel):
    """
    上传错误响应模型。

    Attributes:
        success: 固定为 False
        error: 错误类型
        detail: 错误详情
    """

    success: bool = Field(False, description="固定为 False")
    error: str = Field(..., description="错误类型")
    detail: str = Field(..., description="错误详情")


def get_upload_directory() -> Path:
    """
    获取上传目录路径。

    Returns:
        Path: 上传目录的绝对路径

    Note:
        如果目录不存在会自动创建
    """
    upload_dir = Path(tempfile.gettempdir()) / "cauc-sep-uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


def validate_upload_file(file: UploadFile) -> Path:
    """
    验证上传文件。

    执行完整的文件安全验证，包括文件名、类型和扩展名检查。

    Args:
        file: 上传的文件对象

    Returns:
        Path: 安全的文件名（仅文件名，不含路径）

    Raises:
        HTTPException: 验证失败时抛出 400 错误

    Security:
        - 检查文件名是否为空
        - 移除路径组件（防止路径遍历）
        - 检查危险扩展名
        - 验证 MIME 类型白名单
        - 验证扩展名与 MIME 类型匹配

    Example:
        >>> safe_name = validate_upload_file(upload_file)
        >>> print(safe_name)  # "document.pdf"
    """
    # 检查文件名
    if not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能为空",
        )

    # 提取纯文件名（移除路径组件，防止路径遍历）
    filename = Path(file.filename).name

    # 检查文件名安全性
    if ".." in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名包含非法字符 '..'",
        )

    if filename.startswith("."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件名不能以点开头",
        )

    # 检查文件扩展名是否在危险列表中
    file_ext = Path(filename).suffix.lower()
    if file_ext in DANGEROUS_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"禁止上传的文件类型: {file_ext}",
        )

    # 检查文件 MIME 类型
    content_type = file.content_type or "application/octet-stream"
    if content_type not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型: {content_type}",
        )

    # 检查扩展名是否与 MIME 类型匹配
    expected_ext = ALLOWED_EXTENSIONS[content_type]
    if not filename.lower().endswith(expected_ext):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件扩展名不匹配，应为 {expected_ext}",
        )

    return Path(filename)


@router.post("/", response_model=UploadResponse)
async def upload_file(
    file: Annotated[UploadFile, File(description="上传的文件")],
) -> UploadResponse:
    """
    上传文件。

    接收并保存上传的文件，执行完整的安全验证。

    Args:
        file: 上传的文件对象

    Returns:
        UploadResponse: 上传结果，包含文件名、大小和校验和

    Raises:
        HTTPException: 验证失败或保存失败时抛出

    Security:
        - 文件类型白名单验证
        - 文件大小限制 (10MB)
        - 文件名安全处理
        - 防止路径遍历攻击
        - 防止文件覆盖

    Supported Types:
        - PDF: application/pdf
        - JSON: application/json
        - CSV: text/csv

    Example:
        POST /api/v1/upload/
        Content-Type: multipart/form-data

        file: <binary data>
    """
    # 验证文件
    safe_filename = validate_upload_file(file)

    # 读取内容并验证大小
    content = await file.read()

    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"文件大小超过限制 ({MAX_FILE_SIZE // 1024 // 1024}MB)",
        )

    # 检查文件是否为空
    if len(content) == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件内容为空",
        )

    # 计算校验和（SHA256 前16位）
    checksum = hashlib.sha256(content).hexdigest()[:16]

    # 获取上传目录
    upload_dir = get_upload_directory()

    # 生成安全文件名（使用校验和前缀防止冲突）
    safe_name = f"{checksum}_{safe_filename.name}"
    save_path = upload_dir / safe_name

    # 防止覆盖：如果文件已存在，添加计数器
    counter = 0
    while save_path.exists():
        counter += 1
        safe_name = f"{checksum}_{counter}_{safe_filename.name}"
        save_path = upload_dir / safe_name

    # 保存文件
    try:
        save_path.write_bytes(content)
        logger.info(f"File uploaded: {safe_name} ({len(content)} bytes)")
    except OSError as e:
        logger.error(f"Failed to save uploaded file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件保存失败",
        )

    return UploadResponse(
        success=True,
        filename=safe_name,
        size=len(content),
        checksum=checksum,
        message="文件上传成功",
    )


@router.get("/types")
async def get_allowed_file_types() -> dict[str, list[str] | int]:
    """
    获取允许上传的文件类型列表。

    Returns:
        dict: 包含允许的 MIME 类型和扩展名列表

    Example:
        GET /api/v1/upload/types

        Response:
        {
            "mime_types": ["application/pdf", "application/json", ...],
            "extensions": [".pdf", ".json", ".csv"],
            "max_size_bytes": 10485760,
            "max_size_mb": 10
        }
    """
    return {
        "mime_types": list(ALLOWED_EXTENSIONS.keys()),
        "extensions": list(ALLOWED_FILE_EXTENSIONS),
        "max_size_bytes": MAX_FILE_SIZE,
        "max_size_mb": MAX_FILE_SIZE // 1024 // 1024,
    }


@router.delete("/{filename}")
async def delete_uploaded_file(filename: str) -> dict[str, str]:
    """
    删除上传的文件。

    Args:
        filename: 要删除的文件名

    Returns:
        dict: 删除结果

    Raises:
        HTTPException: 文件不存在或删除失败时抛出

    Security:
        - 只能删除上传目录中的文件
        - 防止路径遍历攻击
    """
    # 安全检查：防止路径遍历
    if ".." in filename or "/" in filename or "\\" in filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="无效的文件名",
        )

    # 构建文件路径
    upload_dir = get_upload_directory()
    file_path = upload_dir / filename

    # 检查文件是否在上传目录内（防止目录遍历）
    try:
        file_path.resolve().relative_to(upload_dir.resolve())
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="文件路径无效",
        )

    # 检查文件是否存在
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="文件不存在",
        )

    # 检查是否为文件（不是目录）
    if not file_path.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="路径不是文件",
        )

    # 删除文件
    try:
        file_path.unlink()
        logger.info(f"File deleted: {filename}")
    except OSError as e:
        logger.error(f"Failed to delete file: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="文件删除失败",
        )

    return {
        "success": "true",
        "message": f"文件 {filename} 已删除",
    }
