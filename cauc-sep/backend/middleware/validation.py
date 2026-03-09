"""
请求参数验证工具模块

功能：
- XSS（跨站脚本攻击）过滤
- SQL注入防护
- 输入参数验证
- 敏感数据检测
- 文件名安全处理

安全特性：
- 防止XSS攻击
- 防止SQL注入
- 防止路径遍历
- 防止命令注入
- 数据脱敏

作者: Backend Engineer Agent
创建日期: 2026-03-08
依赖: re, html
"""

import html
import logging
import re
from dataclasses import dataclass
from typing import Any

logger = logging.getLogger(__name__)


# ==================== XSS过滤 ====================


# 危险HTML标签
DANGEROUS_TAGS = {
    "script", "iframe", "object", "embed", "applet",
    "meta", "link", "style", "base", "form",
}

# 危险属性
DANGEROUS_ATTRIBUTES = {
    "onload", "onerror", "onclick", "onmouseover", "onmouseout",
    "onkeydown", "onkeyup", "onkeypress", "onfocus", "onblur",
    "onsubmit", "onreset", "onchange", "oninput", "onselect",
    "ondrag", "ondrop", "onscroll", "onwheel",
    "formaction", "action", "srcdoc", "xlink:href",
}

# XSS攻击模式
XSS_PATTERNS = [
    # JavaScript协议
    re.compile(r"javascript\s*:", re.IGNORECASE),
    re.compile(r"vbscript\s*:", re.IGNORECASE),
    re.compile(r"data\s*:\s*text/html", re.IGNORECASE),
    # 事件处理器
    re.compile(r"on\w+\s*=", re.IGNORECASE),
    # HTML实体编码绕过
    re.compile(r"&#x?[0-9a-f]+;?", re.IGNORECASE),
    # SVG/HTML注入
    re.compile(r"<\s*svg", re.IGNORECASE),
    re.compile(r"<\s*img[^>]+src\s*=", re.IGNORECASE),
    # 表达式注入
    re.compile(r"expression\s*\(", re.IGNORECASE),
    # URL编码绕过
    re.compile(r"%3c\s*script", re.IGNORECASE),
    re.compile(r"%3c\s*img", re.IGNORECASE),
]


@dataclass
class ValidationResult:
    """
    验证结果。
    
    Attributes:
        is_valid: 是否有效
        sanitized_value: 清理后的值
        warnings: 警告信息列表
        errors: 错误信息列表
    """
    
    is_valid: bool
    sanitized_value: Any
    warnings: list[str] = None
    errors: list[str] = None
    
    def __post_init__(self):
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []


def sanitize_html(text: str, allow_basic_formatting: bool = False) -> str:
    """
    清理HTML内容，移除危险标签和属性。
    
    Args:
        text: 原始文本
        allow_basic_formatting: 是否允许基本格式标签
    
    Returns:
        str: 清理后的安全文本
    """
    if not text or not isinstance(text, str):
        return ""
    
    # HTML实体编码
    sanitized = html.escape(text)
    
    if allow_basic_formatting:
        # 允许基本格式标签：b, i, u, strong, em, br, p
        allowed_tags = ["b", "i", "u", "strong", "em", "br", "p"]
        for tag in allowed_tags:
            # 恢复允许的标签
            sanitized = sanitized.replace(f"&lt;{tag}&gt;", f"<{tag}>")
            sanitized = sanitized.replace(f"&lt;/{tag}&gt;", f"</{tag}>")
    
    return sanitized


def strip_xss(text: str) -> str:
    """
    移除XSS攻击向量。
    
    Args:
        text: 原始文本
    
    Returns:
        str: 清理后的安全文本
    """
    if not text or not isinstance(text, str):
        return ""
    
    sanitized = text
    
    # 移除危险标签
    for tag in DANGEROUS_TAGS:
        # 移除完整标签
        sanitized = re.sub(
            rf"<\s*{tag}[^>]*>.*?</\s*{tag}\s*>",
            "",
            sanitized,
            flags=re.IGNORECASE | re.DOTALL,
        )
        # 移除自闭合标签
        sanitized = re.sub(
            rf"<\s*{tag}[^>]*/?\s*>",
            "",
            sanitized,
            flags=re.IGNORECASE,
        )
    
    # 移除危险属性
    for attr in DANGEROUS_ATTRIBUTES:
        sanitized = re.sub(
            rf'{attr}\s*=\s*["\'][^"\']*["\']',
            "",
            sanitized,
            flags=re.IGNORECASE,
        )
        sanitized = re.sub(
            rf'{attr}\s*=\s*[^\s>]+',
            "",
            sanitized,
            flags=re.IGNORECASE,
        )
    
    # 移除XSS攻击模式
    for pattern in XSS_PATTERNS:
        sanitized = pattern.sub("", sanitized)
    
    return sanitized


