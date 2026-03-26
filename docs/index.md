# 自动询价系统文档

欢迎使用自动询价系统！这是一个三渠道综合询价平台。

## 功能特性

- **网页询价** - 自动抓取电商/官网价格
- **厂家询价** - 邮件/飞书自动发送
- **历史询价** - 本地数据库 + 语义匹配
- **竞品追踪** - 价格告警 + 趋势分析
- **价格预测** - 基于历史的智能预测

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### CLI 模式

```bash
python main.py -i products.csv -m web history
```

### API 服务

```bash
python api.py
# 访问 http://localhost:8000/docs
```

### Docker 部署

```bash
./start.sh docker
```

## 目录

```{toctree}
:maxdepth: 2

api/index
modules
deployment
```

## 索引

- {ref}`genindex`
- {ref}`modindex`
- {ref}`search`
