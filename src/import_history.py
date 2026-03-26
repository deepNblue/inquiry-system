"""
历史数据导入工具
支持从 CSV/Excel 批量导入历史价格
"""

import csv
import json
from typing import List, Dict, Optional
from pathlib import Path
from datetime import datetime

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False


class HistoryImporter:
    """历史数据导入器"""
    
    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = db_path
        self.conn = None
        self._init_db()
    
    def _init_db(self):
        """初始化数据库连接"""
        import sqlite3
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
    
    def import_csv(
        self,
        file_path: str,
        mappings: Dict[str, str] = None,
        has_header: bool = True
    ) -> int:
        """
        从 CSV 导入历史数据
        
        Args:
            file_path: CSV 文件路径
            mappings: 字段映射，如 {"产品名称": "product_name", "价格": "price"}
            has_header: 是否有表头
        
        Returns:
            导入记录数
        """
        mappings = mappings or {
            "产品名称": "product_name",
            "品牌": "brand",
            "型号": "model",
            "价格": "price",
            "来源": "source",
            "类别": "category",
            "规格": "specs",
            "日期": "timestamp",
        }
        
        count = 0
        
        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f) if has_header else csv.reader(f)
            
            if has_header:
                rows = list(reader)
            else:
                # 无表头时使用默认字段名
                rows = []
                for row in reader:
                    if len(row) >= 3:
                        rows.append({
                            "product_name": row[0] if len(row) > 0 else "",
                            "price": row[1] if len(row) > 1 else "0",
                            "source": row[2] if len(row) > 2 else "",
                        })
            
            for row in rows:
                # 映射字段
                record = {}
                for cn, en in mappings.items():
                    record[en] = row.get(cn, "")
                
                # 处理价格
                price_str = str(record.get("price", "0")).replace(",", "").replace("¥", "")
                try:
                    record["price"] = float(price_str)
                except:
                    record["price"] = 0
                
                # 默认值
                record.setdefault("brand", "")
                record.setdefault("model", "")
                record.setdefault("source", "导入")
                record.setdefault("category", "")
                record.setdefault("specs", "")
                record.setdefault("currency", "CNY")
                record.setdefault("source_type", "import")
                
                # 时间戳
                if not record.get("timestamp"):
                    record["timestamp"] = datetime.now().isoformat()
                
                # 插入数据库
                self._insert_record(record)
                count += 1
        
        return count
    
    def import_excel(self, file_path: str, sheet: int = 0, mappings: Dict = None) -> int:
        """从 Excel 导入"""
        if not HAS_PANDAS:
            raise ImportError("pandas required for Excel import: pip install pandas openpyxl")
        
        mappings = mappings or {
            "产品名称": "product_name",
            "品牌": "brand",
            "型号": "model",
            "价格": "price",
            "来源": "source",
        }
        
        df = pd.read_excel(file_path, sheet_name=sheet)
        
        # 转换并导入
        records = []
        for _, row in df.iterrows():
            record = {}
            for cn, en in mappings.items():
                if cn in df.columns:
                    record[en] = str(row[cn])
                else:
                    record[en] = ""
            
            records.append(record)
        
        # 批量插入
        count = 0
        for r in records:
            price_str = str(r.get("price", "0")).replace(",", "").replace("¥", "")
            try:
                r["price"] = float(price_str)
            except:
                r["price"] = 0
            
            r.setdefault("brand", "")
            r.setdefault("model", "")
            r.setdefault("source", "导入")
            r.setdefault("currency", "CNY")
            r.setdefault("source_type", "import")
            r.setdefault("timestamp", datetime.now().isoformat())
            
            self._insert_record(r)
            count += 1
        
        return count
    
    def import_json(self, file_path: str) -> int:
        """从 JSON 导入"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            records = data
        else:
            records = data.get("records", [])
        
        count = 0
        for r in records:
            r.setdefault("source_type", "import")
            r.setdefault("timestamp", datetime.now().isoformat())
            self._insert_record(r)
            count += 1
        
        return count
    
    def _insert_record(self, record: Dict):
        """插入单条记录"""
        self.conn.execute("""
            INSERT INTO price_history 
            (product_name, brand, model, price, currency, source, source_type, category, specs, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            record.get("product_name", ""),
            record.get("brand", ""),
            record.get("model", ""),
            record.get("price", 0),
            record.get("currency", "CNY"),
            record.get("source", ""),
            record.get("source_type", "import"),
            record.get("category", ""),
            record.get("specs", ""),
            record.get("timestamp", datetime.now().isoformat()),
        ))
        self.conn.commit()
    
    def close(self):
        """关闭连接"""
        if self.conn:
            self.conn.close()


# 命令行工具
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="历史数据导入工具")
    parser.add_argument("-f", "--file", required=True, help="导入文件路径")
    parser.add_argument("-t", "--type", choices=["csv", "excel", "json"], default="csv", help="文件类型")
    parser.add_argument("-d", "--db", default="data/history.db", help="数据库路径")
    
    args = parser.parse_args()
    
    importer = HistoryImporter(args.db)
    
    if args.type == "csv":
        count = importer.import_csv(args.file)
    elif args.type == "excel":
        count = importer.import_excel(args.file)
    else:
        count = importer.import_json(args.file)
    
    print(f"导入完成: {count} 条记录")
    
    importer.close()
