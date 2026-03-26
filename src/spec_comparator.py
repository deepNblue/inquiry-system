"""
参数偏离检测模块
对比技术参数与需求，识别偏离情况
"""

import re
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum


class MatchLevel(Enum):
    """匹配等级"""
    EXACT = "exact"          # 完全匹配
    BETTER = "better"        # 优于要求
    ACCEPTABLE = "acceptable"  # 可接受（有偏差但满足基本需求）
    INFERIOR = "inferior"    # 劣于要求
    MISMATCH = "mismatch"    # 不匹配
    UNKNOWN = "unknown"      # 未知


@dataclass
class SpecComparison:
    """参数对比结果"""
    param_name: str           # 参数名
    required_value: str       # 要求值
    actual_value: str        # 实际值
    match_level: MatchLevel   # 匹配等级
    deviation_desc: str = ""  # 偏离描述
    severity: str = "info"   # 严重程度: critical/warning/info
    
    def to_dict(self) -> Dict:
        return {
            "param": self.param_name,
            "required": self.required_value,
            "actual": self.actual_value,
            "level": self.match_level.value,
            "description": self.deviation_desc,
            "severity": self.severity
        }


@dataclass
class ProductComparison:
    """产品对比结果"""
    product_name: str
    required_specs: Dict[str, str]  # 需求规格
    actual_specs: Dict[str, str]    # 实际规格
    comparisons: List[SpecComparison] = field(default_factory=list)
    
    # 汇总
    total_params: int = 0
    matched_params: int = 0
    better_params: int = 0
    inferior_params: int = 0
    mismatch_params: int = 0
    
    overall_score: float = 0   # 整体匹配度 0-100
    is_qualified: bool = True  # 是否满足要求
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "product": self.product_name,
            "qualified": self.is_qualified,
            "score": self.overall_score,
            "summary": {
                "total": self.total_params,
                "matched": self.matched_params,
                "better": self.better_params,
                "inferior": self.inferior_params,
                "mismatch": self.mismatch_params,
            },
            "details": [c.to_dict() for c in self.comparisons],
            "warnings": self.warnings
        }


