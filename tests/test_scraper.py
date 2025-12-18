"""
scraper 模块测试

测试 Scraper 主类的完整工作流。
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, MagicMock, patch, PropertyMock

from paper_scraper.scraper import Scraper, create_scraper
from paper_scraper.extractor import Extractor
from paper_scraper.filters import title_filter, abstract_filter, always_match_filter


class MockPaper:
    """模拟 OpenReview 论文对象"""
    
    def __init__(self, forum: str, title: str = "Test Paper", abstract: str = "Test abstract"):
        self.forum = forum
        self.content = {
            'title': title,
            'abstract': abstract,
            'keywords': ['AI', 'ML'],
            'pdf': '/pdf/test.pdf',
        }


def create_mock_extractor():
    """创建测试用的 Extractor"""
    return Extractor(
        fields=['forum'],
        subfields={'content': ['title', 'abstract', 'keywords']},
        include_subfield=False
    )


# ============ Scraper 初始化测试 ============

class TestScraperInit:
    """测试 Scraper 初始化"""
    
    def test_basic_init(self):
        """测试基本初始化"""
        extractor = create_mock_extractor()
        
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI'],
            extractor=extractor,
            fpath='test.csv',
        )
        
        assert scraper.conferences == ['ICLR']
        assert scraper.years == ['2024']
        assert scraper.keywords == ['AI']
        assert scraper.fpath == 'test.csv'
        assert scraper.only_accepted is True
        assert scraper.filters == []
    
    def test_init_with_client(self):
        """测试传入 client"""
        extractor = create_mock_extractor()
        mock_client = Mock()
        
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
            client=mock_client,
        )
        
        assert scraper._client is mock_client
    
    def test_default_groups(self):
        """测试默认分组"""
        extractor = create_mock_extractor()
        
        scraper = Scraper(
            conferences=['ICLR', 'ICML'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        # 默认按会议分组
        assert scraper.groups == ['ICLR', 'ICML']
    
    def test_custom_groups(self):
        """测试自定义分组"""
        extractor = create_mock_extractor()
        
        scraper = Scraper(
            conferences=['ICLR', 'ICML'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
            groups=['Conference'],
        )
        
        assert scraper.groups == ['Conference']
    
    def test_repr(self):
        """测试字符串表示"""
        extractor = create_mock_extractor()
        
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI', 'ML'],
            extractor=extractor,
            fpath='test.csv',
        )
        
        repr_str = repr(scraper)
        assert 'ICLR' in repr_str
        assert '2024' in repr_str


# ============ add_filter 测试 ============

class TestAddFilter:
    """测试添加过滤器"""
    
    def test_add_single_filter(self):
        """测试添加单个过滤器"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI'],
            extractor=extractor,
            fpath='test.csv',
        )
        
        scraper.add_filter(title_filter)
        
        assert len(scraper.filters) == 1
        assert scraper.filters[0][0] is title_filter
    
    def test_add_multiple_filters(self):
        """测试添加多个过滤器"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI'],
            extractor=extractor,
            fpath='test.csv',
        )
        
        scraper.add_filter(title_filter)
        scraper.add_filter(abstract_filter)
        
        assert len(scraper.filters) == 2
    
    def test_chain_add_filter(self):
        """测试链式调用"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI'],
            extractor=extractor,
            fpath='test.csv',
        )
        
        result = scraper.add_filter(title_filter).add_filter(abstract_filter)
        
        assert result is scraper
        assert len(scraper.filters) == 2
    
    def test_add_filter_with_kwargs(self):
        """测试添加带参数的过滤器"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI'],
            extractor=extractor,
            fpath='test.csv',
        )
        
        scraper.add_filter(title_filter, threshold=90)
        
        assert scraper.filters[0][2] == {'threshold': 90}
    
    def test_clear_filters(self):
        """测试清空过滤器"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI'],
            extractor=extractor,
            fpath='test.csv',
        )
        
        scraper.add_filter(title_filter)
        scraper.add_filter(abstract_filter)
        scraper.clear_filters()
        
        assert len(scraper.filters) == 0


# ============ _parse_venue 测试 ============

