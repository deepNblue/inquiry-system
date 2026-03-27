"""
系统级品牌策略 v2
- 核心设备：同一系统内品牌一致
- 通用设备：性价比优先
- 关联系统：紧密关联的系统尽量保持一致
"""

from typing import List, Dict, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum


def detect_system_type(device_name: str) -> Optional[str]:
    """检测设备所属系统"""
    name = device_name.lower()
    
    for sys_name, config in SYSTEMS.items():
        for keyword in config["core_keywords"]:
            if keyword.lower() in name:
                return sys_name
    
    # 检查辅材关联
    for category, brands in GENERAL_BRANDS.items():
        if category.lower() in name:
            # 监控相关辅材归属安防
            if category in ["监控硬盘"]:
                return "安防系统"
            # 网线等通用辅材不归属特定系统
            return None
    
    return None


class DeviceType(Enum):
    """设备类型"""
    CORE = "core"       # 核心设备：系统内品牌一致
    GENERAL = "general"  # 通用设备：性价比优先


# 系统配置
SYSTEMS = {
    "安防系统": {
        "core_keywords": [
            "摄像机", "摄像头", "NVR", "硬盘录像机", "视频解码器",
            "视频管理平台", "监控摄像头", "网络摄像机"
        ],
        "preferred_brand": "海康威视",
        "related_systems": ["网络系统", "服务器系统"],  # 关联系统
    },
    "网络系统": {
        "core_keywords": [
            "交换机", "路由器", "防火墙", "负载均衡", "无线AC",
            "无线控制器", "核心交换机", "汇聚交换机"
        ],
        "preferred_brand": "华为",
        "related_systems": ["安防系统", "服务器系统"],
    },
    "服务器系统": {
        "core_keywords": [
            "服务器", "存储服务器", "SAN存储", "磁带库",
            "备份设备", "光纤交换机", "存储", "阵列", "磁带"
        ],
        "preferred_brand": "戴尔",
        "related_systems": ["网络系统", "机房系统"],
    },
    "机房系统": {
        "core_keywords": [
            "UPS", "精密空调", "动环监控", "配电柜", "蓄电池",
            "列头柜", "冷水机组"
        ],
        "preferred_brand": "施耐德",
        "related_systems": ["服务器系统"],
    },
}

# 核心设备的兼容品牌（同系统内可接受的替代）
CORE_COMPATIBLE = {
    "安防系统": ["海康威视", "大华", "宇视", "华为", "天地伟业"],
    "网络系统": ["华为", "华三", "思科", "锐捷", "中兴"],
    "服务器系统": ["戴尔", "惠普", "华为", "联想", "浪潮", "新华三"],
    "机房系统": ["施耐德", "艾默生", "维谛", "华为", "伊顿", "山特"],
}

# 通用辅材品牌（性价比优先）
GENERAL_BRANDS = {
    "监控硬盘": ["希捷", "西数", "东芝"],
    "硬盘": ["希捷", "西数", "东芝"],
    "固态硬盘": ["三星", "intel", "西部数据", "金士顿"],
    "网线": ["康普", "罗格朗", "泛达", "绿联", "秋叶原"],
    "光纤跳线": ["康宁", "长飞", "泛达", "光纤之城"],
    "水晶头": ["绿联", "泛达", "罗格朗"],
    "电源适配器": ["台达", "明纬", "菲尼克斯", "长城"],
    "机柜": ["图腾", "艾默生", "威图", "国产标准"],
    "PDU": ["突破", "施耐德", "艾默生"],
    "理线架": ["绿联", "泛达", "康普"],
}


@dataclass
class SystemBrand:
    """系统品牌记录"""
    system_type: str
    brand: str
    is_core_selected: bool = False


