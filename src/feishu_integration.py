"""
飞书通知集成
将询价结果和告警推送到飞书
"""

import os
import requests
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class FeishuConfig:
    """飞书配置"""
    webhook_url: str = ""
    app_id: str = ""
    app_secret: str = ""
    bot_name: str = "询价机器人"


class FeishuNotifier:
    """
    飞书通知器
    支持 webhook 和 企微机器人 两种方式
    """
    
    def __init__(self, config: FeishuConfig = None):
        self.config = config or self._load_config()
        self.access_token = None
        self.token_expires_at = None
    
    def _load_config(self) -> FeishuConfig:
        """从环境变量加载配置"""
        return FeishuConfig(
            webhook_url=os.getenv("FEISHU_WEBHOOK", ""),
            app_id=os.getenv("FEISHU_APP_ID", ""),
            app_secret=os.getenv("FEISHU_APP_SECRET", ""),
        )
    
    def _get_access_token(self) -> str:
        """获取 tenant_access_token"""
        if not self.config.app_id or not self.config.app_secret:
            return ""
        
        # 检查缓存
        if self.access_token and self.token_expires_at:
            if datetime.now() < self.token_expires_at:
                return self.access_token
        
        # 获取新 token
        try:
            resp = requests.post(
                "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": self.config.app_id,
                    "app_secret": self.config.app_secret
                },
                timeout=10
            )
            
            if resp.status_code == 200:
                data = resp.json()
                if data.get("code") == 0:
                    self.access_token = data["tenant_access_token"]
                    # 提前5分钟过期
                    self.token_expires_at = datetime.now().timestamp() + data.get("expire", 7200) - 300
                    return self.access_token
        except Exception as e:
            print(f"获取 access_token 失败: {e}")
        
        return ""
    
    # ==================== Webhook 方式 ====================
    
    def send_webhook_text(self, text: str) -> bool:
        """发送文本消息 (webhook)"""
        if not self.config.webhook_url:
            print("⚠ 未配置飞书 Webhook")
            return False
        
        try:
            payload = {
                "msg_type": "text",
                "content": {"text": text}
            }
            
            resp = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=10
            )
            
            return resp.status_code == 200
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    def send_webhook_card(self, title: str, content: str, extra: str = "") -> bool:
        """发送卡片消息 (webhook)"""
        if not self.config.webhook_url:
            print("⚠ 未配置飞书 Webhook")
            return False
        
        try:
            payload = {
                "msg_type": "interactive",
                "card": {
                    "header": {
                        "title": {
                            "tag": "plain_text",
                            "content": title
                        },
                        "template": "blue"
                    },
                    "elements": [
                        {
                            "tag": "div",
                            "text": {
                                "tag": "lark_md",
                                "content": content
                            }
                        }
                    ]
                }
            }
            
            if extra:
                payload["card"]["elements"].append({
                    "tag": "note",
                    "elements": [
                        {"tag": "plain_text", "content": extra}
                    ]
                })
            
            resp = requests.post(
                self.config.webhook_url,
                json=payload,
                timeout=10
            )
            
            return resp.status_code == 200
        except Exception as e:
            print(f"发送失败: {e}")
            return False
    
    # ==================== 询价结果通知 ====================
    
    def send_inquiry_result(self, results: List[Dict], title: str = "询价完成") -> bool:
        """发送询价结果通知"""
        if not self.config.webhook_url:
            return self._print_notification(results, title)
        
        # 构建消息内容
        lines = [f"**{title}**\n"]
        lines.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        lines.append(f"产品数量: {len(results)}")
        lines.append("")
        lines.append("---")
        
        for r in results[:10]:  # 最多显示10个
            name = r.get('product_name', r.get('name', '未知'))
            min_price = r.get('min_price', 0)
            confidence = r.get('overall_confidence', 0)
            
            lines.append(f"• **{name}**")
            if min_price > 0:
                lines.append(f"  💰 ¥{min_price:,.0f}")
            if confidence > 0:
                icon = "🟢" if confidence >= 70 else ("🟡" if confidence >= 50 else "🔴")
                lines.append(f"  {icon} 置信度 {confidence:.0f}%")
            lines.append("")
        
        if len(results) > 10:
            lines.append(f"... 还有 {len(results) - 10} 个产品")
        
        content = "\n".join(lines)
        
        return self.send_webhook_card(title, content)
    
    def send_price_alert(self, product_name: str, old_price: float, new_price: float, source: str = "") -> bool:
        """发送价格告警"""
        if not self.config.webhook_url:
            return self._print_alert(product_name, old_price, new_price, source)
        
        change = (new_price - old_price) / old_price * 100 if old_price > 0 else 0
        
        if change < 0:
            title = f"📉 价格下降: {product_name}"
            template = "green"
            icon = "📉"
        else:
            title = f"📈 价格上涨: {product_name}"
            template = "red"
            icon = "📈"
        
        content = f"""
{icon} **{product_name}**

• 原价: ¥{old_price:,.2f}
• 现价: ¥{new_price:,.2f}
• 变化: {change:+.1f}%
"""
        if source:
            content += f"\n• 来源: {source}"
        
        return self.send_webhook_card(title, content, f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    
    def send_inquiry_summary(self, session_id: str, sent: int, received: int, results: List[Dict]) -> bool:
        """发送询价会话汇总"""
        if not self.config.webhook_url:
            return self._print_summary(session_id, sent, received, results)
        
        total_price = sum(r.get('min_price', 0) for r in results if r.get('min_price', 0) > 0)
        
        content = f"""
**📋 询价会话汇总**

• 会话ID: `{session_id}`
• 发送邮件: {sent} 封
• 收到回复: {received} 封
• 产品数量: {len(results)}
• 预计总价: ¥{total_price:,.2f}

**询价结果:**
"""
        
        for r in results[:5]:
            name = r.get('product_name', '未知')
            price = r.get('min_price', 0)
            content += f"\n• {name}: ¥{price:,.0f}" if price > 0 else f"\n• {name}: 待报价"
        
        if len(results) > 5:
            content += f"\n\n... 还有 {len(results) - 5} 个产品"
        
        return self.send_webhook_card("📊 询价会话汇总", content)
    
    # ==================== 辅助方法 ====================
    
    def _print_notification(self, results: List[Dict], title: str):
        """打印通知（无飞书配置时）"""
        print(f"\n{'='*50}")
        print(f"  {title}")
        print(f"{'='*50}")
        print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        print(f"产品数量: {len(results)}")
        print()
        
        for r in results[:5]:
            name = r.get('product_name', r.get('name', '未知'))
            min_price = r.get('min_price', 0)
            print(f"• {name}: ¥{min_price:,.0f}" if min_price > 0 else f"• {name}")
        
        if len(results) > 5:
            print(f"... 还有 {len(results) - 5} 个产品")
        
        print(f"{'='*50}\n")
        return True
    
    def _print_alert(self, product_name: str, old_price: float, new_price: float, source: str):
        """打印告警"""
        change = (new_price - old_price) / old_price * 100 if old_price > 0 else 0
        icon = "📉" if change < 0 else "📈"
        
        print(f"\n{icon} 价格告警: {product_name}")
        print(f"   原价: ¥{old_price:,.2f} → 现价: ¥{new_price:,.2f} ({change:+.1f}%)")
        if source:
            print(f"   来源: {source}")
        
        return True
    
    def _print_summary(self, session_id: str, sent: int, received: int, results: List[Dict]):
        """打印汇总"""
        total_price = sum(r.get('min_price', 0) for r in results if r.get('min_price', 0) > 0)
        
        print(f"\n{'='*50}")
        print(f"  询价会话汇总")
        print(f"{'='*50}")
        print(f"会话ID: {session_id}")
        print(f"发送: {sent} 封 | 收到: {received} 封")
        print(f"产品: {len(results)} | 总价: ¥{total_price:,.2f}")
        print(f"{'='*50}\n")
        
        return True


# 便捷函数
def notify_inquiry_results(results: List[Dict], title: str = "询价完成"):
    """快速发送询价结果通知"""
    notifier = FeishuNotifier()
    return notifier.send_inquiry_result(results, title)