class SpecComparator:
    """
    技术参数对比器
    检测参数偏离情况
    """
    
    # 关键参数（必须满足）
    CRITICAL_PARAMS = [
        "分辨率", "像素", "焦距", "光圈",
        "电压", "功率", "电流",
        "容量", "内存", "存储",
        "接口", "协议",
    ]
    
    # 可优于的参数
    BETTER_PARAMS = [
        "像素", "分辨率", "光圈", "光变", "帧率",
        "内存", "存储", "带宽",
        "防护等级", "工作温度",
    ]
    
    # 数值参数（可直接比较）
    NUMERIC_PARAMS = [
        "分辨率", "像素", "焦距", "光圈", "光变",
        "电压", "功率", "电流", "容量",
        "内存", "存储", "带宽", "帧率",
        "防护等级", "工作温度范围",
    ]
    
    def __init__(self):
        pass
    
    def compare(
        self,
        required_specs: Dict[str, str],
        actual_specs: Dict[str, str],
        product_name: str = ""
    ) -> ProductComparison:
        """
        对比需求规格与实际规格
        
        Args:
            required_specs: 需求规格 {参数名: 值}
            actual_specs: 实际规格 {参数名: 值}
            product_name: 产品名称
        
        Returns:
            对比结果
        """
        comparison = ProductComparison(
            product_name=product_name,
            required_specs=required_specs,
            actual_specs=actual_specs
        )
        
        for param, req_value in required_specs.items():
            # 在实际规格中查找对应参数
            actual_value = self._find_param(param, actual_specs)
            
            if actual_value:
                # 有对应值，进行对比
                result = self._compare_param(param, req_value, actual_value)
            else:
                # 未找到对应参数
                result = SpecComparison(
                    param_name=param,
                    required_value=req_value,
                    actual_value="未提供",
                    match_level=MatchLevel.UNKNOWN,
                    deviation_desc=f"缺少参数: {param}",
                    severity="warning"
                )
                comparison.warnings.append(f"缺少参数: {param}")
            
            comparison.comparisons.append(result)
        
        # 统计
        comparison.total_params = len(comparison.comparisons)
        
        for c in comparison.comparisons:
            if c.match_level == MatchLevel.EXACT or c.match_level == MatchLevel.BETTER:
                comparison.matched_params += 1
            if c.match_level == MatchLevel.BETTER:
                comparison.better_params += 1
            elif c.match_level == MatchLevel.INFERIOR:
                comparison.inferior_params += 1
            elif c.match_level == MatchLevel.MISMATCH or c.match_level == MatchLevel.UNKNOWN:
                comparison.mismatch_params += 1
        
        # 计算整体分数
        comparison.overall_score = self._calculate_score(comparison)
        
        # 判断是否满足要求
        comparison.is_qualified = self._is_qualified(comparison)
        
        return comparison
    
    def _find_param(self, param: str, specs: Dict[str, str]) -> Optional[str]:
        """在规格中查找参数（模糊匹配）"""
        param_lower = param.lower()
        
        # 精确匹配
        if param in specs:
            return specs[param]
        
        # 模糊匹配
        for key, value in specs.items():
            key_lower = key.lower()
            if param_lower in key_lower or key_lower in param_lower:
                return value
        
        return None
    
    def _compare_param(self, param: str, required: str, actual: str) -> SpecComparison:
        """对比单个参数"""
        # 判断是否为数值参数
        is_numeric = any(np in param for np in self.NUMERIC_PARAMS)
        
        if is_numeric:
            return self._compare_numeric(param, required, actual)
        else:
            return self._compare_text(param, required, actual)
    
    def _compare_numeric(self, param: str, required: str, actual: str) -> SpecComparison:
        """对比数值参数"""
        req_nums = self._extract_numbers(required)
        act_nums = self._extract_numbers(actual)
        
        if not req_nums or not act_nums:
            return self._compare_text(param, required, actual)
        
        # 取第一个数值进行比较
        req_val = req_nums[0]
        act_val = act_nums[0]
        
        # 判断参数类型（越大越好 vs 越小越好）
        is_larger_better = self._is_larger_better(param)
        
        if req_val == act_val:
            level = MatchLevel.EXACT
            desc = f"{param} 匹配: {actual}"
            severity = "info"
        elif is_larger_better:
            if act_val >= req_val:
                # 实际值 >= 要求值 = 满足（可能优于）
                if param in self.BETTER_PARAMS and act_val > req_val * 1.1:
                    level = MatchLevel.BETTER
                    desc = f"{param} 优于要求: {actual} > {required}"
                    severity = "info"
                else:
                    level = MatchLevel.EXACT
                    desc = f"{param} 满足要求: {actual}"
                    severity = "info"
            else:
                level = MatchLevel.INFERIOR
                ratio = (req_val - act_val) / req_val
                desc = f"{param} 低于要求: {actual} < {required} (低{ratio:.1%})"
                severity = "critical" if param in self.CRITICAL_PARAMS else "warning"
        else:
            if act_val <= req_val:
                level = MatchLevel.EXACT
                desc = f"{param} 满足要求: {actual}"
                severity = "info"
            else:
                level = MatchLevel.INFERIOR
                ratio = (act_val - req_val) / req_val
                desc = f"{param} 超过要求: {actual} > {required} (高{ratio:.1%})"
                severity = "warning"
        
        return SpecComparison(
            param_name=param,
            required_value=required,
            actual_value=actual,
            match_level=level,
            deviation_desc=desc,
            severity=severity
        )
    
    def _compare_text(self, param: str, required: str, actual: str) -> SpecComparison:
        """对比文本参数"""
        req_lower = required.lower()
        act_lower = actual.lower()
        
        # 包含匹配
        if req_lower == act_lower:
            level = MatchLevel.EXACT
            severity = "info"
        elif req_lower in act_lower or act_lower in req_lower:
            level = MatchLevel.EXACT
            severity = "info"
        elif self._text_similarity(req_lower, act_lower) > 0.6:
            level = MatchLevel.ACCEPTABLE
            severity = "info"
        else:
            level = MatchLevel.MISMATCH
            severity = "warning"
        
        return SpecComparison(
            param_name=param,
            required_value=required,
            actual_value=actual,
            match_level=level,
            deviation_desc=f"{param}: 要求'{required}', 实际'{actual}'",
            severity=severity
        )
    
    def _extract_numbers(self, text: str) -> List[float]:
        """提取文本中的所有数值"""
        pattern = r'[\d.]+'
        matches = re.findall(pattern, text)
        numbers = []
        for m in matches:
            try:
                numbers.append(float(m))
            except ValueError:
                pass
        return numbers
    
    def _is_larger_better(self, param: str) -> bool:
        """判断参数是否越大越好"""
        larger_better = [
            "分辨率", "像素", "焦距", "光圈",
            "光变", "帧率", "内存", "存储",
            "容量", "带宽", "防护等级",
            "功率", "电流",
        ]
        return any(p in param for p in larger_better)
    
    def _text_similarity(self, s1: str, s2: str) -> float:
        """文本相似度"""
        if not s1 or not s2:
            return 0
        
        common = sum(1 for c in s1 if c in s2)
        return common / max(len(s1), len(s2))
    
    def _calculate_score(self, comparison: ProductComparison) -> float:
        """计算整体匹配分数"""
        if comparison.total_params == 0:
            return 100
        
        # 权重配置
        weights = {
            MatchLevel.EXACT: 1.0,
            MatchLevel.BETTER: 1.0,
            MatchLevel.ACCEPTABLE: 0.7,
            MatchLevel.INFERIOR: 0.3,
            MatchLevel.MISMATCH: 0.0,
            MatchLevel.UNKNOWN: 0.2,
        }
        
        total_weight = 0
        weighted_score = 0
        
        for c in comparison.comparisons:
            weight = 1.0
            if c.param_name in self.CRITICAL_PARAMS:
                weight = 2.0  # 关键参数权重加倍
            
            total_weight += weight
            weighted_score += weights.get(c.match_level, 0) * weight
        
        return (weighted_score / total_weight) * 100 if total_weight > 0 else 0
    
    def _is_qualified(self, comparison: ProductComparison) -> bool:
        """判断是否满足要求"""
        # 关键参数必须满足
        for c in comparison.comparisons:
            if c.param_name in self.CRITICAL_PARAMS:
                if c.match_level in [MatchLevel.INFERIOR, MatchLevel.MISMATCH]:
                    return False
        
        # 不匹配参数不能超过30%
        if comparison.total_params > 0:
            mismatch_ratio = comparison.mismatch_params / comparison.total_params
            if mismatch_ratio > 0.3:
                return False
        
        # 整体分数不能低于60
        if comparison.overall_score < 60:
            return False
        
        return True
    
    def generate_report(self, comparison: ProductComparison) -> str:
        """生成对比报告"""
        lines = [
            f"# 参数对比报告: {comparison.product_name}",
            "",
            f"**整体评分**: {comparison.overall_score:.1f}/100",
            f"**是否合格**: {'✅ 是' if comparison.is_qualified else '❌ 否'}",
            "",
            "## 参数对比详情",
            "",
        ]
        
        # 按严重程度分组
        critical = [c for c in comparison.comparisons if c.severity == "critical"]
        warnings = [c for c in comparison.comparisons if c.severity == "warning"]
        infos = [c for c in comparison.comparisons if c.severity == "info"]
        
        if critical:
            lines.append("### 🔴 严重偏离")
            for c in critical:
                lines.append(f"- **{c.param_name}**: {c.deviation_desc}")
            lines.append("")
        
        if warnings:
            lines.append("### 🟡 轻微偏离")
            for c in warnings:
                lines.append(f"- **{c.param_name}**: {c.deviation_desc}")
            lines.append("")
        
        if infos:
            lines.append("### 🟢 匹配正常")
            for c in infos:
                lines.append(f"- {c.param_name}: {c.actual_value}")
            lines.append("")
        
        # 警告信息
        if comparison.warnings:
            lines.append("### ⚠️ 注意事项")
            for w in comparison.warnings:
                lines.append(f"- {w}")
        
        return "\n".join(lines)


# 便捷函数
def compare_specs(
    required: Dict[str, str],
    actual: Dict[str, str],
    product_name: str = ""
) -> ProductComparison:
    """快速对比参数"""
    comparator = SpecComparator()
    return comparator.compare(required, actual, product_name)
