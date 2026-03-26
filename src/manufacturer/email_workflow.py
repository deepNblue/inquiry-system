"""
邮件询价工作流
整合发送、收取、关联的完整闭环
"""

import os
import uuid
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import sqlite3

from .email_sender import EmailSender, EmailTemplate, InquiryEmail, SalesContactManager, SalesContact
from ..email_receiver import EmailReceiver, EmailInquiry, ExtractedPrice


@dataclass
class InquirySession:
    """询价会话"""
    id: str
    products: List[Dict]  # 产品列表
    contacts: List[str]   # 发送的联系人邮箱
    emails_sent: int = 0
    emails_received: int = 0
    replies: List[EmailInquiry] = field(default_factory=list)
    extracted_prices: List[ExtractedPrice] = field(default_factory=list)
    status: str = "active"  # active/completed/cancelled
    created_at: datetime = None
    updated_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.updated_at is None:
            self.updated_at = datetime.now()


@dataclass
class PriceFromEmail:
    """从邮件提取的价格"""
    inquiry_session_id: str
    product_name: str
    price: float
    source_email: str
    source_name: str
    received_at: datetime
    confidence: float = 0
    notes: str = ""


class EmailInquiryWorkflow:
    """
    邮件询价工作流
    完整闭环：发送询价 → 收取回复 → 提取价格 → 关联分析
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
        
        # 邮件发送器
        self.sender = EmailSender({
            "smtp_host": self.config.get("smtp_host"),
            "smtp_port": self.config.get("smtp_port", 587),
            "smtp_user": self.config.get("smtp_user"),
            "smtp_password": self.config.get("smtp_password"),
            "from_name": self.config.get("from_name", "询价系统"),
        })
        
        # 邮件收取器
        self.receiver = EmailReceiver({
            "imap_host": self.config.get("imap_host"),
            "imap_port": self.config.get("imap_port", 993),
            "imap_user": self.config.get("imap_user"),
            "imap_password": self.config.get("imap_password"),
        })
        
        # 销售联系人管理
        self.contacts = SalesContactManager(
            self.config.get("contacts_db", "data/sales_contacts.db")
        )
        
        # 会话存储
        self.db_path = self.config.get("workflow_db", "data/email_workflow.db")
        self._init_db()
        
        # 当前会话
        self.current_session: Optional[InquirySession] = None
    
    def _init_db(self):
        """初始化数据库"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        conn = sqlite3.connect(self.db_path)
        
        # 询价会话
        conn.execute("""
            CREATE TABLE IF NOT EXISTS inquiry_sessions (
                id TEXT PRIMARY KEY,
                products TEXT,
                contacts TEXT,
                emails_sent INTEGER DEFAULT 0,
                emails_received INTEGER DEFAULT 0,
                status TEXT DEFAULT 'active',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # 提取的价格
        conn.execute("""
            CREATE TABLE IF NOT EXISTS email_prices (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                product_name TEXT,
                price REAL,
                source_email TEXT,
                source_name TEXT,
                received_at TEXT,
                confidence REAL,
                notes TEXT,
                FOREIGN KEY (session_id) REFERENCES inquiry_sessions(id)
            )
        """)
        
        # 发送记录
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sent_emails (
                id TEXT PRIMARY KEY,
                session_id TEXT,
                to_email TEXT,
                to_name TEXT,
                subject TEXT,
                sent_at TEXT,
                status TEXT,
                FOREIGN KEY (session_id) REFERENCES inquiry_sessions(id)
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_session(self, products: List[Dict]) -> InquirySession:
        """创建询价会话"""
        session_id = str(uuid.uuid4())[:8]
        
        session = InquirySession(
            id=session_id,
            products=products,
            contacts=[]
        )
        
        # 保存到数据库
        self._save_session(session)
        
        self.current_session = session
        return session
    
    def _save_session(self, session: InquirySession):
        """保存会话"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO inquiry_sessions
            (id, products, contacts, emails_sent, emails_received, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            session.id,
            str(session.products),
            str(session.contacts),
            session.emails_sent,
            session.emails_received,
            session.status,
            session.created_at.isoformat(),
            datetime.now().isoformat()
        ))
        conn.commit()
        conn.close()
    
    def send_inquiry(
        self,
        products: List[Dict],
        template_id: str = "inquiry_general",
        recipients: List[str] = None,
        brand_filter: str = None
    ) -> InquirySession:
        """
        发送询价邮件
        
        Args:
            products: 产品列表 [{name, specs, brand, model, quantity}]
            template_id: 邮件模板ID
            recipients: 指定收件人邮箱列表
            brand_filter: 按品牌过滤联系人
        
        Returns:
            询价会话
        """
        # 创建会话
        session = self.create_session(products)
        
        # 确定收件人
        if not recipients:
            recipients = self._find_recipients(products, brand_filter)
        
        if not recipients:
            print("⚠ 未找到收件人")
            return session
        
        # 连接发送服务器
        if not self.sender.connect():
            print("⚠ 无法连接邮件服务器")
            return session
        
        # 生成产品列表文本
        product_list = self._format_products(products)
        product_table = self._format_products_table(products)
        
        # 逐个发送
        for recipient in recipients:
            # 查找联系人信息
            contact = self.contacts.find_by_brand(recipient.get("brand", ""))
            contact_info = self._format_contact(recipient)
            
            # 渲染邮件
            try:
                email = self.sender.render_template(template_id, {
                    "to_email": recipient.get("email", ""),
                    "to_name": recipient.get("name", ""),
                    "product_names": ", ".join([p.get("name", "") for p in products]),
                    "product_list": product_list,
                    "product_table": product_table,
                    "company_name": self.config.get("company_name", "我司"),
                    "sender_name": self.config.get("sender_name", "采购部"),
                    "contact_info": contact_info,
                    "deadline": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%d"),
                })
                
                email.inquiry_id = session.id
                
                if self.sender.send(email):
                    session.emails_sent += 1
                    self._save_sent_email(session.id, email)
                    
                    # 更新联系人
                    if recipient.get("email"):
                        for c in contact:
                            self.contacts.update_last_contact(c.id)
                
            except Exception as e:
                print(f"发送失败: {e}")
        
        session.contacts = [r.get("email", "") for r in recipients]
        self._save_session(session)
        
        return session
    
    def _find_recipients(self, products: List[Dict], brand_filter: str = None) -> List[Dict]:
        """查找收件人"""
        recipients = []
        seen_emails = set()
        
        for product in products:
            brand = product.get("brand", "")
            
            # 按品牌查找联系人
            if brand:
                contacts = self.contacts.find_by_brand(brand)
                for c in contacts:
                    if c.email not in seen_emails:
                        recipients.append({
                            "email": c.email,
                            "name": c.name,
                            "company": c.company,
                            "brand": c.brand
                        })
                        seen_emails.add(c.email)
            
            # 按类别查找
            category = product.get("category", "")
            if category:
                contacts = self.contacts.find_by_category(category)
                for c in contacts:
                    if c.email not in seen_emails:
                        recipients.append({
                            "email": c.email,
                            "name": c.name,
                            "company": c.company,
                            "brand": c.brand
                        })
                        seen_emails.add(c.email)
        
        return recipients
    
    def _format_products(self, products: List[Dict]) -> str:
        """格式化产品列表"""
        lines = []
        for i, p in enumerate(products, 1):
            name = p.get("name", "")
            specs = p.get("specs", "")
            qty = p.get("quantity", 1)
            unit = p.get("unit", "台")
            
            line = f"{i}. {name}"
            if specs:
                line += f" - {specs}"
            line += f" × {qty} {unit}"
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def _format_products_table(self, products: List[Dict]) -> str:
        """格式化产品表格"""
        lines = [
            "| 序号 | 设备名称 | 技术参数 | 品牌 | 型号 | 数量 | 单位 |",
            "|------|----------|----------|------|------|------|------|"
        ]
        
        for i, p in enumerate(products, 1):
            lines.append(f"| {i} | {p.get('name', '')} | {p.get('specs', '')} | {p.get('brand', '')} | {p.get('model', '')} | {p.get('quantity', 1)} | {p.get('unit', '台')} |")
        
        return "\n".join(lines)
    
    def _format_contact(self, contact: Dict) -> str:
        """格式化联系信息"""
        lines = [
            f"公司：{contact.get('company', '')}",
            f"联系人：{contact.get('name', '')}",
            f"电话：{contact.get('phone', '')}",
        ]
        return "\n".join(filter(None, lines))
    
    def _save_sent_email(self, session_id: str, email: InquiryEmail):
        """保存发送记录"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO sent_emails (id, session_id, to_email, to_name, subject, sent_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4())[:8],
            session_id,
            email.to_email,
            email.to_name,
            email.subject,
            email.sent_at.isoformat(),
            email.status
        ))
        conn.commit()
        conn.close()
    
    def receive_replies(self, session_id: str = None) -> List[EmailInquiry]:
        """
        收取回复邮件
        
        Args:
            session_id: 会话ID，不指定则检查所有会话
        
        Returns:
            回复邮件列表
        """
        # 查找相关会话
        if not session_id:
            session_id = self.current_session.id if self.current_session else None
        
        # 收取新邮件
        emails = self.receiver.fetch_new_emails(days=7)
        
        # 过滤询价相关邮件
        relevant_emails = []
        for email in emails:
            # 检查是否与我们的会话相关
            if self._is_relevant_reply(email):
                # 提取价格
                prices = self.receiver.extract_prices_from_email(email)
                
                email.extracted_prices = prices
                relevant_emails.append(email)
                
                # 保存提取的价格
                for price in prices:
                    self._save_extracted_price(session_id, price, email)
        
        return relevant_emails
    
    def _is_relevant_reply(self, email: EmailInquiry) -> bool:
        """判断是否为相关回复"""
        # 检查收件人
        if self.config.get("imap_user"):
            if self.config["imap_user"] not in email.to_email:
                return False
        
        # 检查主题关键字
        keywords = ["报价", "询价", "price", "quote", "quotation", "回复", "RE:", "回复:"]
        for kw in keywords:
            if kw.lower() in email.subject.lower():
                return True
        
        # 检查正文中的价格
        if email.body:
            import re
            if re.search(r'[¥￥]\s*[\d,]+', email.body):
                return True
        
        return False
    
    def _save_extracted_price(
        self,
        session_id: str,
        price: ExtractedPrice,
        email: EmailInquiry
    ):
        """保存提取的价格"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT INTO email_prices
            (id, session_id, product_name, price, source_email, source_name, received_at, confidence, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            str(uuid.uuid4())[:8],
            session_id,
            price.product_name,
            price.price,
            email.from_email,
            email.from_name,
            email.received_at.isoformat(),
            price.confidence,
            price.source_text[:200]
        ))
        conn.commit()
        conn.close()
    
    def get_results(self, session_id: str = None) -> List[PriceFromEmail]:
        """获取询价结果"""
        if not session_id:
            session_id = self.current_session.id if self.current_session else None
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.execute("""
            SELECT * FROM email_prices WHERE session_id = ?
            ORDER BY received_at DESC
        """, (session_id,))
        
        results = []
        for row in cursor.fetchall():
            results.append(PriceFromEmail(
                inquiry_session_id=row[1],
                product_name=row[2],
                price=row[3],
                source_email=row[4],
                source_name=row[5],
                received_at=datetime.fromisoformat(row[6]),
                confidence=row[7] or 0,
                notes=row[8] or ""
            ))
        
        conn.close()
        return results
    
    def run_full_workflow(
        self,
        products: List[Dict],
        recipients: List[Dict] = None,
        brand_filter: str = None
    ) -> InquirySession:
        """
        运行完整工作流
        
        Args:
            products: 产品列表
            recipients: 收件人列表
            brand_filter: 品牌过滤
        
        Returns:
            询价会话
        """
        print("=" * 50)
        print("邮件询价工作流")
        print("=" * 50)
        
        # 1. 发送询价
        print("\n[1/3] 发送询价邮件...")
        session = self.send_inquiry(products, recipients=recipients, brand_filter=brand_filter)
        print(f"已发送 {session.emails_sent} 封询价邮件")
        
        # 2. 等待回复（实际使用时跳过）
        print("\n[2/3] 等待回复...")
        print("(使用 receive_replies() 方法收取回复)")
        
        # 3. 获取结果
        print("\n[3/3] 查看结果...")
        results = self.get_results(session.id)
        print(f"收到 {len(results)} 条报价")
        
        return session
    
    def add_contact(self, contact: SalesContact):
        """添加销售联系人"""
        self.contacts.add(contact)
        print(f"✓ 已添加联系人: {contact.name} ({contact.email})")
