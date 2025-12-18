# Paper Scraper - 顶会论文获取工具

从多个来源批量获取 AI 顶会论文元数据的 Python 工具。

## ✨ 功能特性

- 🎯 支持主流 AI 会议：ICML、ICLR、NeurIPS、AAAI、IJCAI、ACL、EMNLP 等
- 🔍 关键词过滤：在标题、摘要、关键词中模糊匹配
- 📊 全量抓取：获取会议所有已接受论文
- 🏷️ 展示类型：自动识别 Oral/Spotlight/Poster
- 💾 多种导出格式：CSV（表格）、PKL（原始对象）

## 📦 数据来源

| 来源类型 | 支持会议 | 获取方式 |
|---------|---------|---------|
| **OpenReview API** | ICLR, ICML, NeurIPS | 直接调用 API 获取元数据 |
| **网页爬取** | AAAI, IJCAI, ACL, EMNLP, NAACL, AISTATS | 解析官网 HTML 获取论文列表 |
| **PDF 提取** | AAMAS | 下载 PDF 后提取 title/abstract/keywords |

## 🚀 快速开始

### 安装

```bash
# 克隆项目
git clone <repo-url>
cd 论文获取

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # macOS/Linux

# 安装依赖
pip install -r requirements.txt
```

### 配置

```bash
# 复制配置模板
cp config/config.example.py config/config.py

# 编辑配置文件，填入 OpenReview 账号（仅 OpenReview 来源需要）
```

或使用环境变量：

```bash
export OPENREVIEW_EMAIL="your_email@example.com"
export OPENREVIEW_PASSWORD="your_password"
```

### 使用

```bash
# 抓取 ICLR 2024 所有论文（OpenReview）
python scripts/scrape.py --conference ICLR --years 2024

# 抓取 AAAI 2025（网页爬取）
python scripts/scrape.py --conference AAAI --years 2025

# 指定输出目录
python scripts/scrape.py --conference ICML --years 2024 --output-dir ./papers
```

## 📁 项目结构

```
论文获取/
├── paper_scraper/          # 核心 Python 包
│   ├── __init__.py         # 包入口
│   ├── scraper.py          # Scraper 主类
│   ├── paper.py            # 论文获取（OpenReview）
│   ├── venue.py            # Venue 处理
│   ├── extractor.py        # 字段提取
│   ├── filters.py          # 关键词过滤
│   ├── web_scraper.py      # 网页爬取（AAAI/IJCAI等）
│   ├── pdf_extractor.py    # PDF 元数据提取（AAMAS）
│   └── utils.py            # 工具函数
│
├── scripts/                # 使用脚本
├── tests/                  # 测试文件
├── config/                 # 配置目录
│
├── requirements.txt        # Python 依赖
└── README.md              # 本文件
```

## 📖 API 使用

```python
from paper_scraper import Scraper, Extractor
from paper_scraper.filters import title_filter, abstract_filter

# 配置提取器
extractor = Extractor(
    fields=['forum'],
    subfields={'content': ['title', 'keywords', 'abstract', 'pdf']}
)

# 创建爬虫（OpenReview 来源）
scraper = Scraper(
    conferences=['ICLR'],
    years=['2024'],
    keywords=['reinforcement learning'],  # 可选：关键词过滤
    extractor=extractor,
    fpath='output.csv',
    only_accepted=True
)

# 添加过滤器（可选）
scraper.add_filter(title_filter)
scraper.add_filter(abstract_filter)

# 运行
scraper()
```

## 📋 CSV 输出格式

| 字段 | 说明 |
|------|------|
| `id` | 唯一标识 |
| `title` | 论文标题 |
| `keywords` | 关键词列表 |
| `abstract` | 摘要 |
| `pdf` | PDF 链接 |
| `forum` | 论文页面链接 |
| `year` | 年份 |
| `presentation_type` | 展示类型 (Oral/Spotlight/Poster) |

## 🧪 测试

```bash
# 运行所有测试
python -m pytest tests/ -v
```

## 📝 License

MIT License
