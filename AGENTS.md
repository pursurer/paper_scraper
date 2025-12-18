# AGENTS.md - AI Agent 开发指南

> 本文件为 AI Agent（如 Cursor、GitHub Copilot）提供项目上下文和开发规范。

---

## 📁 项目结构 (Project Structure)

```
论文获取/
├── paper_scraper/          # 核心 Python 包
│   ├── __init__.py         # 包入口，暴露公开 API
│   ├── scraper.py          # Scraper 主类（OpenReview）
│   ├── paper.py            # 论文获取逻辑
│   ├── venue.py            # Venue 发现与分组
│   ├── extractor.py        # 字段提取器
│   ├── filters.py          # 关键词过滤器
│   ├── web_scraper.py      # 网页爬取（AAAI/IJCAI/ACL等）
│   ├── pdf_extractor.py    # PDF 元数据提取（AAMAS）
│   └── utils.py            # 工具函数（API客户端、CSV导出、重试机制）
│
├── scripts/                # 使用脚本
│   ├── scrape.py           # 统一 CLI 入口
│   └── batch_scrape.py     # 批量抓取脚本
│
├── tests/                  # 测试文件
├── config/                 # 配置目录
│
├── 文件结构.md              # 详细的文件结构文档
├── 项目指南.md              # TDD 行动指南（查看当前任务）
└── AGENTS.md               # 本文件
```

---

## 📦 数据来源架构 (Data Sources)

```
┌─────────────────────────────────────────────────────────────┐
│                    Paper Scraper                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ OpenReview  │  │ Web Scrape  │  │ PDF Extract │         │
│  │    API      │  │   (HTML)    │  │  (AAMAS)    │         │
│  ├─────────────┤  ├─────────────┤  ├─────────────┤         │
│  │ • ICLR      │  │ • AAAI      │  │ • AAMAS     │         │
│  │ • ICML      │  │ • IJCAI     │  │             │         │
│  │ • NeurIPS   │  │ • ACL       │  │             │         │
│  │             │  │ • EMNLP     │  │             │         │
│  │             │  │ • NAACL     │  │             │         │
│  │             │  │ • AISTATS   │  │             │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
│                           │                                 │
│                           ▼                                 │
│                  ┌─────────────────┐                        │
│                  │  Unified CSV    │                        │
│                  │  Output Format  │                        │
│                  └─────────────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 开发环境 (Dev Environment)

### 环境设置
```bash
cd 论文获取/
python -m venv venv
source venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 配置凭证（仅 OpenReview 来源需要）
```bash
cp config/config.example.py config/config.py
# 编辑 config/config.py，填入 OpenReview 账号
```

### 依赖说明
| 包名 | 用途 | 来源 |
|------|------|------|
| `openreview-py` | OpenReview API v2 客户端 | OpenReview |
| `beautifulsoup4` | HTML 解析 | Web Scrape |
| `requests` | HTTP 请求 | Web Scrape |
| `PyMuPDF` | PDF 解析 | PDF Extract |
| `dill` | 序列化 Python 对象 | 通用 |
| `thefuzz` | 模糊字符串匹配 | 通用 |

### 常用命令
```bash
# 激活虚拟环境
source venv/bin/activate

# 安装/更新依赖
pip install -r requirements.txt

# 运行单会议抓取
python scripts/scrape.py --conference ICLR --years 2024

# 运行测试
python -m pytest tests/
```

---

## 🧪 测试说明 (Testing Instructions)

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行特定测试文件
python -m pytest tests/test_scraper.py -v

# 运行特定测试函数
python -m pytest tests/test_scraper.py::test_venue_discovery -v
```

### 测试规范
- 测试文件命名：`test_<module>.py`
- 测试函数命名：`test_<功能描述>`
- 为修改的代码添加或更新测试
- 提交前确保所有测试通过

### Mock API/网络请求
```python
# 测试时使用 mock 避免真实 API/网络调用
from unittest.mock import Mock, patch

@patch('paper_scraper.utils.get_client')
def test_scraper(mock_client):
    mock_client.return_value = Mock()
    # ...测试代码
