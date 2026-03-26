"""
厂家询价模块
支持邮件、飞书、微信等多种渠道
"""

import os
import smtplib
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

import requests


@dataclass
class InquiryMessage:
    """询价消息"""
    recipient: str  # 邮箱/手机号/微信号
    recipient_name: str = ""
    subject: str = ""
    body: str = ""
    channel: str = "email"  # email/feishu/wechat
    status: str = "pending"  # pending/sent/failed
    sent_at: str = ""
    error: str = ""


class ManufacturerInquiry:
    """厂家询价器"""
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        self.smtp_server = self.config.get("smtp_server")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_user = self.config.get("smtp_user")
        self.smtp_password = self.config.get("smtp_password")
        self.from_email = self.config.get("from_email", self.smtp_user)
        
        # 飞书配置
        self.feishu_webhook = self.config.get("feishu_webhook")
        self.feishu_app_id = self.config.get("feishu_app_id")
        self.feishu_app_secret = self.config.get("feishu_app_secret")
        
        # 邮件模板
        self._init_templates()
    
    def _init_templates(self):
        """初始化询价模板"""
        self.email_template = """
您好，

我们是 [公司名称]，现需要采购以下产品，烦请提供报价：

{product_list}

规格要求：{specs}
数量：{quantity}
期望交货期：{delivery_time}
付款方式：{payment_terms}

如有疑问，请联系：{contact}

此致
敬礼

[联系人]
[公司名称]
[电话]
"""
    
    def create_inquiry_message(
        self,
        products: List[Dict],
        recipient: str,
        channel: str = "email",
        **kwargs
    ) -> InquiryMessage:
        """创建询价消息"""
        # 构建产品列表
        product_lines = []
        for i, p in enumerate(products, 1):
            line = f"{i}. {p.get('name', '')}"
            if p.get('brand'):
                line += f" ({p['brand']})"
            if p.get('model'):
                line += f" - 型号: {p['model']}"
            if p.get('specs'):
                line += f"\n   规格: {p['specs']}"
            product_lines.append(line)
        
        product_list = "\n".join(product_lines)
        
        # 填充模板
        body = self.email_template.format(
            product_list=product_list,
            specs=kwargs.get("specs", "见上方描述"),
            quantity=kwargs.get("quantity", "待定"),
            delivery_time=kwargs.get("delivery_time", "尽快"),
            payment_terms=kwargs.get("payment_terms", "面议"),
            contact=kwargs.get("contact", ""),
        )
        
        return InquiryMessage(
            recipient=recipient,
            subject=f"产品询价 - {len(products)} 个产品",
            body=body,
            channel=channel,
        )
    
    async def send_inquiry(self, message: InquiryMessage) -> InquiryMessage:
        """发送询价"""
        try:
            if message.channel == "email":
                return await self._send_email(message)
            elif message.channel == "feishu":
                return await self._send_feishu(message)
            elif message.channel == "wechat":
                return await self._send_wechat(message)
            else:
                message.status = "failed"
                message.error = f"Unknown channel: {message.channel}"
                return message
        except Exception as e:
            message.status = "failed"
            message.error = str(e)
            return message
    
    async def _send_email(self, message: InquiryMessage) -> InquiryMessage:
        """发送邮件"""
        if not self.smtp_server:
            message.status = "failed"
            message.error = "SMTP not configured"
            return message
        
        try:
            msg = MIMEMultipart()
            msg["From"] = self.from_email
            msg["To"] = message.recipient
            msg["Subject"] = message.subject
            msg.attach(MIMEText(message.body, "plain", "utf-8"))
            
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(msg)
            
            message.status = "sent"
            message.sent_at = datetime.now().isoformat()
            return message
            
        except Exception as e:
            message.status = "failed"
            message.error = str(e)
            return message
    
    async def _send_feishu(self, message: InquiryMessage) -> InquiryMessage:
        """发送飞书消息"""
        if not self.feishu_webhook:
            message.status = "failed"
            message.error = "Feishu webhook not configured"
            return message
        
        try:
            payload = {
                "msg_type": "text",
                "content": {
                    "text": f"**{message.subject}**\n\n{message.body[:2000]}"
                }
            }
            
            response = requests.post(
                self.feishu_webhook,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                message.status = "sent"
                message.sent_at = datetime.now().isoformat()
            else:
                message.status = "failed"
                message.error = f"HTTP {response.status_code}"
            
            return message
            
        except Exception as e:
            message.status = "failed"
            message.error = str(e)
            return message
    
    async def _send_wechat(self, message: InquiryMessage) -> InquiryMessage:
        """发送微信消息（企业微信）"""
        # TODO: 实现企业微信 API
        message.status = "failed"
        message.error = "WeChat integration not implemented"
        return message
    
    async def batch_send(
        self,
        messages: List[InquiryMessage]
    ) -> List[InquiryMessage]:
        """批量发送"""
        import asyncio
        tasks = [self.send_inquiry(m) for m in messages]
        return await asyncio.gather(*tasks)
    
    def load_manufacturer_contacts(self, path: str) -> List[Dict]:
        """加载厂家联系人"""
        if path.endswith(".json"):
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        elif path.endswith(".csv"):
            import csv
            with open(path, "r", encoding="utf-8") as f:
                return list(csv.DictReader(f))
        else:
            raise ValueError(f"Unsupported file format: {path}")


# 新增模块导出
from .email_workflow import EmailInquiryWorkflow, InquirySession, PriceFromEmail
from .email_sender import EmailSender, EmailTemplate, InquiryEmail, SalesContact, SalesContactManager

__all__ = [
    'ManufacturerInquiry',
    'InquiryMessage',
    'EmailInquiryWorkflow',
    'InquirySession',
    'PriceFromEmail',
    'EmailSender',
    'EmailTemplate',
    'InquiryEmail',
    'SalesContact',
    'SalesContactManager',
]
