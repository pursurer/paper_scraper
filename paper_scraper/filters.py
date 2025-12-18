"""
关键词过滤器模块

基于模糊字符串匹配筛选论文，支持标题、摘要、关键词过滤。
使用 thefuzz 库进行模糊匹配。
"""

from typing import List, Tuple, Any, Optional, Callable

from thefuzz import fuzz


# ============ 底层匹配函数 ============

def check_keywords_with_keywords(
    keywords: List[str],
    paper_keywords: Any,
    threshold: int = 85
) -> Tuple[Optional[str], bool]:
    """
    检查搜索关键词是否与论文关键词匹配。
    
    使用精确匹配（fuzz.ratio）比较每个关键词。
    
    Args:
        keywords: 搜索关键词列表
        paper_keywords: 论文的关键词（可以是列表、字符串或其他可迭代对象）
        threshold: 匹配阈值（0-100），默认 85
        
    Returns:
        (matched_keyword, is_matched): 匹配的关键词和是否匹配
    """
    if not paper_keywords:
        return None, False
    
    # 确保 paper_keywords 是列表
    if not isinstance(paper_keywords, list):
        if isinstance(paper_keywords, str):
            paper_keywords = [paper_keywords]
        else:
            try:
                paper_keywords = list(paper_keywords)
            except:
                paper_keywords = [str(paper_keywords)]
    
    for keyword in keywords:
        if keyword is None:
            continue
        
        # 确保 keyword 是字符串
        keyword = str(keyword)
        
        if not keyword.strip():
            continue
        
        for paper_keyword in paper_keywords:
            if paper_keyword is None:
                continue
            
            # 确保 paper_keyword 是字符串
            paper_keyword = str(paper_keyword)
            
            if not paper_keyword.strip():
                continue
            
            try:
                # 使用精确匹配比较
                if fuzz.ratio(keyword.lower(), paper_keyword.lower()) >= threshold:
                    return keyword, True
            except Exception as e:
                print(f"⚠️  比较 '{keyword}' 与 '{paper_keyword}' 时出错: {e}")
                continue
    
    return None, False


def check_keywords_with_text(
    keywords: List[str],
    text: Any,
    threshold: int = 85
) -> Tuple[Optional[str], bool]:
    """
    检查搜索关键词是否在文本中出现。
    
    使用部分匹配（fuzz.partial_ratio）查找关键词。
    
    Args:
        keywords: 搜索关键词列表
        text: 要搜索的文本（标题、摘要等）
        threshold: 匹配阈值（0-100），默认 85
        
    Returns:
        (matched_keyword, is_matched): 匹配的关键词和是否匹配
    """
    if text is None:
        return None, False
    
    # 确保 text 是字符串
    text = str(text)
    
    if not text.strip():
        return None, False
    
    for keyword in keywords:
        if keyword is None:
            continue
        
        # 确保 keyword 是字符串
        keyword = str(keyword)
        
        if not keyword.strip():
            continue
        
        try:
            # 使用部分匹配（关键词可能是文本的一部分）
            if fuzz.partial_ratio(keyword.lower(), text.lower()) >= threshold:
                return keyword, True
        except Exception as e:
            print(f"⚠️  在文本中搜索 '{keyword}' 时出错: {e}")
            continue
    
    return None, False


# ============ 论文过滤器 ============

def title_filter(
    paper: Any,
    keywords: List[str],
    threshold: int = 85
) -> Tuple[Optional[str], bool]:
    """
    标题过滤器：检查论文标题是否包含关键词。
    
    Args:
        paper: 论文对象（需要有 content 属性或键）
        keywords: 搜索关键词列表
        threshold: 匹配阈值（0-100），默认 85
        
    Returns:
        (matched_keyword, is_matched): 匹配的关键词和是否匹配
        
    Example:
        >>> matched, is_match = title_filter(paper, ['reinforcement learning'])
        >>> if is_match:
        ...     print(f"标题包含关键词: {matched}")
    """
    paper_title = _get_paper_field(paper, 'title')
    if paper_title is not None:
        return check_keywords_with_text(keywords, paper_title, threshold)
    return None, False


