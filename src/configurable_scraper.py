"""
可配置化数据源
支持按产品类别配置不同的数据源和解析规则
"""

import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DataSource:
    """数据源配置"""
    name: str
    url_template: str
    price_selector: str = ""
    title_selector: str = ""
    model_selector: str = ""
    headers: Dict[str, str] = None
    requires_browser: bool = False  # 是否需要 JS 渲染


class ConfigurableScraper:
    """可配置化询价器"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path
        self.sources: Dict[str, List[DataSource]] = {}
        self.default_sources: List[DataSource] = []
        
        if config_path and Path(config_path).exists():
            self.load_config(config_path)
    
    def load_config(self, path: str):
        """加载数据源配置"""
        with open(path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        sources_config = config.get("sources", {})
        
        # 解析各类别的数据源
        for category, sources in sources_config.items():
            self.sources[category] = [
                DataSource(
                    name=s.get("name", ""),
                    url_template=s.get("url_template", ""),
                    price_selector=s.get("price_selector", ""),
                    title_selector=s.get("title_selector", ""),
                    model_selector=s.get("model_selector", ""),
                    headers=s.get("headers", {}),
                    requires_browser=s.get("requires_browser", False),
                )
                for s in sources
            ]
        
        # 默认数据源
        default = config.get("default_sources", [])
        self.default_sources = [
            DataSource(
                name=s.get("name", ""),
                url_template=s.get("url_template", ""),
                price_selector=s.get("price_selector", ""),
                title_selector=s.get("title_selector", ""),
                model_selector=s.get("model_selector", ""),
                headers=s.get("headers", {}),
                requires_browser=s.get("requires_browser", False),
            )
            for s in default
        ]
    
    def get_sources(self, category: str = None) -> List[DataSource]:
        """获取指定类别的数据源"""
        if category and category in self.sources:
            return self.sources[category]
        return self.default_sources or self._get_builtin_sources()
    
    def _get_builtin_sources(self) -> List[DataSource]:
        """内置默认数据源"""
        return [
            DataSource(
                name="京东",
                url_template="https://search.jd.com/Search?keyword={keyword}&enc=utf-8",
                price_selector=".p-price strong i",
                title_selector=".p-name em",
                requires_browser=True,
            ),
            DataSource(
                name="淘宝/天猫",
                url_template="https://s.taobao.com/search?q={keyword}",
                price_selector=".price",
                title_selector=".title",
                requires_browser=True,
            ),
            DataSource(
                name="阿里巴巴",
                url_template="https://www.alibaba.com/trade/search?SearchText={keyword}",
                price_selector=".price",
                title_selector=".title",
                requires_browser=False,
            ),
        ]
    
    def build_url(self, source: DataSource, keyword: str) -> str:
        """构建搜索 URL"""
        return source.url_template.format(keyword=keyword)


# 示例配置文件
EXAMPLE_CONFIG = """
# 数据源配置文件示例

sources:
  手机:
    - name: 京东
      url_template: "https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
      price_selector: ".p-price strong i"
      title_selector: ".p-name em"
      requires_browser: true
    
    - name: 拼多多
      url_template: "https://mobile.yangkeduo.com/search.html?query={keyword}"
      price_selector: ".price"
      requires_browser: false

  笔记本:
    - name: 京东
      url_template: "https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
      price_selector: ".p-price"
      title_selector: ".p-name"
      requires_browser: true
    
    - name: 苏宁
      url_template: "https://search.suning.com/{keyword}/"
      price_selector: ".def-price"
      requires_browser: false

  通用:
    - name: 百度
      url_template: "https://www.baidu.com/s?wd={keyword}+价格"
      price_selector: ""
      requires_browser: false

default_sources:
  - name: 京东
    url_template: "https://search.jd.com/Search?keyword={keyword}&enc=utf-8"
    price_selector: ".p-price strong i"
    requires_browser: true
"""
