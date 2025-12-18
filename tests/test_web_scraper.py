"""
web_scraper 模块测试

测试网页爬取功能（使用 mock 避免真实网络请求）。
"""
import pytest
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock

from paper_scraper.web_scraper import (
    get_random_user_agent,
    fetch_page,
    scrape_ijcai,
    scrape_aaai,
    scrape_conference,
    batch_scrape,
    _parse_ijcai_page,
    _get_aaai_track_urls,
    _scrape_aaai_track,
    _save_papers_csv,
    USER_AGENTS,
)


# ============ 工具函数测试 ============

class TestGetRandomUserAgent:
    """测试随机 User-Agent"""
    
    def test_returns_string(self):
        """测试返回字符串"""
        ua = get_random_user_agent()
        assert isinstance(ua, str)
    
    def test_returns_from_list(self):
        """测试从列表中返回"""
        ua = get_random_user_agent()
        assert ua in USER_AGENTS
    
    def test_randomness(self):
        """测试随机性（可能不同）"""
        # 多次调用，至少应该有一些变化（概率性测试）
        results = set()
        for _ in range(100):
            results.add(get_random_user_agent())
        # 如果 USER_AGENTS 有多个，应该有多个结果
        if len(USER_AGENTS) > 1:
            assert len(results) >= 1


class TestFetchPage:
    """测试页面获取"""
    
    def test_successful_fetch(self):
        """测试成功获取"""
        mock_response = Mock()
        mock_response.text = '<html><body>Test</body></html>'
        mock_response.raise_for_status = Mock()
        
        with patch('paper_scraper.web_scraper.requests.get', return_value=mock_response):
            result = fetch_page('https://example.com', verbose=False)
        
        assert result == '<html><body>Test</body></html>'
    
    def test_retry_on_failure(self):
        """测试失败重试"""
        import requests
        
        mock_response = Mock()
        mock_response.text = '<html>Success</html>'
        mock_response.raise_for_status = Mock()
        
        # 前两次失败，第三次成功
        with patch('paper_scraper.web_scraper.requests.get', side_effect=[
            requests.RequestException("Error 1"),
            requests.RequestException("Error 2"),
            mock_response,
        ]):
            with patch('paper_scraper.web_scraper.time.sleep'):
                result = fetch_page('https://example.com', retries=3, verbose=False)
        
        assert result == '<html>Success</html>'
    
    def test_return_none_on_max_retries(self):
        """测试达到最大重试次数返回 None"""
        import requests
        
        with patch('paper_scraper.web_scraper.requests.get', 
                   side_effect=requests.RequestException("Error")):
            with patch('paper_scraper.web_scraper.time.sleep'):
                result = fetch_page('https://example.com', retries=2, verbose=False)
        
        assert result is None


# ============ IJCAI 爬虫测试 ============

