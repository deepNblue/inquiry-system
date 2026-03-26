"""
Webhook 告警模块
支持价格突变告警、阈值监控、Webhook 推送
"""

import os
import asyncio
import hashlib
from typing import List, Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import json

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


class AlertType(Enum):
    """告警类型"""
    PRICE_DROP = "price_drop"  # 价格下降
    PRICE_RISE = "price_rise"  # 价格上升
    THRESHOLD_EXCEED = "threshold_exceed"  # 超过阈值
    NEW_PRICE = "new_price"  # 新价格
    BACK_IN_STOCK = "back_in_stock"  # 有货了


@dataclass
class AlertRule:
    """告警规则"""
    id: str
    product_name: str
    brand: str = ""
    model: str = ""
    
    # 阈值配置
    min_price: float = 0  # 价格低于此值告警
    max_price: float = 0  # 价格高于此值告警
    change_threshold: float = 0.05  # 变化超过 5% 告警
    
    # 通知配置
    webhook_url: str = ""
    channels: List[str] = field(default_factory=lambda: ["webhook"])  # webhook/feishu/email
    
    # 状态
    enabled: bool = True
    last_alert_at: str = ""
    alert_cooldown_hours: int = 24  # 告警冷却期（小时）


@dataclass
class PriceAlert:
    """价格告警"""
    rule_id: str
    product_name: str
    alert_type: AlertType
    old_price: float
    new_price: float
    change_percent: float
    timestamp: str
    message: str


