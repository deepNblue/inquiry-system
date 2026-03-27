#!/usr/bin/env python3
"""
系统级询价 v2
- 核心设备：系统内品牌一致
- 通用设备：性价比优先
- 关联系统：紧密关联的系统尽量保持一致
"""

import sys
import csv
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))

from src.brand_strategy import BrandStrategy, DeviceType, SYSTEMS


@dataclass
class ProductResult:
    """产品询价结果"""
    name: str
    brand: str
    model: str
    specs: str
    price: float
    source: str
    device_type: str          # core / general
    recommended_brand: str
    note: str


class SystemInquiry:
    """系统级询价"""
    
    def __init__(self):
        self.strategy = BrandStrategy()
        self.results: List[ProductResult] = []
    
    def inquire(
        self,
        products: List[Dict],
        system_type: str = "安防系统"
    ) -> List[ProductResult]:
        """
        执行系统级询价
        
        策略:
        1. 核心设备 → 系统内品牌一致
        2. 通用设备 → 性价比最优
        3. 关联系统 → 尽量保持一致
        """
        print(f"\n{'='*60}")
        print(f"  系统级询价: {system_type}")
        print(f"{'='*60}\n")
        
        # 分离核心和通用设备
        core_devices = []
        general_devices = []
        
        for p in products:
            device_type = self.strategy.get_device_type(p.get("name", ""))
            if device_type == DeviceType.CORE:
                core_devices.append(p)
            else:
                general_devices.append(p)
        
        results = []
        
        # 1. 先询价核心设备（确定系统品牌）
        if core_devices:
            print(f"🔴 核心设备 ({len(core_devices)} 项)")
            print(f"   策略: 系统内品牌一致\n")
            
            # 选择系统主品牌
            main_brand = self.strategy.select_core_brand(system_type)
            print(f"   主选品牌: {main_brand}\n")
            
            for p in core_devices:
                result = self._inquire_core_device(p, system_type, main_brand)
                results.append(result)
        
        # 2. 询价通用设备（性价比优先）
        if general_devices:
            print(f"\n🟢 通用设备 ({len(general_devices)} 项)")
            print(f"   策略: 性价比优先\n")
            
            for p in general_devices:
                result = self._inquire_general_device(p)
                results.append(result)
        
        self.results = results
        return results
    
    def _inquire_core_device(self, product: Dict, system_type: str, main_brand: str) -> ProductResult:
        """询价核心设备"""
        name = product.get("name", "")
        
        print(f"  📹 {name}")
        print(f"     品牌: {main_brand}")
        
        # 查询主品牌
        from src.history import HistoryMatcher, SearchOptions
        matcher = HistoryMatcher()
        options = SearchOptions(top_k=5)
        
        matches = matcher.search_similar(name, brand=main_brand, options=options)
        
        if matches:
            r = matches[0]
            print(f"     结果: {r.brand} ¥{r.price:,.0f}")
            matcher.close()
            return ProductResult(
                name=name,
                brand=r.brand,
                model=r.model,
                specs=r.specs,
                price=r.price,
                source=r.source,
                device_type="core",
                recommended_brand=main_brand,
                note=f"核心设备，{r.brand}"
            )
        
        # 尝试兼容品牌
        from src.brand_strategy import CORE_COMPATIBLE
        compatible = CORE_COMPATIBLE.get(system_type, [])
        
        for brand in compatible:
            if brand != main_brand:
                matches = matcher.search_similar(name, brand=brand, options=options)
                if matches:
                    r = matches[0]
                    print(f"     备选: {r.brand} ¥{r.price:,.0f}")
                    matcher.close()
                    return ProductResult(
                        name=name,
                        brand=r.brand,
                        model=r.model,
                        specs=r.specs,
                        price=r.price,
                        source=r.source,
                        device_type="core",
                        recommended_brand=main_brand,
                        note=f"核心设备，{r.brand}替代"
                    )
        
        matcher.close()
        print(f"     ⚠️ 无历史数据")
        return ProductResult(
            name=name,
            brand="待定",
            model="",
            specs=product.get("specs", ""),
            price=0,
            source="",
            device_type="core",
            recommended_brand=main_brand,
            note="核心设备，待询价"
        )
    
    def _inquire_general_device(self, product: Dict) -> ProductResult:
        """询价通用设备"""
        name = product.get("name", "")
        
        print(f"  💰 {name}")
        
        from src.history import HistoryMatcher, SearchOptions
        from src.brand_strategy import GENERAL_BRANDS
        
        matcher = HistoryMatcher()
        options = SearchOptions(top_k=10, min_similarity=0.3)
        
        # 获取辅材品牌列表
        general_brands = self.strategy.get_general_brands(name)
        
        all_matches = []
        
        # 查询所有辅材品牌
        for brand in general_brands:
            matches = matcher.search_similar(name, brand=brand, options=options)
            all_matches.extend(matches)
        
        # 按价格排序，选最低
        if all_matches:
            all_matches.sort(key=lambda x: x.price)
            r = all_matches[0]
            print(f"     结果: {r.brand} ¥{r.price:,.0f} [性价比最优]")
            matcher.close()
            return ProductResult(
                name=name,
                brand=r.brand,
                model=r.model,
                specs=r.specs,
                price=r.price,
                source=r.source,
                device_type="general",
                recommended_brand=r.brand,
                note="通用辅材，性价比最优"
            )
        
        matcher.close()
        print(f"     ⚠️ 无历史数据")
        return ProductResult(
            name=name,
            brand="待定",
            model="",
            specs=product.get("specs", ""),
            price=0,
            source="",
            device_type="general",
            recommended_brand="性价比最优",
            note="通用辅材，待询价"
        )
    
    def generate_report(self, output_path: str = "output/system_inquiry.md") -> str:
        """生成询价报告"""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 汇总品牌选择
        core_brands = {}
        for r in self.results:
            if r.device_type == "core" and r.brand != "待定":
                if r.recommended_brand not in core_brands:
                    core_brands[r.recommended_brand] = []
                core_brands[r.recommended_brand].append(r)
        
        lines = [
            f"# 系统询价报告",
            f"",
            f"**询价时间**: 略",
            f"",
            f"---",
            f"",
        ]
        
        # 核心设备
        core = [r for r in self.results if r.device_type == "core"]
        if core:
            # 汇总核心品牌
            brand_summary = {}
            for r in core:
                if r.brand != "待定":
                    brand_summary[r.brand] = brand_summary.get(r.brand, 0) + 1
            
            lines.extend([
                f"## 🔴 核心设备 ({len(core)} 项)",
                f"",
                f"| 设备 | 品牌 | 型号 | 价格 | 说明 |",
                f"|------|------|------|------|------|",
            ])
            for r in core:
                lines.append(f"| {r.name} | {r.brand} | {r.model} | ¥{r.price:,.0f} | {r.note} |")
            
            if brand_summary:
                brands_str = " + ".join([f"{b}×{c}" for b, c in brand_summary.items()])
                lines.extend(["", f"**核心品牌**: {brands_str}"])
            lines.append("")
        
        # 通用设备
        general = [r for r in self.results if r.device_type == "general"]
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
            f"- 通用设备: {len(general)} 项",
            f"- **预估总价: ¥{total:,.0f}**",
            f"",
            f"---",
            f"",
            f"## 💡 询价建议",
            f"",
            f"1. **核心设备** 建议整包采购同一品牌",
            f"2. **通用辅材** 可分项采购，选择性价比高的品牌",
            f"3. 建议联系品牌代理商获取正式报价",
        ])
        
        content = "\n".join(lines)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_path
    
    def close(self):
        """关闭"""
        pass


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
    parser.add_argument("-s", "--system", default="安防系统", help="系统类型")
    parser.add_argument("-o", "--output", default="output/system_inquiry.md", help="输出报告")
    
    args = parser.parse_args()
    
    # 加载产品
    products = load_products_from_csv(args.input)
    print(f"加载 {len(products)} 个产品")
    
    # 执行询价
    inquiry = SystemInquiry()
    results = inquiry.inquire(products, args.system)
    
    # 生成报告
    report_path = inquiry.generate_report(args.output)
    print(f"\n✅ 报告已生成: {report_path}")
    
    # 打印汇总
    total = sum(r.price for r in results if r.price > 0)
    core_count = len([r for r in results if r.device_type == "core"])
    general_count = len([r for r in results if r.device_type == "general"])
    
    print(f"\n📊 汇总:")
    print(f"   核心设备: {core_count} 项")
    print(f"   通用设备: {general_count} 项")
    print(f"   预估总价: ¥{total:,.0f}")


if __name__ == "__main__":
    main()
