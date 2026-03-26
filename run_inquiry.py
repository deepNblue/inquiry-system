#!/usr/bin/env python3
"""
实际询价测试脚本
使用设备清单向供应商发送询价
"""

import sys
import os
import csv
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.manufacturer import EmailInquiryWorkflow, EmailSender, InquiryEmail
from src.report_generator import ReportGenerator


def load_equipment_list(csv_path: str) -> list:
    """加载设备清单"""
    products = []
    
    with open(csv_path, 'r', encoding='utf-8-sig') as f:
        reader = csv.DictReader(f)
        for row in reader:
            products.append({
                'name': row.get('设备名称', row.get('name', '')),
                'specs': row.get('技术参数', row.get('specs', '')),
                'brand': row.get('品牌', row.get('brand', '')),
                'model': row.get('型号', row.get('model', '')),
                'quantity': int(row.get('数量', row.get('quantity', 1))),
                'unit': row.get('单位', row.get('unit', '台')),
                'notes': row.get('备注', row.get('notes', '')),
            })
    
    return products


def main():
    print("=" * 60)
    print("  实际询价测试")
    print("=" * 60)
    print()
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    # 配置
    config = {
        'smtp_host': 'smtp.qq.com',
        'smtp_port': 465,
        'smtp_ssl': True,
        'smtp_user': '13151793@qq.com',
        'smtp_password': 'ezcgckpvpmgcbjce',
        'from_name': '采购部',
        'company_name': 'XX公司',
        'sender_name': '李经理',
    }
    
    # 加载设备清单
    products = load_equipment_list('examples/equipment_list.csv')
    
    print(f"已加载 {len(products)} 个设备:")
    for i, p in enumerate(products, 1):
        print(f"  {i}. {p['name']} ({p['brand']}) × {p['quantity']} {p['unit']}")
    
    print()
    
    # 创建邮件发送器
    sender = EmailSender(config)
    
    # 测试连接
    if not sender.connect():
        print("✗ 无法连接邮件服务器")
        return
    
    print("✓ 邮件服务器连接成功")
    
    # 生成询价邮件内容
    print()
    print("生成询价邮件...")
    
    # 格式化产品表格
    lines = [
        "| 序号 | 设备名称 | 技术参数 | 品牌 | 型号 | 数量 | 单位 |",
        "|------|----------|----------|------|------|------|------|",
    ]
    for i, p in enumerate(products, 1):
        lines.append(f"| {i} | {p['name']} | {p['specs']} | {p['brand']} | {p['model']} | {p['quantity']} | {p['unit']} |")
    
    product_table = "\n".join(lines)
    
    # 渲染邮件模板
    from src.manufacturer import EmailTemplate
    
    template = EmailTemplate(
        id="inquiry_test",
        name="测试询价",
        subject="【项目询价】智能化项目设备询价 - 10种设备",
        body=f"""您好，

我司正在执行智能化项目，需要采购以下设备，请您提供报价：

{product_table}

报价要求：
1. 含税含运费
2. 品牌正品，行货
3. 供货周期
4. 售后服务

请于 3 个工作日内回复，谢谢！

联系信息：
公司：XX公司
联系人：李经理
电话：138-0000-0000
邮箱：13151793@qq.com

此致
敬礼

李经理
{datetime.now().strftime('%Y-%m-%d')}"""
    )
    
    print()
    print("=" * 60)
    print("  询价邮件预览")
    print("=" * 60)
    print(f"主题: {template.subject}")
    print(f"正文长度: {len(template.body)} 字符")
    print()
    print(template.body[:500] + "...")
    print()
    
    # 确认发送
    print("=" * 60)
    response = input("是否发送询价邮件? (y/n): ")
    
    if response.lower() != 'y':
        print("已取消发送")
        return
    
    # 选择收件人
    # 这里设置为发送到自己进行测试
    recipients = [
        {'email': '13151793@qq.com', 'name': '测试收件人', 'company': '测试公司', 'brand': ''}
    ]
    
    # 逐个发送
    print()
    print("正在发送...")
    
    success = 0
    for r in recipients:
        email = InquiryEmail(
            to_email=r['email'],
            to_name=r['name'],
            subject=template.subject,
            body=template.body,
        )
        
        if sender.send(email):
            success += 1
            print(f"✓ 已发送: {r['email']}")
        else:
            print(f"✗ 发送失败: {r['email']}")
    
    print()
    print(f"发送完成: {success}/{len(recipients)} 成功")
    
    # 生成报告
    print()
    print("生成询价报告...")
    
    # 模拟结果数据（实际需要等待回复）
    results = []
    for p in products:
        results.append({
            'product_name': p['name'],
            'brand': p['brand'],
            'model': p['model'],
            'specs': p['specs'],
            'quantity': p['quantity'],
            'unit': p['unit'],
            'min_price': 0,  # 待报价
            'overall_confidence': 0,
            'sources': [],
        })
    
    # 生成报告
    report_gen = ReportGenerator()
    os.makedirs('output', exist_ok=True)
    
    report_path = f"output/inquiry_{datetime.now().strftime('%Y%m%d_%H%M')}"
    
    # Markdown 报告
    md_content = report_gen.generate(results, '智能化项目设备询价', 'markdown')
    with open(f"{report_path}.md", 'w', encoding='utf-8') as f:
        f.write(md_content)
    
    # HTML 报告
    html_content = report_gen.generate(results, '智能化项目设备询价', 'html')
    with open(f"{report_path}.html", 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"✓ 报告已生成:")
    print(f"  - {report_path}.md")
    print(f"  - {report_path}.html")
    
    sender.disconnect()
    
    print()
    print("=" * 60)
    print("  询价测试完成")
    print("=" * 60)
    print()
    print("后续操作:")
    print("1. 等待供应商回复邮件")
    print("2. 收到回复后，运行收取脚本提取价格")
    print("3. 更新报告中的价格信息")


if __name__ == "__main__":
    main()
