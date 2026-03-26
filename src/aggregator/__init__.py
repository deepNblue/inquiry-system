"""
价格聚合模块
整合多渠道询价结果，统一输出
"""

import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from enum import Enum

try:
    from ..scraper import PriceResult
    from ..history import HistoryPrice
    from ..manufacturer import InquiryMessage
except ImportError:
    PriceResult = None
    HistoryPrice = None
    InquiryMessage = None


class SourceType(Enum):
    WEB = "web"
    MANUFACTURER = "manufacturer"
    HISTORY = "history"


@dataclass
class AggregatedPrice:
    """聚合后的价格"""
    product_name: str
    brand: str = ""
    model: str = ""
    category: str = ""
    
    # 价格信息
    prices: List[Dict] = field(default_factory=list)  # [{source, price, currency, timestamp}]
    
    # 统计
    min_price: float = 0
    max_price: float = 0
    avg_price: float = 0
    median_price: float = 0
    
    # 推荐
    recommended_source: str = ""
    recommended_price: float = 0
    
    # 元数据
    last_updated: str = ""
    source_count: int = 0
    
    def calculate_stats(self):
        """计算统计信息"""
        if not self.prices:
            return
        
        price_values = [p["price"] for p in self.prices if p.get("price", 0) > 0]
        
        if price_values:
            self.min_price = min(price_values)
            self.max_price = max(price_values)
            self.avg_price = sum(price_values) / len(price_values)
            price_values.sort()
            n = len(price_values)
            self.median_price = price_values[n // 2] if n % 2 else (price_values[n//2-1] + price_values[n//2]) / 2
            
            # 推荐最低价
            best = min(self.prices, key=lambda x: x.get("price", float("inf")))
            self.recommended_source = best.get("source", "")
            self.recommended_price = best.get("price", 0)
        
        self.source_count = len(self.prices)
        self.last_updated = datetime.now().isoformat()
    
    def to_dict(self) -> Dict:
        """转为字典"""
        return asdict(self)
    
    def to_markdown(self) -> str:
        """转为 Markdown 格式"""
        lines = [
            f"## {self.product_name}",
            "",
        ]
        
        if self.brand:
            lines.append(f"**品牌**: {self.brand}")
        if self.model:
            lines.append(f"**型号**: {self.model}")
        
        lines.append("")
        lines.append("### 价格汇总")
        lines.append("")
        lines.append(f"| 来源 | 价格 | 备注 |")
        lines.append(f"|------|------|------|")
        
        for p in self.prices:
            source = p.get("source", "未知")
            price = f"¥{p['price']:,.2f}" if p.get("price") else "待报价"
            note = p.get("note", "")
            lines.append(f"| {source} | {price} | {note} |")
        
        lines.append("")
        lines.append("### 统计")
        lines.append("")
        lines.append(f"- 最低价: ¥{self.min_price:,.2f}")
        lines.append(f"- 最高价: ¥{self.max_price:,.2f}")
        lines.append(f"- 平均价: ¥{self.avg_price:,.2f}")
        lines.append(f"- 中位数: ¥{self.median_price:,.2f}")
        
        if self.recommended_source:
            lines.append("")
            lines.append(f"**推荐**: {self.recommended_source} - ¥{self.recommended_price:,.2f}")
        
        return "\n".join(lines)


class PriceAggregator:
    """价格聚合器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def aggregate(
        self,
        web_results: List[Any] = None,
        manufacturer_messages: List[Any] = None,
        history_results: List[Any] = None
    ) -> List[AggregatedPrice]:
        """
        聚合多渠道询价结果
        
        Args:
            web_results: 网页询价结果 (List[PriceResult])
            manufacturer_messages: 厂家询价消息
            history_results: 历史询价结果 (List[HistoryPrice])
        
        Returns:
            聚合后的价格列表
        """
        # 按产品分组
        product_prices: Dict[str, AggregatedPrice] = {}
        
        # 处理网页结果
        if web_results:
            for r in web_results:
                if PriceResult and isinstance(r, PriceResult):
                    self._add_web_result(product_prices, r)
        
        # 处理历史结果
        if history_results:
            for r in history_results:
                if HistoryPrice and isinstance(r, HistoryPrice):
                    self._add_history_result(product_prices, r)
        
        # 计算统计
        for ap in product_prices.values():
            ap.calculate_stats()
        
        return list(product_prices.values())
    
    def _add_web_result(self, products: Dict, result):
        """添加网页结果"""
        key = self._make_key(result.product_name, result.brand, result.model)
        
        if key not in products:
            products[key] = AggregatedPrice(
                product_name=result.product_name,
                brand=result.brand,
                model=result.model,
            )
        
        products[key].prices.append({
            "source": result.source,
            "source_type": "web",
            "price": result.price,
            "currency": result.currency,
            "timestamp": result.timestamp,
            "url": result.url,
        })
    
    def _add_history_result(self, products: Dict, result):
        """添加历史结果"""
        key = self._make_key(result.product_name, result.brand, result.model)
        
        if key not in products:
            products[key] = AggregatedPrice(
                product_name=result.product_name,
                brand=result.brand,
                model=result.model,
            )
        
        products[key].prices.append({
            "source": f"历史记录({result.source})",
            "source_type": "history",
            "price": result.price,
            "currency": result.currency,
            "timestamp": result.timestamp,
            "similarity": result.similarity,
        })
    
    def _make_key(self, name: str, brand: str = "", model: str = "") -> str:
        """生成产品唯一键"""
        return f"{brand}:{name}:{model}".lower()
    
    def generate_report(
        self,
        results: List[AggregatedPrice],
        format: str = "markdown"
    ) -> str:
        """生成报告"""
        if format == "markdown":
            return self._generate_markdown(results)
        elif format == "json":
            return json.dumps([r.to_dict() for r in results], ensure_ascii=False, indent=2)
        elif format == "csv":
            return self._generate_csv(results)
        else:
            raise ValueError(f"Unknown format: {format}")
    
    def _generate_markdown(self, results: List[AggregatedPrice]) -> str:
        """生成 Markdown 报告"""
        lines = [
            "# 询价报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"共 {len(results)} 个产品",
            "",
            "---",
            "",
        ]
        
        for r in results:
            lines.append(r.to_markdown())
            lines.append("")
            lines.append("---")
            lines.append("")
        
        return "\n".join(lines)
    
    def _generate_csv(self, results: List[AggregatedPrice]) -> str:
        """生成 CSV 报告"""
        lines = ["产品名称,品牌,型号,最低价,最高价,平均价,推荐来源,推荐价格,报价数量"]
        
        for r in results:
            lines.append(
                f'"{r.product_name}","{r.brand}","{r.model}",'
                f'{r.min_price},{r.max_price},{r.avg_price:.2f},'
                f'"{r.recommended_source}",{r.recommended_price},{r.source_count}'
            )
        
        return "\n".join(lines)
