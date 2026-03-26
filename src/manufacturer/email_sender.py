"""
邮件发送模块
支持模板、批量发送、自动跟进
"""

import os
import smtplib
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from email.header import Header
import sqlite3


@dataclass
class EmailTemplate:
    """邮件模板"""
    id: str
    name: str
    subject: str
    body: str
    category: str = ""  # 产品类别
    variables: List[str] = field(default_factory=list)  # 可用变量


@dataclass
class InquiryEmail:
    """询价邮件"""
    to_email: str
    to_name: str = ""
    subject: str = ""
    body: str = ""
    template_id: str = ""
    related_products: List[str] = field(default_factory=list)
    inquiry_id: str = ""  # 关联询价单ID
    sent_at: datetime = None
    status: str = "pending"  # pending/sent/failed
    
    def __post_init__(self):
        if self.sent_at is None:
            self.sent_at = datetime.now()


@dataclass
class SalesContact:
    """销售联系人"""
    id: str
    name: str
    email: str
    company: str = ""
    brand: str = ""  # 代理品牌
    category: str = ""  # 产品类别
    phone: str = ""
    notes: str = ""
    response_rate: float = 0  # 回复率
    last_contact: datetime = None


class EmailSender:
    """
    邮件发送器
    支持 SMTP 配置、模板发送、批量询价
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # SMTP 配置
        self.smtp_host = self.config.get("smtp_host", "smtp.gmail.com")
        self.smtp_port = self.config.get("smtp_port", 587)
        self.smtp_ssl = self.config.get("smtp_ssl", False)  # QQ邮箱使用SSL
        self.smtp_user = self.config.get("smtp_user", "")
        self.smtp_password = self.config.get("smtp_password", "")
        self.from_email = self.config.get("from_email", self.smtp_user)
        self.from_name = self.config.get("from_name", "询价系统")
        
        self.server = None
        self._connected = False
        
        # 模板
        self.templates = self._load_default_templates()
    
    def connect(self) -> bool:
        """连接 SMTP 服务器"""
        try:
            if self.smtp_ssl:
                # QQ邮箱使用SSL
                self.server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
            else:
                self.server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                self.server.starttls()
            
            self.server.login(self.smtp_user, self.smtp_password)
            self._connected = True
            print(f"✓ 已连接 SMTP: {self.smtp_host}:{self.smtp_port}")
            return True
        except Exception as e:
            print(f"✗ SMTP 连接失败: {e}")
            return False
    
    def disconnect(self):
        """断开连接"""
        if self.server:
            try:
                self.server.quit()
            except:
                pass
            self._connected = False
    
    def send(self, email: InquiryEmail) -> bool:
        """
        发送邮件
        
        Args:
            email: 询价邮件
        
        Returns:
            是否发送成功
        """
        if not self._connected:
            if not self.connect():
                return False
        
        try:
            msg = MIMEMultipart("alternative")
            
            # QQ邮箱兼容：From只用邮箱地址
            msg["From"] = self.from_email
            msg["To"] = email.to_email if not email.to_name else f"{email.to_name} <{email.to_email}>"
            
            # 使用Header编码Subject
            msg["Subject"] = Header(email.subject, "utf-8").encode()
            
            if email.inquiry_id:
                msg["In-Reply-To"] = email.inquiry_id
            
            # 添加纯文本正文
            msg.attach(MIMEText(email.body, "plain", "utf-8"))
            
            # 添加 HTML 正文（可选）
            html_body = self._plain_to_html(email.body)
            msg.attach(MIMEText(html_body, "html", "utf-8"))
            
            # 发送
            self.server.sendmail(
                self.from_email,
                [email.to_email],
                msg.as_string()
            )
            
            email.status = "sent"
            print(f"✓ 邮件已发送: {email.to_email}")
            return True
            
        except Exception as e:
            email.status = "failed"
            print(f"✗ 发送失败: {e}")
            return False
    
    def send_batch(self, emails: List[InquiryEmail]) -> Dict:
        """
        批量发送
        
        Returns:
            发送结果统计
        """
        if not emails:
            return {"total": 0, "sent": 0, "failed": 0}
        
        if not self._connected:
            self.connect()
        
        results = {"total": len(emails), "sent": 0, "failed": 0}
        
        for email in emails:
            if self.send(email):
                results["sent"] += 1
            else:
                results["failed"] += 1
        
        return results
    
    def _plain_to_html(self, text: str) -> str:
        """简单转换为 HTML"""
        # 转义 HTML 特殊字符
        html = text.replace("&", "&amp;")
        html = html.replace("<", "&lt;")
        html = html.replace(">", "&gt;")
        
        # 换行转 <br>
        html = html.replace("\n", "<br>")
        
        return f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6;">
            <div style="max-width: 600px; margin: 0 auto;">
                {html}
            </div>
        </body>
        </html>
        """
    
    def _load_default_templates(self) -> List[EmailTemplate]:
        """加载默认模板"""
        return [
            EmailTemplate(
                id="inquiry_general",
                name="通用询价",
                subject="【询价】{product_names} - {company_name}",
                body="""您好，

我是 {sender_name}，现需要询价以下产品：

{product_list}

请提供上述产品的报价（含税含运费），谢谢！

{contact_info}

此致
{sender_name}
{datetime}""",
                variables=["product_names", "company_name", "product_list", "sender_name", "contact_info"]
            ),
            EmailTemplate(
                id="inquiry_project",
                name="项目询价",
                subject="【项目询价】{project_name} - {product_count}种设备",
                body="""您好，

我司正在执行 [{project_name}] 项目，需要采购以下设备，请您报价：

{product_table}

报价要求：
1. 含税含运费
2. 品牌正品，行货
3. 供货周期
4. 售后服务

请于 {deadline} 前回复，谢谢！

{contact_info}

此致
{sender_name}
{datetime}""",
                category="项目",
                variables=["project_name", "product_count", "product_table", "deadline", "contact_info", "sender_name"]
            ),
            EmailTemplate(
                id="follow_up",
                name="询价跟进",
                subject="【跟进】之前询价产品报价确认",
                body="""您好，

我司于 {inquiry_date} 向贵司询价的产品，不知是否有报价了？

询价产品：{product_names}

期待您的回复，谢谢！

{contact_info}

此致
{sender_name}
{datetime}""",
                variables=["inquiry_date", "product_names", "contact_info", "sender_name"]
            ),
        ]
    
    def render_template(
        self,
        template_id: str,
        variables: Dict[str, str]
    ) -> InquiryEmail:
        """
        渲染模板
        
        Args:
            template_id: 模板ID
            variables: 变量字典
        
        Returns:
            渲染后的邮件对象
        """
        template = next((t for t in self.templates if t.id == template_id), None)
        if not template:
            raise ValueError(f"模板不存在: {template_id}")
        
        # 渲染主题
        subject = template.subject
        for key, value in variables.items():
            subject = subject.replace(f"{{{key}}}", value)
        
        # 渲染正文
        body = template.body
        for key, value in variables.items():
            body = body.replace(f"{{{key}}}", value)
        
        # 替换日期
        body = body.replace("{datetime}", datetime.now().strftime("%Y-%m-%d"))
        
        return InquiryEmail(
            to_email=variables.get("to_email", ""),
            to_name=variables.get("to_name", ""),
            subject=subject,
            body=body,
            template_id=template_id,
            related_products=variables.get("products", [])
        )


