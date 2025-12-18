"""
网页爬取模块

从会议官网 HTML 页面获取论文元数据。
支持 AAAI、IJCAI、ACL、EMNLP 等会议。
"""

import time
import random
import csv
import os
import re
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from slugify import slugify

from .utils import to_csv


# ============ 通用工具函数 ============

# 默认 User-Agent 列表
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 '
    '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
]


def get_random_user_agent() -> str:
    """获取随机 User-Agent。"""
    return random.choice(USER_AGENTS)


def fetch_page(
    url: str,
    headers: Optional[Dict] = None,
    timeout: int = 30,
    retries: int = 3,
    delay: float = 1.0,
    verbose: bool = True
) -> Optional[str]:
    """
    获取网页内容，带重试机制。
    
    Args:
        url: 网页 URL
        headers: 请求头（可选）
        timeout: 超时时间（秒）
        retries: 重试次数
        delay: 失败后的延迟（秒）
        verbose: 是否打印日志
        
    Returns:
        网页内容（HTML 字符串），失败返回 None
    """
    if headers is None:
        headers = {
            'User-Agent': get_random_user_agent(),
        }
    
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            if verbose:
                print(f"   ⚠️  请求失败 (尝试 {attempt + 1}/{retries}): {e}")
            if attempt < retries - 1:
                time.sleep(delay * (attempt + 1))
    
    return None


def random_delay(min_sec: float = 2.0, max_sec: float = 5.0) -> None:
    """随机延迟，避免请求过快。"""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


# ============ IJCAI 爬虫 ============

