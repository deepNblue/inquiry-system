#!/usr/bin/env python3
"""
数据库优化工具
索引优化、查询优化、清理
"""

import os
import sqlite3
from datetime import datetime


class DatabaseOptimizer:
    """数据库优化器"""
    
    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = db_path
        self.conn = None
    
    def connect(self):
        """连接数据库"""
        if os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path)
            print(f"✓ 连接数据库: {self.db_path}")
        else:
            print(f"✗ 数据库不存在: {self.db_path}")
            return False
        return True
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()
    
    def analyze(self):
        """分析数据库"""
        if not self.conn:
            return
        
        print("\n📊 数据库分析")
        print("=" * 50)
        
        # 表大小
        cursor = self.conn.execute("""
            SELECT COUNT(*) FROM price_history
        """)
        count = cursor.fetchone()[0]
        print(f"记录数: {count}")
        
        # 索引信息
        cursor = self.conn.execute("""
            SELECT name, tbl_name FROM sqlite_master 
            WHERE type = 'index' AND tbl_name = 'price_history'
        """)
        indexes = cursor.fetchall()
        print(f"索引数: {len(indexes)}")
        
        for idx_name, tbl_name in indexes:
            print(f"  - {idx_name}")
        
        # 数据库大小
        db_size = os.path.getsize(self.db_path)
        print(f"数据库大小: {db_size / 1024:.1f} KB")
    
    def create_indexes(self):
        """创建索引"""
        if not self.conn:
            return
        
        print("\n📇 创建索引")
        print("=" * 50)
        
        indexes = [
            ("idx_product_name", "product_name"),
            ("idx_brand", "brand"),
            ("idx_model", "model"),
            ("idx_timestamp", "timestamp"),
            ("idx_price", "price"),
        ]
        
        for idx_name, column in indexes:
            try:
                self.conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {idx_name} 
                    ON price_history({column})
                """)
                print(f"✓ {idx_name} on {column}")
            except Exception as e:
                print(f"✗ {idx_name}: {e}")
        
        self.conn.commit()
    
    def vacuum(self):
        """清理数据库"""
        if not self.conn:
            return
        
        print("\n🧹 清理数据库")
        print("=" * 50)
        
        before_size = os.path.getsize(self.db_path)
        
        self.conn.execute("VACUUM")
        
        after_size = os.path.getsize(self.db_path)
        saved = before_size - after_size
        
        print(f"清理前: {before_size / 1024:.1f} KB")
        print(f"清理后: {after_size / 1024:.1f} KB")
        print(f"节省空间: {saved / 1024:.1f} KB")
    
    def show_slow_queries(self):
        """分析慢查询"""
        if not self.conn:
            return
        
        print("\n🐌 查询分析")
        print("=" * 50)
        
        # 检查是否使用了索引
        queries = [
            ("按产品名查询", "EXPLAIN QUERY PLAN SELECT * FROM price_history WHERE product_name = 'test'"),
            ("按品牌查询", "EXPLAIN QUERY PLAN SELECT * FROM price_history WHERE brand = 'test'"),
            ("全表扫描", "EXPLAIN QUERY PLAN SELECT * FROM price_history WHERE price > 1000"),
        ]
        
        for name, query in queries:
            print(f"\n{name}:")
            cursor = self.conn.execute(query)
            for row in cursor:
                print(f"  {row}")
    
    def optimize_all(self):
        """执行所有优化"""
        if not self.connect():
            return
        
        print("=" * 50)
        print("  数据库优化")
        print("=" * 50)
        
        self.analyze()
        self.create_indexes()
        self.vacuum()
        
        self.close()
        
        print("\n✓ 优化完成")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='数据库优化工具')
    parser.add_argument('--db', default='data/history.db', help='数据库路径')
    parser.add_argument('--analyze', action='store_true', help='分析数据库')
    parser.add_argument('--indexes', action='store_true', help='创建索引')
    parser.add_argument('--vacuum', action='store_true', help='清理数据库')
    parser.add_argument('--all', action='store_true', help='执行所有优化')
    
    args = parser.parse_args()
    
    optimizer = DatabaseOptimizer(args.db)
    
    if args.all:
        optimizer.optimize_all()
    else:
        if not optimizer.connect():
            return
        
        if args.analyze:
            optimizer.analyze()
        if args.indexes:
            optimizer.create_indexes()
        if args.vacuum:
            optimizer.vacuum()
        
        if not (args.analyze or args.indexes or args.vacuum):
            optimizer.analyze()
        
        optimizer.close()


if __name__ == "__main__":
    main()
