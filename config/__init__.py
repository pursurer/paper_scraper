"""
配置模块

支持多种配置来源（优先级从高到低）：
1. 环境变量
2. config.py 文件
3. 默认值

Usage:
    from config import Config
    
    config = Config()
    print(config.openreview_email)
    print(config.request_delay)
"""
import os
import sys
from typing import Optional, Dict, Any


class Config:
    """
    配置管理类
    
    支持从环境变量和配置文件加载配置。
    """
    
    # 默认配置值
    DEFAULTS = {
        # OpenReview 凭证
        'openreview_email': None,
        'openreview_password': None,
        
        # 请求配置
        'request_delay_min': 2.0,  # 最小请求延迟（秒）
        'request_delay_max': 5.0,  # 最大请求延迟（秒）
        'request_timeout': 30,     # 请求超时（秒）
        'request_retries': 3,      # 重试次数
        
        # 输出配置
        'output_dir': './output',  # 默认输出目录
        'csv_encoding': 'utf-8-sig',  # CSV 编码
        
        # 日志配置
        'verbose': True,  # 是否打印详细日志
    }
    
    # 环境变量映射
    ENV_MAPPING = {
        'openreview_email': 'OPENREVIEW_EMAIL',
        'openreview_password': 'OPENREVIEW_PASSWORD',
        'request_delay_min': 'PAPER_SCRAPER_DELAY_MIN',
        'request_delay_max': 'PAPER_SCRAPER_DELAY_MAX',
        'request_timeout': 'PAPER_SCRAPER_TIMEOUT',
        'request_retries': 'PAPER_SCRAPER_RETRIES',
        'output_dir': 'PAPER_SCRAPER_OUTPUT_DIR',
        'verbose': 'PAPER_SCRAPER_VERBOSE',
    }
    
    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置。
        
        Args:
            config_file: 配置文件路径（可选）
        """
        self._config: Dict[str, Any] = {}
        self._load_defaults()
        self._load_from_file(config_file)
        self._load_from_env()
    
    def _load_defaults(self) -> None:
        """加载默认配置。"""
        self._config.update(self.DEFAULTS.copy())
    
    def _load_from_file(self, config_file: Optional[str] = None) -> None:
        """从配置文件加载配置。"""
        # 尝试从 config.py 加载
        try:
            from .config import EMAIL, PASSWORD
            if EMAIL:
                self._config['openreview_email'] = EMAIL
            if PASSWORD:
                self._config['openreview_password'] = PASSWORD
        except ImportError:
            pass
        
        # 如果指定了配置文件，尝试加载
        if config_file and os.path.exists(config_file):
            self._load_config_file(config_file)
    
    def _load_config_file(self, config_file: str) -> None:
        """加载指定的配置文件。"""
        import importlib.util
        spec = importlib.util.spec_from_file_location("config", config_file)
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            try:
                spec.loader.exec_module(module)
                # 加载配置
                if hasattr(module, 'EMAIL'):
                    self._config['openreview_email'] = module.EMAIL
                if hasattr(module, 'PASSWORD'):
                    self._config['openreview_password'] = module.PASSWORD
            except Exception:
                pass
    
    def _load_from_env(self) -> None:
        """从环境变量加载配置（优先级最高）。"""
        for key, env_var in self.ENV_MAPPING.items():
            value = os.environ.get(env_var)
            if value is not None:
                # 类型转换
                if key in ['request_delay_min', 'request_delay_max']:
                    self._config[key] = float(value)
                elif key in ['request_timeout', 'request_retries']:
                    self._config[key] = int(value)
                elif key == 'verbose':
                    self._config[key] = value.lower() in ('true', '1', 'yes')
                else:
                    self._config[key] = value
    
    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值。"""
        return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """设置配置值。"""
        self._config[key] = value
    
    def to_dict(self) -> Dict[str, Any]:
        """返回所有配置（隐藏敏感信息）。"""
        result = self._config.copy()
        # 隐藏密码
        if result.get('openreview_password'):
            result['openreview_password'] = '***'
        return result
    
    # 便捷属性
    @property
    def openreview_email(self) -> Optional[str]:
        return self._config.get('openreview_email')
    
    @property
    def openreview_password(self) -> Optional[str]:
        return self._config.get('openreview_password')
    
    @property
    def request_delay_min(self) -> float:
        return self._config.get('request_delay_min', 2.0)
    
    @property
    def request_delay_max(self) -> float:
        return self._config.get('request_delay_max', 5.0)
    
    @property
    def request_timeout(self) -> int:
        return self._config.get('request_timeout', 30)
    
    @property
    def request_retries(self) -> int:
        return self._config.get('request_retries', 3)
    
    @property
    def output_dir(self) -> str:
        return self._config.get('output_dir', './output')
    
    @property
    def verbose(self) -> bool:
        return self._config.get('verbose', True)
    
    @property
    def has_credentials(self) -> bool:
        """检查是否有 OpenReview 凭证。"""
        return bool(self.openreview_email and self.openreview_password)
    
    def __repr__(self) -> str:
        return f"Config({self.to_dict()})"


# 全局配置实例
_config: Optional[Config] = None


def get_config() -> Config:
    """获取全局配置实例。"""
    global _config
    if _config is None:
        _config = Config()
    return _config


def reset_config() -> None:
    """重置全局配置实例。"""
    global _config
    _config = None


# 向后兼容：导出旧的变量
EMAIL = None
PASSWORD = None

# 延迟加载凭证
def _init_credentials():
    global EMAIL, PASSWORD
    config = get_config()
    EMAIL = config.openreview_email
    PASSWORD = config.openreview_password

# 在非测试环境下初始化
if "pytest" not in sys.modules:
    _init_credentials()
    
    # 如果没有凭证，打印警告
    if not EMAIL or not PASSWORD:
        print("⚠️  警告: 未找到 OpenReview 凭证")
        print("   请复制 config/config.example.py 为 config/config.py 并填入凭证")
        print("   或设置环境变量 OPENREVIEW_EMAIL 和 OPENREVIEW_PASSWORD")
