#!/usr/bin/env python3
"""
快速启动脚本
"""

import os
import sys


def main():
    print("=" * 60)
    print("  自动询价系统 v0.2.0")
    print("=" * 60)
    print()
    
    print("选择启动方式:")
    print("  1. 交互式CLI")
    print("  2. Web UI (Gradio)")
    print("  3. API服务 (FastAPI)")
    print("  4. 生成报告")
    print("  5. 填充演示数据")
    print("  0. 退出")
    print()
    
    choice = input("请选择 (0-5): ").strip()
    
    if choice == "1":
        print("\n启动交互式CLI...")
        os.system("python3 interactive_cli.py")
    
    elif choice == "2":
        print("\n启动 Web UI...")
        print("访问 http://localhost:7860")
        os.system("python3 web_ui.py")
    
    elif choice == "3":
        print("\n启动 API 服务...")
        print("访问 http://localhost:8000/docs")
        os.system("python3 api.py")
    
    elif choice == "4":
        print("\n生成报告...")
        os.system("python3 generate_reports.py")
    
    elif choice == "5":
        print("\n填充演示数据...")
        os.system("python3 seed_demo_data.py")
    
    elif choice == "0":
        print("\n再见!")
    
    else:
        print("\n无效选择")


if __name__ == "__main__":
    main()
