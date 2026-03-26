"""
置信度引擎
计算询价结果的置信度
来源权重 × 时效衰减 × 参数匹配度
"""

import re
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ConfidenceResult:
    """置信度计算结果"""
    total_score: float  # 总分 0-100
    source_score: float  # 来源得分
    time_score: float    # 时效得分
    match_score: float  # 匹配得分
    factors: Dict[str, Any] = field(default_factory=dict)  # 详细因子
    
    @property
    def level(self) -> str:
        """置信度等级"""
        if self.total_score >= 90:
            return "A"
        elif self.total_score >= 70:
            return "B"
        elif self.total_score >= 50:
            return "C"
        elif self.total_score >= 30:
            return "D"
        else:
            return "F"
    
    @property
    def description(self) -> str:
        """置信度描述"""
        descriptions = {
            "A": "高置信度 - 建议直接采用",
            "B": "较高置信度 - 可供参考",
            "C": "中等置信度 - 建议核实",
            "D": "较低置信度 - 仅供参考",
            "F": "低置信度 - 需进一步核实"
        }
        return descriptions.get(self.level, "")


@dataclass
class PriceRecord:
    """价格记录"""
    product_name: str
    price: float
    source: str  # 来源: 京东/淘宝/邮件/历史
    source_type: str  # web/manufacturer/email/history
    timestamp: datetime
    brand: str = ""
    model: str = ""
    specs: Dict[str, Any] = field(default_factory=dict)  # 技术参数
    match_score: float = 1.0  # 与需求的匹配度
    url: str = ""


