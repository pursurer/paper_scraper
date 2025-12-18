# Paper Scraper 📚

顶会论文获取工具 - 支持 OpenReview、网页爬取、PDF 提取三种数据来源。

[![Tests](https://img.shields.io/badge/tests-293%20passed-brightgreen)]()
[![Python](https://img.shields.io/badge/python-3.8+-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

## ✨ 特性

- **多数据源支持**：OpenReview API、网页爬取、PDF 提取
- **统一 CLI 工具**：`python -m paper_scraper`
- **关键词过滤**：标题/摘要/关键词模糊匹配
- **批量爬取**：支持多会议多年份
- **CSV 导出**：统一输出格式

## 📋 支持的会议

| 来源类型 | 支持会议 |
|---------|---------|
| **OpenReview** | ICLR, ICML, NeurIPS |
| **网页爬取** | AAAI, IJCAI, ACL, EMNLP, NAACL, AISTATS |
| **PDF 提取** | AAMAS |

## 🚀 快速开始

### 安装

```bash
git clone https://github.com/pursurer/paper_scraper.git
cd paper_scraper

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 配置（仅 OpenReview 来源需要）

```bash
# 方式一：环境变量
export OPENREVIEW_EMAIL="your_email@example.com"
export OPENREVIEW_PASSWORD="your_password"

# 方式二：配置文件
cp config/config.example.py config/config.py
# 编辑 config.py 填入凭证
```

## 💻 使用方法

### 命令行 (CLI)

```bash
# 列出支持的会议
python -m paper_scraper --list-conferences

# 爬取 IJCAI 2024 (网页爬取)
python -m paper_scraper -c IJCAI -y 2024 -o ijcai_2024.csv

# 爬取 ICLR 2024 (OpenReview)
python -m paper_scraper -c ICLR -y 2024 -o iclr_2024.csv

# 批量爬取多会议
python -m paper_scraper -c ICLR ICML NeurIPS -y 2023 2024 --output-dir ./output

# 带关键词过滤
python -m paper_scraper -c ICLR -y 2024 -k "reinforcement learning" -o rl_papers.csv

# PDF 提取 (AAMAS)
python -m paper_scraper --pdf-dir ./aamas2025 -y 2025 -o aamas_2025.csv
```

### Python API

```python
# ============ OpenReview 来源 ============
from paper_scraper import Scraper, Extractor, title_filter, abstract_filter

extractor = Extractor(
    fields=['forum'],
    subfields={'content': ['title', 'abstract', 'keywords', 'pdf']}
)

scraper = Scraper(
    conferences=['ICLR'],
    years=['2024'],
    keywords=['reinforcement learning'],
    extractor=extractor,
    fpath='iclr_2024.csv'
)
scraper.add_filter(title_filter)
scraper.add_filter(abstract_filter)
scraper()

# ============ 网页爬取来源 ============
from paper_scraper import scrape_ijcai, scrape_aaai, scrape_acl, batch_scrape

# 单会议
papers = scrape_ijcai(2024, output_path='ijcai_2024.csv')
papers = scrape_aaai(2025, output_path='aaai_2025.csv')
papers = scrape_acl(2023, output_path='acl_2023.csv')

# 批量
results = batch_scrape(['IJCAI', 'AAAI'], [2023, 2024], output_dir='./output')

# ============ PDF 提取 ============
from paper_scraper import extract_aamas_metadata

papers = extract_aamas_metadata('./aamas2025/', 2025, output_path='aamas_2025.csv')
```

## 📁 输出格式

CSV 文件包含以下字段：

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 (会议名_年份_序号) |
| `title` | 论文标题 |
| `keywords` | 关键词 |
| `abstract` | 摘要 |
| `pdf` | PDF 链接 |
| `forum` | 论文页面链接 |
| `year` | 年份 |
| `presentation_type` | 展示类型 (Oral/Spotlight/Poster) |

> **注意**：不同来源的字段完整性有所不同：
> - **OpenReview**：所有字段完整，包含 presentation_type
> - **网页爬取**：部分会议可能缺少 abstract/keywords
> - **PDF 提取**：从 PDF 中提取 abstract/keywords

## ⚙️ 配置选项

支持环境变量配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| `OPENREVIEW_EMAIL` | OpenReview 邮箱 | - |
| `OPENREVIEW_PASSWORD` | OpenReview 密码 | - |
| `PAPER_SCRAPER_DELAY_MIN` | 最小请求延迟(秒) | 2.0 |
| `PAPER_SCRAPER_DELAY_MAX` | 最大请求延迟(秒) | 5.0 |
| `PAPER_SCRAPER_TIMEOUT` | 请求超时(秒) | 30 |
| `PAPER_SCRAPER_RETRIES` | 重试次数 | 3 |
| `PAPER_SCRAPER_OUTPUT_DIR` | 输出目录 | ./output |

## 🧪 运行测试

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单个测试文件
python -m pytest tests/test_web_scraper.py -v
```

## 📦 项目结构

```
paper_scraper/
├── paper_scraper/          # 核心包
│   ├── __init__.py         # 包入口
│   ├── __main__.py         # CLI 入口
│   ├── scraper.py          # Scraper 主类
│   ├── extractor.py        # 字段提取器
│   ├── filters.py          # 关键词过滤器
│   ├── venue.py            # Venue 处理
│   ├── paper.py            # 论文获取
│   ├── web_scraper.py      # 网页爬取
│   ├── pdf_extractor.py    # PDF 提取
│   └── utils.py            # 工具函数
├── config/                 # 配置
├── tests/                  # 测试
└── requirements.txt        # 依赖
```

## 📄 License

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！
