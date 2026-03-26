#!/usr/bin/env python3
"""
自动询价系统 - CLI 管理工具
告警规则管理、定时任务控制、系统状态查看
"""

import os
import sys
import asyncio
import argparse
import json
from pathlib import Path
from typing import List, Dict, Optional

# 添加 src 目录到路径
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.webhook_alert import AlertManager, AlertRule, AlertType


class InquiryCLI:
    """询价系统 CLI 管理工具"""
    
    def __init__(self):
        self.alert_manager = AlertManager()
    
    # ============ 规则管理 ============
    
    def list_rules(self):
        """列出所有告警规则"""
        rules = self.alert_manager.list_rules()
        
        if not rules:
            print("暂无告警规则")
            return
        
        print(f"\n{'='*60}")
        print(f"共 {len(rules)} 条告警规则")
        print(f"{'='*60}")
        
        for r in rules:
            status = "✓" if r.enabled else "✗"
            print(f"\n[{status}] {r.product_name}")
            print(f"   品牌: {r.brand or '-'}")
            print(f"   型号: {r.model or '-'}")
            print(f"   最低价: {r.min_price if r.min_price > 0 else '-'}")
            print(f"   变化阈值: {r.change_threshold*100:.0f}%")
            print(f"   冷却期: {r.alert_cooldown_hours}h")
            print(f"   Webhook: {r.webhook_url[:50]}..." if len(r.webhook_url) > 50 else f"   Webhook: {r.webhook_url or '-'}")
    
    def add_rule(
        self,
        product: str,
        brand: str = "",
        webhook: str = "",
        min_price: float = 0,
        max_price: float = 0,
        change_threshold: float = 0.05
    ):
        """添加告警规则"""
        rule = AlertRule(
            id="",
            product_name=product,
            brand=brand,
            webhook_url=webhook,
            min_price=min_price,
            max_price=max_price,
            change_threshold=change_threshold
        )
        
        rule_id = self.alert_manager.add_rule(rule)
        print(f"✓ 规则已添加: {rule_id}")
    
    def remove_rule(self, rule_id: str):
        """删除告警规则"""
        if rule_id not in [r.id for r in self.alert_manager.list_rules()]:
            print(f"✗ 规则不存在: {rule_id}")
            return
        
        self.alert_manager.remove_rule(rule_id)
        print(f"✓ 规则已删除: {rule_id}")
    
    def enable_rule(self, rule_id: str, enabled: bool = True):
        """启用/禁用规则"""
        rules = {r.id: r for r in self.alert_manager.list_rules()}
        
        if rule_id not in rules:
            print(f"✗ 规则不存在: {rule_id}")
            return
        
        rules[rule_id].enabled = enabled
        self.alert_manager._save_rules()
        status = "启用" if enabled else "禁用"
        print(f"✓ 规则已{status}: {rule_id}")
    
    # ============ 监控命令 ============
    
    def check_now(self, product: str = None):
        """立即检查"""
        print("\n开始价格检查...")
        
        if product:
            print(f"检查: {product}")
            # TODO: 实现单产品检查
        else:
            rules = self.alert_manager.list_rules()
            print(f"检查 {len(rules)} 个产品...")
            
            # TODO: 批量检查
    
    # ============ 告警历史 ============
    
    def show_alerts(self, limit: int = 20):
        """显示告警历史"""
        alerts = self.alert_manager.alerts[-limit:]
        
        if not alerts:
            print("暂无告警记录")
            return
        
        print(f"\n{'='*60}")
        print(f"最近 {len(alerts)} 条告警")
        print(f"{'='*60}")
        
        for a in alerts:
            emoji = {
                AlertType.PRICE_DROP: "📉",
                AlertType.PRICE_RISE: "📈",
                AlertType.THRESHOLD_EXCEED: "⚠️",
                AlertType.NEW_PRICE: "🆕"
            }.get(a.alert_type, "📢")
            
            print(f"\n{emoji} {a.product_name}")
            print(f"   类型: {a.alert_type.value}")
            print(f"   变化: ¥{a.old_price:,.0f} → ¥{a.new_price:,.0f} ({a.change_percent:+.1f}%)")
            print(f"   时间: {a.timestamp[:16]}")
    
    # ============ 状态 ============
    
    def status(self):
        """系统状态"""
        rules = self.alert_manager.list_rules()
        enabled = sum(1 for r in rules if r.enabled)
        
        print(f"\n{'='*40}")
        print("  自动询价系统 - 状态")
        print(f"{'='*40}")
        print(f"告警规则: {len(rules)} 条 ({enabled} 启用)")
        print(f"Redis: {'✓' if self.alert_manager.redis_client else '✗ (文件缓存)'}")
        print(f"告警历史: {len(self.alert_manager.alerts)} 条")
        
        # 检查定时任务
        print(f"\n{'-'*40}")
        print("定时任务:")
        
        # TODO: 列出定时任务
    
    # ============ 导入/导出 ============
    
    def export_rules(self, path: str):
        """导出规则"""
        rules = self.alert_manager.list_rules()
        
        data = {
            "rules": [vars(r) for r in rules],
            "exported_at": __import__('datetime').datetime.now().isoformat()
        }
        
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        
        print(f"✓ 已导出 {len(rules)} 条规则到: {path}")
    
    def import_rules(self, path: str):
        """导入规则"""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        count = 0
        for r_data in data.get("rules", []):
            rule = AlertRule(**r_data)
            rule.id = ""  # 重新生成ID
            self.alert_manager.add_rule(rule)
            count += 1
        
        print(f"✓ 已导入 {count} 条规则")


