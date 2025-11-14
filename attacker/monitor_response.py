#!/usr/bin/env python3
"""
监控脚本 - 实时检测victim服务响应状态
用于验证DDoS攻击效果
"""

import time
import requests
import statistics
import threading
from datetime import datetime

def monitor_victim(target_url="http://10.10.20.20", duration=60, interval=1):
    """
    监控victim服务的响应状态
    
    :param target_url: 目标URL
    :param duration: 监控持续时间（秒）
    :param interval: 检测间隔（秒）
    """
    print(f"{'='*60}")
    print(f"🔍 开始监控victim服务响应状态")
    print(f"{'='*60}")
    print(f"目标URL: {target_url}")
    print(f"监控时长: {duration}秒")
    print(f"检测间隔: {interval}秒")
    print(f"{'='*60}\n")
    
    results = []
    start_time = time.time()
    end_time = start_time + duration
    success_count = 0
    failure_count = 0
    timeout_count = 0
    
    # 清除屏幕函数
    def clear_screen():
        print("\033c" if sys.platform != "win32" else "\n"*2)  # 简单清除屏幕
    
    try:
        while time.time() < end_time:
            current_time = time.time()
            elapsed = current_time - start_time
            timestamp = datetime.now().strftime("%H:%M:%S")
            
            try:
                # 发送请求并测量响应时间
                response = requests.get(target_url, timeout=5)
                response_time = response.elapsed.total_seconds() * 1000  # 毫秒
                
                if response.status_code == 200:
                    status = "✅ 成功"
                    success_count += 1
                else:
                    status = f"❌ 失败 (状态码: {response.status_code})"
                    failure_count += 1
                
                results.append(response_time)
                print(f"[{timestamp}] 第{len(results)}次检测 - {status} - 响应时间: {response_time:.2f}ms")
                
            except requests.Timeout:
                print(f"[{timestamp}] 第{len(results)+1}次检测 - ⏱️  超时")
                timeout_count += 1
                failure_count += 1
            except Exception as e:
                print(f"[{timestamp}] 第{len(results)+1}次检测 - 🚨 错误: {str(e)}")
                failure_count += 1
            
            # 等待下一次检测
            sleep_time = interval - (time.time() - current_time)
            if sleep_time > 0:
                time.sleep(sleep_time)
    
    except KeyboardInterrupt:
        print("\n\n🛑 监控已停止")
    
    # 打印统计信息
    print("\n" + "="*60)
    print("📊 监控结果统计")
    print("="*60)
    print(f"总检测次数: {success_count + failure_count}")
    print(f"成功次数: {success_count}")
    print(f"失败次数: {failure_count}")
    print(f"超时次数: {timeout_count}")
    print(f"成功率: {(success_count/(success_count + failure_count)*100):.2f}%" if (success_count + failure_count) > 0 else "无有效检测")
    
    if results:
        print(f"\n响应时间统计:")
        print(f"最小响应时间: {min(results):.2f}ms")
        print(f"最大响应时间: {max(results):.2f}ms")
        print(f"平均响应时间: {statistics.mean(results):.2f}ms")
        if len(results) > 1:
            print(f"响应时间标准差: {statistics.stdev(results):.2f}ms")
    
    # 分析攻击效果
    if failure_count > 0:
        print("\n⚠️  攻击效果分析:")
        if failure_count / (success_count + failure_count) > 0.5:
            print("✅ 攻击效果显著: 超过50%的请求失败")
        else:
            print("⚠️  攻击效果有限: 请求成功率仍然较高")
    else:
        print("\n❌ 攻击效果不明显: 所有请求均成功")
    
    print("="*60)

if __name__ == "__main__":
    import sys
    
    # 解析命令行参数
    target_url = "http://10.10.20.20"
    duration = 60
    interval = 1
    
    if len(sys.argv) > 1:
        target_url = sys.argv[1]
    if len(sys.argv) > 2:
        duration = int(sys.argv[2])
    if len(sys.argv) > 3:
        interval = float(sys.argv[3])
    
    monitor_victim(target_url, duration, interval)