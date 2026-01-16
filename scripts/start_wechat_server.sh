#!/bin/bash
# 启动微信服务器脚本
# 自动清理占用端口的进程，然后启动服务器

set -e

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# 进入项目根目录
cd "$PROJECT_ROOT"

# 从配置中读取端口（默认80，如果环境变量未设置）
PORT=${SERVER_PORT:-80}

echo "=========================================="
echo "启动微信服务器"
echo "=========================================="
echo "端口: $PORT"
echo ""

# 检查端口是否被占用
check_port() {
    local port=$1
    if command -v lsof >/dev/null 2>&1; then
        # 使用 lsof 检查端口
        PID=$(lsof -ti:$port 2>/dev/null || echo "")
    elif command -v netstat >/dev/null 2>&1; then
        # 使用 netstat 检查端口
        PID=$(netstat -tlnp 2>/dev/null | grep ":$port " | awk '{print $7}' | cut -d'/' -f1 | head -1 || echo "")
    elif command -v ss >/dev/null 2>&1; then
        # 使用 ss 检查端口
        PID=$(ss -tlnp 2>/dev/null | grep ":$port " | awk '{print $6}' | cut -d',' -f2 | cut -d'=' -f2 | head -1 || echo "")
    else
        echo "警告: 未找到端口检查工具 (lsof/netstat/ss)，跳过端口检查"
        PID=""
    fi
    
    echo "$PID"
}

# 清理占用端口的进程
cleanup_port() {
    local port=$1
    echo "检查端口 $port 是否被占用..."
    
    PID=$(check_port $port)
    
    if [ -n "$PID" ] && [ "$PID" != "" ]; then
        echo "发现端口 $port 被进程 $PID 占用"
        echo "正在清理进程 $PID..."
        
        # 尝试优雅地终止进程
        if kill -0 "$PID" 2>/dev/null; then
            kill "$PID" 2>/dev/null || true
            sleep 1
            
            # 如果进程还在，强制终止
            if kill -0 "$PID" 2>/dev/null; then
                echo "进程仍在运行，强制终止..."
                kill -9 "$PID" 2>/dev/null || true
                sleep 1
            fi
            
            # 再次检查
            NEW_PID=$(check_port $port)
            if [ -z "$NEW_PID" ] || [ "$NEW_PID" == "" ]; then
                echo "✓ 端口 $port 已释放"
            else
                echo "✗ 警告: 端口 $port 可能仍被占用"
            fi
        else
            echo "进程 $PID 已不存在"
        fi
    else
        echo "✓ 端口 $port 未被占用"
    fi
    echo ""
}

# 清理端口
cleanup_port $PORT

# 激活 conda 环境（如果存在）
if command -v conda >/dev/null 2>&1; then
    if conda env list | grep -q "personal-assistant"; then
        echo "激活 conda 环境: personal-assistant"
        eval "$(conda shell.bash hook)"
        conda activate personal-assistant
    fi
fi

# 启动服务器
echo "启动服务器..."
echo "=========================================="
echo ""

python -m interfaces.wechat.server

