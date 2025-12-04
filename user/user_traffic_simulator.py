#!/usr/bin/env python3
"""
用户流量模拟器
模拟正常用户的网络活动，发送少量的TCP和UDP包给victim服务器
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

        # TTL设置为33（用户要求的）
        self.ttl = 33

        print("🏠 用户流量模拟器启动")
        print(f"🎯 目标: {victim_ip}")
        print(f"🔌 TCP端口: {tcp_port}, UDP端口: {udp_port}")
        print(f"⏰ TTL: {self.ttl}")
        print("-" * 50)

    def send_tcp_packets(self, count=3):
        """发送少量TCP包到victim的TCP服务器"""
        print(f"\n🔄 发送 {count} 个TCP包到 {self.victim_ip}:{self.tcp_port}")

        for i in range(count):
            try:
                # 创建TCP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

                # 设置TTL
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, self.ttl)

                # 设置超时
                sock.settimeout(5.0)

                print(f"  [{i+1}] 连接到 {self.victim_ip}:{self.tcp_port}...")

                # 连接到victim
                start_time = time.time()
                sock.connect((self.victim_ip, self.tcp_port))
                connect_time = time.time() - start_time

                print(f"      ✓ 连接成功 ({connect_time:.3f}s)")

                # 发送数据
                messages = [
                    "Hello from normal user!",
                    "This is a legitimate TCP request",
                    "Normal user activity simulation",
                    "Testing connection to server",
                    "User browsing the website"
                ]

                message = random.choice(messages)
                data = f"USER_TCP_REQUEST: {message}\n".encode('utf-8')

                sock.send(data)
                print(f"      📤 发送: {data.decode().strip()}")

                # 接收响应
                response = sock.recv(1024)
                print(f"      📥 响应: {response.decode().strip()[:50]}...")

                # 随机等待1-3秒，模拟用户行为
                wait_time = random.uniform(1, 3)
                print(f"      ⏱️  等待 {wait_time:.1f}秒...")
                time.sleep(wait_time)

                sock.close()
                print(f"      ✓ TCP包 {i+1} 发送完成")

            except socket.timeout:
                print(f"      ✗ TCP包 {i+1} 超时")
            except socket.error as e:
                print(f"      ✗ TCP包 {i+1} 错误: {e}")
            except Exception as e:
                print(f"      ✗ TCP包 {i+1} 未知错误: {e}")

    def send_udp_packets(self, count=5):
        """发送少量UDP包到victim的UDP服务器"""
        print(f"\n📡 发送 {count} 个UDP包到 {self.victim_ip}:{self.udp_port}")

        for i in range(count):
            try:
                # 创建UDP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                # 设置TTL
                sock.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, self.ttl)

                # 设置超时
                sock.settimeout(2.0)

                messages = [
                    "DNS query from user",
                    "NTP time sync request",
                    "Gaming heartbeat packet",
                    "VoIP audio data",
                    "User UDP traffic test"
                ]

                message = random.choice(messages)
                data = f"USER_UDP_PACKET: {message} | SEQ:{i+1} | TIME:{datetime.now().strftime('%H:%M:%S')}".encode('utf-8')

                print(f"  [{i+1}] 发送UDP包: {data.decode()[:50]}...")

                # 发送UDP包
                sock.sendto(data, (self.victim_ip, self.udp_port))

                # 尝试接收响应（UDP echo服务器会回复）
                try:
                    response, addr = sock.recvfrom(1024)
                    print(f"      📥 响应: {response.decode()[:50]}...")
                except socket.timeout:
                    print(f"      📭 无响应（正常）")

                # 随机等待0.5-2秒
                wait_time = random.uniform(0.5, 2)
                print(f"      ⏱️  等待 {wait_time:.1f}秒...")
                time.sleep(wait_time)

                sock.close()
                print(f"      ✓ UDP包 {i+1} 发送完成")

            except socket.error as e:
                print(f"      ✗ UDP包 {i+1} 错误: {e}")
            except Exception as e:
                print(f"      ✗ UDP包 {i+1} 未知错误: {e}")

    def run_simulation(self, cycles=10, cycle_interval=10):
        """
        运行模拟
        :param cycles: 循环次数
        :param cycle_interval: 每次循环间隔（秒）
        """
        print(f"\n🚀 开始用户流量模拟")
        print(f"🔄 循环次数: {cycles}")
        print(f"⏱️  循环间隔: {cycle_interval}秒")
        print("=" * 50)

        try:
            for cycle in range(cycles):
                print(f"\n🎯 循环 {cycle + 1}/{cycles} - {datetime.now().strftime('%H:%M:%S')}")

                # 发送TCP包（3个）
                self.send_tcp_packets(3)

                # 发送UDP包（5个）
                self.send_udp_packets(5)

                if cycle < cycles - 1:
                    print(f"\n💤 等待 {cycle_interval}秒后开始下一轮...")
                    time.sleep(cycle_interval)
                else:
                    print("✅ 所有循环完成！")     
        except KeyboardInterrupt:
            print("\n🛑 用户中断模拟")
        except Exception as e:
            print(f"\n❌ 模拟错误: {e}")

    def interactive_mode(self):
        """交互模式"""
        print("\n🎮 交互模式 - 选择要发送的流量类型:")
        print("1. 发送TCP包")
        print("2. 发送UDP包")
        print("3. 运行完整模拟")
        print("4. 退出")

        while True:
            try:
                choice = input("\n请选择 (1-4): ").strip()

                if choice == "1":
                    count = int(input("输入TCP包数量 (默认3): ") or "3")
                    self.send_tcp_packets(count)
                elif choice == "2":
                    count = int(input("输入UDP包数量 (默认5): ") or "5")
                    self.send_udp_packets(count)
                elif choice == "3":
                    cycles = int(input("输入循环次数 (默认5): ") or "5")
                    interval = int(input("输入循环间隔(秒，默认10): ") or "10")
                    self.run_simulation(cycles, interval)
                    break
                elif choice == "4":
                    break
                else:
                    print("❌ 无效选择，请重新输入")

            except ValueError:
                print("❌ 请输入有效的数字")
            except KeyboardInterrupt:
                print("\n👋 再见!")
                break

def main():
    import argparse

    parser = argparse.ArgumentParser(description='用户流量模拟器')
    parser.add_argument('--victim-ip', default='10.10.20.20', help='受害者IP地址')
    parser.add_argument('--tcp-port', type=int, default=80, help='TCP端口')
    parser.add_argument('--udp-port', type=int, default=9999, help='UDP端口')
    parser.add_argument('--cycles', type=int, default=10, help='模拟循环次数')
    parser.add_argument('--interval', type=int, default=10, help='循环间隔(秒)')
    parser.add_argument('--interactive', action='store_true', help='启用交互模式')

    args = parser.parse_args()

    simulator = UserTrafficSimulator(
        victim_ip=args.victim_ip,
        tcp_port=args.tcp_port,
        udp_port=args.udp_port
    )

    if args.interactive:
        simulator.interactive_mode()
    else:
        simulator.run_simulation(args.cycles, args.interval)

if __name__ == "__main__":
    main()