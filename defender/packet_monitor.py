#!/usr/bin/env python3
"""
Defender实时包监控器
捕获和分析网络数据包，实时显示关键信息
"""

import sys
import time
import argparse
import threading
from datetime import datetime
from collections import defaultdict, deque
import signal
import os

try:
    from scapy.all import *
    from scapy.layers.inet import IP, TCP, UDP, ICMP
    from scapy.layers.l2 import Ether
except ImportError:
    print("错误: 需要安装Scapy库")
    print("运行: pip3 install scapy")
    sys.exit(1)

# 全局变量
# 这些统计信息将在每个窗口周期开始时重置
packet_stats_window = defaultdict(int) 
# 存储最近1000个包的详细信息
recent_packets = deque(maxlen=1000)
# 保护 recent_packets 的读写
recent_packets_lock = threading.Lock()
# 控制程序运行状态
running = True

class PacketAnalyzer:
    """数据包分析器，负责状态维护和信息提取"""
    def __init__(self):
        # 统计锁用于保护 packet_stats_window
        self.stats_lock = threading.Lock()
        self.packet_stats_window = packet_stats_window # 引用全局窗口统计

    def analyze_packet(self, packet):
        """分析单个数据包"""
        if not packet:
            return None

        packet_info = {
            'timestamp': datetime.now().strftime('%H:%M:%S.%f')[:-3],
            'length': len(packet),
            'protocol': 'UNKNOWN',
            'src_ip': 'N/A',
            'dst_ip': 'N/A',
            'src_port': 'N/A',
            'dst_port': 'N/A',
            'flags': 'N/A',
            'ttl': 'N/A',
            'details': {}
        }

        # 分析IP层
        if packet.haslayer(IP):
            ip = packet[IP]
            packet_info['src_ip'] = ip.src
            packet_info['dst_ip'] = ip.dst
            packet_info['protocol'] = ip.proto
            packet_info['ttl'] = ip.ttl

            # 协议映射
            proto_map = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}
            packet_info['protocol'] = proto_map.get(ip.proto, f'PROTO_{ip.proto}')

            # 分析TCP层
            if packet.haslayer(TCP):
                tcp = packet[TCP]
                packet_info['src_port'] = tcp.sport
                packet_info['dst_port'] = tcp.dport

                # TCP标志位
                flags = []
                if tcp.flags & 0x01: flags.append('FIN')
                if tcp.flags & 0x02: flags.append('SYN')
                if tcp.flags & 0x04: flags.append('RST')
                if tcp.flags & 0x08: flags.append('PSH')
                if tcp.flags & 0x10: flags.append('ACK')
                if tcp.flags & 0x20: flags.append('URG')
                packet_info['flags'] = '|'.join(flags) if flags else 'NONE'
            
            # 分析UDP层
            elif packet.haslayer(UDP):
                udp = packet[UDP]
                packet_info['src_port'] = udp.sport
                packet_info['dst_port'] = udp.dport

            # 分析ICMP
            elif packet.haslayer(ICMP):
                icmp = packet[ICMP]
                packet_info['details'].update({
                    'icmp_type': icmp.type,
                    'icmp_code': icmp.code
                })

        # 更新内部窗口统计 (只统计当前窗口的包)
        with self.stats_lock:
            self.packet_stats_window['total_packets'] += 1
            self.packet_stats_window[f'proto_{packet_info["protocol"]}'] += 1

        return packet_info

    def get_window_stats(self, window_seconds):
        """获取当前窗口的统计摘要，并重置计数器"""
        with self.stats_lock:
            # 计算 PPS
            total_packets = self.packet_stats_window['total_packets']
            pps = total_packets / window_seconds if window_seconds > 0 else 0

            summary = {
                'total_packets': total_packets,
                'window_seconds': window_seconds,
                'packets_per_second': pps,
                'protocols': {k: v for k, v in self.packet_stats_window.items() if k.startswith('proto_')},
            }
            
            # 重置所有计数器，实现窗口化统计
            self.packet_stats_window.clear()
            
            return summary

def packet_callback(packet, analyzer_instance):
    """Scapy包回调函数，接受分析器实例"""
    global recent_packets

    packet_info = analyzer_instance.analyze_packet(packet)

    if packet_info:
        # 使用锁保护对 deque 的修改
        with recent_packets_lock:
            recent_packets.append(packet_info)