```

---

## 📝 代码规范 (Code Style)

### 命名约定
| 类型 | 规范 | 示例 |
|------|------|------|
| 函数/变量 | `snake_case` | `get_papers()`, `venue_list` |
| 类名 | `PascalCase` | `Scraper`, `Extractor` |
| 常量 | `UPPER_CASE` | `MAX_RETRIES`, `API_BASE_URL` |
| 私有方法 | `_snake_case` | `_parse_venue()` |

### 文档字符串
```python
def get_papers(client, venue_id: str, only_accepted: bool = True) -> List[dict]:
    """
    从 OpenReview API 获取论文列表。
    
    Args:
        client: OpenReview API v2 客户端
        venue_id: Venue 标识符，如 'ICLR.cc/2024/Conference'
        only_accepted: 是否只获取已接受论文
        
    Returns:
        论文字典列表，包含 title, abstract, forum 等字段
        
    Raises:
        OpenReviewError: API 调用失败时抛出
    """
```

### 状态输出
使用 emoji 表示状态，保持输出一致：
```python
print("✅ 成功")
print("❌ 失败")
print("⚠️  警告")
print("📊 统计")
print("🔍 搜索中...")
```

---

## 🔧 重要上下文 (Key Context)

### 三种数据来源

#### 1. OpenReview API (ICLR, ICML, NeurIPS)
- 基础 URL: `https://api2.openreview.net`
- 需要账号登录获取完整数据
- 有速率限制，需要重试机制（429 错误）
- Venue 格式: `ICLR.cc/2024/Conference`

#### 2. 网页爬取 (AAAI, IJCAI, ACL, EMNLP, NAACL, AISTATS)
- 从各会议官网解析 HTML
- 使用 BeautifulSoup 提取论文信息
- 不同年份网页结构可能不同，需要适配
- 参考实现: `AAMAS论文获取/paper_downloader/code/paper_downloader_*.py`

#### 3. PDF 提取 (AAMAS)
- 先下载 PDF 文件
- 使用 PyMuPDF 从 PDF 提取 title, abstract, keywords
- 转换为统一 CSV 格式
- 参考实现: `AAMAS论文获取/paper_downloader/code/extract_aamas_metadata.py`

### 统一输出格式
| 字段 | 说明 |
|------|------|
| `id` | 会议名_序号 (例: iclr_2024_1) |
| `title` | 论文标题 |
| `keywords` | 关键词列表 |
| `abstract` | 摘要 |
| `pdf` | PDF 链接 |
| `forum` | 论文页面链接 |
| `year` | 年份 |
| `presentation_type` | 展示类型 (Oral/Spotlight/Poster) |

---

## 📋 任务执行规范 (Task Execution)

### 执行前
1. **阅读 `项目指南.md`** - 了解当前原子任务
2. **阅读 `文件结构.md`** - 了解项目整体架构
3. **检查 Out-of-scope** - 不要超出任务边界

### 执行中
1. 遵循 TDD：先写测试，再实现功能
2. 小步提交，每个提交只做一件事
3. 保持代码风格一致

### 执行后
1. 运行测试确保通过
2. **更新 `项目指南.md`**：
   - 将完成的任务移到"TDD 演进日志"
   - 更新"宏观项目蓝图"进度
   - 为下一个任务编写规格书

---

## 🚫 禁止事项 (Do NOT)

- ❌ 不要修改原项目（`Openreview论文获取方案/`、`AAMAS论文获取/`）- 只读参考
- ❌ 不要硬编码凭证
- ❌ 不要在代码中使用 `print` 调试后忘记删除
- ❌ 不要跳过测试
- ❌ 不要在一次提交中做多件事
- ❌ 不要使用 `*` 通配符导入

---

## ✅ 检查清单 (Checklist)

提交前确认：
- [ ] 代码符合命名规范
- [ ] 添加/更新了相关测试
- [ ] 测试全部通过
- [ ] 文档已更新（如有需要）
- [ ] `项目指南.md` 已更新
