"""
venue 模块测试

测试 Venue 发现与分组功能。
"""
import pytest
from unittest.mock import Mock, MagicMock, patch

from paper_scraper.venue import (
    filter_by_year,
    filter_by_conference,
    group_venues,
    get_all_subgroups,
    get_venues,
    _should_expand_venue,
    get_venue_info,
    format_venues_summary,
)


# ============ filter_by_year 测试 ============

class TestFilterByYear:
    """测试年份过滤"""
    
    def test_match_year(self):
        """测试年份匹配"""
        venue = 'ICLR.cc/2024/Conference'
        
        result = filter_by_year(venue, ['2024'])
        
        assert result == venue
    
    def test_no_match_year(self):
        """测试年份不匹配"""
        venue = 'ICLR.cc/2024/Conference'
        
        result = filter_by_year(venue, ['2023', '2025'])
        
        assert result is None
    
    def test_multiple_years(self):
        """测试多年份"""
        venue = 'ICML.cc/2023/Conference'
        
        result = filter_by_year(venue, ['2022', '2023', '2024'])
        
        assert result == venue
    
    def test_none_venue(self):
        """测试 None 输入"""
        result = filter_by_year(None, ['2024'])
        
        assert result is None
    
    def test_empty_years(self):
        """测试空年份列表"""
        venue = 'ICLR.cc/2024/Conference'
        
        result = filter_by_year(venue, [])
        
        assert result is None


# ============ filter_by_conference 测试 ============

class TestFilterByConference:
    """测试会议过滤"""
    
    def test_match_conference(self):
        """测试会议匹配"""
        venue = 'ICLR.cc/2024/Conference'
        
        result = filter_by_conference(venue, ['ICLR'])
        
        assert result is True
    
    def test_no_match_conference(self):
        """测试会议不匹配"""
        venue = 'ICLR.cc/2024/Conference'
        
        result = filter_by_conference(venue, ['ICML', 'NeurIPS'])
        
        assert result is False
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        venue = 'ICLR.cc/2024/Conference'
        
        result = filter_by_conference(venue, ['iclr'])
        
        assert result is True
    
    def test_partial_match(self):
        """测试部分匹配"""
        venue = 'NeurIPS.cc/2024/Conference'
        
        result = filter_by_conference(venue, ['NeurIPS'])
        
        assert result is True
    
    def test_none_venue(self):
        """测试 None 输入"""
        result = filter_by_conference(None, ['ICLR'])
        
        assert result is False


# ============ group_venues 测试 ============

class TestGroupVenues:
    """测试 Venue 分组"""
    
    def test_basic_grouping(self):
        """测试基本分组"""
        venues = [
            'ICLR.cc/2024/Conference',
            'ICML.cc/2024/Conference',
            'ICLR.cc/2023/Conference',
        ]
        
        grouped = group_venues(venues, ['ICLR', 'ICML'])
        
        assert len(grouped['ICLR']) == 2
        assert len(grouped['ICML']) == 1
    
    def test_empty_group(self):
        """测试空分组"""
        venues = ['ICLR.cc/2024/Conference']
        
        grouped = group_venues(venues, ['ICLR', 'ICML', 'NeurIPS'])
        
        assert len(grouped['ICLR']) == 1
        assert len(grouped['ICML']) == 0
        assert len(grouped['NeurIPS']) == 0
    
    def test_empty_venues(self):
        """测试空 venues 列表"""
        grouped = group_venues([], ['ICLR', 'ICML'])
        
        assert grouped == {'ICLR': [], 'ICML': []}
    
    def test_no_matching_conference(self):
        """测试无匹配的会议"""
        venues = ['Unknown.cc/2024/Conference']
        
        grouped = group_venues(venues, ['ICLR', 'ICML'])
        
        assert all(len(v) == 0 for v in grouped.values())


# ============ get_all_subgroups 测试 ============

