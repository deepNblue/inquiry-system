# 模块参考

## 核心模块

### src.scraper

网页询价模块，支持多种数据源。

```python
from src.scraper import WebScraper

scraper = WebScraper(config)
results = await scraper.search_price(product)
```

### src.history

历史价格查询模块。

```python
from src.history import HistoryMatcher

matcher = HistoryMatcher("data/history.db")
results = matcher.search_similar("iPhone 15", brand="Apple")
```

### src.aggregator

多渠道价格聚合。

```python
from src.aggregator import PriceAggregator

agg = PriceAggregator()
result = agg.aggregate(web_results, history_results)
```

## 增强模块

### src.price_predictor

价格趋势分析和预测。

```python
from src.price_predictor import PricePredictor

pred = PricePredictor()
analysis = pred.analyze_trend("iPhone 15", days=30)
prediction = pred.predict_price("iPhone 15", days_ahead=7)
```

### src.ai_insights

AI 驱动的报告生成。

```python
from src.ai_insights import AIReportGenerator

gen = AIReportGenerator(api_key="...")
summary = await gen.generate_report_summary(products)
```

### src.visualizer

价格趋势可视化。

```python
from src.visualizer import PriceVisualizer

viz = PriceVisualizer()
chart = viz.plot_price_trend(dates, prices, "iPhone 15")
```

## 服务模块

### src.auth

JWT 认证和用户管理。

```python
from src.auth import AuthManager

auth = AuthManager()
user_id = auth.create_user("user", "pass")
token = auth.create_access_token(user_id)
```

### src.realtime

WebSocket 实时推送。

```python
from src.realtime import PriceWebSocket

ws = get_price_websocket()
await ws.push_price_update("iPhone 15", 6999, "京东")
```

## 数据模块

### src.database

数据库管理。

```python
from src.database import get_db

db = get_db()
db.execute("INSERT INTO ...", params)
```

### src.cache

Redis 缓存。

```python
from src.cache import get_cache

cache = get_cache()
cache.set_price("iPhone 15", {"price": 6999})
```

## 工具模块

### src.webhook_alert

Webhook 告警。

```python
from src.webhook_alert import AlertManager

manager = AlertManager()
alerts = await manager.check_price("iPhone 15", 6999)
```

### src.monitor

定时监控服务。

```python
from src.monitor import PriceMonitor

monitor = PriceMonitor()
monitor.add_task("监控任务", ["iPhone 15"], interval_hours=6)
monitor.start()
```