def sanitize_input(
    text: str,
    max_length: int = 10000,
    allow_html: bool = False,
    strip_dangerous_chars: bool = True,
) -> ValidationResult:
    """
    清理输入文本。
    
    Args:
        text: 原始文本
        max_length: 最大长度
        allow_html: 是否允许HTML
        strip_dangerous_chars: 是否移除危险字符
    
    Returns:
        ValidationResult: 验证结果
    """
    warnings = []
    errors = []
    
    if not text:
        return ValidationResult(is_valid=True, sanitized_value="")
    
    if not isinstance(text, str):
        return ValidationResult(
            is_valid=False,
            sanitized_value="",
            errors=["输入必须是字符串类型"],
        )
    
    # 长度检查
    if len(text) > max_length:
        warnings.append(f"输入长度超过限制({max_length})，已截断")
        text = text[:max_length]
    
    # XSS清理
    if allow_html:
        sanitized = sanitize_html(text, allow_basic_formatting=True)
    else:
        sanitized = strip_xss(text)
    
    # 移除危险字符
    if strip_dangerous_chars:
        # 移除控制字符（保留换行和制表符）
        sanitized = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]", "", sanitized)
    
    # 检测是否包含潜在危险内容
    detected_patterns = []
    for pattern in XSS_PATTERNS:
        if pattern.search(text):
            detected_patterns.append(pattern.pattern)
    
    if detected_patterns:
        warnings.append(f"检测到潜在危险内容，已清理")
        logger.warning(f"XSS pattern detected in input: {detected_patterns}")
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=sanitized,
        warnings=warnings,
        errors=errors,
    )


# ==================== SQL注入防护 ====================


# SQL注入危险模式
SQL_INJECTION_PATTERNS = [
    # SQL注释
    re.compile(r"--\s*$", re.IGNORECASE),
    re.compile(r"#\s*$", re.IGNORECASE),
    re.compile(r"/\*.*\*/", re.IGNORECASE | re.DOTALL),
    # SQL关键字组合
    re.compile(r"\b(union\s+select|select\s+.*\s+from|insert\s+into|delete\s+from|drop\s+table|truncate\s+table)\b", re.IGNORECASE),
    # SQL函数
    re.compile(r"\b(exec|execute|xp_cmdshell|sp_executesql)\s*\(", re.IGNORECASE),
    # 布尔注入
    re.compile(r"\b(or|and)\s+['\"]?\d+['\"]?\s*=\s*['\"]?\d+", re.IGNORECASE),
    re.compile(r"\b(or|and)\s+['\"]?[\w]+['\"]?\s*=\s*['\"]?[\w]+['\"]?", re.IGNORECASE),
    # 时间盲注
    re.compile(r"\b(waitfor\s+delay|sleep\s*\(|benchmark\s*\()", re.IGNORECASE),
    # 堆叠查询
    re.compile(r";\s*(select|insert|update|delete|drop|create|alter)", re.IGNORECASE),
]

# SQL关键字（用于检测）
SQL_KEYWORDS = {
    "select", "insert", "update", "delete", "drop", "create", "alter",
    "truncate", "union", "join", "where", "from", "into", "values",
    "exec", "execute", "xp_", "sp_", "declare", "cast", "convert",
}


def detect_sql_injection(text: str) -> tuple[bool, list[str]]:
    """
    检测SQL注入攻击。
    
    Args:
        text: 待检测文本
    
    Returns:
        tuple[bool, list[str]]: 是否检测到注入、匹配的模式列表
    """
    if not text or not isinstance(text, str):
        return False, []
    
    detected_patterns = []
    
    for pattern in SQL_INJECTION_PATTERNS:
        if pattern.search(text):
            detected_patterns.append(pattern.pattern)
    
    return len(detected_patterns) > 0, detected_patterns


