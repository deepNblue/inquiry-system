#!/usr/bin/env python3
"""生成完整可视化报告"""

import os
import csv
from datetime import datetime
from src.history import HistoryMatcher
from src.charts import generate_summary_text, generate_price_comparison, generate_confidence_chart
from src.visualize import generate_dashboard


def main():
    # 加载设备
    products = []
    with open('examples/equipment_list.csv', 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                'product_name': row.get('设备名称', ''),
                'brand': row.get('品牌', ''),
                'model': row.get('型号', ''),
                'specs': row.get('技术参数', ''),
                'quantity': int(row.get('数量', 1)),
                'unit': row.get('单位', '台'),
            })

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

    total_price = sum(p['min_price'] * p['quantity'] for p in products)
    now = datetime.now().strftime('%Y-%m-%d %H:%M')

    # Markdown报告
    lines = [
        f'# 智能化项目设备询价报告',
        '',
        f'**生成时间**: {now}',
        '',
        '---',
        '',
        '## 📊 项目概览',
        '',
        '| 指标 | 数值 |',
        '|------|------|',
        f'| 设备种类 | {len(products)} |',
        f'| 有价格数据 | {sum(1 for p in products if p["min_price"] > 0)} |',
        f'| 预计总价 | ¥{total_price:,.0f} |',
        '',
        '---',
        '',
        '## 💰 价格汇总',
        '',
        '```',
        generate_price_comparison(products),
        '```',
        '',
        '---',
        '',
        '## 📈 置信度',
        '',
        '```',
        generate_confidence_chart(products),
        '```',
        '',
        '---',
        '',
        '## 📋 设备明细',
        '',
        '| 序号 | 设备 | 品牌 | 数量 | 单价 | 小计 | 置信度 |',
        '|------|------|------|------|------|------|--------|',
    ]

    for i, p in enumerate(products, 1):
        price = p.get('min_price', 0)
        qty = p['quantity']
        conf = p.get('overall_confidence', 0)
        
        if conf >= 70:
            icon = '🟢'
        elif conf >= 50:
            icon = '🟡'
        else:
            icon = '🔴'
        
        price_text = f'¥{price:,.0f}' if price > 0 else '待询价'
        subtotal = f'¥{price * qty:,.0f}' if price > 0 else '-'
        
        lines.append(f'| {i} | {p["product_name"]} | {p["brand"]} | {qty}{p["unit"]} | {price_text} | {subtotal} | {icon}{conf}% |')

    lines.extend([
        '',
        '---',
        '',
        '## 📁 相关文件',
        '',
        '| 文件 | 说明 |',
        '|------|------|',
        '| output/dashboard.html | 可视化仪表板 |',
        '| output/final_report.md | 详细报告 |',
        '',
        '---',
        '',
        '*本报告由自动询价系统生成*',
    ])

    report = '\n'.join(lines)
    
    os.makedirs('output', exist_ok=True)
    with open('output/visual_report.md', 'w', encoding='utf-8') as f:
        f.write(report)

    # 生成HTML仪表板
    generate_dashboard(products)

    print('='*50)
    print('  报告生成完成')
    print('='*50)
    print()
    print('📁 文件:')
    print('   output/visual_report.md    (文本报告)')
    print('   output/dashboard.html      (可视化仪表板)')
    print()
    print(f'💰 预计总价: ¥{total_price:,.0f}')


if __name__ == '__main__':
    main()
