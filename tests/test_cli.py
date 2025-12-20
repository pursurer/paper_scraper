"""
CLI (__main__.py) 模块测试

测试命令行接口功能。
"""
import pytest
import sys
from unittest.mock import patch, MagicMock

from paper_scraper.__main__ import (
    create_parser,
    get_source_type,
    list_conferences,
    main,
)


# ============ 参数解析测试 ============

class TestCreateParser:
    """测试参数解析器"""
    
    def test_parser_creation(self):
        """测试解析器创建"""
        parser = create_parser()
        assert parser is not None
    
    def test_parse_conference(self):
        """测试会议参数"""
        parser = create_parser()
        args = parser.parse_args(['-c', 'ICLR', '-y', '2024', '-o', 'test.csv'])
        
        assert args.conferences == ['ICLR']
        assert args.years == ['2024']
        assert args.output == 'test.csv'
    
    def test_parse_multiple_conferences(self):
        """测试多会议参数"""
        parser = create_parser()
        args = parser.parse_args(['-c', 'ICLR', 'ICML', '-y', '2024', '-o', 'test.csv'])
        
        assert args.conferences == ['ICLR', 'ICML']
    
    def test_parse_multiple_years(self):
        """测试多年份参数"""
        parser = create_parser()
        args = parser.parse_args(['-c', 'ICLR', '-y', '2023', '2024', '-o', 'test.csv'])
        
        assert args.years == ['2023', '2024']
    
    def test_parse_keywords(self):
        """测试关键词参数"""
        parser = create_parser()
        args = parser.parse_args(['-c', 'ICLR', '-y', '2024', '-k', 'RL', 'NLP', '-o', 'test.csv'])
        
        assert args.keywords == ['RL', 'NLP']
    
    def test_parse_pdf_dir(self):
        """测试 PDF 目录参数"""
        parser = create_parser()
        args = parser.parse_args(['--pdf-dir', './pdfs', '-y', '2025', '-o', 'test.csv'])
        
        assert args.pdf_dir == './pdfs'
    
    def test_parse_output_dir(self):
        """测试输出目录参数"""
        parser = create_parser()
        args = parser.parse_args(['-c', 'ICLR', '-y', '2024', '--output-dir', './output'])
        
        assert args.output_dir == './output'
    
    def test_parse_quiet(self):
        """测试安静模式"""
        parser = create_parser()
        args = parser.parse_args(['-c', 'ICLR', '-y', '2024', '-o', 'test.csv', '-q'])
        
        assert args.quiet is True
    
    def test_parse_list_conferences(self):
        """测试列出会议参数"""
        parser = create_parser()
        args = parser.parse_args(['--list-conferences'])
        
        assert args.list_conferences is True


# ============ 数据源类型测试 ============

class TestGetSourceType:
    """测试数据源类型判断"""
    
    def test_openreview_source(self):
        """测试 OpenReview 来源"""
        assert get_source_type('ICLR') == 'openreview'
        assert get_source_type('ICML') == 'openreview'
        assert get_source_type('NeurIPS') == 'openreview'
    
    def test_web_scrape_source(self):
        """测试网页爬取来源"""
        assert get_source_type('AAAI') == 'web_scrape'
        assert get_source_type('IJCAI') == 'web_scrape'
        assert get_source_type('ACL') == 'web_scrape'
    
    def test_pdf_extract_source(self):
        """测试 PDF 提取来源"""
        assert get_source_type('AAMAS') == 'pdf_extract'
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        assert get_source_type('iclr') == 'openreview'
        assert get_source_type('Iclr') == 'openreview'
    
    def test_unknown_source(self):
        """测试未知来源"""
        assert get_source_type('UNKNOWN') == 'unknown'


# ============ main 函数测试 ============

class TestMain:
    """测试主函数"""
    
    def test_list_conferences(self):
        """测试列出会议"""
        result = main(['--list-conferences'])
        assert result == 0
    
    def test_version(self):
        """测试版本信息"""
        with pytest.raises(SystemExit) as exc_info:
            main(['-v'])
        assert exc_info.value.code == 0
    
    def test_missing_conference(self):
        """测试缺少会议参数"""
        result = main(['-y', '2024', '-o', 'test.csv'])
        assert result == 1
    
    def test_missing_year(self):
        """测试缺少年份参数"""
        result = main(['-c', 'ICLR', '-o', 'test.csv'])
        assert result == 1
    
    def test_default_output(self):
        """测试默认输出路径"""
        # 模拟 run_openreview_scrape 返回成功
        with patch('paper_scraper.__main__.run_openreview_scrape', return_value=0) as mock_run:
            # 模拟 os.makedirs 避免实际创建目录
            with patch('os.makedirs'):
                result = main(['-c', 'ICLR', '-y', '2024'])
                assert result == 0
                
                # 检查是否调用了 run_openreview_scrape，且 output 参数包含 paper/
                args = mock_run.call_args
                assert 'paper/iclr_2024.csv' in args[0][3] or args[0][3].endswith('iclr_2024.csv')
    
    def test_unknown_conference(self):
        """测试未知会议"""
        result = main(['-c', 'UNKNOWN', '-y', '2024', '-o', 'test.csv'])
        assert result == 1
    
    def test_pdf_mode_missing_year(self):
        """测试 PDF 模式缺少年份"""
        result = main(['--pdf-dir', './pdfs', '-o', 'test.csv'])
        assert result == 1
    
    def test_pdf_mode_multiple_years(self):
        """测试 PDF 模式多年份"""
        result = main(['--pdf-dir', './pdfs', '-y', '2024', '2025', '-o', 'test.csv'])
        assert result == 1


# ============ 集成测试 ============

class TestCliIntegration:
    """CLI 集成测试"""
    
    def test_web_scrape_single(self):
        """测试单会议网页爬取"""
        with patch('paper_scraper.__main__.scrape_conference', return_value=[]) as mock:
            result = main(['-c', 'IJCAI', '-y', '2024', '-o', 'test.csv', '-q'])
        
        assert result == 0
        mock.assert_called_once()
    
    def test_web_scrape_batch(self):
        """测试批量网页爬取"""
        with patch('paper_scraper.__main__.batch_scrape', return_value={}) as mock:
            result = main(['-c', 'IJCAI', 'AAAI', '-y', '2024', '--output-dir', './out', '-q'])
        
        assert result == 0
        mock.assert_called_once()
    
    def test_pdf_extract(self):
        """测试 PDF 提取"""
        with patch('paper_scraper.__main__.is_pdf_available', return_value=True):
            with patch('paper_scraper.__main__.extract_aamas_metadata', return_value=[]) as mock:
                result = main(['--pdf-dir', './pdfs', '-y', '2025', '-o', 'test.csv', '-q'])
        
        assert result == 0
        mock.assert_called_once()
    
    def test_pdf_extract_no_library(self):
        """测试 PDF 提取无库"""
        with patch('paper_scraper.__main__.is_pdf_available', return_value=False):
            result = main(['--pdf-dir', './pdfs', '-y', '2025', '-o', 'test.csv', '-q'])
        
        assert result == 1

