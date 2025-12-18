"""
Paper Scraper 配置模板

使用步骤:
1. 复制此文件为 config.py: cp config.example.py config.py
2. 填入你的配置信息
3. 确保 config.py 已添加到 .gitignore（不要提交到版本控制）

或者使用环境变量:
    export OPENREVIEW_EMAIL="your_email@example.com"
    export OPENREVIEW_PASSWORD="your_password"
    export PAPER_SCRAPER_DELAY_MIN="2.0"
    export PAPER_SCRAPER_DELAY_MAX="5.0"
    export PAPER_SCRAPER_TIMEOUT="30"
    export PAPER_SCRAPER_RETRIES="3"
    export PAPER_SCRAPER_OUTPUT_DIR="./output"
    export PAPER_SCRAPER_VERBOSE="true"

注意: OpenReview 账号可在 https://openreview.net 免费注册
"""

# ============ OpenReview 凭证 ============
# 用于访问 ICLR/ICML/NeurIPS 等会议的论文

EMAIL = "your_email@example.com"
PASSWORD = "your_password"

# ============ 可选配置 ============
# 以下配置也可通过环境变量设置，取消注释并修改即可

# 请求延迟（秒）- 避免请求过快被封禁
# REQUEST_DELAY_MIN = 2.0
# REQUEST_DELAY_MAX = 5.0

# 请求超时（秒）
# REQUEST_TIMEOUT = 30

# 重试次数
# REQUEST_RETRIES = 3

# 默认输出目录
# OUTPUT_DIR = "./output"

# 是否打印详细日志
# VERBOSE = True
