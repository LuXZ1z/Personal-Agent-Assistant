#!/bin/bash

echo "============================================"
echo "启动最小化测试服务器"
echo "============================================"
echo ""

# 检查端口是否被占用
if lsof -i:8024 > /dev/null 2>&1; then
    echo "端口 8024 已被占用，正在关闭..."
    lsof -t -i:8024 | xargs kill -9
    sleep 2
fi

echo "✓ 端口 8024 未被占用"
echo ""

# 启动服务器
cd /home/Personal-Agent-Assistant
python minimal_test_server.py

