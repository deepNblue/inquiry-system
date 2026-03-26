"""
统一配置管理器
集中管理所有配置
"""

import os
import yaml
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class AppConfig:
    """应用配置"""
    # 邮件
    smtp_host: str = "smtp.qq.com"
    smtp_port: int = 465
    smtp_ssl: bool = True
    smtp_user: str = ""
    smtp_password: str = ""
    imap_host: str = "imap.qq.com"
    imap_port: int = 993
    
    # 飞书
    feishu_webhook: str = ""
    feishu_app_id: str = ""
    feishu_app_secret: str = ""
    
    # 数据库
    db_type: str = "sqlite"
    db_path: str = "data/history.db"
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "inquiry"
    db_user: str = "postgres"
    db_password: str = ""
    
    # Redis
    redis_enabled: bool = False
    redis_url: str = "redis://localhost:6379/0"
    
    # 其他
    sender_name: str = "询价系统"
    company_name: str = "XX公司"
    default_currency: str = "CNY"
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'email': {
                'smtp_host': self.smtp_host,
                'smtp_port': self.smtp_port,
                'smtp_ssl': self.smtp_ssl,
                'smtp_user': self.smtp_user,
                'smtp_password': '***' if self.smtp_password else '',
                'imap_host': self.imap_host,
                'imap_port': self.imap_port,
            },
            'feishu': {
                'webhook': self.feishu_webhook or '(未配置)',
                'app_id': self.feishu_app_id or '(未配置)',
            },
            'database': {
                'type': self.db_type,
                'path': self.db_path,
            },
            'redis': {
                'enabled': self.redis_enabled,
            },
            'system': {
                'sender_name': self.sender_name,
                'company_name': self.company_name,
            }
        }


