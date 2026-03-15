"""
backend/examples 模块

包含后端功能使用示例和指南：
- examples_new_features.py: 新增物理分析功能示例
- examples_tracing.py: 链路追踪系统使用示例
- msgpack_protocol_guide.py: MessagePack协议使用指南
- update_api_guide.py: 自动更新系统API使用指南
"""

from pathlib import Path

EXAMPLES_DIR = Path(__file__).parent

__all__ = [
    "EXAMPLES_DIR",
]
