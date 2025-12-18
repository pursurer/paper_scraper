"""
extractor 模块测试

测试 Extractor 类的字段提取功能。
"""
import pytest
from unittest.mock import Mock

from paper_scraper.extractor import Extractor


class MockPaper:
    """模拟 OpenReview 论文对象"""
    
    def __init__(self, forum: str, content: dict):
        self.forum = forum
        self.id = f"note_{forum}"
        self.content = content


class TestExtractorInit:
    """测试 Extractor 初始化"""
    
    def test_default_init(self):
        """测试默认初始化"""
        extractor = Extractor()
        assert extractor.fields == []
        assert extractor.subfields == {}
        assert extractor.include_subfield is False
    
    def test_custom_init(self):
        """测试自定义初始化"""
        extractor = Extractor(
            fields=['forum', 'id'],
            subfields={'content': ['title', 'abstract']},
            include_subfield=True
        )
        assert extractor.fields == ['forum', 'id']
        assert extractor.subfields == {'content': ['title', 'abstract']}
        assert extractor.include_subfield is True
    
    def test_repr(self):
        """测试字符串表示"""
        extractor = Extractor(fields=['forum'])
        repr_str = repr(extractor)
        assert 'Extractor' in repr_str
        assert 'forum' in repr_str


class TestExtractTopLevelFields:
    """测试顶层字段提取"""
    
    def test_extract_single_field(self):
        """测试提取单个顶层字段"""
        paper = MockPaper(
            forum='abc123',
            content={'title': 'Test Paper'}
        )
        
        extractor = Extractor(fields=['forum'])
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
    
    def test_extract_multiple_fields(self):
        """测试提取多个顶层字段"""
        paper = MockPaper(
            forum='abc123',
            content={'title': 'Test Paper'}
        )
        
        extractor = Extractor(fields=['forum', 'id'])
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
        assert result['id'] == 'note_abc123'
    
    def test_extract_missing_field(self):
        """测试提取不存在的字段"""
        paper = MockPaper(
            forum='abc123',
            content={'title': 'Test Paper'}
        )
        
        extractor = Extractor(fields=['forum', 'nonexistent'])
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
        assert result['nonexistent'] == ''


class TestExtractSubfields:
    """测试嵌套字段提取"""
    
    def test_extract_subfields_flat(self):
        """测试提取嵌套字段（扁平化）"""
        paper = MockPaper(
            forum='abc123',
            content={
                'title': 'Test Paper',
                'abstract': 'This is a test abstract.',
                'keywords': ['AI', 'ML']
            }
        )
        
        extractor = Extractor(
            fields=['forum'],
            subfields={'content': ['title', 'abstract', 'keywords']}
        )
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
        assert result['title'] == 'Test Paper'
        assert result['abstract'] == 'This is a test abstract.'
        assert result['keywords'] == ['AI', 'ML']
    
    def test_extract_subfields_nested(self):
        """测试提取嵌套字段（保留嵌套结构）"""
        paper = MockPaper(
            forum='abc123',
            content={
                'title': 'Test Paper',
                'abstract': 'This is abstract.'
            }
        )
        
        extractor = Extractor(
            fields=['forum'],
            subfields={'content': ['title', 'abstract']},
            include_subfield=True
        )
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
        assert 'content' in result
        assert result['content']['title'] == 'Test Paper'
        assert result['content']['abstract'] == 'This is abstract.'
    
    def test_extract_missing_subfield(self):
        """测试提取不存在的嵌套字段"""
        paper = MockPaper(
            forum='abc123',
            content={'title': 'Test Paper'}
        )
        
        extractor = Extractor(
            subfields={'content': ['title', 'nonexistent']}
        )
        result = extractor.extract(paper)
        
        assert result['title'] == 'Test Paper'
        assert result['nonexistent'] == ''


class TestOpenReviewValueFormat:
    """测试 OpenReview 的 {value: "..."} 格式处理"""
    
    def test_handle_value_dict_format(self):
        """测试处理 {value: "..."} 格式"""
        paper = MockPaper(
            forum='abc123',
            content={
                'title': {'value': 'Paper Title'},
                'abstract': {'value': 'Paper Abstract'},
                'keywords': {'value': ['AI', 'ML']}
            }
        )
        
        extractor = Extractor(
            subfields={'content': ['title', 'abstract', 'keywords']}
        )
        result = extractor.extract(paper)
        
        assert result['title'] == 'Paper Title'
        assert result['abstract'] == 'Paper Abstract'
        assert result['keywords'] == ['AI', 'ML']
    
    def test_mixed_value_formats(self):
        """测试混合格式（部分字段使用 value 格式）"""
        paper = MockPaper(
            forum='abc123',
            content={
                'title': {'value': 'Paper Title'},
                'abstract': 'Direct abstract value',
            }
        )
        
        extractor = Extractor(
            subfields={'content': ['title', 'abstract']}
        )
        result = extractor.extract(paper)
        
        assert result['title'] == 'Paper Title'
        assert result['abstract'] == 'Direct abstract value'


class TestDictInput:
    """测试字典输入（而非对象）"""
    
    def test_extract_from_dict(self):
        """测试从字典提取字段"""
        paper = {
            'forum': 'abc123',
            'content': {
                'title': 'Test Paper',
                'abstract': 'Test abstract'
            }
        }
        
        extractor = Extractor(
            fields=['forum'],
            subfields={'content': ['title', 'abstract']}
        )
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
        assert result['title'] == 'Test Paper'
        assert result['abstract'] == 'Test abstract'
    
    def test_extract_from_nested_dict(self):
        """测试从嵌套字典提取"""
        paper = {
            'forum': 'abc123',
            'content': {
                'title': {'value': 'Paper Title'},
            }
        }
        
        extractor = Extractor(
            fields=['forum'],
            subfields={'content': ['title']}
        )
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
        assert result['title'] == 'Paper Title'


class TestCallable:
    """测试可调用接口"""
    
    def test_callable_interface(self):
        """测试 __call__ 方法"""
        paper = MockPaper(
            forum='abc123',
            content={'title': 'Test'}
        )
        
        extractor = Extractor(
            fields=['forum'],
            subfields={'content': ['title']}
        )
        
        # 使用 __call__
        result = extractor(paper)
        
        assert result['forum'] == 'abc123'
        assert result['title'] == 'Test'


class TestEdgeCases:
    """测试边缘情况"""
    
    def test_none_paper(self):
        """测试 None 输入"""
        extractor = Extractor(fields=['forum'])
        result = extractor.extract(None)
        
        assert result['forum'] == ''
    
    def test_empty_fields(self):
        """测试空字段列表"""
        paper = MockPaper(
            forum='abc123',
            content={'title': 'Test'}
        )
        
        extractor = Extractor(fields=[], subfields={})
        result = extractor.extract(paper)
        
        assert result == {}
    
    def test_none_content(self):
        """测试 content 为 None"""
        paper = Mock()
        paper.forum = 'abc123'
        paper.content = None
        
        extractor = Extractor(
            fields=['forum'],
            subfields={'content': ['title']}
        )
        result = extractor.extract(paper)
        
        assert result['forum'] == 'abc123'
        assert result['title'] == ''

