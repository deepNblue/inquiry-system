#!/usr/bin/env python3
"""
自动询价系统 - 主程序
三渠道综合询价：网页 + 厂家 + 历史
"""

import os
import sys
import asyncio
import argparse
import json
import csv
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import yaml

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scraper import WebScraper
from src.manufacturer import ManufacturerInquiry
from src.history import HistoryMatcher
from src.aggregator import PriceAggregator
from src.scheduler import InquiryScheduler


class InquirySystem:
    """自动询价系统"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config = self._load_config(config_path)
        
        # 初始化各模块
        self.web_scraper = WebScraper(self.config.get("web_scraper", {}))
        self.manufacturer = ManufacturerInquiry(self.config.get("manufacturer", {}))
        self.history = HistoryMatcher(self.config.get("history", {}).get("db_path", "data/history.db"))
        self.aggregator = PriceAggregator(self.config)
        self.scheduler = InquiryScheduler(self.config.get("scheduler", {}))
    
    def _load_config(self, path: str) -> Dict:
        """加载配置"""
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}
    
    async def inquiry(
        self,
        products: List[Dict],
        methods: List[str] = None,
        save_history: bool = True
    ) -> List:
        """
        执行询价
        
        Args:
            products: 产品列表
            methods: 询价方式 ["web", "manufacturer", "history"]
            save_history: 是否保存到历史记录
        
        Returns:
            聚合后的询价结果
        """
        methods = methods or ["web", "history"]
        
        print(f"\n{'='*50}")
        print(f"开始询价 - {len(products)} 个产品")
        print(f"询价方式: {', '.join(methods)}")
        print(f"{'='*50}\n")
        
        results = {}
        
        # 1. 网页询价
        if "web" in methods:
            print("[1/3] 网页询价中...")
            web_results = await self.web_scraper.batch_search(products)
            results["web"] = web_results
            print(f"   完成: {len(web_results)} 条结果")
            
            # 保存到历史
            if save_history:
                self._save_to_history(web_results, "web")
        
        # 2. 厂家询价
        if "manufacturer" in methods:
            print("[2/3] 厂家询价中...")
            # TODO: 实现厂家询价逻辑
            results["manufacturer"] = []
            print("   完成: 0 条结果 (待实现)")
        
        # 3. 历史询价
        if "history" in methods:
            print("[3/3] 历史询价中...")
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
            print(f"   完成: {len(history_results)} 条结果")
        
        # 聚合结果
        print("\n聚合结果...")
        aggregated = self.aggregator.aggregate(
            web_results=results.get("web"),
            history_results=results.get("history")
        )
        
        return aggregated
    
    def _save_to_history(self, results, source_type: str):
        """保存到历史记录"""
        for r in results:
            if hasattr(r, "price") and r.price > 0:
                self.history.add_price_record(
                    product_name=getattr(r, "product_name", ""),
                    price=r.price,
                    brand=getattr(r, "brand", ""),
                    model=getattr(r, "model", ""),
                    source=getattr(r, "source", ""),
                    source_type=source_type,
                    currency=getattr(r, "currency", "CNY"),
                    raw_data=getattr(r, "raw_data", None)
                )
    
    def load_products(self, path: str) -> List[Dict]:
        """加载产品列表"""
        products = []
        
        if path.endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                products = json.load(f)
        elif path.endswith(".csv"):
            with open(path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                products = list(reader)
        elif path.endswith(".txt"):
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        products.append({"name": line})
        else:
            raise ValueError(f"Unsupported file format: {path}")
        
        return products
    
    def save_results(self, results: List, path: str, format: str = "markdown"):
        """保存结果"""
        report = self.aggregator.generate_report(results, format)
        
        os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(report)
        
        print(f"\n结果已保存: {path}")


async def main():
    parser = argparse.ArgumentParser(description="自动询价系统")
    parser.add_argument("-i", "--input", required=True, help="产品列表文件 (CSV/JSON/TXT)")
    parser.add_argument("-o", "--output", default="output/report.md", help="输出文件")
    parser.add_argument("-c", "--config", default="config.yaml", help="配置文件")
    parser.add_argument("-m", "--methods", nargs="+", default=["web", "history"],
                        choices=["web", "manufacturer", "history"],
                        help="询价方式")
    parser.add_argument("--format", default="markdown", choices=["markdown", "json", "csv"],
                        help="输出格式")
    parser.add_argument("--notify", action="store_true", help="完成后发送飞书通知")
    parser.add_argument("--visualize", action="store_true", help="生成可视化图表")
    parser.add_argument("--ai-summary", action="store_true", help="生成AI摘要")
    parser.add_argument("--export", nargs="+", default=[], choices=["markdown", "json", "csv", "html", "excel"],
                        help="多格式导出")
    parser.add_argument("--trend", action="store_true", help="生成趋势分析报告")
    parser.add_argument("--predict", type=int, default=0, help="预测未来N天价格")
    parser.add_argument("--spec-compare", action="store_true", help="参数偏离对比")
    parser.add_argument("--dashboard", action="store_true", help="生成HTML仪表板")
    parser.add_argument("--feishu-config", action="store_true", help="配置飞书通知")
    
    args = parser.parse_args()
    
    # 飞书配置模式
    if args.feishu_config:
        from configure_feishu import configure_feishu, show_current_config
        show_current_config()
        configure_feishu()
        return
    
    # 仪表板模式
    if args.dashboard:
        from src.visualize import generate_dashboard
        from spec_compare import SpecComparator
        
        # 加载产品
        system = InquirySystem(args.config)
        products = system.load_products(args.input)
        
        # 添加历史价格
        for p in products:
            matches = system.history.search_similar(p.get('name', ''), brand=p.get('brand', ''), top_k=3)
            if matches:
                p['min_price'] = min(m.price for m in matches)
                p['overall_confidence'] = int(sum(m.similarity for m in matches) / len(matches) * 100)
        
        # 生成仪表板
        generate_dashboard(products)
        print("✓ 仪表板已生成: output/dashboard.html")
        return
    
    # 创建系统
    system = InquirySystem(args.config)
    
    # 加载产品
    print(f"加载产品: {args.input}")
    products = system.load_products(args.input)
    print(f"加载完成: {len(products)} 个产品\n")
    
    # 执行询价
    results = await system.inquiry(products, args.methods)
    
    # 保存结果
    if args.format == "json":
        output_path = args.output.replace(".md", ".json")
    elif args.format == "csv":
        output_path = args.output.replace(".md", ".csv")
    else:
        output_path = args.output
    
    system.save_results(results, output_path, args.format)
    
    # 飞书通知
    if args.notify:
        from src.feishu_notifier import FeishuNotifier
        feishu = FeishuNotifier(webhook_url=system.config.get("feishu_webhook"))
        feishu.send_inquiry_results(results, "询价报告")
        print("✓ 已发送飞书通知")
    
    # 可视化图表
    if args.visualize:
        try:
            from src.visualizer import PriceVisualizer
            viz = PriceVisualizer()
            
            # 产品对比图
            chart_file = viz.plot_product_comparison([
                {"name": r.product_name, "min_price": r.min_price, "max_price": r.max_price}
                for r in results
            ])
            if chart_file:
                print(f"✓ 图表已生成: {chart_file}")
        except Exception as e:
            print(f"⚠ 可视化失败: {e}")
    
    # AI 摘要
    if args.ai_summary:
        try:
            from src.ai_insights import AIReportGenerator
            import asyncio
            
            async def gen_summary():
                generator = AIReportGenerator()
                return await generator.generate_report_summary(results)
            
            summary = asyncio.run(gen_summary())
            print(f"\n{'='*50}")
            print("AI 摘要:")
            print(summary)
            print(f"{'='*50}")
        except Exception as e:
            print(f"⚠ AI摘要失败: {e}")
    
    # 趋势分析报告
    if args.trend:
        try:
            from src.price_predictor import PricePredictor
            from src.trend_report import TrendReporter
            
            predictor = PricePredictor()
            
            # 批量分析
            analyses = []
            for r in results:
                analysis = predictor.analyze_trend(
                    r.product_name,
                    brand=r.brand,
                    days=30
                )
                analyses.append(analysis)
            
            predictor.close()
            
            # 生成报告
            reporter = TrendReporter()
            report = reporter.generate_report(analyses)
            
            # 保存报告
            trend_file = args.output.replace(".md", "_trend.md")
            with open(trend_file, "w", encoding="utf-8") as f:
                f.write(report)
            
            print(f"\n✓ 趋势分析报告已生成: {trend_file}")
            
            # 打印摘要
            print(f"\n{'='*50}")
            print("趋势分析摘要:")
            print(f"{'='*50}")
            
            for a in analyses[:5]:  # 只显示前5个
                rec_emoji = {'buy': '✅', 'wait': '⏳', 'hold': '🤔'}.get(a.recommendation, '⚪')
                print(f"  {rec_emoji} {a.product_name}: {a.recommendation.upper()} ({a.trend_score}分)")
            
        except Exception as e:
            print(f"⚠ 趋势分析失败: {e}")
    
    # 价格预测
    if args.predict > 0:
        try:
            from src.price_predictor import PricePredictor
            
            predictor = PricePredictor()
            
            print(f"\n{'='*50}")
            print(f"价格预测 (未来 {args.predict} 天):")
            print(f"{'='*50}")
            
            for r in results[:5]:  # 只预测前5个
                pred = predictor.predict_price(r.product_name, r.brand, days_ahead=args.predict)
                if pred.get('prediction') != 'unknown':
                    curr = pred.get('current_price', 0)
                    future = pred.get('predicted_price', 0)
                    direction = pred.get('prediction', '')
                    emoji = {'rising': '📈', 'falling': '📉', 'stable': '➡️'}.get(direction, '❓')
                    print(f"  {emoji} {pred['product_name']}: ¥{curr:,.0f} → ¥{future:,.0f} ({direction})")
            
            predictor.close()
            
        except Exception as e:
            print(f"⚠ 价格预测失败: {e}")
    
    # 参数偏离对比
    if args.spec_compare:
        try:
            from spec_compare import SpecComparator
            
            comparator = SpecComparator()
            
            print(f"\n{'='*50}")
            print("参数偏离对比:")
            print(f"{'='*50}")
            
            for r in results:
                if hasattr(r, 'specs') and r.specs:
                    # 实际规格
                    matches = system.history.search_similar(r.product_name, top_k=1)
                    actual = matches[0].specs if matches else ''
                    
                    comparison = comparator.compare_product(
                        r.product_name,
                        r.specs,
                        actual
                    )
                    
                    if comparison.warnings + comparison.critical_issues > 0:
                        print(f"\n  {r.product_name}:")
                        for item in comparison.items:
                            if item.status != 'match':
                                icon = '⚠️' if item.status == 'warning' else '❓'
                                print(f"    {icon} {item.key}: {item.required} vs {item.actual or '无'}")
            
            print()
            
        except Exception as e:
            print(f"⚠ 参数对比失败: {e}")
    
    # 多格式导出
    if args.export:
        try:
            from src.exporter import DataExporter
            exporter = DataExporter()
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"inquiry_{timestamp}"
            
            for fmt in args.export:
                out_file = exporter.export(results, base_name, fmt)
                print(f"✓ 已导出 [{fmt}]: {out_file}")
        except Exception as e:
            print(f"⚠ 导出失败: {e}")
    
    # 打印摘要
    print(f"\n{'='*50}")
    print(f"询价完成！")
    print(f"产品数: {len(results)}")
    for r in results:
        if r.min_price > 0:
            print(f"  - {r.product_name}: ¥{r.min_price:,.2f} ~ ¥{r.max_price:,.2f}")
        else:
            print(f"  - {r.product_name}: 待报价")
    print(f"{'='*50}")


if __name__ == "__main__":
    asyncio.run(main())
