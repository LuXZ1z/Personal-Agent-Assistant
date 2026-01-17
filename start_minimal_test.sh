#!/bin/bash

# 启动最小化测试服务器（使用正确的虚拟环境）

echo "============================================"
echo "启动最小化测试服务器"
echo "============================================"
echo ""

# 检查并清理端口
if lsof -i:8024 > /dev/null 2>&1; then
    echo "端口 8024 已被占用，正在关闭..."
    lsof -t -i:8024 | xargs kill -9
    sleep 2
fi

# 切换到项目目录
cd /home/Personal-Agent-Assistant

# 激活虚拟环境（如果存在）
if [ -d "/root/miniconda3/envs/personal-assistant" ]; then
    echo "激活虚拟环境: personal-assistant"
    source /root/miniconda3/bin/activate personal-assistant
elif [ -d "$HOME/.conda/envs/personal-assistant" ]; then
    echo "激活虚拟环境: personal-assistant"
    source $HOME/.conda/bin/activate personal-assistant
else
    echo "警告: 未找到 personal-assistant 虚拟环境"
    echo "请手动激活虚拟环境后运行: python minimal_test_server.py"
    exit 1
fi

# 检查依赖
echo "检查依赖..."
python -c "import yaml, fastapi, uvicorn" 2>/dev/null || {
    echo "安装缺失的依赖..."
    pip install pyyaml fastapi uvicorn -q
}

echo ""
echo "启动服务器..."
echo "============================================"
echo ""

# 启动服务器
python minimal_test_server.py

