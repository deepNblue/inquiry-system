"""
网页询价模块
支持 FreeScraper (默认) + Firecrawl + Scrapling
"""

import os
import json
import asyncio
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime

try:
    from .firecrawl_client import FirecrawlClient
except ImportError:
    FirecrawlClient = None

try:
    from .scrapling_client import ScraplingClient
except ImportError:
    ScraplingClient = None


@dataclass
class PriceResult:
    """价格查询结果"""
    product_name: str
    brand: str
    model: str
    price: float
    currency: str = "CNY"
    source: str = ""
    source_type: str = "web"  # web/manufacturer/history
    url: str = ""
    timestamp: str = ""
    raw_data: Dict[str, Any] = None
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()
        if self.raw_data is None:
            self.raw_data = {}


class WebScraper:
    """网页询价器 - 支持多种数据源"""
    
    # 预设电商平台搜索URL模板
    SEARCH_TEMPLATES = {
        "jd": "https://search.jd.com/Search?keyword={keyword}&enc=utf-8",
        "taobao": "https://s.taobao.com/search?q={keyword}",
        "alibaba": "https://www.alibaba.com/trade/search?SearchText={keyword}",
        "bing": "https://www.bing.com/search?q={keyword}+价格+site:jd.com+OR+site:taobao.com+OR+site:alibaba.com",
    }
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.firecrawl = None
        self.scrapling = None
        self._init_clients()
    
    def _init_clients(self):
        """初始化客户端"""
        # Firecrawl
        firecrawl_key = self.config.get("firecrawl_api_key") or os.getenv("FIRECRAWL_API_KEY")
        if firecrawl_key and FirecrawlClient:
            self.firecrawl = FirecrawlClient(firecrawl_key)
        
        # Scrapling
        if ScraplingClient:
            self.scrapling = ScraplingClient()
    
    async def search_price(self, product: Dict[str, str]) -> List[PriceResult]:
        """
        搜索产品价格
        
        Args:
            product: 产品信息字典，包含 name, brand, model 等
        
        Returns:
            价格结果列表
        """
        keyword = self._build_keyword(product)
        results = []
        
        # 并行尝试多种方式
        tasks = [
            self._search_via_firecrawl(keyword, product),
            self._search_via_scrapling(keyword, product),
            self._search_via_reach(keyword, product),
        ]
        
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        for r in task_results:
            if isinstance(r, list):
                results.extend(r)
        
        return results
    
    def _build_keyword(self, product: Dict[str, str]) -> str:
        """构建搜索关键词"""
        parts = [product.get("name", "")]
        if product.get("brand"):
            parts.insert(0, product["brand"])
        if product.get("model"):
            parts.append(product["model"])
        return " ".join(parts)
    
    async def _search_via_firecrawl(self, keyword: str, product: Dict) -> List[PriceResult]:
        """通过 Firecrawl 搜索"""
        if not self.firecrawl:
            return []
        
        try:
            # 搜索相关网站
            search_url = self.SEARCH_TEMPLATES["bing"].format(keyword=keyword)
            data = await self.firecrawl.scrape(search_url)
            
            results = []
            # 解析结果...
            return results
        except Exception as e:
            print(f"Firecrawl 搜索失败: {e}")
            return []
    
    async def _search_via_scrapling(self, keyword: str, product: Dict) -> List[PriceResult]:
        """通过 Scrapling 搜索"""
        if not self.scrapling:
            return []
        
        try:
            # 直接抓取电商搜索页
            url = self.SEARCH_TEMPLATES["jd"].format(keyword=keyword)
            data = await self.scrapling.fetch(url)
            
            results = []
            # 解析数据...
            return results
        except Exception as e:
            print(f"Scrapling 搜索失败: {e}")
            return []
    
    async def _search_via_reach(self, keyword: str, product: Dict) -> List[PriceResult]:
        """通过 Agent Reach / FreeScraper 搜索"""
        try:
            # 尝试使用 FreeScraper
            from src.free_scraper import FreeScraper
            
            scraper = FreeScraper()
            results = await scraper.search_and_scrape(keyword, max_results=3)
            
            price_results = []
            for r in results:
                price_results.append(PriceResult(
                    product_name=r.product_name or product.get("name", ""),
                    brand=product.get("brand", ""),
                    model=product.get("model", ""),
                    price=r.price,
                    source=r.source,
                    source_type="web",
                    url=r.url,
                    raw_data={"raw_text": r.raw_text}
                ))
            
            return price_results
            
        except ImportError:
            print("FreeScraper 不可用，尝试备用方案")
            return await self._search_fallback(keyword, product)
        except Exception as e:
            print(f"FreeScraper 搜索失败: {e}")
            return await self._search_fallback(keyword, product)
    
    async def _search_fallback(self, keyword: str, product: Dict) -> List[PriceResult]:
        """备用搜索方案 - 使用 Jina 直接抓取"""
        try:
            import requests
            import urllib.parse
            
            # 使用 Jina Reader 直接抓取搜索结果
            search_url = f"https://www.bing.com/search?q={urllib.parse.quote(keyword)}+价格"
            jina_url = f"https://r.jina.ai/{urllib.parse.quote(search_url)}"
            
            response = requests.get(
                jina_url,
                headers={"Accept": "text/plain", "X-Timeout": "10"},
                timeout=15
            )
            
            if response.status_code == 200:
                content = response.text
                
                # 提取价格
                import re
                prices = re.findall(r'[¥￥]\s*([\d,]+\.?\d*)', content)
                
                price_results = []
                for i, p in enumerate(prices[:5]):
                    try:
                        price = float(p.replace(',', ''))
                        if 100 < price < 100000:  # 合理范围
                            price_results.append(PriceResult(
                                product_name=product.get("name", ""),
                                brand=product.get("brand", ""),
                                model=product.get("model", ""),
                                price=price,
                                source=f"搜索结果{i+1}",
                                source_type="web",
                                url=search_url
                            ))
                    except:
                        pass
                
                return price_results
                
        except Exception as e:
            print(f"备用搜索也失败: {e}")
        
        return []
    
    async def batch_search(self, products: List[Dict[str, str]]) -> List[PriceResult]:
        """批量搜索"""
        tasks = [self.search_price(p) for p in products]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for r in results:
            if isinstance(r, list):
                all_results.extend(r)
        
        return all_results