def scrape_ijcai(
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    爬取 IJCAI 论文列表。
    
    Args:
        year: 会议年份（如 2024）
        output_path: 输出 CSV 路径（可选）
        verbose: 是否打印日志
        
    Returns:
        论文列表，每项包含 title, pdf_url, group, year, conference
        
    Example:
        >>> papers = scrape_ijcai(2024, output_path='ijcai_2024.csv')
        >>> len(papers)
        850
    """
    if verbose:
        print(f"\n🔍 爬取 IJCAI {year} 论文...")
    
    # IJCAI proceedings URL
    if year >= 2017:
        base_url = f'https://www.ijcai.org/proceedings/{year}/'
    elif year >= 2003:
        base_url = f'https://www.ijcai.org/Proceedings/{year}/'
    else:
        if verbose:
            print(f"   ❌ 不支持 {year} 年之前的 IJCAI")
        return []
    
    headers = {
        'User-Agent': get_random_user_agent(),
        'Referer': 'https://www.ijcai.org',
    }
    
    html = fetch_page(base_url, headers=headers, verbose=verbose)
    if not html:
        if verbose:
            print(f"   ❌ 无法获取 IJCAI {year} 页面")
        return []
    
    papers = _parse_ijcai_page(html, base_url, year, verbose)
    
    if verbose:
        print(f"   ✅ 找到 {len(papers)} 篇论文")
    
    # 保存 CSV
    if output_path and papers:
        _save_papers_csv(papers, output_path, verbose)
    
    return papers


def _parse_ijcai_page(
    html: str,
    base_url: str,
    year: int,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """解析 IJCAI 页面，提取论文信息。"""
    soup = BeautifulSoup(html, 'html.parser')
    papers = []
    
    if year >= 2017:
        # 2017+ 结构：section_title -> paper_wrapper
        sections = soup.find_all('div', {'class': 'section_title'})
        
        for section in sections:
            group = slugify(section.get_text(strip=True))
            
            # 找到同级的论文
            parent = section.parent
            if not parent:
                continue
            
            paper_wrappers = parent.find_all('div', {'class': 'paper_wrapper'})
            
            for wrapper in paper_wrappers:
                try:
                    # 标题
                    title_div = wrapper.find('div', {'class': 'title'})
                    if not title_div:
                        continue
                    title = title_div.get_text(strip=True)
                    
                    # PDF 链接
                    pdf_url = None
                    details = wrapper.find('div', {'class': 'details'})
                    if details:
                        for a in details.find_all('a'):
                            if 'PDF' in a.get_text():
                                pdf_url = urljoin(base_url, a.get('href', ''))
                                break
                    
                    papers.append({
                        'title': title,
                        'pdf_url': pdf_url or '',
                        'group': group,
                        'year': str(year),
                        'conference': 'IJCAI',
                    })
                except Exception as e:
                    if verbose:
                        print(f"   ⚠️  解析论文失败: {e}")
    else:
        # 旧版结构，简化处理
        for a in soup.find_all('a', href=True):
            href = a.get('href', '')
            if href.endswith('.pdf'):
                title = a.get_text(strip=True)
                if title:
                    papers.append({
                        'title': title,
                        'pdf_url': urljoin(base_url, href),
                        'group': '',
                        'year': str(year),
                        'conference': 'IJCAI',
                    })
    
    return papers


# ============ AAAI 爬虫 ============

def scrape_aaai(
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    爬取 AAAI 论文列表。
    
    Args:
        year: 会议年份（如 2024, 2025）
        output_path: 输出 CSV 路径（可选）
        verbose: 是否打印日志
        
    Returns:
        论文列表，每项包含 title, pdf_url, group, year, conference
        
    Example:
        >>> papers = scrape_aaai(2025, output_path='aaai_2025.csv')
    """
    if verbose:
        print(f"\n🔍 爬取 AAAI {year} 论文...")
    
    # 获取 track URLs
    track_urls = _get_aaai_track_urls(year, verbose)
    if not track_urls:
        if verbose:
            print(f"   ❌ 无法获取 AAAI {year} tracks")
        return []
    
    all_papers = []
    
    for idx, (track_name, track_url) in enumerate(track_urls.items()):
        if verbose:
            print(f"\n   📁 [{idx+1}/{len(track_urls)}] {track_name}")
        
        papers = _scrape_aaai_track(track_url, year, verbose)
        all_papers.extend(papers)
        
        if verbose:
            print(f"      找到 {len(papers)} 篇论文")
        
        # 随机延迟
        if idx < len(track_urls) - 1:
            random_delay(3, 7)
    
    if verbose:
        print(f"\n   ✅ 总计 {len(all_papers)} 篇论文")
    
    # 保存 CSV
    if output_path and all_papers:
        _save_papers_csv(all_papers, output_path, verbose)
    
    return all_papers


def _get_aaai_track_urls(year: int, verbose: bool = True) -> Dict[str, str]:
    """获取 AAAI 各 track 的 URL。"""
    track_urls = {}
    
    if year >= 2023:
        # 新版：ojs.aaai.org
        base_url = 'https://ojs.aaai.org/index.php/AAAI/issue/archive'
        headers = {
            'User-Agent': get_random_user_agent(),
            'Referer': 'https://ojs.aaai.org',
        }
        
        html = fetch_page(base_url, headers=headers, verbose=verbose)
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        issues = soup.find('ul', {'class': 'issues_archive'})
        if not issues:
            return {}
        
        for li in issues.find_all('li'):
            h2 = li.find('h2')
            if not h2 or not h2.find('a'):
                continue
            
            track_name = slugify(h2.get_text(strip=True))
            # 检查是否是指定年份
            year_short = str(year - 2000)
            if f'aaai-{year_short}' in track_name.lower():
                track_url = h2.find('a').get('href', '')
                if track_url:
                    track_urls[track_name] = track_url
    else:
        # 旧版：aaai.org
        proceeding_th = year - 1986 if year >= 2010 else year - 1979
        base_url = f'https://aaai.org/proceeding/aaai-{proceeding_th:02d}-{year}/'
        
        headers = {
            'User-Agent': get_random_user_agent(),
            'Referer': 'https://aaai.org',
        }
        
        html = fetch_page(base_url, headers=headers, verbose=verbose)
        if not html:
            return {}
        
        soup = BeautifulSoup(html, 'html.parser')
        main = soup.find('main', {'class': 'content'})
        if not main:
            return {}
        
        for li in main.find_all('li'):
            a = li.find('a')
            if a:
                track_name = slugify(a.get_text(strip=True))
                track_url = a.get('href', '')
                if track_url:
                    track_urls[track_name] = track_url
    
    return track_urls


def _scrape_aaai_track(
    track_url: str,
    year: int,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """爬取单个 AAAI track 的论文。"""
    papers = []
    
    headers = {
        'User-Agent': get_random_user_agent(),
    }
    
    html = fetch_page(track_url, headers=headers, verbose=verbose)
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    
    if year >= 2023:
        # ojs.aaai.org 结构
        sections = soup.find_all('div', {'class': 'section'})
        
        for section in sections:
            h2 = section.find('h2')
            group = slugify(h2.get_text(strip=True)) if h2 else ''
            
            for li in section.find_all('li'):
                try:
                    h3 = li.find('h3', {'class': 'title'})
                    if not h3:
                        continue
                    title = h3.get_text(strip=True)
                    
                    pdf_link = li.find('a', {'class': 'obj_galley_link'})
                    pdf_url = ''
                    if pdf_link:
                        pdf_url = pdf_link.get('href', '').replace('view', 'download')
                    
                    papers.append({
                        'title': title,
                        'pdf_url': pdf_url,
                        'group': group,
                        'year': str(year),
                        'conference': 'AAAI',
                    })
                except Exception:
                    pass
    else:
        # aaai.org 结构
        tracks = soup.find_all('div', {'class': 'track-wrap'})
        
        for track in tracks:
            h2 = track.find('h2')
            group = slugify(h2.get_text(strip=True)) if h2 else ''
            
            for li in track.find_all('li'):
                try:
                    h5 = li.find('h5')
                    if not h5:
                        continue
                    title = h5.get_text(strip=True)
                    
                    pdf_link = li.find('a', {'class': 'wp-block-button'})
                    pdf_url = pdf_link.get('href', '') if pdf_link else ''
                    
                    papers.append({
                        'title': title,
                        'pdf_url': pdf_url,
                        'group': group,
                        'year': str(year),
                        'conference': 'AAAI',
                    })
                except Exception:
                    pass
    
    return papers


# ============ AISTATS 爬虫 (PMLR) ============

# AISTATS 年份到 PMLR volume 的映射
AISTATS_VOLUMES = {
    2025: 258, 2024: 238, 2023: 206, 2022: 151, 2021: 130,
    2020: 108, 2019: 89, 2018: 84, 2017: 54, 2016: 51,
    2015: 38, 2014: 33, 2013: 31, 2012: 22, 2011: 15,
    2010: 9, 2009: 5, 2007: 2,
}


def scrape_aistats(
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    爬取 AISTATS 论文列表（从 PMLR）。
    
    Args:
        year: 会议年份（如 2024）
        output_path: 输出 CSV 路径（可选）
        verbose: 是否打印日志
        
    Returns:
        论文列表
        
    Example:
        >>> papers = scrape_aistats(2024, output_path='aistats_2024.csv')
    """
    if verbose:
        print(f"\n🔍 爬取 AISTATS {year} 论文 (PMLR)...")
    
    if year not in AISTATS_VOLUMES:
        if verbose:
            print(f"   ❌ 不支持 AISTATS {year}")
        return []
    
    volume = AISTATS_VOLUMES[year]
    papers = scrape_pmlr(f'v{volume}', 'AISTATS', year, verbose)
    
    if verbose:
        print(f"   ✅ 找到 {len(papers)} 篇论文")
    
    if output_path and papers:
        _save_papers_csv(papers, output_path, verbose)
    
    return papers


def scrape_pmlr(
    volume: str,
    conference: str,
    year: int,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    从 PMLR (Proceedings of Machine Learning Research) 爬取论文。
    
    Args:
        volume: PMLR volume，如 'v238'
        conference: 会议名称
        year: 年份
        verbose: 是否打印日志
        
    Returns:
        论文列表
    """
    base_url = f'https://proceedings.mlr.press/{volume}/'
    
    headers = {
        'User-Agent': get_random_user_agent(),
    }
    
    html = fetch_page(base_url, headers=headers, verbose=verbose)
    if not html:
        return []
    
    soup = BeautifulSoup(html, 'html.parser')
    paper_divs = soup.find_all('div', {'class': 'paper'})
    
    papers = []
    for div in paper_divs:
        try:
            # 标题
            title_p = div.find('p', {'class': 'title'})
            if not title_p:
                continue
            title = title_p.get_text(strip=True)
            
            # PDF 链接
            pdf_url = ''
            links_p = div.find('p', {'class': 'links'})
            if links_p:
                for a in links_p.find_all('a'):
                    text = a.get_text(strip=True).lower()
                    if 'pdf' in text or 'download' in text:
                        pdf_url = a.get('href', '')
                        break
            
            papers.append({
                'title': title,
                'pdf_url': pdf_url,
                'group': '',
                'year': str(year),
                'conference': conference,
            })
        except Exception:
            pass
    
    return papers


# ============ ACL Anthology 爬虫 ============

def scrape_acl_anthology(
    conference: str,
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    从 ACL Anthology 爬取论文列表。
    
    支持 ACL, EMNLP, NAACL, EACL, COLING 等会议。
    
    Args:
        conference: 会议名称 ('ACL', 'EMNLP', 'NAACL' 等)
        year: 会议年份
        output_path: 输出 CSV 路径
        verbose: 是否打印日志
        
    Returns:
        论文列表
        
    Example:
        >>> papers = scrape_acl_anthology('ACL', 2023)
    """
    if verbose:
        print(f"\n🔍 爬取 {conference} {year} 论文 (ACL Anthology)...")
    
    # ACL Anthology 的会议代码映射
    conf_codes = {
        'ACL': 'acl',
        'EMNLP': 'emnlp',
        'NAACL': 'naacl',
        'EACL': 'eacl',
        'COLING': 'coling',
        'FINDINGS': 'findings',
    }
    
    conf_upper = conference.upper()
    if conf_upper not in conf_codes:
        if verbose:
            print(f"   ❌ 不支持的会议: {conference}")
        return []
    
    code = conf_codes[conf_upper]
    
    # ACL Anthology URL 格式
    # 主会议: https://aclanthology.org/events/acl-2023/
    base_url = f'https://aclanthology.org/events/{code}-{year}/'
    
    headers = {
        'User-Agent': get_random_user_agent(),
    }
    
    html = fetch_page(base_url, headers=headers, verbose=verbose)
    if not html:
        if verbose:
            print(f"   ❌ 无法获取 {conference} {year} 页面")
        return []
    
    papers = _parse_acl_anthology_page(html, conf_upper, year, verbose)
    
    if verbose:
        print(f"   ✅ 找到 {len(papers)} 篇论文")
    
    if output_path and papers:
        _save_papers_csv(papers, output_path, verbose)
    
    return papers


def _parse_acl_anthology_page(
    html: str,
    conference: str,
    year: int,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """解析 ACL Anthology 页面。"""
    soup = BeautifulSoup(html, 'html.parser')
    papers = []
    
    # 查找所有论文条目
    # ACL Anthology 使用 <p class="d-sm-flex align-items-stretch"> 包装论文
    paper_entries = soup.find_all('p', {'class': 'd-sm-flex'})
    
    for entry in paper_entries:
        try:
            # 查找标题链接
            title_span = entry.find('span', {'class': 'd-block'})
            if not title_span:
                continue
            
            title_link = title_span.find('a', {'class': 'align-middle'})
            if not title_link:
                continue
            
            title = title_link.get_text(strip=True)
            paper_url = title_link.get('href', '')
            
            # PDF 链接通常是 paper_url + .pdf
            pdf_url = ''
            if paper_url:
                # 从论文页面 URL 构造 PDF URL
                # https://aclanthology.org/2023.acl-long.1/ -> https://aclanthology.org/2023.acl-long.1.pdf
                pdf_url = f'https://aclanthology.org{paper_url}'.rstrip('/') + '.pdf'
            
            papers.append({
                'title': title,
                'pdf_url': pdf_url,
                'group': '',
                'year': str(year),
                'conference': conference,
            })
        except Exception:
            pass
    
    return papers


def scrape_acl(
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """爬取 ACL 论文。"""
    return scrape_acl_anthology('ACL', year, output_path, verbose)


def scrape_emnlp(
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """爬取 EMNLP 论文。"""
    return scrape_acl_anthology('EMNLP', year, output_path, verbose)


def scrape_naacl(
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """爬取 NAACL 论文。"""
    return scrape_acl_anthology('NAACL', year, output_path, verbose)


# ============ 通用保存函数 ============

def _save_papers_csv(
    papers: List[Dict[str, Any]],
    output_path: str,
    verbose: bool = True
) -> None:
    """保存论文列表到 CSV。"""
    if not papers:
        return
    
    # 确保目录存在
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    # 转换格式以适配 to_csv
    papers_for_csv = []
    for idx, p in enumerate(papers):
        papers_for_csv.append({
            'id': f"{p.get('conference', 'CONF')}_{p.get('year', '')}_{idx+1:04d}",
            'title': p.get('title', ''),
            'pdf': p.get('pdf_url', ''),
            'group': p.get('group', ''),
            'year': p.get('year', ''),
            'conference': p.get('conference', ''),
            'keywords': '',
            'abstract': '',
        })
    
    to_csv(papers_for_csv, output_path)
    
    if verbose:
        print(f"   💾 已保存到 {output_path}")


# ============ 统一入口 ============

def scrape_conference(
    conference: str,
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    统一的会议爬取入口。
    
    Args:
        conference: 会议名称（'AAAI', 'IJCAI' 等）
        year: 会议年份
        output_path: 输出路径（可选）
        verbose: 是否打印日志
        
    Returns:
        论文列表
        
    Example:
        >>> papers = scrape_conference('IJCAI', 2024)
    """
    conference = conference.upper()
    
    scrapers = {
        'IJCAI': scrape_ijcai,
        'AAAI': scrape_aaai,
        'AISTATS': scrape_aistats,
        'ACL': scrape_acl,
        'EMNLP': scrape_emnlp,
        'NAACL': scrape_naacl,
    }
    
    if conference not in scrapers:
        supported = ', '.join(sorted(scrapers.keys()))
        raise ValueError(f"不支持的会议: {conference}。支持: {supported}")
    
    return scrapers[conference](year, output_path, verbose)


# ============ 批量爬取 ============

def batch_scrape(
    conferences: List[str],
    years: List[int],
    output_dir: str = './output',
    verbose: bool = True
) -> Dict[str, List[Dict[str, Any]]]:
    """
    批量爬取多个会议。
    
    Args:
        conferences: 会议名称列表
        years: 年份列表
        output_dir: 输出目录
        verbose: 是否打印日志
        
    Returns:
        {会议_年份: 论文列表} 字典
        
    Example:
        >>> results = batch_scrape(['IJCAI', 'AAAI'], [2023, 2024])
    """
    os.makedirs(output_dir, exist_ok=True)
    results = {}
    
    for conf in conferences:
        for year in years:
            key = f"{conf}_{year}"
            output_path = os.path.join(output_dir, f"{key}.csv")
            
            if verbose:
                print(f"\n{'='*50}")
                print(f"📚 爬取 {conf} {year}")
                print(f"{'='*50}")
            
            try:
                papers = scrape_conference(conf, year, output_path, verbose)
                results[key] = papers
            except Exception as e:
                if verbose:
                    print(f"   ❌ 爬取失败: {e}")
                results[key] = []
            
            # 会议间延迟
            random_delay(5, 10)
    
    return results

