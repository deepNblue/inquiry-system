#!/usr/bin/env python3
"""
系统级询价 v3
- 核心设备：系统内品牌一致
- 通用设备：性价比优先
- 关联系统：紧密关联的系统尽量保持一致
- 支持多系统混合询价
"""

import sys
import csv
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent))

from src.brand_strategy import (
    BrandStrategy, DeviceType, SYSTEMS, CORE_COMPATIBLE, 
    GENERAL_BRANDS, detect_system_type
)


@dataclass
class ProductResult:
    """产品询价结果"""
    name: str
    brand: str
    model: str
    specs: str
    price: float
    source: str
    system_type: str        # 所属系统
    device_type: str        # core / general
    recommended_brand: str
    note: str


class SystemInquiry:
    """系统级询价（支持多系统混合）"""
    
    def __init__(self):
        self.strategies: Dict[str, BrandStrategy] = {}  # 每系统独立策略
        self.results: List[ProductResult] = []
    
    def _get_strategy(self, system_type: str) -> BrandStrategy:
        """获取或创建系统策略"""
        if system_type not in self.strategies:
            self.strategies[system_type] = BrandStrategy()
        return self.strategies[system_type]
    
    def inquire(
        self,
        products: List[Dict],
        auto_detect_system: bool = True
    ) -> List[ProductResult]:
        """
        执行系统级询价
        
        Args:
            products: 产品列表
            auto_detect_system: 自动检测产品所属系统
        """
        print(f"\n{'='*60}")
        print(f"  系统级询价 (多系统混合)")
        print(f"{'='*60}\n")
        
        # 1. 按系统分组设备
        system_devices = defaultdict(list)
        general_devices = []
        
        for p in products:
            name = p.get("name", "")
            
            if auto_detect_system:
                detected = detect_system_type(name)
                if detected:
                    system_devices[detected].append(p)
                else:
                    general_devices.append(p)
            else:
                system_devices["通用"].append(p)
        
        # 2. 处理各系统核心设备
        for sys_type, devices in system_devices.items():
            if sys_type == "通用":
                continue
            
            core = [d for d in devices if self._get_strategy(sys_type).get_device_type(d.get("name", "")) == DeviceType.CORE]
            gen = [d for d in devices if self._get_strategy(sys_type).get_device_type(d.get("name", "")) == DeviceType.GENERAL]
            
            if core:
                print(f"\n🔴 {sys_type} - 核心设备 ({len(core)} 项)")
                print(f"   策略: 系统内品牌一致\n")
                for p in core:
                    result = self._inquire_core_device(p, sys_type)
                    self.results.append(result)
            
            if gen:
                general_devices.extend(gen)
        
        # 3. 处理通用设备
        if general_devices:
            print(f"\n🟢 通用辅材 ({len(general_devices)} 项)")
            print(f"   策略: 性价比优先\n")
            for p in general_devices:
                result = self._inquire_general_device(p)
                self.results.append(result)
        
        return self.results
    
    def _inquire_core_device(self, product: Dict, system_type: str) -> ProductResult:
        """询价核心设备"""
        name = product.get("name", "")
        strategy = self._get_strategy(system_type)
        
        # 选择系统主品牌（考虑关联系统）
        main_brand = strategy.select_core_brand(system_type)
        
        print(f"  📹 {name}")
        print(f"     系统: {system_type} | 品牌: {main_brand}")
        
        from src.history import HistoryMatcher, SearchOptions
        matcher = HistoryMatcher()
        options = SearchOptions(top_k=5)
        
        # 查询主品牌
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
                system_type=system_type,
                device_type="core",
                recommended_brand=main_brand,
                note=f"核心设备，系统内一致"
            )
        
        # 尝试兼容品牌
        compatible = CORE_COMPATIBLE.get(system_type, [])
        for brand in compatible:
            if brand != main_brand:
                matches = matcher.search_similar(name, brand=brand, options=options)
                if matches:
                    r = matches[0]
                    print(f"     备选: {r.brand} ¥{r.price:,.0f}")
                    matcher.close()
                    return ProductResult(
                        name=name, brand=r.brand, model=r.model, specs=r.specs,
                        price=r.price, source=r.source, system_type=system_type,
                        device_type="core", recommended_brand=main_brand,
                        note=f"兼容替代"
                    )
        
        matcher.close()
        print(f"     ⚠️ 无历史数据")
        return ProductResult(
            name=name, brand="待定", model="", specs=product.get("specs", ""),
            price=0, source="", system_type=system_type, device_type="core",
            recommended_brand=main_brand, note="待询价"
        )
    
    def _inquire_general_device(self, product: Dict) -> ProductResult:
        """询价通用设备"""
        name = product.get("name", "")
        
        print(f"  💰 {name}")
        
        from src.history import HistoryMatcher, SearchOptions
        matcher = HistoryMatcher()
        options = SearchOptions(top_k=10, min_similarity=0.3)
        
        # 获取辅材品牌
        general_brands = list(GENERAL_BRANDS.values())[0] if GENERAL_BRANDS else []
        
        all_matches = []
        for brand in general_brands:
            matches = matcher.search_similar(name, brand=brand, options=options)
            all_matches.extend(matches)
        
        if all_matches:
            all_matches.sort(key=lambda x: x.price)
            r = all_matches[0]
            print(f"     结果: {r.brand} ¥{r.price:,.0f} [性价比最优]")
            matcher.close()
            return ProductResult(
                name=name, brand=r.brand, model=r.model, specs=r.specs,
                price=r.price, source=r.source, system_type="通用",
                device_type="general", recommended_brand=r.brand,
                note="性价比最优"
            )
        
        matcher.close()
        print(f"     ⚠️ 无历史数据")
        return ProductResult(
            name=name, brand="待定", model="", specs=product.get("specs", ""),
            price=0, source="", system_type="通用", device_type="general",
            recommended_brand="性价比最优", note="待询价"
        )
    
    def generate_report(self, output_path: str = "output/system_inquiry.md") -> str:
        """生成询价报告"""
        import os
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # 按系统分组
        systems = defaultdict(list)
        for r in self.results:
            systems[r.system_type].append(r)
        
        lines = [
            "# 系统询价报告",
            "",
            f"**询价时间**: 略",
            "",
            "---",
            "",
        ]
        
        # 各系统汇总
        for sys_type in ["安防系统", "网络系统", "服务器系统", "机房系统", "通用"]:
            if sys_type not in systems:
                continue
            
            devices = systems[sys_type]
            core = [d for d in devices if d.device_type == "core"]
            general = [d for d in devices if d.device_type == "general"]
            
            icon = "🔴" if sys_type != "通用" else "🟢"
            lines.append(f"## {icon} {sys_type}")
            
            # 核心设备
            if core:
                lines.extend([
                    f"### 核心设备 ({len(core)} 项)",
                    "| 设备 | 品牌 | 型号 | 价格 | 说明 |",
                    "|------|------|------|------|------|",
                ])
                for r in core:
                    lines.append(f"| {r.name} | {r.brand} | {r.model} | ¥{r.price:,.0f} | {r.note} |")
                lines.append("")
            
            # 通用设备
            if general:
                lines.extend([
                    f"### 通用辅材 ({len(general)} 项)",
                    "| 设备 | 品牌 | 型号 | 价格 | 说明 |",
                    "|------|------|------|------|------|",
                ])
                for r in general:
                    lines.append(f"| {r.name} | {r.brand} | {r.model} | ¥{r.price:,.0f} | {r.note} |")
                lines.append("")
        
        # 汇总
        total = sum(r.price for r in self.results if r.price > 0)
        core_total = sum(r.price for r in self.results if r.price > 0 and r.device_type == "core")
        general_total = sum(r.price for r in self.results if r.price > 0 and r.device_type == "general")
        
        lines.extend([
            "---",
            "",
            "## 📊 汇总",
            "",
            f"- **核心设备**: ¥{core_total:,.0f}",
            f"- **通用辅材**: ¥{general_total:,.0f}",
            f"- **总计**: ¥{total:,.0f}",
            "",
            "---",
            "",
            "## 💡 询价建议",
            "",
            "1. **核心设备** 建议整包采购同一品牌",
            "2. **通用辅材** 可分项采购，选择性价比高的品牌",
            "3. 建议联系品牌代理商获取正式报价",
        ])
        
        content = "\n".join(lines)
        
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        
        return output_path


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
    parser.add_argument("-s", "--system", default="", help="指定系统类型(默认自动检测)")
    parser.add_argument("-o", "--output", default="output/system_inquiry.md", help="输出报告")
    
    args = parser.parse_args()
    
    # 加载产品
    products = load_products_from_csv(args.input)
    print(f"加载 {len(products)} 个产品")
    
    # 执行询价
    inquiry = SystemInquiry()
    auto_detect = not args.system
    results = inquiry.inquire(products, auto_detect_system=auto_detect)
    
    # 生成报告
    report_path = inquiry.generate_report(args.output)
    print(f"\n✅ 报告已生成: {report_path}")
    
    # 打印汇总
    total = sum(r.price for r in results if r.price > 0)
    core_count = len([r for r in results if r.device_type == "core"])
    general_count = len([r for r in results if r.device_type == "general"])
    
    print(f"\n📊 汇总:")
    print(f"   核心设备: {core_count} 项")
    print(f"   通用辅材: {general_count} 项")
    print(f"   预估总价: ¥{total:,.0f}")


if __name__ == "__main__":
    main()