class TestGetAllSubgroups:
    """测试子组获取"""
    
    def test_basic_subgroups(self):
        """测试基本子组获取"""
        # 模拟 API client
        mock_client = Mock()
        mock_group = Mock()
        mock_group.members = [
            'AAAI.org/2025/Conference',
            'AAAI.org/2025/Track/Main',
            'AAAI.org/2025/Track/AI_for_Science',
            'AAAI.org/2024/Conference',  # 不同年份，应排除
            'AAAI.org/2025/Reviewers',  # 审稿人组，应排除
        ]
        mock_client.get_group.return_value = mock_group
        
        with patch('paper_scraper.venue.safe_api_call', return_value=mock_group):
            subgroups = get_all_subgroups(
                mock_client,
                'AAAI.org/2025/Conference',
                ['2025'],
                verbose=False
            )
        
        assert 'AAAI.org/2025/Conference' in subgroups
        assert 'AAAI.org/2025/Track/Main' in subgroups
        assert 'AAAI.org/2025/Track/AI_for_Science' in subgroups
        assert 'AAAI.org/2024/Conference' not in subgroups  # 年份不匹配
        assert 'AAAI.org/2025/Reviewers' not in subgroups  # 被排除
    
    def test_exclude_patterns(self):
        """测试排除模式"""
        mock_client = Mock()
        mock_group = Mock()
        mock_group.members = [
            'AAAI.org/2025/Conference',
            'AAAI.org/2025/Program_Chairs',
            'AAAI.org/2025/Area_Chairs',
            'AAAI.org/2025/Authors',
            'AAAI.org/2025/Track/Main',
        ]
        mock_client.get_group.return_value = mock_group
        
        with patch('paper_scraper.venue.safe_api_call', return_value=mock_group):
            subgroups = get_all_subgroups(
                mock_client,
                'AAAI.org/2025/Conference',
                ['2025'],
                verbose=False
            )
        
        # 只应包含 Conference 和 Track/Main
        assert len(subgroups) == 2
        assert 'AAAI.org/2025/Conference' in subgroups
        assert 'AAAI.org/2025/Track/Main' in subgroups
    
    def test_api_failure(self):
        """测试 API 失败"""
        mock_client = Mock()
        
        with patch('paper_scraper.venue.safe_api_call', side_effect=Exception("API Error")):
            subgroups = get_all_subgroups(
                mock_client,
                'AAAI.org/2025/Conference',
                ['2025'],
                verbose=False
            )
        
        # 应至少返回父组
        assert subgroups == ['AAAI.org/2025/Conference']


# ============ get_venues 测试 ============

class TestGetVenues:
    """测试 Venue 获取"""
    
    def test_basic_get_venues(self):
        """测试基本 venue 获取"""
        mock_client = Mock()
        mock_group = Mock()
        mock_group.members = [
            'ICLR.cc/2024/Conference',
            'ICML.cc/2024/Conference',
            'NeurIPS.cc/2024/Conference',
            'ICLR.cc/2023/Conference',
        ]
        mock_client.get_group.return_value = mock_group
        
        with patch('paper_scraper.venue.safe_api_call', return_value=mock_group):
            venues = get_venues(
                mock_client,
                conferences=['ICLR'],
                years=['2024'],
                expand_subgroups=False,
                verbose=False
            )
        
        assert len(venues) == 1
        assert 'ICLR.cc/2024/Conference' in venues
    
    def test_multiple_conferences(self):
        """测试多会议"""
        mock_client = Mock()
        mock_group = Mock()
        mock_group.members = [
            'ICLR.cc/2024/Conference',
            'ICML.cc/2024/Conference',
            'NeurIPS.cc/2024/Conference',
        ]
        mock_client.get_group.return_value = mock_group
        
        with patch('paper_scraper.venue.safe_api_call', return_value=mock_group):
            venues = get_venues(
                mock_client,
                conferences=['ICLR', 'ICML'],
                years=['2024'],
                expand_subgroups=False,
                verbose=False
            )
        
        assert len(venues) == 2
        assert 'ICLR.cc/2024/Conference' in venues
        assert 'ICML.cc/2024/Conference' in venues
    
    def test_multiple_years(self):
        """测试多年份"""
        mock_client = Mock()
        mock_group = Mock()
        mock_group.members = [
            'ICLR.cc/2024/Conference',
            'ICLR.cc/2023/Conference',
            'ICLR.cc/2022/Conference',
        ]
        mock_client.get_group.return_value = mock_group
        
        with patch('paper_scraper.venue.safe_api_call', return_value=mock_group):
            venues = get_venues(
                mock_client,
                conferences=['ICLR'],
                years=['2023', '2024'],
                expand_subgroups=False,
                verbose=False
            )
        
        assert len(venues) == 2
        assert 'ICLR.cc/2024/Conference' in venues
        assert 'ICLR.cc/2023/Conference' in venues
    
    def test_no_matching_venues(self):
        """测试无匹配 venue"""
        mock_client = Mock()
        mock_group = Mock()
        mock_group.members = [
            'CVPR.cc/2024/Conference',
            'ECCV.cc/2024/Conference',
        ]
        mock_client.get_group.return_value = mock_group
        
        with patch('paper_scraper.venue.safe_api_call', return_value=mock_group):
            venues = get_venues(
                mock_client,
                conferences=['ICLR'],
                years=['2024'],
                expand_subgroups=False,
                verbose=False
            )
        
        assert len(venues) == 0
    
    def test_api_failure(self):
        """测试 API 失败"""
        mock_client = Mock()
        
        with patch('paper_scraper.venue.safe_api_call', side_effect=Exception("API Error")):
            venues = get_venues(
                mock_client,
                conferences=['ICLR'],
                years=['2024'],
                verbose=False
            )
        
        assert venues == []


