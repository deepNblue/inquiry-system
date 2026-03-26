#!/usr/bin/env python3
"""
生成IT系统产品模拟数据
6大类，500+条记录
"""

import random
import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict


# ==================== 产品数据定义 ====================

CATEGORIES = {
    "服务器": {
        "brands": ["戴尔", "惠普", "华为", "联想", "浪潮", "新华三"],
        "prefixes": ["PowerEdge", "ProLiant", "FusionServer", "ThinkSystem", "NF", "Rack"],
        "products": [
            {"name": "机架式服务器", "base_price": 15000, "price_range": (8000, 50000)},
            {"name": "塔式服务器", "base_price": 8000, "price_range": (5000, 30000)},
            {"name": "刀片服务器", "base_price": 50000, "price_range": (30000, 150000)},
            {"name": "高密度服务器", "base_price": 80000, "price_range": (50000, 200000)},
            {"name": "GPU服务器", "base_price": 120000, "price_range": (60000, 500000)},
            {"name": "存储服务器", "base_price": 40000, "price_range": (20000, 150000)},
        ],
        "specs_patterns": [
            "CPU:{cpu}|内存:{mem}|硬盘:{disk}|电源:{psu}",
            "处理器:{cpu}|容量:{mem}|存储:{disk}|功率:{psu}W",
        ],
    },
    "存储设备": {
        "brands": ["华为", "戴尔", "惠普", "IBM", "宏杉", "曙光"],
        "prefixes": ["OceanStor", "PowerVault", "MSA", "DS", "Mseries", "ParaStor"],
        "products": [
            {"name": "NAS存储", "base_price": 20000, "price_range": (10000, 100000)},
            {"name": "SAN存储", "base_price": 80000, "price_range": (40000, 500000)},
            {"name": "全闪存阵列", "base_price": 200000, "price_range": (100000, 1000000)},
            {"name": "分布式存储", "base_price": 100000, "price_range": (50000, 800000)},
            {"name": "对象存储", "base_price": 60000, "price_range": (30000, 500000)},
            {"name": "备份设备", "base_price": 30000, "price_range": (15000, 200000)},
        ],
        "specs_patterns": [
            "容量:{capacity}|协议:{protocol}|接口:{iface}",
            "总容量:{capacity}|读写IOPS:{iops}|吞吐量:{bw}MB/s",
        ],
    },
    "网络设备": {
        "brands": ["华为", "华三", "思科", "锐捷", "TP-Link", "中兴"],
        "prefixes": ["S", "H3C", "Catalyst", "RG", "SG", "ZX"],
        "products": [
            {"name": "核心交换机", "base_price": 25000, "price_range": (10000, 100000)},
            {"name": "汇聚交换机", "base_price": 8000, "price_range": (4000, 30000)},
            {"name": "接入交换机", "base_price": 2000, "price_range": (800, 8000)},
            {"name": "路由器", "base_price": 5000, "price_range": (2000, 50000)},
            {"name": "防火墙", "base_price": 15000, "price_range": (5000, 100000)},
            {"name": "无线AP", "base_price": 800, "price_range": (300, 3000)},
        ],
        "specs_patterns": [
            "端口:{ports}|背板带宽:{bw}G|包转发率:{pps}M",
            "万兆口:{port10g}|千兆口:{port1g}|POE:{poe}W",
        ],
    },
    "安全设备": {
        "brands": ["深信服", "奇安信", "启明星辰", "绿盟", "华为", "天融信"],
        "prefixes": ["AF", "NGFW", "TS", "NF", "USG", "Top"],
        "products": [
            {"name": "下一代防火墙", "base_price": 20000, "price_range": (8000, 80000)},
            {"name": "入侵检测系统", "base_price": 15000, "price_range": (5000, 60000)},
            {"name": "入侵防御系统", "base_price": 25000, "price_range": (10000, 100000)},
            {"name": "负载均衡", "base_price": 30000, "price_range": (15000, 150000)},
            {"name": "VPN网关", "base_price": 8000, "price_range": (3000, 40000)},
            {"name": "日志审计", "base_price": 12000, "price_range": (5000, 50000)},
        ],
        "specs_patterns": [
            "吞吐量:{throughput}G|并发:{conn}万|每秒新建:{cps}",
            "带宽:{bw}M|隧道数:{tunnel}|用户数:{users}",
        ],
    },
    "监控设备": {
        "brands": ["海康威视", "大华", "宇视", "华为", "天地伟业", "中维世纪"],
        "prefixes": ["DS-", "DH-", "IPC", "Camera", "TVT", "JVS"],
        "products": [
            {"name": "网络摄像机", "base_price": 500, "price_range": (200, 3000)},
            {"name": "硬盘录像机NVR", "base_price": 3000, "price_range": (1000, 15000)},
            {"name": "视频编码器", "base_price": 1500, "price_range": (500, 5000)},
            {"name": "监控硬盘", "base_price": 800, "price_range": (400, 2000)},
            {"name": "光纤收发器", "base_price": 150, "price_range": (50, 500)},
            {"name": "监视器", "base_price": 2000, "price_range": (800, 10000)},
        ],
        "specs_patterns": [
            "分辨率:{res}|焦距:{focal}mm|红外:{ir}m|防护:{ip}",
            "像素:{pixel}M|帧率:{fps}|编码:{codec}|接口:{iface}",
        ],
    },
    "机房基础设施": {
        "brands": ["施耐德", "艾默生", "维谛", "华为", "伊顿", "山特"],
        "prefixes": ["Galaxy", "Liebert", "Vertiv", "UPS", "Power", "CASTLE"],
        "products": [
            {"name": "UPS不间断电源", "base_price": 20000, "price_range": (10000, 200000)},
            {"name": "精密空调", "base_price": 50000, "price_range": (25000, 300000)},
            {"name": "机柜", "base_price": 5000, "price_range": (2000, 20000)},
            {"name": "PDU配电单元", "base_price": 800, "price_range": (300, 3000)},
            {"name": "动环监控", "base_price": 15000, "price_range": (5000, 80000)},
            {"name": "消防设备", "base_price": 20000, "price_range": (8000, 100000)},
        ],
        "specs_patterns": [
            "功率:{power}kVA|备电:{backup}min|效率:{eff}%",
            "制冷量:{cool}kW|风量:{air}m³/h|加湿:{humid}kg/h",
        ],
    },
}

