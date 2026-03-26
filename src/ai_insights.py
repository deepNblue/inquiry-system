"""
AI 增强模块
LLM 驱动的报告摘要和采购建议
"""

import os
import json
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class InquiryInsight:
    """询价洞察"""
    summary: str  # 摘要
    recommendations: List[str]  # 建议
    price_analysis: str  # 价格分析
    market_trend: str  # 市场趋势
    risk_alerts: List[str]  # 风险提示


class AIReportGenerator:
    """
    AI 报告生成器
    使用 LLM 生成询价报告摘要和洞察
    """
    
    def __init__(self, api_key: str = None, model: str = "gpt-3.5-turbo"):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.model = model
        self.base_url = "https://api.openai.com/v1"
    
    async def generate_report_summary(
        self,
        products: List[Dict],
        include_recommendations: bool = True
    ) -> str:
        """
        生成报告摘要
        
        Args:
            products: 产品询价结果
            include_recommendations: 是否包含采购建议
        
        Returns:
            摘要文本
        """
        if not self.api_key:
            return self._generate_simple_summary(products)
        
        try:
            import httpx
            
            # 构建提示
            prompt = self._build_summary_prompt(products, include_recommendations)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的采购分析助手，负责生成简洁、准确的询价报告摘要。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.3,
                        "max_tokens": 500
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data["choices"][0]["message"]["content"]
                else:
                    return self._generate_simple_summary(products)
                    
        except Exception as e:
            print(f"LLM 调用失败: {e}")
            return self._generate_simple_summary(products)
    
    def _build_summary_prompt(self, products: List[Dict], include_recommendations: bool) -> str:
        """构建提示词"""
        
        # 格式化产品数据
        product_lines = []
        for p in products:
            name = p.get("product_name", "未知")
            min_p = p.get("min_price", 0)
            max_p = p.get("max_price", 0)
            source = p.get("recommended_source", "")
            count = p.get("source_count", 0)
            
            if min_p > 0:
                product_lines.append(f"- {name}: ¥{min_p:,.0f}~¥{max_p:,.0f} (推荐{source}, {count}个来源)")
            else:
                product_lines.append(f"- {name}: 待报价")
        
        products_text = "\n".join(product_lines)
        
        prompt = f"""
请为以下询价结果生成简洁摘要：

{products_text}

请按以下格式回复：
1. 总体概述（一句话）
2. 价格亮点（最低价的2-3个产品）
3. 待询价产品（如有）

"""
        
        if include_recommendations:
            prompt += "\n4. 采购建议（最优购买时机和渠道）"
        
        return prompt
    
    def _generate_simple_summary(self, products: List[Dict]) -> str:
        """生成简单摘要（无 LLM）"""
        total = len(products)
        quoted = sum(1 for p in products if p.get("min_price", 0) > 0)
        pending = total - quoted
        
        total_savings = sum(
            p.get("max_price", 0) - p.get("min_price", 0)
            for p in products if p.get("max_price", 0) > 0
        )
        
        lines = [
            f"## 询价摘要",
            "",
            f"共询价 {total} 个产品，其中 {quoted} 个已获取报价，{pending} 个待报价。",
            "",
        ]
        
        # 最低价产品
        quoted_products = [p for p in products if p.get("min_price", 0) > 0]
        if quoted_products:
            quoted_products.sort(key=lambda x: x.get("min_price", 0))
            
            lines.append("### 价格最优")
            for p in quoted_products[:3]:
                lines.append(f"- **{p['product_name']}**: ¥{p['min_price']:,.0f} ({p.get('recommended_source', '')})")
            lines.append("")
        
        # 节省潜力
        if total_savings > 0:
            lines.append(f"### 节省潜力")
            lines.append(f"最高价与最低价差额总计约 ¥{total_savings:,.0f}")
        
        return "\n".join(lines)
    
    async def generate_insights(
        self,
        products: List[Dict],
        history_trends: Dict[str, List] = None
    ) -> InquiryInsight:
        """
        生成深度洞察
        
        Args:
            products: 当前询价结果
            history_trends: 历史趋势数据
        
        Returns:
            询价洞察
        """
        if not self.api_key:
            return self._generate_simple_insights(products)
        
        try:
            import httpx
            
            prompt = self._build_insight_prompt(products, history_trends)
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": "你是一个专业的市场分析专家，擅长价格分析和采购策略建议。"},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.5,
                        "max_tokens": 800
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data["choices"][0]["message"]["content"]
                    return self._parse_insights(content)
                else:
                    return self._generate_simple_insights(products)
                    
        except Exception as e:
            print(f"洞察生成失败: {e}")
            return self._generate_simple_insights(products)
    
    def _build_insight_prompt(self, products: List[Dict], trends: Dict = None) -> str:
        """构建洞察提示"""
        
        product_lines = []
        for p in products:
            name = p.get("product_name", "")
            min_p = p.get("min_price", 0)
            max_p = p.get("max_price", 0)
            source = p.get("recommended_source", "")
            
            if min_p > 0:
                product_lines.append(f"- {name}: ¥{min_p:,.0f}~¥{max_p:,.0f}")
        
        prompt = f"""
分析以下询价数据，生成采购洞察：

当前询价：
{chr(10).join(product_lines) if product_lines else "无报价数据"}

请分析：
1. 价格是否合理（偏高/偏低/合理）
2. 当前是否是好的采购时机
3. 推荐的采购策略
4. 需要关注的风险点

请用简洁的要点回复，每点不超过20字。
"""
        
        return prompt
    
    def _parse_insights(self, content: str) -> InquiryInsight:
        """解析洞察回复"""
        lines = content.split("\n")
        
        return InquiryInsight(
            summary=lines[0] if lines else "基于当前数据分析",
            recommendations=[l for l in lines if "建议" in l or "推荐" in l][:3],
            price_analysis="\n".join(lines[:3]),
            market_trend="稳定",
            risk_alerts=[l for l in lines if "风险" in l or "注意" in l][:2]
        )
    
    def _generate_simple_insights(self, products: List[Dict]) -> InquiryInsight:
        """生成简单洞察"""
        
        quoted = [p for p in products if p.get("min_price", 0) > 0]
        
        if quoted:
            avg_price = sum(p.get("min_price", 0) for p in quoted) / len(quoted)
            price_range = max(p.get("max_price", 0) for p in quoted) - min(p.get("min_price", 0) for p in quoted)
            
            summary = f"平均价格 ¥{avg_price:,.0f}，价格区间差异 ¥{price_range:,.0f}"
            analysis = "价格整体合理" if price_range < avg_price * 0.2 else "价格差异较大，建议多方比价"
        else:
            summary = "暂无报价数据"
            analysis = "等待供应商报价"
        
        return InquiryInsight(
            summary=summary,
            recommendations=[
                "建议选择报价最低的供应商",
                "关注促销活动获取更优价格",
                "大批量采购可谈折扣"
            ],
            price_analysis=analysis,
            market_trend="市场价格稳定",
            risk_alerts=[
                "密切关注价格波动",
                "及时跟进待报价产品"
            ]
        )


