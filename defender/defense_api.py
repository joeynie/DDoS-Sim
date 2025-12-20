#!/usr/bin/env python3
"""DDoS Defense API - RL compatible"""

from flask import Flask, request, jsonify, render_template, send_from_directory
from nftables_config import RLDefenseConfig, NFTablesManager
from packet_monitor import PacketAnalyzer
import logging
import os
import time
import psutil

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, 
            template_folder=os.path.join(BASE_DIR, 'templates'),
            static_folder=os.path.join(BASE_DIR, 'static'))

config = RLDefenseConfig()
manager = NFTablesManager(config)
packet_analyzer = PacketAnalyzer()
packet_analyzer.start_monitoring()

stats_cache = {'data': {}, 'timestamp': 0}
CACHE_TTL = 1


@app.route('/', methods=['GET'])
def index():
    return render_template('dashboard.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'ok', 'service': 'defense'})


@app.route('/api/params', methods=['GET'])
def get_params():
    return jsonify({'success': True, 'params': manager.get_all_params()})


@app.route('/api/params/ranges', methods=['GET'])
def get_param_ranges():
    return jsonify({'success': True, 'ranges': manager.get_param_ranges()})


@app.route('/api/params/update', methods=['POST'])
def update_params():
    data = request.get_json()
    if 'batch' in data:
        success = manager.batch_update_params(data['batch'])
        return jsonify({'success': success})
    else:
        category = data.get('category')
        param = data.get('param')
        value = data.get('value')
        if not all([category, param, value is not None]):
            return jsonify({'success': False}), 400
        success = manager.update_param(category, param, value)
        return jsonify({'success': success})


@app.route('/api/stats', methods=['GET'])
def get_stats():
    global stats_cache
    current_time = time.time()
    if current_time - stats_cache['timestamp'] < CACHE_TTL:
        return jsonify({'success': True, 'stats': stats_cache['data'], 'cached': True})
    stats = manager.get_statistics()
    stats_cache = {'data': stats, 'timestamp': current_time}
    return jsonify({'success': True, 'stats': stats, 'cached': False})


@app.route('/api/rules/apply', methods=['POST'])
def apply_rules():
    success = manager.apply_rules()
    return jsonify({'success': success})


@app.route('/api/rules/generate', methods=['GET'])
def generate_rules():
    return jsonify({'success': True, 'rules': manager.generate_nftables_rules()})


@app.route('/api/blacklist', methods=['GET'])
def get_blacklist():
    stats = manager.get_statistics()
    blacklist = stats.get('sets', {}).get('blacklist', {})
    return jsonify({'success': True, 'blacklist': blacklist})


@app.route('/api/blacklist/add', methods=['POST'])
def add_blacklist():
    data = request.get_json()
    ip = data.get('ip')
    timeout = data.get('timeout')
    if not ip:
        return jsonify({'success': False}), 400
    success = manager.add_to_blacklist(ip, timeout)
    return jsonify({'success': success})


@app.route('/api/blacklist/remove', methods=['POST'])
def remove_blacklist():
    data = request.get_json()
    ip = data.get('ip')
    if not ip:
        return jsonify({'success': False}), 400
    success = manager.remove_from_blacklist(ip)
    return jsonify({'success': success})


@app.route('/api/whitelist/add', methods=['POST'])
def add_whitelist():
    data = request.get_json()
    ip = data.get('ip')
    if not ip:
        return jsonify({'success': False}), 400
    success = manager.add_to_whitelist(ip)
    return jsonify({'success': success})


@app.route('/api/config/save', methods=['POST'])
def save_config():
    data = request.get_json() or {}
    filepath = data.get('filepath', '/etc/nftables_defense_config.json')
    try:
        manager.config.save(filepath)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False}), 500


@app.route('/api/config/load', methods=['POST'])
def load_config():
    global manager
    data = request.get_json() or {}
    filepath = data.get('filepath', '/etc/nftables_defense_config.json')
    try:
        config = RLDefenseConfig.load(filepath)
        manager = NFTablesManager(config)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False}), 500


@app.route('/api/rl/state', methods=['GET'])
def get_rl_state():
    """RL state: observation + counters"""
    params = manager.get_all_params()
    stats = manager.get_statistics()
    counters = stats.get('counters', {})
    
    tp = counters.get('tp_count', 0)
    fp = counters.get('fp_count', 0)
    tn = counters.get('tn_count', 0)
    fn = counters.get('fn_count', 0)
    
    total_attack = tp + fn
    total_normal = fp + tn
    attack_drop_rate = tp / total_attack if total_attack > 0 else 0.0
    normal_drop_rate = fp / total_normal if total_normal > 0 else 0.0
    
    cpu_load = psutil.cpu_percent(interval=0.1) / 100.0
    traffic_features = packet_analyzer.get_rl_observation()
    
    obs_json = {
        'attack_drop_rate': attack_drop_rate,
        'normal_drop_rate': normal_drop_rate,
        'abnormal_ratio': traffic_features.get('ttl_abnormal_ratio', 0.0),
        'syn_ratio': traffic_features.get('syn_ratio', 0.0),
        'udp_ratio': traffic_features.get('udp_ratio', 0.0),
        'max_ip_ratio': traffic_features.get('max_ip_ratio', 0.0),
        'cpu_load': cpu_load,
        'traffic_intensity': traffic_features.get('total_pps', 0.0),
        'curr_global_limit': params.get('global_limit', 10000),
        'curr_single_ip_limit': params.get('single_ip_limit', 100),
        'curr_conn_limit': params.get('conn_limit', 50)
    }
    
    return jsonify({'success': True, 'state': {'obs': obs_json, 'counters': counters}})


@app.route('/api/rl/action', methods=['POST'])
def apply_rl_action():
    data = request.get_json()
    actions = data.get('actions', {})
    if not actions:
        return jsonify({'success': False}), 400
    success = manager.batch_update_params(actions)
    return jsonify({'success': success, 'new_state': manager.get_all_params()})


@app.route('/api/rl/reset', methods=['POST'])
def reset_to_default():
    global manager
    manager = NFTablesManager(RLDefenseConfig())
    success = manager.apply_rules()
    return jsonify({'success': success, 'params': manager.get_all_params()})


if __name__ == '__main__':
    import time
    import argparse
    
    parser = argparse.ArgumentParser(description='DDoS Defense API')
    parser.add_argument('--host', default='0.0.0.0')
    parser.add_argument('--port', type=int, default=5000)
    parser.add_argument('--apply-on-start', action='store_true')
    args = parser.parse_args()
    
    if args.apply_on_start:
        manager.apply_rules()
    
    logger.info(f"API started on {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)
