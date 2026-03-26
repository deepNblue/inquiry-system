"""
增强版历史询价策略
- 智能相似度匹配
- 冷启动降级
- 时效性加权
"""

import os
import sqlite3
import json
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from collections import defaultdict

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
    currency: str = "CNY"
    source: str = ""
    category: str = ""
    specs: str = ""
    timestamp: str = ""
    similarity: float = 0.0
    match_type: str = "exact"  # exact, fuzzy, fallback


@dataclass
class SearchOptions:
    """搜索选项"""
    min_similarity: float = 0.5      # 最低相似度阈值
    days: int = 90                   # 时间窗口
    top_k: int = 5                   # 返回数量
    brand_weight: float = 1.5        # 品牌匹配权重
    recency_weight: float = 0.3       # 时效性权重
    fallback_enabled: bool = True     # 冷启动降级


class EnhancedHistoryMatcher:
    """增强版历史价格匹配器"""
    
    def __init__(self, db_path: str = None, options: SearchOptions = None):
        self.db_path = db_path or "data/history.db"
        self.options = options or SearchOptions()
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
        
        # 创建索引
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_product_name ON price_history(product_name)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_brand ON price_history(brand)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON price_history(timestamp)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_category ON price_history(category)")
        
        self.conn.commit()
    
    def _init_vectorizer(self):
        """初始化向量化器"""
        self.vectorizer = TfidfVectorizer(
            max_features=500,
            ngram_range=(1, 2),
            token_pattern=r'(?u)\b\w+\b',  # 支持中文
        )
    
    def search_similar(
        self,
        product_name: str,
        brand: str = "",
        model: str = "",
        category: str = "",
        options: SearchOptions = None
    ) -> List[HistoryPrice]:
        """
        智能搜索相似产品
        
        搜索策略优先级:
        1. 精确匹配 (品牌+产品名完全相同)
        2. 模糊匹配 (产品名相似)
        3. 品牌降级 (同类品牌)
        4. 品类降级 (同类产品)
        """
        opts = options or self.options
        
        # 1. 精确匹配
        results = self._exact_match(product_name, brand, model, opts)
        if results:
            return self._apply_fusion_score(results, opts)
        
        # 2. 模糊匹配
        results = self._fuzzy_match(product_name, brand, opts)
        if results:
            return self._apply_fusion_score(results, opts, match_type="fuzzy")
        
        # 3. 冷启动降级
        if opts.fallback_enabled:
            results = self._fallback_search(product_name, brand, category, opts)
            if results:
                return self._apply_fusion_score(results, opts, match_type="fallback")
        
        return []
    
    def _exact_match(
        self,
        product_name: str,
        brand: str,
        model: str,
        opts: SearchOptions
    ) -> List[Tuple]:
        """精确匹配"""
        cursor = self.conn.execute("""
            SELECT id, product_name, brand, model, price, currency, source, category, specs, timestamp
            FROM price_history
            WHERE product_name = ?
              AND (? = '' OR brand = ?)
              AND timestamp >= ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (product_name, brand, brand if brand else "%", 
              (datetime.now() - timedelta(days=opts.days)).isoformat(),
              opts.top_k))
        
        return cursor.fetchall()
    
    def _fuzzy_match(
        self,
        product_name: str,
        brand: str,
        opts: SearchOptions
    ) -> List[Tuple]:
        """模糊匹配"""
        # 品牌优先的模糊查询
        brand_pattern = f"%{brand}%" if brand else "%"
        
        cursor = self.conn.execute("""
            SELECT id, product_name, brand, model, price, currency, source, category, specs, timestamp,
                   CASE 
                     WHEN brand = ? THEN 1.0
                     WHEN brand LIKE ? THEN 0.8
                     ELSE 0.5
                   END as brand_score
            FROM price_history
            WHERE (product_name LIKE ? OR product_name LIKE ?)
              AND brand LIKE ?
              AND timestamp >= ?
            ORDER BY brand_score DESC, timestamp DESC
            LIMIT ?
        """, (
            brand, f"%{brand}%",
            f"%{product_name}%", f"%{product_name.replace(' ', '%')}%",
            brand_pattern,
            (datetime.now() - timedelta(days=opts.days)).isoformat(),
            opts.top_k * 2
        ))
        
        return cursor.fetchall()
    
    def _fallback_search(
        self,
        product_name: str,
        brand: str,
        category: str,
        opts: SearchOptions
    ) -> List[Tuple]:
        """冷启动降级搜索"""
        # 策略: 同品牌其他产品 → 同品类产品 → 品类平均
        
        # 尝试同类品牌
        if brand:
            cursor = self.conn.execute("""
                SELECT id, product_name, brand, model, price, currency, source, category, specs, timestamp
                FROM price_history
                WHERE brand = ?
                  AND timestamp >= ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (brand, (datetime.now() - timedelta(days=opts.days)).isoformat(), opts.top_k))
            
            results = cursor.fetchall()
            if results:
                return results
        
        # 同品类
        if category:
            cursor = self.conn.execute("""
                SELECT id, product_name, brand, model, AVG(price) as avg_price, 
                       'CNY' as currency, '品类平均' as source, category, '' as specs,
                       MAX(timestamp) as timestamp
                FROM price_history
                WHERE category = ?
                  AND timestamp >= ?
                GROUP BY product_name
                LIMIT ?
            """, (category, (datetime.now() - timedelta(days=opts.days)).isoformat(), opts.top_k))
            
            results = cursor.fetchall()
            if results:
                return results
        
        # 全品类平均
        cursor = self.conn.execute("""
            SELECT id, product_name, brand, model, AVG(price) as avg_price,
                   'CNY' as currency, '系统平均' as source, category, '' as specs,
                   MAX(timestamp) as timestamp
            FROM price_history
            WHERE timestamp >= ?
            GROUP BY product_name
            ORDER BY MAX(timestamp) DESC
            LIMIT ?
        """, ((datetime.now() - timedelta(days=365)).isoformat(), opts.top_k))
        
        return cursor.fetchall()
    
    def _apply_fusion_score(
        self,
        rows: List[Tuple],
        opts: SearchOptions,
        match_type: str = "exact"
    ) -> List[HistoryPrice]:
        """融合多维度评分"""
        results = []
        now = datetime.now()
        
        for row in rows:
            # 基础相似度
            similarity = 1.0 if match_type == "exact" else 0.6
            
            # 时效性衰减 (越新权重越高)
            try:
                record_time = datetime.fromisoformat(row[9])
                days_ago = (now - record_time).days
                recency_score = max(0, 1 - days_ago * opts.recency_weight / 30)
                similarity = similarity * (1 - opts.recency_weight) + recency_score * opts.recency_weight
            except:
                recency_score = 0.5
            
            # 品牌精确匹配加分
            if len(row) > 2 and row[2]:
                similarity += 0.1
            
            # 过滤低于阈值的
            if similarity >= opts.min_similarity:
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
                    similarity=min(similarity, 1.0),
                    match_type=match_type
                ))
        
        # 按相似度排序
        results.sort(key=lambda x: x.similarity, reverse=True)
        
        return results[:opts.top_k]
    
    def get_category_avg_price(self, category: str = None, brand: str = None) -> Dict:
        """获取品类/品牌平均价格"""
        conditions = []
        params = []
        
        if category:
            conditions.append("category = ?")
            params.append(category)
        
        if brand:
            conditions.append("brand = ?")
            params.append(brand)
        
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        
        cursor = self.conn.execute(f"""
            SELECT 
                AVG(price) as avg_price,
                MIN(price) as min_price,
                MAX(price) as max_price,
                COUNT(*) as record_count
            FROM price_history
            {where}
        """, params)
        
        row = cursor.fetchone()
        return {
            "avg_price": row[0] or 0,
            "min_price": row[1] or 0,
            "max_price": row[2] or 0,
            "record_count": row[3]
        }
    
    def add_price_record(
        self,
        product_name: str,
        price: float,
        brand: str = "",
        model: str = "",
        source: str = "",
        category: str = "",
        specs: str = "",
        raw_data: Dict = None
    ) -> int:
        """添加价格记录"""
        cursor = self.conn.execute("""
            INSERT INTO price_history 
            (product_name, brand, model, price, currency, source, source_type, category, specs, timestamp, raw_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            product_name, brand, model, price, "CNY", source, "web",
            category, specs, datetime.now().isoformat(),
            json.dumps(raw_data) if raw_data else None
        ))
        self.conn.commit()
        return cursor.lastrowid
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        self.close()


# 兼容性：保留原接口
class HistoryMatcher(EnhancedHistoryMatcher):
    """兼容原接口"""
    pass
