#!/bin/bash

# 确保 defender (10.10.10.5) 是访问 10.10.20.0/24 网络的下一跳
echo "Adding route to 10.10.20.0/24 via 10.10.10.5..."
ip route add 10.10.20.0/24 via 10.10.10.5

# 运行主要程序
echo "Starting user traffic simulator..."
python3 /usr/local/bin/user_traffic_simulator.py