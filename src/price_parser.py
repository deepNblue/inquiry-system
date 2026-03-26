"""
智能价格解析模块
多策略价格提取 + 置信度评估
"""

import re
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import Enum
import json


class PriceSource(Enum):
    """价格来源类型"""
    JD = "jd"
    TAOBAO = "taobao"
    Tmall = "tmall"
    PDD = "pdd"
    ALIBABA = "alibaba"
    SUNING = "suning"
    OTHER = "other"


@dataclass
class ParsedPrice:
    """解析后的价格"""
    price: float
    currency: str = "CNY"
    source_type: str = ""
    unit: str = ""  # 个/台/件等
    discount: float = 1.0  # 折扣率
    original_price: float = 0  # 原价
    confidence: float = 0.5  # 置信度
    raw_text: str = ""  # 原始文本
    selector: str = ""  # 匹配的CSS选择器


class PriceParser:
    """
    智能价格解析器
    支持多种提取策略和置信度评估
    """
    
    # 价格正则模式
    PRICE_PATTERNS = [
        # ¥1234.56
        r"¥\s*([\d,]+\.?\d*)",
        # RMB 1234
        r"(?:RMB|CNY|人民币)\s*([\d,]+\.?\d*)",
        # 1234元
        r"([\d,]+\.?\d*)\s*元",
        # $123 (美元)
        r"\$\s*([\d,]+\.?\d*)",
        # 促销价标签
        r"(?:促销价|活动价|秒杀价|特惠价)[：:]\s*¥?\s*([\d,]+\.?\d*)",
    ]
    
    # 各平台特征
    PLATFORM_SIGNATURES = {
        "jd": {
            "domain": "jd.com",
            "selectors": [
                ".p-price .price",
                ".p-price strong i",
                ".J_pPrice .price",
                "[class*='price']",
            ],
            "patterns": [r"¥\s*([\d,]+)"]
        },
        "taobao": {
            "domain": "taobao.com",
            "selectors": [
                ".price",
                ".deal-count",
                "[class*='price']",
            ],
            "patterns": [r"(\d+\.?\d*)\s*元"]
        },
        "pdd": {
            "domain": "pdd",
            "selectors": [
                ".price",
                ".goods-price",
            ],
            "patterns": [r"¥\s*(\d+\.?\d*)"]
        },
        "alibaba": {
            "domain": "alibaba.com",
            "selectors": [
                ".price",
                ".ma-spec-price",
            ],
            "patterns": [r"\$\s*([\d,]+\.?\d*)"]
        }
    }
    
    def __init__(self):
        self.source_type = PriceSource.OTHER
    
    def detect_platform(self, url: str) -> PriceSource:
        """检测平台类型"""
        url_lower = url.lower()
        
        for platform, sig in self.PLATFORM_SIGNATURES.items():
            if sig["domain"] in url_lower:
                return PriceSource[platform.upper()]
        
        return PriceSource.OTHER
    
    def extract_prices(self, text: str, url: str = "") -> List[ParsedPrice]:
        """
        从文本中提取价格
        
        Args:
            text: HTML 或纯文本
            url: 来源URL（用于平台识别）
        
        Returns:
            价格列表（按置信度排序）
        """
        prices = []
        
        # 1. 平台特定提取
        platform = self.detect_platform(url)
        
        if platform != PriceSource.OTHER:
            sig = self.PLATFORM_SIGNATURES[platform.value]
            
            # 尝试CSS选择器提取（如果有DOM结构）
            css_prices = self._extract_from_css(text, sig["selectors"])
            prices.extend(css_prices)
            
            # 模式匹配
            for pattern in sig["patterns"]:
                pattern_prices = self._extract_by_pattern(text, pattern, platform.value)
                prices.extend(pattern_prices)
        
        # 2. 通用模式提取
        for pattern in self.PRICE_PATTERNS:
            generic_prices = self._extract_by_pattern(text, pattern, "generic")
            prices.extend(generic_prices)
        
        # 3. 去重并排序
        unique_prices = self._deduplicate(prices)
        unique_prices.sort(key=lambda x: x.confidence, reverse=True)
        
        return unique_prices
    
    def _extract_from_css(self, text: str, selectors: List[str]) -> List[ParsedPrice]:
        """从CSS选择器风格的结构中提取"""
        prices = []
        
        for selector in selectors:
            # 简化CSS匹配
            class_match = re.search(rf'class=["\'].*?{re.escape(selector.replace(".", "").replace("#", ""))}.*?["\']', text)
            if class_match:
                # 提取class附近的文本
                start = max(0, class_match.start() - 50)
                end = min(len(text), class_match.end() + 100)
                snippet = text[start:end]
                
                # 提取价格
                for pattern in self.PRICE_PATTERNS:
                    extracted = self._extract_by_pattern(snippet, pattern, f"css:{selector}")
                    prices.extend(extracted)
        
        return prices
    
    def _extract_by_pattern(self, text: str, pattern: str, source: str) -> List[ParsedPrice]:
        """通过正则模式提取"""
        prices = []
        
        matches = re.finditer(pattern, text, re.IGNORECASE)
        
        for match in matches:
            try:
                price_str = match.group(1).replace(",", "")
                price = float(price_str)
                
                # 过滤不合理价格
                if not self._is_valid_price(price):
                    continue
                
                # 提取上下文计算置信度
                context = text[max(0, match.start()-20):match.end()+20]
                
                parsed = ParsedPrice(
                    price=price,
                    source_type=source,
                    confidence=self._calculate_confidence(context, price),
                    raw_text=match.group(0)
                )
                
                prices.append(parsed)
                
            except (ValueError, IndexError):
                continue
        
        return prices
    
    def _is_valid_price(self, price: float) -> bool:
        """验证价格合理性"""
        # 排除明显不是价格的值
        if price < 0.01 or price > 1000000:  # 1分 ~ 100万
            return False
        
        # 排除序号等
        if price == round(price) and price > 1000 and price < 100000:
            # 可能是年份或电话号码
            if 1900 < price < 2030:  # 年份
                return False
        
        return True
    
    def _calculate_confidence(self, context: str, price: float) -> float:
        """计算置信度"""
        confidence = 0.5  # 基础置信度
        
        context_lower = context.lower()
        
        # 价格相关关键词加成
        positive_keywords = ["价格", "价", "¥", "￥", "$", "促销", "特惠", "秒杀", "活动"]
        for kw in positive_keywords:
            if kw in context_lower:
                confidence += 0.1
        
        # 货币符号加成
        if "¥" in context or "￥" in context:
            confidence += 0.15
        
        # 折扣信息加成
        if "折" in context:
            confidence += 0.05
        
        # 原价标注加成
        if "原价" in context_lower or "原价" in context:
            confidence += 0.1
        
        # 附近有其他价格（互相印证）
        other_prices = re.findall(r"[\d,]+\.?\d*", context)
        if len(other_prices) > 1:
            confidence += 0.05
        
        return min(confidence, 1.0)
    
    def _deduplicate(self, prices: List[ParsedPrice]) -> List[ParsedPrice]:
        """去重（相近价格合并）"""
        if not prices:
            return []
        
        unique = []
        seen_values = set()
        
        for p in prices:
            # 按10元精度去重
            rounded = round(p.price, -1)
            
            if rounded not in seen_values:
                unique.append(p)
                seen_values.add(rounded)
        
        return unique
    
    def get_best_price(self, text: str, url: str = "") -> Optional[float]:
        """获取最佳价格（置信度最高）"""
        prices = self.extract_prices(text, url)
        
        if not prices:
            return None
        
        return prices[0].price
    
    def extract_price_range(self, text: str, url: str = "") -> Tuple[Optional[float], Optional[float]]:
        """提取价格区间"""
        prices = self.extract_prices(text, url)
        
        if not prices:
            return None, None
        
        # 过滤极端值
        valid_prices = [p.price for p in prices if 0.01 < p.price < 100000]
        
        if not valid_prices:
            return None, None
        
        return min(valid_prices), max(valid_prices)


# 便捷函数
def extract_price(text: str, url: str = "") -> Optional[float]:
    """快速提取价格"""
    parser = PriceParser()
    return parser.get_best_price(text, url)


def extract_all_prices(text: str, url: str = "") -> List[ParsedPrice]:
    """提取所有价格"""
    parser = PriceParser()
    return parser.extract_prices(text, url)
