"""
语义搜索模块
基于嵌入向量的产品相似度匹配
支持本地模型和 API 两种方式
"""

import os
import sqlite3
import json
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


class SemanticSearch:
    """
    语义搜索器
    使用嵌入向量进行产品相似度匹配
    """
    
    def __init__(self, db_path: str = "data/embeddings.db"):
        self.db_path = db_path
        self.conn = None
        self.embedder = None
        self._init_db()
        self._init_embedder()
    
    def _init_db(self):
        """初始化数据库"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        
        # 嵌入向量表
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS embeddings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id TEXT UNIQUE,
                product_name TEXT,
                brand TEXT,
                model TEXT,
                category TEXT,
                embedding BLOB,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 创建索引
        self.conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_product_name ON embeddings(product_name)
        """)
        
        self.conn.commit()
    
    def _init_embedder(self):
        """初始化嵌入模型"""
        # 优先使用本地模型
        try:
            from sentence_transformers import SentenceTransformer
            self.embedder = LocalEmbedder()
            print("使用本地嵌入模型")
        except ImportError:
            # 回退到 TF-IDF
            self.embedder = TfidfEmbedder()
            print("使用 TF-IDF 嵌入")
    
    def add_product(
        self,
        product_id: str,
        product_name: str,
        brand: str = "",
        model: str = "",
        category: str = ""
    ):
        """添加产品嵌入"""
        # 生成文本
        text = self._build_text(product_name, brand, model, category)
        
        # 生成嵌入
        embedding = self.embedder.encode(text)
        
        # 存储
        self.conn.execute("""
            INSERT OR REPLACE INTO embeddings 
            (product_id, product_name, brand, model, category, embedding)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (product_id, product_name, brand, model, category, embedding))
        
        self.conn.commit()
    
    def batch_add(self, products: List[Dict]):
        """批量添加"""
        for p in products:
            self.add_product(
                product_id=p.get("id", p.get("name", "")),
                product_name=p.get("name", ""),
                brand=p.get("brand", ""),
                model=p.get("model", ""),
                category=p.get("category", "")
            )
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = 0.5
    ) -> List[Tuple[str, float]]:
        """
        语义搜索
        
        Args:
            query: 查询文本
            top_k: 返回数量
            threshold: 相似度阈值
        
        Returns:
            [(product_id, similarity_score), ...]
        """
        # 生成查询向量
        query_embedding = self.embedder.encode(query)
        
        # 获取所有产品嵌入
        cursor = self.conn.execute("""
            SELECT product_id, embedding FROM embeddings
        """)
        
        results = []
        for row in cursor.fetchall():
            product_id = row[0]
            embedding = row[1]
            
            # 计算相似度
            similarity = self.embedder.similarity(query_embedding, embedding)
            
            if similarity >= threshold:
                results.append((product_id, similarity))
        
        # 排序
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:top_k]
    
    def find_similar(self, product_name: str, top_k: int = 5) -> List[Dict]:
        """查找相似产品"""
        results = self.search(product_name, top_k)
        
        if not results:
            return []
        
        # 获取产品详情
        product_ids = [r[0] for r in results]
        placeholders = ",".join(["?" for _ in product_ids])
        
        cursor = self.conn.execute(f"""
            SELECT product_id, product_name, brand, model, category
            FROM embeddings
            WHERE product_id IN ({placeholders})
        """, product_ids)
        
        product_map = {row[0]: row[1:] for row in cursor.fetchall()}
        
        # 组合结果
        similar = []
        for product_id, score in results:
            if product_id in product_map:
                name, brand, model, category = product_map[product_id]
                similar.append({
                    "product_id": product_id,
                    "product_name": name,
                    "brand": brand,
                    "model": model,
                    "category": category,
                    "similarity": score
                })
        
        return similar
    
    def _build_text(self, name: str, brand: str = "", model: str = "", category: str = "") -> str:
        """构建搜索文本"""
        parts = [name]
        if brand:
            parts.insert(0, brand)
        if model:
            parts.append(model)
        if category:
            parts.append(category)
        return " ".join(parts)
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


class LocalEmbedder:
    """本地嵌入模型"""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name)
        self.dim = self.model.get_sentence_embedding_dimension()
    
    def encode(self, text: str) -> bytes:
        """编码为字节串"""
        embedding = self.model.encode(text)
        return embedding.astype(float).tobytes()
    
    def decode(self, data: bytes) -> List[float]:
        """解码为浮点数列表"""
        import numpy as np
        return np.frombuffer(data, dtype=float).tolist()
    
    def similarity(self, emb1: bytes, emb2: bytes) -> float:
        """计算余弦相似度"""
        import numpy as np
        
        vec1 = np.frombuffer(emb1, dtype=float)
        vec2 = np.frombuffer(emb2, dtype=float)
        
        dot = np.dot(vec1, vec2)
        norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm == 0:
            return 0
        
        return float(dot / norm)


class TfidfEmbedder:
    """TF-IDF 嵌入（无外部依赖）"""
    
    def __init__(self):
        self.vectorizer = None
        self.fitted = False
    
    def _tokenize(self, text: str) -> List[str]:
        """简单分词"""
        import re
        # 简单中文分词
        text = re.sub(r'[^\w\s]', ' ', text)
        words = text.lower().split()
        # 中文单字/双字
        chinese = re.findall(r'[\u4e00-\u9fff]+', text)
        for c in chinese:
            for i in range(len(c) - 1):
                words.append(c[i:i+2])
        return words
    
    def encode(self, text: str) -> bytes:
        """编码为字节串"""
        import numpy as np
        
        words = self._tokenize(text)
        
        if not self.fitted:
            # 简单向量化
            self.vocab = list(set(words))
            self.fitted = True
        
        # 简单词袋
        vec = np.zeros(max(len(self.vocab), 1))
        for i, w in enumerate(self.vocab):
            if w in words:
                vec[i] = words.count(w)
        
        return vec.astype(float).tobytes()
    
    def similarity(self, emb1: bytes, emb2: bytes) -> float:
        """计算相似度"""
        import numpy as np
        
        vec1 = np.frombuffer(emb1, dtype=float)
        vec2 = np.frombuffer(emb2, dtype=float)
        
        dot = np.dot(vec1, vec2)
        norm = np.linalg.norm(vec1) * np.linalg.norm(vec2)
        
        if norm == 0:
            return 0
        
        return float(dot / norm)


# 便捷函数
def create_semantic_search(db_path: str = "data/embeddings.db") -> SemanticSearch:
    """创建语义搜索实例"""
    return SemanticSearch(db_path)
