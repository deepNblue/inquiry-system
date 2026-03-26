#!/bin/bash
# 自动询价系统 - 快速启动脚本

set -e

echo "=================================="
echo "  自动询价系统 - 快速启动"
echo "=================================="

# 检查依赖
check_deps() {
    echo "检查依赖..."
    python3 --version || { echo "Python3 未安装"; exit 1; }
}

# 安装依赖
install_deps() {
    echo "安装依赖..."
    pip install -r requirements.txt -q
}

# 初始化配置
init_config() {
    if [ ! -f config.yaml ]; then
        echo "创建配置文件..."
        cp config.example.yaml config.yaml
        echo "请编辑 config.yaml 填入 API Keys"
    fi
    
    # 创建目录
    mkdir -p data output logs
}

# Docker 模式
run_docker() {
    echo "启动 Docker 模式..."
    
    if [ ! -f .env ]; then
        cp .env.production .env
        echo "已创建 .env 文件，请编辑填入安全密码"
    fi
    
    docker-compose -f docker-compose.prod.yaml up -d
    echo "✓ 服务已启动"
    echo "  API: http://localhost:8000"
    echo "  UI:  http://localhost:7860"
    echo "  API Docs: http://localhost:8000/docs"
}

# 运行模式
run_mode() {
    case "$1" in
        cli)
            echo "启动 CLI 模式..."
            python3 main.py -i examples/products.csv -m web history
            ;;
        api)
            echo "启动 API 服务..."
            python3 api.py
            ;;
        ui)
            echo "启动 Web UI..."
            python3 ui.py
            ;;
        docker|prod)
            run_docker
            ;;
        monitor)
            echo "启动监控服务..."
            python3 src/monitor.py start
            ;;
        status)
            echo "检查服务状态..."
            curl -s http://localhost:8000/health 2>/dev/null && echo " API: ✓" || echo " API: ✗"
            ;;
        stop)
            echo "停止 Docker 服务..."
            docker-compose -f docker-compose.prod.yaml down
            ;;
        *)
            echo ""
            echo "用法: ./start.sh [cli|api|ui|docker|monitor|status|stop]"
            echo ""
            echo "  cli     - 命令行模式"
            echo "  api     - API 服务 (http://localhost:8000)"
            echo "  ui      - Web 界面 (http://localhost:7860)"
            echo "  docker  - Docker 生产部署"
            echo "  monitor- 价格监控服务"
            echo "  status  - 检查服务状态"
            echo "  stop    - 停止 Docker 服务"
            ;;
    esac
}

# 主流程
main() {
    check_deps
    install_deps
    init_config
    run_mode "$@"
}

main "$@"