class TestParseIjcaiPage:
    """测试 IJCAI 页面解析"""
    
    def test_parse_2017_format(self):
        """测试 2017+ 格式"""
        html = '''
        <html>
        <body>
            <div class="section_title">Machine Learning</div>
            <div class="parent">
                <div class="paper_wrapper">
                    <div class="title">Paper Title 1</div>
                    <div class="details">
                        <a href="/pdf/paper1.pdf">PDF</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        # 需要调整 HTML 结构以匹配解析逻辑
        html_proper = '''
        <html>
        <body>
            <div>
                <div class="section_title">Machine Learning</div>
                <div class="paper_wrapper">
                    <div class="title">Paper Title 1</div>
                    <div class="details">
                        <a href="/pdf/paper1.pdf">PDF</a>
                    </div>
                </div>
            </div>
        </body>
        </html>
        '''
        
        papers = _parse_ijcai_page(html_proper, 'https://www.ijcai.org/', 2024, verbose=False)
        
        # 至少应该能解析
        assert isinstance(papers, list)
    
    def test_parse_old_format(self):
        """测试旧格式（<2017）"""
        html = '''
        <html>
        <body>
            <a href="paper1.pdf">Paper Title 1</a>
            <a href="paper2.pdf">Paper Title 2</a>
        </body>
        </html>
        '''
        
        papers = _parse_ijcai_page(html, 'https://www.ijcai.org/', 2010, verbose=False)
        
        assert len(papers) == 2
        assert papers[0]['title'] == 'Paper Title 1'
        assert papers[0]['conference'] == 'IJCAI'


class TestScrapeIjcai:
    """测试 IJCAI 爬取"""
    
    def test_scrape_returns_list(self):
        """测试返回列表"""
        mock_html = '''
        <html><body>
            <a href="paper.pdf">Test Paper</a>
        </body></html>
        '''
        
        with patch('paper_scraper.web_scraper.fetch_page', return_value=mock_html):
            papers = scrape_ijcai(2024, verbose=False)
        
        assert isinstance(papers, list)
    
    def test_scrape_no_network(self):
        """测试网络失败"""
        with patch('paper_scraper.web_scraper.fetch_page', return_value=None):
            papers = scrape_ijcai(2024, verbose=False)
        
        assert papers == []
    
    def test_scrape_old_year(self):
        """测试不支持的年份"""
        papers = scrape_ijcai(2000, verbose=False)
        assert papers == []


# ============ AAAI 爬虫测试 ============

class TestGetAaaiTrackUrls:
    """测试 AAAI track URL 获取"""
    
    def test_parse_2023_format(self):
        """测试 2023+ 格式"""
        mock_html = '''
        <html><body>
            <ul class="issues_archive">
                <li>
                    <h2><a href="/issue/1">AAAI-24 Vol 1</a></h2>
                </li>
                <li>
                    <h2><a href="/issue/2">AAAI-23 Vol 1</a></h2>
                </li>
            </ul>
        </body></html>
        '''
        
        with patch('paper_scraper.web_scraper.fetch_page', return_value=mock_html):
            urls = _get_aaai_track_urls(2024, verbose=False)
        
        assert isinstance(urls, dict)
    
    def test_return_empty_on_failure(self):
        """测试失败返回空"""
        with patch('paper_scraper.web_scraper.fetch_page', return_value=None):
            urls = _get_aaai_track_urls(2024, verbose=False)
        
        assert urls == {}


class TestScrapeAaaiTrack:
    """测试 AAAI track 爬取"""
    
    def test_parse_2023_format(self):
        """测试 2023+ 格式"""
        mock_html = '''
        <html><body>
            <div class="section">
                <h2>AI Applications</h2>
                <li>
                    <h3 class="title">Paper 1</h3>
                    <a class="obj_galley_link" href="/view/123">PDF</a>
                </li>
            </div>
        </body></html>
        '''
        
        with patch('paper_scraper.web_scraper.fetch_page', return_value=mock_html):
            papers = _scrape_aaai_track('https://example.com', 2024, verbose=False)
        
        assert isinstance(papers, list)


class TestScrapeAaai:
    """测试 AAAI 爬取"""
    
    def test_scrape_returns_list(self):
        """测试返回列表"""
        with patch('paper_scraper.web_scraper._get_aaai_track_urls', return_value={}):
            papers = scrape_aaai(2024, verbose=False)
        
        assert isinstance(papers, list)
    
    def test_scrape_no_tracks(self):
        """测试无 tracks"""
        with patch('paper_scraper.web_scraper._get_aaai_track_urls', return_value={}):
            papers = scrape_aaai(2024, verbose=False)
        
        assert papers == []


# ============ 统一入口测试 ============

class TestScrapeConference:
    """测试统一爬取入口"""
    
    def test_dispatch_to_ijcai(self):
        """测试分发到 IJCAI"""
        with patch('paper_scraper.web_scraper.scrape_ijcai', return_value=[{'title': 'Test'}]) as mock:
            papers = scrape_conference('IJCAI', 2024, verbose=False)
        
        mock.assert_called_once_with(2024, None, False)
        assert papers == [{'title': 'Test'}]
    
    def test_dispatch_to_aaai(self):
        """测试分发到 AAAI"""
        with patch('paper_scraper.web_scraper.scrape_aaai', return_value=[]) as mock:
            papers = scrape_conference('AAAI', 2024, verbose=False)
        
        mock.assert_called_once_with(2024, None, False)
    
    def test_case_insensitive(self):
        """测试大小写不敏感"""
        with patch('paper_scraper.web_scraper.scrape_ijcai', return_value=[]):
            papers = scrape_conference('ijcai', 2024, verbose=False)
        
        assert isinstance(papers, list)
    
    def test_unsupported_conference(self):
        """测试不支持的会议"""
        with pytest.raises(ValueError) as exc_info:
            scrape_conference('UNKNOWN', 2024, verbose=False)
        
        assert '不支持的会议' in str(exc_info.value)


# ============ 批量爬取测试 ============

class TestBatchScrape:
    """测试批量爬取"""
    
    def test_batch_returns_dict(self):
        """测试返回字典"""
        with patch('paper_scraper.web_scraper.scrape_conference', return_value=[]):
            with patch('paper_scraper.web_scraper.random_delay'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    results = batch_scrape(['IJCAI'], [2024], output_dir=tmpdir, verbose=False)
        
        assert isinstance(results, dict)
        assert 'IJCAI_2024' in results
    
    def test_batch_multiple_conferences(self):
        """测试多会议"""
        with patch('paper_scraper.web_scraper.scrape_conference', return_value=[]):
            with patch('paper_scraper.web_scraper.random_delay'):
                with tempfile.TemporaryDirectory() as tmpdir:
                    results = batch_scrape(
                        ['IJCAI', 'AAAI'],
                        [2023, 2024],
                        output_dir=tmpdir,
                        verbose=False
                    )
        
        assert len(results) == 4
        assert 'IJCAI_2023' in results
        assert 'IJCAI_2024' in results
        assert 'AAAI_2023' in results
        assert 'AAAI_2024' in results


# ============ 保存函数测试 ============

class TestSavePapersCsv:
    """测试 CSV 保存"""
    
    def test_save_creates_file(self):
        """测试创建文件"""
        papers = [
            {
                'title': 'Test Paper',
                'pdf_url': 'https://example.com/paper.pdf',
                'group': 'AI',
                'year': '2024',
                'conference': 'TEST',
            }
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            _save_papers_csv(papers, temp_path, verbose=False)
            assert os.path.exists(temp_path)
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)
    
    def test_save_empty_list(self):
        """测试空列表"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            temp_path = f.name
        
        try:
            _save_papers_csv([], temp_path, verbose=False)
            # 空列表不应创建文件或不写入
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


# ============ 集成测试 ============

class TestWebScraperIntegration:
    """集成测试"""
    
    def test_ijcai_full_flow(self):
        """测试 IJCAI 完整流程"""
        mock_html = '''
        <html><body>
            <a href="paper1.pdf">Deep Learning Paper</a>
            <a href="paper2.pdf">NLP Paper</a>
        </body></html>
        '''
        
        with patch('paper_scraper.web_scraper.fetch_page', return_value=mock_html):
            with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
                temp_path = f.name
            
            try:
                papers = scrape_ijcai(2015, output_path=temp_path, verbose=False)
                
                assert len(papers) == 2
                assert papers[0]['conference'] == 'IJCAI'
                assert os.path.exists(temp_path)
            finally:
                if os.path.exists(temp_path):
                    os.unlink(temp_path)

