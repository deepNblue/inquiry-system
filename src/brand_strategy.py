"""
系统级品牌策略
支持核心设备品牌一致、辅材性价比优先
"""

from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from enum import Enum


class DevicePriority(Enum):
    """设备优先级"""
    CORE = "core"           # 核心设备：品牌一致优先
    IMPORTANT = "important"  # 重要设备：品牌参考
    GENERAL = "general"     # 通用设备：性价比优先


# 设备分类配置
DEVICE_CATEGORIES = {
    # 安防系统
    "安防系统": {
        "core": [
            "网络摄像机", "摄像头", "NVR", "硬盘录像机", 
            "视频解码器", "视频管理平台", "存储服务器"
        ],
        "important": [
            "核心交换机", "汇聚交换机", "磁盘阵列", "SAN存储"
        ],
        "general": [
            "监控硬盘", "硬盘", "网线", "光纤跳线", "水晶头",
            "电源适配器", "交换机电源", "机柜", "PDU"
        ],
        "preferred_brand": "海康威视",
        "compatible_brands": ["海康威视", "大华", "宇视"]
    },
    
    # 网络系统
    "网络系统": {
        "core": [
            "核心交换机", "路由器", "防火墙", "负载均衡"
        ],
        "important": [
            "汇聚交换机", "无线控制器", "AC控制器"
        ],
        "general": [
            "接入交换机", "无线AP", "POE交换机", "网线"
        ],
        "preferred_brand": "华为",
        "compatible_brands": ["华为", "华三", "思科", "锐捷"]
    },
    
    # 服务器系统
    "服务器系统": {
        "core": [
            "服务器", "存储服务器", "SAN存储"
        ],
        "important": [
            "磁带库", "备份设备", "光纤交换机"
        ],
        "general": [
            "KVM", "机柜", "PDU", "显示器"
        ],
        "preferred_brand": "戴尔",
        "compatible_brands": ["戴尔", "惠普", "华为", "联想"]
    },
    
    # 机房基础设施
    "机房系统": {
        "core": [
            "UPS", "精密空调", "动环监控"
        ],
        "important": [
            "配电柜", "蓄电池", "列头柜"
        ],
        "general": [
            "PDU", "机柜", "线缆", "消防设备"
        ],
        "preferred_brand": "施耐德",
        "compatible_brands": ["施耐德", "艾默生", "维谛", "华为"]
    }
}

# 辅材兼容品牌映射
GENERAL_COMPATIBLE_BRANDS = {
    "监控硬盘": ["希捷", "西数", "东芝"],
    "硬盘": ["希捷", "西数", "东芝"],
    "网线": ["康普", "罗格朗", "泛达", "绿联"],
    "光纤跳线": ["康宁", "长飞", "泛达"],
    "电源适配器": ["台达", "明纬", "菲尼克斯"],
}


@dataclass
class SystemInquiryConfig:
    """系统询价配置"""
    system_type: str                    # 系统类型
    preferred_brand: str                # 主选品牌
    core_devices: List[str]            # 核心设备
    important_devices: List[str]        # 重要设备
    general_devices: List[str]          # 通用设备
    compatible_brands: List[str]       # 兼容品牌


