"""
utils 模块测试

测试工具函数的正确性。
"""
import os
import csv
import tempfile
import pytest
from unittest.mock import Mock, patch, MagicMock

from paper_scraper.utils import (
    retry_with_backoff,
    safe_api_call,
    papers_to_list,
    to_csv,
    save_papers,
    load_papers,
    _clean_value,
    _clean_text_field,
    _extract_forum_id,
    DEFAULT_CSV_FIELDS,
)


# ============ retry_with_backoff 测试 ============

class TestRetryWithBackoff:
    """测试重试装饰器"""
    
    def test_success_on_first_try(self):
        """测试首次调用成功"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = success_func()
        assert result == "success"
        assert call_count == 1
    
    def test_success_after_retry(self):
        """测试重试后成功"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def fail_then_success():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Temporary error")
            return "success"
        
        result = fail_then_success()
        assert result == "success"
        assert call_count == 2
    
    def test_max_retries_exceeded(self):
        """测试超过最大重试次数"""
        call_count = 0
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def always_fail():
            nonlocal call_count
            call_count += 1
            raise Exception("Always fails")
        
        with pytest.raises(Exception, match="Always fails"):
            always_fail()
        
        assert call_count == 3
    
    def test_rate_limit_detection(self, capsys):
        """测试 429 错误检测"""
        call_count = 0
        
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def rate_limited():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("429 Too Many Requests")
            return "success"
        
        result = rate_limited()
        assert result == "success"
        
        captured = capsys.readouterr()
        assert "429" in captured.out or "限流" in captured.out


class TestSafeApiCall:
    """测试安全 API 调用"""
    
    def test_successful_call(self):
        """测试成功调用"""
        mock_func = Mock(return_value="result")
        result = safe_api_call(mock_func, "arg1", key="value")
        
        assert result == "result"
        mock_func.assert_called_once_with("arg1", key="value")


# ============ 数据转换测试 ============

class TestPapersToList:
    """测试论文字典转列表"""
    
    def test_basic_conversion(self):
        """测试基本转换"""
        papers = {
            'ICLR': {
                'ICLR.cc/2024/Conference': [
                    {'title': 'Paper 1'},
                    {'title': 'Paper 2'},
                ]
            }
        }
        
        result = papers_to_list(papers)
        
        assert len(result) == 2
        assert result[0]['title'] == 'Paper 1'
        assert result[1]['title'] == 'Paper 2'
    
    def test_multiple_venues(self):
        """测试多个 venue"""
        papers = {
            'ICLR': {
                'Venue1': [{'title': 'P1'}],
                'Venue2': [{'title': 'P2'}],
            },
            'ICML': {
                'Venue3': [{'title': 'P3'}],
            }
        }
        
        result = papers_to_list(papers)
        
        assert len(result) == 3
    
    def test_empty_input(self):
        """测试空输入"""
        result = papers_to_list({})
        assert result == []


# ============ 清理函数测试 ============

class TestCleanValue:
    """测试值清理函数"""
    
    def test_none_value(self):
        """测试 None 值"""
        assert _clean_value(None) == ''
    
    def test_string_value(self):
        """测试字符串值"""
        assert _clean_value("hello") == "hello"
    
    def test_dict_value(self):
        """测试字典值"""
        result = _clean_value({"key": "value"})
        assert '"key"' in result and '"value"' in result
    
    def test_list_value(self):
        """测试列表值"""
        result = _clean_value(["a", "b"])
        assert '"a"' in result and '"b"' in result
    
    def test_int_value(self):
        """测试整数值"""
        assert _clean_value(123) == "123"


class TestCleanTextField:
    """测试文本字段清理"""
    
    def test_newline_removal(self):
        """测试换行符移除"""
        text = "Hello\nWorld\r\nTest"
        result = _clean_text_field(text)
        assert '\n' not in result
        assert '\r' not in result
        assert result == "Hello World Test"
    
    def test_multiple_spaces(self):
        """测试多余空格清理"""
        text = "Hello    World"
        result = _clean_text_field(text)
        assert result == "Hello World"
    
    def test_strip_whitespace(self):
        """测试首尾空白移除"""
        text = "  Hello World  "
        result = _clean_text_field(text)
        assert result == "Hello World"