class PurchaseAdvisor:
    """
    采购建议器
    基于询价结果给出具体采购建议
    """
    
    def generate_recommendations(
        self,
        products: List[Dict],
        budget: float = None,
        urgency: str = "normal"  # urgent, normal, flexible
    ) -> List[Dict]:
        """
        生成采购建议
        
        Args:
            products: 询价结果
            budget: 预算限制
            urgency: 紧急程度
        
        Returns:
            建议列表
        """
        recommendations = []
        
        for p in products:
            if p.get("min_price", 0) <= 0:
                continue
            
            name = p.get("product_name", "")
            best_price = p.get("min_price", 0)
            best_source = p.get("recommended_source", "")
            max_price = p.get("max_price", 0)
            sources = p.get("source_count", 0)
            
            rec = {
                "product": name,
                "recommended": {
                    "source": best_source,
                    "price": best_price,
                    "savings": max_price - best_price if max_price > best_price else 0
                },
                "urgency": urgency,
                "action": ""
            }
            
            # 根据紧迫程度给出建议
            if urgency == "urgent":
                rec["action"] = f"立即从 {best_source} 采购"
            elif urgency == "normal":
                if sources >= 3:
                    rec["action"] = f"可从 {best_source} 采购，预计节省 ¥{rec['recommended']['savings']:,.0f}"
                else:
                    rec["action"] = f"建议再观望1-2天，比较更多渠道后采购"
            else:  # flexible
                rec["action"] = "价格合适可入手，不急可等促销"
            
            # 预算检查
            if budget and best_price > budget:
                rec["action"] += "（超出预算）"
                rec["warning"] = f"超出预算 ¥{best_price - budget:,.0f}"
            
            recommendations.append(rec)
        
        return recommendations


# 便捷函数
async def generate_summary(products: List[Dict]) -> str:
    """快速生成摘要"""
    generator = AIReportGenerator()
    return await generator.generate_report_summary(products)


def get_recommendations(products: List[Dict], **kwargs) -> List[Dict]:
    """快速获取建议"""
    advisor = PurchaseAdvisor()
    return advisor.generate_recommendations(products, **kwargs)
