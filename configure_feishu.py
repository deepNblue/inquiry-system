#!/usr/bin/env python3
"""
飞书Webhook配置工具
"""

import os
import sys


def configure_feishu():
    """配置飞书Webhook"""
    
    print("=" * 50)
    print("  飞书Webhook配置")
    print("=" * 50)
    print()
    
    print("获取Webhook URL步骤:")
    print("-" * 50)
    print("1. 打开飞书工作台")
    print("2. 搜索「群机器人」或「自定义机器人」")
    print("3. 添加机器人，类型选择「自定义机器人」")
    print("4. 设置机器人名称，如「询价通知」")
    print("5. 复制WebHook地址")
    print()
    
    webhook_url = input("请输入Webhook URL: ").strip()
    
    if not webhook_url:
        print("✗ 未输入URL")
        return
    
    if not webhook_url.startswith("https://"):
        print("✗ URL格式不正确，应以 https:// 开头")
        return
    
    # 保存到 .env 文件
    env_file = ".env"
    
    # 读取现有配置
    env_vars = {}
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if '=' in line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    env_vars[key] = value
    
    # 更新配置
    env_vars['FEISHU_WEBHOOK'] = webhook_url
    
    # 写入文件
    with open(env_file, 'w') as f:
        for key, value in env_vars.items():
            f.write(f"{key}={value}\n")
    
    print()
    print("✓ Webhook配置已保存")
    print()
    
    # 测试发送
    test = input("是否发送测试消息? (y/n): ").strip().lower()
    
    if test == 'y':
        test_notification(webhook_url)


def test_notification(webhook_url: str):
    """发送测试通知"""
    import requests
    from datetime import datetime
    
    print("\n发送测试消息...")
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "🔔 询价系统测试消息"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"**时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n这是一条来自**自动询价系统**的测试消息。"
                    }
                },
                {
                    "tag": "hr"
                },
                {
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": "如果收到此消息，说明飞书通知配置成功！"}
                    ]
                }
            ]
        }
    }
    
    try:
        resp = requests.post(webhook_url, json=payload, timeout=10)
        
        if resp.status_code == 200:
            print("✓ 测试消息发送成功！")
            print("请检查飞书群是否收到消息。")
        else:
            print(f"✗ 发送失败: {resp.status_code}")
            print(resp.text)
    except Exception as e:
        print(f"✗ 发送失败: {e}")


def show_current_config():
    """显示当前配置"""
    print("=" * 50)
    print("  当前飞书配置")
    print("=" * 50)
    
    webhook = os.getenv("FEISHU_WEBHOOK", "")
    
    if webhook:
        # 隐藏部分URL
        if len(webhook) > 30:
            display = webhook[:30] + "..."
        else:
            display = webhook
        print(f"\nWebhook: ✓ 已配置")
        print(f"URL: {display}")
    else:
        print("\nWebhook: ✗ 未配置")
    
    # 检查.env文件
    if os.path.exists(".env"):
        with open(".env", 'r') as f:
            for line in f:
                if "FEISHU_WEBHOOK" in line:
                    print("\n✓ .env文件中已有配置")
                    break
    else:
        print("\n✗ .env文件不存在")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='飞书Webhook配置工具')
    parser.add_argument('--show', action='store_true', help='显示当前配置')
    parser.add_argument('--test', metavar='URL', help='测试发送消息')
    
    args = parser.parse_args()
    
    if args.show:
        show_current_config()
    elif args.test:
        test_notification(args.test)
    else:
        configure_feishu()


if __name__ == "__main__":
    main()
