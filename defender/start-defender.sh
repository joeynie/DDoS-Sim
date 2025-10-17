#!/bin/bash

echo "Starting Defender Gateway..."

# 1. 开启内核的IP转发功能，这是作为路由器的前提
echo "Enabling IP forwarding..."
sysctl -w net.ipv4.ip_forward=1

# 2. 清空所有现有的iptables规则，确保一个干净的环境
echo "Flushing existing iptables rules..."
iptables -F
iptables -t nat -F
iptables -X

# 3. 设置默认策略：允许所有输入输出，但默认丢弃所有转发流量
# 这是安全的做法，我们只允许我们明确定义的流量通过
iptables -P INPUT ACCEPT
iptables -P OUTPUT ACCEPT
iptables -P FORWARD DROP

# 4. 设置NAT（网络地址转换）
# 让从victim_net出去的包（即victim的响应包）能够伪装成defender的地址，
# 这样响应才能正确返回给attacker
echo "Setting up NAT masquerade..."
iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE

# 5. 设置转发规则，允许双向流量通过
# 允许已建立的连接和相关流量通过，这是所有有状态防火墙的基础
iptables -A FORWARD -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT
# 允许从攻击网络到受害者网络的流量
iptables -A FORWARD -i eth0 -o eth1 -j ACCEPT

# ======================================================================
# 【防御规则区域】
# 在这里添加你的DDoS防御规则。
# 默认情况下，这里是空的，流量可以自由通过。
#
# --- 示例：SYN Flood防御规则（默认注释掉） ---
# 限制进入eth0（来自attacker）的SYN包，每秒最多10个，突发不超过20个
# echo "Applying SYN Flood protection..."
# iptables -A FORWARD -i eth0 -p tcp --syn -m limit --limit 10/s --limit-burst 20 -j ACCEPT
# iptables -A FORWARD -i eth0 -p tcp --syn -j DROP
# ======================================================================

echo "Defender is running. Forwarding rules are set."
echo "Current iptables FORWARD chain:"
iptables -L FORWARD -v -n

# 保持容器在前台运行，否则脚本执行完容器会退出
tail -f /dev/null