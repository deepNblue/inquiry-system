#!/usr/bin/env python3
"""
投标询价工具
整合系统询价 + 投标报价清单 + 偏离表
"""

import sys
import csv
from pathlib import Path
from typing import List, Dict, Optional
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent))

from src.bid_quote import (
    BidQuoteGenerator, BidQuoteConfig, QuoteItem, 
    DeviationType, compare_specs
)
from system_inquiry import SystemInquiry, load_products_from_csv


@dataclass
class BidInquiryResult:
    """投标询价结果"""
    items: List[QuoteItem]           # 报价清单
    quote_summary: Dict              # 报价汇总
    tax_rate: float                 # 税率
    total_no_tax: float            # 总价（不含税）
    total_with_tax: float           # 总价（含税）


class BidInquiry:
    """投标询价"""
    
    def __init__(self, config: BidQuoteConfig = None):
        self.config = config or BidQuoteConfig()
        self.system_inquiry = SystemInquiry()
        self.quote_gen = BidQuoteGenerator(self.config)
    
    def inquire(
        self,
        products: List[Dict],
        specs_requirements: List[Dict] = None
    ) -> BidInquiryResult:
        """
        执行投标询价
        
        Args:
            products: 产品列表 [{name, brand, model, specs, quantity}]
            specs_requirements: 招标文件技术要求 [{name, spec_required}]
        """
        print(f"\n{'='*60}")
        print(f"  投标询价")
        print(f"  项目: {self.config.project_name}")
        print(f"{'='*60}\n")
        
        # 1. 执行系统询价
        print("📋 第1步: 系统询价...")
        results = self.system_inquiry.inquire(products)
        print(f"   询价完成: {len(results)} 项\n")
        
        # 2. 生成报价清单
        print("📋 第2步: 生成报价清单...")
        for i, r in enumerate(results, 1):
            # 添加报价项
            item = QuoteItem(
                seq=i,
                name=r.name,
                brand=r.brand,
                model=r.model or r.specs[:50],
                unit_price=r.price,
                quantity=1,
                tax_rate=self.config.tax_rate,
                warranty=self.config.warranty_default,
                delivery=self.config.delivery_default,
                deviation=r.note,
            )
            self.quote_gen.add_item(item)
        
        # 3. 计算汇总
        print("📋 第3步: 计算汇总...")
        calc = self.quote_gen.calculate()
        
        print(f"""
📊 报价汇总:
   设备项数: {calc['item_count']} 项
   含税总额: ¥{calc['total_with_tax']:,.2f}
   不含税总额: ¥{calc['subtotal_no_tax']:,.2f}
   税额: ¥{calc['tax_amount']:,.2f}
   税率: {calc['tax_rate']*100:.0f}%
""")
        
        # 4. 生成偏离表
        if specs_requirements:
            print("📋 第4步: 生成偏离表...")
            # 对比规格
            for req in specs_requirements:
                for item in self.quote_gen.items:
                    if req.get("name") == item.name:
                        deviation_type, note = compare_specs(
                            req.get("spec_required", ""),
                            item.model
                        )
                        item.deviation = deviation_type.value
                        item.deviation_note = note
        
        return BidInquiryResult(
            items=self.quote_gen.items,
            quote_summary=calc,
            tax_rate=calc["tax_rate"],
            total_no_tax=calc["subtotal_no_tax"],
            total_with_tax=calc["total_with_tax"],
        )
    
    def generate_report(
        self,
        output_dir: str = "output",
        specs_requirements: List[Dict] = None
    ) -> Dict[str, str]:
        """
        生成投标文件
        
        Returns:
            生成的报告路径
        """
        import os
        os.makedirs(output_dir, exist_ok=True)
        
        outputs = {}
        
        # 1. 报价清单 (Markdown)
        quote_md = self.quote_gen.generate_quote_table()
        quote_path = f"{output_dir}/bid_quote.md"
        with open(quote_path, "w", encoding="utf-8") as f:
            f.write(quote_md)
        outputs["quote_md"] = quote_path
        print(f"✅ 报价清单: {quote_path}")
        
        # 2. 偏离表 (Markdown)
        if specs_requirements:
            dev_path = f"{output_dir}/bid_deviation.md"
            dev_md = self.quote_gen.generate_deviation_table(specs_requirements)
            with open(dev_path, "w", encoding="utf-8") as f:
                f.write(dev_md)
            outputs["deviation_md"] = dev_path
            print(f"✅ 偏离表: {dev_path}")
        
        # 3. 完整投标文件
        full_path = f"{output_dir}/bid_full.md"
        full_md = self.quote_gen.generate_full_document(specs_requirements)
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(full_md)
        outputs["full_md"] = full_path
        print(f"✅ 完整投标文件: {full_path}")
        
        # 4. Excel导出
        try:
            excel_path = self.quote_gen.export_excel(f"{output_dir}/bid_quote.xlsx")
            if excel_path:
                outputs["excel"] = excel_path
                print(f"✅ Excel报价: {excel_path}")
        except Exception as e:
            print(f"⚠️ Excel导出失败: {e}")
        
        return outputs
    
    def close(self):
        """关闭"""
        pass


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="投标询价")
    parser.add_argument("-i", "--input", required=True, help="产品CSV文件")
    parser.add_argument("-o", "--output", default="output", help="输出目录")
    parser.add_argument("-p", "--project", default="投标项目", help="项目名称")
    parser.add_argument("-t", "--tax", type=float, default=0.13, help="税率")
    parser.add_argument("-w", "--warranty", default="3年", help="质保期")
    parser.add_argument("-d", "--delivery", default="30天", help="交货期")
    
    args = parser.parse_args()
    
    # 配置
    config = BidQuoteConfig(
        project_name=args.project,
        tax_rate=args.tax,
        warranty_default=args.warranty,
        delivery_default=args.delivery,
    )
    
    # 加载产品
    products = load_products_from_csv(args.input)
    print(f"加载 {len(products)} 个产品")
    
    # 执行询价
    inquiry = BidInquiry(config)
    result = inquiry.inquire(products)
    
    # 生成报告
    outputs = inquiry.generate_report(args.output)
    
    print(f"\n{'='*60}")
    print("  投标询价完成!")
    print(f"{'='*60}")
    print(f"\n💰 投标报价（含税）: ¥{result.total_with_tax:,.2f}")
    print(f"   投标报价（不含税）: ¥{result.total_no_tax:,.2f}")


if __name__ == "__main__":
    main()
