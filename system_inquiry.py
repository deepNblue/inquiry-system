#!/usr/bin/env python3
"""
系统级询价
支持核心设备品牌一致、辅材性价比优先
"""

import sys
import csv
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))

from src.brand_strategy import BrandStrategy, DevicePriority, get_brand_strategy
from src.history import HistoryMatcher, SearchOptions
from src.report_generator import ReportGenerator


@dataclass
class ProductResult:
    """产品询价结果"""
    name: str
    brand: str
    model: str
    specs: str
    price: float
    source: str
    priority: str
    recommended_brand: str
    note: str


class SystemInquiry:
    """系统级询价"""
    
    def __init__(self, system_type: str = "安防系统"):
        self.strategy = BrandStrategy(system_type)
        self.matcher = HistoryMatcher()
        self.results: List[ProductResult] = []
    
    def inquire(
        self,
        products: List[Dict],
        system_type: str = "安防系统"
    ) -> List[ProductResult]:
        """
        执行系统级询价
        
        Args:
            products: 产品列表 [{name, brand, model, specs, quantity}]
            system_type: 系统类型
        
        Returns:
            询价结果列表
        """
        # 更新策略
        self.strategy = BrandStrategy(system_type)
        
        print(f"\n{'='*60}")
        print(f"  系统级询价: {system_type}")
        print(f"  主选品牌: {self.strategy.config.preferred_brand}")
        print(f"{'='*60}\n")
        
        # 分类设备
        classified = self.strategy.classify_devices(products)
        
        results = []
        
        # 1. 询价核心设备（品牌一致）
        if classified["core"]:
            print(f"🔴 核心设备询价 ({len(classified['core'])} 项)")
            print(f"   策略: 品牌一致优先 ({self.strategy.config.preferred_brand})\n")
            for p in classified["core"]:
                result = self._inquire_core_device(p)
                results.append(result)
        
        # 2. 询价重要设备（品牌参考）
        if classified["important"]:
            print(f"\n🟡 重要设备询价 ({len(classified['important'])} 项)")
            print(f"   策略: 品牌参考\n")
            for p in classified["important"]:
                result = self._inquire_important_device(p)
                results.append(result)
        
        # 3. 询价通用设备（性价比优先）
        if classified["general"]:
            print(f"\n🟢 通用设备询价 ({len(classified['general'])} 项)")
            print(f"   策略: 性价比优先\n")
            for p in classified["general"]:
                result = self._inquire_general_device(p)
                results.append(result)
        
        self.results = results
        return results
    
    def _inquire_core_device(self, product: Dict) -> ProductResult:
        """询价核心设备"""
        name = product.get("name", "")
        preferred = self.strategy.config.preferred_brand
        
        print(f"  📹 {name}")
        print(f"     首选: {preferred}")
        
        # 查询主选品牌
        options = SearchOptions(top_k=3)
        matches = self.matcher.search_similar(
            name,
            brand=preferred,
            specs=product.get("specs", ""),
            options=options
        )
        
        if matches:
            r = matches[0]
            print(f"     结果: {r.brand} ¥{r.price:,.0f}")
            return ProductResult(
                name=name,
                brand=r.brand,
                model=r.model,
                specs=r.specs,
                price=r.price,
                source=r.source,
                priority="core",
                recommended_brand=preferred,
                note=f"核心设备，品牌一致"
            )
        
        # 尝试兼容品牌
        for brand in self.strategy.config.compatible_brands:
            if brand != preferred:
                matches = self.matcher.search_similar(name, brand=brand, options=options)
                if matches:
                    r = matches[0]
                    print(f"     备选: {r.brand} ¥{r.price:,.0f}")
                    return ProductResult(
                        name=name,
                        brand=r.brand,
                        model=r.model,
                        specs=r.specs,
                        price=r.price,
                        source=r.source,
                        priority="core",
                        recommended_brand=preferred,
                        note=f"核心设备，{r.brand}替代"
                    )
        
        print(f"     ⚠️ 无历史数据")
        return ProductResult(
            name=name,
            brand="待定",
            model="",
            specs=product.get("specs", ""),
            price=0,
            source="",
            priority="core",
            recommended_brand=preferred,
            note="核心设备，待询价"
        )
    
    def _inquire_important_device(self, product: Dict) -> ProductResult:
        """询价重要设备"""
        name = product.get("name", "")
        compatible = self.strategy.config.compatible_brands
        
        print(f"  ⚡ {name}")
        
        # 尝试兼容品牌
        options = SearchOptions(top_k=3)
        for brand in compatible:
            matches = self.matcher.search_similar(name, brand=brand, options=options)
            if matches:
                r = matches[0]
                note = "同品牌" if brand == self.strategy.config.preferred_brand else "兼容品牌"
                print(f"     {brand} ¥{r.price:,.0f} [{note}]")
                return ProductResult(
                    name=name,
                    brand=r.brand,
                    model=r.model,
                    specs=r.specs,
                    price=r.price,
                    source=r.source,
                    priority="important",
                    recommended_brand=brand,
                    note=f"重要设备，{note}"
                )
        
        print(f"     ⚠️ 无历史数据")
        return ProductResult(
            name=name,
            brand="待定",
            model="",
            specs=product.get("specs", ""),
            price=0,
            source="",
            priority="important",
            recommended_brand=compatible[0],
            note="重要设备，待询价"
        )
    
    def _inquire_general_device(self, product: Dict) -> ProductResult:
        """询价通用设备（性价比优先）"""
        name = product.get("name", "")
        
        print(f"  💰 {name}")
        
        # 获取辅材兼容品牌
        preferred = self.strategy.get_preferred_brands(name)
        
        options = SearchOptions(top_k=5, min_similarity=0.3)
        all_matches = []
        
        # 查询所有兼容品牌
        for brand in preferred:
            matches = self.matcher.search_similar(name, brand=brand, options=options)
            all_matches.extend(matches)
        
        # 按价格排序，选最低
        if all_matches:
            all_matches.sort(key=lambda x: x.price)
            r = all_matches[0]
            print(f"     {r.brand} ¥{r.price:,.0f} [性价比最优]")
            return ProductResult(
                name=name,
                brand=r.brand,
                model=r.model,
                specs=r.specs,
                price=r.price,
                source=r.source,
                priority="general",
                recommended_brand=r.brand,
                note="辅材，性价比最优"
            )
        
        print(f"     ⚠️ 无历史数据")
        return ProductResult(
            name=name,
            brand="待定",
            model="",
            specs=product.get("specs", ""),
            price=0,
            source="",
            priority="general",
            recommended_brand="性价比最优",
            note="辅材，待询价"
        )
    
    def generate_report(self, output_path: str = "output/system_inquiry.md") -> str:
        """生成询价报告"""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        lines = [
            f"# 系统询价报告",
            f"",
            f"**系统类型**: {self.strategy.system_type}",
            f"**主选品牌**: {self.strategy.config.preferred_brand}",
            f"**询价时间**: 略",
            f"",
            f"---",
            f"",
        ]
        
        # 按优先级分组
        core = [r for r in self.results if r.priority == "core"]
        important = [r for r in self.results if r.priority == "important"]
        general = [r for r in self.results if r.priority == "general"]
        
        # 核心设备
        if core:
            lines.extend([
                f"## 🔴 核心设备 ({len(core)} 项)",
                f"",
                f"| 设备 | 品牌 | 型号 | 价格 | 推荐品牌 | 说明 |",
                f"|------|------|------|------|----------|------|",
            ])
            for r in core:
                lines.append(f"| {r.name} | {r.brand} | {r.model} | ¥{r.price:,.0f} | {r.recommended_brand} | {r.note} |")
            lines.append("")
        
        # 重要设备
        if important:
            lines.extend([
                f"## 🟡 重要设备 ({len(important)} 项)",
                f"",
                f"| 设备 | 品牌 | 型号 | 价格 | 说明 |",
                f"|------|------|------|------|------|",
            ])
            for r in important:
                lines.append(f"| {r.name} | {r.brand} | {r.model} | ¥{r.price:,.0f} | {r.note} |")
            lines.append("")
        
        # 通用设备
        if general:
            lines.extend([
                f"## 🟢 通用设备 ({len(general)} 项)",
                f"",
                f"| 设备 | 品牌 | 型号 | 价格 | 说明 |",
                f"|------|------|------|------|------|",
            ])
            for r in general:
                lines.append(f"| {r.name} | {r.brand} | {r.model} | ¥{r.price:,.0f} | {r.note} |")
            lines.append("")
        
        # 汇总
        total = sum(r.price for r in self.results if r.price > 0)
        lines.extend([
            f"---",
            f"",
            f"## 📊 汇总",
            f"",
            f"- 核心设备: {len(core)} 项",
            f"- 重要设备: {len(important)} 项",
            f"- 通用设备: {len(general)} 项",
            f"- **预估总价: ¥{total:,.0f}**",
            f"",
            f"---",
            f"",
            f"## 💡 询价建议",
            f"",
            f"1. **核心设备** ({self.strategy.config.preferred_brand}) 建议整包采购",
            f"2. **辅材** 可分项采购，选择性价比高的品牌",
            f"3. 建议联系 {self.strategy.config.preferred_brand} 代理商获取正式报价",
        ])
        
        content = "\n".join(lines)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_path
    
    def close(self):
        """关闭连接"""
        self.matcher.close()


