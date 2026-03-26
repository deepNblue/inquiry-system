"""
飞书通知模块
询价完成后推送结果到飞书
"""

import requests
from typing import List, Dict, Any
from datetime import datetime


class FeishuNotifier:
    """飞书通知器"""
    
    def __init__(self, webhook_url: str = None, app_id: str = None, app_secret: str = None):
        self.webhook_url = webhook_url
        self.app_id = app_id
        self.app_secret = app_secret
        self.access_token = None
    
    def send_text(self, text: str) -> bool:
        """发送文本消息"""
        if not self.webhook_url:
            print("未配置飞书 Webhook")
            return False
        
        try:
            payload = {
                "msg_type": "text",
                "content": {"text": text}
            }
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"飞书发送失败: {e}")
            return False
    
    def send_inquiry_results(self, results: List[Any], title: str = "询价报告") -> bool:
        """发送询价结果"""
        if not self.webhook_url:
            return False
        
        # 构建消息
        lines = [
            f"📊 **{title}**",
            f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
        ]
        
        for r in results:
            name = getattr(r, "product_name", "未知")
            min_p = getattr(r, "min_price", 0)
            max_p = getattr(r, "max_price", 0)
            source = getattr(r, "recommended_source", "")
            
            if min_p > 0:
                lines.append(f"• **{name}**")
                lines.append(f"  💰 ¥{min_p:,.0f} ~ ¥{max_p:,.0f}")
                if source:
                    lines.append(f"  📍 推荐: {source}")
            else:
                lines.append(f"• **{name}** - 待报价")
            lines.append("")
        
        # 飞书文本有长度限制，需要截断
        text = "\n".join(lines)
        if len(text) > 4000:
            text = text[:4000] + "\n\n...(结果过长已截断)"
        
        return self.send_text(text)
    
    def send_card(self, content: Dict[str, Any]) -> bool:
        """发送卡片消息（富文本）"""
        if not self.webhook_url:
            return False
        
        payload = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "elements": [
                    {
                        "tag": "markdown",
                        "content": content.get("content", "")
                    }
                ]
            }
        }
        
        try:
            resp = requests.post(self.webhook_url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"飞书卡片发送失败: {e}")
            return False


# 便捷函数
def notify_inquiry_complete(results: List, webhook_url: str, title: str = "询价完成"):
    """发送询价完成通知"""
    notifier = FeishuNotifier(webhook_url=webhook_url)
    return notifier.send_inquiry_results(results, title)
