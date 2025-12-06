#!/bin/bash

echo "=========================================="
echo "  NFTables 防御系统启动中..."
echo "=========================================="

# 1. 开启内核的IP转发功能
echo "[1/6] 启用IP转发..."
sysctl -w net.ipv4.ip_forward=1

# 2. 配置连接追踪参数
echo "[2/6] 配置连接追踪参数..."
# 增加连接追踪表大小
sysctl -w net.netfilter.nf_conntrack_max=1000000 2>/dev/null || true
# 减少TIME_WAIT超时
sysctl -w net.ipv4.tcp_fin_timeout=30 2>/dev/null || true
# 启用SYN cookies
sysctl -w net.ipv4.tcp_syncookies=1 2>/dev/null || true
# 减少SYN-ACK重试次数
sysctl -w net.ipv4.tcp_synack_retries=2 2>/dev/null || true
# 增加SYN队列长度
sysctl -w net.ipv4.tcp_max_syn_backlog=65535 2>/dev/null || true
# 启用TCP时间戳
sysctl -w net.ipv4.tcp_timestamps=1 2>/dev/null || true

# 3. 清空现有规则
echo "[3/6] 清空现有防火墙规则..."
nft flush ruleset 2>/dev/null || true
iptables -F 2>/dev/null || true
iptables -t nat -F 2>/dev/null || true

# 4. 设置基本NAT（使用iptables，因为nftables的NAT需要额外配置）
echo "[4/6] 配置NAT..."
iptables -t nat -A POSTROUTING -o eth1 -j MASQUERADE

# 5. 应用NFTables防御规则
echo "[5/6] 应用NFTables防御规则..."
cd /app
python3 -c "
from nftables_config import DefenseConfig, NFTablesManager

iptables -A FORWARD -i eth1 -o eth0 -j ACCEPT

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
# 创建默认配置
config = DefenseConfig()

# 可以在这里自定义初始参数
# config.syn_defense.rate_limit = 100
# config.udp_defense.per_ip_rate = 50

# 创建管理器并应用规则
manager = NFTablesManager(config)
success = manager.apply_rules()

if success:
    print('NFTables规则应用成功!')
    # 保存配置
    config.save()
else:
    print('NFTables规则应用失败!')
    exit(1)
"

# 6. 启动API服务
echo "[6/6] 启动防御API服务..."
echo ""
echo "=========================================="
echo "  防御系统已启动"
echo "  API地址: http://0.0.0.0:5000"
echo "=========================================="
echo ""
echo "可用API端点:"
echo "  GET  /api/health        - 健康检查"
echo "  GET  /api/params        - 获取所有参数"
echo "  GET  /api/params/ranges - 获取参数范围"
echo "  POST /api/params/update - 更新参数"
echo "  GET  /api/stats         - 获取统计信息"
echo "  POST /api/rules/apply   - 应用规则"
echo "  GET  /api/rl/state      - 获取RL状态"
echo "  POST /api/rl/action     - 应用RL动作"
echo ""

# 启动Flask API服务
python3 /app/defense_api.py --host 0.0.0.0 --port 5000