# ============ _should_expand_venue 测试 ============

class TestShouldExpandVenue:
    """测试是否应展开 venue"""
    
    def test_conference_should_expand(self):
        """测试主 Conference 应该展开"""
        assert _should_expand_venue('AAAI.org/2025/Conference') is True
        assert _should_expand_venue('ICLR.cc/2024/Conference') is True
    
    def test_track_should_not_expand(self):
        """测试 Track 不应展开"""
        assert _should_expand_venue('AAAI.org/2025/Track/Main') is False
        assert _should_expand_venue('AAAI.org/2025/Demo_Track') is False
    
    def test_workshop_should_not_expand(self):
        """测试 Workshop 不应展开"""
        assert _should_expand_venue('ICLR.cc/2024/Workshop/X') is False
    
    def test_no_conference_suffix(self):
        """测试没有 Conference 后缀的不展开"""
        assert _should_expand_venue('ICLR.cc/2024') is False


# ============ get_venue_info 测试 ============

class TestGetVenueInfo:
    """测试 venue 信息解析"""
    
    def test_standard_venue(self):
        """测试标准 venue"""
        info = get_venue_info('ICLR.cc/2024/Conference')
        
        assert info['org'] == 'ICLR.cc'
        assert info['year'] == '2024'
        assert info['type'] == 'Conference'
    
    def test_track_venue(self):
        """测试 Track venue"""
        info = get_venue_info('AAAI.org/2025/Track/Main')
        
        assert info['org'] == 'AAAI.org'
        assert info['year'] == '2025'
        assert info['type'] == 'Main'
    
    def test_no_year(self):
        """测试没有年份的 venue"""
        info = get_venue_info('SomeConf.cc/Conference')
        
        assert info['year'] == ''
    
    def test_empty_venue(self):
        """测试空 venue"""
        info = get_venue_info('')
        
        assert info['org'] == ''
        assert info['year'] == ''


# ============ format_venues_summary 测试 ============

class TestFormatVenuesSummary:
    """测试 venue 摘要格式化"""
    
    def test_basic_summary(self):
        """测试基本摘要"""
        venues = [
            'ICLR.cc/2024/Conference',
            'ICML.cc/2024/Conference',
        ]
        
        summary = format_venues_summary(venues)
        
        assert 'Found 2 venues' in summary
        assert '2024' in summary
    
    def test_multiple_years(self):
        """测试多年份摘要"""
        venues = [
            'ICLR.cc/2024/Conference',
            'ICLR.cc/2023/Conference',
        ]
        
        summary = format_venues_summary(venues)
        
        assert '2024' in summary
        assert '2023' in summary
    
    def test_empty_venues(self):
        """测试空 venues"""
        summary = format_venues_summary([])
        
        assert 'No venues found' in summary


# ============ 集成测试 ============

class TestVenueIntegration:
    """集成测试"""
    
    def test_filter_and_group_workflow(self):
        """测试过滤和分组的完整流程"""
        all_venues = [
            'ICLR.cc/2024/Conference',
            'ICLR.cc/2023/Conference',
            'ICML.cc/2024/Conference',
            'NeurIPS.cc/2024/Conference',
            'CVPR.cc/2024/Conference',
        ]
        
        # 过滤年份
        filtered = [v for v in all_venues if filter_by_year(v, ['2024'])]
        assert len(filtered) == 4
        
        # 过滤会议
        filtered = [v for v in filtered if filter_by_conference(v, ['ICLR', 'ICML'])]
        assert len(filtered) == 2
        
        # 分组
        grouped = group_venues(filtered, ['ICLR', 'ICML'])
        assert grouped['ICLR'] == ['ICLR.cc/2024/Conference']
        assert grouped['ICML'] == ['ICML.cc/2024/Conference']