def sanitize_sql_input(text: str) -> ValidationResult:
    """
    清理SQL输入，防止注入攻击。
    
    注意：此函数仅作为辅助防护，主要防护应使用参数化查询。
    
    Args:
        text: 原始文本
    
    Returns:
        ValidationResult: 验证结果
    """
    warnings = []
    errors = []
    
    if not text:
        return ValidationResult(is_valid=True, sanitized_value="")
    
    if not isinstance(text, str):
        return ValidationResult(
            is_valid=False,
            sanitized_value="",
            errors=["输入必须是字符串类型"],
        )
    
    # 检测SQL注入
    is_injection, patterns = detect_sql_injection(text)
    
    if is_injection:
        errors.append("检测到潜在的SQL注入攻击")
        logger.warning(f"SQL injection detected: patterns={patterns}, input={text[:100]}")
        
        # 记录安全事件
        log_security_event(
            event_type="sql_injection_attempt",
            detail=f"SQL injection pattern detected: {patterns}",
            severity="critical",
        )
        
        return ValidationResult(
            is_valid=False,
            sanitized_value="",
            warnings=warnings,
            errors=errors,
        )
    
    # 基本清理
    sanitized = text
    
    # 移除危险字符
    sanitized = sanitized.replace("'", "''")  # 转义单引号
    sanitized = sanitized.replace("\\", "\\\\")  # 转义反斜杠
    
    # 移除注释
    sanitized = re.sub(r"--.*$", "", sanitized, flags=re.MULTILINE)
    sanitized = re.sub(r"#.*$", "", sanitized, flags=re.MULTILINE)
    sanitized = re.sub(r"/\*.*?\*/", "", sanitized, flags=re.DOTALL)
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=sanitized,
        warnings=warnings,
        errors=errors,
    )


def validate_identifier(identifier: str, max_length: int = 64) -> ValidationResult:
    """
    验证标识符（表名、列名等）。
    
    Args:
        identifier: 标识符
        max_length: 最大长度
    
    Returns:
        ValidationResult: 验证结果
    """
    warnings = []
    errors = []
    
    if not identifier:
        return ValidationResult(
            is_valid=False,
            sanitized_value="",
            errors=["标识符不能为空"],
        )
    
    if not isinstance(identifier, str):
        return ValidationResult(
            is_valid=False,
            sanitized_value="",
            errors=["标识符必须是字符串类型"],
        )
    
    # 长度检查
    if len(identifier) > max_length:
        errors.append(f"标识符长度超过限制({max_length})")
        return ValidationResult(is_valid=False, sanitized_value="", errors=errors)
    
    # 格式检查：只允许字母、数字、下划线
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
        errors.append("标识符格式无效：只允许字母、数字、下划线，且不能以数字开头")
        return ValidationResult(is_valid=False, sanitized_value="", errors=errors)
    
    # 检查是否为SQL关键字
    if identifier.lower() in SQL_KEYWORDS:
        warnings.append(f"标识符与SQL关键字冲突: {identifier}")
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=identifier,
        warnings=warnings,
        errors=errors,
    )


# ==================== 路径安全 ====================


