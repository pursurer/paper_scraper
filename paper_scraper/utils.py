"""
工具函数模块

提供通用的工具函数：
- API 客户端获取和重试机制
- CSV 导出（带去重、清理换行符）
- PKL 序列化/反序列化
"""

import csv
import os
import time
import json
from functools import wraps
from typing import List, Dict, Any, Callable, Optional
from datetime import datetime

import dill


# ============ 重试机制 ============

def retry_with_backoff(
    max_retries: int = 5,
    initial_delay: float = 1,
    max_delay: float = 60,
    backoff_factor: float = 2
) -> Callable:
    """
    装饰器：为函数添加重试机制和指数退避策略，特别处理 429 错误（API 限流）
    
    Args:
        max_retries: 最大重试次数
        initial_delay: 初始延迟（秒）
        max_delay: 最大延迟（秒）
        backoff_factor: 退避因子（每次重试延迟乘以这个因子）
        
    Returns:
        装饰后的函数
        
    Example:
        @retry_with_backoff(max_retries=3, initial_delay=2)
        def my_api_call():
            return requests.get(url)
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = initial_delay
            last_exception = None
            
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    error_str = str(e)
                    
                    # 检查是否是 429 错误（API 限流）
                    is_rate_limit = (
                        '429' in error_str or 
                        'Too Many Requests' in error_str or 
                        'rate limit' in error_str.lower()
                    )
                    
                    if attempt < max_retries - 1:  # 不是最后一次尝试
                        if is_rate_limit:
                            # 对于 429 错误，使用更长的延迟
                            wait_time = min(delay * 2, max_delay)
                            print(f"⚠️  API 限流（429 错误），等待 {wait_time} 秒后重试... "
                                  f"(尝试 {attempt + 1}/{max_retries})")
                        else:
                            wait_time = delay
                            print(f"⚠️  请求失败，等待 {wait_time} 秒后重试... "
                                  f"(尝试 {attempt + 1}/{max_retries})")
                            print(f"   错误信息: {error_str[:100]}")
                        
                        time.sleep(wait_time)
                        delay = min(delay * backoff_factor, max_delay)
                    else:
                        # 最后一次尝试也失败了
                        print(f"❌ 请求失败，已达到最大重试次数 ({max_retries})")
                        print(f"   最后错误: {error_str}")
                        raise last_exception
            
            # 理论上不会到达这里，但为了安全起见
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def safe_api_call(func: Callable, *args, **kwargs) -> Any:
    """
    安全地调用 API 函数，带重试机制
    
    Args:
        func: 要调用的函数
        *args, **kwargs: 传递给函数的参数
    
    Returns:
        函数返回值
        
    Example:
        result = safe_api_call(client.get_all_notes, content={'venueid': venue})
    """
    @retry_with_backoff(max_retries=5, initial_delay=2, max_delay=120)
    def _call():
        return func(*args, **kwargs)
    
    return _call()


# ============ OpenReview API 客户端 ============

def get_client():
    """
    获取 OpenReview API v2 客户端。
    使用重试机制处理登录时的 API 限流。
    
    Returns:
        OpenReview API v2 客户端实例
        
    Raises:
        ImportError: 如果 openreview 包未安装
        Exception: 如果登录失败
    """
    try:
        import openreview
    except ImportError:
        raise ImportError(
            "openreview-py 未安装。请运行: pip install openreview-py"
        )
    
    # 从新配置系统获取凭证
    email = None
    password = None
    
    try:
        from config import get_config
        config = get_config()
        email = config.openreview_email
        password = config.openreview_password
    except ImportError:
        pass
    
    # 向后兼容：如果配置系统未设置，尝试环境变量
    if not email or not password:
        email = os.environ.get("OPENREVIEW_EMAIL") or email
        password = os.environ.get("OPENREVIEW_PASSWORD") or password
    
    if not email or not password:
        raise ValueError(
            "未找到 OpenReview 凭证。请设置环境变量 OPENREVIEW_EMAIL 和 OPENREVIEW_PASSWORD，"
            "或创建 config/config.py 文件。"
        )
    
    @retry_with_backoff(max_retries=5, initial_delay=5, max_delay=120, backoff_factor=2)
    def _create_client_v2():
        return openreview.api.OpenReviewClient(
            baseurl='https://api2.openreview.net',
            username=email,
            password=password
        )
    
    print("🔄 正在登录 OpenReview API v2...")
    client = _create_client_v2()
    print("✅ API v2 登录成功")
    
    return client


# ============ 数据转换 ============

def papers_to_list(papers: Dict) -> List[Dict]:
    """
    将嵌套的论文字典转换为扁平列表。
    
    Args:
        papers: 嵌套字典，格式为 {group: {venue: [paper, ...]}}
        
    Returns:
        论文列表
    """
    all_papers = []
    for grouped_venues in papers.values():
        for venue_papers in grouped_venues.values():
            for paper in venue_papers:
                all_papers.append(paper)
    return all_papers


# ============ CSV 导出 ============

# 默认 CSV 字段（按顺序）
DEFAULT_CSV_FIELDS = [
    'id', 'title', 'keywords', 'abstract', 
    'pdf', 'forum', 'year', 'presentation_type'
]

# 需要清理换行符的文本字段
TEXT_FIELDS_TO_CLEAN = ['abstract', 'title', 'keywords']


def _clean_value(value: Any) -> str:
    """
    清理字段值，确保是字符串且没有 None。
    
    Args:
        value: 任意类型的值
        
    Returns:
        清理后的字符串
    """
    if value is None:
        return ''
    if isinstance(value, (dict, list)):
        try:
            return json.dumps(value, ensure_ascii=False)
        except:
            return str(value)
    return str(value)


def _clean_text_field(value: str) -> str:
    """
    清理文本字段中的换行符。
    
    Args:
        value: 文本字符串
        
    Returns:
        清理后的字符串（换行符替换为空格）
    """
    if not isinstance(value, str):
        return value
    # 将换行符替换为空格
    cleaned = value.replace('\n', ' ').replace('\r', ' ')
    # 将多个连续空格替换为单个空格
    while '  ' in cleaned:
        cleaned = cleaned.replace('  ', ' ')
    return cleaned.strip()


def _extract_forum_id(forum: str) -> Optional[str]:
    """
    从 forum 字段提取论文 ID（可能是完整 URL）。
    
    Args:
        forum: forum 字段值
        
    Returns:
        提取的 ID 或 None
    """
    if not isinstance(forum, str) or not forum.strip():
        return None
    
    # 如果是 URL，提取 ID 部分
    if 'forum?id=' in forum:
        return forum.split('forum?id=')[-1].split('&')[0]
    elif '/' in forum and len(forum) > 20:
        return forum.split('/')[-1].split('?')[0]
    else:
        return forum.strip()


def to_csv(
    papers_list: List[Dict],
    fpath: str,
    fields: List[str] = None,
    append: bool = True
) -> None:
    """
    将论文列表写入 CSV 文件。
    
    功能特性：
    - 自动去重（基于 forum 字段或 title+year）
    - 清理换行符和特殊字符
    - 支持追加模式（合并现有数据）
    - 自动生成唯一 ID
    - UTF-8 BOM 编码（Excel 友好）
    - 按展示类型排序（Oral > Spotlight > Poster）
    
    Args:
        papers_list: 论文字典列表
        fpath: 输出 CSV 文件路径
        fields: 要保留的字段列表，默认使用 DEFAULT_CSV_FIELDS
        append: 是否追加到现有文件（默认 True）
    """
    if fields is None:
        fields = DEFAULT_CSV_FIELDS.copy()
    
    # 从文件路径提取会议名称（用于生成 ID）
    filename = os.path.basename(fpath)
    if '_papers.csv' in filename:
        conference_name = filename.replace('_papers.csv', '').lower()
    elif '.csv' in filename:
        conference_name = filename.replace('.csv', '').lower()
    else:
        conference_name = None
    
    # 如果论文列表为空，创建带表头的空 CSV 文件
    if len(papers_list) == 0:
        with open(fpath, 'w', encoding='utf-8-sig', newline='') as fp:
            writer = csv.DictWriter(
                fp,
                fieldnames=fields,
                quoting=csv.QUOTE_MINIMAL,
                doublequote=True,
                lineterminator='\n'
            )
            writer.writeheader()
        print(f"✅ 已创建空 CSV 文件（带表头）: {fpath}")
        return
    
    # 读取现有数据（如果文件存在且 append=True）
    existing_papers = []
    if append and os.path.exists(fpath):
        try:
            with open(fpath, 'r', encoding='utf-8-sig', newline='') as fp:
                reader = csv.DictReader(fp)
                existing_papers = list(reader)
        except Exception as e:
            print(f"⚠️  无法读取现有文件 {fpath}，将创建新文件: {e}")
            existing_papers = []
    
    # 合并数据（新数据优先）
    all_papers = papers_list + existing_papers
    
    # 去重
    seen_ids = set()
    unique_papers = []
    duplicates_count = 0
    
    for paper in all_papers:
        # 清理字段值
        cleaned_paper = {}
        for key, value in paper.items():
            cleaned_value = _clean_value(value)
            if key in TEXT_FIELDS_TO_CLEAN:
                cleaned_value = _clean_text_field(cleaned_value)
            cleaned_paper[key] = cleaned_value
        
        # 提取唯一标识
        forum_id = _extract_forum_id(cleaned_paper.get('forum', ''))
        
        if forum_id:
            unique_id = forum_id
        else:
            # 使用 title + year 作为备选标识
            title = cleaned_paper.get('title', '').strip()
            year = cleaned_paper.get('year', '').strip()
            unique_id = f"{title}|{year}"
        
        if unique_id not in seen_ids:
            seen_ids.add(unique_id)
            unique_papers.append(cleaned_paper)
        else:
            duplicates_count += 1
    
    if duplicates_count > 0:
        print(f"📊 去重: 移除了 {duplicates_count} 条重复记录")
    
    print(f"📊 唯一论文数: {len(unique_papers)}")
    
    # 按展示类型排序
    presentation_priority = {'Oral': 0, 'Spotlight': 1, 'Poster': 2}
    
    def sort_key(paper):
        ptype = paper.get('presentation_type', 'Poster')
        priority = presentation_priority.get(ptype, 3)
        title = paper.get('title', '')
        return (priority, title.lower())
    
    unique_papers.sort(key=sort_key)
    
    # 生成唯一 ID
    if conference_name:
        for idx, paper in enumerate(unique_papers, start=1):
            paper['id'] = f"{conference_name}_{idx}"
    
    # 写入 CSV
    with open(fpath, 'w', encoding='utf-8-sig', newline='') as fp:
        writer = csv.DictWriter(
            fp,
            fieldnames=fields,
            quoting=csv.QUOTE_MINIMAL,
            doublequote=True,
            lineterminator='\n'
        )
        writer.writeheader()
        
        for paper in unique_papers:
            row = {field: paper.get(field, '') for field in fields}
            writer.writerow(row)
    
    if conference_name:
        print(f"✅ 已为论文添加唯一 ID（格式: {conference_name}_序号）")
    
    print(f"✅ CSV 文件已保存: {fpath}")


# ============ PKL 序列化 ============

def save_papers(papers: Any, fpath: str) -> None:
    """
    将论文数据保存为 PKL 文件。
    
    Args:
        papers: 要保存的论文数据（任意 Python 对象）
        fpath: 输出文件路径
    """
    with open(fpath, 'wb') as fp:
        dill.dump(papers, fp)
    print(f"✅ Papers saved at: {fpath}")


def load_papers(fpath: str) -> Any:
    """
    从 PKL 文件加载论文数据。
    
    Args:
        fpath: PKL 文件路径
        
    Returns:
        加载的论文数据
    """
    with open(fpath, 'rb') as fp:
        papers = dill.load(fp)
    print(f"✅ Papers loaded from: {fpath}")
    return papers

