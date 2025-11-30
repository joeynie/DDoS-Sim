#!/bin/sh

# ========================================
# 1. 限制网络带宽 (用于 UDP 泛洪攻击演示)
# ========================================
# 检测网卡名称
IFACE=$(ip route | grep default | awk '{print $5}' | head -n1)
echo "检测到网卡: $IFACE"

# 限制带宽到 1Mbps
echo "限制带宽到 1Mbps..."
tc qdisc add dev $IFACE root tbf rate 1mbit burst 32kbit latency 400ms

# ========================================
# 2. TCP 参数配置 (用于 SYN 攻击演示)
# ========================================
sysctl -w net.ipv4.tcp_max_syn_backlog=1024
sysctl -w net.ipv4.tcp_synack_retries=6
sysctl -w net.ipv4.tcp_syn_retries=6
sysctl -w net.ipv4.tcp_syncookies=0
sysctl -w net.ipv4.tcp_abort_on_overflow=0
sysctl -w net.core.somaxconn=1

# ========================================
# 3. UDP 参数配置 (用于 UDP 泛洪攻击演示)
# ========================================
# 减小 UDP 接收/发送缓冲区
sysctl -w net.core.rmem_default=8192
sysctl -w net.core.rmem_max=16384
sysctl -w net.core.wmem_default=8192
sysctl -w net.core.wmem_max=16384

# 减小网络设备队列长度
sysctl -w net.core.netdev_max_backlog=100

# 限制 UDP 内存使用
sysctl -w net.ipv4.udp_mem="8192 16384 24576"
sysctl -w net.ipv4.udp_rmem_min=4096
sysctl -w net.ipv4.udp_wmem_min=4096

echo "所有易受攻击参数已配置完成"

# ========================================
# 启动后端与 nginx
# ========================================
python3 /app/app.py &
python3 /app/udp_echo_server_9999.py &
nginx -g "daemon off;"
