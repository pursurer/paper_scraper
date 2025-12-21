"""
Venue 发现与分组模块

用于从 OpenReview API 获取和组织 venues。
支持自动发现子 track（如 AAAI 的各个分 track）。
"""

import re
from typing import List, Dict, Any, Optional, Callable

from .utils import safe_api_call


# ============ Venue 过滤函数 ============

def filter_by_year(venue: str, years: List[str]) -> Optional[str]:
    """
    根据年份过滤 venue。
    
    Args:
        venue: venue ID
        years: 年份列表（字符串格式，如 ['2024', '2025']）
        
    Returns:
        匹配的 venue 或 None
    """
    if venue is None:
        return None
    for year in years:
        if year in venue:
            return venue
    return None


def filter_by_conference(venue: str, conferences: List[str]) -> bool:
    """
    检查 venue 是否属于指定会议。
    
    Args:
        venue: venue ID
        conferences: 会议名称列表（如 ['ICLR', 'ICML']）
        
    Returns:
        是否匹配
    """
    if venue is None:
        return False
    venue_lower = venue.lower()
    for conf in conferences:
        if conf.lower() in venue_lower:
            return True
    return False


# ============ Venue 分组函数 ============

def group_venues(venues: List[str], conferences: List[str]) -> Dict[str, List[str]]:
    """
    按会议名称对 venues 进行分组。
    
    Args:
        venues: venue ID 列表
        conferences: 会议名称列表（作为分组的 key）
        
    Returns:
        按会议分组的 venues 字典
        
    Example:
        >>> venues = ['ICLR.cc/2024/Conference', 'ICML.cc/2024/Conference']
        >>> grouped = group_venues(venues, ['ICLR', 'ICML'])
        >>> grouped['ICLR']
        ['ICLR.cc/2024/Conference']
    """
    grouped = {conf: [] for conf in conferences}
    
    for venue in venues:
        for conf in conferences:
            if conf.lower() in venue.lower():
                grouped[conf].append(venue)
                break  # 每个 venue 只归属于一个会议
    
    return grouped


# ============ 子 Track 发现 ============

def get_all_subgroups(
    client: Any,
    parent_group_id: str,
    years: List[str],
    verbose: bool = True,
    exclude_workshops: bool = True
) -> List[str]:
    """
    获取指定父组的所有子组。
    
    使用正则表达式从所有 venues 中匹配子组，
    这对于 AAAI 等有多个 track 的会议特别有用。
    
    Args:
        client: OpenReview API v2 client
        parent_group_id: 父组的 ID，例如 'AAAI.org/2025/Conference'
        years: 年份列表
        verbose: 是否打印日志
        exclude_workshops: 是否排除 Workshop
        
    Returns:
        所有子组 ID 列表（包括父组本身）
        
    Example:
        >>> subgroups = get_all_subgroups(client, 'AAAI.org/2025/Conference', ['2025'])
        >>> # 返回类似 ['AAAI.org/2025/Conference', 'AAAI.org/2025/Track/Main', ...]
    """
    all_groups = [parent_group_id]
    
    # 从 parent_group_id 提取基础路径
    # 例如 'AAAI.org/2025/Conference' -> 'AAAI.org/2025'
    base_path = '/'.join(parent_group_id.split('/')[:-1])
    
    # 构建正则表达式模式，匹配所有以 base_path 开头的 venue
    pattern = re.compile(f'^{re.escape(base_path)}/.*')
    
    # 从所有 venues 中筛选匹配的子组
    all_venues = []
    try:
        if verbose:
            print("   正在从所有 venues 中查找匹配的子组...")
        
        # 获取所有 venues
        venues_group = safe_api_call(client.get_group, id='venues')
        if venues_group and hasattr(venues_group, 'members'):
            all_venues = list(venues_group.members)
    except Exception as e:
        if verbose:
            print(f"   ⚠️  获取 venues 失败: {e}")
    
    # 需要排除的模式（不是论文 venue 的组）
    exclude_patterns = [
        '/-/',
        '/Program_Chairs',
        '/Area_Chairs',
        '/Reviewers',
        '/Authors',
        '/Ethics_Reviewers',
        '/Senior_Area_Chairs',
        '/Action_Editors',
    ]
    
    # 筛选匹配的子组
    for venue in all_venues:
        if pattern.match(venue):
            # 确保包含年份
            if any(year in venue for year in years):
                # 排除非论文 venue
                if not any(exclude in venue for exclude in exclude_patterns):
                    # 排除 Workshop
                    if exclude_workshops and 'workshop' in venue.lower():
                        continue
                        
                    if venue not in all_groups:
                        all_groups.append(venue)
    
    return all_groups


