"""
Paper Scraper CLI 入口

支持通过 python -m paper_scraper 调用。

Usage:
    # OpenReview 来源
    python -m paper_scraper --conference ICLR --year 2024 --output iclr_2024.csv
    
    # 网页爬取来源
    python -m paper_scraper --conference IJCAI --year 2024 --output ijcai_2024.csv
    
    # PDF 提取
    python -m paper_scraper --pdf-dir ./aamas2025 --year 2025 --output aamas_2025.csv
    
    # 批量爬取
    python -m paper_scraper --conferences ICLR ICML --years 2023 2024 --output-dir ./output
"""

import argparse
import sys
import os

from . import (
    __version__,
    SOURCES,
    Scraper,
    Extractor,
    scrape_conference,
    batch_scrape,
    extract_aamas_metadata,
    is_pdf_available,
)


def get_source_type(conference: str) -> str:
    """获取会议的数据源类型。"""
    conf_upper = conference.upper()
    for source_type, conferences in SOURCES.items():
        # 大小写不敏感比较
        if conf_upper in [c.upper() for c in conferences]:
            return source_type
    return 'unknown'


def create_parser() -> argparse.ArgumentParser:
    """创建命令行参数解析器。"""
    parser = argparse.ArgumentParser(
        prog='paper_scraper',
        description='顶会论文获取工具 - 支持 OpenReview、网页爬取、PDF 提取',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 爬取 ICLR 2024 (OpenReview)
  python -m paper_scraper -c ICLR -y 2024 -o iclr_2024.csv

  # 爬取 IJCAI 2024 (网页爬取)
  python -m paper_scraper -c IJCAI -y 2024 -o ijcai_2024.csv

  # 批量爬取多个会议
  python -m paper_scraper -c ICLR ICML -y 2023 2024 --output-dir ./output

  # 从 PDF 提取 AAMAS 元数据
  python -m paper_scraper --pdf-dir ./aamas2025 -y 2025 -o aamas_2025.csv

  # 带关键词过滤
  python -m paper_scraper -c ICLR -y 2024 -k "reinforcement learning" -o rl_papers.csv

支持的会议:
  OpenReview: ICLR, ICML, NeurIPS
  网页爬取: AAAI, IJCAI, ACL, EMNLP, NAACL, AISTATS
  PDF 提取: AAMAS
        """
    )
    
    # 版本信息
    parser.add_argument(
        '-v', '--version',
        action='version',
        version=f'paper_scraper {__version__}'
    )
    
    # 会议选项
    parser.add_argument(
        '-c', '--conference', '--conferences',
        nargs='+',
        dest='conferences',
        help='会议名称（可指定多个）'
    )
    
    # 年份选项
    parser.add_argument(
        '-y', '--year', '--years',
        nargs='+',
        dest='years',
        help='年份（可指定多个）'
    )
    
    # 输出选项
    parser.add_argument(
        '-o', '--output',
        help='输出 CSV 文件路径'
    )
    
    parser.add_argument(
        '--output-dir',
        help='批量输出目录（与 --output 互斥）'
    )
    
    # 关键词过滤
    parser.add_argument(
        '-k', '--keywords',
        nargs='+',
        default=[],
        help='过滤关键词（可指定多个）'
    )
    
    # PDF 提取选项
    parser.add_argument(
        '--pdf-dir',
        help='PDF 目录路径（用于 AAMAS 等 PDF 提取）'
    )
    
    # 其他选项
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='安静模式，减少输出'
    )
    
    parser.add_argument(
        '--list-conferences',
        action='store_true',
        help='列出所有支持的会议'
    )
    
    return parser


def list_conferences() -> None:
    """列出所有支持的会议。"""
    print("\n📚 支持的会议列表:\n")
    
    print("🔗 OpenReview API:")
    for conf in SOURCES['openreview']:
        print(f"   - {conf}")
    
    print("\n🌐 网页爬取:")
    for conf in SOURCES['web_scrape']:
        print(f"   - {conf}")
    
    print("\n📄 PDF 提取:")
    for conf in SOURCES['pdf_extract']:
        print(f"   - {conf}")
    
    print()


def run_openreview_scrape(
    conferences: list,
    years: list,
    keywords: list,
    output: str,
    verbose: bool
) -> int:
    """运行 OpenReview 爬取。"""
    if verbose:
        print(f"\n🔍 OpenReview 爬取: {', '.join(conferences)} ({', '.join(years)})")
    
    try:
        extractor = Extractor(
            fields=['forum'],
            subfields={'content': ['title', 'keywords', 'abstract', 'pdf']}
        )
        
        # 添加自定义处理函数
        def modify_paper(paper):
            paper.forum = f"https://openreview.net/forum?id={paper.forum}"
            if 'pdf' in paper.content:
                pdf_value = paper.content['pdf']
                # 处理 OpenReview API v2 的 {'value': '...'} 格式
                if isinstance(pdf_value, dict) and 'value' in pdf_value:
                    pdf_value = pdf_value['value']
                paper.content['pdf'] = f"https://openreview.net{pdf_value}"
            return paper
        
        scraper = Scraper(
            conferences=conferences,
            years=years,
            keywords=keywords,
            extractor=extractor,
            fpath=output,
            fns=[modify_paper]
        )
        
        if keywords:
            from .filters import title_filter, abstract_filter, keywords_filter
            scraper.add_filter(title_filter)
            scraper.add_filter(abstract_filter)
            scraper.add_filter(keywords_filter)
        
        scraper()
        return 0
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


def run_web_scrape(
    conferences: list,
    years: list,
    output: str,
    output_dir: str,
    verbose: bool
) -> int:
    """运行网页爬取。"""
    try:
        if len(conferences) == 1 and len(years) == 1 and output:
            # 单会议单年份
            papers = scrape_conference(
                conferences[0],
                int(years[0]),
                output,
                verbose
            )
            if verbose:
                print(f"\n✅ 完成! 共 {len(papers)} 篇论文")
        else:
            # 批量爬取
            out_dir = output_dir or './output'
            results = batch_scrape(
                conferences,
                [int(y) for y in years],
                out_dir,
                verbose
            )
            if verbose:
                total = sum(len(papers) for papers in results.values())
                print(f"\n✅ 完成! 共 {total} 篇论文")
        
        return 0
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


def run_pdf_extract(
    pdf_dir: str,
    year: str,
    output: str,
    verbose: bool
) -> int:
    """运行 PDF 提取。"""
    if not is_pdf_available():
        print("❌ 未安装 PDF 库，请安装: pip install PyMuPDF")
        return 1
    
    try:
        papers = extract_aamas_metadata(
            pdf_dir,
            int(year),
            output,
            verbose
        )
        
        if verbose:
            print(f"\n✅ 完成! 共 {len(papers)} 篇论文")
        
        return 0
    except Exception as e:
        print(f"❌ 错误: {e}")
        return 1


def main(args=None) -> int:
    """主入口函数。"""
    parser = create_parser()
    parsed = parser.parse_args(args)
    
    verbose = not parsed.quiet
    
    # 列出会议
    if parsed.list_conferences:
        list_conferences()
        return 0
    
    # PDF 提取模式
    if parsed.pdf_dir:
        if not parsed.years or len(parsed.years) != 1:
            print("❌ PDF 提取模式需要指定单个年份 (-y)")
            return 1
        if not parsed.output:
            print("❌ 需要指定输出文件 (-o)")
            return 1
        
        return run_pdf_extract(
            parsed.pdf_dir,
            parsed.years[0],
            parsed.output,
            verbose
        )
    
    # 常规爬取模式
    if not parsed.conferences:
        print("❌ 需要指定会议 (-c)")
        parser.print_help()
        return 1
    
    if not parsed.years:
        print("❌ 需要指定年份 (-y)")
        return 1
    
    if not parsed.output and not parsed.output_dir:
        print("❌ 需要指定输出文件 (-o) 或输出目录 (--output-dir)")
        return 1
    
    # 判断数据源类型
    source_types = set(get_source_type(c) for c in parsed.conferences)
    
    if 'unknown' in source_types:
        unknown_confs = [c for c in parsed.conferences if get_source_type(c) == 'unknown']
        print(f"❌ 不支持的会议: {', '.join(unknown_confs)}")
        list_conferences()
        return 1
    
    if len(source_types) > 1:
        print("⚠️  混合数据源，将分别处理...")
    
    # OpenReview 来源
    openreview_confs = [c for c in parsed.conferences if get_source_type(c) == 'openreview']
    if openreview_confs:
        output = parsed.output or os.path.join(parsed.output_dir, 'openreview_papers.csv')
        result = run_openreview_scrape(
            openreview_confs,
            parsed.years,
            parsed.keywords,
            output,
            verbose
        )
        if result != 0:
            return result
    
    # 网页爬取来源
    web_confs = [c for c in parsed.conferences if get_source_type(c) == 'web_scrape']
    if web_confs:
        result = run_web_scrape(
            web_confs,
            parsed.years,
            parsed.output if len(web_confs) == 1 and len(parsed.years) == 1 else None,
            parsed.output_dir,
            verbose
        )
        if result != 0:
            return result
    
    return 0


if __name__ == '__main__':
    sys.exit(main())

