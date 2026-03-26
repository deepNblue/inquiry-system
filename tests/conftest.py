"""
pytest 配置文件
"""

import pytest
import sys
import os

# 确保项目路径在 sys.path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def project_root():
    """项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture(scope="session")
def test_data_dir(project_root):
    """测试数据目录"""
    return os.path.join(project_root, "tests", "data")


@pytest.fixture
def sample_products():
    """示例产品数据"""
    return [
        {"name": "iPhone 15 Pro", "brand": "Apple", "model": "A2892"},
        {"name": "MacBook Pro 14", "brand": "Apple", "model": "M3 Pro"},
        {"name": "ThinkPad X1 Carbon", "brand": "联想", "model": "21M"},
    ]


@pytest.fixture
def sample_prices():
    """示例价格数据"""
    return [
        {"product": "iPhone 15", "price": 6999, "source": "京东"},
        {"product": "iPhone 15", "price": 6599, "source": "拼多多"},
        {"product": "iPhone 15", "price": 6899, "source": "天猫"},
    ]