class ConfidenceEngine:
    """
    置信度引擎
    综合评估价格的可信程度
    """
    
    # 来源权重配置
    SOURCE_WEIGHTS = {
        # 高权重来源（官方/权威）
        "官网": 1.0,
        "官方网站": 1.0,
        "厂商": 1.0,
        "厂家": 1.0,
        "official": 1.0,
        
        # 中高权重来源（正规渠道）
        "京东": 0.95,
        "天猫": 0.9,
        "淘宝": 0.85,
        "官方旗舰店": 0.95,
        "jd": 0.95,
        "tmall": 0.9,
        "taobao": 0.85,
        
        # 中权重来源（第三方平台）
        "1688": 0.8,
        "拼多多": 0.75,
        "pdd": 0.75,
        "alibaba": 0.8,
        
        # 中低权重来源
        "分销商": 0.7,
        "代理商": 0.7,
        "经销商": 0.7,
        
        # 低权重来源
        "询价邮件": 0.6,
        "邮件": 0.6,
        "email": 0.6,
        "微信": 0.5,
        "wechat": 0.5,
        
        # 最低权重
        "历史记录": 0.5,
        "history": 0.5,
        "估算": 0.3,
        "estimate": 0.3,
    }
    
    # 默认权重
    DEFAULT_SOURCE_WEIGHT = 0.5
    
    def __init__(self):
        self.discount_rate = 0.05  # 每月折扣率 5%
    
    def calculate(self, record: PriceRecord, requirement: Dict = None) -> ConfidenceResult:
        """
        计算置信度
        
        Args:
            record: 价格记录
            requirement: 需求规格（用于匹配度计算）
        
        Returns:
            置信度结果
        """
        # 1. 来源得分
        source_score = self._calculate_source_score(record.source, record.source_type)
        
        # 2. 时效得分（越新越高）
        time_score = self._calculate_time_score(record.timestamp)
        
        # 3. 匹配得分（参数匹配度）
        match_score = self._calculate_match_score(record, requirement)
        
        # 4. 综合得分（加权平均）
        # 来源: 30%, 时效: 20%, 匹配: 50%
        total_score = (
            source_score * 0.30 +
            time_score * 0.20 +
            match_score * 0.50
        )
        
        return ConfidenceResult(
            total_score=round(total_score, 2),
            source_score=round(source_score, 2),
            time_score=round(time_score, 2),
            match_score=round(match_score, 2),
            factors={
                "source": record.source,
                "source_type": record.source_type,
                "age_days": (datetime.now() - record.timestamp).days,
                "match_details": self._get_match_details(record, requirement)
            }
        )
    
    def _calculate_source_score(self, source: str, source_type: str) -> float:
        """计算来源得分"""
        # 优先按来源名称匹配
        source_lower = source.lower()
        for key, weight in self.SOURCE_WEIGHTS.items():
            if key.lower() in source_lower:
                return weight * 100
        
        # 按来源类型
        type_weights = {
            "web": 0.8,
            "manufacturer": 0.9,
            "email": 0.6,
            "history": 0.5,
        }
        
        return type_weights.get(source_type, self.DEFAULT_SOURCE_WEIGHT) * 100
    
    def _calculate_time_score(self, timestamp: datetime) -> float:
        """计算时效得分（按天衰减）"""
        if not timestamp:
            return 50.0  # 无时间信息
        
        days_old = (datetime.now() - timestamp).days
        
        if days_old < 0:
            # 未来时间，按当前计算
            days_old = 0
        
        # 初始100，每天衰减
        score = 100 - (days_old * self.discount_rate * 100)
        
        # 最少不低于10
        return max(10.0, score)
    
    def _calculate_match_score(self, record: PriceRecord, requirement: Dict) -> float:
        """计算匹配得分"""
        if not requirement:
            return 80.0  # 无需求信息，默认80
        
        score = 80.0
        details = []
        
        # 1. 品牌匹配
        if requirement.get("brand") and record.brand:
            if self._brand_match(requirement["brand"], record.brand):
                score += 10
                details.append("品牌匹配")
            else:
                score -= 15
                details.append(f"品牌不匹配: 要求{requirement['brand']}, 实际{record.brand}")
        
        # 2. 型号匹配
        if requirement.get("model") and record.model:
            if self._model_match(requirement["model"], record.model):
                score += 10
                details.append("型号匹配")
            else:
                # 型号相似度
                similarity = self._string_similarity(requirement["model"], record.model)
                if similarity > 0.6:
                    score += 5
                else:
                    score -= 10
                    details.append(f"型号差异")
        
        # 3. 参数匹配
        if requirement.get("specs") and record.specs:
            spec_match = self._specs_match(requirement["specs"], record.specs)
            score += spec_match * 10
            if spec_match < 0.5:
                details.append(f"参数匹配度: {spec_match:.0%}")
        
        # 4. 价格合理性
        if record.price > 0:
            # 价格异常检测（过高或过低）
            if record.price < 1 or record.price > 10000000:
                score -= 20
                details.append("价格异常")
        
        return max(0, min(100, score))
    
    def _brand_match(self, required: str, actual: str) -> bool:
        """品牌匹配"""
        required = required.lower()
        actual = actual.lower()
        
        # 完全匹配
        if required == actual:
            return True
        
        # 包含匹配
        if required in actual or actual in required:
            return True
        
        # 常见别名
        aliases = {
            "hikvision": ["海康", "HIKVISION", "海康威视"],
            "dahua": ["大华", "dahua", "浙江大华"],
            "huawei": ["华为", "HUAWEI"],
            "apple": ["苹果", "Apple"],
            "lenovo": ["联想", "Lenovo"],
        }
        
        for eng, chn_list in aliases.items():
            if eng in required or eng in actual:
                for chn in chn_list:
                    if chn in required and chn in actual:
                        return True
        
        return False
    
    def _model_match(self, required: str, actual: str) -> bool:
        """型号匹配"""
        # 清理后匹配
        r = re.sub(r'[\s\-_]', '', required.lower())
        a = re.sub(r'[\s\-_]', '', actual.lower())
        
        if r == a:
            return True
        
        # 包含匹配
        if r in a or a in r:
            return True
        
        # 相似度
        similarity = self._string_similarity(r, a)
        return similarity > 0.8
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """字符串相似度（简单版）"""
        if not s1 or not s2:
            return 0
        
        # 公共字符比例
        common = sum(1 for c in s1 if c in s2)
        return common / max(len(s1), len(s2))
    
    def _specs_match(self, required: Dict, actual: Dict) -> float:
        """参数匹配"""
        if not required or not actual:
            return 0.5
        
        matched = 0
        total = len(required)
        
        for key, value in required.items():
            if key in actual:
                if self._value_match(str(value), str(actual[key])):
                    matched += 1
        
        return matched / total if total > 0 else 0.5
    
    def _value_match(self, v1: str, v2: str) -> bool:
        """参数值匹配"""
        # 数字比较
        try:
            n1 = float(re.search(r'[\d.]+', v1).group())
            n2 = float(re.search(r'[\d.]+', v2).group())
            
            # 允许10%误差
            if abs(n1 - n2) / max(n1, n2) < 0.1:
                return True
            
            # 实际值 >= 要求值（参数优于要求）
            if n2 >= n1:
                return True
                
        except (ValueError, AttributeError):
            pass
        
        # 字符串包含
        v1_clean = v1.lower()
        v2_clean = v2.lower()
        return v1_clean in v2_clean or v2_clean in v1_clean
    
    def _get_match_details(self, record: PriceRecord, requirement: Dict) -> str:
        """获取匹配详情"""
        if not requirement:
            return "无规格要求"
        
        details = []
        
        if requirement.get("brand") and record.brand:
            if self._brand_match(requirement["brand"], record.brand):
                details.append("✓ 品牌匹配")
            else:
                details.append(f"✗ 品牌不匹配")
        
        if requirement.get("model") and record.model:
            if self._model_match(requirement["model"], record.model):
                details.append("✓ 型号匹配")
            else:
                details.append("△ 型号有差异")
        
        return ", ".join(details) if details else "基本匹配"


def calculate_confidence(record: PriceRecord, requirement: Dict = None) -> ConfidenceResult:
    """快速计算置信度"""
    engine = ConfidenceEngine()
    return engine.calculate(record, requirement)