class BrandStrategy:
    """品牌策略管理器"""
    
    def __init__(self, system_type: str = "安防系统"):
        self.system_type = system_type
        self.config = self._get_config(system_type)
    
    def _get_config(self, system_type: str) -> SystemInquiryConfig:
        """获取系统配置"""
        if system_type not in DEVICE_CATEGORIES:
            # 默认安防系统
            system_type = "安防系统"
        
        cat = DEVICE_CATEGORIES[system_type]
        return SystemInquiryConfig(
            system_type=system_type,
            preferred_brand=cat["preferred_brand"],
            core_devices=cat["core"],
            important_devices=cat["important"],
            general_devices=cat["general"],
            compatible_brands=cat["compatible_brands"]
        )
    
    def get_device_priority(self, device_name: str) -> DevicePriority:
        """获取设备优先级"""
        name = device_name.lower()
        
        # 核心设备
        for d in self.config.core_devices:
            if d.lower() in name or name in d.lower():
                return DevicePriority.CORE
        
        # 重要设备
        for d in self.config.important_devices:
            if d.lower() in name or name in d.lower():
                return DevicePriority.IMPORTANT
        
        # 通用设备
        for d in self.config.general_devices:
            if d.lower() in name or name in d.lower():
                return DevicePriority.GENERAL
        
        # 默认重要设备
        return DevicePriority.IMPORTANT
    
    def get_preferred_brands(self, device_name: str) -> List[str]:
        """
        获取首选品牌列表
        
        核心设备：主选品牌优先
        通用设备：性价比品牌
        """
        priority = self.get_device_priority(device_name)
        name = device_name.lower()
        
        if priority == DevicePriority.CORE:
            # 核心设备：主选品牌优先
            return [self.config.preferred_brand] + self.config.compatible_brands
        
        elif priority == DevicePriority.IMPORTANT:
            # 重要设备：兼容品牌
            return self.config.compatible_brands
        
        else:
            # 通用设备：辅材兼容品牌
            for general_type, brands in GENERAL_COMPATIBLE_BRANDS.items():
                if general_type.lower() in name:
                    return brands
            # 默认返回兼容品牌
            return self.config.compatible_brands
    
    def classify_devices(self, devices: List[Dict]) -> Dict[str, List[Dict]]:
        """对设备列表进行分类"""
        classified = {
            "core": [],
            "important": [],
            "general": []
        }
        
        for device in devices:
            name = device.get("name", "")
            priority = self.get_device_priority(name)
            
            if priority == DevicePriority.CORE:
                classified["core"].append(device)
            elif priority == DevicePriority.IMPORTANT:
                classified["important"].append(device)
            else:
                classified["general"].append(device)
        
        return classified
    
    def suggest_brand(self, device_name: str, available_brands: List[str]) -> str:
        """建议品牌"""
        preferred = self.get_preferred_brands(device_name)
        
        # 按优先级顺序选择
        for brand in preferred:
            if brand in available_brands:
                return brand
        
        # 如果首选都不在，返回可用品牌中的第一个
        return available_brands[0] if available_brands else "待定"
    
    def generate_strategy_report(self) -> str:
        """生成策略报告"""
        lines = [
            f"## 系统类型: {self.config.system_type}",
            f"**主选品牌**: {self.config.preferred_brand}",
            "",
            "### 设备分类",
            "",
            "**🔴 核心设备** (品牌一致优先):",
        ]
        
        for d in self.config.core_devices:
            lines.append(f"- {d}")
        
        lines.extend(["", "**🟡 重要设备** (品牌参考):"])
        for d in self.config.important_devices:
            lines.append(f"- {d}")
        
        lines.extend(["", "**🟢 通用设备** (性价比优先):"])
        for d in self.config.general_devices:
            lines.append(f"- {d}")
        
        lines.extend(["", "### 兼容品牌"])
        lines.append(f"- 主选: {self.config.preferred_brand}")
        lines.append(f"- 兼容: {', '.join(self.config.compatible_brands)}")
        
        return "\n".join(lines)


# 快捷函数
def get_brand_strategy(system_type: str = "安防系统") -> BrandStrategy:
    """获取品牌策略"""
    return BrandStrategy(system_type)


def classify_device(device_name: str, system_type: str = "安防系统") -> str:
    """快速分类设备"""
    strategy = BrandStrategy(system_type)
    priority = strategy.get_device_priority(device_name)
    return priority.value


def get_best_brand(device_name: str, available_brands: List[str], system_type: str = "安防系统") -> str:
    """获取最佳品牌"""
    strategy = BrandStrategy(system_type)
    return strategy.suggest_brand(device_name, available_brands)
