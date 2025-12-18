"""
论文获取模块

从 OpenReview API v2 获取论文数据。
支持获取已接受论文和所有提交，自动去重。
"""

import time
from typing import List, Dict, Any, Optional

from .utils import safe_api_call


def get_venue_papers(
    client: Any,
    venue: str,
    only_accepted: bool = True,
    verbose: bool = True,
    delay: float = 1.0
) -> List[Any]:
    """
    获取单个 venue 的论文。
    
    Args:
        client: OpenReview API v2 client
        venue: venue ID，如 'ICLR.cc/2024/Conference'
        only_accepted: 是否只获取已接受的论文（默认 True）
        verbose: 是否打印日志
        delay: API 调用之间的延迟（秒）
        
    Returns:
        论文列表（已去重）
        
    Example:
        >>> from paper_scraper.utils import get_client
        >>> client = get_client()
        >>> papers = get_venue_papers(client, 'ICLR.cc/2024/Conference')
    """
    submissions = []
    
    try:
        if only_accepted:
            if verbose:
                print(f"  从 API v2 获取已接受的论文...")
            
            # 获取已接受的论文（通过 venueid）
            submissions = safe_api_call(
                client.get_all_notes,
                content={'venueid': venue},
                details='directReplies'
            )
        else:
            if verbose:
                print(f"  从 API v2 获取所有论文...")
            
            # 获取所有提交（包括单盲和双盲）
            single_blind = safe_api_call(
                client.get_all_notes,
                invitation=f'{venue}/-/Submission',
                details='directReplies'
            )
            
            if delay > 0:
                time.sleep(delay)
            
            double_blind = safe_api_call(
                client.get_all_notes,
                invitation=f'{venue}/-/Blind_Submission',
                details='directReplies'
            )
            
            submissions = (single_blind or []) + (double_blind or [])
        
        if verbose:
            print(f"  ✅ API v2: 找到 {len(submissions or [])} 篇论文")
            
    except Exception as e:
        if verbose:
            print(f"  ❌ Error getting papers from API v2 for venue {venue}: {e}")
        submissions = []
    
    # 去重（基于 forum ID）
    unique_papers = deduplicate_papers(submissions or [])
    
    if verbose:
        print(f"  📊 总计: {len(unique_papers)} 篇唯一论文")
    
    return unique_papers


def get_grouped_venue_papers(
    client: Any,
    venues: List[str],
    only_accepted: bool = True,
    verbose: bool = True,
    delay_between_venues: float = 2.0
) -> Dict[str, List[Any]]:
    """
    获取多个 venue 的论文，按 venue 分组。
    
    Args:
        client: OpenReview API v2 client
        venues: venue ID 列表
        only_accepted: 是否只获取已接受的论文
        verbose: 是否打印日志
        delay_between_venues: venue 之间的延迟（秒）
        
    Returns:
        按 venue 分组的论文字典 {venue_id: [papers]}
        
    Example:
        >>> venues = ['ICLR.cc/2024/Conference', 'ICML.cc/2024/Conference']
        >>> papers = get_grouped_venue_papers(client, venues)
        >>> papers['ICLR.cc/2024/Conference']  # ICLR 的论文列表
    """
    papers = {}
    
    for idx, venue in enumerate(venues):
        if verbose:
            print(f"\n处理 venue {idx + 1}/{len(venues)}: {venue}")
        
        papers[venue] = get_venue_papers(
            client,
            venue,
            only_accepted=only_accepted,
            verbose=verbose
        )
        
        # 在处理下一个 venue 之前添加延迟（避免 rate limit）
        if idx < len(venues) - 1 and delay_between_venues > 0:
            time.sleep(delay_between_venues)
    
    return papers


def get_papers(
    client: Any,
    grouped_venues: Dict[str, List[str]],
    only_accepted: bool = True,
    verbose: bool = True
) -> Dict[str, Dict[str, List[Any]]]:
    """
    获取所有分组 venue 的论文。
    
    这是最高层的获取函数，用于处理按会议分组的 venues。
    
    Args:
        client: OpenReview API v2 client
        grouped_venues: 按会议分组的 venues {conference: [venue_ids]}
        only_accepted: 是否只获取已接受的论文
        verbose: 是否打印日志
        
    Returns:
        双层嵌套字典 {conference: {venue_id: [papers]}}
        
    Example:
        >>> from paper_scraper.venue import get_venues, group_venues
        >>> venues = get_venues(client, ['ICLR', 'ICML'], ['2024'])
        >>> grouped = group_venues(venues, ['ICLR', 'ICML'])
        >>> papers = get_papers(client, grouped)
        >>> papers['ICLR']['ICLR.cc/2024/Conference']  # 获取 ICLR 2024 的论文
    """
    all_papers = {}
    
    for conference, venues in grouped_venues.items():
        if verbose:
            print(f"\n{'='*50}")
            print(f"📚 处理会议: {conference} ({len(venues)} 个 venues)")
            print(f"{'='*50}")
        
        all_papers[conference] = get_grouped_venue_papers(
            client,
            venues,
            only_accepted=only_accepted,
            verbose=verbose
        )
    
    return all_papers


def deduplicate_papers(papers: List[Any]) -> List[Any]:
    """
    基于 forum ID 对论文列表去重。
    
    OpenReview 中，forum 是论文的唯一标识符。
    同一篇论文可能出现在多个地方（如不同的 track），
    但它们的 forum ID 是相同的。
    
    Args:
        papers: 论文列表（OpenReview Note 对象）
        
    Returns:
        去重后的论文列表
    """
    if not papers:
        return []
    
    seen_forums = set()
    unique_papers = []
    
    for paper in papers:
        # 获取 forum ID
        forum_id = None
        if hasattr(paper, 'forum'):
            forum_id = paper.forum
        elif isinstance(paper, dict):
            forum_id = paper.get('forum')
        
        if forum_id and forum_id not in seen_forums:
            seen_forums.add(forum_id)
            unique_papers.append(paper)
        elif forum_id is None:
            # 如果没有 forum ID，保留论文但不去重
            unique_papers.append(paper)
    
    return unique_papers


def count_papers(papers: Dict[str, Dict[str, List[Any]]]) -> Dict[str, int]:
    """
    统计各会议的论文数量。
    
    Args:
        papers: get_papers 返回的嵌套字典
        
    Returns:
        {conference: total_count} 字典
    """
    counts = {}
    
    for conference, venue_papers in papers.items():
        total = sum(len(p) for p in venue_papers.values())
        counts[conference] = total
    
    return counts


def flatten_papers(papers: Dict[str, Dict[str, List[Any]]]) -> List[Any]:
    """
    将嵌套的论文字典展平为列表。
    
    Args:
        papers: get_papers 返回的嵌套字典
        
    Returns:
        所有论文的列表（已去重）
    """
    all_papers = []
    
    for conference, venue_papers in papers.items():
        for venue, paper_list in venue_papers.items():
            all_papers.extend(paper_list)
    
    # 再次去重（跨 venue 可能有重复）
    return deduplicate_papers(all_papers)


def get_paper_ids(papers: List[Any]) -> List[str]:
    """
    从论文列表中提取所有 forum ID。
    
    Args:
        papers: 论文列表
        
    Returns:
        forum ID 列表
    """
    ids = []
    
    for paper in papers:
        if hasattr(paper, 'forum'):
            ids.append(paper.forum)
        elif isinstance(paper, dict) and 'forum' in paper:
            ids.append(paper['forum'])
    
    return ids

