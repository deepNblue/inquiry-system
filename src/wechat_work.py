"""
企业微信集成模块
支持发送消息、应用通知、群聊机器人
"""

import os
import hashlib
import time
import requests
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum


class WeChatMsgType(Enum):
    """消息类型"""
    TEXT = "text"
    MARKDOWN = "markdown"
    IMAGE = "image"
    NEWS = "news"
    TEMPLATE_CARD = "template_card"


@dataclass
class WeChatConfig:
    """企业微信配置"""
    corp_id: str = ""
    corp_secret: str = ""
    agent_id: str = ""
    # 或使用 Webhook
    webhook_url: str = ""
    # 或使用测试号
    app_id: str = ""
    app_secret: str = ""


class WeChatClient:
    """
    企业微信客户端
    支持多种发送方式
    """
    
    # API 地址
    API_BASE = "https://qyapi.weixin.qq.com"
    
    def __init__(self, config: WeChatConfig):
        self.config = config
        self.access_token = None
        self.token_expires_at = 0
    
    def _get_access_token(self) -> Optional[str]:
        """获取 Access Token"""
        # 检查缓存
        if self.access_token and time.time() < self.token_expires_at:
            return self.access_token
        
        if not self.config.corp_id or not self.config.corp_secret:
            return None
        
        url = f"{self.API_BASE}/cgi-bin/gettoken"
        params = {
            "corpid": self.config.corp_id,
            "corpsecret": self.config.corp_secret
        }
        
        try:
            resp = requests.get(url, params=params, timeout=10)
            data = resp.json()
            
            if data.get("errcode") == 0:
                self.access_token = data["access_token"]
                self.token_expires_at = time.time() + data.get("expires_in", 7200) - 300
                return self.access_token
            
        except Exception as e:
            print(f"获取 access_token 失败: {e}")
        
        return None
    
    def send_text(self, content: str, to_user: str = "@all", to_party: str = "", to_tag: str = "") -> bool:
        """发送文本消息"""
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"{self.API_BASE}/cgi-bin/message/send"
        params = {"access_token": token}
        
        payload = {
            "touser": to_user,
            "toparty": to_party,
            "totag": to_tag,
            "msgtype": "text",
            "agentid": self.config.agent_id,
            "text": {"content": content}
        }
        
        try:
            resp = requests.post(url, params=params, json=payload, timeout=10)
            data = resp.json()
            
            return data.get("errcode") == 0
            
        except Exception as e:
            print(f"发送消息失败: {e}")
            return False
    
    def send_markdown(self, content: str, to_user: str = "@all") -> bool:
        """发送 Markdown 消息"""
        token = self._get_access_token()
        if not token:
            return False
        
        url = f"{self.API_BASE}/cgi-bin/message/send"
        params = {"access_token": token}
        
        payload = {
            "touser": to_user,
            "msgtype": "markdown",
            "agentid": self.config.agent_id,
            "markdown": {"content": content}
        }
        
        try:
            resp = requests.post(url, params=params, json=payload, timeout=10)
            data = resp.json()
            
            return data.get("errcode") == 0
            
        except Exception as e:
            print(f"发送 Markdown 失败: {e}")
            return False
    
    def send_inquiry_notification(self, results: List[Dict], title: str = "询价报告") -> bool:
        """发送询价结果通知"""
        # 格式化为 Markdown
        lines = [
            f"### {title}",
            f"时间: {time.strftime('%Y-%m-%d %H:%M')}",
            "",
        ]
        
        for r in results[:10]:  # 限制10条
            name = r.get("product_name", "未知")
            price = r.get("min_price", 0)
            source = r.get("recommended_source", "")
            
            if price > 0:
                lines.append(f"**{name}**")
                lines.append(f"- 价格: ¥{price:,.2f}")
                if source:
                    lines.append(f"- 来源: {source}")
            else:
                lines.append(f"**{name}** - 待报价")
            
            lines.append("")
        
        if len(results) > 10:
            lines.append(f"_...还有 {len(results) - 10} 个产品_")
        
        content = "\n".join(lines)
        return self.send_markdown(content)


class WeChatRobot:
    """
    企业微信群机器人
    简单 Webhook 方式
    """
    
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url
    
    def send_text(self, content: str) -> bool:
        """发送文本"""
        payload = {
            "msgtype": "text",
            "text": {"content": content}
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    def send_markdown(self, content: str) -> bool:
        """发送 Markdown（支持部分语法）"""
        payload = {
            "msgtype": "markdown",
            "markdown": {"content": content}
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    def send_inquiry_results(self, results: List[Dict]) -> bool:
        """发送询价结果"""
        lines = [
            "## 询价报告",
            "",
        ]
        
        for r in results[:5]:
            name = r.get("product_name", "")[:20]
            price = r.get("min_price", 0)
            
            if price > 0:
                lines.append(f"**{name}**: ¥{price:,.0f}")
            else:
                lines.append(f"**{name}**: 待报价")
        
        content = "\n".join(lines)
        return self.send_markdown(content)


# 便捷函数
def create_wechat_client(
    corp_id: str = None,
    corp_secret: str = None,
    agent_id: str = None,
    webhook_url: str = None
) -> WeChatClient:
    """创建企业微信客户端"""
    config = WeChatConfig(
        corp_id=corp_id or os.getenv("WECHAT_CORP_ID", ""),
        corp_secret=corp_secret or os.getenv("WECHAT_CORP_SECRET", ""),
        agent_id=agent_id or os.getenv("WECHAT_AGENT_ID", ""),
        webhook_url=webhook_url or os.getenv("WECHAT_WEBHOOK_URL", ""),
    )
    return WeChatClient(config)


def create_robot(webhook_url: str = None) -> WeChatRobot:
    """创建群机器人"""
    url = webhook_url or os.getenv("WECHAT_ROBOT_WEBHOOK", "")
    return WeChatRobot(url)
