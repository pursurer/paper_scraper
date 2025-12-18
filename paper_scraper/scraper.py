"""
Scraper 主类模块

协调 venue 发现、论文获取、过滤、提取的完整工作流。
这是 paper_scraper 包的核心入口类。
"""

from typing import List, Dict, Any, Optional, Callable, Tuple

from .utils import get_client, to_csv, papers_to_list
from .venue import get_venues, group_venues
from .paper import get_papers, flatten_papers
from .filters import satisfies_any_filters
from .extractor import Extractor


class Scraper:
    """
    论文抓取器主类。
    
    协调以下流程：
    1. 从 OpenReview API 获取 venues
    2. 获取各 venue 的论文
    3. 应用关键词过滤器
    4. 提取指定字段
    5. 保存为 CSV
    
    Attributes:
        conferences: 会议名称列表
        years: 年份列表
        keywords: 搜索关键词列表
        extractor: 字段提取器
        fpath: 输出文件路径
        filters: 过滤器列表
        
    Example:
        >>> from paper_scraper import Scraper, Extractor
        >>> 
        >>> extractor = Extractor(
        ...     fields=['forum'],
        ...     subfields={'content': ['title', 'abstract', 'keywords', 'pdf']}
        ... )
        >>> 
        >>> scraper = Scraper(
        ...     conferences=['ICLR'],
        ...     years=['2024'],
        ...     keywords=['reinforcement learning'],
        ...     extractor=extractor,
        ...     fpath='papers.csv'
        ... )
        >>> 
        >>> # 添加过滤器
        >>> from paper_scraper import title_filter, abstract_filter
        >>> scraper.add_filter(title_filter)
        >>> scraper.add_filter(abstract_filter)
        >>> 
        >>> # 运行抓取
        >>> scraper()
    """
    
    def __init__(
        self,
        conferences: List[str],
        years: List[str],
        keywords: List[str],
        extractor: Extractor,
        fpath: str,
        fns: Optional[List[Callable]] = None,
        groups: Optional[List[str]] = None,
        only_accepted: bool = True,
        client: Any = None,
        verbose: bool = True,
        exclude_workshops: bool = True,
    ):
        """
        初始化 Scraper。
        
        Args:
            conferences: 会议名称列表，如 ['ICLR', 'ICML']
            years: 年份列表，如 ['2024', '2025']
            keywords: 搜索关键词列表，空列表表示获取所有论文
            extractor: Extractor 实例，用于提取论文字段
            fpath: 输出 CSV 文件路径
            fns: 自定义处理函数列表，每个函数接收论文对象并返回修改后的论文
            groups: 分组依据，默认为会议名称
            only_accepted: 是否只获取已接受的论文（默认 True）
            client: OpenReview API client（可选，默认自动创建）
            verbose: 是否打印日志（默认 True）
            exclude_workshops: 是否排除 Workshop（默认 True）
        """
        self.conferences = conferences
        self.years = years
        self.keywords = keywords
        self.extractor = extractor
        self.fpath = fpath
        self.fns = fns or []
        self.groups = groups or conferences  # 默认按会议分组
        self.only_accepted = only_accepted
        self.verbose = verbose
        self.exclude_workshops = exclude_workshops
        
        # 过滤器列表：[(filter_func, args, kwargs), ...]
        self.filters: List[Tuple[Callable, tuple, dict]] = []
        
        # API client（延迟初始化）
        self._client = client
        
        # 存储抓取结果
        self.raw_papers: Optional[Dict] = None
        self.filtered_papers: Optional[Dict] = None
    
    @property
    def client(self) -> Any:
        """延迟获取 API client。"""
        if self._client is None:
            self._client = get_client()
        return self._client
    
    def __call__(self) -> List[Dict]:
        """可调用接口，执行抓取流程。"""
        return self.scrape()
    
    def __repr__(self) -> str:
        return (
            f"Scraper(conferences={self.conferences}, "
            f"years={self.years}, "
            f"keywords={self.keywords[:3]}{'...' if len(self.keywords) > 3 else ''}, "
            f"filters={len(self.filters)})"
        )
    
    def add_filter(
        self,
        filter_func: Callable,
        *args,
        **kwargs
    ) -> 'Scraper':
        """
        添加过滤器。
        
        Args:
            filter_func: 过滤器函数，如 title_filter, abstract_filter
            *args: 传递给过滤器的额外位置参数
            **kwargs: 传递给过滤器的额外关键字参数
            
        Returns:
            self，支持链式调用
            
        Example:
            >>> scraper.add_filter(title_filter)
            >>> scraper.add_filter(abstract_filter, threshold=90)
        """
        self.filters.append((filter_func, args, kwargs))
        return self
    
    def clear_filters(self) -> 'Scraper':
        """清空所有过滤器。"""
        self.filters = []
        return self
    
    def scrape(self) -> List[Dict]:
        """
        执行完整的抓取流程。
        
        流程：
        1. 获取 venues
        2. 获取论文
        3. 应用过滤器和提取器
        4. 保存为 CSV
        
        Returns:
            提取后的论文列表（字典格式）
        """
        if self.verbose:
            print("=" * 60)
            print(f"🚀 Paper Scraper")
            print(f"   会议: {', '.join(self.conferences)}")
            print(f"   年份: {', '.join(self.years)}")
            print(f"   关键词: {self.keywords if self.keywords else '(获取所有论文)'}")
            print(f"   过滤器: {len(self.filters)} 个")
            if self.exclude_workshops:
                print("   排除: Workshops")
            print("=" * 60)
        
        # Step 1: 获取 venues
        if self.verbose:
            print("\n📍 Step 1: 获取 venues...")
        venues = get_venues(
            self.client,
            self.conferences,
            self.years,
            verbose=self.verbose,
            exclude_workshops=self.exclude_workshops
        )
        
        if not venues:
            if self.verbose:
                print("❌ 未找到任何 venue，终止抓取")
            return []
        
        # Step 2: 获取论文
        if self.verbose:
            print(f"\n📄 Step 2: 获取论文...")
        
        grouped_venues = group_venues(venues, self.groups)
        self.raw_papers = get_papers(
            self.client,
            grouped_venues,
            only_accepted=self.only_accepted,
            verbose=self.verbose
        )
        
        # Step 3: 应用过滤器和提取器
        if self.verbose:
            print(f"\n🔍 Step 3: 应用过滤器...")
        
        self.filtered_papers = self._apply_on_papers(self.raw_papers)
        
        # Step 4: 转换为列表
        papers_list = papers_to_list(self.filtered_papers)
        
        if self.verbose:
            print(f"\n📊 结果: {len(papers_list)} 篇论文匹配")
        
        # Step 5: 保存 CSV
        if self.fpath:
            # 确保目录存在
            import os
            os.makedirs(os.path.dirname(self.fpath) or '.', exist_ok=True)
            
            if self.verbose:
                print(f"\n💾 Step 4: 保存到 {self.fpath}...")
            to_csv(papers_list, self.fpath)
            if self.verbose:
                print(f"✅ 已保存到 {self.fpath}")
        
        if self.verbose:
            print("\n" + "=" * 60)
            print("🎉 抓取完成!")
            print("=" * 60)
        
        return papers_list
    
    def _apply_on_papers(self, papers: Dict) -> Dict:
        """
        对论文应用过滤器、自定义函数和提取器。
        
        Args:
            papers: 嵌套的论文字典 {group: {venue: [papers]}}
            
        Returns:
            处理后的论文字典（同样结构，但论文已转为字典格式）
        """
        modified_papers = {}
        total_matched = 0
        
        for group, grouped_venues in papers.items():
            modified_papers[group] = {}
            
            for venue, venue_papers in grouped_venues.items():
                modified_papers[group][venue] = []
                
                # 解析 venue 信息
                venue_info = self._parse_venue(venue)
                
                for paper in venue_papers:
                    # 应用过滤器
                    if self.filters and self.keywords:
                        _, _, satisfies = satisfies_any_filters(
                            paper,
                            self.keywords,
                            self.filters
                        )
                        if not satisfies:
                            continue
                    
                    # 添加元数据
                    self._add_metadata(paper, group, venue, venue_info)
                    
                    # 执行自定义函数
                    for fn in self.fns:
                        paper = fn(paper)
                    
                    # 提取字段
                    extracted_paper = self.extractor(paper)
                    
                    # 添加年份
                    extracted_paper['year'] = venue_info.get('year', '')
                    
                    modified_papers[group][venue].append(extracted_paper)
                    total_matched += 1
        
        if self.verbose:
            print(f"   ✅ 匹配 {total_matched} 篇论文")
        
        return modified_papers
    
    def _parse_venue(self, venue: str) -> Dict[str, str]:
        """
        解析 venue ID，提取组织、年份、类型信息。
        
        Args:
            venue: venue ID，如 'ICLR.cc/2024/Conference'
            
        Returns:
            包含 org, year, type 的字典
        """
        parts = venue.split('/')
        
        info = {
            'org': parts[0] if len(parts) > 0 else '',
            'year': '',
            'type': parts[-1] if len(parts) > 1 else '',
        }
        
        # 找到年份
        for part in parts:
            if part.isdigit() and len(part) == 4:
                info['year'] = part
                break
        
        return info
    
    def _add_metadata(
        self,
        paper: Any,
        group: str,
        venue: str,
        venue_info: Dict[str, str]
    ) -> None:
        """
        向论文添加元数据。
        
        Args:
            paper: 论文对象
            group: 分组名称
            venue: venue ID
            venue_info: 解析后的 venue 信息
        """
        # 确保 content 存在
        if not hasattr(paper, 'content'):
            return
        
        if not isinstance(paper.content, dict):
            return
        
        # 添加分组信息
        paper.content['group'] = group
        
        # 推断 presentation type（如果未设置）
        presentation_type = paper.content.get('presentation_type')
        if not presentation_type:
            paper.content['presentation_type'] = self._infer_presentation_type(venue)
    
    def _infer_presentation_type(self, venue: str) -> str:
        """
        从 venue 名称推断论文展示类型。
        
        Args:
            venue: venue ID
            
        Returns:
            展示类型：'Oral', 'Spotlight', 或 'Poster'
        """
        venue_lower = venue.lower()
        
        if 'oral' in venue_lower and 'spotlight' not in venue_lower:
            return 'Oral'
        elif 'spotlight' in venue_lower:
            return 'Spotlight'
        else:
            return 'Poster'
    
    # ============ 便捷方法 ============
    
    def get_paper_count(self) -> int:
        """获取已抓取的论文总数。"""
        if self.filtered_papers is None:
            return 0
        
        total = 0
        for group_papers in self.filtered_papers.values():
            for venue_papers in group_papers.values():
                total += len(venue_papers)
        return total
    
    def get_papers_flat(self) -> List[Dict]:
        """获取扁平化的论文列表。"""
        if self.filtered_papers is None:
            return []
        return papers_to_list(self.filtered_papers)


