#!/usr/bin/env python3
"""
邮件配置测试脚本
使用 QQ 邮箱测试发送功能
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.manufacturer import EmailSender, InquiryEmail


def test_smtp_connection():
    """测试 SMTP 连接"""
    print("=" * 50)
    print("测试 SMTP 连接 (QQ邮箱)")
    print("=" * 50)
    
    sender = EmailSender({
        "smtp_host": "smtp.qq.com",
        "smtp_port": 465,
        "smtp_user": "13151793@qq.com",
        "smtp_password": "ezcgckpvpmgcbjce",
        "from_name": "自动询价系统",
    })
    
    print(f"\n配置:")
    print(f"  SMTP: {sender.smtp_host}:{sender.smtp_port}")
    print(f"  用户: {sender.smtp_user}")
    
    print("\n尝试连接...")
    
    try:
        import smtplib
        server = smtplib.SMTP_SSL(sender.smtp_host, sender.smtp_port)
        server.login(sender.smtp_user, sender.smtp_password)
        server.quit()
        print("✓ SMTP 连接成功!")
        return True
    except Exception as e:
        print(f"✗ SMTP 连接失败: {e}")
        return False


def test_send_sample():
    """发送测试邮件"""
    print("\n" + "=" * 50)
    print("发送测试邮件")
    print("=" * 50)
    
    sender = EmailSender({
        "smtp_host": "smtp.qq.com",
        "smtp_port": 465,
        "smtp_user": "13151793@qq.com",
        "smtp_password": "ezcgckpvpmgcbjce",
        "from_name": "自动询价系统",
    })
    
    # 创建测试邮件（发送到发件人自己）
    email = InquiryEmail(
        to_email="13151793@qq.com",
        to_name="测试",
        subject="【询价系统测试】这是一封测试邮件",
        body="""
您好，

这是一封来自自动询价系统的测试邮件。

如果收到这封邮件，说明邮件发送功能正常！

系统信息:
- 发送时间: {time}
- 发送者: 13151793@qq.com

此致
自动询价系统
""".format(time=__import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M"))
    )
    
    print(f"\n邮件信息:")
    print(f"  收件人: {email.to_email}")
    print(f"  主题: {email.subject}")
    
    print("\n发送中...")
    
    if sender.connect():
        if sender.send(email):
            print("✓ 测试邮件发送成功!")
            return True
        else:
            print("✗ 发送失败")
            return False
    else:
        print("✗ 无法连接 SMTP 服务器")
        return False


def test_imap_connection():
    """测试 IMAP 连接"""
    print("\n" + "=" * 50)
    print("测试 IMAP 连接 (QQ邮箱)")
    print("=" * 50)
    
    try:
        import imaplib
        
        print(f"\n配置:")
        print(f"  IMAP: imap.qq.com:993")
        print(f"  用户: 13151793@qq.com")
        
        print("\n尝试连接...")
        
        mail = imaplib.IMAP4_SSL("imap.qq.com", 993)
        mail.login("13151793@qq.com", "ezcgckpvpmgcbjce")
        
        # 列出文件夹
        status, folders = mail.list()
        print(f"✓ IMAP 连接成功!")
        print(f"  文件夹数量: {len(folders)}")
        
        # 检查收件箱
        mail.select("INBOX")
        status, count = mail.search(None, "ALL")
        if status == "OK":
            ids = count[0].split()
            print(f"  收件箱邮件数: {len(ids)}")
        
        mail.logout()
        return True
        
    except Exception as e:
        print(f"✗ IMAP 连接失败: {e}")
        return False


if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("  邮件配置测试工具")
    print("=" * 50)
    
    results = []
    
    # 测试 SMTP
    results.append(("SMTP 连接", test_smtp_connection()))
    
    # 测试 IMAP
    results.append(("IMAP 连接", test_imap_connection()))
    
    # 测试发送（可选，需要用户确认）
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        print(f"  {name}: {status}")
    
    # 如果都通过，询问是否发送测试邮件
    if all(r[1] for r in results):
        print("\n所有连接测试通过!")
        response = input("\n是否发送测试邮件到 13151793@qq.com? (y/n): ")
        if response.lower() == 'y':
            test_send_sample()
        else:
            print("跳过发送测试")
    else:
        print("\n部分测试失败，请检查配置")
    
    print("\n" + "=" * 50)