def display_packets(analyzer_instance):
    """显示包信息"""
    global running
    
    WINDOW_SECONDS = 5.0 # 定义统计窗口时长
    
    print("\n" + "="*120)
    print("🔍 DEFENDER 实时包监控器")
    print("="*120)
    print(f"{'时间':<12} {'协议':<6} {'源IP':<15} {'目的IP':<15} {'源端口':<8} {'目的端口':<10} {'标志':<12} {'长度':<6} {'TTL':<5}")
    print("-"*120)

    last_display_time = time.time()

    while running:
        try:
            # 显示新包
            with recent_packets_lock:
                while recent_packets:
                    packet = recent_packets.popleft()

                    src_ip = str(packet['src_ip'])[:14]
                    dst_ip = str(packet['dst_ip'])[:14]

                    print(f"{packet['timestamp']:<12} "
                          f"{packet['protocol']:<6} "
                          f"{src_ip:<15} "
                          f"{dst_ip:<15} "
                          f"{str(packet['src_port']):<8} "
                          f"{str(packet['dst_port']):<10} "
                          f"{packet['flags'][:10]:<12} "
                          f"{packet['length']:<6} "
                          f"{str(packet['ttl']):<5}")

            # 每 5 秒显示一次窗口统计信息
            current_time = time.time()
            if current_time - last_display_time >= WINDOW_SECONDS:
                # 获取窗口统计信息，并在内部重置计数器
                stats = analyzer_instance.get_window_stats(WINDOW_SECONDS)

                print(f"\n📊 窗口统计信息 (周期: {WINDOW_SECONDS:.1f}秒)")
                # 总包数现在是 5 秒内的包数
                print(f"   周期总包数: {stats['total_packets']} | 周期 PPS: {stats['packets_per_second']:.1f}")
                print(f"   协议分布: {stats['protocols']}")

                print("-"*120)
                last_display_time = current_time

            time.sleep(0.1)  # 短暂休眠避免CPU占用过高

        except Exception as e:
            # 如果显示线程发生错误，关闭运行标志以通知嗅探线程
            print(f"显示线程错误: {e}")
            running = False
            break

def signal_handler(signum, frame):
    """信号处理函数"""
    global running
    print(f"\n收到信号 {signum}，正在停止监控...")
    running = False
    # 强制退出：在某些环境下，为了确保 Scapy 立即停止，可以发送一个 OS 信号
    # 但由于我们使用的是 stop_filter，通常不需要 os._exit(1)
    # 依赖 stop_filter 来优雅地关闭

def stop_sniffing(packet):
    """检查全局 running 状态，用于 sniff 的 stop_filter"""
    global running
    return not running

def main():
    parser = argparse.ArgumentParser(description='Defender实时包监控器')
    parser.add_argument('-i', '--interface', default='any', help='监听的网络接口 (默认: any)')
    parser.add_argument('-f', '--filter', default='', help='BPF过滤器表达式')
    parser.add_argument('--no-promisc', action='store_true', help='不使用混杂模式')

    args = parser.parse_args()

    # 实例化单例分析器
    analyzer = PacketAnalyzer()

    # 设置信号处理
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("启动Defender包监控器...")
    print(f"监听接口: {args.interface}")
    if args.filter:
        print(f"过滤器: {args.filter}")

    # 启动显示线程，并将分析器实例传入
    display_thread = threading.Thread(target=display_packets, args=(analyzer,), daemon=True)
    display_thread.start()

    try:
        filter_expr = args.filter if args.filter else "ip"
        promisc = not args.no_promisc

        print("开始捕获包... 按 Ctrl+C 停止")
        
        # 使用 stop_filter 来确保当 running 变为 False 时，sniff 立即停止
        sniff(iface=args.interface, 
              prn=lambda p: packet_callback(p, analyzer), 
              filter=filter_expr,
              store=0, 
              promisc=promisc,
              stop_filter=stop_sniffing)

    except Exception as e:
        # 当 stop_filter 触发时，sniff 可能会退出并抛出异常，这里忽略它
        if running: # 如果运行标志仍为 True，则这是一个真正的错误
            print(f"捕获错误: {e}")
    finally:
        # global running
        # 无论 sniff 如何退出，都确保 running 被设置为 False
        running = False 
        
        # 等待显示线程优雅退出
        display_thread.join(timeout=2)
        print("\n监控器已停止")

if __name__ == "__main__":
    main()