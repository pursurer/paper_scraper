"""
PDF 元数据提取模块

从 PDF 文件中提取论文的 abstract、keywords 等元数据。
主要用于 AAMAS 等需要从 PDF 获取信息的会议。
"""

import os
import re
import csv
from typing import Dict, List, Optional, Tuple, Any

from .utils import to_csv

# 尝试导入 PDF 库
_PDF_LIBRARY = None
try:
    # PyMuPDF 1.24.3+ 的模块名；旧名 fitz 已弃用，将被移除
    import pymupdf
    _PDF_LIBRARY = 'pymupdf'
except ImportError:
    try:
        import fitz as pymupdf  # 更早的 PyMuPDF 只有 fitz 这个名字
        _PDF_LIBRARY = 'pymupdf'
    except ImportError:
        try:
            from pdfminer.high_level import extract_text as pdfminer_extract
            _PDF_LIBRARY = 'pdfminer'
        except ImportError:
            pass


def get_pdf_library() -> Optional[str]:
    """获取当前可用的 PDF 库。"""
    return _PDF_LIBRARY


def is_pdf_available() -> bool:
    """检查是否有可用的 PDF 库。"""
    return _PDF_LIBRARY is not None


# ============ 文本提取 ============

def extract_text_from_pdf(pdf_path: str) -> str:
    """
    从 PDF 文件中提取文本内容。
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        提取的文本内容，失败返回空字符串
    """
    if not is_pdf_available():
        return ''
    
    if not os.path.exists(pdf_path):
        return ''
    
    try:
        if _PDF_LIBRARY == 'pymupdf':
            doc = pymupdf.open(pdf_path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        elif _PDF_LIBRARY == 'pdfminer':
            from pdfminer.high_level import extract_text as pdfminer_extract
            return pdfminer_extract(pdf_path)
    except Exception:
        pass
    
    return ''


# ============ Abstract 提取 ============

# Abstract 匹配模式
ABSTRACT_PATTERNS = [
    r'Abstract\s*\n\s*([^\n]+(?:\n(?!\s*(?:Keywords?|Introduction|1\.|I\.|§))[^\n]+)*)',
    r'ABSTRACT\s*\n\s*([^\n]+(?:\n(?!\s*(?:Keywords?|Introduction|1\.|I\.|§))[^\n]+)*)',
    r'Abstract\.?\s*\n\s*([^\n]+(?:\n(?!\s*(?:Keywords?|Introduction|1\.|I\.|§))[^\n]+)*)',
]


def extract_abstract(text: str, max_length: int = 2000) -> Optional[str]:
    """
    从文本中提取 abstract。
    
    Args:
        text: PDF 提取的文本
        max_length: 最大长度限制
        
    Returns:
        提取的 abstract，失败返回 None
    """
    if not text:
        return None
    
    for pattern in ABSTRACT_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            abstract = match.group(1).strip()
            # 清理：移除多余空白
            abstract = re.sub(r'\s+', ' ', abstract)
            # 如果太长，截断到前几句
            if len(abstract) > max_length:
                sentences = abstract.split('.')
                abstract = '. '.join(sentences[:5])
            return abstract[:max_length]
    
    return None


# ============ Keywords 提取 ============

# Keywords 匹配模式
KEYWORDS_PATTERNS = [
    r'Keywords?[:\s]+\n?\s*([^\n]+(?:\n(?!\s*(?:Introduction|1\.|I\.|§|Abstract))[^\n]+)*)',
    r'KEYWORDS?[:\s]+\n?\s*([^\n]+(?:\n(?!\s*(?:Introduction|1\.|I\.|§|Abstract))[^\n]+)*)',
]


def extract_keywords(text: str, max_length: int = 500) -> Optional[str]:
    """
    从文本中提取 keywords。
    
    Args:
        text: PDF 提取的文本
        max_length: 最大长度限制
        
    Returns:
        提取的 keywords，失败返回 None
    """
    if not text:
        return None
    
    for pattern in KEYWORDS_PATTERNS:
        match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE | re.DOTALL)
        if match:
            keywords = match.group(1).strip()
            # 清理：移除多余空白
            keywords = re.sub(r'\s+', ' ', keywords)
            # 如果太长，截断到第一个分隔符
            if len(keywords) > max_length:
                for sep in [';', '.', '\n']:
                    if sep in keywords:
                        keywords = keywords.split(sep)[0]
                        break
            return keywords[:max_length]
    
    return None


