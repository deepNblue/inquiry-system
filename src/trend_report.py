"""
趋势分析报告模块
生成趋势分析报表和建议
"""

from typing import List, Dict, Optional, Any
from datetime import datetime
from dataclasses import dataclass


@dataclass
class ProductReport:
    """单个产品报告"""
    product_name: str
    brand: str
    
    # 趋势分析
    trend: str
    trend_score: int
    direction: str
    
    # 价格统计
    current_price: float
    avg_price: float
    min_price: float
    max_price: float
    
    # 建议
    recommendation: str
    recommendation_reason: str
    
    # 预测
    predicted_price: float = 0
    prediction_confidence: float = 0


class TrendReporter:
    """
    趋势分析报告生成器
    """
    
    def __init__(self):
        pass
    
    def generate_report(
        self,
        analyses: List[Any],
        predictions: List[Dict] = None
    ) -> str:
        """
        生成趋势分析报告
        
        Args:
            analyses: 趋势分析结果列表
            predictions: 预测结果列表
        
        Returns:
            Markdown 格式报告
        """
        lines = [
            "# 📊 价格趋势分析报告",
            "",
            f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            ""
        ]
        
        if not analyses:
            lines.append("*暂无数据*")
            return "\n".join(lines)
        
        # 概览
        total = len(analyses)
        buy_recs = sum(1 for a in analyses if getattr(a, 'recommendation', '') == 'buy')
        wait_recs = sum(1 for a in analyses if getattr(a, 'recommendation', '') == 'wait')
        hold_recs = sum(1 for a in analyses if getattr(a, 'recommendation', '') in ['hold', 'insufficient_data'])
        
        lines.extend([
            "## 📈 概览",
            "",
            f"| 指标 | 数值 |",
            f"|------|------|",
            f"| 产品数量 | {total} |",
            f"| 建议购买 | {buy_recs} |",
            f"| 建议观望 | {wait_recs} |",
            f"| 可考虑 | {hold_recs} |",
            ""
        ])
        
        # 详细分析
        lines.extend([
            "---",
            "",
            "## 📋 详细分析",
            ""
        ])
        
        for a in analyses:
            name = getattr(a, 'product_name', '未知')
            brand = getattr(a, 'brand', '')
            
            direction = getattr(a, 'direction', 'unknown')
            direction_emoji = {
                'up': '📈',
                'down': '📉',
                'stable': '➡️',
                'unknown': '❓'
            }.get(str(direction).split('.')[-1], '❓')
            
            recommendation = getattr(a, 'recommendation', '')
            rec_emoji = {
                'buy': '✅',
                'wait': '⏳',
                'hold': '🤔',
                'insufficient_data': '⚪'
            }.get(recommendation, '⚪')
            
            lines.extend([
                f"### {direction_emoji} {name} {f'({brand})' if brand else ''}",
                "",
            ])
            
            # 价格信息
            avg_p = getattr(a, 'avg_price', 0)
            min_p = getattr(a, 'min_price', 0)
            max_p = getattr(a, 'max_price', 0)
            score = getattr(a, 'trend_score', 50)
            
            lines.extend([
                f"| 指标 | 数值 |",
                f"|------|------|",
                f"| 平均价格 | ¥{avg_p:,.0f} |",
                f"| 价格区间 | ¥{min_p:,.0f} ~ ¥{max_p:,.0f} |",
                f"| 趋势评分 | {score} |",
                ""
            ])
            
            # 建议
            reason = getattr(a, 'recommendation_reason', '')
            lines.extend([
                f"**{rec_emoji} 建议: {recommendation.upper()}**",
                f"",
                f"*{reason}*",
                ""
            ])
            
            lines.append("---")
            lines.append("")
        
        # 采购建议汇总
        lines.extend([
            "## 🛒 采购建议汇总",
            ""
        ])
        
        # 建议购买
        buy_products = [a for a in analyses if getattr(a, 'recommendation', '') == 'buy']
        if buy_products:
            lines.append("### ✅ 建议立即购买")
            lines.append("")
            for a in buy_products:
                price = getattr(a, 'min_price', 0)
                lines.append(f"- **{a.product_name}**: ¥{price:,.0f}")
            lines.append("")
        
        # 可考虑
        hold_products = [a for a in analyses if getattr(a, 'recommendation', '') == 'hold']
        if hold_products:
            lines.append("### 🤔 可考虑购买")
            lines.append("")
            for a in hold_products:
                price = getattr(a, 'avg_price', 0)
                lines.append(f"- **{a.product_name}**: ¥{price:,.0f}")
            lines.append("")
        
        # 建议观望
        wait_products = [a for a in analyses if getattr(a, 'recommendation', '') == 'wait']
        if wait_products:
            lines.append("### ⏳ 建议观望")
            lines.append("")
            for a in wait_products:
                price = getattr(a, 'avg_price', 0)
                lines.append(f"- **{a.product_name}**: ¥{price:,.0f}")
            lines.append("")
        
        return "\n".join(lines)
    
    def generate_comparison_table(
        self,
        analyses: List[Any]
    ) -> str:
        """生成对比表格"""
        lines = [
            "| 产品 | 品牌 | 趋势 | 评分 | 当前参考价 | 建议 |",
            "|------|------|------|------|------------|------|"
        ]
        
        for a in analyses:
            name = a.product_name[:20]
            brand = a.brand or "-"
            
            direction = str(a.direction).split('.')[-1].lower()
            direction_icon = {'up': '📈', 'down': '📉', 'stable': '➡️', 'unknown': '❓'}.get(direction, '❓')
            
            score = a.trend_score
            score_icon = '🔴' if score > 65 else ('🟢' if score < 35 else '🟡')
            
            price = a.min_price if a.min_price > 0 else a.avg_price
            
            rec = a.recommendation.upper()
            
            lines.append(f"| {name} | {brand} | {direction_icon} | {score_icon}{score} | ¥{price:,.0f} | {rec} |")
        
        return "\n".join(lines)
    
    def generate_markdown_alert(
        self,
        analysis: Any
    ) -> str:
        """生成告警格式的 Markdown"""
        name = analysis.product_name
        direction = str(analysis.direction).split('.')[-1].lower()
        
        emoji = {'up': '📈', 'down': '📉', 'stable': '➡️', 'unknown': '❓'}.get(direction, '❓')
        
        lines = [
            f"{emoji} **{name}**",
            f"",
            f"趋势: {direction.upper()}",
            f"评分: {analysis.trend_score}/100",
            f"建议: {analysis.recommendation.upper()}",
            f"",
            f"*{analysis.recommendation_reason}*"
        ]
        
        return "\n".join(lines)


# 便捷函数
def generate_trend_report(analyses: List) -> str:
    """快速生成报告"""
    reporter = TrendReporter()
    return reporter.generate_report(analyses)
