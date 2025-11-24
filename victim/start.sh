#!/bin/sh
# 配置极度脆弱的TCP参数 - 让SYN攻击更容易成功
echo "🎯 正在配置极度脆弱的victim系统..."
sysctl -w net.ipv4.tcp_max_syn_backlog=1
sysctl -w net.ipv4.tcp_synack_retries=6
sysctl -w net.ipv4.tcp_syn_retries=6
sysctl -w net.ipv4.tcp_syncookies=0
sysctl -w net.ipv4.tcp_abort_on_overflow=0
sysctl -w net.core.somaxconn=1

echo "📊 当前TCP参数配置:"
echo "   tcp_max_syn_backlog = $(sysctl -n net.ipv4.tcp_max_syn_backlog)"
echo "   tcp_syncookies = $(sysctl -n net.ipv4.tcp_syncookies)"
echo "   somaxconn = $(sysctl -n net.core.somaxconn)"
echo "✅ 脆弱配置已应用!"
echo ""

# 启动后端与 nginx
python3 /app/app.py &
nginx -g "daemon off;"