# 规格参数选项
SPEC_OPTIONS = {
    "cpu": ["Intel Xeon Gold 4210", "Intel Xeon Silver 4214", "AMD EPYC 7302", "Intel Xeon Gold 6248"],
    "mem": ["16GB DDR4", "32GB DDR4", "64GB DDR4", "128GB DDR4", "256GB DDR4"],
    "disk": ["480GB SSD", "960GB SSD", "2TB SSD", "4TB HDD", "8TB HDD", "16TB RAID"],
    "psu": ["550W", "750W", "1200W", "1600W"],
    "capacity": ["10TB", "20TB", "50TB", "100TB", "200TB", "500TB"],
    "protocol": ["iSCSI", "FC", "NFS", "SMB", "S3"],
    "iface": ["10GbE", "25GbE", "40GbE", "100GbE", "32Gb FC"],
    "iops": ["100K", "500K", "1M", "2M"],
    "bw": ["100", "200", "500", "1000", "2000"],
    "ports": ["24口", "48口", "24千兆+4万兆"],
    "port10g": ["2", "4", "6", "8", "12"],
    "port1g": ["24", "48"],
    "poe": ["0", "150", "370", "740"],
    "throughput": ["1", "2", "5", "10", "20", "40"],
    "conn": ["10", "50", "100", "200", "500"],
    "cps": ["1", "5", "10", "20", "50"],
    "tunnel": ["100", "500", "1000", "5000"],
    "users": ["100", "500", "1000", "5000"],
    "res": ["720P", "1080P", "2K", "4K", "800万"],
    "focal": ["2.8", "4", "6", "8", "12"],
    "ir": ["10", "20", "30", "50", "80", "100"],
    "ip": ["IP66", "IP67", "IP68"],
    "pixel": ["200", "300", "400", "800"],
    "fps": ["25", "30", "60"],
    "codec": ["H.264", "H.265", "H.265+"],
    "power": ["10", "20", "30", "40", "60", "80", "120", "200"],
    "backup": ["15", "30", "60", "120"],
    "eff": ["90", "92", "95", "96"],
    "cool": ["10", "20", "30", "50", "80", "100"],
    "air": ["2000", "4000", "6000", "8000"],
    "humid": ["3", "5", "8", "10"],
}

# 数据来源
SOURCES = ["京东", "天猫", "渠道商", "厂家直供", "政府采购平台", "电商平台"]


def random_spec(pattern: str) -> str:
    """生成随机规格"""
    spec = pattern
    for key, options in SPEC_OPTIONS.items():
        if f"{{{key}}}" in spec:
            value = random.choice(options)
            spec = spec.replace(f"{{{key}}}", value)
    return spec