class TestExtractForumId:
    """测试 forum ID 提取"""
    
    def test_full_url(self):
        """测试完整 URL"""
        url = "https://openreview.net/forum?id=abc123"
        assert _extract_forum_id(url) == "abc123"
    
    def test_simple_id(self):
        """测试简单 ID"""
        assert _extract_forum_id("abc123") == "abc123"
    
    def test_empty_string(self):
        """测试空字符串"""
        assert _extract_forum_id("") is None
    
    def test_none_value(self):
        """测试 None 值"""
        assert _extract_forum_id(None) is None


# ============ CSV 导出测试 ============

class TestToCsv:
    """测试 CSV 导出"""
    
    def test_basic_export(self):
        """测试基本导出"""
        papers = [
            {
                'title': 'Test Paper',
                'abstract': 'This is abstract',
                'keywords': 'AI, ML',
                'pdf': 'http://example.com/paper.pdf',
                'forum': 'abc123',
                'year': '2024',
                'presentation_type': 'Poster'
            }
        ]
        
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_papers.csv', delete=False
        ) as f:
            fpath = f.name
        
        try:
            to_csv(papers, fpath)
            
            # 验证文件存在
            assert os.path.exists(fpath)
            
            # 读取并验证内容
            with open(fpath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 1
            assert rows[0]['title'] == 'Test Paper'
            assert rows[0]['abstract'] == 'This is abstract'
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
    
    def test_empty_list(self):
        """测试空列表导出"""
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.csv', delete=False
        ) as f:
            fpath = f.name
        
        try:
            to_csv([], fpath)
            
            # 验证文件存在且只有表头
            with open(fpath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            assert len(rows) == 0
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
    
    def test_deduplication(self):
        """测试去重"""
        papers = [
            {'title': 'Paper 1', 'forum': 'abc123', 'year': '2024'},
            {'title': 'Paper 1 (dup)', 'forum': 'abc123', 'year': '2024'},  # 重复
            {'title': 'Paper 2', 'forum': 'def456', 'year': '2024'},
        ]
        
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_papers.csv', delete=False
        ) as f:
            fpath = f.name
        
        try:
            to_csv(papers, fpath)
            
            with open(fpath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # 应该只有 2 条记录（去重后）
            assert len(rows) == 2
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
    
    def test_newline_in_abstract(self):
        """测试摘要中的换行符被清理"""
        papers = [
            {
                'title': 'Test',
                'abstract': 'Line 1\nLine 2\r\nLine 3',
                'forum': 'test123',
                'year': '2024',
            }
        ]
        
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_papers.csv', delete=False
        ) as f:
            fpath = f.name
        
        try:
            to_csv(papers, fpath)
            
            with open(fpath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # 换行符应该被替换为空格
            assert '\n' not in rows[0]['abstract']
            assert '\r' not in rows[0]['abstract']
            assert 'Line 1 Line 2 Line 3' == rows[0]['abstract']
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
    
    def test_auto_id_generation(self):
        """测试自动 ID 生成"""
        papers = [
            {'title': 'Paper A', 'forum': 'a', 'year': '2024'},
            {'title': 'Paper B', 'forum': 'b', 'year': '2024'},
        ]
        
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='_papers.csv', delete=False, prefix='test'
        ) as f:
            fpath = f.name
        
        try:
            to_csv(papers, fpath)
            
            with open(fpath, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                rows = list(reader)
            
            # 应该有自动生成的 ID
            assert rows[0]['id'].endswith('_1')
            assert rows[1]['id'].endswith('_2')
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)


# ============ PKL 序列化测试 ============

class TestPklSerialization:
    """测试 PKL 序列化/反序列化"""
    
    def test_save_and_load(self):
        """测试保存和加载"""
        papers = {
            'ICLR': {
                'venue1': [{'title': 'Test Paper'}]
            }
        }
        
        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.pkl', delete=False
        ) as f:
            fpath = f.name
        
        try:
            save_papers(papers, fpath)
            loaded = load_papers(fpath)
            
            assert loaded == papers
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)
    
    def test_load_complex_objects(self):
        """测试加载复杂对象"""
        # 包含各种类型的数据
        data = {
            'list': [1, 2, 3],
            'dict': {'nested': True},
            'string': 'hello',
            'none': None,
        }
        
        with tempfile.NamedTemporaryFile(
            mode='wb', suffix='.pkl', delete=False
        ) as f:
            fpath = f.name
        
        try:
            save_papers(data, fpath)
            loaded = load_papers(fpath)
            
            assert loaded == data
        finally:
            if os.path.exists(fpath):
                os.remove(fpath)

