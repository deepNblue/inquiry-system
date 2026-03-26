"""
价格聚合模块测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.aggregator import PriceAggregator, AggregatedPrice, SourceType


class TestPriceAggregator:
    """价格聚合器测试"""
    
    def setup_method(self):
        """每个测试方法前执行"""
        self.aggregator = PriceAggregator()
    
    def test_aggregate_empty(self):
        """测试空结果聚合"""
        result = self.aggregator.aggregate()
        assert result == []
    
    def test_aggregate_single_price(self):
        """测试单个价格聚合"""
        # 模拟 PriceResult
        class MockPriceResult:
            def __init__(self, name, brand, price, source):
                self.product_name = name
                self.brand = brand
                self.model = ""
                self.price = price
                self.source = source
                self.source_type = "web"
                self.currency = "CNY"
                self.timestamp = ""
                self.url = ""
        
        web_results = [
            MockPriceResult("iPhone 15", "Apple", 6999, "京东"),
            MockPriceResult("iPhone 15", "Apple", 6599, "拼多多"),
        ]
        
        result = self.aggregator.aggregate(web_results=web_results)
        
        assert len(result) == 1
        assert result[0].product_name == "iPhone 15"
        assert result[0].min_price == 6599
        assert result[0].max_price == 6999
        assert result[0].recommended_source == "拼多多"
    
    def test_calculate_stats(self):
        """测试统计计算"""
        aggregated = AggregatedPrice(
            product_name="Test Product",
            brand="TestBrand"
        )
        
        aggregated.prices = [
            {"price": 100, "source": "A"},
            {"price": 200, "source": "B"},
            {"price": 150, "source": "C"},
        ]
        
        aggregated.calculate_stats()
        
        assert aggregated.min_price == 100
        assert aggregated.max_price == 200
        assert aggregated.avg_price == 150
        assert aggregated.source_count == 3
    
    def test_to_dict(self):
        """测试转换为字典"""
        aggregated = AggregatedPrice(
            product_name="Test",
            brand="Brand",
            min_price=100,
            max_price=200
        )
        
        d = aggregated.to_dict()
        
        assert d["product_name"] == "Test"
        assert d["brand"] == "Brand"
        assert d["min_price"] == 100


class TestAggregatedPrice:
    """聚合价格测试"""
    
    def test_create(self):
        """测试创建"""
        price = AggregatedPrice(
            product_name="Test",
            brand="Brand"
        )
        
        assert price.product_name == "Test"
        assert price.prices == []
        assert price.min_price == 0
    
    def test_markdown_format(self):
        """测试 Markdown 格式化"""
        price = AggregatedPrice(
            product_name="iPhone",
            brand="Apple",
            min_price=6999,
            max_price=7999,
            avg_price=7499,
            recommended_source="京东",
            recommended_price=6999
        )
        
        md = price.to_markdown()
        
        assert "## iPhone" in md
        assert "**品牌**: Apple" in md
        assert "¥6,999.00" in md
        assert "京东" in md
