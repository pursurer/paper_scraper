"""
paper 模块测试

测试论文获取功能。
"""
import pytest
from unittest.mock import Mock, MagicMock, patch, call

from paper_scraper.paper import (
    get_venue_papers,
    get_grouped_venue_papers,
    get_papers,
    deduplicate_papers,
    count_papers,
    flatten_papers,
    get_paper_ids,
)


class MockPaper:
    """模拟 OpenReview 论文对象"""
    
    def __init__(self, forum: str, title: str = "Test Paper"):
        self.forum = forum
        self.content = {'title': title}


# ============ deduplicate_papers 测试 ============

class TestDeduplicatePapers:
    """测试论文去重"""
    
    def test_no_duplicates(self):
        """测试无重复情况"""
        papers = [
            MockPaper('paper1'),
            MockPaper('paper2'),
            MockPaper('paper3'),
        ]
        
        result = deduplicate_papers(papers)
        
        assert len(result) == 3
    
    def test_with_duplicates(self):
        """测试有重复情况"""
        papers = [
            MockPaper('paper1'),
            MockPaper('paper2'),
            MockPaper('paper1'),  # 重复
            MockPaper('paper3'),
            MockPaper('paper2'),  # 重复
        ]
        
        result = deduplicate_papers(papers)
        
        assert len(result) == 3
        forum_ids = [p.forum for p in result]
        assert forum_ids == ['paper1', 'paper2', 'paper3']
    
    def test_empty_list(self):
        """测试空列表"""
        result = deduplicate_papers([])
        
        assert result == []
    
    def test_dict_papers(self):
        """测试字典格式的论文"""
        papers = [
            {'forum': 'paper1', 'title': 'A'},
            {'forum': 'paper2', 'title': 'B'},
            {'forum': 'paper1', 'title': 'A'},  # 重复
        ]
        
        result = deduplicate_papers(papers)
        
        assert len(result) == 2
    
    def test_papers_without_forum(self):
        """测试没有 forum 的论文"""
        class NoForumPaper:
            def __init__(self, title):
                self.title = title
        
        papers = [
            MockPaper('paper1'),
            NoForumPaper('No Forum'),
            MockPaper('paper2'),
        ]
        
        result = deduplicate_papers(papers)
        
        # 没有 forum 的论文也应该保留
        assert len(result) == 3


# ============ get_venue_papers 测试 ============

class TestGetVenuePapers:
    """测试单个 venue 论文获取"""
    
    def test_get_accepted_papers(self):
        """测试获取已接受论文"""
        mock_client = Mock()
        mock_papers = [
            MockPaper('paper1'),
            MockPaper('paper2'),
        ]
        
        with patch('paper_scraper.paper.safe_api_call', return_value=mock_papers):
            result = get_venue_papers(
                mock_client,
                'ICLR.cc/2024/Conference',
                only_accepted=True,
                verbose=False
            )
        
        assert len(result) == 2
    
    def test_get_all_submissions(self):
        """测试获取所有提交"""
        mock_client = Mock()
        single_blind = [MockPaper('paper1')]
        double_blind = [MockPaper('paper2')]
        
        with patch('paper_scraper.paper.safe_api_call', side_effect=[single_blind, double_blind]):
            with patch('paper_scraper.paper.time.sleep'):  # 跳过延迟
                result = get_venue_papers(
                    mock_client,
                    'ICLR.cc/2024/Conference',
                    only_accepted=False,
                    verbose=False,
                    delay=0
                )
        
        assert len(result) == 2
    
    def test_deduplication(self):
        """测试自动去重"""
        mock_client = Mock()
        mock_papers = [
            MockPaper('paper1'),
            MockPaper('paper1'),  # 重复
            MockPaper('paper2'),
        ]
        
        with patch('paper_scraper.paper.safe_api_call', return_value=mock_papers):
            result = get_venue_papers(
                mock_client,
                'ICLR.cc/2024/Conference',
                verbose=False
            )
        
        assert len(result) == 2
    
    def test_api_error(self):
        """测试 API 错误处理"""
        mock_client = Mock()
        
        with patch('paper_scraper.paper.safe_api_call', side_effect=Exception("API Error")):
            result = get_venue_papers(
                mock_client,
                'ICLR.cc/2024/Conference',
                verbose=False
            )
        
        assert result == []
    
    def test_none_response(self):
        """测试 API 返回 None"""
        mock_client = Mock()
        
        with patch('paper_scraper.paper.safe_api_call', return_value=None):
            result = get_venue_papers(
                mock_client,
                'ICLR.cc/2024/Conference',
                verbose=False
            )
        
        assert result == []


# ============ get_grouped_venue_papers 测试 ============

class TestGetGroupedVenuePapers:
    """测试多 venue 论文获取"""
    
    def test_multiple_venues(self):
        """测试多个 venue"""
        mock_client = Mock()
        papers_v1 = [MockPaper('paper1')]
        papers_v2 = [MockPaper('paper2')]
        
        with patch('paper_scraper.paper.safe_api_call', side_effect=[papers_v1, papers_v2]):
            with patch('paper_scraper.paper.time.sleep'):  # 跳过延迟
                result = get_grouped_venue_papers(
                    mock_client,
                    ['venue1', 'venue2'],
                    verbose=False,
                    delay_between_venues=0
                )
        
        assert 'venue1' in result
        assert 'venue2' in result
        assert len(result['venue1']) == 1
        assert len(result['venue2']) == 1
    
    def test_empty_venues(self):
        """测试空 venue 列表"""
        mock_client = Mock()
        
        result = get_grouped_venue_papers(
            mock_client,
            [],
            verbose=False
        )
        
        assert result == {}
    
    def test_single_venue(self):
        """测试单个 venue"""
        mock_client = Mock()
        mock_papers = [MockPaper('paper1'), MockPaper('paper2')]
        
        with patch('paper_scraper.paper.safe_api_call', return_value=mock_papers):
            result = get_grouped_venue_papers(
                mock_client,
                ['ICLR.cc/2024/Conference'],
                verbose=False
            )
        
        assert len(result) == 1
        assert len(result['ICLR.cc/2024/Conference']) == 2


