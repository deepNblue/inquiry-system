# 自动询价系统 🐈

> 智能化项目设备询价管理，支持网页询价、厂家询价、历史价格分析

## 功能特性

| 功能 | 说明 |
|------|------|
| 🔍 **三渠道询价** | 网页抓取、厂家邮件、历史数据 |
| 📊 **智能报告** | Markdown/HTML双格式，含参数对比 |
| 📈 **价格分析** | 趋势预测、可视化图表 |
| 📧 **邮件闭环** | 发送询价 → 收取回复 → 自动提取 |
| 🔔 **飞书通知** | Webhook实时推送 |
| 💾 **数据管理** | SQLite + 历史追溯 |

## 快速开始

### 安装

```bash
git clone https://github.com/your-repo/inquiry-system.git
cd inquiry-system
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 编辑 .env 填写配置
```

### 运行

```bash
# 命令行
python main.py -i examples/equipment_list.csv

# Web UI
python ui.py

# API服务
python api.py
```

## 使用示例

### 命令行询价

```bash
# 从文件询价
python main.py -i examples/equipment_list.csv -m history

# 单产品询价
python main.py -p "iPhone 15 Pro" -b Apple

# 生成报告
python main.py -i examples/equipment_list.csv --export markdown html
```

### 交互式菜单

```bash
python interactive_cli.py
```

### Python API

```python
from src.history import HistoryMatcher
from src.report_generator import ReportGenerator

# 查询历史价格
matcher = HistoryMatcher()
results = matcher.search_similar("网络摄像机", brand="海康威视")

# 生成报告
gen = ReportGenerator()
report = gen.generate(results, "询价报告", "markdown")
```

## 项目结构

```
inquiry-system/
├── main.py              # CLI入口
├── api.py               # FastAPI服务
├── ui.py                # Web界面
├── interactive_cli.py   # 交互式菜单
├── src/
│   ├── history/         # 历史数据
│   ├── manufacturer/    # 厂家询价
│   ├── scraper/         # 网页抓取
│   ├── report_generator.py   # 报告生成
│   ├── charts.py        # 文本图表
│   ├── visualize.py     # HTML可视化
│   └── ...
├── examples/            # 示例数据
├── tests/               # 单元测试
└── docs/                # 文档
```

## 配置说明

### 邮件配置

```yaml
# config.email.yaml
smtp:
  host: smtp.qq.com
  port: 465
  ssl: true
  user: your-email@qq.com
  password: your-auth-code
```

### 飞书配置

```bash
export FEISHU_WEBHOOK=https://open.feishu.cn/open-apis/bot/v2/hook/xxx
```

## 部署

### Docker部署

```bash
# 构建
docker build -t inquiry-system .

# 运行
docker-compose up -d

# 生产环境
docker-compose -f docker-compose.prod.yml up -d
```

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| SMTP_HOST | SMTP服务器 | smtp.qq.com |
| SMTP_PORT | SMTP端口 | 465 |
| SMTP_USER | 用户名 | - |
| SMTP_PASSWORD | 密码/授权码 | - |
| FEISHU_WEBHOOK | 飞书Webhook | - |

## 开发

```bash
# 运行测试
python tests/test_inquiry.py

# 数据库优化
python -m src.db_optimize --all

# 快速命令
./quick_commands.sh init
./quick_commands.sh report
./quick_commands.sh test
```

## 技术栈

- Python 3.12
- SQLite / PostgreSQL
- FastAPI + Gradio
- Sentence Transformers (语义搜索)
- Matplotlib (可视化)

## 许可证

MIT License

## 联系方式

- 邮箱: 13151793@qq.com
- 项目地址: https://github.com/your-repo/inquiry-system