# ============ 主要 Venue 获取函数 ============

def get_venues(
    client: Any,
    conferences: List[str],
    years: List[str],
    expand_subgroups: bool = True,
    verbose: bool = True,
    exclude_workshops: bool = True,
    main_track_only: bool = True
) -> List[str]:
    """
    从 OpenReview API v2 获取 venues。
    
    对于 AAAI 等有多个 track 的会议，会自动发现所有子 track/venue。
    
    Args:
        client: OpenReview API v2 client
        conferences: 会议名称列表（如 ['ICLR', 'AAAI']）
        years: 年份列表（如 ['2024', '2025']）
        expand_subgroups: 是否展开子 track（默认 True）
        verbose: 是否打印日志
        exclude_workshops: 是否排除 Workshop（默认 True）
        main_track_only: 是否只保留主会 Track（默认 True）
        
    Returns:
        符合条件的 venue ID 列表
    """
    # 从 API v2 获取所有 venues
    all_venues = []
    try:
        if verbose:
            print("正在从 API v2 获取 venues...")
        
        venues_group = safe_api_call(client.get_group, id='venues')
        if venues_group and hasattr(venues_group, 'members'):
            all_venues = list(venues_group.members)
            if verbose:
                print(f"✅ API v2: 找到 {len(all_venues)} 个 venues")
    except Exception as e:
        if verbose:
            print(f"❌ Error getting venues from API v2: {e}")
        return []
    
    # 过滤：年份 + 会议名称
    filtered_venues = []
    for venue in all_venues:
        # 年份过滤
        if filter_by_year(venue, years) is None:
            continue
        # 会议过滤
        if filter_by_conference(venue, conferences):
            # Workshop 过滤
            if exclude_workshops and 'workshop' in venue.lower():
                continue
            filtered_venues.append(venue)
    
    if not expand_subgroups:
        return filtered_venues
    
    # 展开子 track
    expanded_venues = []
    for venue in filtered_venues:
        expanded_venues.append(venue)
        
        # 检查是否是主 Conference venue（例如 AAAI.org/2025/Conference）
        # 对于 AAAI，论文可能分散在各个 Track 下
        if _should_expand_venue(venue):
            if verbose:
                print(f"\n🔍 发现主 Conference venue: {venue}")
                print("   正在获取所有子 track/venue...")
            
            try:
                sub_venues = get_all_subgroups(
                    client, 
                    venue, 
                    years, 
                    verbose,
                    exclude_workshops=exclude_workshops
                )
                
                # 过滤掉主 venue 本身（已添加），只添加子 venue
                added_count = 0
                for sub_venue in sub_venues:
                    if sub_venue != venue and sub_venue not in expanded_venues:
                        expanded_venues.append(sub_venue)
                        added_count += 1
                
                if verbose and added_count > 0:
                    print(f"   ✅ 找到 {added_count} 个子 venue")
            except Exception as e:
                if verbose:
                    print(f"   ⚠️  获取子 venue 时出错: {e}")
    
    if verbose and len(expanded_venues) > len(filtered_venues):
        print(f"\n📊 Venue 扩展: {len(filtered_venues)} -> {len(expanded_venues)} 个 venue")
    
    # 全局去重（保持顺序）
    unique_venues = list(dict.fromkeys(expanded_venues))
    
    if verbose and len(unique_venues) < len(expanded_venues):
        print(f"   去重后: {len(unique_venues)} 个 venue")
    
    # 最终过滤：Main Track Only
    if main_track_only:
        final_venues = []
        for venue in unique_venues:
            lower = venue.lower()
            
            # 排除 Competition
            if 'competition' in lower:
                continue
            
            # 排除 High School Projects
            if 'high_school' in lower:
                continue
                
            # 排除 Creative AI
            if 'creative_ai' in lower:
                continue
                
            # 排除 Demo
            if 'demo' in lower:
                continue

            # 排除 Datasets and Benchmarks (通常作为独立 Track)
            # 除非用户想要，但这里默认排除以只保留 "主会"
            if 'datasets_and_benchmarks' in lower:
                continue
            
            # 排除 Education Program
            if 'education' in lower:
                continue
            
            # 排除 Position Paper Track
            if 'position_paper' in lower:
                continue

            # 排除其他 Track (除非是 Track/Main)
            # NeurIPS.cc/2024/Conference 应该保留
            if 'track' in lower and 'track/main' not in lower:
                continue
            
            final_venues.append(venue)
        
        if verbose and len(final_venues) < len(unique_venues):
            print(f"   主会过滤后: {len(final_venues)} 个 venue")
        
        return final_venues
        
    return unique_venues


