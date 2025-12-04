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
# 新结构: defaultdict(lambda: defaultdict(int)) 用于嵌套存储
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

        # 额外的窗口统计结构：
        # key: src_ip, value: {'count': int, 'bytes': int, 'proto_tcp_count': int, 'proto_udp_count': int}
        self.ip_traffic_stats = defaultdict(lambda: defaultdict(int))
        self.ttl_counts = defaultdict(int) # key: TTL value, value: count

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
            src_ip = ip.src
            packet_info['src_ip'] = src_ip
            packet_info['dst_ip'] = ip.dst
            packet_info['protocol'] = ip.proto
            packet_info['ttl'] = ip.ttl

            # 协议映射
            proto_map = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}
            proto_name = proto_map.get(ip.proto, f'PROTO_{ip.proto}')
            packet_info['protocol'] = proto_name

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
            
            # ----------------- 新增统计聚合逻辑 -----------------
            with self.stats_lock:
                # 1. 更新总包数和协议分布 (兼容原逻辑)
                self.packet_stats_window['total_packets'] += 1
                self.packet_stats_window[f'proto_{proto_name}'] += 1

                # 2. 更新IP流量统计
                self.ip_traffic_stats[src_ip]['count'] += 1
                self.ip_traffic_stats[src_ip]['bytes'] += packet_info['length']
                
                if proto_name == 'TCP':
                    self.ip_traffic_stats[src_ip]['proto_tcp_count'] += 1
                elif proto_name == 'UDP':
                    self.ip_traffic_stats[src_ip]['proto_udp_count'] += 1

                # 3. 更新TTL计数 (只关注 33 和 63)
                if ip.ttl == 32 or ip.ttl == 63:
                    self.ttl_counts[ip.ttl] += 1

        return packet_info

    def get_window_stats(self, window_seconds):
        """获取当前窗口的统计摘要，并重置计数器"""
        with self.stats_lock:
            # 1. 计算基础统计
            total_packets = self.packet_stats_window['total_packets']
            pps = total_packets / window_seconds if window_seconds > 0 else 0

            # 2. 计算 IP 流量统计 (PPS/BPS)
            ip_stats_list = []
            for ip, stats in self.ip_traffic_stats.items():
                ip_stats_list.append({
                    'ip': ip,
                    'pps': stats['count'] / window_seconds,
                    'bps': stats['bytes'] / window_seconds,
                    'tcp_count': stats['proto_tcp_count'],
                    'udp_count': stats['proto_udp_count']
                })

            # 3. 计算 TTL 比例
            ttl_33_count = self.ttl_counts[32]
            ttl_63_count = self.ttl_counts[63]
            ttl_ratio = float('inf')
            if ttl_63_count > 0:
                ttl_ratio = ttl_33_count / ttl_63_count
            elif ttl_33_count > 0:
                 ttl_ratio = ttl_33_count # 63为0时，等同于33的包数

            # 4. 排序 TCP/UDP 流量
            
            # 排序：按 TCP 计数降序取前 5
            top_tcp_ips = sorted(
                ip_stats_list, 
                key=lambda x: x['tcp_count'], 
                reverse=True
            )[:5]

            # 排序：按 UDP 计数降序取前 5
            top_udp_ips = sorted(
                ip_stats_list, 
                key=lambda x: x['udp_count'], 
                reverse=True
            )[:5]

            summary = {
                # 基础信息 (原)
                'total_packets': total_packets,
                'window_seconds': window_seconds,
                'packets_per_second': pps,
                'protocols': {k: v for k, v in self.packet_stats_window.items() if k.startswith('proto_')},
                
                # 新增聚合特征
                'ip_traffic_summary': ip_stats_list,
                'ttl_33_count': ttl_33_count,
                'ttl_63_count': ttl_63_count,
                'ttl_33_to_63_ratio': ttl_ratio,
                'top_tcp_ips': [{'ip': d['ip'], 'count': d['tcp_count']} for d in top_tcp_ips if d['tcp_count'] > 0],
                'top_udp_ips': [{'ip': d['ip'], 'count': d['udp_count']} for d in top_udp_ips if d['udp_count'] > 0]
            }
            
            # 重置所有计数器，实现窗口化统计
            self.packet_stats_window.clear()
            self.ip_traffic_stats.clear()
            self.ttl_counts.clear()
            
            return summary

