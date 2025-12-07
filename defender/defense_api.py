#!/usr/bin/env python3
"""
NFTables 防御系统 HTTP API
提供 RESTful 接口供强化学习网络调用
"""

from flask import Flask, request, jsonify
from nftables_config import RLDefenseConfig, NFTablesManager
import threading
import time
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 全局管理器实例
config = RLDefenseConfig()
manager = NFTablesManager(config)

# 统计数据缓存
stats_cache = {'data': {}, 'timestamp': 0}
CACHE_TTL = 1  # 缓存有效期（秒）


@app.route('/api/health', methods=['GET'])
def health_check():
    """健康检查"""
    return jsonify({'status': 'ok', 'service': 'nftables-defense'})


@app.route('/api/params', methods=['GET'])
def get_params():
    """获取所有当前参数"""
    return jsonify({
        'success': True,
        'params': manager.get_all_params()
    })


@app.route('/api/params/ranges', methods=['GET'])
def get_param_ranges():
    """获取参数范围（用于强化学习）"""
    return jsonify({
        'success': True,
        'ranges': manager.get_param_ranges()
    })


@app.route('/api/params/update', methods=['POST'])
def update_params():
    """更新参数
    
    请求体格式:
    {
        "category": "syn_defense",
        "param": "rate_limit",
        "value": 200
    }
    或批量更新:
    {
        "batch": {
            "syn_defense.rate_limit": 200,
            "udp_defense.per_ip_rate": 100
        }
    }
    """
    data = request.get_json()
    
    if 'batch' in data:
        success = manager.batch_update_params(data['batch'])
        return jsonify({
            'success': success,
            'message': '批量参数更新' + ('成功' if success else '失败')
        })
    else:
        category = data.get('category')
        param = data.get('param')
        value = data.get('value')
        
        if not all([category, param, value is not None]):
            return jsonify({
                'success': False,
                'message': '缺少必要参数: category, param, value'
            }), 400
        
        success = manager.update_param(category, param, value)
        return jsonify({
            'success': success,
            'message': f'参数 {category}.{param} 更新' + ('成功' if success else '失败')
        })


@app.route('/api/stats', methods=['GET'])
def get_stats():
    """获取防御统计信息"""
    global stats_cache
    
    # 检查缓存
    current_time = time.time()
    if current_time - stats_cache['timestamp'] < CACHE_TTL:
        return jsonify({
            'success': True,
            'stats': stats_cache['data'],
            'cached': True
        })
    
    # 获取新统计
    stats = manager.get_statistics()
    stats_cache = {'data': stats, 'timestamp': current_time}
    
    return jsonify({
        'success': True,
        'stats': stats,
        'cached': False
    })


@app.route('/api/rules/apply', methods=['POST'])
def apply_rules():
    """应用当前配置的规则"""
    success = manager.apply_rules()
    return jsonify({
        'success': success,
        'message': '规则应用' + ('成功' if success else '失败')
    })


@app.route('/api/rules/generate', methods=['GET'])
def generate_rules():
    """生成规则预览（不应用）"""
    rules = manager.generate_nftables_rules()
    return jsonify({
        'success': True,
        'rules': rules
    })


@app.route('/api/blacklist', methods=['GET'])
def get_blacklist():
    """获取黑名单"""
    stats = manager.get_statistics()
    blacklist = stats.get('sets', {}).get('blacklist', {})
    return jsonify({
        'success': True,
        'blacklist': blacklist
    })


@app.route('/api/blacklist/add', methods=['POST'])
def add_blacklist():
    """添加IP到黑名单
    
    请求体: {"ip": "1.2.3.4", "timeout": 300}
    """
    data = request.get_json()
    ip = data.get('ip')
    timeout = data.get('timeout')
    
    if not ip:
        return jsonify({'success': False, 'message': '缺少IP参数'}), 400
    
    success = manager.add_to_blacklist(ip, timeout)
    return jsonify({
        'success': success,
        'message': f'IP {ip} ' + ('已添加到黑名单' if success else '添加失败')
    })