def keywords_filter(
    paper: Any,
    keywords: List[str],
    threshold: int = 85
) -> Tuple[Optional[str], bool]:
    """
    关键词过滤器：检查论文关键词是否与搜索关键词匹配。
    
    Args:
        paper: 论文对象（需要有 content 属性或键）
        keywords: 搜索关键词列表
        threshold: 匹配阈值（0-100），默认 85
        
    Returns:
        (matched_keyword, is_matched): 匹配的关键词和是否匹配
    """
    paper_keywords = _get_paper_field(paper, 'keywords')
    if paper_keywords is not None:
        return check_keywords_with_keywords(keywords, paper_keywords, threshold)
    return None, False


def abstract_filter(
    paper: Any,
    keywords: List[str],
    threshold: int = 85
) -> Tuple[Optional[str], bool]:
    """
    摘要过滤器：检查论文摘要是否包含关键词。
    
    Args:
        paper: 论文对象（需要有 content 属性或键）
        keywords: 搜索关键词列表
        threshold: 匹配阈值（0-100），默认 85
        
    Returns:
        (matched_keyword, is_matched): 匹配的关键词和是否匹配
    """
    paper_abstract = _get_paper_field(paper, 'abstract')
    if paper_abstract is not None:
        return check_keywords_with_text(keywords, paper_abstract, threshold)
    return None, False


# ============ 组合过滤 ============

def satisfies_any_filters(
    paper: Any,
    keywords: List[str],
    filters: List[Tuple[Callable, tuple, dict]]
) -> Tuple[Optional[str], Optional[str], bool]:
    """
    检查论文是否满足任意一个过滤器。
    
    Args:
        paper: 论文对象
        keywords: 搜索关键词列表
        filters: 过滤器列表，每个元素为 (filter_func, args, kwargs)
        
    Returns:
        (matched_keyword, filter_type, is_matched):
        - matched_keyword: 匹配的关键词
        - filter_type: 匹配的过滤器名称
        - is_matched: 是否匹配
        
    Example:
        >>> filters = [
        ...     (title_filter, (), {}),
        ...     (abstract_filter, (), {'threshold': 90}),
        ... ]
        >>> keyword, filter_type, matched = satisfies_any_filters(
        ...     paper, ['AI'], filters
        ... )
    """
    for filter_func, args, kwargs in filters:
        matched_keyword, matched = filter_func(paper, keywords=keywords, *args, **kwargs)
        if matched:
            filter_type = filter_func.__name__
            return matched_keyword, filter_type, True
    return None, None, False


def always_match_filter(
    paper: Any,
    keywords: List[str] = None,
    **kwargs
) -> Tuple[str, bool]:
    """
    总是匹配的过滤器，用于获取所有论文（不进行过滤）。
    
    Args:
        paper: 论文对象（不使用）
        keywords: 关键词列表（不使用）
        
    Returns:
        ("all", True): 总是返回匹配
    """
    return "all", True


# ============ 辅助函数 ============

def _get_paper_field(paper: Any, field: str) -> Any:
    """
    安全地获取论文字段值。
    
    支持以下格式：
    - OpenReview 对象: paper.content.get('field')
    - 字典: paper['content']['field'] 或 paper.get('content', {}).get('field')
    
    Args:
        paper: 论文对象或字典
        field: 字段名（在 content 下）
        
    Returns:
        字段值，如果不存在则返回 None
    """
    if paper is None:
        return None
    
    # 尝试获取 content
    content = None
    
    if isinstance(paper, dict):
        content = paper.get('content')
    else:
        try:
            content = getattr(paper, 'content', None)
        except:
            return None
    
    if content is None:
        return None
    
    # 从 content 中获取字段
    if isinstance(content, dict):
        value = content.get(field)
        # 处理 OpenReview 的 {value: "..."} 格式
        if isinstance(value, dict) and 'value' in value:
            return value['value']
        return value
    else:
        try:
            value = getattr(content, field, None)
            if isinstance(value, dict) and 'value' in value:
                return value['value']
            return value
        except:
            return None

