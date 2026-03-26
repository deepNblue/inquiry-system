#!/bin/bash
# 快速命令脚本

echo "=========================================="
echo "  询价系统 - 快速命令"
echo "=========================================="
echo ""

case "$1" in
  "init")
    echo "初始化系统..."
    python3 seed_demo_data.py
    python3 -m src.db_optimize --all
    echo "✓ 初始化完成"
    ;;
    
  "report")
    echo "生成报告..."
    python3 generate_reports.py
    ;;
    
  "cli")
    echo "启动交互式CLI..."
    python3 interactive_cli.py
    ;;
    
  "test")
    echo "运行测试..."
    python3 tests/test_inquiry.py
    ;;
    
  "stats")
    echo "系统统计..."
    python3 -c "
from src.history import HistoryMatcher
matcher = HistoryMatcher()
conn = matcher.conn
cursor = conn.execute('SELECT COUNT(*) FROM price_history')
count = cursor.fetchone()[0]
print(f'历史记录: {count} 条')
cursor = conn.execute('SELECT COUNT(DISTINCT product_name) FROM price_history')
products = cursor.fetchone()[0]
print(f'产品种类: {products} 种')
matcher.close()
"
    ;;
    
  "export")
    echo "导出数据..."
    python3 -c "
import csv
from src.history import HistoryMatcher

matcher = HistoryMatcher()
conn = matcher.conn
cursor = conn.execute('SELECT product_name, brand, model, price, source, timestamp FROM price_history ORDER BY product_name')

with open('data/export.csv', 'w', newline='', encoding='utf-8-sig') as f:
    writer = csv.writer(f)
    writer.writerow(['产品名', '品牌', '型号', '价格', '来源', '时间'])
    for row in cursor:
        writer.writerow(row)

matcher.close()
print('✓ 已导出到 data/export.csv')
"
    ;;
    
  "db")
    echo "数据库优化..."
    python3 -m src.db_optimize --all
    ;;
    
  "dashboard")
    echo "打开仪表板..."
    python3 src/visualize.py
    ;;
    
  *)
    echo "用法: ./quick_commands.sh <command>"
    echo ""
    echo "可用命令:"
    echo "  init      - 初始化系统"
    echo "  report    - 生成报告"
    echo "  cli       - 交互式CLI"
    echo "  test      - 运行测试"
    echo "  stats     - 系统统计"
    echo "  export    - 导出数据"
    echo "  db        - 数据库优化"
    echo "  dashboard - 生成仪表板"
    ;;
esac
