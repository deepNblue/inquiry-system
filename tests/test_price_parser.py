"""
价格解析模块测试
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.price_parser import PriceParser, extract_price, extract_all_prices, PriceSource


class TestPriceParser:
    """价格解析器测试"""
    
    def setup_method(self):
        """每个测试前创建解析器"""
        self.parser = PriceParser()
    
    def test_detect_platform_jd(self):
        """测试京东平台检测"""
        platform = self.parser.detect_platform("https://item.jd.com/123.html")
        assert platform == PriceSource.JD
    
    def test_detect_platform_taobao(self):
        """测试淘宝平台检测"""
        platform = self.parser.detect_platform("https://detail.taobao.com/item.htm?id=123")
        assert platform == PriceSource.TAOBAO
    
    def test_detect_platform_other(self):
        """测试其他平台检测"""
        platform = self.parser.detect_platform("https://example.com/product")
        assert platform == PriceSource.OTHER
    
    def test_is_valid_price(self):
        """测试价格有效性验证"""
        assert self.parser._is_valid_price(99.99) is True
        assert self.parser._is_valid_price(9999) is True
        assert self.parser._is_valid_price(0.001) is False
        assert self.parser._is_valid_price(1000001) is False
        assert self.parser._is_valid_price(2024) is False  # 年份
    
    def test_extract_prices_yuan(self):
        """测试人民币价格提取"""
        text = "价格：¥1234.56元"
        
        prices = self.parser.extract_prices(text)
        
        assert len(prices) > 0
        assert any(1234.0 <= p.price <= 1235.0 for p in prices)
    
    def test_extract_prices_unicode(self):
        """测试 Unicode 价格符号"""
        text = "售价￥999"
        
        prices = self.parser.extract_prices(text)
        
        assert len(prices) > 0
    
    def test_extract_prices_usd(self):
        """测试美元价格"""
        text = "Price: $99.99"
        
        prices = self.parser.extract_prices(text)
        
        assert len(prices) > 0
        assert any(99.0 <= p.price <= 100.0 for p in prices)
    
    def test_get_best_price(self):
        """测试获取最佳价格"""
        text = "原价¥199 现价¥99"
        
        best = self.parser.get_best_price(text)
        
        assert best is not None
    
    def test_get_best_price_no_price(self):
        """测试无价格文本"""
        text = "这个产品没有标注价格"
        
        best = self.parser.get_best_price(text)
        
        assert best is None
    
    def test_extract_price_range(self):
        """测试价格区间提取"""
        text = "价格范围：¥100-200元"
        
        min_price, max_price = self.parser.extract_price_range(text)
        
        assert min_price is not None
        assert max_price is not None
    
    def test_deduplicate(self):
        """测试去重"""
        from src.price_parser import ParsedPrice
        
        prices = [
            ParsedPrice(price=100, confidence=0.8),
            ParsedPrice(price=105, confidence=0.7),
            ParsedPrice(price=200, confidence=0.9),
        ]
        
        unique = self.parser._deduplicate(prices)
        
        assert len(unique) == 2


class TestExtractFunctions:
    """便捷函数测试"""
    
    def test_extract_price_function(self):
        """测试 extract_price 函数"""
        text = "¥1999"
        
        price = extract_price(text)
        
        assert price is not None
        assert 1990 < price < 2010
    
    def test_extract_all_prices_function(self):
        """测试 extract_all_prices 函数"""
        text = "¥199 + ¥299 = ¥498"
        
        prices = extract_all_prices(text)
        
        assert len(prices) >= 2