def load_products_from_csv(file_path: str) -> List[Dict]:
    """从CSV加载产品"""
    products = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                "name": row.get("name", row.get("产品", "")),
                "brand": row.get("brand", row.get("品牌", "")),
                "model": row.get("model", row.get("型号", "")),
                "specs": row.get("specs", row.get("规格", "")),
                "quantity": int(row.get("quantity", row.get("数量", 1)))
            })
    return products


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="系统级询价")
    parser.add_argument("-i", "--input", required=True, help="产品CSV文件")
    parser.add_argument("-s", "--system", default="安防系统", choices=["安防系统", "网络系统", "服务器系统", "机房系统"],
                        help="系统类型")
    parser.add_argument("-o", "--output", default="output/system_inquiry.md", help="输出报告")
    
    args = parser.parse_args()
    
    # 加载产品
    products = load_products_from_csv(args.input)
    print(f"加载 {len(products)} 个产品")
    
    # 执行询价
    inquiry = SystemInquiry(args.system)
    results = inquiry.inquire(products, args.system)
    
    # 生成报告
    report_path = inquiry.generate_report(args.output)
    print(f"\n✅ 报告已生成: {report_path}")
    
    # 打印汇总
    total = sum(r.price for r in results if r.price > 0)
    print(f"\n📊 预估总价: ¥{total:,.0f}")
    
    inquiry.close()


if __name__ == "__main__":
    main()
