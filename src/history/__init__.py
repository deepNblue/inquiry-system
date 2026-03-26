"""
历史询价模块
基于 SQLite + 语义匹配查询历史价格
"""

import os
import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import asyncio

try:
    import numpy as np
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_VECTORIZER = True
except ImportError:
    HAS_VECTORIZER = False


@dataclass
class HistoryPrice:
    """历史价格记录"""
    id: int
    product_name: str
    brand: str
    model: str
    price: float
    currency: str
    source: str
    category: str
    specs: str
    timestamp: str
    similarity: float = 0.0  # 与查询的相似度


class HistoryMatcher:
    """历史价格匹配器"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path or "data/history.db"
        self.conn = None
        self._init_db()
        self.vectorizer = None
        if HAS_VECTORIZER:
            self._init_vectorizer()
    
    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # 创建表
        self.conn.execute("""
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
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_name ON price_history(product_name)
        """)
        
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp ON price_history(timestamp)
        """)
        
        self.conn.commit()
    
    def _init_vectorizer(self):
        """初始化向量化器"""
        self.vectorizer = TfidfVectorizer(
            max_features=1000,
            ngram_range=(1, 2),
        )
    
    def add_price_record(
        self,
        product_name: str,
        price: float,
        brand: str = "",
        model: str = "",
        source: str = "",
        source_type: str = "web",
        category: str = "",
        specs: str = "",
        currency: str = "CNY",
        raw_data: Dict = None
    ) -> int:
        """添加价格记录"""
        cursor = self.conn.execute("""
            INSERT INTO price_history 
            (product_name, brand, model, price, currency, source, source_type, category, specs, timestamp, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_name, brand, model, price, currency, source, source_type,
            category, specs, datetime.now().isoformat(),
            json.dumps(raw_data) if raw_data else None
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def batch_add(self, records: List[Dict]) -> int:
        """批量添加记录"""
        count = 0
        for r in records:
            self.add_price_record(
                product_name=r.get("product_name", ""),
                price=r.get("price", 0),
                brand=r.get("brand", ""),
                model=r.get("model", ""),
                source=r.get("source", ""),
                source_type=r.get("source_type", "web"),
                category=r.get("category", ""),
                specs=r.get("specs", ""),
                currency=r.get("currency", "CNY"),
                raw_data=r.get("raw_data"),
            )
            count += 1
        return count
    
    def search_similar(
        self,
        product_name: str,
        brand: str = "",
        model: str = "",
        top_k: int = 5,
        days: int = 90
    ) -> List[HistoryPrice]:
        """搜索相似产品历史价格"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        
        # 先用 SQL 模糊匹配
        query = f"%{product_name}%"
        brand_pattern = f"%{brand}%" if brand else "%"
        
        cursor = self.conn.execute("""
            SELECT id, product_name, brand, model, price, currency, source, category, specs, timestamp
            FROM price_history
            WHERE product_name LIKE ?
              AND brand LIKE ?
              AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (query, brand_pattern, cutoff, top_k * 2))
        
        rows = cursor.fetchall()
        
        if not rows:
            return []
        
        # 如果有向量化器，进行语义匹配
        if HAS_VECTORIZER and len(rows) > 1:
            return self._semantic_search(rows, product_name, brand, top_k)
        else:
            return self._simple_search(rows, top_k)
    
    def _simple_search(self, rows: List, top_k: int) -> List[HistoryPrice]:
        """简单搜索（按时间排序）"""
        results = []
        for row in rows[:top_k]:
            results.append(HistoryPrice(
                id=row[0],
                product_name=row[1],
                brand=row[2] or "",
                model=row[3] or "",
                price=row[4],
                currency=row[5] or "CNY",
                source=row[6] or "",
                category=row[7] or "",
                specs=row[8] or "",
                timestamp=row[9],
                similarity=1.0
            ))
        return results
    
    def _semantic_search(
        self,
        rows: List,
        query: str,
        brand: str,
        top_k: int
    ) -> List[HistoryPrice]:
        """语义搜索"""
        try:
            # 构建文本
            texts = [f"{r[1]} {r[2]} {r[3]}" for r in rows]
            query_text = f"{query} {brand}"
            
            # 向量化
            tfidf_matrix = self.vectorizer.fit_transform(texts + [query_text])
            query_vec = tfidf_matrix[-1]
            doc_vecs = tfidf_matrix[:-1]
            
            # 计算相似度
            similarities = cosine_similarity(query_vec, doc_vecs)[0]
            
            # 排序
            scored = list(zip(rows, similarities))
            scored.sort(key=lambda x: x[1], reverse=True)
            
            results = []
            for row, sim in scored[:top_k]:
                results.append(HistoryPrice(
                    id=row[0],
                    product_name=row[1],
                    brand=row[2] or "",
                    model=row[3] or "",
                    price=row[4],
                    currency=row[5] or "CNY",
                    source=row[6] or "",
                    category=row[7] or "",
                    specs=row[8] or "",
                    timestamp=row[9],
                    similarity=sim
                ))
            return results
            
        except Exception as e:
            print(f"语义搜索失败: {e}")
            return self._simple_search(rows, top_k)
    
    def get_latest_price(
        self,
        product_name: str,
        brand: str = "",
        model: str = ""
    ) -> Optional[HistoryPrice]:
        """获取最新价格"""
        results = self.search_similar(product_name, brand, model, top_k=1)
        return results[0] if results else None
    
    def get_price_trend(
        self,
        product_name: str,
        brand: str = "",
        days: int = 30
    ) -> List[Tuple[str, float]]:
        """获取价格趋势"""
        cutoff = (datetime.now() - timedelta(days=days)).isoformat()
        query = f"%{product_name}%"
        brand_pattern = f"%{brand}%" if brand else "%"
        
        cursor = self.conn.execute("""
            SELECT DATE(timestamp) as date, AVG(price) as avg_price
            FROM price_history
            WHERE product_name LIKE ?
              AND brand LIKE ?
              AND timestamp >= ?
            GROUP BY DATE(timestamp)
            ORDER BY date
        """, (query, brand_pattern, cutoff))
        
        return [(row[0], row[1]) for row in cursor.fetchall()]
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()