class TestParseVenue:
    """测试 venue 解析"""
    
    def test_standard_venue(self):
        """测试标准 venue"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        info = scraper._parse_venue('ICLR.cc/2024/Conference')
        
        assert info['org'] == 'ICLR.cc'
        assert info['year'] == '2024'
        assert info['type'] == 'Conference'
    
    def test_track_venue(self):
        """测试 Track venue"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['AAAI'],
            years=['2025'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        info = scraper._parse_venue('AAAI.org/2025/Track/Main')
        
        assert info['year'] == '2025'


# ============ _infer_presentation_type 测试 ============

class TestInferPresentationType:
    """测试展示类型推断"""
    
    def test_oral(self):
        """测试 Oral"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        result = scraper._infer_presentation_type('ICLR.cc/2024/Conference/Oral')
        
        assert result == 'Oral'
    
    def test_spotlight(self):
        """测试 Spotlight"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        result = scraper._infer_presentation_type('ICLR.cc/2024/Conference/Spotlight')
        
        assert result == 'Spotlight'
    
    def test_default_poster(self):
        """测试默认 Poster"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        result = scraper._infer_presentation_type('ICLR.cc/2024/Conference')
        
        assert result == 'Poster'


# ============ _apply_on_papers 测试 ============

class TestApplyOnPapers:
    """测试论文处理"""
    
    def test_apply_without_filters(self):
        """测试无过滤器时的处理"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
            verbose=False,
        )
        
        papers = {
            'ICLR': {
                'ICLR.cc/2024/Conference': [
                    MockPaper('paper1', 'Title 1'),
                    MockPaper('paper2', 'Title 2'),
                ]
            }
        }
        
        result = scraper._apply_on_papers(papers)
        
        assert len(result['ICLR']['ICLR.cc/2024/Conference']) == 2
    
    def test_apply_with_filters(self):
        """测试有过滤器时的处理"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['machine learning'],
            extractor=extractor,
            fpath='test.csv',
            verbose=False,
        )
        scraper.add_filter(title_filter)
        
        papers = {
            'ICLR': {
                'ICLR.cc/2024/Conference': [
                    MockPaper('paper1', 'Machine Learning Paper'),
                    MockPaper('paper2', 'Computer Vision Paper'),
                ]
            }
        }
        
        result = scraper._apply_on_papers(papers)
        
        # 只有第一篇匹配
        assert len(result['ICLR']['ICLR.cc/2024/Conference']) == 1
    
    def test_apply_adds_year(self):
        """测试添加年份字段"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
            verbose=False,
        )
        
        papers = {
            'ICLR': {
                'ICLR.cc/2024/Conference': [MockPaper('paper1')]
            }
        }
        
        result = scraper._apply_on_papers(papers)
        
        paper = result['ICLR']['ICLR.cc/2024/Conference'][0]
        assert paper['year'] == '2024'
    
    def test_apply_custom_functions(self):
        """测试自定义处理函数"""
        extractor = create_mock_extractor()
        
        def add_prefix(paper):
            paper.content['title'] = '[PREFIX] ' + paper.content['title']
            return paper
        
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
            fns=[add_prefix],
            verbose=False,
        )
        
        papers = {
            'ICLR': {
                'ICLR.cc/2024/Conference': [MockPaper('paper1', 'Original Title')]
            }
        }
        
        result = scraper._apply_on_papers(papers)
        
        paper = result['ICLR']['ICLR.cc/2024/Conference'][0]
        assert paper['title'].startswith('[PREFIX]')


# ============ scrape 工作流测试 ============

class TestScrapeWorkflow:
    """测试完整抓取工作流"""
    
    def test_scrape_returns_list(self):
        """测试 scrape 返回列表"""
        extractor = create_mock_extractor()
        mock_client = Mock()
        
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='',  # 不保存文件
            client=mock_client,
            verbose=False,
        )
        
        # Mock 依赖函数
        with patch('paper_scraper.scraper.get_venues', return_value=['ICLR.cc/2024/Conference']):
            with patch('paper_scraper.scraper.group_venues', return_value={'ICLR': ['ICLR.cc/2024/Conference']}):
                with patch('paper_scraper.scraper.get_papers', return_value={
                    'ICLR': {
                        'ICLR.cc/2024/Conference': [MockPaper('paper1')]
                    }
                }):
                    result = scraper.scrape()
        
        assert isinstance(result, list)
        assert len(result) == 1
    
    def test_scrape_empty_venues(self):
        """测试空 venues"""
        extractor = create_mock_extractor()
        mock_client = Mock()
        
        scraper = Scraper(
            conferences=['UNKNOWN'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='',
            client=mock_client,
            verbose=False,
        )
        
        with patch('paper_scraper.scraper.get_venues', return_value=[]):
            result = scraper.scrape()
        
        assert result == []
    
    def test_scrape_saves_csv(self):
        """测试保存 CSV"""
        extractor = create_mock_extractor()
        mock_client = Mock()
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            scraper = Scraper(
                conferences=['ICLR'],
                years=['2024'],
                keywords=[],
                extractor=extractor,
                fpath=temp_path,
                client=mock_client,
                verbose=False,
            )
            
            with patch('paper_scraper.scraper.get_venues', return_value=['ICLR.cc/2024/Conference']):
                with patch('paper_scraper.scraper.group_venues', return_value={'ICLR': ['ICLR.cc/2024/Conference']}):
                    with patch('paper_scraper.scraper.get_papers', return_value={
                        'ICLR': {
                            'ICLR.cc/2024/Conference': [MockPaper('paper1', 'Test Paper')]
                        }
                    }):
                        scraper.scrape()
            
            # 验证文件已创建
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_callable_interface(self):
        """测试可调用接口"""
        extractor = create_mock_extractor()
        mock_client = Mock()
        
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='',
            client=mock_client,
            verbose=False,
        )
        
        with patch('paper_scraper.scraper.get_venues', return_value=['ICLR.cc/2024/Conference']):
            with patch('paper_scraper.scraper.group_venues', return_value={'ICLR': ['ICLR.cc/2024/Conference']}):
                with patch('paper_scraper.scraper.get_papers', return_value={
                    'ICLR': {
                        'ICLR.cc/2024/Conference': [MockPaper('paper1')]
                    }
                }):
                    # 使用 __call__
                    result = scraper()
        
        assert isinstance(result, list)


