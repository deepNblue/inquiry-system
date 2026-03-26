#!/usr/bin/env python3
"""
发送询价邮件
向供应商发送项目设备询价
"""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.manufacturer import EmailSender, InquiryEmail


def load_email_content():
    """加载邮件内容"""
    email_path = "output/inquiry_email.txt"
    if os.path.exists(email_path):
        with open(email_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 提取主题（第一行之后的文本）
        lines = content.split('\n')
        subject = f"【项目询价】智能化项目设备询价 - {len([l for l in lines if l.startswith('|')])} 种设备"
        return subject, content
    
    return None, None


def main():
    print("=" * 60)
    print("  发送询价邮件")
    print("=" * 60)
    print()
    
    # 邮件配置
    config = {
        'smtp_host': 'smtp.qq.com',
        'smtp_port': 465,
        'smtp_ssl': True,
        'smtp_user': '13151793@qq.com',
        'smtp_password': 'ezcgckpvpmgcbjce',
        'from_name': '采购部',
    }
    
    # 加载邮件内容
    subject, body = load_email_content()
    
    if not subject:
        print("✗ 未找到邮件内容文件 (output/inquiry_email.txt)")
        return
    
    print(f"主题: {subject}")
    print(f"长度: {len(body)} 字符")
    print()
    
    # 显示收件人选项
    print("【收件人选项】")
    print("-" * 40)
    print("  1. 发送到自己的邮箱 (测试)")
    print("  2. 发送到 contacts.csv 中的联系人")
    print("  0. 取消")
    print()
    
    choice = input("请选择 (0-2): ").strip()
    
    if choice == '0':
        print("已取消")
        return
    
    recipients = []
    
    if choice == '1':
        recipients = [{'email': '13151793@qq.com', 'name': '测试收件人'}]
    elif choice == '2':
        # 从 contacts.csv 加载
        contacts_path = "examples/contacts.csv"
        if os.path.exists(contacts_path):
            import csv
            with open(contacts_path, 'r', encoding='utf-8-sig') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    recipients.append({
                        'email': row.get('email', ''),
                        'name': row.get('name', ''),
                    })
        else:
            print("✗ 未找到联系人文件")
            return
    else:
        print("无效选项")
        return
    
    if not recipients:
        print("✗ 没有收件人")
        return
    
    print()
    print(f"收件人 ({len(recipients)} 个):")
    for r in recipients:
        print(f"  - {r['name']} <{r['email']}>")
    print()
    
    # 确认发送
    confirm = input("确认发送? (y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    # 发送邮件
    print()
    print("正在发送...")
    
    sender = EmailSender(config)
    
    if not sender.connect():
        print("✗ 无法连接邮件服务器")
        return
    
    success = 0
    for r in recipients:
        email = InquiryEmail(
            to_email=r['email'],
            to_name=r['name'],
            subject=subject,
            body=body,
        )
        
        if sender.send(email):
            success += 1
            print(f"  ✓ 已发送: {r['email']}")
        else:
            print(f"  ✗ 发送失败: {r['email']}")
    
    sender.disconnect()
    
    print()
    print("=" * 60)
    print(f"发送完成: {success}/{len(recipients)} 成功")
    print("=" * 60)
    
    if success > 0:
        print()
        print("提示: 收到供应商回复后，运行以下命令提取报价：")
        print("  python src/email_receiver.py")


if __name__ == "__main__":
    main()
