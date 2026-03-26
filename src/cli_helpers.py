"""
CLI 帮助函数
"""

import os
import sys
from datetime import datetime


def print_header(title: str, width: int = 60):
    """打印标题"""
    print()
    print("=" * width)
    print(f"  {title}")
    print("=" * width)
    print()


def print_success(message: str):
    """打印成功信息"""
    print(f"✅ {message}")


def print_error(message: str):
    """打印错误信息"""
    print(f"❌ {message}")


def print_warning(message: str):
    """打印警告信息"""
    print(f"⚠️  {message}")


def print_info(message: str):
    """打印信息"""
    print(f"ℹ️  {message}")


def confirm(message: str) -> bool:
    """确认提示"""
    response = input(f"{message} (y/n): ").strip().lower()
    return response == 'y'


def input_choice(max_choice: int, prompt: str = "请选择") -> int:
    """输入选择"""
    try:
        choice = input(f"{prompt} (0-{max_choice}): ").strip()
        return int(choice) if choice else -1
    except:
        return -1


def input_text(prompt: str, default: str = "") -> str:
    """输入文本"""
    if default:
        value = input(f"{prompt} [{default}]: ").strip()
        return value if value else default
    else:
        return input(f"{prompt}: ").strip()


def print_table(headers: list, rows: list, widths: list = None):
    """打印表格"""
    if not rows:
        print("(无数据)")
        return
    
    # 计算列宽
    if widths is None:
        widths = []
        for i, h in enumerate(headers):
            max_width = len(h)
            for row in rows:
                if i < len(row):
                    max_width = max(max_width, len(str(row[i])))
            widths.append(max_width + 2)
    
    # 打印表头
    header_line = "|" + "|".join(f" {h:<{widths[i]}} " for i, h in enumerate(headers)) + "|"
    separator = "|" + "|".join("-" * (w + 2) for w in widths) + "|"
    
    print(header_line)
    print(separator)
    
    # 打印数据行
    for row in rows:
        data = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        print("|" + "|".join(f" {d:<{widths[i]}} " for i, d in enumerate(data)) + "|")


def print_progress_bar(current: int, total: int, width: int = 40):
    """打印进度条"""
    percent = current / total if total > 0 else 0
    filled = int(width * percent)
    bar = "█" * filled + "░" * (width - filled)
    print(f"\r[{bar}] {current}/{total}", end="", flush=True)
    if current >= total:
        print()


def print_system_info():
    """打印系统信息"""
    print_header("系统信息")
    
    # 数据库信息
    db_path = "data/history.db"
    if os.path.exists(db_path):
        size = os.path.getsize(db_path)
        print(f"📁 数据库: {db_path} ({size / 1024:.1f} KB)")
    else:
        print(f"📁 数据库: 未创建")
    
    # 输出目录
    if os.path.exists("output"):
        files = os.listdir("output")
        print(f"📂 输出文件: {len(files)} 个")
    else:
        print(f"📂 输出文件: 0 个")
    
    # 代码统计
    py_files = []
    for root, dirs, files in os.walk("."):
        # 跳过隐藏目录和输出目录
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['output', 'venv', '__pycache__']]
        for f in files:
            if f.endswith(".py"):
                py_files.append(os.path.join(root, f))
    
    total_lines = 0
    for f in py_files:
        try:
            with open(f, 'r', encoding='utf-8') as fp:
                total_lines += len(fp.readlines())
        except:
            pass
    
    print(f"📊 代码: {len(py_files)} 个文件, {total_lines:,} 行")
    print()


def clear_screen():
    """清屏"""
    os.system('cls' if os.name == 'nt' else 'clear')


def pause():
    """暂停"""
    input("\n按回车继续...")


def format_price(price: float) -> str:
    """格式化价格"""
    if price >= 10000:
        return f"¥{price / 10000:.1f}万"
    return f"¥{price:,.0f}"


def format_timestamp(timestamp: str = None) -> str:
    """格式化时间"""
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%m-%d %H:%M")
        except:
            return timestamp[:10]
    return datetime.now().strftime("%m-%d %H:%M")
