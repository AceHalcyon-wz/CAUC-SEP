"""
单元测试 conftest.py

文件名: conftest.py
路径: backend/tests/unit/
功能: 设置单元测试路径，继承父级 conftest 的 fixtures
作者: CAUC-SEP Team
创建日期: 2026-03-16
"""

import os
import sys

# 将 backend 目录添加到 Python 路径
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)
