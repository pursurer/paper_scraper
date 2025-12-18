"""
config 模块测试

测试配置管理功能。
"""
import pytest
import os
from unittest.mock import patch

from config import Config, get_config, reset_config


# ============ Config 类测试 ============

class TestConfigInit:
    """测试 Config 初始化"""
    
    def test_default_values(self):
        """测试默认值"""
        config = Config()
        
        assert config.request_delay_min == 2.0
        assert config.request_delay_max == 5.0
        assert config.request_timeout == 30
        assert config.request_retries == 3
        assert config.verbose is True
    
    def test_defaults_dict(self):
        """测试默认值字典"""
        assert 'openreview_email' in Config.DEFAULTS
        assert 'request_timeout' in Config.DEFAULTS
    
    def test_env_mapping(self):
        """测试环境变量映射"""
        assert 'openreview_email' in Config.ENV_MAPPING
        assert Config.ENV_MAPPING['openreview_email'] == 'OPENREVIEW_EMAIL'


class TestConfigEnvLoading:
    """测试从环境变量加载配置"""
    
    def test_load_email_from_env(self):
        """测试从环境变量加载邮箱"""
        with patch.dict(os.environ, {'OPENREVIEW_EMAIL': 'test@example.com'}):
            config = Config()
            assert config.openreview_email == 'test@example.com'
    
    def test_load_delay_from_env(self):
        """测试从环境变量加载延迟"""
        with patch.dict(os.environ, {'PAPER_SCRAPER_DELAY_MIN': '3.0'}):
            config = Config()
            assert config.request_delay_min == 3.0
    
    def test_load_timeout_from_env(self):
        """测试从环境变量加载超时"""
        with patch.dict(os.environ, {'PAPER_SCRAPER_TIMEOUT': '60'}):
            config = Config()
            assert config.request_timeout == 60
    
    def test_load_verbose_from_env(self):
        """测试从环境变量加载 verbose"""
        with patch.dict(os.environ, {'PAPER_SCRAPER_VERBOSE': 'false'}):
            config = Config()
            assert config.verbose is False
        
        with patch.dict(os.environ, {'PAPER_SCRAPER_VERBOSE': 'true'}):
            config = Config()
            assert config.verbose is True


class TestConfigGetSet:
    """测试配置获取和设置"""
    
    def test_get_existing_key(self):
        """测试获取存在的键"""
        config = Config()
        assert config.get('request_timeout') == 30
    
    def test_get_nonexistent_key(self):
        """测试获取不存在的键"""
        config = Config()
        assert config.get('nonexistent') is None
        assert config.get('nonexistent', 'default') == 'default'
    
    def test_set_value(self):
        """测试设置值"""
        config = Config()
        config.set('custom_key', 'custom_value')
        assert config.get('custom_key') == 'custom_value'


class TestConfigProperties:
    """测试配置属性"""
    
    def test_openreview_email(self):
        """测试 openreview_email 属性"""
        config = Config()
        config.set('openreview_email', 'test@example.com')
        assert config.openreview_email == 'test@example.com'
    
    def test_has_credentials_false(self):
        """测试无凭证"""
        config = Config()
        config.set('openreview_email', None)
        config.set('openreview_password', None)
        assert config.has_credentials is False
    
    def test_has_credentials_true(self):
        """测试有凭证"""
        config = Config()
        config.set('openreview_email', 'test@example.com')
        config.set('openreview_password', 'password')
        assert config.has_credentials is True
    
    def test_output_dir(self):
        """测试 output_dir 属性"""
        config = Config()
        assert config.output_dir == './output'


class TestConfigToDict:
    """测试配置转字典"""
    
    def test_to_dict_returns_dict(self):
        """测试返回字典"""
        config = Config()
        result = config.to_dict()
        assert isinstance(result, dict)
    
    def test_to_dict_hides_password(self):
        """测试隐藏密码"""
        config = Config()
        config.set('openreview_password', 'secret')
        result = config.to_dict()
        assert result['openreview_password'] == '***'
    
    def test_repr(self):
        """测试 repr"""
        config = Config()
        repr_str = repr(config)
        assert 'Config(' in repr_str


# ============ 全局配置测试 ============

class TestGlobalConfig:
    """测试全局配置"""
    
    def setup_method(self):
        """每个测试前重置配置"""
        reset_config()
    
    def test_get_config_returns_config(self):
        """测试获取全局配置"""
        config = get_config()
        assert isinstance(config, Config)
    
    def test_get_config_singleton(self):
        """测试单例模式"""
        config1 = get_config()
        config2 = get_config()
        assert config1 is config2
    
    def test_reset_config(self):
        """测试重置配置"""
        config1 = get_config()
        reset_config()
        config2 = get_config()
        assert config1 is not config2


# ============ 集成测试 ============

class TestConfigIntegration:
    """集成测试"""
    
    def test_full_config_flow(self):
        """测试完整配置流程"""
        reset_config()
        
        # 设置环境变量
        with patch.dict(os.environ, {
            'OPENREVIEW_EMAIL': 'test@example.com',
            'PAPER_SCRAPER_TIMEOUT': '45',
            'PAPER_SCRAPER_VERBOSE': 'false',
        }):
            config = Config()
            
            assert config.openreview_email == 'test@example.com'
            assert config.request_timeout == 45
            assert config.verbose is False
            
            # 默认值应该保持
            assert config.request_delay_min == 2.0
    
    def test_config_precedence(self):
        """测试配置优先级"""
        # 环境变量应该覆盖默认值
        with patch.dict(os.environ, {'PAPER_SCRAPER_RETRIES': '5'}):
            config = Config()
            assert config.request_retries == 5

