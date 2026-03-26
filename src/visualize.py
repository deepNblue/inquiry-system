#!/usr/bin/env python3
"""
HTML 可视化图表生成器
"""

import os
from typing import List, Dict
from datetime import datetime


class HTMLChart:
    """HTML 图表生成器"""
    
    @staticmethod
    def generate_price_chart(products: List[Dict]) -> str:
        """生成价格柱状图 HTML"""
        
        # 按价格排序
        items = [(p['product_name'], p.get('min_price', 0) * p.get('quantity', 1)) 
                 for p in products if p.get('min_price', 0) > 0]
        items.sort(key=lambda x: x[1], reverse=True)
        
        max_price = max(v for _, v in items) if items else 1
        
        # 准备数据
        labels = [name[:8] + '...' if len(name) > 8 else name for name, _ in items]
        values = [v for _, v in items]
        
        html = f'''
<div class="chart-container">
    <h3>💰 设备价格对比</h3>
    <div class="bar-chart">
'''

        for label, value in items:
            width = int(value / max_price * 100)
            html += f'''
        <div class="bar-item">
            <div class="bar-label">{label}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width: {width}%"></div>
            </div>
            <div class="bar-value">¥{value:,.0f}</div>
        </div>
'''

        html += '''
    </div>
</div>
'''
        return html
    
    @staticmethod
    def generate_confidence_pie(products: List[Dict]) -> str:
        """生成置信度饼图"""
        
        high = sum(1 for p in products if p.get('overall_confidence', 0) >= 70)
        medium = sum(1 for p in products if 50 <= p.get('overall_confidence', 0) < 70)
        low = sum(1 for p in products if 0 < p.get('overall_confidence', 0) < 50)
        none = sum(1 for p in products if p.get('overall_confidence', 0) == 0)
        
        total = len(products)
        if total == 0:
            return ""
        
        # 简单进度条表示
        high_pct = high / total * 100
        medium_pct = medium / total * 100
        low_pct = low / total * 100
        
        html = f'''
<div class="chart-container">
    <h3>📊 数据置信度分布</h3>
    <div class="pie-container">
        <div class="pie-bar">
            <div class="pie-segment high" style="width: {high_pct}%"></div>
            <div class="pie-segment medium" style="width: {medium_pct}%"></div>
            <div class="pie-segment low" style="width: {low_pct}%"></div>
        </div>
    </div>
    <div class="pie-legend">
        <span class="legend-item"><span class="dot high"></span> 高置信度 ({high})</span>
        <span class="legend-item"><span class="dot medium"></span> 中置信度 ({medium})</span>
        <span class="legend-item"><span class="dot low"></span> 低置信度 ({low})</span>
        <span class="legend-item"><span class="dot none"></span> 无数据 ({none})</span>
    </div>
</div>
'''
        return html
    
    @staticmethod
    def generate_spec_match_chart(products: List[Dict]) -> str:
        """生成规格匹配率图表"""
        
        items = [(p['product_name'][:10], p.get('spec_match', 0)) for p in products]
        max_match = 100
        
        html = '''
<div class="chart-container">
    <h3>🔍 规格匹配率</h3>
    <div class="bar-chart">
'''

        for label, value in items:
            color = '#28a745' if value >= 90 else ('#ffc107' if value >= 70 else '#dc3545')
            html += f'''
        <div class="bar-item">
            <div class="bar-label">{label}</div>
            <div class="bar-track">
                <div class="bar-fill" style="width: {value}%; background: {color}"></div>
            </div>
            <div class="bar-value">{value:.0f}%</div>
        </div>
'''

        html += '''
    </div>
</div>
'''
        return html
    
    @staticmethod
    def get_css() -> str:
        """获取 CSS 样式"""
        return '''
<style>
.chart-container {
    background: white;
    border-radius: 10px;
    padding: 20px;
    margin: 20px 0;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}
.chart-container h3 {
    margin: 0 0 15px 0;
    color: #333;
}
.bar-chart {
    display: flex;
    flex-direction: column;
    gap: 10px;
}
.bar-item {
    display: flex;
    align-items: center;
    gap: 10px;
}
.bar-label {
    width: 80px;
    font-size: 12px;
    color: #666;
    text-align: right;
}
.bar-track {
    flex: 1;
    height: 20px;
    background: #f0f0f0;
    border-radius: 4px;
    overflow: hidden;
}
.bar-fill {
    height: 100%;
    background: linear-gradient(90deg, #667eea, #764ba2);
    border-radius: 4px;
    transition: width 0.5s ease;
}
.bar-value {
    width: 80px;
    font-size: 12px;
    font-weight: bold;
    color: #333;
}
.pie-container {
    margin: 15px 0;
}
.pie-bar {
    display: flex;
    height: 30px;
    border-radius: 15px;
    overflow: hidden;
}
.pie-segment {
    height: 100%;
    transition: width 0.5s ease;
}
.pie-segment.high { background: #28a745; }
.pie-segment.medium { background: #ffc107; }
.pie-segment.low { background: #dc3545; }
.pie-legend {
    display: flex;
    gap: 20px;
    margin-top: 15px;
    flex-wrap: wrap;
}
.legend-item {
    display: flex;
    align-items: center;
    gap: 5px;
    font-size: 12px;
}
.dot {
    width: 10px;
    height: 10px;
    border-radius: 50%;
}
.dot.high { background: #28a745; }
.dot.medium { background: #ffc107; }
.dot.low { background: #dc3545; }
.dot.none { background: #ccc; }
</style>
'''


def generate_dashboard(products: List[Dict], output_path: str = "output/dashboard.html"):
    """生成可视化仪表板"""
    
    total_price = sum(p.get('min_price', 0) * p.get('quantity', 1) for p in products)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>询价仪表板</title>
    {HTMLChart.get_css()}
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 询价仪表板</h1>
            <div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
        </div>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{len(products)}</div>
                <div class="stat-label">设备种类</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">¥{total_price:,.0f}</div>
                <div class="stat-label">预计总价</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{sum(1 for p in products if p.get('min_price', 0) > 0)}</div>
                <div class="stat-label">有价格数据</div>
            </div>
        </div>
        
        {HTMLChart.generate_price_chart(products)}
        {HTMLChart.generate_confidence_pie(products)}
        {HTMLChart.generate_spec_match_chart(products)}
    </div>
</body>
</html>
'''
    
    os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"✓ 仪表板已生成: {output_path}")


if __name__ == "__main__":
    import csv
    from src.history import HistoryMatcher
    from spec_compare import SpecComparator
    
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
    
    matcher = HistoryMatcher()
    comparator = SpecComparator()
    
    for p in products:
        matches = matcher.search_similar(p['product_name'], brand=p.get('brand', ''), top_k=3)
        if matches:
            p['min_price'] = min(m.price for m in matches)
            p['overall_confidence'] = int(sum(m.similarity for m in matches) / len(matches) * 100)
            comparison = comparator.compare_product(p['product_name'], p['specs'], matches[0].specs or '')
            total = len(comparison.items)
            matched = sum(1 for i in comparison.items if i.status == 'match')
            p['spec_match'] = (matched / total * 100) if total > 0 else 0
        else:
            p['min_price'] = 0
            p['overall_confidence'] = 0
            p['spec_match'] = 0
    
    matcher.close()
    
    generate_dashboard(products)
