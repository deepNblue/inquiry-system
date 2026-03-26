"""
增强结果汇总模块
整合三种询价方式的结果，带置信度和偏离说明
"""

from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class InquirySource(Enum):
    """询价来源"""
    WEB = "web"
    MANUFACTURER = "manufacturer"
    EMAIL = "email"
    HISTORY = "history"


@dataclass
class PriceSource:
    """价格来源"""
    source: str              # 来源名称: 京东/淘宝/邮件等
    source_type: InquirySource
    price: float             # 价格
    timestamp: datetime      # 获取时间
    url: str = ""            # 链接
    confidence: float = 0    # 置信度 0-100
    specs_deviation: str = "" # 参数偏离说明
    notes: str = ""          # 备注


@dataclass
class EnhancedPriceResult:
    """增强的价格结果"""
    product_name: str
    brand: str = ""
    model: str = ""
    specs_required: Dict[str, str] = field(default_factory=dict)  # 需求规格
    specs_actual: Dict[str, str] = field(default_factory=dict)     # 实际规格
    
    # 价格来源列表
    sources: List[PriceSource] = field(default_factory=list)
    
    # 统计
    min_price: float = 0
    max_price: float = 0
    avg_price: float = 0
    recommended_source: str = ""
    recommended_price: float = 0
    
    # 整体评估
    overall_confidence: float = 0      # 整体置信度
    qualification: str = "unknown"     # 合格性: qualified/partial/unqualified
    warnings: List[str] = field(default_factory=list)
    
    # 参数对比
    specs_match_score: float = 0       # 参数匹配分数
    specs_deviations: List[Dict] = field(default_factory=list)


