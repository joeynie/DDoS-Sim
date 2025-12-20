#!/usr/bin/env python3
"""
DDoS Defense Gymnasium Environment
用于强化学习训练的环境，通过 Defender API 与防御系统交互
"""

import gymnasium as gym
import numpy as np
import requests
import time
import os
from gymnasium import spaces
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()

class DDoSDefenseEnv(gym.Env):
    """DDoS Defense RL Environment
    
    Observation (11D, normalized [0,1]):
      [attack_drop_rate, normal_drop_rate,           # 战况反馈
       abnormal_ratio, syn_ratio, udp_ratio,         # 敌情特征
       max_ip_ratio, cpu_load, traffic_intensity,    # 自身状态
       global_limit, single_ip_limit, conn_limit]
    
    Action (4D, normalized [0,1]):
      [global_limit, single_ip_limit, conn_limit, ban_threshold]
    
    Reward: (TN + TP - 5*FN - FP) / total
    """
    
    def __init__(self, defender_url=None):
        super(DDoSDefenseEnv, self).__init__()
        
        if defender_url is None:
            defender_url = os.environ.get('DEFENDER_URL', 'http://defender:5000')
        
        self.defender_url = defender_url
        self.max_steps = int(os.environ.get('MAX_STEPS_PER_EPISODE', 1000))
        self.sampling_interval = int(os.environ.get('SAMPLING_INTERVAL', 2))
        
        # 参数范围（来自RLDefenseConfig）
        self.param_ranges = {
            'global_limit': {'min': 1000, 'max': 100000},
            'single_ip_limit': {'min': 10, 'max': 5000},
            'conn_limit': {'min': 10, 'max': 1000},
            'ban_threshold': {'min': 1, 'max': 100}
        }
        
        # 动作空间：4个连续参数，归一化到[0,1]
        self.action_space = spaces.Box(low=0, high=1, shape=(4,), dtype=np.float32)
        
        # 观察空间：11维，归一化到[0,1]
        self.observation_space = spaces.Box(low=0, high=1, shape=(11,), dtype=np.float32)
        
        self.step_count = 0
        
        print(f"[Env] Init: {self.defender_url}")

    def step(self, action):
        """Execute action, return (obs, reward, terminated, truncated, info)"""
        self.step_count += 1
        self._apply_action(action)
        time.sleep(self.sampling_interval)
        raw_state = self._fetch_state()
        obs, metrics = self._process_observation(raw_state)
        reward = self._calculate_reward(metrics)
        truncated = self.step_count >= self.max_steps
        
        return obs, reward, False, truncated, {'metrics': metrics, 'action': action, 'step': self.step_count}

    def reset(self, seed=None, options=None):
        """Reset environment"""
        super().reset(seed=seed)
        
        try:
            requests.post(f"{self.defender_url}/api/rl/reset", timeout=5)
        except:
            pass
        
        self.step_count = 0
        time.sleep(1)
        
        raw_state = self._fetch_state()
        obs, _ = self._process_observation(raw_state)
        return obs, {}

    def _fetch_state(self):
        """Fetch state from Defender API"""
        try:
            resp = requests.get(f"{self.defender_url}/api/rl/state", timeout=5)
            if resp.status_code == 200:
                return resp.json().get('state', {})
        except:
            pass
        return {}

    def _process_observation(self, raw_state):
        """Process raw state into normalized observation and metrics"""
        state_obs = raw_state.get('obs', {})
        
        # 提取特征（已从API归一化）
        obs = np.array([
            state_obs.get('attack_drop_rate', 0.0),
            state_obs.get('normal_drop_rate', 0.0),
            state_obs.get('abnormal_ratio', 0.0),
            state_obs.get('syn_ratio', 0.0),
            state_obs.get('udp_ratio', 0.0),
            state_obs.get('max_ip_ratio', 0.0),
            state_obs.get('cpu_load', 0.0),
            min(state_obs.get('traffic_intensity', 0.0) / 10000.0, 1.0),
            min(state_obs.get('curr_global_limit', 10000) / 100000.0, 1.0),
            min(state_obs.get('curr_single_ip_limit', 100) / 5000.0, 1.0),
            min(state_obs.get('curr_conn_limit', 50) / 1000.0, 1.0)
        ], dtype=np.float32)
        
        metrics = {
            'attack_drop_rate': state_obs.get('attack_drop_rate', 0.0),
            'normal_drop_rate': state_obs.get('normal_drop_rate', 0.0)
        }
        return obs, metrics

    def _calculate_reward(self, metrics):
        """Reward: attack_drop_rate - 5*normal_drop_rate"""
        attack_drop_rate = metrics['attack_drop_rate']
        normal_drop_rate = metrics['normal_drop_rate']
        
        # 鼓励高拦截率，严重惩罚误杀
        reward = attack_drop_rate - 5.0 * normal_drop_rate
        return reward

    def _apply_action(self, action):
        """Apply normalized action [global_limit, single_ip_limit, conn_limit, ban_threshold] to API"""
        # print(f"[RL Env] action: {action}")
        action = np.clip(action, 0, 1)
        
        # 反归一化为实际参数值
        params = {}
        param_names = ['global_limit', 'single_ip_limit', 'conn_limit', 'ban_threshold']
        
        for i, name in enumerate(param_names):
            min_val = self.param_ranges[name]['min']
            max_val = self.param_ranges[name]['max']
            params[name] = int(min_val + action[i] * (max_val - min_val))
        
        payload = {"actions": {
            "global_limit": params['global_limit'],
            "single_ip_limit": params['single_ip_limit'],
            "conn_limit": params['conn_limit'],
            "ban_threshold": params['ban_threshold']
        }}
        
        try:
            requests.post(f"{self.defender_url}/api/rl/action", json=payload, timeout=2)
        except:
            pass

    def render(self, mode='human'):
        """渲染环境（可选）"""
        pass
    
    def close(self):
        """关闭环境"""
        print(f"[RL Env] 环境关闭")
