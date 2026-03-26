"""
Firecrawl 客户端封装
"""

import os
from typing import Dict, Optional, List, Any
import requests


class FirecrawlClient:
    """Firecrawl API 客户端"""
    
    def __init__(self, api_key: str, base_url: str = "https://api.firecrawl.dev"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        })
    
    def scrape(
        self,
        url: str,
        page_options: Dict = None,
        extractor_options: Dict = None
    ) -> Dict[str, Any]:
        """
        抓取单个页面
        
        Args:
            url: 页面 URL
            page_options: 页面选项 (wait_for, screenshot 等)
            extractor_options: 提取选项
        
        Returns:
            {"content": "...", "metadata": {...}}
        """
        payload = {
            "url": url,
            "pageOptions": page_options or {},
            "extractorOptions": extractor_options or {"extractionStrategy": "markdown"}
        }
        
        response = self.session.post(
            f"{self.base_url}/v1/scrape",
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    
    def crawl(
        self,
        url: str,
        limit: int = 10,
        poll_interval: int = 2,
        **kwargs
    ) -> Dict[str, Any]:
        """
        整站爬取
        
        Args:
            url: 起始 URL
            limit: 最大页面数
            poll_interval: 轮询间隔(秒)
        
        Returns:
            {"status": "completed", "data": [...]}
        """
        # 启动爬取任务
        payload = {
            "url": url,
            "limit": limit,
            **kwargs
        }
        
        response = self.session.post(
            f"{self.base_url}/v1/crawl",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        job_id = response.json().get("id")
        
        # 轮询结果
        import time
        while True:
            result = self.session.get(
                f"{self.base_url}/v1/crawl/{job_id}"
            )
            result.raise_for_status()
            data = result.json()
            
            if data.get("status") in ["completed", "failed"]:
                return data
            
            time.sleep(poll_interval)
    
    def map(self, url: str) -> List[str]:
        """
        获取网站结构
        
        Args:
            url: 网站 URL
        
        Returns:
            URL 列表
        """
        payload = {"url": url}
        
        response = self.session.post(
            f"{self.base_url}/v1/map",
            json=payload,
            timeout=30
        )
        response.raise_for_status()
        return response.json().get("links", [])
    
    def batch_scrape(self, urls: List[str]) -> List[Dict]:
        """批量抓取"""
        results = []
        for url in urls:
            try:
                result = self.scrape(url)
                results.append(result)
            except Exception as e:
                print(f"抓取失败 {url}: {e}")
                results.append({"url": url, "error": str(e)})
        return results