# ============ 标题提取 ============

def extract_title(text: str, max_length: int = 300) -> Optional[str]:
    """
    从文本中提取论文标题（通常是第一行或前几行）。
    
    Args:
        text: PDF 提取的文本
        max_length: 最大长度限制
        
    Returns:
        提取的标题，失败返回 None
    """
    if not text:
        return None
    
    # 取前几行，尝试找到标题
    lines = text.strip().split('\n')
    
    # 跳过空行和短行
    for line in lines[:10]:
        line = line.strip()
        # 跳过空行、太短或太长的行
        if len(line) < 5 or len(line) > max_length:
            continue
        # 跳过明显不是标题的行（如作者、机构等）
        if '@' in line or 'University' in line or 'Institute' in line:
            continue
        # 跳过页码、日期等
        if re.match(r'^\d+$', line) or re.match(r'^\d{4}[-/]\d{1,2}', line):
            continue
        return line
    
    return None


# ============ PDF 处理 ============

def process_pdf(pdf_path: str) -> Dict[str, Optional[str]]:
    """
    处理单个 PDF 文件，提取所有元数据。
    
    Args:
        pdf_path: PDF 文件路径
        
    Returns:
        包含 title, abstract, keywords 的字典
    """
    text = extract_text_from_pdf(pdf_path)
    
    return {
        'title': extract_title(text),
        'abstract': extract_abstract(text),
        'keywords': extract_keywords(text),
    }


