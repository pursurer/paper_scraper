"""
配置模块

从 config.py 加载 OpenReview 凭证。
如果 config.py 不存在，将提示用户创建。
"""
import os
import sys

# 尝试从环境变量加载（优先级最高）
EMAIL = os.environ.get("OPENREVIEW_EMAIL")
PASSWORD = os.environ.get("OPENREVIEW_PASSWORD")

# 如果环境变量未设置，尝试从 config.py 加载
if not EMAIL or not PASSWORD:
    try:
        from .config import EMAIL, PASSWORD
    except ImportError:
        # config.py 不存在，检查是否在测试环境
        if "pytest" not in sys.modules:
            print("⚠️  警告: 未找到配置文件")
            print("   请复制 config/config.example.py 为 config/config.py 并填入凭证")
            print("   或设置环境变量 OPENREVIEW_EMAIL 和 OPENREVIEW_PASSWORD")
        EMAIL = None
        PASSWORD = None

