"""
filters 模块测试

测试关键词过滤器的匹配功能。
"""
import pytest
from unittest.mock import Mock

from paper_scraper.filters import (
    check_keywords_with_keywords,
    check_keywords_with_text,
    title_filter,
    keywords_filter,
    abstract_filter,
    satisfies_any_filters,
    always_match_filter,
    _get_paper_field,
)


class MockPaper:
    """模拟 OpenReview 论文对象"""
    
    def __init__(self, title: str = None, abstract: str = None, keywords: list = None):
        self.content = {}
        if title is not None:
            self.content['title'] = title
        if abstract is not None:
            self.content['abstract'] = abstract
        if keywords is not None:
            self.content['keywords'] = keywords


# ============ check_keywords_with_keywords 测试 ============

class TestCheckKeywordsWithKeywords:
    """测试关键词与关键词匹配"""
    
    def test_exact_match(self):
        """测试精确匹配"""
        keywords = ['machine learning']
        paper_keywords = ['machine learning', 'deep learning']
        
        matched, is_match = check_keywords_with_keywords(keywords, paper_keywords)
        
        assert is_match is True
        assert matched == 'machine learning'
    
    def test_fuzzy_match(self):
        """测试模糊匹配"""
        keywords = ['reinforcement learning']
        paper_keywords = ['Reinforcement Learning', 'RL']
        
        matched, is_match = check_keywords_with_keywords(keywords, paper_keywords)
        
        assert is_match is True
    
    def test_no_match(self):
        """测试不匹配"""
        keywords = ['computer vision']
        paper_keywords = ['natural language processing', 'NLP']
        
        matched, is_match = check_keywords_with_keywords(keywords, paper_keywords)
        
        assert is_match is False
        assert matched is None
    
    def test_empty_paper_keywords(self):
        """测试论文关键词为空"""
        keywords = ['AI']
        
        matched, is_match = check_keywords_with_keywords(keywords, [])
        assert is_match is False
        
        matched, is_match = check_keywords_with_keywords(keywords, None)
        assert is_match is False
    
    def test_string_paper_keywords(self):
        """测试论文关键词为字符串（而非列表）"""
        keywords = ['AI']
        paper_keywords = 'artificial intelligence'
        
        # 应该能处理字符串输入
        matched, is_match = check_keywords_with_keywords(keywords, paper_keywords, threshold=50)
        # 'AI' 与 'artificial intelligence' 的模糊匹配
        assert isinstance(is_match, bool)
    
    def test_threshold_parameter(self):
        """测试阈值参数"""
        keywords = ['ML']
        paper_keywords = ['machine learning']
        
        # 低阈值应该匹配
        matched, is_match = check_keywords_with_keywords(keywords, paper_keywords, threshold=20)
        # ML 与 machine learning 部分匹配
        
        # 高阈值可能不匹配
        matched_high, is_match_high = check_keywords_with_keywords(
            keywords, paper_keywords, threshold=95
        )
        assert is_match_high is False


# ============ check_keywords_with_text 测试 ============

class TestCheckKeywordsWithText:
    """测试关键词与文本匹配"""
    
    def test_keyword_in_text(self):
        """测试关键词在文本中"""
        keywords = ['neural network']
        text = 'This paper presents a new neural network architecture.'
        
        matched, is_match = check_keywords_with_text(keywords, text)
        
        assert is_match is True
        assert matched == 'neural network'
    
    def test_partial_match(self):
        """测试部分匹配"""
        keywords = ['learning']
        text = 'Deep reinforcement learning for robotics'
        
        matched, is_match = check_keywords_with_text(keywords, text)
        
        assert is_match is True
    
    def test_no_match(self):
        """测试不匹配"""
        keywords = ['computer vision']
        text = 'Natural language processing with transformers'
        
        matched, is_match = check_keywords_with_text(keywords, text)
        
        assert is_match is False
    
    def test_empty_text(self):
        """测试空文本"""
        keywords = ['AI']
        
        matched, is_match = check_keywords_with_text(keywords, '')
        assert is_match is False
        
        matched, is_match = check_keywords_with_text(keywords, None)
        assert is_match is False
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        keywords = ['TRANSFORMER']
        text = 'Attention is all you need: introducing the transformer model'
        
        matched, is_match = check_keywords_with_text(keywords, text)
        
        assert is_match is True


# ============ title_filter 测试 ============

class TestTitleFilter:
    """测试标题过滤器"""
    
    def test_match_in_title(self):
        """测试标题匹配"""
        paper = MockPaper(title='Deep Learning for Image Classification')
        
        matched, is_match = title_filter(paper, ['deep learning'])
        
        assert is_match is True
        assert matched == 'deep learning'
    
    def test_no_match_in_title(self):
        """测试标题不匹配"""
        paper = MockPaper(title='Quantum Computing Overview')
        
        matched, is_match = title_filter(paper, ['machine learning'])
        
        assert is_match is False
    
    def test_missing_title(self):
        """测试缺失标题"""
        paper = MockPaper()  # 没有标题
        
        matched, is_match = title_filter(paper, ['AI'])
        
        assert is_match is False
    
    def test_dict_paper(self):
        """测试字典格式的论文"""
        paper = {'content': {'title': 'Neural Networks'}}
        
        matched, is_match = title_filter(paper, ['neural'])
        
        assert is_match is True


# ============ keywords_filter 测试 ============

