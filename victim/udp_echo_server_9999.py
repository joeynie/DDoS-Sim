#!/usr/bin/env python3
"""
UDP Echo服务器 - 监听9999端口
会回复每个收到的包，并添加序号，方便检测丢包
"""

import socket
import time
import sys

def start_udp_echo_server(host='0.0.0.0', port=9999):
    # 禁用输出缓冲
    sys.stdout = open(sys.stdout.fileno(), mode='w', buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode='w', buffering=1)
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    
    # 尝试增大缓冲区
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
    except:
        pass
    
    sock.bind((host, port))
    
    print(f"[UDP Echo服务器] 启动在 {host}:{port}", flush=True)
    print(f"[UDP Echo服务器] 会回复每个收到的包", flush=True)
    print(f"[UDP Echo服务器] 格式: [序号] 原始消息", flush=True)
    
    packet_count = 0
    bytes_received = 0
    bytes_sent = 0
    start_time = time.time()
    last_print_time = start_time
    
    try:
        while True:
            try:
                # 接收数据
                data, addr = sock.recvfrom(65535)
                packet_count += 1
                bytes_received += len(data)
                
                # 构造回复消息：[序号] 原始消息
                reply = f"[{packet_count}] {data.decode('utf-8', errors='ignore')}".encode('utf-8')
                
                # 发送回复
                sock.sendto(reply, addr)
                bytes_sent += len(reply)
                
                # 实时打印每个收到的包（正常流量）
                if len(data) < 100:  # 小包才打印内容，大包只打印统计
                    print(f"[UDP Echo] #{packet_count} 从 {addr[0]}:{addr[1]} 收到: {data.decode('utf-8', errors='ignore')[:50]}", flush=True)
                
                # 每100个包或每秒打印一次统计
                current_time = time.time()
                if packet_count % 100 == 0 or (current_time - last_print_time) >= 1.0:
                    elapsed = current_time - start_time
                    pps = packet_count / elapsed if elapsed > 0 else 0
                    mbps_in = (bytes_received * 8 / 1000000) / elapsed if elapsed > 0 else 0
                    mbps_out = (bytes_sent * 8 / 1000000) / elapsed if elapsed > 0 else 0
                    print(f"[统计] 总计 {packet_count} 包 | 接收: {pps:.0f} pps, {mbps_in:.2f} Mbps | 发送: {mbps_out:.2f} Mbps", flush=True)
                    last_print_time = current_time
                    
            except socket.error as e:
                print(f"[UDP Echo] Socket错误: {e}", flush=True)
                time.sleep(0.1)
            except Exception as e:
                print(f"[UDP Echo] 处理错误: {e}", flush=True)
            
    except KeyboardInterrupt:
        print("\n[UDP Echo服务器] 服务器停止", flush=True)
    finally:
        sock.close()
        elapsed = time.time() - start_time
        print(f"\n[UDP Echo服务器] 最终统计:", flush=True)
        print(f"  总包数: {packet_count}", flush=True)
        print(f"  接收字节: {bytes_received:,}", flush=True)
        print(f"  发送字节: {bytes_sent:,}", flush=True)
        print(f"  运行时间: {elapsed:.1f} 秒", flush=True)

if __name__ == "__main__":
    start_udp_echo_server()