class ConfigManager:
    """
    配置管理器
    统一管理所有配置
    """
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config = AppConfig()
        self._load()
    
    def _load(self):
        """加载配置"""
        # 1. 先加载默认配置
        default_file = "config.example.yaml"
        if os.path.exists(default_file):
            with open(default_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                self._apply_dict(data)
        
        # 2. 加载用户配置（覆盖默认）
        if os.path.exists(self.config_file):
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
                self._apply_dict(data)
        
        # 3. 从环境变量加载（最高优先级）
        self._load_from_env()
    
    def _apply_dict(self, data: Dict):
        """应用字典配置"""
        # 邮件
        if 'email' in data or 'smtp' in data:
            email = data.get('email', data.get('smtp', {}))
            self.config.smtp_host = email.get('host', self.config.smtp_host)
            self.config.smtp_port = email.get('port', self.config.smtp_port)
            self.config.smtp_ssl = email.get('ssl', self.config.smtp_ssl)
            self.config.smtp_user = email.get('user', self.config.smtp_user)
            self.config.smtp_password = email.get('password', self.config.smtp_password)
        
        if 'imap' in data:
            imap = data['imap']
            self.config.imap_host = imap.get('host', self.config.imap_host)
            self.config.imap_port = imap.get('port', self.config.imap_port)
        
        # 飞书
        if 'feishu' in data:
            feishu = data['feishu']
            self.config.feishu_webhook = feishu.get('webhook', self.config.feishu_webhook)
            self.config.feishu_app_id = feishu.get('app_id', self.config.feishu_app_id)
            self.config.feishu_app_secret = feishu.get('app_secret', self.config.feishu_app_secret)
        
        # 数据库
        if 'database' in data or 'db' in data:
            db = data.get('database', data.get('db', {}))
            self.config.db_type = db.get('type', self.config.db_type)
            self.config.db_path = db.get('path', self.config.db_path)
        
        # 系统
        if 'from' in data:
            self.config.sender_name = data['from'].get('name', self.config.sender_name)
    
    def _load_from_env(self):
        """从环境变量加载"""
        # 邮件
        self.config.smtp_host = os.getenv('SMTP_HOST', self.config.smtp_host)
        self.config.smtp_port = int(os.getenv('SMTP_PORT', self.config.smtp_port))
        self.config.smtp_user = os.getenv('SMTP_USER', self.config.smtp_user)
        self.config.smtp_password = os.getenv('SMTP_PASSWORD', self.config.smtp_password)
        
        self.config.imap_host = os.getenv('IMAP_HOST', self.config.imap_host)
        self.config.imap_port = int(os.getenv('IMAP_PORT', self.config.imap_port))
        
        # 飞书
        self.config.feishu_webhook = os.getenv('FEISHU_WEBHOOK', self.config.feishu_webhook)
        self.config.feishu_app_id = os.getenv('FEISHU_APP_ID', self.config.feishu_app_id)
        self.config.feishu_app_secret = os.getenv('FEISHU_APP_SECRET', self.config.feishu_app_secret)
    
    def save(self, config_file: str = None):
        """保存配置"""
        config_file = config_file or self.config_file
        
        data = {
            'email': {
                'smtp_host': self.config.smtp_host,
                'smtp_port': self.config.smtp_port,
                'smtp_ssl': self.config.smtp_ssl,
                'smtp_user': self.config.smtp_user,
                'smtp_password': self.config.smtp_password,
            },
            'imap': {
                'host': self.config.imap_host,
                'port': self.config.imap_port,
            },
            'feishu': {
                'webhook': self.config.feishu_webhook,
                'app_id': self.config.feishu_app_id,
                'app_secret': self.config.feishu_app_secret,
            },
            'database': {
                'type': self.config.db_type,
                'path': self.config.db_path,
            },
            'from': {
                'name': self.config.sender_name,
                'company': self.config.company_name,
            }
        }
        
        os.makedirs(os.path.dirname(config_file) or '.', exist_ok=True)
        
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, allow_unicode=True, default_flow_style=False)
        
        print(f"✓ 配置已保存: {config_file}")
    
    def get_email_config(self) -> Dict:
        """获取邮件配置"""
        return {
            'smtp_host': self.config.smtp_host,
            'smtp_port': self.config.smtp_port,
            'smtp_ssl': self.config.smtp_ssl,
            'smtp_user': self.config.smtp_user,
            'smtp_password': self.config.smtp_password,
            'imap_host': self.config.imap_host,
            'imap_port': self.config.imap_port,
            'from_name': self.config.sender_name,
        }
    
    def get_feishu_config(self) -> Dict:
        """获取飞书配置"""
        return {
            'webhook_url': self.config.feishu_webhook,
            'app_id': self.config.feishu_app_id,
            'app_secret': self.config.feishu_app_secret,
        }
    
    def show(self):
        """显示配置"""
        print("\n" + "=" * 50)
        print("  系统配置")
        print("=" * 50)
        
        info = self.config.to_dict()
        
        print("\n📧 邮件配置:")
        email = info.get('email', {})
        print(f"   SMTP: {email.get('smtp_host', 'N/A')}:{email.get('smtp_port', 'N/A')}")
        print(f"   用户: {email.get('smtp_user', 'N/A')}")
        print(f"   状态: {'✓ 已配置' if email.get('smtp_user') else '✗ 未配置'}")
        
        print("\n📱 飞书配置:")
        feishu = info.get('feishu', {})
        webhook = feishu.get('webhook', 'N/A')
        print(f"   Webhook: {'✓ 已配置' if webhook and webhook != '(未配置)' else '✗ 未配置'}")
        
        print("\n🗄️ 数据库:")
        db = info.get('database', {})
        print(f"   类型: {db.get('type', 'sqlite')}")
        print(f"   路径: {db.get('path', 'N/A')}")
        
        print("\n" + "=" * 50)


# 全局实例
_config = None

def get_config() -> ConfigManager:
    """获取配置管理器"""
    global _config
    if _config is None:
        _config = ConfigManager()
    return _config
