#!/usr/bin/env python3
"""
自动询价系统 - Gradio Web 界面
"""

import asyncio
import os
import sys
import csv
import json
from pathlib import Path
from typing import List

import gradio as gr
import yaml

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scraper import WebScraper
from src.history import HistoryMatcher
from src.aggregator import PriceAggregator


class InquiryUI:
    def __init__(self):
        self.config = self._load_config()
        self.web_scraper = WebScraper(self.config.get("web_scraper", {}))
        self.history = HistoryMatcher(self.config.get("history", {}).get("db_path", "data/history.db"))
        self.aggregator = PriceAggregator(self.config)
    
    def _load_config(self):
        if os.path.exists("config.yaml"):
            with open("config.yaml", "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    async def inquiry(self, products_text: str, methods: List[str]):
        """执行询价"""
        # 解析产品
        lines = products_text.strip().split("\n")
        products = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 简单解析：支持 "名称,品牌,型号" 或纯名称
            parts = [p.strip() for p in line.split(",")]
            products.append({
                "name": parts[0],
                "brand": parts[1] if len(parts) > 1 else "",
                "model": parts[2] if len(parts) > 2 else "",
            })
        
        if not products:
            return "请输入产品信息", None
        
        results = {}
        
        # 网页询价
        if "web" in methods:
            web_results = await self.web_scraper.batch_search(products)
            results["web"] = web_results
        
        # 历史询价
        if "history" in methods:
            history_results = []
            for p in products:
                matches = self.history.search_similar(
                    product_name=p.get("name", ""),
                    brand=p.get("brand", ""),
                    model=p.get("model", ""),
                    top_k=3
                )
                history_results.extend(matches)
            results["history"] = history_results
        
        # 聚合
        aggregated = self.aggregator.aggregate(
            web_results=results.get("web"),
            history_results=results.get("history")
        )
        
        # 生成报告
        report_lines = [
            "# 询价报告\n",
            f"产品数量: {len(aggregated)}\n",
            "---\n",
        ]
        
        for r in aggregated:
            report_lines.append(f"## {r.product_name}")
            if r.brand:
                report_lines.append(f"**品牌**: {r.brand}")
            if r.model:
                report_lines.append(f"**型号**: {r.model}")
            report_lines.append("")
            
            if r.prices:
                report_lines.append("| 来源 | 价格 |")
                report_lines.append("|------|------|")
                for p in r.prices:
                    price = f"¥{p['price']:,.2f}" if p.get("price") else "待报价"
                    report_lines.append(f"| {p.get('source', '未知')} | {price} |")
                report_lines.append("")
                
                report_lines.append(f"- 最低价: ¥{r.min_price:,.2f}")
                report_lines.append(f"- 最高价: ¥{r.max_price:,.2f}")
                report_lines.append(f"- 平均价: ¥{r.avg_price:,.2f}")
                if r.recommended_source:
                    report_lines.append(f"**推荐**: {r.recommended_source} ¥{r.recommended_price:,.2f}")
            else:
                report_lines.append("*暂无报价*")
            
            report_lines.append("\n---\n")
        
        report = "\n".join(report_lines)
        
        # 生成表格数据
        table_data = []
        for r in aggregated:
            if r.prices:
                for p in r.prices:
                    table_data.append([
                        r.product_name,
                        r.brand,
                        p.get("source", ""),
                        f"¥{p['price']:,.2f}" if p.get("price") else "待报价",
                    ])
        
        return report, table_data if table_data else None
    
    def search_history(self, product_name: str, brand: str = ""):
        """查询历史"""
        results = self.history.search_similar(
            product_name=product_name,
            brand=brand,
            top_k=10
        )
        
        if not results:
            return None, "未找到历史记录"
        
        table_data = [
            [r.product_name, r.brand, r.model, f"¥{r.price:,.2f}", r.source, r.timestamp[:10]]
            for r in results
        ]
        
        headers = ["产品", "品牌", "型号", "价格", "来源", "日期"]
        return headers, table_data


def create_ui():
    ui = InquiryUI()
    
    with gr.Blocks(title="自动询价系统") as app:
        gr.Markdown("# 🔍 自动询价系统")
        gr.Markdown("三渠道综合询价：网页询价 + 历史价格 + 厂家询价")
        
        with gr.Tab("询价"):
            with gr.Row():
                with gr.Column(scale=2):
                    products_input = gr.Textbox(
                        label="产品列表",
                        placeholder="每行一个产品，格式：名称,品牌,型号\n例如：\niPhone 15 Pro,Apple,256GB\nMacBook Pro 14,Apple,M3 Pro",
                        lines=10
                    )
                    methods = gr.CheckboxGroup(
                        choices=["web", "history", "manufacturer"],
                        value=["web", "history"],
                        label="询价方式"
                    )
                    inquiry_btn = gr.Button("开始询价", variant="primary")
                
                with gr.Column(scale=3):
                    report_output = gr.Markdown(label="询价报告")
                    table_output = gr.DataFrame(label="价格明细", headers=["产品", "品牌", "来源", "价格"])
            
            inquiry_btn.click(
                ui.inquiry,
                inputs=[products_input, methods],
                outputs=[report_output, table_output]
            )
        
        with gr.Tab("历史价格"):
            with gr.Row():
                with gr.Column():
                    history_product = gr.Textbox(label="产品名称")
                    history_brand = gr.Textbox(label="品牌（可选）")
                    history_btn = gr.Button("查询")
                with gr.Column():
                    history_headers = gr.DataFrame(headers=["产品", "品牌", "型号", "价格", "来源", "日期"], label="历史记录")
            
            history_btn.click(
                ui.search_history,
                inputs=[history_product, history_brand],
                outputs=[history_headers, None]
            )
        
        with gr.Tab("使用说明"):
            gr.Markdown("""
            ## 使用说明
            
            ### 询价
            1. 在「产品列表」中输入产品，每行一个
            2. 选择询价方式（可多选）
            3. 点击「开始询价」
            
            ### 产品格式
            - 纯名称：`iPhone 15`
            - 带品牌：`iPhone 15,Apple`
            - 完整格式：`iPhone 15 Pro,Apple,256GB,A2892`
            
            ### 数据导入
            支持 CSV 格式导入历史价格数据
            
            ### API 调用
            ```bash
            # 启动 API 服务
            python api.py
            
            # 调用示例
            curl -X POST http://localhost:8000/inquiry \
              -H "Content-Type: application/json" \
              -d '{"products":[{"name":"iPhone 15"}]}'
            ```
            """)
    
    return app


if __name__ == "__main__":
    app = create_ui()
    app.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )
