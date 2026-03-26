#!/usr/bin/env python3
"""
填充演示数据
为系统添加历史价格数据，便于演示和测试
"""

import os
import sys
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.history import HistoryMatcher


def seed_demo_data():
    """填充演示数据"""
    
    print("=" * 50)
    print("  填充演示数据")
    print("=" * 50)
    
    # 创建历史匹配器
    matcher = HistoryMatcher()
    
    # 演示产品数据（带详细技术参数）
    products = [
        # 安防监控 - 网络摄像机
        {
            "product_name": "网络摄像机",
            "brand": "海康威视",
            "model": "DS-2CD3T86FWDV2-I3S",
            "specs": "分辨率:1920*1080@30fps;焦距:4mm定焦;红外距离:30m;防护等级:IP67;宽动态:120dB",
            "base_price": 850,
            "variance": 150,
            "source": "京东"
        },
        {
            "product_name": "网络摄像机",
            "brand": "海康威视",
            "model": "DS-2CD3T86FWDV2-I3S",
            "specs": "分辨率:1920*1080@30fps;焦距:4mm定焦;红外距离:30m;防护等级:IP67;宽动态:120dB",
            "base_price": 780,
            "variance": 80,
            "source": "渠道商"
        },
        {
            "product_name": "网络摄像机",
            "brand": "海康威视",
            "model": "DS-2CD3T86FWDV2-I3S",
            "specs": "分辨率:1920*1080@30fps;焦距:6mm;红外距离:50m;防护等级:IP67",
            "base_price": 920,
            "variance": 100,
            "source": "天猫"
        },
        # 硬盘录像机
        {
            "product_name": "硬盘录像机",
            "brand": "海康威视",
            "model": "DS-8632N-K8",
            "specs": "32路NVR;8盘位;支持H.265+;4K HDMI输出;千兆网口",
            "base_price": 3200,
            "variance": 400,
            "source": "京东"
        },
        {
            "product_name": "硬盘录像机",
            "brand": "海康威视",
            "model": "DS-8632N-K8",
            "specs": "32路NVR;8盘位;支持H.265+;4K HDMI输出;千兆网口",
            "base_price": 2950,
            "variance": 200,
            "source": "天猫"
        },
        # 监控硬盘
        {
            "product_name": "监控硬盘",
            "brand": "希捷",
            "model": "ST8000VX001",
            "specs": "容量:8TB;转速:7200RPM;缓存:256MB;接口:SATA3;支持7*24工作",
            "base_price": 1250,
            "variance": 100,
            "source": "京东"
        },
        {
            "product_name": "监控硬盘",
            "brand": "希捷",
            "model": "ST8000VX001",
            "specs": "容量:8TB;转速:7200RPM;缓存:256MB;接口:SATA3;支持7*24工作",
            "base_price": 1180,
            "variance": 50,
            "source": "渠道商"
        },
        {
            "product_name": "监控硬盘",
            "brand": "西部数据",
            "model": "WD80PURZ",
            "specs": "容量:8TB;转速:5400RPM;缓存:128MB;接口:SATA3;紫盘",
            "base_price": 1150,
            "variance": 80,
            "source": "天猫"
        },
        # 核心交换机
        {
            "product_name": "核心交换机",
            "brand": "华为",
            "model": "S5735S-L48T4S-A1",
            "specs": "48千兆电口+4万兆光口;交换容量:256Gbps;包转发率:96Mpps;支持VLAN/ACL/QoS",
            "base_price": 5800,
            "variance": 800,
            "source": "京东"
        },
        {
            "product_name": "核心交换机",
            "brand": "华为",
            "model": "S5735S-L48T4S-A1",
            "specs": "48千兆电口+4万兆光口;交换容量:256Gbps;包转发率:96Mpps;支持VLAN/ACL/QoS",
            "base_price": 5500,
            "variance": 500,
            "source": "渠道商"
        },
        # 接入交换机
        {
            "product_name": "接入交换机",
            "brand": "华为",
            "model": "S1730S-L24P-A",
            "specs": "24千兆POE口;POE功率:370W;支持802.3af/at;万兆上联;风扇散热",
            "base_price": 1850,
            "variance": 200,
            "source": "天猫"
        },
        {
            "product_name": "接入交换机",
            "brand": "华为",
            "model": "S1730S-L24P-A",
            "specs": "24千兆POE口;POE功率:370W;支持802.3af/at;万兆上联;风扇散热",
            "base_price": 1750,
            "variance": 150,
            "source": "京东"
        },
        # 光纤收发器
        {
            "product_name": "光纤收发器",
            "brand": "TP-Link",
            "model": "MC210CS",
            "specs": "速率:千兆;传输距离:20km;波长:1310nm;单模光纤;SC接口",
            "base_price": 180,
            "variance": 30,
            "source": "京东"
        },
        {
            "product_name": "光纤收发器",
            "brand": "TP-Link",
            "model": "MC210CS",
            "specs": "速率:千兆;传输距离:20km;波长:1310nm;单模光纤;SC接口",
            "base_price": 165,
            "variance": 20,
            "source": "天猫"
        },
        # 服务器
        {
            "product_name": "服务器",
            "brand": "戴尔",
            "model": "PowerEdge R750",
            "specs": "CPU:2*Xeon Gold 4210;内存:256GB DDR4;硬盘:4TB SSD+8TB SATA;RAID卡;双电源",
            "base_price": 45000,
            "variance": 5000,
            "source": "戴尔官网"
        },
        {
            "product_name": "服务器",
            "brand": "联想",
            "model": "ThinkSystem SR650",
            "specs": "CPU:2*Xeon Silver 4210;内存:128GB DDR4;硬盘:2TB SSD+4TB SATA;RAID卡;双电源",
            "base_price": 38000,
            "variance": 4000,
            "source": "联想官网"
        },
        # 精密空调
        {
            "product_name": "精密空调",
            "brand": "施耐德",
            "model": "ACRD061",
            "specs": "制冷量:30kW;风量:6000m³/h;加湿量:8kg/h;噪声:<55dB;电加热:9kW",
            "base_price": 68000,
            "variance": 5000,
            "source": "厂商"
        },
        {
            "product_name": "精密空调",
            "brand": "艾默生",
            "model": "Liebert CRA",
            "specs": "制冷量:30kW;风量:6500m³/h;加湿量:10kg/h;噪声:<58dB;电加热:12kW",
            "base_price": 65000,
            "variance": 4000,
            "source": "厂商"
        },
        # UPS电源
        {
            "product_name": "UPS电源",
            "brand": "艾默生",
            "model": "UH31-40KL",
            "specs": "容量:40kVA/40kW;输入:380Vac;输出:380Vac;电池:32节12V/100Ah;效率:95%",
            "base_price": 55000,
            "variance": 3000,
            "source": "厂商"
        },
        {
            "product_name": "UPS电源",
            "brand": "施耐德",
            "model": "Galaxy VS",
            "specs": "容量:40kVA;模块化;效率:96%;输入功率因数:0.99;支持并机",
            "base_price": 58000,
            "variance": 5000,
            "source": "厂商"
        },
        # 机柜
        {
            "product_name": "机柜",
            "brand": "联想",
            "model": "NetCol5000-A042K",
            "specs": "规格:42U;尺寸:600*1100*2000mm;承重:1500kg;前网孔门;后网孔门;侧门;顶盖",
            "base_price": 5800,
            "variance": 800,
            "source": "渠道商"
        },
        {
            "product_name": "机柜",
            "brand": "图腾",
            "model": "K3-6642",
            "specs": "规格:42U;尺寸:600*1100*2000mm;承重:1200kg;前网孔门;后网孔门;侧门;PDU",
            "base_price": 4500,
            "variance": 500,
            "source": "天猫"
        },
    ]
    
    print(f"\n开始填充 {len(products)} 个产品数据...")
    print()
    
    total_added = 0
    
    for p in products:
        # 生成多条历史记录
        for i in range(random.randint(2, 4)):
            # 价格波动
            price = p["base_price"] + random.randint(-p["variance"], p["variance"])
            price = round(price / 10) * 10
            
            try:
                matcher.add_price_record(
                    product_name=p["product_name"],
                    price=price,
                    brand=p["brand"],
                    model=p["model"],
                    specs=p["specs"],
                    source=p["source"],
                    source_type="history"
                )
                total_added += 1
            except Exception as e:
                print(f"  添加失败: {e}")
    
    print(f"✓ 已添加 {total_added} 条历史记录")
    
    # 查询统计
    print("\n数据统计:")
    print("-" * 40)
    
    for brand in ["海康威视", "华为", "Apple", "戴尔"]:
        results = matcher.search_similar(brand, top_k=100)
        if results:
            avg_price = sum(r.price for r in results) / len(results)
            print(f"  {brand}: {len(results)} 条记录, 平均价格 ¥{avg_price:,.0f}")
    
    matcher.close()
    
    print("\n" + "=" * 50)
    print("  演示数据填充完成")
    print("=" * 50)


if __name__ == "__main__":
    seed_demo_data()