class BrandStrategy:
    """品牌策略管理器"""
    
    def __init__(self):
        self.selected_brands: Dict[str, str] = {}  # system_type -> brand
        self.related_brand_hints: Set[str] = set()  # 关联品牌提示
    
    def get_device_type(self, device_name: str) -> DeviceType:
        """判断设备类型"""
        name = device_name.lower()
        
        for system_name, config in SYSTEMS.items():
            for keyword in config["core_keywords"]:
                if keyword.lower() in name:
                    return DeviceType.CORE
        
        return DeviceType.GENERAL
    
    def get_core_brands(self, system_type: str) -> List[str]:
        """获取核心品牌列表"""
        brands = CORE_COMPATIBLE.get(system_type, [])
        
        # 加入关联系统已选品牌
        related = self._get_related_selected_brands(system_type)
        brands = list(dict.fromkeys(related + brands))  # 去重，保持顺序
        
        return brands
    
    def get_general_brands(self, device_name: str) -> List[str]:
        """获取通用品牌列表（性价比优先）"""
        name = device_name.lower()
        
        # 查找匹配的辅材类别
        for category, brands in GENERAL_BRANDS.items():
            if category.lower() in name:
                return brands
        
        # 默认辅材品牌
        return ["希捷", "西数", "绿联", "台达"]
    
    def _get_related_selected_brands(self, system_type: str) -> List[str]:
        """获取关联系统已选品牌"""
        related_brands = []
        
        # 1. 关联系统已选品牌
        related_systems = SYSTEMS.get(system_type, {}).get("related_systems", [])
        for rel_sys in related_systems:
            if rel_sys in self.selected_brands:
                related_brands.append(self.selected_brands[rel_sys])
        
        return related_brands
    
    def select_core_brand(self, system_type: str) -> str:
        """选择核心品牌"""
        if system_type in self.selected_brands:
            return self.selected_brands[system_type]
        
        # 优先选择关联系统已选品牌
        related = self._get_related_selected_brands(system_type)
        if related:
            brand = related[0]
            self.selected_brands[system_type] = brand
            return brand
        
        # 否则选择系统主选品牌
        brand = SYSTEMS.get(system_type, {}).get("preferred_brand", "待定")
        self.selected_brands[system_type] = brand
        return brand
    
    def select_brand_for_device(
        self,
        device_name: str,
        system_type: str,
        available_brands: List[str] = None
    ) -> str:
        """
        为设备选择品牌
        
        策略:
        1. 核心设备：优先同系统已选品牌，其次关联系统品牌
        2. 通用设备：性价比最优
        """
        device_type = self.get_device_type(device_name)
        
        if device_type == DeviceType.CORE:
            # 核心设备：品牌一致
            core_brands = self.get_core_brands(system_type)
            
            # 按优先级选择
            for brand in core_brands:
                if available_brands:
                    if brand in available_brands:
                        return brand
                else:
                    return brand
            
            return core_brands[0] if core_brands else "待定"
        
        else:
            # 通用设备：性价比优先
            general_brands = self.get_general_brands(device_name)
            
            for brand in general_brands:
                if available_brands:
                    if brand in available_brands:
                        return brand
                else:
                    return brand
            
            return general_brands[0] if general_brands else "性价比最优"
    
    def record_selection(self, system_type: str, brand: str, is_core: bool):
        """记录品牌选择"""
        if is_core:
            self.selected_brands[system_type] = brand
    
    def get_selection_summary(self) -> str:
        """获取选择汇总"""
        lines = []
        for system, brand in self.selected_brands.items():
            lines.append(f"- {system}: {brand}")
        return "\n".join(lines) if lines else "尚未选择任何品牌"


# 辅助函数
def classify_core_device(device_name: str) -> bool:
    """判断是否为核心设备"""
    strategy = BrandStrategy()
    return strategy.get_device_type(device_name) == DeviceType.CORE


def suggest_brand(device_name: str, system_type: str, available_brands: List[str] = None) -> str:
    """建议品牌"""
    strategy = BrandStrategy()
    return strategy.select_brand_for_device(device_name, system_type, available_brands)


