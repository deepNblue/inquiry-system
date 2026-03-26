"""
增强报告生成器
支持 Markdown + HTML 双格式
"""

import os
from typing import List, Dict, Optional
from datetime import datetime
from dataclasses import dataclass


@dataclass
class InquiryReport:
    """询价报告"""
    title: str
    products: List[Dict]
    summary: Dict
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class ReportGenerator:
    """
    报告生成器
    生成 Markdown 和 HTML 格式的报告
    """
    
    def __init__(self):
        self.template_dir = "templates"
    
    def generate(
        self,
        products: List[Dict],
        title: str = "询价报告",
        format: str = "markdown"
    ) -> str:
        """
        生成报告
        
        Args:
            products: 产品列表
            title: 报告标题
            format: markdown 或 html
        
        Returns:
            报告内容
        """
        if format == "html":
            return self._generate_html(products, title)
        else:
            return self._generate_markdown(products, title)
    
    def _generate_markdown(self, products: List[Dict], title: str) -> str:
        """生成 Markdown 报告"""
        lines = [
            f"# {title}",
            "",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            f"共 **{len(products)}** 个产品",
            "",
            "---",
            ""
        ]
        
        # 统计
        if products:
            prices = [p.get('min_price', 0) for p in products if p.get('min_price', 0) > 0]
            total = sum(prices)
            avg = total / len(prices) if prices else 0
            
            lines.extend([
                "## 📊 统计概览",
                "",
                f"| 指标 | 数值 |",
                f"|------|------|",
                f"| 产品数量 | {len(products)} |",
                f"| 最低总价 | ¥{total:,.2f} |",
                f"| 平均单价 | ¥{avg:,.2f} |",
                ""
            ])
        
        # 产品详情
        for i, p in enumerate(products, 1):
            lines.extend(self._format_product_markdown(p, i))
        
        return "\n".join(lines)
    
    def _format_product_markdown(self, product: Dict, index: int) -> List[str]:
        """格式化产品为 Markdown"""
        lines = []
        
        name = product.get('product_name', product.get('name', '未知产品'))
        brand = product.get('brand', '')
        model = product.get('model', '')
        specs = product.get('specs', '')
        
        lines.extend([
            f"## {index}. {name}",
            ""
        ])
        
        # 基本信息
        if brand:
            lines.append(f"**品牌**: {brand}")
        if model:
            lines.append(f"**型号**: {model}")
        
        # 技术参数
        if specs:
            lines.extend([
                "",
                "### 🔧 技术参数"
            ])
            # 解析参数（格式: 名称:值;名称:值）
            params = specs.split(';')
            for param in params:
                param = param.strip()
                if ':' in param:
                    key, value = param.split(':', 1)
                    lines.append(f"- **{key.strip()}**: {value.strip()}")
                else:
                    lines.append(f"- {param}")
            lines.append("")
        
        # 价格
        min_price = product.get('min_price', 0)
        max_price = product.get('max_price', 0)
        
        if min_price > 0:
            lines.extend([
                "",
                "### 💰 价格信息",
                "",
                f"| 来源 | 价格 |",
                f"|------|------|",
            ])
            
            sources = product.get('sources', [])
            if sources:
                for s in sources:
                    lines.append(f"| {s.get('source', '未知')} | ¥{s.get('price', 0):,.2f} |")
            else:
                lines.append(f"| 最低价 | ¥{min_price:,.2f} |")
                if max_price > min_price:
                    lines.append(f"| 最高价 | ¥{max_price:,.2f} |")
            
            lines.extend([
                "",
                f"**推荐采购价**: ¥{min_price:,.2f}",
                ""
            ])
        
        # 置信度
        confidence = product.get('overall_confidence', 0)
        if confidence > 0:
            icon = "🟢" if confidence >= 70 else ("🟡" if confidence >= 50 else "🔴")
            lines.extend([
                "### 📈 置信度",
                "",
                f"{icon} **{confidence:.0f}%**",
                ""
            ])
        
        # 参数偏离
        deviations = product.get('specs_deviations', [])
        if deviations:
            lines.extend([
                "### ⚠️ 参数偏离",
                ""
            ])
            
            for d in deviations:
                if d.get('severity') in ['critical', 'warning']:
                    lines.append(f"- **{d['param']}**: {d['description']}")
            
            lines.append("")
        
        lines.append("---")
        lines.append("")
        
        return lines
    
    def _generate_html(self, products: List[Dict], title: str) -> str:
        """生成 HTML 报告"""
        # 计算统计
        total_price = sum(p.get('min_price', 0) for p in products if p.get('min_price', 0) > 0)
        
        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: #f5f5f5;
            color: #333;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
        }}
        .header h1 {{ margin: 0 0 10px 0; }}
        .header .meta {{ opacity: 0.9; font-size: 14px; }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .stat-card .label {{ color: #666; font-size: 14px; }}
        .stat-card .value {{ font-size: 28px; font-weight: bold; color: #333; margin-top: 5px; }}
        .product {{
            background: white;
            border-radius: 10px;
            padding: 25px;
            margin-bottom: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }}
        .product-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 1px solid #eee;
        }}
        .product-name {{ font-size: 20px; font-weight: bold; }}
        .product-brand {{ color: #666; font-size: 14px; }}
        .confidence {{
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: bold;
        }}
        .confidence.high {{ background: #d4edda; color: #155724; }}
        .confidence.medium {{ background: #fff3cd; color: #856404; }}
        .confidence.low {{ background: #f8d7da; color: #721c24; }}
        .price-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        .price-table th, .price-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #eee;
        }}
        .price-table th {{ background: #f8f9fa; font-weight: 600; }}
        .recommendation {{
            background: #e7f3ff;
            border-left: 4px solid #2196F3;
            padding: 15px;
            margin-top: 15px;
            border-radius: 0 5px 5px 0;
        }}
        .warning {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin-top: 15px;
            border-radius: 0 5px 5px 0;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            color: #999;
            font-size: 12px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{title}</h1>
        <div class="meta">生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}</div>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="label">产品数量</div>
            <div class="value">{len(products)}</div>
        </div>
        <div class="stat-card">
            <div class="label">最低总价</div>
            <div class="value">¥{total_price:,.2f}</div>
        </div>
    </div>
"""
        
        # 产品详情
        for product in products:
            html += self._format_product_html(product)
        
        html += f"""
    <div class="footer">
        <p>由自动询价系统生成 | {datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>
</body>
</html>"""
        
        return html
    
    def _format_product_html(self, product: Dict) -> str:
        """格式化产品为 HTML"""
        name = product.get('product_name', product.get('name', '未知产品'))
        brand = product.get('brand', '')
        model = product.get('model', '')
        specs = product.get('specs', '')
        min_price = product.get('min_price', 0)
        confidence = product.get('overall_confidence', 0)
        
        conf_class = 'high' if confidence >= 70 else ('medium' if confidence >= 50 else 'low')
        conf_icon = '🟢' if confidence >= 70 else ('🟡' if confidence >= 50 else '🔴')
        
        html = f"""
    <div class="product">
        <div class="product-header">
            <div>
                <div class="product-name">{name}</div>
                <div class="product-brand">{brand} {model}</div>
            </div>
"""
        
        if confidence > 0:
            html += f'            <div class="confidence {conf_class}">{conf_icon} {confidence:.0f}%</div>\n'
        
        html += """        </div>
"""
        
        # 技术参数
        if specs:
            html += """
        <div style="background:#f8f9fa;padding:15px;border-radius:5px;margin:15px 0;">
            <strong>🔧 技术参数:</strong>
            <ul style="margin:10px 0 0 20px;padding:0;">
"""
            # 解析参数
            params = specs.split(';')
            for param in params:
                param = param.strip()
                if ':' in param:
                    key, value = param.split(':', 1)
                    html += f'                <li><strong>{key.strip()}:</strong> {value.strip()}</li>\n'
                else:
                    html += f'                <li>{param}</li>\n'
            
            html += """            </ul>
        </div>
"""
        
        # 价格表格
        if min_price > 0:
            html += """
        <table class="price-table">
            <thead>
                <tr>
                    <th>来源</th>
                    <th>价格</th>
                    <th>备注</th>
                </tr>
            </thead>
            <tbody>
"""
            
            sources = product.get('sources', [])
            if sources:
                for s in sources:
                    html += f"""                <tr>
                    <td>{s.get('source', '未知')}</td>
                    <td>¥{s.get('price', 0):,.2f}</td>
                    <td>{s.get('notes', '-')}</td>
                </tr>
"""
            else:
                html += f"""                <tr>
                    <td>最低价</td>
                    <td>¥{min_price:,.2f}</td>
                    <td>-</td>
                </tr>
"""
            
            html += """            </tbody>
        </table>
        
        <div class="recommendation">
            <strong>💰 推荐采购价:</strong> ¥{:.2f}
        </div>
""".format(min_price)
        
        # 参数偏离
        deviations = product.get('specs_deviations', [])
        critical = [d for d in deviations if d.get('severity') == 'critical']
        
        if critical:
            html += """
        <div class="warning">
            <strong>⚠️ 参数偏离:</strong>
            <ul style="margin: 10px 0 0 0; padding-left: 20px;">
"""
            for d in critical:
                html += f"                <li><strong>{d['param']}</strong>: {d['description']}</li>\n"
            html += """            </ul>
        </div>
"""
        
        html += """    </div>
"""
        
        return html
    
    def save(self, content: str, path: str, format: str = "markdown"):
        """保存报告"""
        os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✓ 报告已保存: {path}")
        return path
    
    def save_both(self, products: List[Dict], output_path: str, title: str = "询价报告"):
        """同时保存 Markdown 和 HTML"""
        base_path = output_path.replace('.md', '').replace('.html', '')
        
        # 保存 Markdown
        md_content = self.generate(products, title, 'markdown')
        md_path = f"{base_path}.md"
        self.save(md_content, md_path)
        
        # 保存 HTML
        html_content = self.generate(products, title, 'html')
        html_path = f"{base_path}.html"
        self.save(html_path.replace('.html', '') + '.html', html_content)
        
        return md_path, html_path


# 便捷函数
def generate_report(products: List[Dict], title: str = "询价报告", format: str = "markdown") -> str:
    """快速生成报告"""
    gen = ReportGenerator()
    return gen.generate(products, title, format)
