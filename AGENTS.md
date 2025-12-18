# AI Agent 开发指南

## 项目概述

`paper_scraper` 是一个顶会论文获取工具，支持三种数据来源：
- **OpenReview API**: ICLR, ICML, NeurIPS
- **网页爬取**: AAAI, IJCAI, ACL, EMNLP, NAACL, AISTATS
- **PDF 提取**: AAMAS

## 项目结构

```
论文获取/
├── paper_scraper/          # 核心 Python 包
│   ├── __init__.py         # 包入口，定义 SOURCES 和导出
│   ├── __main__.py         # CLI 入口
│   ├── scraper.py          # Scraper 主类（OpenReview）
│   ├── extractor.py        # 字段提取器
│   ├── filters.py          # 关键词过滤器
│   ├── venue.py            # Venue 处理
│   ├── paper.py            # 论文获取
│   ├── web_scraper.py      # 网页爬取
│   ├── pdf_extractor.py    # PDF 提取
│   └── utils.py            # 工具函数
│
├── config/                 # 配置目录
│   ├── __init__.py         # Config 类
│   └── config.example.py   # 配置模板
│
├── tests/                  # 测试目录 (293 个测试)
│   ├── test_*.py
│   └── __init__.py
│
├── 项目指南.md              # TDD 行动指南
├── 文件结构.md              # 文件结构参考
├── README.md               # 项目说明
└── requirements.txt        # 依赖
```

## 开发环境

```bash
# 进入项目
cd 论文获取

# 激活虚拟环境
source venv/bin/activate  # 或 . venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 运行测试
python -m pytest tests/ -v
```

## 测试规范

- 使用 `pytest` 框架
- 测试文件: `tests/test_*.py`
- Mock 外部依赖（网络请求、API 调用）
- 每个模块对应一个测试文件

```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单个测试
python -m pytest tests/test_web_scraper.py -v

# 运行特定测试类
python -m pytest tests/test_cli.py::TestMain -v
```

## 代码风格

- **命名**: `snake_case` (函数/变量), `PascalCase` (类)
- **文档**: 每个模块/类/函数都有 docstring
- **类型**: 使用 type hints
- **导入**: 相对导入 `from .utils import ...`

## 核心模块说明

### scraper.py - OpenReview 来源
```python
class Scraper:
    def __init__(self, conferences, years, keywords, extractor, fpath, ...)
    def add_filter(self, filter_fn)
    def scrape(self)
```

### web_scraper.py - 网页爬取来源
```python
scrape_ijcai(year, output_path, verbose)
scrape_aaai(year, output_path, verbose)
scrape_aistats(year, output_path, verbose)
scrape_acl(year, output_path, verbose)
scrape_emnlp(year, output_path, verbose)
scrape_naacl(year, output_path, verbose)
scrape_conference(conference, year, output_path, verbose)
batch_scrape(conferences, years, output_dir, verbose)
```

### pdf_extractor.py - PDF 提取来源
```python
extract_text_from_pdf(pdf_path)
extract_abstract(text)
extract_keywords(text)
extract_aamas_metadata(pdf_dir, year, output_path, verbose)
```

### config/__init__.py - 配置系统
```python
class Config:
    openreview_email
    openreview_password
    request_delay_min/max
    request_timeout
    request_retries
    output_dir
    verbose
    has_credentials

get_config() -> Config
reset_config()
```

## 数据来源架构

```
┌─────────────────┐     ┌──────────────────┐     ┌───────────────┐
│  OpenReview API │     │   Web Scraping   │     │  PDF Extract  │
│  (ICLR,ICML...) │     │ (AAAI,IJCAI...)  │     │   (AAMAS)     │
└────────┬────────┘     └────────┬─────────┘     └───────┬───────┘
         │                       │                       │
         │   Scraper             │   scrape_*()          │   extract_*()
         │   Extractor           │   fetch_page()        │   process_pdf()
         │   Venue               │   BeautifulSoup       │   PyMuPDF/pdfminer
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
                         ┌───────▼───────┐
                         │  统一 CSV 输出 │
                         │  to_csv()     │
                         └───────────────┘
```

## Git 提交规范

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
test: 测试相关
refactor: 重构
style: 格式调整
```

## 任务执行规范

1. **阅读项目指南.md** 了解当前任务
2. **参考文件结构.md** 了解旧项目实现
3. **TDD 流程**: 写测试 → 实现 → 通过测试
4. **提交**: 完成任务后 git commit + push

## 重要文件

| 文件 | 用途 |
|------|------|
| `项目指南.md` | TDD 行动指南，任务追踪 |
| `文件结构.md` | 旧项目参考 |
| `paper_scraper/__init__.py` | 包入口，SOURCES 定义 |
| `config/__init__.py` | 配置系统 |

## 常见问题

### Q: 如何添加新会议支持？
1. 确定数据来源类型
2. 在对应模块添加爬取函数
3. 更新 `__init__.py` 的 SOURCES 和导出
4. 更新 `__main__.py` 的 scrapers 字典
5. 添加测试用例

### Q: 如何调试网页爬取？
```python
from paper_scraper.web_scraper import fetch_page
html = fetch_page('https://...', verbose=True)
print(html[:1000])  # 查看 HTML 结构
```

### Q: 如何测试 PDF 提取？
```python
from paper_scraper.pdf_extractor import process_pdf
result = process_pdf('./test.pdf')
print(result)
```