def sanitize_filename(filename: str, max_length: int = 255) -> ValidationResult:
    """
    清理文件名，防止路径遍历攻击。
    
    Args:
        filename: 原始文件名
        max_length: 最大长度
    
    Returns:
        ValidationResult: 验证结果
    """
    warnings = []
    errors = []
    
    if not filename:
        return ValidationResult(
            is_valid=False,
            sanitized_value="unnamed",
            errors=["文件名不能为空"],
        )
    
    if not isinstance(filename, str):
        return ValidationResult(
            is_valid=False,
            sanitized_value="unnamed",
            errors=["文件名必须是字符串类型"],
        )
    
    # 移除路径遍历字符
    sanitized = filename
    sanitized = sanitized.replace("..", "")
    sanitized = sanitized.replace("/", "")
    sanitized = sanitized.replace("\\", "")
    sanitized = sanitized.replace("\x00", "")  # 空字节
    
    # 只保留安全字符
    sanitized = re.sub(r"[^a-zA-Z0-9._\-]", "_", sanitized)
    
    # 移除前导点（防止隐藏文件）
    sanitized = sanitized.lstrip(".")
    
    # 限制长度
    if len(sanitized) > max_length:
        # 保留扩展名
        if "." in sanitized:
            name, ext = sanitized.rsplit(".", 1)
            ext = "." + ext[:10]  # 扩展名最多10字符
            name = name[:max_length - len(ext)]
            sanitized = name + ext
        else:
            sanitized = sanitized[:max_length]
    
    # 确保文件名不为空
    if not sanitized:
        sanitized = "unnamed"
        warnings.append("文件名无效，已使用默认名称")
    
    # 检查危险文件扩展名
    dangerous_extensions = {
        ".exe", ".bat", ".cmd", ".com", ".pif", ".scr",
        ".vbs", ".js", ".jar", ".php", ".asp", ".aspx",
        ".sh", ".bash", ".zsh", ".ps1", ".psm1",
    }
    
    ext = "." + sanitized.rsplit(".", 1)[-1].lower() if "." in sanitized else ""
    if ext in dangerous_extensions:
        warnings.append(f"危险的文件扩展名: {ext}")
        sanitized = sanitized + ".txt"  # 强制改为安全扩展名
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=sanitized,
        warnings=warnings,
        errors=errors,
    )


def sanitize_path(path: str, base_dir: str | None = None) -> ValidationResult:
    """
    清理路径，防止路径遍历攻击。
    
    Args:
        path: 原始路径
        base_dir: 基础目录（如果提供，确保结果路径在此目录内）
    
    Returns:
        ValidationResult: 验证结果
    """
    warnings = []
    errors = []
    
    if not path:
        return ValidationResult(
            is_valid=False,
            sanitized_value="",
            errors=["路径不能为空"],
        )
    
    if not isinstance(path, str):
        return ValidationResult(
            is_valid=False,
            sanitized_value="",
            errors=["路径必须是字符串类型"],
        )
    
    # 检测路径遍历攻击
    if ".." in path:
        errors.append("检测到路径遍历攻击")
        logger.warning(f"Path traversal detected: {path}")
        return ValidationResult(is_valid=False, sanitized_value="", errors=errors)
    
    # 移除危险字符
    sanitized = path
    sanitized = re.sub(r"[\x00-\x1f]", "", sanitized)  # 控制字符
    
    # 标准化路径分隔符
    sanitized = sanitized.replace("\\", "/")
    
    # 移除多余的斜杠
    sanitized = re.sub(r"/+", "/", sanitized)
    
    # 如果提供了基础目录，确保路径在其内
    if base_dir:
        import os
        base_dir = os.path.abspath(base_dir)
        full_path = os.path.abspath(os.path.join(base_dir, sanitized))
        
        if not full_path.startswith(base_dir):
            errors.append("路径超出允许范围")
            logger.warning(f"Path escape detected: {path}")
            return ValidationResult(is_valid=False, sanitized_value="", errors=errors)
        
        sanitized = os.path.relpath(full_path, base_dir)
    
    return ValidationResult(
        is_valid=True,
        sanitized_value=sanitized,
        warnings=warnings,
        errors=errors,
    )


# ==================== 敏感数据检测 ====================


# 敏感数据模式
SENSITIVE_DATA_PATTERNS = {
    "email": re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
    "phone_cn": re.compile(r"1[3-9]\d{9}"),
    "id_card_cn": re.compile(r"\d{17}[\dXx]"),
    "credit_card": re.compile(r"\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}"),
    "password": re.compile(r"(password|passwd|pwd)\s*[=:]\s*\S+", re.IGNORECASE),
    "api_key": re.compile(r"(api[_-]?key|apikey)\s*[=:]\s*\S+", re.IGNORECASE),
    "secret": re.compile(r"(secret|token)\s*[=:]\s*\S+", re.IGNORECASE),
}


