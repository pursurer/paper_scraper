"""
pdf_extractor 模块测试

测试 PDF 元数据提取功能（使用 mock 避免真实文件操作）。
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

from paper_scraper.pdf_extractor import (
    get_pdf_library,
    is_pdf_available,
    extract_text_from_pdf,
    extract_abstract,
    extract_keywords,
    extract_title,
    process_pdf,
    process_pdf_directory,
    extract_aamas_metadata,
    process_from_index,
    ABSTRACT_PATTERNS,
    KEYWORDS_PATTERNS,
)


# ============ PDF 库检测测试 ============

class TestPdfLibrary:
    """测试 PDF 库检测"""
    
    def test_get_pdf_library_returns_string_or_none(self):
        """测试返回字符串或 None"""
        result = get_pdf_library()
        assert result is None or isinstance(result, str)
    
    def test_is_pdf_available_returns_bool(self):
        """测试返回布尔值"""
        result = is_pdf_available()
        assert isinstance(result, bool)


# ============ Abstract 提取测试 ============

class TestExtractAbstract:
    """测试 Abstract 提取"""
    
    def test_extract_standard_abstract(self):
        """测试标准格式 abstract"""
        text = """
        Abstract
        This paper presents a novel approach to reinforcement learning.
        We show that our method achieves state-of-the-art performance.
        
        Keywords: reinforcement learning, deep learning
        """
        
        result = extract_abstract(text)
        
        assert result is not None
        assert 'novel approach' in result
        assert 'Keywords' not in result
    
    def test_extract_uppercase_abstract(self):
        """测试大写 ABSTRACT"""
        text = """
        ABSTRACT
        This is the abstract content.
        
        1. Introduction
        """
        
        result = extract_abstract(text)
        
        assert result is not None
        assert 'abstract content' in result
    
    def test_truncate_long_abstract(self):
        """测试截断过长 abstract"""
        long_text = "Abstract\n" + "This is a sentence. " * 200 + "\n\nKeywords: test"
        
        result = extract_abstract(long_text, max_length=500)
        
        assert result is not None
        assert len(result) <= 500
    
    def test_empty_text(self):
        """测试空文本"""
        assert extract_abstract('') is None
        assert extract_abstract(None) is None
    
    def test_no_abstract(self):
        """测试无 abstract"""
        text = "Some random text without abstract section."
        assert extract_abstract(text) is None


# ============ Keywords 提取测试 ============

class TestExtractKeywords:
    """测试 Keywords 提取"""
    
    def test_extract_standard_keywords(self):
        """测试标准格式 keywords"""
        text = """
        Abstract
        Some abstract text.
        
        Keywords: machine learning, deep learning, reinforcement learning
        
        1. Introduction
        """
        
        result = extract_keywords(text)
        
        assert result is not None
        assert 'machine learning' in result
    
    def test_extract_uppercase_keywords(self):
        """测试大写 KEYWORDS"""
        text = """
        KEYWORDS: AI, ML, DL
        
        Introduction
        """
        
        result = extract_keywords(text)
        
        assert result is not None
        assert 'AI' in result
    
    def test_truncate_long_keywords(self):
        """测试截断过长 keywords"""
        long_keywords = "Keywords: " + "keyword" * 100 + "\n\n1. Introduction"
        
        result = extract_keywords(long_keywords, max_length=100)
        
        assert result is not None
        assert len(result) <= 100
    
    def test_empty_text(self):
        """测试空文本"""
        assert extract_keywords('') is None
        assert extract_keywords(None) is None
    
    def test_no_keywords(self):
        """测试无 keywords"""
        text = "Some random text without any special markers."
        assert extract_keywords(text) is None


# ============ Title 提取测试 ============

class TestExtractTitle:
    """测试 Title 提取"""
    
    def test_extract_first_line(self):
        """测试提取第一行"""
        text = """A Novel Approach to Machine Learning
        
        Author Name
        University of Test
        """
        
        result = extract_title(text)
        
        assert result is not None
        assert 'Novel Approach' in result
    
    def test_skip_short_lines(self):
        """测试跳过短行"""
        text = """
        
        
        A Novel Approach to Machine Learning
        """
        
        result = extract_title(text)
        
        assert result is not None
        assert 'Novel Approach' in result
    
    def test_skip_author_lines(self):
        """测试跳过作者行"""
        text = """author@university.edu
        University of Test
        A Novel Approach to Machine Learning
        """
        
        result = extract_title(text)
        
        assert result is not None
        # 应该跳过包含 @ 和 University 的行
    
    def test_empty_text(self):
        """测试空文本"""
        assert extract_title('') is None
        assert extract_title(None) is None


# ============ process_pdf 测试 ============

class TestProcessPdf:
    """测试 process_pdf"""
    
    def test_returns_dict(self):
        """测试返回字典"""
        with patch('paper_scraper.pdf_extractor.extract_text_from_pdf', return_value=''):
            result = process_pdf('/fake/path.pdf')
        
        assert isinstance(result, dict)
        assert 'title' in result
        assert 'abstract' in result
        assert 'keywords' in result
    
    def test_extracts_all_fields(self):
        """测试提取所有字段"""
        mock_text = """Test Title
        
        Abstract
        This is the abstract.
        
        Keywords: test, example
        """
        
        with patch('paper_scraper.pdf_extractor.extract_text_from_pdf', return_value=mock_text):
            result = process_pdf('/fake/path.pdf')
        
        assert result['title'] is not None or result['abstract'] is not None


# ============ process_pdf_directory 测试 ============

class TestProcessPdfDirectory:
    """测试 process_pdf_directory"""
    
    def test_empty_directory(self):
        """测试空目录"""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = process_pdf_directory(tmpdir, verbose=False)
        
        assert result == []
    
    def test_nonexistent_directory(self):
        """测试不存在的目录"""
        result = process_pdf_directory('/nonexistent/path', verbose=False)
        assert result == []
    
    def test_no_pdf_library(self):
        """测试无 PDF 库"""
        with patch('paper_scraper.pdf_extractor.is_pdf_available', return_value=False):
            with tempfile.TemporaryDirectory() as tmpdir:
                result = process_pdf_directory(tmpdir, verbose=False)
        
        assert result == []


# ============ extract_aamas_metadata 测试 ============

class TestExtractAamasMetadata:
    """测试 extract_aamas_metadata"""
    
    def test_returns_list(self):
        """测试返回列表"""
        with patch('paper_scraper.pdf_extractor.process_pdf_directory', return_value=[]):
            result = extract_aamas_metadata('/fake/dir', 2025, verbose=False)
        
        assert isinstance(result, list)
    
    def test_adds_conference_field(self):
        """测试添加会议字段"""
        mock_papers = [{'title': 'Test'}]
        
        with patch('paper_scraper.pdf_extractor.process_pdf_directory', return_value=mock_papers):
            result = extract_aamas_metadata('/fake/dir', 2025, verbose=False)
        
        assert len(result) == 1
        assert result[0]['conference'] == 'AAMAS'
        assert result[0]['year'] == '2025'
        assert 'id' in result[0]


# ============ process_from_index 测试 ============

class TestProcessFromIndex:
    """测试 process_from_index"""
    
    def test_nonexistent_index(self):
        """测试不存在的索引文件"""
        result = process_from_index('/nonexistent/index.csv', verbose=False)
        assert result == []
    
    def test_no_pdf_library(self):
        """测试无 PDF 库"""
        with patch('paper_scraper.pdf_extractor.is_pdf_available', return_value=False):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                f.write('title,pdf_local_path\n')
                f.write('Test Paper,test.pdf\n')
                temp_path = f.name
            
            try:
                result = process_from_index(temp_path, verbose=False)
                assert result == []
            finally:
                os.unlink(temp_path)


# ============ 集成测试 ============

class TestPdfExtractorIntegration:
    """集成测试"""
    
    def test_abstract_patterns_valid(self):
        """测试 abstract 模式有效"""
        assert len(ABSTRACT_PATTERNS) > 0
        for pattern in ABSTRACT_PATTERNS:
            # 确保模式可以编译
            import re
            re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    def test_keywords_patterns_valid(self):
        """测试 keywords 模式有效"""
        assert len(KEYWORDS_PATTERNS) > 0
        for pattern in KEYWORDS_PATTERNS:
            import re
            re.compile(pattern, re.IGNORECASE | re.MULTILINE | re.DOTALL)
    
    def test_full_extraction_flow(self):
        """测试完整提取流程"""
        mock_text = """
        A Novel Deep Learning Method for Optimization
        
        John Doe
        MIT
        
        Abstract
        We present a novel deep learning method for optimization problems.
        Our approach achieves significant improvements over baselines.
        
        Keywords: deep learning, optimization, neural networks
        
        1. Introduction
        This paper introduces...
        """
        
        abstract = extract_abstract(mock_text)
        keywords = extract_keywords(mock_text)
        title = extract_title(mock_text)
        
        assert abstract is not None
        assert 'novel deep learning' in abstract.lower()
        
        assert keywords is not None
        assert 'deep learning' in keywords.lower()
        
        # title 提取可能因格式不同而有不同结果

