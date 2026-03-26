#!/usr/bin/env python3
"""
价格趋势可视化
生成价格趋势图和对比图
"""

import os
import sys
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

# 生成简单的文本图表
class PriceChart:
    """文本价格图表"""
    
    def __init__(self, width: int = 60, height: int = 10):
        self.width = width
        self.height = height
    
    def bar_chart(self, data: Dict[str, float], title: str = "") -> str:
        """生成柱状图（文本）"""
        if not data:
            return "无数据"
        
        lines = []
        
        if title:
            lines.append(title)
            lines.append("=" * self.width)
        
        max_value = max(data.values())
        if max_value == 0:
            return "无有效数据"
        
        for label, value in data.items():
            bar_len = int(value / max_value * (self.width - 20))
            bar = "█" * bar_len
            lines.append(f"{label:15} │{bar} {value:,.0f}")
        
        return "\n".join(lines)
    
    def horizontal_bar(self, items: List[Tuple[str, float]], title: str = "") -> str:
        """水平柱状图"""
        if not items:
            return "无数据"
        
        lines = []
        
        if title:
            lines.append(title)
            lines.append("=" * self.width)
        
        max_value = max(v for _, v in items)
        if max_value == 0:
            return "无有效数据"
        
        max_label_len = max(len(l) for l, _ in items)
        
        for label, value in items:
            bar_len = int(value / max_value * (self.width - max_label_len - 15))
            bar = "▓" * bar_len
            pct = value / max_value * 100
            lines.append(f"{label:<{max_label_len}} │{bar} {value:>10,.0f} ({pct:5.1f}%)")
        
        return "\n".join(lines)


def generate_price_comparison(products: List[Dict]) -> str:
    """生成价格对比图"""
    chart = PriceChart(width=55)
    
    # 按价格排序
    items = [(p['product_name'], p.get('min_price', 0)) for p in products]
    items = [(name, price) for name, price in items if price > 0]
    items.sort(key=lambda x: x[1], reverse=True)
    
    return chart.horizontal_bar(items, "📊 设备价格对比")


def generate_confidence_chart(products: List[Dict]) -> str:
    """生成置信度图表"""
    chart = PriceChart(width=50)
    
    items = []
    for p in products:
        conf = p.get('overall_confidence', 0)
        if conf > 0:
            items.append((p['product_name'][:12], conf))
    
    return chart.horizontal_bar(items, "📈 数据置信度")


def generate_summary_text(products: List[Dict]) -> str:
    """生成汇总文本"""
    total_price = sum(p.get('min_price', 0) * p.get('quantity', 1) for p in products)
    total_items = len(products)
    has_price = sum(1 for p in products if p.get('min_price', 0) > 0)
    avg_conf = sum(p.get('overall_confidence', 0) for p in products if p.get('overall_confidence', 0) > 0)
    avg_conf = avg_conf / has_price if has_price > 0 else 0
    
    lines = [
        "┌" + "─" * 50 + "┐",
        "│" + "  询价汇总".center(50) + "│",
        "├" + "─" * 50 + "┤",
        f"│  设备种类: {total_items:<40}│",
        f"│  有价格数据: {has_price:<40}│",
        f"│  预计总价: ¥{total_price:>30,.0f}      │",
        f"│  平均置信度: {avg_conf:>28.0f}%     │",
        "└" + "─" * 50 + "┘",
    ]
    
    return "\n".join(lines)


def main():
    """测试图表生成"""
    import csv
    from src.history import HistoryMatcher
    
    # 加载设备
    products = []
    with open('examples/equipment_list.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                'product_name': row.get('设备名称', ''),
                'brand': row.get('品牌', ''),
                'specs': row.get('技术参数', ''),
                'quantity': int(row.get('数量', 1)),
            })
    
    # 查询价格
    matcher = HistoryMatcher()
    for p in products:
        matches = matcher.search_similar(p['product_name'], brand=p.get('brand', ''), top_k=3)
        if matches:
            p['min_price'] = min(m.price for m in matches)
            p['overall_confidence'] = int(sum(m.similarity for m in matches) / len(matches) * 100)
        else:
            p['min_price'] = 0
            p['overall_confidence'] = 0
    matcher.close()
    
    print(generate_summary_text(products))
    print()
    print(generate_price_comparison(products))
    print()
    print(generate_confidence_chart(products))


if __name__ == "__main__":
    main()