class EnhancedResultAggregator:
    """
    增强结果聚合器
    整合多种来源的结果，计算置信度，生成详细报告
    """
    
    def __init__(self):
        self.comparator = None  # 延迟导入
        self.confidence_engine = None
    
    def _init_engines(self):
        if self.comparator is None:
            from src.spec_comparator import SpecComparator
            self.comparator = SpecComparator()
        if self.confidence_engine is None:
            from src.confidence import ConfidenceEngine, PriceRecord
            self.confidence_engine = ConfidenceEngine()
    
    def aggregate(
        self,
        web_results: List[Any] = None,
        manufacturer_results: List[Any] = None,
        email_results: List[Any] = None,
        history_results: List[Any] = None,
        requirement: Dict = None
    ) -> List[EnhancedPriceResult]:
        """
        聚合多种来源的结果
        
        Args:
            web_results: 网页询价结果
            manufacturer_results: 厂家询价结果
            email_results: 邮件询价结果
            history_results: 历史询价结果
            requirement: 需求规格
        
        Returns:
            聚合后的增强结果
        """
        self._init_engines()
        
        # 按产品分组
        product_data: Dict[str, EnhancedPriceResult] = {}
        
        # 处理各类结果
        for source_type, results in [
            (InquirySource.WEB, web_results or []),
            (InquirySource.MANUFACTURER, manufacturer_results or []),
            (InquirySource.EMAIL, email_results or []),
            (InquirySource.HISTORY, history_results or []),
        ]:
            for r in results:
                self._process_result(r, source_type, product_data)
        
        # 计算统计数据
        for product, result in product_data.items():
            self._calculate_stats(result, requirement)
        
        return list(product_data.values())
    
    def _process_result(
        self,
        result: Any,
        source_type: InquirySource,
        product_data: Dict[str, EnhancedPriceResult]
    ):
        """处理单个结果"""
        # 获取产品标识
        product_name = getattr(result, 'product_name', '') or getattr(result, 'name', '')
        if not product_name:
            return
        
        # 创建或获取产品记录
        if product_name not in product_data:
            product_data[product_name] = EnhancedPriceResult(product_name=product_name)
        
        record = product_data[product_name]
        
        # 提取价格来源
        price_source = PriceSource(
            source=getattr(result, 'source', 'Unknown'),
            source_type=source_type,
            price=getattr(result, 'price', 0) or getattr(result, 'min_price', 0),
            timestamp=getattr(result, 'timestamp', datetime.now()),
            url=getattr(result, 'url', ''),
            notes=getattr(result, 'notes', '')
        )
        
        record.sources.append(price_source)
        
        # 更新基本信息
        if getattr(result, 'brand', ''):
            record.brand = result.brand
        if getattr(result, 'model', ''):
            record.model = result.model
    
    def _calculate_stats(self, result: EnhancedPriceResult, requirement: Dict):
        """计算统计信息"""
        if not result.sources:
            return
        
        # 价格统计
        prices = [s.price for s in result.sources if s.price > 0]
        if prices:
            result.min_price = min(prices)
            result.max_price = max(prices)
            result.avg_price = sum(prices) / len(prices)
            
            # 推荐来源：最低价且置信度高
            best_source = None
            best_score = -1
            for s in result.sources:
                if s.price == result.min_price:
                    if s.confidence > best_score:
                        best_score = s.confidence
                        best_source = s
            
            if best_source:
                result.recommended_source = best_source.source
                result.recommended_price = best_source.price
        
        # 计算整体置信度
        result.overall_confidence = self._calculate_overall_confidence(result, requirement)
        
        # 参数偏离分析
        if requirement and requirement.get("specs"):
            self._analyze_specs(result, requirement)
    
    def _calculate_overall_confidence(self, result: EnhancedPriceResult, requirement: Dict) -> float:
        """计算整体置信度"""
        if not result.sources:
            return 0
        
        # 加权平均
        total_weight = 0
        weighted_sum = 0
        
        for s in result.sources:
            # 来源权重
            source_weight = {
                InquirySource.WEB: 0.3,
                InquirySource.MANUFACTURER: 0.4,
                InquirySource.EMAIL: 0.2,
                InquirySource.HISTORY: 0.1,
            }.get(s.source_type, 0.2)
            
            total_weight += source_weight
            weighted_sum += (s.confidence or 50) * source_weight
        
        base_confidence = weighted_sum / total_weight if total_weight > 0 else 50
        
        # 根据来源数量调整
        source_count_bonus = min(len(result.sources) * 5, 20)  # 最多+20
        
        return min(100, base_confidence + source_count_bonus)
    
    def _analyze_specs(self, result: EnhancedPriceResult, requirement: Dict):
        """分析参数偏离"""
        specs_required = requirement.get("specs", {})
        
        # 从来源中提取规格
        specs_actual = {}
        for s in result.sources:
            if hasattr(s, 'specs'):
                specs_actual.update(getattr(s, 'specs', {}))
        
        if specs_required and specs_actual:
            comparison = self.comparator.compare(specs_required, specs_actual, result.product_name)
            
            result.specs_match_score = comparison.overall_score
            result.specs_deviations = [c.to_dict() for c in comparison.comparisons]
            result.specs_actual = specs_actual
            
            # 判断合格性
            if comparison.is_qualified:
                result.qualification = "qualified"
            elif comparison.overall_score >= 60:
                result.qualification = "partial"
                result.warnings.extend([c.deviation_desc for c in comparison.comparisons if c.severity != "info"])
            else:
                result.qualification = "unqualified"
                result.warnings.extend([c.deviation_desc for c in comparison.comparisons])
    
    def generate_markdown_report(self, results: List[EnhancedPriceResult]) -> str:
        """生成 Markdown 报告"""
        lines = [
            "# 清单询价报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"共 **{len(results)}** 个产品",
            "",
            "---",
            ""
        ]
        
        for r in results:
            lines.extend(self._generate_product_section(r))
        
        return "\n".join(lines)
    
    def _generate_product_section(self, result: EnhancedPriceResult) -> List[str]:
        """生成单个产品的报告部分"""
        lines = [
            f"## {result.product_name}",
            "",
        ]
        
        # 基本信息
        if result.brand:
            lines.append(f"**品牌**: {result.brand}")
        if result.model:
            lines.append(f"**型号**: {result.model}")
        lines.append("")
        
        # 整体评估
        conf_icon = "🟢" if result.overall_confidence >= 70 else ("🟡" if result.overall_confidence >= 50 else "🔴")
        qual_icon = "✅" if result.qualification == "qualified" else ("⚠️" if result.qualification == "partial" else "❌")
        
        lines.extend([
            f"**置信度**: {conf_icon} {result.overall_confidence:.0f}%",
            f"**符合要求**: {qual_icon} {result.qualification}",
            ""
        ])
        
        # 价格来源表
        if result.sources:
            lines.append("### 价格来源"),
            lines.append("")
            lines.append("| 来源 | 类型 | 价格 | 置信度 | 备注 |")
            lines.append("|------|------|------|--------|------|")
            
            for s in result.sources:
                type_name = {
                    InquirySource.WEB: "网页",
                    InquirySource.MANUFACTURER: "厂家",
                    InquirySource.EMAIL: "邮件",
                    InquirySource.HISTORY: "历史",
                }.get(s.source_type, s.source_type.value)
                
                lines.append(f"| {s.source} | {type_name} | ¥{s.price:,.0f} | {s.confidence:.0f}% | {s.notes or '-'} |")
            
            lines.append("")
        
        # 统计
        if result.min_price > 0:
            lines.extend([
                "### 价格统计",
                "",
                f"- **最低价**: ¥{result.min_price:,.0f} ({result.recommended_source})",
                f"- **最高价**: ¥{result.max_price:,.0f}",
                f"- **平均价**: ¥{result.avg_price:,.0f}",
                f"- **推荐采购价**: ¥{result.recommended_price:,.0f}",
                ""
            ])
        
        # 参数偏离
        if result.specs_deviations:
            lines.extend([
                "### 参数对比",
                ""
            ])
            
            # 严重偏离
            critical = [d for d in result.specs_deviations if d.get("severity") == "critical"]
            if critical:
                lines.append("#### 🔴 严重偏离")
                for d in critical:
                    lines.append(f"- **{d['param']}**: {d['description']}")
                lines.append("")
            
            # 轻微偏离
            warnings = [d for d in result.specs_deviations if d.get("severity") == "warning"]
            if warnings:
                lines.append("#### 🟡 轻微偏离")
                for d in warnings:
                    lines.append(f"- {d['param']}: {d['description']}")
                lines.append("")
        
        # 警告
        if result.warnings:
            lines.extend([
                "### ⚠️ 注意事项",
                ""
            ])
            for w in result.warnings:
                lines.append(f"- {w}")
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return lines