# ============ 便捷方法测试 ============

class TestHelperMethods:
    """测试便捷方法"""
    
    def test_get_paper_count_no_papers(self):
        """测试未抓取时的论文计数"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        assert scraper.get_paper_count() == 0
    
    def test_get_paper_count_with_papers(self):
        """测试有论文时的计数"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        # 模拟已处理的论文
        scraper.filtered_papers = {
            'ICLR': {
                'venue1': [{'forum': 'p1'}, {'forum': 'p2'}],
                'venue2': [{'forum': 'p3'}],
            }
        }
        
        assert scraper.get_paper_count() == 3
    
    def test_get_papers_flat(self):
        """测试获取扁平化列表"""
        extractor = create_mock_extractor()
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=[],
            extractor=extractor,
            fpath='test.csv',
        )
        
        scraper.filtered_papers = {
            'ICLR': {
                'venue1': [{'forum': 'p1'}],
                'venue2': [{'forum': 'p2'}],
            }
        }
        
        result = scraper.get_papers_flat()
        
        assert len(result) == 2


# ============ create_scraper 便捷函数测试 ============

class TestCreateScraper:
    """测试便捷创建函数"""
    
    def test_create_basic_scraper(self):
        """测试基本创建"""
        scraper = create_scraper(
            conferences=['ICLR'],
            years=['2024'],
        )
        
        assert scraper.conferences == ['ICLR']
        assert scraper.years == ['2024']
        assert scraper.keywords == []
        assert scraper.fpath == 'papers.csv'
    
    def test_create_with_keywords(self):
        """测试带关键词创建"""
        scraper = create_scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['AI', 'ML'],
        )
        
        assert scraper.keywords == ['AI', 'ML']
    
    def test_create_with_custom_path(self):
        """测试自定义路径"""
        scraper = create_scraper(
            conferences=['ICLR'],
            years=['2024'],
            output_path='custom.csv',
        )
        
        assert scraper.fpath == 'custom.csv'
    
    def test_create_with_custom_fields(self):
        """测试自定义字段"""
        scraper = create_scraper(
            conferences=['ICLR'],
            years=['2024'],
            fields=['forum', 'id'],
            subfields={'content': ['title']},
        )
        
        assert scraper.extractor.fields == ['forum', 'id']


# ============ 集成测试 ============

class TestScraperIntegration:
    """集成测试"""
    
    def test_full_workflow_with_filters(self):
        """测试带过滤器的完整流程"""
        extractor = create_mock_extractor()
        mock_client = Mock()
        
        scraper = Scraper(
            conferences=['ICLR'],
            years=['2024'],
            keywords=['deep learning'],
            extractor=extractor,
            fpath='',
            client=mock_client,
            verbose=False,
        )
        scraper.add_filter(title_filter)
        scraper.add_filter(abstract_filter)
        
        # 创建测试数据
        test_papers = {
            'ICLR': {
                'ICLR.cc/2024/Conference': [
                    MockPaper('p1', 'Deep Learning Paper', 'About deep learning'),
                    MockPaper('p2', 'NLP Paper', 'Natural language processing'),
                    MockPaper('p3', 'Vision', 'Deep learning for vision'),
                ]
            }
        }
        
        with patch('paper_scraper.scraper.get_venues', return_value=['ICLR.cc/2024/Conference']):
            with patch('paper_scraper.scraper.group_venues', return_value={'ICLR': ['ICLR.cc/2024/Conference']}):
                with patch('paper_scraper.scraper.get_papers', return_value=test_papers):
                    result = scraper()
        
        # p1 匹配标题，p3 匹配摘要
        assert len(result) == 2

