"""
基础包导入测试

验证 paper_scraper 包可以正常导入。
"""
import pytest


def test_package_import():
    """测试包可以正常导入"""
    import paper_scraper
    assert paper_scraper is not None


def test_version_exists():
    """测试版本号存在"""
    from paper_scraper import __version__
    assert __version__ is not None
    assert isinstance(__version__, str)
    assert len(__version__) > 0


def test_version_format():
    """测试版本号格式 (semver)"""
    from paper_scraper import __version__
    parts = __version__.split(".")
    assert len(parts) >= 2, "版本号应至少包含 major.minor"
    # 检查每部分都是数字
    for part in parts:
        assert part.isdigit(), f"版本号部分 '{part}' 应为数字"


def test_sources_defined():
    """测试数据来源已定义"""
    from paper_scraper import SOURCES
    assert SOURCES is not None
    assert isinstance(SOURCES, dict)
    assert 'openreview' in SOURCES
    assert 'web_scrape' in SOURCES
    assert 'pdf_extract' in SOURCES

