"""
竞品调研模块
自动追踪竞品价格变化
"""

import asyncio
from typing import List, Dict, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
from pathlib import Path


@dataclass
class CompetitorProduct:
    """竞品追踪产品"""
    id: str
    name: str
    brand: str
    category: str = ""
    keywords: List[str] = field(default_factory=list)
    data_sources: List[str] = field(default_factory=list)  # ["jd", "taobao", "alibaba"]
    check_interval_hours: int = 24
    alert_threshold: float = 0  # 价格变化超过此百分比时告警


@dataclass 
class PriceAlert:
    """价格告警"""
    product_id: str
    product_name: str
    old_price: float
    new_price: float
    change_percent: float
    source: str
    timestamp: str


class CompetitorTracker:
    """竞品价格追踪器"""
    
    def __init__(self, db_path: str = "data/competitors.db"):
        self.db_path = db_path
        self.conn = None
        self.products: Dict[str, CompetitorProduct] = {}
        self.alerts: List[PriceAlert] = []
        self._init_db()
        self._load_products()
    
    def _init_db(self):
        """初始化数据库"""
        import sqlite3
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS competitor_products (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                brand TEXT,
                category TEXT,
                keywords TEXT,
                data_sources TEXT,
                check_interval_hours INTEGER DEFAULT 24,
                alert_threshold REAL DEFAULT 0
            )
        """)
        
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT,
                price REAL,
                currency TEXT DEFAULT 'CNY',
                source TEXT,
                timestamp TEXT,
                FOREIGN KEY (product_id) REFERENCES competitor_products(id)
            )
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_time ON price_history(product_id, timestamp)
        """)
        
        self.conn.commit()
    
    def _load_products(self):
        """加载产品列表"""
        cursor = self.conn.execute("SELECT * FROM competitor_products")
        for row in cursor.fetchall():
            product = CompetitorProduct(
                id=row[0],
                name=row[1],
                brand=row[2] or "",
                category=row[3] or "",
                keywords=json.loads(row[4]) if row[4] else [],
                data_sources=json.loads(row[5]) if row[5] else [],
                check_interval_hours=row[6] or 24,
                alert_threshold=row[7] or 0
            )
            self.products[product.id] = product
    
    def add_product(self, product: CompetitorProduct):
        """添加竞品"""
        self.conn.execute("""
            INSERT OR REPLACE INTO competitor_products 
            (id, name, brand, category, keywords, data_sources, check_interval_hours, alert_threshold)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product.id,
            product.name,
            product.brand,
            product.category,
            json.dumps(product.keywords),
            json.dumps(product.data_sources),
            product.check_interval_hours,
            product.alert_threshold
        ))
        self.conn.commit()
        self.products[product.id] = product
    
    def record_price(self, product_id: str, price: float, source: str):
        """记录价格"""
        self.conn.execute("""
            INSERT INTO price_history (product_id, price, source, timestamp)
            VALUES (?, ?, ?, ?)
        """, (product_id, price, source, datetime.now().isoformat()))
        self.conn.commit()
        
        # 检查是否需要告警
        self._check_alert(product_id, price, source)
    
    def _check_alert(self, product_id: str, new_price: float, source: str):
        """检查价格告警"""
        if product_id not in self.products:
            return
        
        product = self.products[product_id]
        if product.alert_threshold <= 0:
            return
        
        # 获取上次价格
        cursor = self.conn.execute("""
            SELECT price FROM price_history 
            WHERE product_id = ? AND source = ?
            ORDER BY timestamp DESC LIMIT 1 OFFSET 1
        """, (product_id, source))
        
        row = cursor.fetchone()
        if not row:
            return
        
        old_price = row[0]
        change_pct = abs(new_price - old_price) / old_price * 100
        
        if change_pct >= product.alert_threshold:
            self.alerts.append(PriceAlert(
                product_id=product_id,
                product_name=product.name,
                old_price=old_price,
                new_price=new_price,
                change_percent=change_pct,
                source=source,
                timestamp=datetime.now().isoformat()
            ))
    
    def get_latest_prices(self, product_id: str) -> List[Dict]:
        """获取最新价格"""
        cursor = self.conn.execute("""
            SELECT price, source, timestamp 
            FROM price_history
            WHERE product_id = ?
            ORDER BY timestamp DESC
        """, (product_id,))
        
        return [
            {"price": row[0], "source": row[1], "timestamp": row[2]}
            for row in cursor.fetchall()
        ]
    
    def get_price_trend(self, product_id: str, days: int = 30) -> List[Dict]:
        """获取价格趋势"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = self.conn.execute("""
            SELECT DATE(timestamp) as date, AVG(price) as avg_price, MIN(price) as min_price, MAX(price) as max_price
            FROM price_history
            WHERE product_id = ? AND timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (product_id, cutoff))
        
        return [
            {"date": row[0], "avg_price": row[1], "min_price": row[2], "max_price": row[3]}
            for row in cursor.fetchall()
        ]
    
    def get_all_alerts(self) -> List[PriceAlert]:
        """获取所有告警"""
        return self.alerts
    
    def clear_alerts(self):
        """清除告警"""
        self.alerts = []
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# 便捷函数
def track_product(name: str, brand: str, category: str = "", **kwargs) -> CompetitorProduct:
    """创建竞品追踪产品"""
    import hashlib
    product_id = hashlib.md5(f"{name}{brand}".encode()).hexdigest()[:8]
    
    return CompetitorProduct(
        id=product_id,
        name=name,
        brand=brand,
        category=category,
        **kwargs
    )
