"""
Paper Scraper - 顶会论文元数据获取工具

从多个来源批量获取 AI 顶会论文的元数据：
- OpenReview API: ICML、ICLR、NeurIPS
- 网页爬取: AAAI、IJCAI、ACL、EMNLP、NAACL、AISTATS
- PDF 提取: AAMAS

支持关键词过滤和全量抓取，导出为 CSV/PKL 格式。

Usage:
    from paper_scraper import Scraper, Extractor
    
    extractor = Extractor(
        fields=['forum'],
        subfields={'content': ['title', 'abstract', 'keywords', 'pdf']}
    )
    
    scraper = Scraper(
        conferences=['ICLR'],
        years=['2024'],
        keywords=[],
        extractor=extractor,
        fpath='output.csv'
    )
    scraper()
"""

__version__ = "0.1.0"
__author__ = "huigu"

# 数据源类型
SOURCES = {
    # OpenReview API 获取
    'openreview': ['ICLR', 'ICML', 'NeurIPS'],
    # 网页爬取获取
    'web_scrape': ['AAAI', 'IJCAI', 'ACL', 'EMNLP', 'NAACL', 'AISTATS'],
    # PDF 下载 + 元数据提取
    'pdf_extract': ['AAMAS'],
}

# 核心类将在模块迁移后导出
# from .scraper import Scraper
# from .extractor import Extractor
# from .filters import title_filter, keywords_filter, abstract_filter
# from .utils import save_papers, load_papers

__all__ = [
    "__version__",
    "SOURCES",
    # "Scraper",
    # "Extractor", 
    # "title_filter",
    # "keywords_filter",
    # "abstract_filter",
    # "save_papers",
    # "load_papers",
]