# ============ get_papers 测试 ============

class TestGetPapers:
    """测试分组论文获取"""
    
    def test_grouped_conferences(self):
        """测试按会议分组"""
        mock_client = Mock()
        
        # 模拟不同会议的论文
        def mock_get_papers(client, venues, **kwargs):
            return {v: [MockPaper(f'{v}_paper')] for v in venues}
        
        with patch('paper_scraper.paper.get_grouped_venue_papers', side_effect=mock_get_papers):
            result = get_papers(
                mock_client,
                {
                    'ICLR': ['ICLR.cc/2024/Conference'],
                    'ICML': ['ICML.cc/2024/Conference'],
                },
                verbose=False
            )
        
        assert 'ICLR' in result
        assert 'ICML' in result
    
    def test_empty_grouped_venues(self):
        """测试空分组"""
        mock_client = Mock()
        
        result = get_papers(mock_client, {}, verbose=False)
        
        assert result == {}


# ============ count_papers 测试 ============

class TestCountPapers:
    """测试论文统计"""
    
    def test_count_multiple_conferences(self):
        """测试多会议统计"""
        papers = {
            'ICLR': {
                'venue1': [MockPaper('p1'), MockPaper('p2')],
                'venue2': [MockPaper('p3')],
            },
            'ICML': {
                'venue3': [MockPaper('p4')],
            },
        }
        
        counts = count_papers(papers)
        
        assert counts['ICLR'] == 3
        assert counts['ICML'] == 1
    
    def test_empty_papers(self):
        """测试空论文"""
        counts = count_papers({})
        
        assert counts == {}
    
    def test_empty_venues(self):
        """测试空 venue"""
        papers = {
            'ICLR': {
                'venue1': [],
                'venue2': [],
            },
        }
        
        counts = count_papers(papers)
        
        assert counts['ICLR'] == 0


# ============ flatten_papers 测试 ============

class TestFlattenPapers:
    """测试论文展平"""
    
    def test_flatten_multiple_venues(self):
        """测试展平多个 venue"""
        papers = {
            'ICLR': {
                'venue1': [MockPaper('p1'), MockPaper('p2')],
                'venue2': [MockPaper('p3')],
            },
            'ICML': {
                'venue3': [MockPaper('p4')],
            },
        }
        
        result = flatten_papers(papers)
        
        assert len(result) == 4
    
    def test_flatten_with_duplicates(self):
        """测试展平时去重"""
        papers = {
            'ICLR': {
                'venue1': [MockPaper('p1')],
                'venue2': [MockPaper('p1')],  # 同一篇论文在不同 venue
            },
        }
        
        result = flatten_papers(papers)
        
        assert len(result) == 1
    
    def test_flatten_empty(self):
        """测试空输入"""
        result = flatten_papers({})
        
        assert result == []


# ============ get_paper_ids 测试 ============

class TestGetPaperIds:
    """测试论文 ID 提取"""
    
    def test_extract_from_objects(self):
        """测试从对象提取"""
        papers = [
            MockPaper('paper1'),
            MockPaper('paper2'),
        ]
        
        ids = get_paper_ids(papers)
        
        assert ids == ['paper1', 'paper2']
    
    def test_extract_from_dicts(self):
        """测试从字典提取"""
        papers = [
            {'forum': 'paper1'},
            {'forum': 'paper2'},
        ]
        
        ids = get_paper_ids(papers)
        
        assert ids == ['paper1', 'paper2']
    
    def test_empty_list(self):
        """测试空列表"""
        ids = get_paper_ids([])
        
        assert ids == []
    
    def test_mixed_format(self):
        """测试混合格式"""
        papers = [
            MockPaper('paper1'),
            {'forum': 'paper2'},
        ]
        
        ids = get_paper_ids(papers)
        
        assert ids == ['paper1', 'paper2']


# ============ 集成测试 ============

class TestPaperIntegration:
    """集成测试"""
    
    def test_full_workflow(self):
        """测试完整工作流"""
        mock_client = Mock()
        
        # 模拟 API 返回
        def mock_api_call(func, **kwargs):
            if 'venueid' in kwargs.get('content', {}):
                venue = kwargs['content']['venueid']
                return [MockPaper(f'{venue}_paper1'), MockPaper(f'{venue}_paper2')]
            return []
        
        with patch('paper_scraper.paper.safe_api_call', side_effect=mock_api_call):
            with patch('paper_scraper.paper.time.sleep'):
                # 获取论文
                grouped_venues = {
                    'ICLR': ['ICLR.cc/2024/Conference'],
                }
                papers = get_papers(mock_client, grouped_venues, verbose=False)
                
                # 统计
                counts = count_papers(papers)
                assert counts['ICLR'] == 2
                
                # 展平
                flat = flatten_papers(papers)
                assert len(flat) == 2
                
                # 提取 ID
                ids = get_paper_ids(flat)
                assert len(ids) == 2