def detect_sensitive_data(text: str) -> dict[str, list[str]]:
    """
    检测文本中的敏感数据。
    
    Args:
        text: 待检测文本
    
    Returns:
        dict: 检测到的敏感数据类型和匹配项
    """
    if not text or not isinstance(text, str):
        return {}
    
    detected = {}
    
    for data_type, pattern in SENSITIVE_DATA_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            detected[data_type] = matches[:5]  # 最多返回5个匹配
    
    return detected


def mask_sensitive_data(text: str, mask_char: str = "*") -> str:
    """
    脱敏文本中的敏感数据。
    
    Args:
        text: 原始文本
        mask_char: 脱敏字符
    
    Returns:
        str: 脱敏后的文本
    """
    if not text or not isinstance(text, str):
        return ""
    
    sanitized = text
    
    # 邮箱脱敏
    sanitized = SENSITIVE_DATA_PATTERNS["email"].sub(
        lambda m: m.group(0)[:2] + "****" + m.group(0)[-10:],
        sanitized,
    )
    
    # 手机号脱敏
    sanitized = SENSITIVE_DATA_PATTERNS["phone_cn"].sub(
        lambda m: m.group(0)[:3] + "****" + m.group(0)[-4:],
        sanitized,
    )
    
    # 身份证脱敏
    sanitized = SENSITIVE_DATA_PATTERNS["id_card_cn"].sub(
        lambda m: m.group(0)[:6] + "********" + m.group(0)[-4:],
        sanitized,
    )
    
    # 信用卡脱敏
    sanitized = SENSITIVE_DATA_PATTERNS["credit_card"].sub(
        lambda m: "****-****-****-" + m.group(0)[-4:],
        sanitized,
    )
    
    # 密码脱敏
    sanitized = SENSITIVE_DATA_PATTERNS["password"].sub(
        lambda m: m.group(0).rsplit("=", 1)[0] + "=****",
        sanitized,
    )
    
    # API Key脱敏
    sanitized = SENSITIVE_DATA_PATTERNS["api_key"].sub(
        lambda m: m.group(0).rsplit("=", 1)[0] + "=****",
        sanitized,
    )
    
    return sanitized


# ==================== 综合验证 ====================


