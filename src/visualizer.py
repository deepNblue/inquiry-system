"""
价格趋势可视化模块
生成价格走势图、对比图等
"""

import os
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import json

try:
    import matplotlib
    matplotlib.use('Agg')  # 无头模式
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False


class PriceVisualizer:
    """
    价格可视化器
    生成趋势图表和对比图
    """
    
    def __init__(self, output_dir: str = "output/charts"):
        self.output_dir = output_dir
        Path(output_dir).mkdir(parents=True, exist_ok=True)
        
        if HAS_MATPLOTLIB:
            # 设置中文字体
            plt.rcParams['font.sans-serif'] = ['SimHei', 'DejaVu Sans', 'Arial Unicode MS']
            plt.rcParams['axes.unicode_minus'] = False
    
    def plot_price_trend(
        self,
        dates: List[str],
        prices: List[float],
        product_name: str,
        source: str = "",
        output_file: str = None
    ) -> str:
        """
        绘制价格趋势图
        
        Args:
            dates: 日期列表
            prices: 价格列表
            product_name: 产品名称
            source: 数据来源
            output_file: 输出文件路径
        
        Returns:
            图表文件路径
        """
        if not HAS_MATPLOTLIB:
            return ""
        
        if not dates or not prices:
            return ""
        
        # 解析日期
        x_dates = [datetime.strptime(d[:10], "%Y-%m-%d") for d in dates]
        
        # 创建图表
        fig, ax = plt.subplots(figsize=(12, 6))
        
        ax.plot(x_dates, prices, marker='o', linewidth=2, markersize=6)
        
        # 填充区域
        ax.fill_between(x_dates, prices, alpha=0.3)
        
        # 设置标题和标签
        title = f"{product_name} 价格趋势"
        if source:
            title += f" ({source})"
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格 (¥)', fontsize=12)
        
        # 日期格式
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.xaxis.set_major_locator(mdates.AutoDateLocator())
        
        # 网格
        ax.grid(True, linestyle='--', alpha=0.7)
        
        # 标注最低价
        min_idx = prices.index(min(prices))
        ax.annotate(
            f'最低: ¥{prices[min_idx]:,.0f}',
            xy=(x_dates[min_idx], prices[min_idx]),
            xytext=(10, 10),
            textcoords='offset points',
            fontsize=10,
            color='green',
            fontweight='bold'
        )
        
        plt.tight_layout()
        
        # 保存
        if not output_file:
            safe_name = product_name.replace("/", "_").replace("\\", "_")[:30]
            output_file = f"{self.output_dir}/{safe_name}_trend.png"
        
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def plot_multi_source_comparison(
        self,
        dates: List[str],
        sources_prices: Dict[str, List[float]],
        product_name: str,
        output_file: str = None
    ) -> str:
        """
        多来源价格对比图
        
        Args:
            dates: 日期列表
            sources_prices: {来源: [价格列表]}
            product_name: 产品名称
        
        Returns:
            图表文件路径
        """
        if not HAS_MATPLOTLIB:
            return ""
        
        x_dates = [datetime.strptime(d[:10], "%Y-%m-%d") for d in dates]
        
        fig, ax = plt.subplots(figsize=(14, 7))
        
        colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd', '#8c564b']
        
        for i, (source, prices) in enumerate(sources_prices.items()):
            color = colors[i % len(colors)]
            ax.plot(x_dates, prices, marker='o', label=source, linewidth=2, color=color)
        
        ax.set_title(f"{product_name} 多来源价格对比", fontsize=14, fontweight='bold')
        ax.set_xlabel('日期', fontsize=12)
        ax.set_ylabel('价格 (¥)', fontsize=12)
        
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
        ax.legend(loc='best')
        ax.grid(True, linestyle='--', alpha=0.7)
        
        plt.tight_layout()
        
        if not output_file:
            safe_name = product_name.replace("/", "_")[:30]
            output_file = f"{self.output_dir}/{safe_name}_compare.png"
        
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def plot_product_comparison(
        self,
        products: List[Dict],
        output_file: str = None
    ) -> str:
        """
        产品价格对比柱状图
        
        Args:
            products: [{name, min_price, max_price, recommended_price}, ...]
        
        Returns:
            图表文件路径
        """
        if not HAS_MATPLOTLIB:
            return ""
        
        if not products:
            return ""
        
        names = [p.get("name", "")[:15] for p in products]
        min_prices = [p.get("min_price", 0) for p in products]
        max_prices = [p.get("max_price", 0) for p in products]
        
        x = range(len(names))
        width = 0.35
        
        fig, ax = plt.subplots(figsize=(max(10, len(names) * 1.5), 6))
        
        ax.bar([i - width/2 for i in x], min_prices, width, label='最低价', color='#2ecc71')
        ax.bar([i + width/2 for i in x], max_prices, width, label='最高价', color='#e74c3c')
        
        ax.set_xlabel('产品', fontsize=12)
        ax.set_ylabel('价格 (¥)', fontsize=12)
        ax.set_title('产品价格对比', fontsize=14, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(names, rotation=45, ha='right')
        ax.legend()
        ax.grid(True, linestyle='--', alpha=0.7, axis='y')
        
        # 添加价格标签
        for i, (mn, mx) in enumerate(zip(min_prices, max_prices)):
            if mn > 0:
                ax.text(i - width/2, mn + 50, f'¥{mn:,.0f}', ha='center', va='bottom', fontsize=8)
            if mx > 0:
                ax.text(i + width/2, mx + 50, f'¥{mx:,.0f}', ha='center', va='bottom', fontsize=8)
        
        plt.tight_layout()
        
        if not output_file:
            output_file = f"{self.output_dir}/product_comparison.png"
        
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        return output_file
    
    def generate_dashboard(
        self,
        products_trends: Dict[str, Dict],
        output_file: str = None
    ) -> str:
        """
        生成综合仪表板
        
        Args:
            products_trends: {产品名: {dates: [], prices: [], sources: {}}}
        
        Returns:
            仪表板文件路径
        """
        if not HAS_MATPLOTLIB:
            return ""
        
        n = len(products_trends)
        cols = min(2, n)
        rows = (n + cols - 1) // cols
        
        fig, axes = plt.subplots(rows, cols, figsize=(12, 4 * rows))
        if n == 1:
            axes = [axes]
        else:
            axes = axes.flatten() if hasattr(axes, 'flatten') else [axes]
        
        colors = ['#3498db', '#e74c3c', '#2ecc71', '#f39c12', '#9b59b6']
        
        for i, (name, data) in enumerate(products_trends.items()):
            ax = axes[i]
            
            dates = data.get("dates", [])
            prices = data.get("prices", [])
            sources = data.get("sources", {})
            
            if dates and prices:
                x_dates = [datetime.strptime(d[:10], "%Y-%m-%d") for d in dates]
                ax.plot(x_dates, prices, marker='o', color=colors[i % len(colors)])
                ax.fill_between(x_dates, prices, alpha=0.3)
                ax.set_title(name[:25], fontsize=11, fontweight='bold')
                ax.set_ylabel('价格')
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
                ax.grid(True, linestyle='--', alpha=0.5)
        
        # 隐藏空白子图
        for j in range(i + 1, len(axes)):
            axes[j].set_visible(False)
        
        plt.tight_layout()
        
        if not output_file:
            output_file = f"{self.output_dir}/dashboard.png"
        
        plt.savefig(output_file, dpi=150, bbox_inches='tight')
        plt.close()
        
        return output_file


# 便捷函数
def create_visualizer(output_dir: str = "output/charts") -> PriceVisualizer:
    """创建可视化器"""
    return PriceVisualizer(output_dir)


def plot_trend(dates: List[str], prices: List[float], name: str) -> str:
    """快速绘制趋势图"""
    viz = PriceVisualizer()
    return viz.plot_price_trend(dates, prices, name)
