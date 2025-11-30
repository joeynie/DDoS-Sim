#!/usr/bin/env python3
"""
UDP测试客户端 - 发送带序号的包并检测丢包
"""

import socket
import time
import sys

def test_udp_connection(target_ip, target_port=9999, num_packets=10, interval=0.5):
    """
    发送带序号的UDP包并等待回复
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)  # 2秒超时
    
    print(f"UDP丢包测试")
    print(f"目标: {target_ip}:{target_port}")
    print(f"发送包数: {num_packets}")
    print(f"间隔: {interval}秒")
    print("=" * 60)
    
    sent_count = 0
    received_count = 0
    lost_packets = []
    
    for i in range(1, num_packets + 1):
        try:
            # 发送带序号的消息
            message = f"Test packet #{i}"
            sock.sendto(message.encode('utf-8'), (target_ip, target_port))
            sent_count += 1
            send_time = time.time()
            
            print(f"[发送] #{i}: {message}", end=" ... ")
            sys.stdout.flush()
            
            try:
                # 等待回复
                data, addr = sock.recvfrom(65535)
                recv_time = time.time()
                rtt = (recv_time - send_time) * 1000  # 转换为毫秒
                
                reply = data.decode('utf-8', errors='ignore')
                received_count += 1
                print(f"✓ 收到回复: {reply[:50]} (RTT: {rtt:.1f}ms)")
                
            except socket.timeout:
                print(f"✗ 超时，未收到回复")
                lost_packets.append(i)
            
            # 等待间隔
            if i < num_packets:
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print("\n\n测试中断")
            break
        except Exception as e:
            print(f"✗ 错误: {e}")
            lost_packets.append(i)
    
    sock.close()
    
    # 统计结果
    print("\n" + "=" * 60)
    print("测试结果")
    print("=" * 60)
    print(f"发送包数: {sent_count}")
    print(f"收到回复: {received_count}")
    print(f"丢包数: {len(lost_packets)}")
    print(f"丢包率: {(len(lost_packets) / sent_count * 100):.1f}%")
    
    if lost_packets:
        print(f"丢失的包序号: {lost_packets}")
    else:
        print("✓ 所有包都收到回复！")
    print("=" * 60)

def continuous_test(target_ip, target_port=9999, interval=1.0):
    """
    持续发送UDP包，实时显示丢包情况
    """
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(2.0)
    
    print(f"UDP持续测试 (按Ctrl+C停止)")
    print(f"目标: {target_ip}:{target_port}")
    print(f"间隔: {interval}秒")
    print("=" * 60)
    
    seq = 0
    sent_count = 0
    received_count = 0
    
    try:
        while True:
            seq += 1
            try:
                message = f"Ping #{seq}"
                sock.sendto(message.encode('utf-8'), (target_ip, target_port))
                sent_count += 1
                send_time = time.time()
                
                try:
                    data, addr = sock.recvfrom(65535)
                    recv_time = time.time()
                    rtt = (recv_time - send_time) * 1000
                    received_count += 1
                    
                    loss_rate = ((sent_count - received_count) / sent_count * 100) if sent_count > 0 else 0
                    print(f"#{seq}: ✓ RTT={rtt:.1f}ms | 丢包率: {loss_rate:.1f}% ({received_count}/{sent_count})")
                    
                except socket.timeout:
                    loss_rate = ((sent_count - received_count) / sent_count * 100) if sent_count > 0 else 0
                    print(f"#{seq}: ✗ 超时 | 丢包率: {loss_rate:.1f}% ({received_count}/{sent_count})")
                
                time.sleep(interval)
                
            except Exception as e:
                print(f"#{seq}: ✗ 错误: {e}")
                time.sleep(interval)
                
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("测试结束")
        print("=" * 60)
        print(f"发送包数: {sent_count}")
        print(f"收到回复: {received_count}")
        print(f"丢包数: {sent_count - received_count}")
        print(f"丢包率: {((sent_count - received_count) / sent_count * 100):.1f}%")
        print("=" * 60)
    
    sock.close()

def main():
    if len(sys.argv) < 2:
        print("UDP丢包测试工具")
        print("\n用法:")
        print("  python3 udp_test_client.py <target_ip> [mode] [options]")
        print("\n模式:")
        print("  test     - 发送指定数量的包并统计 (默认)")
        print("  ping     - 持续发送包，实时显示丢包率")
        print("\n示例:")
        print("  # 发送10个包测试")
        print("  python3 udp_test_client.py 10.10.20.20")
        print("  python3 udp_test_client.py 10.10.20.20 test 20 0.5")
        print()
        print("  # 持续ping测试")
        print("  python3 udp_test_client.py 10.10.20.20 ping")
        print("  python3 udp_test_client.py 10.10.20.20 ping 0.2")
        sys.exit(1)
    
    target_ip = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else "test"
    
    if mode == "ping":
        interval = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
        continuous_test(target_ip, 9999, interval)
    else:
        num_packets = int(sys.argv[3]) if len(sys.argv) > 3 else 10
        interval = float(sys.argv[4]) if len(sys.argv) > 4 else 0.5
        test_udp_connection(target_ip, 9999, num_packets, interval)

if __name__ == "__main__":
    main()
