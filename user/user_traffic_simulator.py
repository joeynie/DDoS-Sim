#!/usr/bin/env python3
"""
用户流量模拟器
模拟正常用户的网络活动，发送随机数量的TCP和UDP包给victim服务器。
通过defender转发，设置TTL为33
"""

import socket
import time
import random
import sys
from datetime import datetime

class UserTrafficSimulator:
    def __init__(self, victim_ip="10.10.20.20", tcp_port=80, udp_port=9999):
        self.victim_ip = victim_ip
        self.tcp_port = tcp_port
        self.udp_port = udp_port
        self.ttl = 33

        print("🏠 用户流量模拟器启动 (背景流量生成)")
        print(f"🎯 目标: {victim_ip}")
        print(f"🔌 TCP端口: {tcp_port}, UDP端口: {udp_port}")
        print(f"⏰ Ground Truth TTL: {self.ttl}")
        print("-" * 50)

    def send_tcp_packets(self, count):
        """发送随机数量的TCP包"""
        success = 0
        for i in range(count):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, self.ttl)
                sock.settimeout(3.0) # 缩短超时，避免阻塞太久

                # 连接
                sock.connect((self.victim_ip, self.tcp_port))
                
                # 构造随机请求
                endpoints = ["/", "/index.html", "/api/status", "/login", "/static/style.css"]
                user_agents = ["Mozilla/5.0", "Chrome/90.0", "Safari/14.0"]
                
                request = (
                    f"GET {random.choice(endpoints)} HTTP/1.1\r\n"
                    f"Host: {self.victim_ip}\r\n"
                    f"User-Agent: {random.choice(user_agents)}\r\n"
                    f"Connection: close\r\n\r\n"
                ).encode('utf-8')

                sock.send(request)
                
                # 读取少量响应即可
                sock.recv(512)
                sock.close()
                success += 1
                
                # 极短的微观间隔，模拟突发请求
                time.sleep(random.uniform(0.05, 0.2))

            except Exception:
                # 正常流量偶尔也会丢包或超时，这是正常的，不用打印错误堆栈
                pass
        
        return success

    def send_udp_packets(self, count):
        """发送随机数量的UDP包"""
        success = 0
        for i in range(count):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, self.ttl)
                sock.settimeout(1.0)

                messages = ["DNS", "NTP", "KeepAlive", "GameSync", "Heartbeat"]
                data = f"USER_UDP:{random.choice(messages)}|{time.time()}".encode('utf-8')

                sock.sendto(data, (self.victim_ip, self.udp_port))
                
                # 尝试接收，但不强求
                try:
                    sock.recvfrom(512)
                except socket.timeout:
                    pass
                
                sock.close()
                success += 1
                time.sleep(random.uniform(0.05, 0.2))

            except Exception:
                pass
        
        return success

    def run_simulation(self, base_interval=5):
        """
        运行无限模拟循环
        :param base_interval: 基础循环间隔（秒）
        """
        print(f"\n🚀 开始无限循环模拟")
        print(f"⏱️  基础间隔: {base_interval}秒 (含随机抖动)")
        print("=" * 50)

        cycle = 0
        try:
            while True:
                cycle += 1
                
                # 1. 随机化流量大小 
                traffic_scale = random.choice([1.0, 1.5, 2.0, 0.5]) 
                
                n_tcp = int(random.randint(3, 15) * traffic_scale)
                n_udp = int(random.randint(2, 8) * traffic_scale)

                print(f"[{datetime.now().strftime('%H:%M:%S')}] Cycle {cycle}: 发送 {n_tcp} TCP, {n_udp} UDP...", end="", flush=True)

                # 2. 执行发送
                tcp_ok = self.send_tcp_packets(n_tcp)
                udp_ok = self.send_udp_packets(n_udp)

                print(f" 完成 (TCP:{tcp_ok}/{n_tcp}, UDP:{udp_ok}/{n_udp})")

                # 3. 随机化间隔 (Jitter)
                jitter = base_interval * 0.5
                wait_time = random.uniform(base_interval - jitter, base_interval + jitter)
                
                # 偶尔模拟长等待
                if random.random() < 0.05: # 5%概率
                    print("   (User idle...)")
                    wait_time += 10

                time.sleep(max(0.5, wait_time))

        except KeyboardInterrupt:
            print("\n🛑 模拟停止")
        except Exception as e:
            print(f"\n❌ 发生错误: {e}")

def main():
    import argparse
    parser = argparse.ArgumentParser(description='用户流量模拟器 (随机化版)')
    parser.add_argument('--victim-ip', default='10.10.20.20', help='受害者IP')
    parser.add_argument('--interval', type=float, default=5.0, help='平均发送间隔(秒)')
    
    args = parser.parse_args()

    # 稍微随机等待一下启动，避免所有容器同时发起网络请求
    time.sleep(random.uniform(1, 3))

    simulator = UserTrafficSimulator(
        victim_ip=args.victim_ip,
        tcp_port=80,
        udp_port=9999
    )

    simulator.run_simulation(base_interval=args.interval)

if __name__ == "__main__":
    main()