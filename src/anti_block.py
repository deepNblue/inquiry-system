"""
反爬对抗模块
提供多种反爬策略和自动切换机制
"""

import asyncio
import random
import time
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import httpx


class AntiBlockStrategy(Enum):
    """反爬策略"""
    NONE = "none"  # 无保护
    BASIC = "basic"  # 基础（UA、延时）
    STEALTH = "stealth"  # 隐身（代理、轮换）
    FIRECRAWL = "firecrawl"  # 使用 Firecrawl 服务


@dataclass
class AntiBlockConfig:
    """反爬配置"""
    strategy: AntiBlockStrategy = AntiBlockStrategy.BASIC
    
    # 延时配置
    min_delay: float = 1.0  # 最小延时（秒）
    max_delay: float = 3.0  # 最大延时（秒）
    
    # 重试配置
    max_retries: int = 3
    retry_delay: float = 5.0  # 重试延时（秒）
    
    # User-Agent 轮换
    user_agents: List[str] = None
    
    # 代理配置
    proxies: List[str] = None
    
    # Firecrawl 配置
    firecrawl_key: str = ""
    firecrawl_proxy: str = "auto"


class AntiBlockClient:
    """
    反爬对抗客户端
    自动处理反爬策略切换
    """
    
    # 默认 User-Agent 列表
    DEFAULT_UA = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, config: AntiBlockConfig = None):
        self.config = config or AntiBlockConfig()
        
        if not self.config.user_agents:
            self.config.user_agents = self.DEFAULT_UA
        
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,
        )
        
        # 统计
        self.stats = {
            "total_requests": 0,
            "success": 0,
            "blocked": 0,
            "retries": 0
        }
    
    async def fetch(
        self,
        url: str,
        strategy: AntiBlockStrategy = None,
        **kwargs
    ) -> Optional[str]:
        """
        获取页面内容
        
        Args:
            url: 目标URL
            strategy: 指定策略（None=自动）
        
        Returns:
            页面内容，失败返回None
        """
        strategy = strategy or self.config.strategy
        
        for attempt in range(self.config.max_retries):
            try:
                # 根据策略选择获取方式
                if strategy == AntiBlockStrategy.FIRECRAWL:
                    content = await self._fetch_via_firecrawl(url)
                else:
                    content = await self._fetch_direct(url, strategy)
                
                self.stats["total_requests"] += 1
                
                if content:
                    self.stats["success"] += 1
                    return content
                else:
                    self.stats["blocked"] += 1
                    
            except Exception as e:
                print(f"请求失败 (attempt {attempt+1}): {e}")
                self.stats["retries"] += 1
            
            # 重试延时
            if attempt < self.config.max_retries - 1:
                await asyncio.sleep(self.config.retry_delay)
        
        return None
    
    async def _fetch_direct(
        self,
        url: str,
        strategy: AntiBlockStrategy
    ) -> Optional[str]:
        """直接请求"""
        headers = {}
        
        if strategy in [AntiBlockStrategy.BASIC, AntiBlockStrategy.STEALTH]:
            # 随机 UA
            headers["User-Agent"] = random.choice(self.config.user_agents)
            
            # 基础头
            headers.update({
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
            })
        
        # 代理
        proxies = None
        if strategy == AntiBlockStrategy.STEALTH and self.config.proxies:
            proxies = {
                "http://": random.choice(self.config.proxies),
                "https://": random.choice(self.config.proxies),
            }
        
        # 延时
        if strategy != AntiBlockStrategy.NONE:
            delay = random.uniform(self.config.min_delay, self.config.max_delay)
            await asyncio.sleep(delay)
        
        response = await self.client.get(url, headers=headers, proxies=proxies)
        
        # 检查是否被拦截
        if response.status_code == 403 or response.status_code == 429:
            return None
        
        if "captcha" in response.text.lower() or "验证" in response.text:
            return None
        
        return response.text
    
    async def _fetch_via_firecrawl(self, url: str) -> Optional[str]:
        """通过 Firecrawl 获取"""
        if not self.config.firecrawl_key:
            raise ValueError("Firecrawl API key not configured")
        
        import requests
        
        headers = {
            "Authorization": f"Bearer {self.config.firecrawl_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "url": url,
            "pageOptions": {
                "onlyMainContent": True,
            },
            "extractorOptions": {
                "extractionStrategy": "markdown"
            }
        }
        
        # 使用隐身代理
        if self.config.firecrawl_proxy:
            payload["proxy"] = self.config.firecrawl_proxy
        
        response = requests.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            return None
        
        data = response.json()
        
        # 提取内容
        if data.get("success") and data.get("data"):
            return data["data"].get("content", "")
        
        return None
    
    async def batch_fetch(
        self,
        urls: List[str],
        strategy: AntiBlockStrategy = None,
        concurrency: int = 3
    ) -> Dict[str, Optional[str]]:
        """批量获取（带并发控制）"""
        results = {}
        semaphore = asyncio.Semaphore(concurrency)
        
        async def fetch_with_semaphore(url):
            async with semaphore:
                result = await self.fetch(url, strategy)
                return url, result
        
        tasks = [fetch_with_semaphore(url) for url in urls]
        completed = await asyncio.gather(*tasks, return_exceptions=True)
        
        for item in completed:
            if isinstance(item, tuple):
                url, content = item
                results[url] = content
            else:
                # 处理异常
                pass
        
        return results
    
    def get_stats(self) -> Dict[str, int]:
        """获取统计信息"""
        return self.stats.copy()
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()


# 策略选择器
def choose_strategy(url: str, previous_success: bool = True) -> AntiBlockStrategy:
    """
    根据URL选择策略
    
    Args:
        url: 目标URL
        previous_success: 之前请求是否成功
    
    Returns:
        推荐策略
    """
    url_lower = url.lower()
    
    # 大平台通常有严格反爬
    strict_platforms = ["jd.com", "taobao.com", "tmall.com", "pdd", "alibaba.com"]
    
    for platform in strict_platforms:
        if platform in url_lower:
            if not previous_success:
                # 之前失败过，升级到 Firecrawl
                return AntiBlockStrategy.FIRECRAWL
            else:
                # 基础策略 + 延时
                return AntiBlockStrategy.STEALTH
    
    # 普通网站
    if not previous_success:
        return AntiBlockStrategy.STEALTH
    
    return AntiBlockStrategy.BASIC
