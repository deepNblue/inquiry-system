.PHONY: help install test lint format clean docker-build docker-run docker-stop docs db-optimize

help:
	@echo "自动询价系统 - 开发命令"
	@echo ""
	@echo "  make install       安装依赖"
	@echo "  make test          运行测试"
	@echo "  make lint          代码检查"
	@echo "  make format        代码格式化"
	@echo "  make clean         清理缓存"
	@echo "  make docs          构建文档"
	@echo "  make db-optimize   优化数据库"
	@echo "  make docker-build  构建 Docker 镜像"
	@echo "  make docker-run    运行 Docker 容器"

install:
	pip install -r requirements.txt
	pip install pytest pytest-cov black flake8

test:
	PYTHONPATH=. pytest tests/ -v --cov=src --cov-report=html

lint:
	flake8 . --count --show-source --statistics
	black --check --diff .

format:
	black .

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .coverage htmlcov *.egg-info
	rm -rf data/*.db docs/_build

docs:
	cd docs && sphinx-build -b html . _build || echo "Sphinx not installed, using markdown docs"

db-optimize:
	python -m src.db_optimize --db data/history.db

docker-build:
	docker build -t inquiry-system .

docker-run:
	docker run -p 8000:8000 -p 7860:7860 inquiry-system

docker-stop:
	docker stop $$(docker ps -q --filter "ancestor=inquiry-system") 2>/dev/null || true
