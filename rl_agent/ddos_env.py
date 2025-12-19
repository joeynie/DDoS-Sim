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
    """
    DDoS防御环境
    
    动作空间：
        0: SYN限速 -20% (收紧)
        1: SYN限速 +20% (放松)
        2: UDP限速 -20% (收紧)
        3: UDP限速 +20% (放松)
        4: 保持不变
    
    观察空间：
        [attack_drop_rate, normal_drop_rate,           # 战况反馈（最重要）
         abnormal_ratio, syn_ratio, udp_ratio,         # 敌情特征
         max_ip_ratio, cpu_load, traffic_intensity,    # 自身状态
         global_limit, single_ip_limit, conn_limit]    # 当前策略
        归一化到 [0, 1]
        共 11 维
    
    奖励函数：
        +1.0 * TN (正确拦截攻击)
        +1.0 * TP (正确放行正常流量)
        -5.0 * FN (误杀正常流量，最严重)
        -1.0 * FP (漏过攻击)
    """
    
    def __init__(self, defender_url=None):
        super(DDoSDefenseEnv, self).__init__()
        
        # 从 .env 或参数获取 Defender URL
        if defender_url is None:
            defender_url = os.environ.get('DEFENDER_URL', 'http://defender:5000')
        
        self.defender_url = defender_url
        
        # 从 .env 读取其他配置
        self.max_steps = int(os.environ.get('MAX_STEPS_PER_EPISODE', 1000))
        self.sampling_interval = int(os.environ.get('SAMPLING_INTERVAL', 2))
        
        # === 动作空间 ===
        # 0: SYN限速 -20%
        # 1: SYN限速 +20%
        # 2: UDP限速 -20%
        # 3: UDP限速 +20%
        # 4: 保持不变
        self.action_space = spaces.Discrete(5)
        
        # === 观察空间 ===
        # 包含: [Delta_TP, Delta_FP, Delta_TN, Delta_FN, CPU_Load, 
        #        SYN_Ratio, UDP_Ratio, TTL_Abnormal_Ratio, Max_IP_Ratio,
        #        Current_SYN_Limit, Current_UDP_Limit]
        # 归一化到 [0, 1]，共 11 维
        self.observation_space = spaces.Box(low=0, high=1, shape=(11,), dtype=np.float32)
        
        # 内部状态缓存 (用于计算增量，对应 JS 中的 state.prevTotal)
        self.prev_counters = {
            'tp_count': 0, 
            'fp_count': 0, 
            'tn_count': 0, 
            'fn_count': 0
        }
        
        # 参数记录
        self.current_syn_limit = 1000
        self.current_udp_limit = 1000
        
        # 步数记录
        self.step_count = 0
        
        print(f"[RL Env] 初始化环境")
        print(f"  Defender URL: {self.defender_url}")
        print(f"  Max Steps: {self.max_steps}")
        print(f"  Sampling Interval: {self.sampling_interval}s")

    def step(self, action):
        """
        执行一个动作并返回新状态
        
        Gymnasium 返回格式:
            observation: 新的观察状态
            reward: 奖励值
            terminated: 是否因为目标完成而结束
            truncated: 是否因为时间步限制而截断
            info: 额外信息
        """
        self.step_count += 1
        
        # 1. 执行动作 (调用 /api/rl/action)
        self._apply_action(action)
        
        # 2. 等待环境反应 (非常重要，给 nftables 生效和流量产生统计的时间)
        time.sleep(self.sampling_interval) 
        
        # 3. 获取新状态 (调用 /api/rl/state)
        raw_state = self._fetch_state()
        
        # 4. 处理数据 & 计算奖励
        obs, metrics = self._process_observation(raw_state)
        reward = self._calculate_reward(metrics)
        
        # 5. 判断是否结束（Gymnasium 中需要 terminated 和 truncated）
        terminated = False  # 因目标完成结束（这里不使用）
        truncated = self.step_count >= self.max_steps  # 因时间限制结束
        
        info = {
            'metrics': metrics,
            'action': action,
            'step': self.step_count,
            'syn_limit': self.current_syn_limit,
            'udp_limit': self.current_udp_limit
        }
        
        return obs, reward, terminated, truncated, info

    def reset(self, seed=None, options=None):
        """
        重置环境
        
        Gymnasium 格式返回:
            observation: 初始观察状态
            info: 额外信息
        """
        super().reset(seed=seed)
        
        print(f"[RL Env] 重置环境 (Episode 结束)")
        
        # 调用 /api/rl/reset 重置参数
        try:
            resp = requests.post(f"{self.defender_url}/api/rl/reset", timeout=5)
            if resp.status_code == 200:
                print(f"[RL Env] 防御参数已重置")
            else:
                print(f"[RL Env] 重置失败: {resp.status_code}")
        except Exception as e:
            print(f"[RL Env] 重置请求失败: {e}")
        
        # 重置本地计数器
        self.prev_counters = {
            'tp_count': 0, 
            'fp_count': 0, 
            'tn_count': 0, 
            'fn_count': 0
        }
        self.step_count = 0
        
        # 等待重置生效
        time.sleep(2)
        
        # 获取初始状态
        raw_state = self._fetch_state()
        obs, _ = self._process_observation(raw_state)
        
        return obs, {}

    def _fetch_state(self):
        """
        从 Defender API 获取当前状态
        
        Returns:
            dict: 状态数据
        """
        try:
            resp = requests.get(f"{self.defender_url}/api/rl/state", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return data.get('state', {})
            else:
                print(f"[RL Env] 获取状态失败: {resp.status_code}")
        except Exception as e:
            print(f"[RL Env] 获取状态异常: {e}")
        return {}

    def _process_observation(self, raw_state):
        """
        处理原始状态，提取并归一化观察
        
        Args:
            raw_state: 从 API 获取的原始状态
            
        Returns:
            observation: 归一化的观察空间
            metrics: 指标字典（包含 Delta TP/FP/TN/FN）
        """
        # 从 /api/rl/state 获取 obs_json 和计数器
        state_obs = raw_state.get('obs', {})
        counters = raw_state.get('counters', {})
        
        # === 核心逻辑：计算增量 (复刻 JS 逻辑) ===
        tp = counters.get('tp_count', 0)
        fp = counters.get('fp_count', 0)
        tn = counters.get('tn_count', 0)
        fn = counters.get('fn_count', 0)
        
        # 计算增量 (Delta)
        delta_tp = max(0, tp - self.prev_counters['tp_count'])
        delta_fp = max(0, fp - self.prev_counters['fp_count'])
        delta_tn = max(0, tn - self.prev_counters['tn_count'])
        delta_fn = max(0, fn - self.prev_counters['fn_count'])
        
        # 更新上一帧状态
        self.prev_counters = {
            'tp_count': tp, 
            'fp_count': fp, 
            'tn_count': tn, 
            'fn_count': fn
        }
        
        # 战况反馈
        attack_drop_rate = state_obs.get('attack_drop_rate', 0.0)
        normal_drop_rate = state_obs.get('normal_drop_rate', 0.0)
        
        # 敌情特征
        abnormal_ratio = state_obs.get('abnormal_ratio', 0.0)
        syn_ratio = state_obs.get('syn_ratio', 0.0)
        udp_ratio = state_obs.get('udp_ratio', 0.0)
        max_ip_ratio = state_obs.get('max_ip_ratio', 0.0)
        
        # 自身状态
        cpu_load = state_obs.get('cpu_load', 0.0)
        traffic_intensity = state_obs.get('traffic_intensity', 0.0)
        
        # 当前策略参数
        curr_global_limit = state_obs.get('curr_global_limit', 10000)
        curr_single_ip_limit = state_obs.get('curr_single_ip_limit', 100)
        curr_conn_limit = state_obs.get('curr_conn_limit', 50)
        
        # 记录当前参数
        self.current_syn_limit = curr_single_ip_limit
        self.current_udp_limit = curr_single_ip_limit
        
        # === 归一化 ===
        MAX_LIMIT = 10000.0
        MAX_PPS = 10000.0
        
        obs = np.array([
            # 1. 战况反馈 (最重要)
            min(attack_drop_rate, 1.0),
            min(normal_drop_rate, 1.0),
            
            # 2. 敌情特征
            min(abnormal_ratio, 1.0),
            min(syn_ratio, 1.0),
            min(udp_ratio, 1.0),
            min(max_ip_ratio, 1.0),
            
            # 3. 自身状态
            min(cpu_load, 1.0),
            min(traffic_intensity / MAX_PPS, 1.0),
            
            # 4. 当前策略
            min(curr_global_limit / MAX_LIMIT, 1.0),
            min(curr_single_ip_limit / MAX_LIMIT, 1.0),
            min(curr_conn_limit / 1000.0, 1.0)
        ], dtype=np.float32)
        
        # 计算增量比率用于奖励
        metrics = {
            'tp': delta_tp, 
            'fp': delta_fp, 
            'tn': delta_tn, 
            'fn': delta_fn,
            'total': delta_tp + delta_fp + delta_tn + delta_fn,
            'attack_drop_rate': attack_drop_rate,
            'normal_drop_rate': normal_drop_rate
        }
        
        return obs, metrics

    def _calculate_reward(self, metrics):
        """
        计算奖励
        
        奖励函数设计：
        - 目标：拦截恶意(TN)，放行正常(TP)
        - 严惩：误杀正常请求(FN)，漏过攻击(FP)
        
        Args:
            metrics: 指标字典
            
        Returns:
            float: 奖励值
        """
        tp = metrics['tp']  # True Positive: 正确放行正常流量
        tn = metrics['tn']  # True Negative: 正确拦截攻击
        fp = metrics['fp']  # False Positive: 漏过的攻击
        fn = metrics['fn']  # False Negative: 误杀的正常请求 (最严重)
        
        total = metrics['total']
        
        # 如果没有流量，返回小的负奖励（鼓励保持活跃）
        if total == 0:
            return -0.1
        
        # === 奖励公式 ===
        # +1.0 * 拦截成功 (TN)
        # +1.0 * 正常放行 (TP)
        # -5.0 * 误杀 (FN) - Penalty 最高
        # -1.0 * 漏过 (FP)
        reward = (tn * 1.0) + (tp * 1.0) - (fn * 5.0) - (fp * 1.0)
        
        # 归一化奖励，防止数值过大
        normalized_reward = reward / (total + 1e-5)
        
        return normalized_reward

    def _apply_action(self, action):
        """
        应用动作到防御系统
        
        Args:
            action: 动作编号 (0-4)
        """
        new_syn = self.current_syn_limit
        new_udp = self.current_udp_limit
        
        # 根据动作调整参数
        if action == 0:  # SYN 收紧
            new_syn = max(10, int(new_syn * 0.8))
        elif action == 1:  # SYN 放松
            new_syn = min(5000, int(new_syn * 1.2))
        elif action == 2:  # UDP 收紧
            new_udp = max(10, int(new_udp * 0.8))
        elif action == 3:  # UDP 放松
            new_udp = min(5000, int(new_udp * 1.2))
        # action == 4: 保持不变
        
        # 只有在参数变化时才发送请求
        if action != 4 and (new_syn != self.current_syn_limit or new_udp != self.current_udp_limit):
            payload = {
                "actions": {
                    "syn_defense.rate_limit": new_syn,
                    "udp_defense.per_ip_rate": new_udp
                }
            }
            
            try:
                resp = requests.post(
                    f"{self.defender_url}/api/rl/action", 
                    json=payload, 
                    timeout=2
                )
                
                if resp.status_code == 200:
                    print(f"[RL Env] 动作 {action} 执行成功: SYN={new_syn}, UDP={new_udp}")
                else:
                    print(f"[RL Env] 动作执行失败: {resp.status_code}")
            except Exception as e:
                print(f"[RL Env] 动作执行异常: {e}")
        elif action == 4:
            print(f"[RL Env] 动作 4: 保持当前配置")

    def render(self, mode='human'):
        """渲染环境（可选）"""
        pass
    
    def close(self):
        """关闭环境"""
        print(f"[RL Env] 环境关闭")
