"""
Scrapling 客户端封装
"""

from typing import Dict, Optional, List, Any
import asyncio

try:
    from scrapling import Edgified, PySpider
    HAS_SCRAPLING = True
except ImportError:
    HAS_SCRAPLING = False


class ScraplingClient:
    """Scrapling 网页解析客户端"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.use_browser = self.config.get("use_browser", True)
    
    async def fetch(
        self,
        url: str,
        selectors: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        获取页面内容
        
        Args:
            url: 页面 URL
            selectors: CSS 选择器字典，如 {"title": "h1", "price": ".price"}
        
        Returns:
            解析后的数据
        """
        if not HAS_SCRAPLING:
            raise ImportError("scrapling not installed. Run: pip install scrapling")
        
        try:
            if self.use_browser:
                # 使用浏览器模式 (JS 渲染)
                artifact = Edgified.from_url(url)
            else:
                # 普通模式
                artifact = PySpider.from_url(url)
            
            if selectors:
                result = {}
                for key, selector in selectors.items():
                    try:
                        result[key] = artifact.match(selector).text
                    except:
                        result[key] = None
                return result
            else:
                # 返回完整内容
                return {
                    "html": str(artifact),
                    "text": artifact.text,
                    "url": url
                }
                
        except Exception as e:
            return {"error": str(e), "url": url}
    
    async def batch_fetch(
        self,
        urls: List[str],
        selectors: Dict[str, str] = None
    ) -> List[Dict[str, Any]]:
        """批量获取"""
        tasks = [self.fetch(url, selectors) for url in urls]
        return await asyncio.gather(*tasks, return_exceptions=True)
    
    def extract_prices(self, text: str) -> List[float]:
        """从文本中提取价格"""
        import re
        # 匹配各种价格格式
        patterns = [
            r"¥\s*([\d,]+\.?\d*)",  # ¥123.45
            r"￥\s*([\d,]+\.?\d*)",  # ￥123.45
            r"CNY\s*([\d,]+\.?\d*)",  # CNY 123.45
            r"\$([\d,]+\.?\d*)",  # $123.45
        ]
        
        prices = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            for m in matches:
                try:
                    price = float(m.replace(",", ""))
                    if 0 < price < 1000000:  # 合理价格范围
                        prices.append(price)
                except:
                    pass
        
        return sorted(set(prices))
