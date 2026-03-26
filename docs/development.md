# 开发指南

## 环境设置

### 1. 克隆代码

```bash
git clone https://github.com/your-repo/inquiry-system.git
cd inquiry-system
```

### 2. 创建虚拟环境

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate   # Windows
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
pip install pytest pytest-cov black flake8
```

## 开发命令

```bash
# 代码检查
make lint

# 格式化代码
make format

# 运行测试
make test

# 生成覆盖率报告
pytest tests/ --cov=src --cov-report=html
```

## 项目架构

```
src/
├── scraper/          # 网页抓取
│   ├── __init__.py
│   ├── firecrawl_client.py
│   └── scrapling_client.py
├── manufacturer/     # 厂家询价
├── history/         # 历史询价
├── aggregator/      # 结果聚合
├── scheduler/       # 任务调度
├── price_predictor.py   # 价格预测
├── price_parser.py     # 价格解析
├── ai_insights.py      # AI 摘要
├── visualizer.py       # 可视化
├── auth.py             # 认证
├── webhook_alert.py    # 告警
├── monitor.py          # 监控
└── ...
```

## 添加新模块

1. 在 `src/` 下创建模块目录
2. 创建 `__init__.py` 导出主要类
3. 在主程序中导入使用

示例：

```python
# src/mymodule/__init__.py
from .core import MyClass

__all__ = ['MyClass']

# src/mymodule/core.py
class MyClass:
    def __init__(self):
        pass
```

## 添加测试

```python
# tests/test_mymodule.py
import pytest
from src.mymodule import MyClass

class TestMyClass:
    def test_create(self):
        obj = MyClass()
        assert obj is not None
```

## Git 工作流

```bash
# 创建功能分支
git checkout -b feature/new-feature

# 开发...

# 提交
git add .
git commit -m "feat: 添加新功能"

# 推送
git push origin feature/new-feature

# 创建 PR
```

## 代码规范

- 遵循 PEP 8
- 使用 Black 格式化
- 使用 flake8 检查
- 编写 docstring
- 添加类型提示

示例：

```python
from typing import List, Optional

class MyClass:
    """我的类描述
    
    Attributes:
        name: 类名称
        value: 类值
    """
    
    def __init__(self, name: str, value: int = 0) -> None:
        """初始化
        
        Args:
            name: 名称
            value: 值，默认0
        """
        self.name = name
        self.value = value
    
    def process(self, items: List[str]) -> Optional[str]:
        """处理数据
        
        Args:
            items: 数据列表
        
        Returns:
            处理结果或None
        """
        if not items:
            return None
        return ", ".join(items)
```
