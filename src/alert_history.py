"""
告警历史存储
持久化告警记录，支持查询和统计
"""

import os
import sqlite3
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path


@dataclass
class AlertRecord:
    """告警记录"""
    id: int
    rule_id: str
    product_name: str
    brand: str
    alert_type: str
    old_price: float
    new_price: float
    change_percent: float
    source: str
    timestamp: str
    acknowledged: bool = False
    notes: str = ""


class AlertHistory:
    """
    告警历史管理器
    SQLite 持久化存储
    """
    
    def __init__(self, db_path: str = "data/alert_history.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # 告警记录表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS alert_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rule_id TEXT,
                product_name TEXT NOT NULL,
                brand TEXT,
                alert_type TEXT NOT NULL,
                old_price REAL,
                new_price REAL,
                change_percent REAL,
                source TEXT,
                timestamp TEXT NOT NULL,
                acknowledged INTEGER DEFAULT 0,
                notes TEXT
            )
        """)
        
        # 创建索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_product ON alert_history(product_name)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON alert_history(timestamp)
        """)
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_type ON alert_history(alert_type)
        """)
        
        self.conn.commit()
    
    def add_record(
        self,
        rule_id: str,
        product_name: str,
        alert_type: str,
        old_price: float,
        new_price: float,
        change_percent: float,
        brand: str = "",
        source: str = ""
    ) -> int:
        """添加告警记录"""
        cursor = self.conn.execute("""
            INSERT INTO alert_history 
            (rule_id, product_name, brand, alert_type, old_price, new_price, change_percent, source, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            rule_id, product_name, brand, alert_type,
            old_price, new_price, change_percent, source,
            datetime.now().isoformat()
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def get_records(
        self,
        product_name: str = None,
        alert_type: str = None,
        start_date: str = None,
        end_date: str = None,
        limit: int = 100,
        offset: int = 0,
        acknowledged: bool = None
    ) -> List[AlertRecord]:
        """查询告警记录"""
        query = "SELECT * FROM alert_history WHERE 1=1"
        params = []
        
        if product_name:
            query += " AND product_name LIKE ?"
            params.append(f"%{product_name}%")
        
        if alert_type:
            query += " AND alert_type = ?"
            params.append(alert_type)
        
        if start_date:
            query += " AND timestamp >= ?"
            params.append(start_date)
        
        if end_date:
            query += " AND timestamp <= ?"
            params.append(end_date)
        
        if acknowledged is not None:
            query += " AND acknowledged = ?"
            params.append(1 if acknowledged else 0)
        
        query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor = self.conn.execute(query, params)
        
        records = []
        for row in cursor.fetchall():
            records.append(AlertRecord(
                id=row[0],
                rule_id=row[1],
                product_name=row[2],
                brand=row[3] or "",
                alert_type=row[4],
                old_price=row[5] or 0,
                new_price=row[6] or 0,
                change_percent=row[7] or 0,
                source=row[8] or "",
                timestamp=row[9],
                acknowledged=bool(row[10]),
                notes=row[11] or ""
            ))
        
        return records
    
    def acknowledge(self, record_id: int, notes: str = ""):
        """确认告警"""
        self.conn.execute("""
            UPDATE alert_history SET acknowledged = 1, notes = ?
            WHERE id = ?
        """, (notes, record_id))
        self.conn.commit()
    
    def get_stats(
        self,
        days: int = 30,
        product_name: str = None
    ) -> Dict:
        """获取统计信息"""
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 基本统计
        cursor = self.conn.execute("""
            SELECT 
                COUNT(*) as total,
                SUM(CASE WHEN acknowledged = 1 THEN 1 ELSE 0 END) as acknowledged,
                AVG(change_percent) as avg_change
            FROM alert_history
            WHERE timestamp >= ? AND product_name LIKE ?
        """, (start_date, f"%{product_name or ''}%"))
        
        row = cursor.fetchone()
        
        # 按类型统计
        cursor = self.conn.execute("""
            SELECT alert_type, COUNT(*) as count
            FROM alert_history
            WHERE timestamp >= ?
            GROUP BY alert_type
        """, (start_date,))
        
        by_type = {row[0]: row[1] for row in cursor.fetchall()}
        
        # 按产品统计
        cursor = self.conn.execute("""
            SELECT product_name, COUNT(*) as count
            FROM alert_history
            WHERE timestamp >= ?
            GROUP BY product_name
            ORDER BY count DESC
            LIMIT 10
        """, (start_date,))
        
        top_products = [(row[0], row[1]) for row in cursor.fetchall()]
        
        return {
            "total_alerts": row[0] or 0,
            "acknowledged": row[1] or 0,
            "avg_change_percent": row[2] or 0,
            "by_type": by_type,
            "top_products": top_products,
            "period_days": days
        }
    
    def get_price_trend(
        self,
        product_name: str,
        days: int = 30
    ) -> List[Dict]:
        """获取价格趋势（通过告警记录）"""
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor = self.conn.execute("""
            SELECT timestamp, new_price, alert_type
            FROM alert_history
            WHERE product_name LIKE ? AND timestamp >= ?
            ORDER BY timestamp
        """, (f"%{product_name}%", start_date))
        
        return [
            {
                "timestamp": row[0],
                "price": row[1],
                "type": row[2]
            }
            for row in cursor.fetchall()
        ]
    
    def export_csv(self, path: str, days: int = 30):
        """导出为 CSV"""
        import csv
        
        records = self.get_records(limit=10000, days=days)
        
        with open(path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.writer(f)
            
            writer.writerow([
                "时间", "产品", "品牌", "告警类型",
                "原价", "新价", "变化%", "来源", "已确认"
            ])
            
            for r in records:
                writer.writerow([
                    r.timestamp[:16],
                    r.product_name,
                    r.brand,
                    r.alert_type,
                    r.old_price,
                    r.new_price,
                    f"{r.change_percent:.1f}%",
                    r.source,
                    "是" if r.acknowledged else "否"
                ])
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# 便捷函数
def get_history(
    product_name: str = None,
    days: int = 30
) -> List[AlertRecord]:
    """快速查询"""
    history = AlertHistory()
    start = (datetime.now() - timedelta(days=days)).isoformat()
    return history.get_records(product_name=product_name, start_date=start)


def get_stats(days: int = 30) -> Dict:
    """快速统计"""
    history = AlertHistory()
    return history.get_stats(days=days)
