"""
邮件收取模块
自动收取询价回复、提取价格和分析内容
"""

import os
import re
import email
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.parser import Parser
from email.policy import default
import poplib
import imaplib
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


@dataclass
class EmailInquiry:
    """邮件询价记录"""
    id: str
    subject: str
    from_email: str
    from_name: str
    to_email: str
    body: str
    html_body: str = ""
    received_at: datetime = None
    is_reply: bool = False
    related_inquiry_id: str = ""  # 关联的原始询价
    extracted_prices: List[Dict] = None
    
    def __post_init__(self):
        if self.received_at is None:
            self.received_at = datetime.now()
        if self.extracted_prices is None:
            self.extracted_prices = []


@dataclass
class ExtractedPrice:
    """提取的价格"""
    product_name: str
    price: float
    currency: str = "CNY"
    brand: str = ""
    model: str = ""
    specs: str = ""
    confidence: float = 0  # 0-1 提取置信度
    source_text: str = ""  # 原文


class EmailReceiver:
    """
    邮件收取器
    支持 IMAP 和 POP3 协议
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # IMAP 配置
        self.imap_host = self.config.get("imap_host", "imap.gmail.com")
        self.imap_port = self.config.get("imap_port", 993)
        self.imap_user = self.config.get("imap_user", "")
        self.imap_password = self.config.get("imap_password", "")
        
        # POP3 配置
        self.pop_host = self.config.get("pop_host", "pop.gmail.com")
        self.pop_port = self.config.get("pop_port", 995)
        
        # 标记
        self.seen_ids = set()  # 已处理的邮件ID
    
    def connect_imap(self) -> imaplib.IMAP4_SSL:
        """连接 IMAP"""
        mail = imaplib.IMAP4_SSL(self.imap_host, self.imap_port)
        mail.login(self.imap_user, self.imap_password)
        return mail
    
    def connect_pop3(self) -> poplib.POP3_SSL:
        """连接 POP3"""
        mail = poplib.POP3_SSL(self.pop_host, self.pop_port)
        mail.user(self.imap_user)
        mail.pass_(self.imap_password)
        return mail
    
    def fetch_new_emails(self, folder: str = "INBOX", days: int = 7) -> List[EmailInquiry]:
        """
        获取新邮件
        
        Args:
            folder: 文件夹
            days: 获取最近N天的邮件
        
        Returns:
            邮件列表
        """
        emails = []
        
        try:
            mail = self.connect_imap()
            mail.select(folder)
            
            # 搜索条件：最近N天 + 未读
            date_from = (datetime.now() - timedelta(days=days)).strftime("%d-%b-%Y")
            search_criteria = f'(SINCE {date_from} UNSEEN)'
            
            status, message_ids = mail.search(None, search_criteria)
            
            if status != "OK":
                return emails
            
            for msg_id in message_ids[0].split():
                try:
                    email_data = self._fetch_email(mail, msg_id)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    print(f"获取邮件失败 {msg_id}: {e}")
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"连接失败: {e}")
        
        return emails
    
    def fetch_all_emails(self, folder: str = "INBOX", limit: int = 100) -> List[EmailInquiry]:
        """获取所有邮件（用于测试）"""
        emails = []
        
        try:
            mail = self.connect_imap()
            mail.select(folder)
            
            status, message_ids = mail.search(None, "ALL")
            
            if status != "OK":
                return emails
            
            ids = message_ids[0].split()
            # 只取最近的
            recent_ids = ids[-limit:] if len(ids) > limit else ids
            
            for msg_id in recent_ids:
                try:
                    email_data = self._fetch_email(mail, msg_id)
                    if email_data:
                        emails.append(email_data)
                except Exception as e:
                    print(f"获取邮件失败 {msg_id}: {e}")
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            print(f"连接失败: {e}")
        
        return emails
    
    def _fetch_email(self, mail, msg_id: bytes) -> Optional[EmailInquiry]:
        """获取单封邮件"""
        status, msg_data = mail.fetch(msg_id, "(RFC822)")
        
        if status != "OK":
            return None
        
        raw_email = msg_data[0][1]
        msg = email.message_from_bytes(raw_email, policy=default)
        
        # 解析邮件
        subject = self._decode_header(msg.get("Subject", ""))
        from_addr = msg.get("From", "")
        to_addr = msg.get("To", "")
        
        from_email, from_name = self._parse_address(from_addr)
        
        # 获取正文
        body, html_body = self._get_body(msg)
        
        # 提取邮件ID用于去重
        msg_id_str = msg.get("Message-ID", str(msg_id))
        
        inquiry = EmailInquiry(
            id=msg_id_str,
            subject=subject,
            from_email=from_email,
            from_name=from_name,
            to_email=to_addr,
            body=body,
            html_body=html_body,
            received_at=email.utils.parsedate_to_datetime(msg.get("Date"))
        )
        
        return inquiry
    
    def _decode_header(self, header: str) -> str:
        """解码邮件头"""
        parts = email.header.decode_header(header)
        result = []
        for part, charset in parts:
            if isinstance(part, bytes):
                charset = charset or 'utf-8'
                try:
                    result.append(part.decode(charset, errors='replace'))
                except:
                    result.append(part.decode('utf-8', errors='replace'))
            else:
                result.append(str(part))
        return ''.join(result)
    
    def _parse_address(self, addr: str) -> Tuple[str, str]:
        """解析邮件地址"""
        if not addr:
            return "", ""
        
        # 格式: "名称 <email@example.com>" 或 "email@example.com"
        match = re.match(r'(.+?)\s*<(.+?)>', addr)
        if match:
            return match.group(2), match.group(1).strip()
        return addr.strip(), ""
    
    def _get_body(self, msg) -> Tuple[str, str]:
        """获取邮件正文"""
        body = ""
        html_body = ""
        
        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition"))
                
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        body = part.get_payload(decode=True).decode(charset, errors='replace')
                    except:
                        pass
                
                elif content_type == "text/html" and "attachment" not in content_disposition:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        html_body = part.get_payload(decode=True).decode(charset, errors='replace')
                    except:
                        pass
        else:
            content_type = msg.get_content_type()
            charset = msg.get_content_charset() or 'utf-8'
            try:
                payload = msg.get_payload(decode=True).decode(charset, errors='replace')
                if content_type == "text/html":
                    html_body = payload
                else:
                    body = payload
            except:
                pass
        
        return body, html_body
    
    def extract_prices_from_email(self, email_inquiry: EmailInquiry) -> List[ExtractedPrice]:
        """
        从邮件中提取价格
        
        Args:
            email_inquiry: 邮件对象
        
        Returns:
            提取的价格列表
        """
        prices = []
        
        # 合并文本
        text = email_inquiry.body + "\n" + self._strip_html(email_inquiry.html_body)
        
        # 价格正则模式
        price_patterns = [
            # ¥1,234.56 或 ¥1234
            r'[¥￥]\s*([\d,]+\.?\d*)',
            # 单价：¥1234
            r'单价[：:]\s*[¥￥]?\s*([\d,]+\.?\d*)',
            # 价格：¥1234
            r'价格[：:]\s*[¥￥]?\s*([\d,]+\.?\d*)',
            # 报价：¥1234
            r'报价[：:]\s*[¥￥]?\s*([\d,]+\.?\d*)',
            # 特惠价：¥1234
            r'特惠价[：:]\s*[¥￥]?\s*([\d,]+\.?\d*)',
            # 含税价：¥1234
            r'含税价[：:]\s*[¥￥]?\s*([\d,]+\.?\d*)',
            # 合计：¥1234
            r'合计[：:]\s*[¥￥]?\s*([\d,]+\.?\d*)',
            # 总计：¥1234
            r'总计[：:]\s*[¥￥]?\s*([\d,]+\.?\d*)',
            # (¥1234)
            r'\(([¥￥][\d,]+\.?\d*)\)',
            # RMB: 1234
            r'(?:RMB|rmb|USD|usd)\s*:?\s*([\d,]+\.?\d*)',
        ]
        
        for pattern in price_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price_str = match.group(1).replace(',', '').replace('¥', '').replace('￥', '')
                    price = float(price_str)
                    
                    # 合理范围过滤
                    if 1 < price < 10000000:
                        # 获取上下文用于产品名识别
                        start = max(0, match.start() - 50)
                        end = min(len(text), match.end() + 50)
                        context = text[start:end]
                        
                        # 提取产品名（上下文中的关键词）
                        product_name = self._extract_product_name(context)
                        
                        # 提取品牌
                        brand = self._extract_brand(context)
                        
                        prices.append(ExtractedPrice(
                            product_name=product_name,
                            price=price,
                            brand=brand,
                            confidence=0.8,  # TODO: 根据匹配模式计算
                            source_text=context
                        ))
                except (ValueError, IndexError):
                    pass
        
        # 去重（相同价格）
        seen = set()
        unique_prices = []
        for p in prices:
            key = round(p.price)
            if key not in seen:
                seen.add(key)
                unique_prices.append(p)
        
        return unique_prices
    
    def _strip_html(self, html: str) -> str:
        """去除 HTML 标签"""
        if not html:
            return ""
        
        # 简单去标签
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    
    def _extract_product_name(self, context: str) -> str:
        """从上下文提取产品名"""
        # 去除价格相关词
        text = re.sub(r'[¥￥][\d,]+\.?\d*', '', context)
        text = re.sub(r'(?:单价|价格|报价|特惠价)[：:]?\s*', '', text)
        
        # 取中间有意义的部分
        words = text.split()
        if len(words) >= 3:
            return ' '.join(words[:5])
        return text.strip()
    
    def _extract_brand(self, context: str) -> str:
        """从上下文提取品牌"""
        known_brands = [
            '海康', 'HIKVISION', '大华', 'dahua', '宇视', '天地伟业',
            '华为', 'HUAWEI', '施耐德', 'APC', '艾默生', '海悟',
            '苹果', 'Apple', '联想', 'Lenovo', '戴尔', 'Dell',
            '惠普', 'HP', '思科', 'Cisco', '新华三', 'H3C',
        ]
        
        for brand in known_brands:
            if brand.lower() in context.lower():
                return brand
        
        return ""


# 便捷函数
def receive_and_extract(config: Dict) -> List[ExtractedPrice]:
    """快速收取并提取"""
    receiver = EmailReceiver(config)
    emails = receiver.fetch_new_emails()
    
    all_prices = []
    for email_inquiry in emails:
        prices = receiver.extract_prices_from_email(email_inquiry)
        all_prices.extend(prices)
    
    return all_prices