def main():
    parser = argparse.ArgumentParser(
        description="自动询价系统 CLI 管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有规则
  python cli.py rules list
  
  # 添加规则
  python cli.py rules add "iPhone 15" --brand Apple --webhook https://... --min-price 5000
  
  # 删除规则
  python cli.py rules remove abc123
  
  # 查看告警历史
  python cli.py alerts
  
  # 系统状态
  python cli.py status
  
  # 导出规则
  python cli.py rules export rules.json
  
  # 导入规则
  python cli.py rules import rules.json
"""
    )
    
    subparsers = parser.add_subparsers(dest="command", help="命令")
    
    # 规则管理
    rules_parser = subparsers.add_parser("rules", help="规则管理")
    rules_sub = rules_parser.add_subparsers(dest="subcommand")
    
    rules_sub.add_parser("list", help="列出所有规则")
    rules_sub.add_parser("status", help="系统状态")
    
    add_parser = rules_sub.add_parser("add", help="添加规则")
    add_parser.add_argument("product", help="产品名称")
    add_parser.add_argument("--brand", "-b", default="", help="品牌")
    add_parser.add_argument("--webhook", "-w", default="", help="Webhook URL")
    add_parser.add_argument("--min-price", "-m", type=float, default=0, help="最低价阈值")
    add_parser.add_argument("--max-price", "-M", type=float, default=0, help="最高价阈值")
    add_parser.add_argument("--change", "-c", type=float, default=0.05, help="变化阈值(%%)")
    
    rules_sub.add_parser("remove", help="删除规则").add_argument("rule_id", help="规则ID")
    rules_sub.add_parser("enable", help="启用规则").add_argument("rule_id", help="规则ID")
    rules_sub.add_parser("disable", help="禁用规则").add_argument("rule_id", help="规则ID")
    
    rules_sub.add_parser("export", help="导出规则").add_argument("path", help="导出路径")
    rules_sub.add_parser("import", help="导入规则").add_argument("path", help="导入路径")
    
    # 告警
    alerts_parser = subparsers.add_parser("alerts", help="告警管理")
    alerts_parser.add_argument("--limit", "-n", type=int, default=20, help="显示数量")
    
    # 检查
    check_parser = subparsers.add_parser("check", help="立即检查")
    check_parser.add_argument("product", nargs="?", help="产品名称(可选)")
    
    # 状态
    subparsers.add_parser("status", help="系统状态")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = InquiryCLI()
    
    # 路由
    if args.command == "rules":
        if args.subcommand == "list":
            cli.list_rules()
        elif args.subcommand == "add":
            cli.add_rule(
                args.product,
                brand=args.brand,
                webhook=args.webhook,
                min_price=args.min_price,
                max_price=args.max_price,
                change_threshold=args.change
            )
        elif args.subcommand == "remove":
            cli.remove_rule(args.rule_id)
        elif args.subcommand == "enable":
            cli.enable_rule(args.rule_id, True)
        elif args.subcommand == "disable":
            cli.enable_rule(args.rule_id, False)
        elif args.subcommand == "export":
            cli.export_rules(args.path)
        elif args.subcommand == "import":
            cli.import_rules(args.path)
        else:
            rules_parser.print_help()
    
    elif args.command == "alerts":
        cli.show_alerts(args.limit)
    
    elif args.command == "check":
        cli.check_now(args.product)
    
    elif args.command == "status":
        cli.status()
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