def generate_products():
    """生成产品数据"""
    products = []
    
    for category, config in CATEGORIES.items():
        for product_template in config["products"]:
            for brand in config["brands"][:3]:  # 每个品类每个品牌取前3
                # 生成型号
                model = f"{random.choice(config['prefixes'])}{random.randint(1000, 9999)}"
                
                # 生成名称
                name = product_template["name"]
                
                # 生成规格
                pattern = random.choice(config["specs_patterns"])
                specs = random_spec(pattern)
                
                # 生成价格 (带波动)
                base_price = product_template["base_price"]
                variation = random.uniform(0.8, 1.3)
                price = int(base_price * variation / 10) * 10  # 四舍五入到10
                
                products.append({
                    "name": name,
                    "brand": brand,
                    "model": model,
                    "category": category,
                    "specs": specs,
                    "price": price,
                })
    
    return products


def generate_history_records(products: List[Dict], records_per_product: int = 3):
    """生成历史价格记录"""
    records = []
    
    for product in products:
        # 每个产品生成多条历史记录
        for i in range(records_per_product):
            # 时间分散在过去90天内
            days_ago = random.randint(0, 90)
            timestamp = (datetime.now() - timedelta(days=days_ago)).isoformat()
            
            # 价格波动 ±15%
            price_variation = random.uniform(0.85, 1.15)
            price = int(product["price"] * price_variation / 10) * 10
            
            records.append({
                "product_name": product["name"],
                "brand": product["brand"],
                "model": product["model"],
                "category": product["category"],
                "specs": product["specs"],
                "price": price,
                "source": random.choice(SOURCES),
                "timestamp": timestamp,
            })
    
    return records


def save_to_database(records: List[Dict], db_path: str = "data/history.db"):
    """保存到数据库"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    
    # 创建表
    conn.execute("""
        CREATE TABLE IF NOT EXISTS price_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_name TEXT NOT NULL,
            brand TEXT,
            model TEXT,
            price REAL NOT NULL,
            currency TEXT DEFAULT 'CNY',
            source TEXT,
            source_type TEXT DEFAULT 'web',
            category TEXT,
            specs TEXT,
            timestamp TEXT NOT NULL,
            raw_data TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # 创建索引
    conn.execute("CREATE INDEX IF NOT EXISTS idx_product_name ON price_history(product_name)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_brand ON price_history(brand)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON price_history(category)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON price_history(timestamp)")
    
    # 清空旧数据
    conn.execute("DELETE FROM price_history")
    
    # 插入新数据
    for r in records:
        conn.execute("""
            INSERT INTO price_history 
            (product_name, brand, model, price, source, category, specs, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            r["product_name"], r["brand"], r["model"],
            r["price"], r["source"], r["category"],
            r["specs"], r["timestamp"]
        ))
    
    conn.commit()
    conn.close()


import os

def main():
    print("=" * 60)
    print("  生成IT系统产品模拟数据")
    print("=" * 60)
    
    # 生成产品
    print("\n[1/3] 生成产品数据...")
    products = generate_products()
    print(f"  生成 {len(products)} 种产品")
    
    # 生成分类统计
    category_stats = {}
    for p in products:
        cat = p["category"]
        if cat not in category_stats:
            category_stats[cat] = 0
        category_stats[cat] += 1
    
    for cat, count in category_stats.items():
        print(f"    - {cat}: {count} 种")
    
    # 生成历史记录
    print("\n[2/3] 生成历史价格记录...")
    records = generate_history_records(products, records_per_product=4)
    print(f"  生成 {len(records)} 条历史记录")
    
    # 保存到数据库
    print("\n[3/3] 保存到数据库...")
    db_path = "data/history.db"
    save_to_database(records, db_path)
    
    # 统计
    conn = sqlite3.connect(db_path)
    cursor = conn.execute("SELECT COUNT(*) FROM price_history")
    total = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(DISTINCT product_name) FROM price_history")
    unique_products = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(DISTINCT category) FROM price_history")
    categories = cursor.fetchone()[0]
    
    conn.close()
    
    print(f"\n{'=' * 60}")
    print("  数据生成完成!")
    print(f"{'=' * 60}")
    print(f"  总记录数: {total}")
    print(f"  产品种类: {unique_products}")
    print(f"  产品分类: {categories}")
    print(f"  数据库: {db_path}")
    
    return total


if __name__ == "__main__":
    main()
