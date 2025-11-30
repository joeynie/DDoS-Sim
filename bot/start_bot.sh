#!/bin/sh

# 添加到victim网络的路由
echo "添加路由: 10.10.20.0/24 via 10.10.10.5"
ip route add 10.10.20.0/24 via 10.10.10.5

# 启动bot agent
echo "启动Bot Agent..."
python3 bot_agent.py