def _should_expand_venue(venue: str) -> bool:
    """
    判断是否应该展开该 venue 的子 track。
    
    对于 AAAI 等会议，论文可能分散在各个 Track 下，需要展开。
    但对于已经是特定 Track 的 venue，不需要再展开。
    
    Args:
        venue: venue ID
        
    Returns:
        是否应该展开
    """
    if '/Conference' not in venue:
        return False
    
    # 这些 venue 不需要展开（已经是特定 track）
    no_expand_patterns = [
        'Track',
        'Demo',
        'Workshop',
        'IAAI',
        'Tutorial',
    ]
    
    return not any(pattern in venue for pattern in no_expand_patterns)


# ============ 便捷函数 ============

def get_venue_info(venue: str) -> Dict[str, str]:
    """
    解析 venue ID，提取会议名称、年份等信息。
    
    Args:
        venue: venue ID，如 'ICLR.cc/2024/Conference'
        
    Returns:
        包含 org, year, type 的字典
        
    Example:
        >>> info = get_venue_info('ICLR.cc/2024/Conference')
        >>> info['org']  # 'ICLR.cc'
        >>> info['year']  # '2024'
        >>> info['type']  # 'Conference'
    """
    parts = venue.split('/')
    
    info = {
        'org': parts[0] if len(parts) > 0 else '',
        'year': '',
        'type': '',
        'full': venue,
    }
    
    # 尝试找到年份
    for part in parts:
        if part.isdigit() and len(part) == 4:
            info['year'] = part
            break
    
    # 最后一部分通常是类型
    if len(parts) > 1:
        info['type'] = parts[-1]
    
    return info


def format_venues_summary(venues: List[str]) -> str:
    """
    格式化 venues 列表的摘要信息。
    
    Args:
        venues: venue ID 列表
        
    Returns:
        格式化的摘要字符串
    """
    if not venues:
        return "No venues found."
    
    # 按年份分组
    by_year: Dict[str, List[str]] = {}
    for venue in venues:
        info = get_venue_info(venue)
        year = info['year'] or 'Unknown'
        if year not in by_year:
            by_year[year] = []
        by_year[year].append(venue)
    
    lines = [f"Found {len(venues)} venues:"]
    for year in sorted(by_year.keys(), reverse=True):
        lines.append(f"  {year}: {len(by_year[year])} venues")
    
    return '\n'.join(lines)

