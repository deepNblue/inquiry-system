# 邮件询价工作流使用指南

## 概述

邮件询价工作流实现**发送→收取→提取→汇总**的完整闭环，支持：
- 多种邮件模板
- 销售联系人管理
- 自动收取回复
- 价格智能提取

---

## 快速开始

### 1. 配置邮件账号

```yaml
# config.yaml 中添加
email:
  smtp_host: smtp.gmail.com
  smtp_port: 587
  smtp_user: your-email@gmail.com
  smtp_password: your-app-password  # Gmail需要应用专用密码
  
  imap_host: imap.gmail.com
  imap_port: 993
  imap_user: your-email@gmail.com
  imap_password: your-app-password
  
  from_name: 采购部
  company_name: XX有限公司
  sender_name: 张三
```

### 2. 添加销售联系人

```python
from src.manufacturer import SalesContact, EmailInquiryWorkflow

workflow = EmailInquiryWorkflow()

# 添加单个联系人
contact = SalesContact(
    id="001",
    name="李经理",
    email="limanager@supplier.com",
    company="海康威视经销商",
    brand="海康威视",
    category="安防监控",
    phone="13800138001"
)
workflow.add_contact(contact)

# 或从CSV导入
import csv
with open('examples/contacts.csv') as f:
    for row in csv.DictReader(f):
        contact = SalesContact(**row)
        workflow.add_contact(contact)
```

---

## 使用示例

### 发送询价

```python
from src.manufacturer import EmailInquiryWorkflow

workflow = EmailInquiryWorkflow()

# 产品列表
products = [
    {
        "name": "网络摄像机",
        "specs": "1920*1080@30fps",
        "brand": "海康威视",
        "model": "DS-2CD3T86FWDV2-I3S",
        "quantity": 10,
        "unit": "台"
    },
    {
        "name": "硬盘录像机",
        "specs": "32路NVR",
        "brand": "海康威视",
        "model": "DS-8632N-K8",
        "quantity": 2,
        "unit": "台"
    },
]

# 发送询价
session = workflow.send_inquiry(
    products=products,
    template_id="inquiry_project",  # 项目询价模板
    brand_filter="海康威视"  # 只发送给海康的联系人
)

print(f"发送了 {session.emails_sent} 封询价邮件")
```

### 收取回复

```python
# 收取回复邮件
replies = workflow.receive_replies(session_id=session.id)

print(f"收到 {len(replies)} 封回复")

for reply in replies:
    print(f"来自: {reply.from_name}")
    print(f"价格: {reply.extracted_prices}")
```

### 获取结果

```python
# 获取提取的价格
results = workflow.get_results(session_id=session.id)

for r in results:
    print(f"{r.product_name}: ¥{r.price} (来自 {r.source_name})")
```

---

## 邮件模板

### 通用询价
```
主题: 【询价】{product_names} - {company_name}
```

### 项目询价
```
主题: 【项目询价】{project_name} - {product_count}种设备
正文包含表格格式的产品列表
```

### 跟进询价
```
主题: 【跟进】之前询价产品报价确认
```

---

## 销售联系人管理

| 字段 | 说明 |
|------|------|
| id | 唯一标识 |
| name | 姓名 |
| email | 邮箱 |
| company | 公司 |
| brand | 代理品牌 |
| category | 产品类别 |
| phone | 电话 |
| notes | 备注 |
| response_rate | 回复率 |

---

## 完整工作流示例

```python
from src.manufacturer import EmailInquiryWorkflow

# 初始化
workflow = EmailInquiryWorkflow()

# 产品列表
products = [
    {"name": "网络摄像机", "specs": "1920*1080", "brand": "海康威视", "quantity": 10},
    {"name": "硬盘录像机", "specs": "32路", "brand": "海康威视", "quantity": 2},
]

# 1. 发送询价
print("发送询价...")
session = workflow.send_inquiry(products, brand_filter="海康威视")

# 2. 等待一段时间后收取回复
# replies = workflow.receive_replies(session.id)

# 3. 获取结果
results = workflow.get_results(session.id)

# 4. 生成报告
print("\n询价结果:")
for r in results:
    print(f"  {r.product_name}: ¥{r.price:,.0f} (置信度 {r.confidence:.0%})")
```

---

## 注意事项

1. **Gmail 需要应用专用密码**
   - 开启两步验证后生成
   - 设置 → 安全性 → 应用专用密码

2. **邮件频率控制**
   - 建议每次发送间隔 2-3 秒
   - 每天发送不超过 100 封

3. **价格提取准确度**
   - 邮件格式越规范，提取越准确
   - 建议使用表格格式的报价单