class AlertManager:
    """
    告警管理器
    监控价格变化，触发告警通知
    """
    
    def __init__(self, rules_file: str = "data/alert_rules.json"):
        self.rules_file = rules_file
        self.rules: Dict[str, AlertRule] = {}
        self.redis_client = None
        self.alerts: List[PriceAlert] = []
        
        self._load_rules()
        self._init_redis()
    
    def _load_rules(self):
        """加载告警规则"""
        if os.path.exists(self.rules_file):
            with open(self.rules_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for r in data.get("rules", []):
                    rule = AlertRule(**r)
                    self.rules[rule.id] = rule
    
    def _save_rules(self):
        """保存告警规则"""
        os.makedirs(os.path.dirname(self.rules_file), exist_ok=True)
        with open(self.rules_file, "w", encoding="utf-8") as f:
            json.dump({
                "rules": [vars(r) for r in self.rules.values()]
            }, f, ensure_ascii=False, indent=2)
    
    def _init_redis(self):
        """初始化 Redis"""
        if HAS_REDIS:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
                self.redis_client.ping()
                print("✓ Redis 连接成功")
            except Exception as e:
                print(f"⚠ Redis 连接失败: {e}")
                self.redis_client = None
    
    def add_rule(self, rule: AlertRule) -> str:
        """添加告警规则"""
        if not rule.id:
            rule.id = hashlib.md5(
                f"{rule.product_name}{rule.brand}{rule.model}".encode()
            ).hexdigest()[:8]
        
        self.rules[rule.id] = rule
        self._save_rules()
        return rule.id
    
    def remove_rule(self, rule_id: str):
        """移除告警规则"""
        if rule_id in self.rules:
            del self.rules[rule_id]
            self._save_rules()
    
    def list_rules(self) -> List[AlertRule]:
        """列出所有规则"""
        return list(self.rules.values())
    
    async def check_price(
        self,
        product_name: str,
        new_price: float,
        brand: str = "",
        model: str = "",
        source: str = ""
    ) -> List[PriceAlert]:
        """
        检查价格是否触发告警
        
        Args:
            product_name: 产品名称
            new_price: 新价格
            brand: 品牌
            model: 型号
            source: 来源
        
        Returns:
            触发的告警列表
        """
        alerts = []
        
        # 查找匹配的规则
        for rule in self.rules.values():
            if not rule.enabled:
                continue
            
            # 匹配产品
            if not self._match_product(rule, product_name, brand, model):
                continue
            
            # 检查冷却期
            if rule.last_alert_at:
                last = datetime.fromisoformat(rule.last_alert_at)
                hours_since = (datetime.now() - last).total_seconds() / 3600
                if hours_since < rule.alert_cooldown_hours:
                    continue
            
            # 获取上次价格
            old_price = await self._get_cached_price(product_name, brand)
            
            if old_price is None:
                # 新价格，首次记录
                alert = self._create_alert(
                    rule, AlertType.NEW_PRICE, 0, new_price, source
                )
                if alert:
                    alerts.append(alert)
            else:
                # 检查价格变化
                change_pct = abs(new_price - old_price) / old_price if old_price > 0 else 0
                
                # 阈值检查
                if rule.change_threshold > 0 and change_pct >= rule.change_threshold:
                    alert_type = AlertType.PRICE_DROP if new_price < old_price else AlertType.PRICE_RISE
                    alert = self._create_alert(rule, alert_type, old_price, new_price, source)
                    if alert:
                        alerts.append(alert)
                
                # 绝对价格检查
                if rule.min_price > 0 and new_price <= rule.min_price and old_price > rule.min_price:
                    alert = self._create_alert(rule, AlertType.THRESHOLD_EXCEED, old_price, new_price, source)
                    if alert:
                        alerts.append(alert)
        
        # 更新缓存
        await self._set_cached_price(product_name, brand, new_price)
        
        return alerts
    
    def _match_product(self, rule: AlertRule, name: str, brand: str, model: str) -> bool:
        """匹配产品"""
        # 精确匹配产品名
        if rule.product_name.lower() != name.lower():
            # 部分匹配
            if rule.product_name.lower() not in name.lower() and name.lower() not in rule.product_name.lower():
                return False
        
        # 品牌匹配
        if rule.brand and brand:
            if rule.brand.lower() != brand.lower():
                return False
        
        return True
    
    def _create_alert(
        self,
        rule: AlertRule,
        alert_type: AlertType,
        old_price: float,
        new_price: float,
        source: str
    ) -> Optional[PriceAlert]:
        """创建告警"""
        change_pct = abs(new_price - old_price) / old_price * 100 if old_price > 0 else 0
        
        # 生成消息
        if alert_type == AlertType.PRICE_DROP:
            message = f"🎉 **{rule.product_name}** 价格下降！\n"
            message += f"原价: ¥{old_price:,.0f} → 现价: ¥{new_price:,.0f}\n"
            message += f"降幅: {change_pct:.1f}%"
        elif alert_type == AlertType.PRICE_RISE:
            message = f"⚠️ **{rule.product_name}** 价格上浮\n"
            message += f"原价: ¥{old_price:,.0f} → 现价: ¥{new_price:,.0f}\n"
            message += f"涨幅: {change_pct:.1f}%"
        elif alert_type == AlertType.NEW_PRICE:
            message = f"🆕 **{rule.product_name}** 获取到新价格\n"
            message += f"价格: ¥{new_price:,.0f}"
        else:
            message = f"📢 **{rule.product_name}** 价格告警\n"
            message += f"当前价格: ¥{new_price:,.0f}"
        
        alert = PriceAlert(
            rule_id=rule.id,
            product_name=rule.product_name,
            alert_type=alert_type,
            old_price=old_price,
            new_price=new_price,
            change_percent=change_pct,
            timestamp=datetime.now().isoformat(),
            message=message
        )
        
        self.alerts.append(alert)
        rule.last_alert_at = datetime.now().isoformat()
        
        return alert
    
    async def _get_cached_price(self, product_name: str, brand: str) -> Optional[float]:
        """获取缓存价格"""
        key = self._make_cache_key(product_name, brand)
        
        if self.redis_client:
            try:
                price_str = self.redis_client.get(key)
                return float(price_str) if price_str else None
            except:
                pass
        
        # 回退到内存
        cache_file = f"data/cache/{key}.json"
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                data = json.load(f)
                # 检查过期
                cached_at = datetime.fromisoformat(data["timestamp"])
                if (datetime.now() - cached_at).total_seconds() < 86400:  # 24小时有效
                    return data.get("price")
        
        return None
    
    async def _set_cached_price(self, product_name: str, brand: str, price: float):
        """设置缓存价格"""
        key = self._make_cache_key(product_name, brand)
        
        if self.redis_client:
            try:
                self.redis_client.setex(key, 86400, str(price))  # 24小时TTL
                return
            except:
                pass
        
        # 回退到文件
        cache_file = f"data/cache/{key}.json"
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump({
                "price": price,
                "timestamp": datetime.now().isoformat()
            }, f)
    
    def _make_cache_key(self, product_name: str, brand: str) -> str:
        """生成缓存键"""
        return hashlib.md5(f"{product_name}{brand}".encode()).hexdigest()[:16]
    
    async def send_alerts(self, alerts: List[PriceAlert]):
        """发送告警"""
        for alert in alerts:
            # 查找规则获取 webhook
            rule = self.rules.get(alert.rule_id)
            if not rule or not rule.webhook_url:
                continue
            
            # 发送到 Webhook
            await self._send_webhook(rule.webhook_url, alert)
    
    async def _send_webhook(self, url: str, alert: PriceAlert):
        """发送 Webhook"""
        import httpx
        
        payload = {
            "msg_type": "markdown",
            "markdown": {
                "content": alert.message
            }
        }
        
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(url, json=payload, timeout=10)
                if resp.status_code == 200:
                    print(f"✓ 告警已发送: {alert.product_name}")
                else:
                    print(f"⚠ 告警发送失败: {resp.status_code}")
        except Exception as e:
            print(f"⚠ Webhook 发送异常: {e}")


class PriceCache:
    """
    价格缓存
    基于 Redis 的价格缓存，减少重复抓取
    """
    
    def __init__(self, ttl: int = 3600):  # 默认1小时
        self.ttl = ttl
        self.redis_client = None
        self._init_redis()
    
    def _init_redis(self):
        if HAS_REDIS:
            try:
                redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            except:
                self.redis_client = None
    
    async def get(self, key: str) -> Optional[str]:
        """获取缓存"""
        if self.redis_client:
            return self.redis_client.get(f"price:{key}")
        
        # 文件缓存回退
        cache_file = f"data/cache/{key}.json"
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                data = json.load(f)
                return data.get("value")
        return None
    
    async def set(self, key: str, value: str, ttl: int = None):
        """设置缓存"""
        ttl = ttl or self.ttl
        
        if self.redis_client:
            self.redis_client.setex(f"price:{key}", ttl, value)
            return
        
        # 文件缓存回退
        cache_file = f"data/cache/{key}.json"
        os.makedirs(os.path.dirname(cache_file), exist_ok=True)
        with open(cache_file, "w") as f:
            json.dump({
                "value": value,
                "expires_at": (datetime.now() + timedelta(seconds=ttl)).isoformat()
            }, f)
    
    async def invalidate(self, key: str):
        """失效缓存"""
        if self.redis_client:
            self.redis_client.delete(f"price:{key}")
        
        cache_file = f"data/cache/{key}.json"
        if os.path.exists(cache_file):
            os.remove(cache_file)


# 便捷函数
def create_alert_rule(
    product_name: str,
    webhook_url: str,
    **kwargs
) -> AlertRule:
    """创建告警规则"""
    return AlertRule(
        id="",
        product_name=product_name,
        webhook_url=webhook_url,
        **kwargs
    )
