#!/usr/bin/env python3
"""
Web UI - Gradio界面
"""

import os
import sys
import csv
from datetime import datetime

import gradio as gr

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.history import HistoryMatcher
from src.report_generator import ReportGenerator
from src.charts import PriceChart


def load_products(file_path: str) -> list:
    """加载产品"""
    products = []
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            products = list(reader)
    return products


def search_product(keyword: str, brand: str = "") -> list:
    """搜索产品"""
    matcher = HistoryMatcher()
    results = matcher.search_similar(keyword, brand=brand, top_k=20)
    matcher.close()
    
    return [
        {
            "产品": r.product_name,
            "品牌": r.brand,
            "型号": r.model,
            "价格": f"¥{r.price:,.0f}",
            "来源": r.source,
        }
        for r in results
    ]


def generate_report_json(products_json: str) -> str:
    """生成报告"""
    import json
    
    try:
        products = json.loads(products_json)
        
        gen = ReportGenerator()
        os.makedirs("output", exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        
        # Markdown
        md = gen.generate(products, "询价报告", "markdown")
        md_path = f"output/report_{timestamp}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(md)
        
        return f"✅ 报告已生成:\n{md_path}"
    except Exception as e:
        return f"❌ 生成失败: {str(e)}"


def get_statistics() -> dict:
    """获取统计信息"""
    matcher = HistoryMatcher()
    conn = matcher.conn
    
    cursor = conn.execute("SELECT COUNT(*) FROM price_history")
    total_records = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(DISTINCT product_name) FROM price_history")
    total_products = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(DISTINCT brand) FROM price_history WHERE brand != ''")
    total_brands = cursor.fetchone()[0]
    
    matcher.close()
    
    return {
        "历史记录": total_records,
        "产品种类": total_products,
        "品牌数量": total_brands,
    }


def create_ui():
    """创建UI"""
    
    with gr.Blocks(title="自动询价系统", theme=gr.themes.Soft()) as demo:
        gr.Markdown("# 🔍 自动询价系统")
        gr.Markdown("三渠道综合询价：网页 / 厂家 / 历史")
        
        with gr.Tabs():
            # 询价
            with gr.TabItem("📋 产品询价"):
                with gr.Row():
                    with gr.Column():
                        product_name = gr.Textbox(label="产品名称", placeholder="输入产品名称...")
                        brand = gr.Textbox(label="品牌", placeholder="可选")
                        limit = gr.Slider(1, 50, value=10, step=1, label="结果数量")
                        search_btn = gr.Button("🔍 查询", variant="primary")
                    
                    with gr.Column():
                        results_table = gr.DataFrame(
                            headers=["产品", "品牌", "型号", "价格", "来源"],
                            label="查询结果"
                        )
                
                search_btn.click(
                    search_product,
                    inputs=[product_name, brand],
                    outputs=results_table
                )
            
            # 历史
            with gr.TabItem("📜 历史价格"):
                gr.Markdown("### 查看历史价格趋势")
                
                hist_product = gr.Textbox(label="产品名称")
                hist_brand = gr.Textbox(label="品牌", placeholder="可选")
                hist_btn = gr.Button("📊 查看历史")
                hist_output = gr.JSON(label="历史数据")
                
                hist_btn.click(
                    lambda p, b: {"results": search_product(p, b)},
                    inputs=[hist_product, hist_brand],
                    outputs=hist_output
                )
            
            # 报告
            with gr.TabItem("📊 报告生成"):
                gr.Markdown("### 生成询价报告")
                
                report_input = gr.Textbox(
                    label="产品JSON",
                    placeholder='[{"product_name":"产品A","brand":"品牌A","min_price":100}]',
                    lines=5
                )
                report_btn = gr.Button("📄 生成报告", variant="primary")
                report_output = gr.Textbox(label="结果")
                
                report_btn.click(
                    generate_report_json,
                    inputs=[report_input],
                    outputs=[report_output]
                )
            
            # 统计
            with gr.TabItem("📈 统计信息"):
                gr.Markdown("### 系统统计")
                
                stats = get_statistics()
                
                with gr.Row():
                    gr.Number(label="历史记录", value=stats["历史记录"])
                    gr.Number(label="产品种类", value=stats["产品种类"])
                    gr.Number(label="品牌数量", value=stats["品牌数量"])
                
                refresh_btn = gr.Button("🔄 刷新")
                refresh_btn.click(
                    get_statistics,
                    outputs=[]
                )
            
            # 关于
            with gr.TabItem("ℹ️ 关于"):
                gr.Markdown("""
                ## 自动询价系统 v0.2.0
                
                ### 功能
                - 🔍 三渠道询价 (网页/厂家/历史)
                - 📧 邮件闭环 (发送+收取)
                - 📊 智能报告 (Markdown/HTML)
                - 📈 可视化 (图表+仪表板)
                
                ### 技术栈
                - Python 3.12
                - Gradio UI
                - SQLite
                - Sentence Transformers
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
