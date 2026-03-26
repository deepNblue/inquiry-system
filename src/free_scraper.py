"""
免费网页抓取模块
不依赖 Firecrawl，使用免费的 Agent Reach / Jina / Exa
"""

import os
import re
import json
import asyncio
import subprocess
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime


@dataclass
class ScraperResult:
    """抓取结果"""
    product_name: str
    price: float
    currency: str = "CNY"
    source: str = ""
    source_type: str = "web"
    url: str = ""
    timestamp: str = ""
    raw_text: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class FreeScraper:
    """
    免费网页抓取器
    使用 Jina Reader 和 Exa Search
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.price_parser = None  # 延迟导入
    
    def _get_price_parser(self):
        if self.price_parser is None:
            try:
                from src.price_parser import PriceParser
                self.price_parser = PriceParser()
            except:
                self.price_parser = None
        return self.price_parser
    
    async def search_and_scrape(self, keyword: str, max_results: int = 5) -> List[ScraperResult]:
        """
        搜索 + 抓取 + 价格提取
        
        Args:
            keyword: 搜索关键词
            max_results: 最大结果数
        
        Returns:
            价格结果列表
        """
        results = []
        
        # 1. 使用 Exa 搜索获取相关页面
        pages = await self._search_with_exa(keyword, max_results)
        
        # 2. 对每个页面抓取内容
        for page in pages:
            content = await self._scrape_with_jina(page["url"])
            if content:
                # 3. 提取价格
                price = self._extract_price(content)
                if price:
                    results.append(ScraperResult(
                        product_name=keyword,
                        price=price,
                        source=page.get("source", ""),
                        source_type="search",
                        url=page["url"],
                        raw_text=content[:500]
                    ))
        
        # 4. 如果搜索没结果，尝试直接抓官方网站
        if not results:
            official_results = await self._scrape_official_pages(keyword)
            results.extend(official_results)
        
        return results
    
    async def _search_with_exa(self, keyword: str, max_results: int = 5) -> List[Dict]:
        """使用 Exa 搜索"""
        try:
            cmd = f'powershell.exe -Command "mcporter call exa.web_search_exa query=\'{keyword} 价格\' numResults={max_results}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
            
            pages = []
            # 解析输出
            output = result.stdout
            
            # 提取 URL 和标题
            lines = output.split('\n')
            for line in lines:
                if 'http' in line.lower():
                    # 简单 URL 提取
                    url_match = re.search(r'https?://[^\s\)\"\']+', line)
                    if url_match:
                        url = url_match.group(0)
                        title = line.replace(url, '').strip()
                        pages.append({
                            "url": url,
                            "source": title[:50] if title else "搜索结果",
                            "keyword": keyword
                        })
            
            return pages[:max_results]
            
        except Exception as e:
            print(f"Exa 搜索失败: {e}")
            return []
    
    async def _scrape_with_jina(self, url: str) -> str:
        """使用 Jina Reader 抓取"""
        try:
            import urllib.parse
            encoded = urllib.parse.quote(url, safe='')
            jina_url = f"https://r.jina.ai/{encoded}"
            
            cmd = f'curl -s -L --max-time 15 -H "Accept: text/plain" "{jina_url}"'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=20)
            
            if result.returncode == 0:
                content = result.stdout
                # 清理 markdown 格式
                content = self._clean_content(content)
                return content
                
        except Exception as e:
            print(f"Jina 抓取失败 {url}: {e}")
        
        return ""
    
    def _clean_content(self, content: str) -> str:
        """清理抓取的内容"""
        # 移除 markdown 图片
        content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
        # 移除多余空行
        content = re.sub(r'\n{3,}', '\n\n', content)
        return content.strip()
    
    def _extract_price(self, text: str) -> Optional[float]:
        """从文本中提取价格"""
        parser = self._get_price_parser()
        
        if parser:
            return parser.get_best_price(text)
        
        # 备用：简单正则
        prices = re.findall(r'[¥￥]\s*([\d,]+\.?\d*)', text)
        if prices:
            try:
                return float(prices[0].replace(',', ''))
            except:
                pass
        
        return None
    
    async def _scrape_official_pages(self, keyword: str) -> List[ScraperResult]:
        """抓取官方网站价格"""
        results = []
        
        # 常见官方商城 URL 模板
        official_templates = [
            # 苹果官方
            ("Apple 官网", f"https://www.apple.com/shop/buy-iphone/iphone-15-pro"),
            # 华为官方
            ("华为官网", f"https://www.vmall.com/search?keyword={keyword}"),
            # 小米官方
            ("小米官网", f"https://www.mi.com/search?q={keyword}"),
        ]
        
        for source, url in official_templates:
            content = await self._scrape_with_jina(url)
            if content:
                price = self._extract_price(content)
                if price:
                    results.append(ScraperResult(
                        product_name=keyword,
                        price=price,
                        source=source,
                        source_type="official",
                        url=url
                    ))
        
        return results
    
    async def batch_search(self, keywords: List[str], max_results: int = 3) -> List[ScraperResult]:
        """批量搜索"""
        all_results = []
        
        for keyword in keywords:
            results = await self.search_and_scrape(keyword, max_results)
            all_results.extend(results)
            # 避免频率限制
            await asyncio.sleep(1)
        
        return all_results


class PriceExtractor:
    """
    独立价格提取器
    不依赖外部服务
    """
    
    # 价格模式
    PRICE_PATTERNS = [
        r'¥\s*([\d,]+\.?\d*)',
        r'￥\s*([\d,]+\.?\d*)',
        r'价格[：:]\s*([\d,]+\.?\d*)',
        r'售价[：:]\s*([\d,]+\.?\d*)',
        r'特惠价[：:]\s*([\d,]+\.?\d*)',
        r'活动价[：:]\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*元',
    ]
    
    def extract(self, text: str) -> List[float]:
        """提取所有价格"""
        prices = []
        
        for pattern in self.PRICE_PATTERNS:
            matches = re.findall(pattern, text)
            for m in matches:
                try:
                    price = float(m.replace(',', ''))
                    if 1 < price < 1000000:  # 合理范围
                        prices.append(price)
                except:
                    pass
        
        return sorted(set(prices))
    
    def extract_best(self, text: str) -> Optional[float]:
        """提取最可能的价格（最低的促销价）"""
        prices = self.extract(text)
        if not prices:
            return None
        
        # 假设最低价是促销价
        return min(prices)


# 便捷函数
async def scrape_price(keyword: str) -> List[ScraperResult]:
    """快速抓取价格"""
    scraper = FreeScraper()
    return await scraper.search_and_scrape(keyword)