def validate_request_data(
    data: dict[str, Any],
    rules: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any], list[str]]:
    """
    验证请求数据。
    
    Args:
        data: 请求数据
        rules: 验证规则
    
    Returns:
        tuple[dict, list]: 清理后的数据、错误列表
    
    Example:
        >>> rules = {
        ...     "username": {"type": "string", "min_length": 3, "max_length": 50},
        ...     "email": {"type": "email", "required": True},
        ... }
        >>> data, errors = validate_request_data({"username": "test"}, rules)
    """
    sanitized_data = {}
    errors = []
    
    for field_name, field_rules in rules.items():
        value = data.get(field_name)
        
        # 检查必填字段
        if field_rules.get("required", False) and value is None:
            errors.append(f"字段 '{field_name}' 是必填的")
            continue
        
        if value is None:
            sanitized_data[field_name] = field_rules.get("default")
            continue
        
        field_type = field_rules.get("type", "string")
        
        # 类型验证
        if field_type == "string":
            result = sanitize_input(
                str(value),
                max_length=field_rules.get("max_length", 10000),
                allow_html=field_rules.get("allow_html", False),
            )
            if not result.is_valid:
                errors.extend([f"字段 '{field_name}': {e}" for e in result.errors])
            else:
                sanitized_data[field_name] = result.sanitized_value
                if result.warnings:
                    logger.debug(f"Field '{field_name}' warnings: {result.warnings}")
        
        elif field_type == "email":
            email_pattern = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
            if not email_pattern.match(str(value)):
                errors.append(f"字段 '{field_name}' 不是有效的邮箱地址")
            else:
                sanitized_data[field_name] = str(value).lower()
        
        elif field_type == "integer":
            try:
                int_value = int(value)
                min_val = field_rules.get("min_value")
                max_val = field_rules.get("max_value")
                if min_val is not None and int_value < min_val:
                    errors.append(f"字段 '{field_name}' 值不能小于 {min_val}")
                elif max_val is not None and int_value > max_val:
                    errors.append(f"字段 '{field_name}' 值不能大于 {max_val}")
                else:
                    sanitized_data[field_name] = int_value
            except (ValueError, TypeError):
                errors.append(f"字段 '{field_name}' 必须是整数")
        
        elif field_type == "float":
            try:
                float_value = float(value)
                min_val = field_rules.get("min_value")
                max_val = field_rules.get("max_value")
                if min_val is not None and float_value < min_val:
                    errors.append(f"字段 '{field_name}' 值不能小于 {min_val}")
                elif max_val is not None and float_value > max_val:
                    errors.append(f"字段 '{field_name}' 值不能大于 {max_val}")
                else:
                    sanitized_data[field_name] = float_value
            except (ValueError, TypeError):
                errors.append(f"字段 '{field_name}' 必须是数字")
        
        elif field_type == "boolean":
            if isinstance(value, bool):
                sanitized_data[field_name] = value
            elif str(value).lower() in ("true", "1", "yes"):
                sanitized_data[field_name] = True
            elif str(value).lower() in ("false", "0", "no"):
                sanitized_data[field_name] = False
            else:
                errors.append(f"字段 '{field_name}' 必须是布尔值")
        
        elif field_type == "list":
            if isinstance(value, list):
                max_items = field_rules.get("max_items", 1000)
                if len(value) > max_items:
                    errors.append(f"字段 '{field_name}' 列表长度超过限制({max_items})")
                else:
                    sanitized_data[field_name] = value
            else:
                errors.append(f"字段 '{field_name}' 必须是列表")
        
        elif field_type == "identifier":
            result = validate_identifier(
                str(value),
                max_length=field_rules.get("max_length", 64),
            )
            if not result.is_valid:
                errors.extend([f"字段 '{field_name}': {e}" for e in result.errors])
            else:
                sanitized_data[field_name] = result.sanitized_value
        
        elif field_type == "filename":
            result = sanitize_filename(str(value))
            if not result.is_valid:
                errors.extend([f"字段 '{field_name}': {e}" for e in result.errors])
            else:
                sanitized_data[field_name] = result.sanitized_value
    
    return sanitized_data, errors


# ==================== 安全日志 ====================


def log_security_event(
    event_type: str,
    detail: str,
    severity: str = "warning",
    request_id: str | None = None,
) -> None:
    """
    记录安全事件日志。
    
    Args:
        event_type: 事件类型
        detail: 详细描述
        severity: 严重程度
        request_id: 请求ID
    """
    from datetime import datetime
    
    log_data = {
        "event_type": event_type,
        "detail": detail,
        "severity": severity,
        "request_id": request_id,
        "timestamp": datetime.now().isoformat(),
    }
    
    if severity == "critical":
        logger.critical(f"Security event: {event_type}", extra=log_data)
    elif severity == "warning":
        logger.warning(f"Security event: {event_type}", extra=log_data)
    else:
        logger.info(f"Security event: {event_type}", extra=log_data)


# ==================== Pydantic验证器 ====================


def create_pydantic_validator(field_name: str, validation_type: str) -> classmethod:
    """
    创建Pydantic字段验证器。
    
    Args:
        field_name: 字段名
        validation_type: 验证类型
    
    Returns:
        classmethod: Pydantic验证器
    
    Example:
        >>> from pydantic import BaseModel
        >>> class MyModel(BaseModel):
        ...     username: str
        ...     _validate_username = create_pydantic_validator("username", "xss")
    """
    from pydantic import field_validator
    
    def validator(cls, v):
        if validation_type == "xss":
            result = sanitize_input(str(v))
            if not result.is_valid:
                raise ValueError(result.errors[0])
            return result.sanitized_value
        elif validation_type == "sql":
            result = sanitize_sql_input(str(v))
            if not result.is_valid:
                raise ValueError(result.errors[0])
            return result.sanitized_value
        elif validation_type == "filename":
            result = sanitize_filename(str(v))
            if not result.is_valid:
                raise ValueError(result.errors[0])
            return result.sanitized_value
        elif validation_type == "identifier":
            result = validate_identifier(str(v))
            if not result.is_valid:
                raise ValueError(result.errors[0])
            return result.sanitized_value
        return v
    
    return field_validator(field_name)(validator)