def packet_callback(packet, analyzer_instance):
    """Scapy包回调函数，接受分析器实例"""
    global recent_packets

    # 仅将 IP 层的数据包发送给分析器，忽略 L2 帧
    if packet.haslayer(IP):
        packet_info = analyzer_instance.analyze_packet(packet)

        if packet_info:
            # 使用锁保护对 deque 的修改
            with recent_packets_lock:
                recent_packets.append(packet_info)

def display_packets(analyzer_instance):
    """显示包信息"""
    global running
    
    WINDOW_SECONDS = 5.0 # 定义统计窗口时长
    
    # 初始显示头部
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
                
                # 清屏以提供更清晰的窗口视图 (可选，但推荐在实时监控中使用)
                # os.system('clear' if os.name == 'posix' else 'cls') 
                # 重新打印表头
                # print(f"\n{'='*120}\n{'🔍 DEFENDER 实时包监控器':^120}\n{'='*120}")
                # print(f"{'时间':<12} {'协议':<6} {'源IP':<15} {'目的IP':<15} {'源端口':<8} {'目的端口':<10} {'标志':<12} {'长度':<6} {'TTL':<5}")
                # print("-"*120)


                print(f"\n{'='*60} 📊 窗口统计信息 ({WINDOW_SECONDS:.1f}秒) {'='*60}")
                # 基础统计
                print(f" 📦 周期总包数: {stats['total_packets']} | 周期 PPS: {stats['packets_per_second']:.1f}")
                print(f" 🚀 协议分布: {stats['protocols']}")
                print("-"*120)

                # 1. IP 流量统计 (PPS/BPS)
                print(f" 🌐 源IP流量统计 (PPS/BPS):")
                if stats['ip_traffic_summary']:
                    # 打印表头
                    print(f"{'IP 地址':<15} | {'总包数':<8} | {'PPS':<8} | {'BPS (Bytes/s)':<15}")
                    for d in stats['ip_traffic_summary']:
                         print(f"{d['ip']:<15} | {d['tcp_count'] + d['udp_count']:<8} | {d['pps']:.2f} | {d['bps']:.2f}")
                else:
                    print("  - 暂无 IP 流量数据")
                print("-"*120)


                # 2. TTL 比例 (恶意流量判断依据)
                ttl_ratio_str = f"{stats['ttl_33_to_63_ratio']:.2f}" if stats['ttl_33_to_63_ratio'] != float('inf') else "Inf"
                print(f" ⚠️ TTL 32 vs 62 比例分析 (TTL 32 / TTL 63):")
                print(f"   TTL 32 计数 (去程攻击): {stats['ttl_33_count']}")
                print(f"   TTL 63 计数 (回程响应): {stats['ttl_63_count']}")
                print(f"   TTL 比例: {ttl_ratio_str} (比率过高可能表明攻击/扫描流量占主导)")
                print("-"*120)


                # 3. 排序 TCP/UDP 流量
                print(f" 🔥 TCP 流量前 5 源 IP:")
                if stats['top_tcp_ips']:
                    for d in stats['top_tcp_ips']:
                        print(f"   - {d['ip']:<15}: {d['count']} 个包")
                else:
                    print("  - 暂无 TCP 流量")
                
                print(f"\n 💧 UDP 流量前 5 源 IP:")
                if stats['top_udp_ips']:
                    for d in stats['top_udp_ips']:
                        print(f"   - {d['ip']:<15}: {d['count']} 个包")
                else:
                    print("  - 暂无 UDP 流量")
                
                print("\n" + "="*120)

                last_display_time = current_time

            time.sleep(0.1) # 短暂休眠避免CPU占用过高

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
        # 无论 sniff 如何退出，都确保 running 被设置为 False
        running = False 
        
        # 等待显示线程优雅退出
        display_thread.join(timeout=2)
        print("\n监控器已停止")

if __name__ == "__main__":
    main()