@app.route('/api/blacklist/remove', methods=['POST'])
def remove_blacklist():
    """从黑名单移除IP"""
    data = request.get_json()
    ip = data.get('ip')
    
    if not ip:
        return jsonify({'success': False, 'message': '缺少IP参数'}), 400
    
    success = manager.remove_from_blacklist(ip)
    return jsonify({
        'success': success,
        'message': f'IP {ip} ' + ('已从黑名单移除' if success else '移除失败')
    })


@app.route('/api/whitelist/add', methods=['POST'])
def add_whitelist():
    """添加IP到白名单"""
    data = request.get_json()
    ip = data.get('ip')
    
    if not ip:
        return jsonify({'success': False, 'message': '缺少IP参数'}), 400
    
    success = manager.add_to_whitelist(ip)
    return jsonify({
        'success': success,
        'message': f'IP {ip} ' + ('已添加到白名单' if success else '添加失败')
    })


@app.route('/api/config/save', methods=['POST'])
def save_config():
    """保存当前配置到文件"""
    data = request.get_json() or {}
    filepath = data.get('filepath', '/etc/nftables_defense_config.json')
    
    try:
        manager.config.save(filepath)
        return jsonify({
            'success': True,
            'message': f'配置已保存到 {filepath}'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'保存失败: {str(e)}'
        }), 500


@app.route('/api/config/load', methods=['POST'])
def load_config():
    """从文件加载配置"""
    global manager
    
    data = request.get_json() or {}
    filepath = data.get('filepath', '/etc/nftables_defense_config.json')
    
    try:
        config = DefenseConfig.load(filepath)
        manager = NFTablesManager(config)
        return jsonify({
            'success': True,
            'message': f'配置已从 {filepath} 加载'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'加载失败: {str(e)}'
        }), 500


@app.route('/api/rl/state', methods=['GET'])
def get_rl_state():
    """获取强化学习状态向量
    
    返回当前系统状态，包括:
    - 当前参数值
    - 流量统计
    - 攻击检测指标
    """
    params = manager.get_all_params()
    stats = manager.get_statistics()
    
    # 构建状态向量
    state = {
        'params': params,
        'counters': stats.get('counters', {}),
        'sets': {
            name: info.get('count', 0) 
            for name, info in stats.get('sets', {}).items()
        },
        'conntrack_count': stats.get('conntrack_count', 0)
    }
    
    return jsonify({
        'success': True,
        'state': state
    })


@app.route('/api/rl/action', methods=['POST'])
def apply_rl_action():
    """应用强化学习动作
    
    请求体格式:
    {
        "actions": {
            "syn_defense.rate_limit": 150,
            "udp_defense.per_ip_rate": 80
        }
    }
    """
    data = request.get_json()
    actions = data.get('actions', {})
    
    if not actions:
        return jsonify({
            'success': False,
            'message': '缺少actions参数'
        }), 400
    
    success = manager.batch_update_params(actions)
    
    # 返回新状态
    new_state = manager.get_all_params()
    
    return jsonify({
        'success': success,
        'message': '动作应用' + ('成功' if success else '失败'),
        'new_state': new_state
    })


@app.route('/api/rl/reset', methods=['POST'])
def reset_to_default():
    """重置为默认参数"""
    global manager
    
    manager = NFTablesManager(DefenseConfig())
    success = manager.apply_rules()
    
    return jsonify({
        'success': success,
        'message': '已重置为默认参数',
        'params': manager.get_all_params()
    })


if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser(description='NFTables 防御系统 API 服务')
    parser.add_argument('--host', default='0.0.0.0', help='监听地址')
    parser.add_argument('--port', type=int, default=5000, help='监听端口')
    parser.add_argument('--apply-on-start', action='store_true', help='启动时应用规则')
    
    args = parser.parse_args()
    
    if args.apply_on_start:
        logger.info("启动时应用防御规则...")
        manager.apply_rules()
    
    logger.info(f"API服务启动在 {args.host}:{args.port}")
    app.run(host=args.host, port=args.port, threaded=True)