class TestKeywordsFilter:
    """测试关键词过滤器"""
    
    def test_match_keywords(self):
        """测试关键词匹配"""
        paper = MockPaper(keywords=['machine learning', 'optimization'])
        
        matched, is_match = keywords_filter(paper, ['optimization'])
        
        assert is_match is True
    
    def test_no_match_keywords(self):
        """测试关键词不匹配"""
        paper = MockPaper(keywords=['NLP', 'transformers'])
        
        matched, is_match = keywords_filter(paper, ['computer vision'])
        
        assert is_match is False
    
    def test_missing_keywords(self):
        """测试缺失关键词"""
        paper = MockPaper()  # 没有关键词
        
        matched, is_match = keywords_filter(paper, ['AI'])
        
        assert is_match is False


# ============ abstract_filter 测试 ============

class TestAbstractFilter:
    """测试摘要过滤器"""
    
    def test_match_in_abstract(self):
        """测试摘要匹配"""
        paper = MockPaper(
            abstract='We propose a novel approach to reinforcement learning.'
        )
        
        matched, is_match = abstract_filter(paper, ['reinforcement learning'])
        
        assert is_match is True
    
    def test_no_match_in_abstract(self):
        """测试摘要不匹配"""
        paper = MockPaper(
            abstract='This paper discusses image segmentation techniques.'
        )
        
        matched, is_match = abstract_filter(paper, ['natural language'])
        
        assert is_match is False
    
    def test_missing_abstract(self):
        """测试缺失摘要"""
        paper = MockPaper()  # 没有摘要
        
        matched, is_match = abstract_filter(paper, ['AI'])
        
        assert is_match is False


# ============ satisfies_any_filters 测试 ============

class TestSatisfiesAnyFilters:
    """测试组合过滤"""
    
    def test_match_first_filter(self):
        """测试匹配第一个过滤器"""
        paper = MockPaper(title='Deep Learning', abstract='Other content')
        filters = [
            (title_filter, (), {}),
            (abstract_filter, (), {}),
        ]
        
        keyword, filter_type, is_match = satisfies_any_filters(
            paper, ['deep learning'], filters
        )
        
        assert is_match is True
        assert filter_type == 'title_filter'
    
    def test_match_second_filter(self):
        """测试匹配第二个过滤器"""
        paper = MockPaper(title='Other Title', abstract='Machine learning approach')
        filters = [
            (title_filter, (), {}),
            (abstract_filter, (), {}),
        ]
        
        keyword, filter_type, is_match = satisfies_any_filters(
            paper, ['machine learning'], filters
        )
        
        assert is_match is True
        assert filter_type == 'abstract_filter'
    
    def test_no_match_any(self):
        """测试所有过滤器都不匹配"""
        paper = MockPaper(title='Paper A', abstract='Content B')
        filters = [
            (title_filter, (), {}),
            (abstract_filter, (), {}),
        ]
        
        keyword, filter_type, is_match = satisfies_any_filters(
            paper, ['quantum computing'], filters
        )
        
        assert is_match is False
        assert filter_type is None
    
    def test_empty_filters(self):
        """测试空过滤器列表"""
        paper = MockPaper(title='Any Title')
        
        keyword, filter_type, is_match = satisfies_any_filters(paper, ['AI'], [])
        
        assert is_match is False
    
    def test_custom_threshold(self):
        """测试自定义阈值"""
        paper = MockPaper(title='ML Model')
        filters = [
            (title_filter, (), {'threshold': 50}),
        ]
        
        keyword, filter_type, is_match = satisfies_any_filters(
            paper, ['machine learning'], filters
        )
        # 'ML' 与 'machine learning' 在低阈值下可能匹配


# ============ always_match_filter 测试 ============

class TestAlwaysMatchFilter:
    """测试总是匹配的过滤器"""
    
    def test_always_returns_true(self):
        """测试总是返回 True"""
        paper = MockPaper(title='Any Paper')
        
        matched, is_match = always_match_filter(paper, ['any keyword'])
        
        assert is_match is True
        assert matched == 'all'
    
    def test_with_none_keywords(self):
        """测试关键词为 None"""
        paper = MockPaper()
        
        matched, is_match = always_match_filter(paper, None)
        
        assert is_match is True


# ============ _get_paper_field 测试 ============

class TestGetPaperField:
    """测试字段获取辅助函数"""
    
    def test_get_from_object(self):
        """测试从对象获取"""
        paper = MockPaper(title='Test Title')
        
        value = _get_paper_field(paper, 'title')
        
        assert value == 'Test Title'
    
    def test_get_from_dict(self):
        """测试从字典获取"""
        paper = {'content': {'title': 'Dict Title'}}
        
        value = _get_paper_field(paper, 'title')
        
        assert value == 'Dict Title'
    
    def test_handle_value_format(self):
        """测试处理 {value: "..."} 格式"""
        paper = {'content': {'title': {'value': 'Value Format Title'}}}
        
        value = _get_paper_field(paper, 'title')
        
        assert value == 'Value Format Title'
    
    def test_missing_field(self):
        """测试缺失字段"""
        paper = MockPaper()
        
        value = _get_paper_field(paper, 'nonexistent')
        
        assert value is None
    
    def test_none_paper(self):
        """测试 None 输入"""
        value = _get_paper_field(None, 'title')
        
        assert value is None


# ============ 边缘情况测试 ============

class TestEdgeCases:
    """测试边缘情况"""
    
    def test_empty_keywords_list(self):
        """测试空关键词列表"""
        paper = MockPaper(title='Some Title')
        
        matched, is_match = title_filter(paper, [])
        
        assert is_match is False
    
    def test_none_in_keywords(self):
        """测试关键词列表包含 None"""
        paper = MockPaper(title='Machine Learning Paper')
        
        matched, is_match = title_filter(paper, [None, 'machine learning', None])
        
        assert is_match is True
    
    def test_whitespace_keywords(self):
        """测试空白关键词"""
        paper = MockPaper(title='AI Paper')
        
        matched, is_match = title_filter(paper, ['', '  ', 'AI'])
        
        assert is_match is True
        assert matched == 'AI'

