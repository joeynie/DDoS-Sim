#!/bin/bash

# SYN攻击教学辅助脚本 - 受害者系统TCP参数调整
# 使用方法: ./setup_victim.sh [vulnerable|secure]

echo "🎯 SYN攻击教学 - TCP参数调整脚本"
echo "=================================="

MODE=${1:-vulnerable}

if [ "$MODE" = "vulnerable" ]; then
    echo "📉 配置易受攻击的TCP参数 (用于演示SYN攻击)"
    echo "   - 缩短SYN队列长度: 128"
    echo "   - 延长SYN+ACK重试: 6次"
    echo "   - 关闭SYN Cookies防护"
    echo "   - 关闭队列溢出时的连接拒绝"
    echo ""
    
    # 应用易受攻击的参数
    sysctl -w net.ipv4.tcp_max_syn_backlog=1
    sysctl -w net.ipv4.tcp_synack_retries=6
    sysctl -w net.ipv4.tcp_syn_retries=6
    sysctl -w net.ipv4.tcp_syncookies=0
    sysctl -w net.ipv4.tcp_abort_on_overflow=0
    
    echo "✅ 易受攻击的TCP参数已应用"
    echo "⚠️  系统现在容易受到SYN洪水攻击"
    
elif [ "$MODE" = "default" ] || [ "$MODE" = "secure" ]; then
    if [ "$MODE" = "default" ]; then
        echo "🔄 恢复系统默认TCP参数"
        echo "   - SYN队列长度: 1024 (系统默认)"
        echo "   - SYN+ACK重试: 5次 (系统默认)"
        echo "   - SYN重试次数: 6次 (系统默认)"
        echo "   - SYN Cookies: 1 (系统默认开启)"
        echo "   - 队列溢出处理: 0 (系统默认)"
        echo ""
        
        # 恢复系统默认参数
        sysctl -w net.ipv4.tcp_max_syn_backlog=1024
        sysctl -w net.ipv4.tcp_synack_retries=5
        sysctl -w net.ipv4.tcp_syn_retries=6
        sysctl -w net.ipv4.tcp_syncookies=1
        sysctl -w net.ipv4.tcp_abort_on_overflow=0
        
        echo "✅ 系统默认TCP参数已恢复"
        echo "🔄 系统恢复到原始配置状态"
    else
        echo "🛡️  应用增强安全的TCP参数"
        echo "   - 增大SYN队列长度: 2048 (增强防护)"
        echo "   - 减少SYN+ACK重试: 2次 (快速释放资源)"
        echo "   - 减少SYN重试次数: 2次 (快速释放资源)"
        echo "   - 开启SYN Cookies防护: 1"
        echo "   - 开启队列溢出拒绝: 1 (主动拒绝)"
        echo ""
        
        # 应用增强安全的参数
        sysctl -w net.ipv4.tcp_max_syn_backlog=2048
        sysctl -w net.ipv4.tcp_synack_retries=2
        sysctl -w net.ipv4.tcp_syn_retries=2
        sysctl -w net.ipv4.tcp_syncookies=1
        sysctl -w net.ipv4.tcp_abort_on_overflow=1
        
        echo "✅ 增强安全TCP参数已应用"
        echo "🛡️  系统现在具有强化的SYN攻击防护"
    fi
    
else
    echo "❌ 无效的模式: $MODE"
    echo "用法: $0 [vulnerable|default|secure]"
    echo ""
    echo "模式说明:"
    echo "  vulnerable  # 配置为易受SYN攻击"
    echo "  default     # 恢复系统默认参数"
    echo "  secure      # 应用增强安全配置"
    echo ""
    echo "示例:"
    echo "  $0 vulnerable  # 用于攻击演示"
    echo "  $0 default     # 恢复原始状态"
    echo "  $0 secure      # 强化防护"
    exit 1
fi

echo ""
echo "📊 当前TCP参数状态:"
echo "   SYN队列长度: $(sysctl -n net.ipv4.tcp_max_syn_backlog)"
echo "   SYN+ACK重试: $(sysctl -n net.ipv4.tcp_synack_retries)"
echo "   SYN重试次数: $(sysctl -n net.ipv4.tcp_syn_retries)"
echo "   SYN Cookies: $(sysctl -n net.ipv4.tcp_syncookies)"
echo "   队列溢出处理: $(sysctl -n net.ipv4.tcp_abort_on_overflow)"