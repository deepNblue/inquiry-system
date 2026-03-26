#!/usr/bin/env python3
"""
参数偏离对比
对比需求规格与实际产品规格
"""

import os
import csv
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from src.history import HistoryMatcher


@dataclass
class SpecItem:
    """规格项"""
    key: str
    required: str  # 需求值
    actual: str = ""  # 实际值
    status: str = "pending"  # match/mismatch/warning/pending
    deviation: str = ""  # 偏离说明


@dataclass
class SpecComparison:
    """规格对比结果"""
    product_name: str
    brand: str
    model: str
    items: List[SpecItem]
    match_rate: float = 0.0
    critical_issues: int = 0
    warnings: int = 0


class SpecComparator:
    """
    参数偏离检测器
    """
    
    # 数值参数匹配规则
    NUMERIC_KEYS = [
        '分辨率', '像素', '帧率', '焦距', '距离', '容量', '功率', '功率',
        '转速', '缓存', '端口', '口', '路', '盘位', '带宽', '电流', '电压',
        '承重', '风量', '制冷量', 'kW', 'kVA', 'GHz', 'GB', 'TB', 'MB',
    ]
    
    # 必须匹配的参数
    CRITICAL_KEYS = [
        '分辨率', '容量', '功率', '制冷量', 'kW', 'kVA',
    ]
    
    def __init__(self):
        pass
    
    def parse_specs(self, specs_str: str) -> Dict[str, str]:
        """解析规格字符串为字典"""
        specs = {}
        
        if not specs_str:
            return specs
        
        # 分割参数项
        items = specs_str.split(';')
        
        for item in items:
            item = item.strip()
            if not item:
                continue
            
            # 尝试分离 key: value
            if ':' in item:
                parts = item.split(':', 1)
                key = parts[0].strip()
                value = parts[1].strip()
            else:
                # 没有冒号，尝试提取数字+单位
                key = item
                value = ""
            
            if key:
                specs[key] = value
        
        return specs
    
    def compare_values(self, required: str, actual: str) -> Tuple[bool, str]:
        """
        比较两个值
        
        Returns:
            (是否匹配, 偏离说明)
        """
        if not actual:
            return False, "无实际参数"
        
        if not required:
            return True, ""
        
        # 数值比较
        req_num = self._extract_number(required)
        act_num = self._extract_number(actual)
        
        if req_num and act_num:
            return self._compare_numbers(req_num, required, act_num, actual)
        
        # 字符串包含匹配
        if required in actual or actual in required:
            return True, ""
        
        # 关键词匹配
        if self._fuzzy_match(required, actual):
            return True, ""
        
        return False, f"需求「{required}」，实际「{actual}」"
    
    def _extract_number(self, text: str) -> Optional[float]:
        """提取数值"""
        patterns = [
            r'(\d+\.?\d*)\s*(kW|kVA|kVA/|kW/|GHz|TB|GB|MB|kb|KB|Mbps|Gbps|m³/h|kg/h|°|mm|cm|m|K|℃)',
            r'(\d+\.?\d*)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                num_str = match.group(1)
                try:
                    return float(num_str)
                except:
                    pass
        
        return None
    
    def _compare_numbers(self, req_num: float, required: str, act_num: float, actual: str) -> Tuple[bool, str]:
        """比较数值"""
        # 同一单位直接比较
        if req_num == act_num:
            return True, ""
        
        # 允许 ±10% 误差
        tolerance = 0.1
        if abs(req_num - act_num) / req_num <= tolerance:
            return True, ""
        
        # 检查单位是否一致
        req_unit = self._get_unit(required)
        act_unit = self._get_unit(actual)
        
        # 单位不同但数值相近
        if req_unit != act_unit:
            converted = self._convert_unit(act_num, act_unit, req_unit)
            if converted and abs(req_num - converted) / req_num <= tolerance:
                return True, ""
        
        # 确定偏离方向
        if act_num > req_num:
            return False, f"实际值({act_num})高于需求({req_num})"
        else:
            return False, f"实际值({act_num})低于需求({req_num})"
    
    def _get_unit(self, text: str) -> str:
        """获取单位"""
        units = ['kW', 'kVA', 'GHz', 'GB', 'TB', 'MB', 'm³/h', 'kg/h', 'mm', 'cm', 'm']
        for unit in units:
            if unit in text:
                return unit
        return ''
    
    def _convert_unit(self, value: float, from_unit: str, to_unit: str) -> Optional[float]:
        """单位转换"""
        conversions = {
            ('GB', 'MB'): 1024,
            ('TB', 'GB'): 1024,
            ('kW', 'W'): 1000,
            ('W', 'kW'): 0.001,
        }
        
        key = (from_unit, to_unit)
        if key in conversions:
            return value * conversions[key]
        
        return None
    
    def _fuzzy_match(self, required: str, actual: str) -> bool:
        """模糊匹配"""
        required_lower = required.lower()
        actual_lower = actual.lower()
        
        # 完全包含
        if required_lower in actual_lower or actual_lower in required_lower:
            return True
        
        # 关键词匹配
        keywords = ['支持', '含', '包括', '配有', '具有']
        for kw in keywords:
            if kw in required_lower and kw in actual_lower:
                return True
        
        return False
    
    def compare_product(
        self,
        product_name: str,
        required_specs: str,
        actual_specs: str,
        brand: str = "",
        model: str = ""
    ) -> SpecComparison:
        """对比单个产品"""
        # 解析规格
        req_dict = self.parse_specs(required_specs)
        act_dict = self.parse_specs(actual_specs)
        
        items = []
        critical = 0
        warnings = 0
        matched = 0
        
        # 对比每个需求参数
        for key, req_value in req_dict.items():
            item = SpecItem(
                key=key,
                required=req_value
            )
            
            # 查找实际值
            actual_value = ""
            for act_key, act_value in act_dict.items():
                if key in act_key or act_key in key:
                    actual_value = act_value
                    break
            
            item.actual = actual_value
            
            if actual_value:
                is_match, deviation = self.compare_values(req_value, actual_value)
                
                if is_match:
                    item.status = "match"
                elif key in self.CRITICAL_KEYS:
                    item.status = "mismatch"
                    item.deviation = deviation
                    critical += 1
                else:
                    item.status = "warning"
                    item.deviation = deviation
                    warnings += 1
            else:
                item.status = "pending"
                item.deviation = "无实际参数"
                warnings += 1
            
            items.append(item)
        
        # 计算匹配率
        total = len(items)
        match_rate = (matched / total * 100) if total > 0 else 0
        
        return SpecComparison(
            product_name=product_name,
            brand=brand,
            model=model,
            items=items,
            match_rate=match_rate,
            critical_issues=critical,
            warnings=warnings
        )
    
    def generate_comparison_report(
        self,
        products: List[Dict],
        actual_specs: Dict[str, str]
    ) -> List[SpecComparison]:
        """生成对比报告"""
        results = []
        
        for p in products:
            required_specs = p.get('specs', '')
            
            # 查找实际规格
            actual = actual_specs.get(p.get('product_name', ''), '')
            
            if not actual:
                # 尝试从历史数据获取
                matcher = HistoryMatcher()
                matches = matcher.search_similar(p.get('product_name', ''), top_k=1)
                if matches:
                    actual = matches[0].specs
                matcher.close()
            
            comparison = self.compare_product(
                product_name=p.get('product_name', ''),
                required_specs=required_specs,
                actual_specs=actual,
                brand=p.get('brand', ''),
                model=p.get('model', '')
            )
            
            results.append(comparison)
        
        return results
    
    def format_markdown(self, comparisons: List[SpecComparison]) -> str:
        """格式化为 Markdown"""
        lines = [
            "# 参数偏离对比报告",
            "",
            f"**生成时间**: {__import__('datetime').datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "---",
            ""
        ]
        
        for i, c in enumerate(comparisons, 1):
            lines.extend([
                f"## {i}. {c.product_name}",
                f"**品牌**: {c.brand}",
                f"**型号**: {c.model}",
                "",
            ])
            
            # 状态概览
            if c.critical_issues > 0:
                status_icon = "🔴"
                status_text = f"有 {c.critical_issues} 个关键偏离"
            elif c.warnings > 0:
                status_icon = "🟡"
                status_text = f"有 {c.warnings} 个偏离项"
            else:
                status_icon = "🟢"
                status_text = "参数匹配良好"
            
            lines.append(f"{status_icon} **{status_text}**")
            lines.append("")
            
            # 参数对比表
            lines.extend([
                "| 参数 | 需求规格 | 实际规格 | 状态 |",
                "|------|----------|----------|------|",
            ])
            
            for item in c.items:
                if item.status == "match":
                    icon = "✅"
                elif item.status == "mismatch":
                    icon = "❌"
                elif item.status == "warning":
                    icon = "⚠️"
                else:
                    icon = "❓"
                
                lines.append(f"| {item.key} | {item.required} | {item.actual or '-'} | {icon} {item.deviation or ''} |")
            
            lines.extend(["", "---", ""])
        
        return "\n".join(lines)


def main():
    """测试参数对比"""
    print("=" * 50)
    print("  参数偏离对比测试")
    print("=" * 50)
    
    comparator = SpecComparator()
    
    # 测试用例
    test_cases = [
        {
            "name": "网络摄像机",
            "required": "分辨率:1920*1080@30fps;焦距:4mm;红外距离:30m;防护等级:IP67",
            "actual": "分辨率:1920*1080@30fps;焦距:6mm;红外距离:50m;防护等级:IP67",
        },
        {
            "name": "服务器",
            "required": "CPU:2*Intel Xeon Gold 4210;内存:256GB DDR4;硬盘:4TB SSD+8TB SATA",
            "actual": "CPU:2*Xeon Gold 4210;内存:256GB DDR4;硬盘:4TB SSD+8TB SATA;RAID卡",
        },
    ]
    
    for tc in test_cases:
        result = comparator.compare_product(
            product_name=tc["name"],
            required_specs=tc["required"],
            actual_specs=tc["actual"]
        )
        
        print(f"\n{result.product_name}:")
        for item in result.items:
            status_icon = {"match": "✅", "mismatch": "❌", "warning": "⚠️", "pending": "❓"}.get(item.status, "?")
            print(f"  {status_icon} {item.key}: {item.required} vs {item.actual}")


if __name__ == "__main__":
    main()