def process_pdf_directory(
    pdf_dir: str,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    处理目录中的所有 PDF 文件。
    
    Args:
        pdf_dir: PDF 文件目录
        output_path: 输出 CSV 路径（可选）
        verbose: 是否打印日志
        
    Returns:
        提取的论文列表
    """
    if not os.path.isdir(pdf_dir):
        if verbose:
            print(f"   ❌ 目录不存在: {pdf_dir}")
        return []
    
    if not is_pdf_available():
        if verbose:
            print("   ❌ 未安装 PDF 库，请安装: pip install PyMuPDF")
        return []
    
    # 获取所有 PDF 文件
    pdf_files = [f for f in os.listdir(pdf_dir) if f.lower().endswith('.pdf')]
    pdf_files.sort()
    
    if verbose:
        print(f"\n🔍 处理 PDF 目录: {pdf_dir}")
        print(f"   找到 {len(pdf_files)} 个 PDF 文件")
    
    papers = []
    for idx, pdf_file in enumerate(pdf_files):
        pdf_path = os.path.join(pdf_dir, pdf_file)
        
        if verbose:
            print(f"   [{idx+1}/{len(pdf_files)}] {pdf_file[:50]}...")
        
        metadata = process_pdf(pdf_path)
        
        papers.append({
            'title': metadata['title'] or os.path.splitext(pdf_file)[0],
            'abstract': metadata['abstract'] or '',
            'keywords': metadata['keywords'] or '',
            'pdf_path': pdf_path,
            'pdf_file': pdf_file,
        })
    
    if verbose:
        with_abstract = sum(1 for p in papers if p['abstract'])
        with_keywords = sum(1 for p in papers if p['keywords'])
        print(f"\n   ✅ 处理完成!")
        print(f"      成功提取 abstract: {with_abstract}/{len(papers)}")
        print(f"      成功提取 keywords: {with_keywords}/{len(papers)}")
    
    if output_path and papers:
        _save_extracted_csv(papers, output_path, verbose)
    
    return papers


# ============ AAMAS 专用 ============

def extract_aamas_metadata(
    pdf_dir: str,
    year: int,
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    从 AAMAS PDF 目录提取论文元数据。
    
    Args:
        pdf_dir: 包含 AAMAS PDF 的目录
        year: 会议年份
        output_path: 输出 CSV 路径（可选）
        verbose: 是否打印日志
        
    Returns:
        论文列表
        
    Example:
        >>> papers = extract_aamas_metadata('./aamas2025/', 2025)
    """
    if verbose:
        print(f"\n🔍 提取 AAMAS {year} 论文元数据...")
    
    papers = process_pdf_directory(pdf_dir, verbose=verbose)
    
    # 添加 AAMAS 特定字段
    for idx, paper in enumerate(papers):
        paper['conference'] = 'AAMAS'
        paper['year'] = str(year)
        paper['id'] = f"AAMAS_{year}_{idx+1:04d}"
        paper['group'] = ''
    
    if output_path and papers:
        _save_aamas_csv(papers, output_path, verbose)
    
    return papers


def _save_extracted_csv(
    papers: List[Dict[str, Any]],
    output_path: str,
    verbose: bool = True
) -> None:
    """保存提取的论文到 CSV。"""
    if not papers:
        return
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    
    fieldnames = ['title', 'abstract', 'keywords', 'pdf_file', 'pdf_path']
    
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for paper in papers:
            row = {k: paper.get(k, '') for k in fieldnames}
            writer.writerow(row)
    
    if verbose:
        print(f"   💾 已保存到 {output_path}")


def _save_aamas_csv(
    papers: List[Dict[str, Any]],
    output_path: str,
    verbose: bool = True
) -> None:
    """保存 AAMAS 论文到统一格式 CSV。"""
    if not papers:
        return
    
    # 转换为统一格式
    papers_for_csv = []
    for paper in papers:
        papers_for_csv.append({
            'id': paper.get('id', ''),
            'title': paper.get('title', ''),
            'keywords': paper.get('keywords', ''),
            'abstract': paper.get('abstract', ''),
            'pdf': paper.get('pdf_path', ''),
            'forum': '',
            'year': paper.get('year', ''),
            'group': paper.get('group', ''),
            'conference': paper.get('conference', 'AAMAS'),
        })
    
    to_csv(papers_for_csv, output_path)
    
    if verbose:
        print(f"   💾 已保存到 {output_path}")


# ============ 从索引文件处理 ============

def process_from_index(
    index_file: str,
    pdf_column: str = 'pdf_local_path',
    output_path: Optional[str] = None,
    verbose: bool = True
) -> List[Dict[str, Any]]:
    """
    从索引 CSV 文件读取 PDF 路径并提取元数据。
    
    Args:
        index_file: 索引 CSV 文件路径
        pdf_column: PDF 路径所在的列名
        output_path: 输出 CSV 路径
        verbose: 是否打印日志
        
    Returns:
        带有元数据的论文列表
    """
    if not os.path.exists(index_file):
        if verbose:
            print(f"   ❌ 索引文件不存在: {index_file}")
        return []
    
    if not is_pdf_available():
        if verbose:
            print("   ❌ 未安装 PDF 库，请安装: pip install PyMuPDF")
        return []
    
    # 读取索引
    papers = []
    with open(index_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        papers = list(reader)
    
    if verbose:
        print(f"\n🔍 从索引文件处理: {index_file}")
        print(f"   找到 {len(papers)} 篇论文")
    
    base_dir = os.path.dirname(index_file)
    
    results = []
    for idx, paper in enumerate(papers):
        pdf_path = paper.get(pdf_column, '')
        
        # 处理相对路径
        if pdf_path and not os.path.isabs(pdf_path):
            pdf_path = os.path.join(base_dir, pdf_path)
        
        if verbose:
            title = paper.get('title', pdf_path)[:50]
            print(f"   [{idx+1}/{len(papers)}] {title}...")
        
        metadata = process_pdf(pdf_path) if pdf_path else {}
        
        result = paper.copy()
        result['abstract'] = metadata.get('abstract') or paper.get('abstract', '')
        result['keywords'] = metadata.get('keywords') or paper.get('keywords', '')
        results.append(result)
    
    if verbose:
        with_abstract = sum(1 for r in results if r.get('abstract'))
        with_keywords = sum(1 for r in results if r.get('keywords'))
        print(f"\n   ✅ 处理完成!")
        print(f"      成功提取 abstract: {with_abstract}/{len(results)}")
        print(f"      成功提取 keywords: {with_keywords}/{len(results)}")
    
    if output_path:
        _save_extracted_csv(results, output_path, verbose)
    
    return results