class SalesContactManager:
    """
    销售联系人管理器
    """
    
    def __init__(self, db_path: str = "data/sales_contacts.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT NOT NULL,
                company TEXT,
                brand TEXT,
                category TEXT,
                phone TEXT,
                notes TEXT,
                response_rate REAL DEFAULT 0,
                last_contact TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_brand ON contacts(brand)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_category ON contacts(category)
        """)
        conn.commit()
        conn.close()
    
    def add(self, contact: SalesContact) -> str:
        """添加联系人"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO contacts (id, name, email, company, brand, category, phone, notes, response_rate, last_contact)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            contact.id, contact.name, contact.email, contact.company,
            contact.brand, contact.category, contact.phone, contact.notes,
            contact.response_rate,
            contact.last_contact.isoformat() if contact.last_contact else None
        ))
        conn.commit()
        conn.close()
        return contact.id
    
    def find_by_brand(self, brand: str) -> List[SalesContact]:
        """按品牌查找联系人"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM contacts WHERE brand LIKE ?",
            (f"%{brand}%",)
        )
        contacts = [self._row_to_contact(row) for row in cursor.fetchall()]
        conn.close()
        return contacts
    
    def find_by_category(self, category: str) -> List[SalesContact]:
        """按类别查找联系人"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute(
            "SELECT * FROM contacts WHERE category LIKE ?",
            (f"%{category}%",)
        )
        contacts = [self._row_to_contact(row) for row in cursor.fetchall()]
        conn.close()
        return contacts
    
    def update_last_contact(self, contact_id: str):
        """更新最后联系时间"""
        conn = sqlite3.connect(self.db_path)
        conn.execute(
            "UPDATE contacts SET last_contact = ? WHERE id = ?",
            (datetime.now().isoformat(), contact_id)
        )
        conn.commit()
        conn.close()
    
    def _row_to_contact(self, row) -> SalesContact:
        """行转联系人对象"""
        return SalesContact(
            id=row[0],
            name=row[1],
            email=row[2],
            company=row[3] or "",
            brand=row[4] or "",
            category=row[5] or "",
            phone=row[6] or "",
            notes=row[7] or "",
            response_rate=row[8] or 0,
            last_contact=datetime.fromisoformat(row[9]) if row[9] else None
        )