def create_scraper(
    conferences: List[str],
    years: List[str],
    keywords: Optional[List[str]] = None,
    output_path: str = 'papers.csv',
    fields: Optional[List[str]] = None,
    subfields: Optional[Dict[str, List[str]]] = None,
    only_accepted: bool = True,
    exclude_workshops: bool = True,
) -> Scraper:
    """
    便捷函数：创建配置好的 Scraper 实例。
    
    Args:
        conferences: 会议名称列表
        years: 年份列表
        keywords: 关键词列表（可选）
        output_path: 输出文件路径
        fields: 要提取的顶层字段
        subfields: 要提取的子字段
        only_accepted: 是否只获取已接受论文
        exclude_workshops: 是否排除 Workshop（默认 True）
        
    Returns:
        配置好的 Scraper 实例
        
    Example:
        >>> scraper = create_scraper(
        ...     conferences=['ICLR'],
        ...     years=['2024'],
        ...     keywords=['transformer'],
        ...     output_path='iclr_2024.csv'
        ... )
        >>> scraper.add_filter(title_filter)
        >>> scraper()
    """
    # 默认字段配置
    if fields is None:
        fields = ['forum']
    
    if subfields is None:
        subfields = {
            'content': ['title', 'abstract', 'keywords', 'pdf', 'presentation_type']
        }
    
    extractor = Extractor(
        fields=fields,
        subfields=subfields,
        include_subfield=False
    )
    
    return Scraper(
        conferences=conferences,
        years=years,
        keywords=keywords or [],
        extractor=extractor,
        fpath=output_path,
        only_accepted=only_accepted,
        exclude_workshops=exclude_workshops,
    )

