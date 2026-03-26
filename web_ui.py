#!/usr/bin/env python3
"""
Web UI - Gradio界面 (简化版)
"""

import os
import sys
import csv

import gradio as gr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.history import HistoryMatcher


def search_product(keyword: str, brand: str = "") -> str:
    """搜索产品"""
    if not keyword:
        return "请输入产品名称"
    
    matcher = HistoryMatcher()
    results = matcher.search_similar(keyword, brand=brand, top_k=20)
    matcher.close()
    
    if not results:
        return f"未找到「{keyword}」相关产品"
    
    lines = [f"## 找到 {len(results)} 条结果\n"]
    lines.append("| 产品 | 品牌 | 价格 | 来源 |")
    lines.append("|------|------|------|------|")
    
    for r in results:
        lines.append(f"| {r.product_name} | {r.brand} | ¥{r.price:,.0f} | {r.source} |")
    
    return "\n".join(lines)


def get_statistics() -> str:
    """获取统计信息"""
    matcher = HistoryMatcher()
    conn = matcher.conn
    
    cursor = conn.execute("SELECT COUNT(*) FROM price_history")
    total_records = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(DISTINCT product_name) FROM price_history")
    total_products = cursor.fetchone()[0]
    
    matcher.close()
    
    return f"""
## 系统统计

| 指标 | 数值 |
|------|------|
| 历史记录 | {total_records} |
| 产品种类 | {total_products} |
"""


def create_ui():
    """创建UI"""
    
    with gr.Blocks(title="自动询价系统") as demo:
        gr.Markdown("# 🔍 自动询价系统")
        gr.Markdown("三渠道综合询价：网页 / 厂家 / 历史")
        
        with gr.Row():
            with gr.Column():
                product_name = gr.Textbox(label="产品名称", placeholder="输入产品名称...")
                brand = gr.Textbox(label="品牌", placeholder="可选")
                search_btn = gr.Button("🔍 查询", variant="primary")
            
            with gr.Column():
                results = gr.Markdown("查询结果将显示在这里")
        
        search_btn.click(
            search_product,
            inputs=[product_name, brand],
            outputs=results
        )
        
        gr.Markdown("---")
        gr.Markdown("## 📈 统计信息")
        stats_btn = gr.Button("🔄 刷新统计")
        stats_output = gr.Markdown()
        
        stats_btn.click(
            get_statistics,
            outputs=stats_output
        )
        
        gr.Markdown("---")
        gr.Markdown("""
        ## ℹ️ 关于
        
        **自动询价系统 v0.2.0**
        
        ### 功能
        - 🔍 三渠道询价 (网页/厂家/历史)
        - 📧 邮件闭环 (发送+收取)
        - 📊 智能报告 (Markdown/HTML)
        - 📈 可视化 (图表+仪表板)
        
        ### 启动方式
        - Web UI: 当前页面
        - CLI: `python3 interactive_cli.py`
        - API: `python3 api.py`
        """)
    
    return demo


def main():
    """启动UI"""
    print("启动 Web UI...")
    print("访问: http://localhost:7860")
    
    demo = create_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False
    )


if __name__ == "__main__":
    main()
