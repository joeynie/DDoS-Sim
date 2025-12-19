#!/usr/bin/env python3
"""
RL Agent 训练脚本
使用 PPO (Proximal Policy Optimization) 算法训练 DDoS 防御策略
"""

from stable_baselines3 import PPO
from stable_baselines3.common.callbacks import BaseCallback
from ddos_env import DDoSDefenseEnv
import time
import os
import requests
from dotenv import load_dotenv

# 加载 .env 文件中的环境变量
load_dotenv()

class TrainingCallback(BaseCallback):
    """
    自定义回调，用于监控训练进度
    """
    def __init__(self, check_freq=100, verbose=1):
        super(TrainingCallback, self).__init__(verbose)
        self.check_freq = check_freq
        self.best_mean_reward = -float('inf')
        
    def _on_step(self):
        if self.n_calls % self.check_freq == 0:
            # 打印当前进度
            print(f"\n{'='*60}")
            print(f"Training Step: {self.n_calls}")
            print(f"Episode: {self.num_timesteps}")
            print(f"{'='*60}\n")
        return True

def wait_for_defender(defender_url, max_retries=30):
    """
    等待 Defender 服务启动
    
    Args:
        defender_url: Defender API 地址
        max_retries: 最大重试次数
    
    Returns:
        bool: 是否成功连接
    """
    print(f"[RL Agent] 等待 Defender API 启动...")
    
    for i in range(max_retries):
        try:
            resp = requests.get(f"{defender_url}/api/health", timeout=2)
            if resp.status_code == 200:
                print(f"[RL Agent] ✓ 成功连接到 Defender!")
                return True
        except:
            pass
        
        print(f"[RL Agent] 重试 {i+1}/{max_retries}...")
        time.sleep(3)
    
    print(f"[RL Agent] ✗ 无法连接到 Defender")
    return False

def train_model(env, model_path, total_timesteps=10000):
    """
    训练模型
    
    Args:
        env: Gymnasium 环境
        model_path: 模型保存路径
        total_timesteps: 总训练步数
    """
    # 从 .env 读取超参数
    learning_rate = float(os.environ.get('LEARNING_RATE', '0.0003'))
    batch_size = int(os.environ.get('BATCH_SIZE', '64'))
    
    # 检查是否有已存在的模型
    model_file = f"{model_path}.zip"
    
    if os.path.exists(model_file):
        print(f"[RL Agent] 加载已有模型: {model_path}")
        model = PPO.load(model_path, env=env)
        print(f"[RL Agent] 继续训练...")
    else:
        print(f"[RL Agent] 创建新模型...")
        model = PPO(
            "MlpPolicy",  # 多层感知机策略
            env,
            verbose=1,
            learning_rate=learning_rate,
            n_steps=2048,
            batch_size=batch_size,
            n_epochs=10,
            gamma=0.99,
            gae_lambda=0.95,
            clip_range=0.2,
            ent_coef=0.01,  # 熵系数，鼓励探索
        )
        print(f"  Learning Rate: {learning_rate}")
        print(f"  Batch Size: {batch_size}")
    
    # 创建回调
    callback = TrainingCallback(check_freq=100)
    
    # 开始训练
    print(f"[RL Agent] 开始训练 (总步数: {total_timesteps})...")
    sampling_interval = int(os.environ.get('SAMPLING_INTERVAL', '2'))
    print(f"[RL Agent] 预计耗时: {total_timesteps * sampling_interval / 60:.1f} 分钟")
    
    try:
        model.learn(
            total_timesteps=total_timesteps,
            callback=callback,
            reset_num_timesteps=False  # 继续之前的训练
        )
        model.save(model_path)
        print(f"[RL Agent] ✓ 模型已保存: {model_path}")
        return model
    except KeyboardInterrupt:
        print(f"\n[RL Agent] 训练被中断，保存当前模型...")
        model.save(model_path)
        print(f"[RL Agent] ✓ 模型已保存")
        return model
    except Exception as e:
        print(f"[RL Agent] ✗ 训练出错: {e}")
        model.save(f"{model_path}_error")
        return None

def inference_mode(env, model, delay=5):
    """
    推理模式 - 使用训练好的模型进行实时防御
    
    Args:
        env: Gymnasium 环境
        model: 训练好的模型
        delay: 每次动作之间的延迟（秒）
    """
    print(f"\n{'='*60}")
    print(f"进入推理模式 (实时防御)")
    print(f"{'='*60}\n")
    
    obs, info = env.reset()
    episode_reward = 0
    step = 0
    
    try:
        while True:
            # 使用模型预测动作
            action, _states = model.predict(obs, deterministic=True)
            
            # 执行动作
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            step += 1
            
            # 打印信息
            metrics = info.get('metrics', {})
            print(f"[Step {step}] Action: {action}, Reward: {reward:.4f}, "
                  f"Cumulative: {episode_reward:.2f}")
            print(f"  TP={metrics.get('tp', 0)}, FP={metrics.get('fp', 0)}, "
                  f"TN={metrics.get('tn', 0)}, FN={metrics.get('fn', 0)}")
            print(f"  SYN_Limit={info.get('syn_limit')}, "
                  f"UDP_Limit={info.get('udp_limit')}")
            
            # 如果 episode 结束，重置
            if terminated or truncated:
                print(f"\n[Episode 结束] 总奖励: {episode_reward:.2f}")
                obs, info = env.reset()
                episode_reward = 0
                step = 0
            
            # 额外延迟
            if delay > 0:
                time.sleep(delay)
                
    except KeyboardInterrupt:
        print(f"\n[RL Agent] 推理模式停止")

def main():
    """主函数"""
    print("="*60)
    print("DDoS Defense RL Agent")
    print("="*60)
    
    # 配置
    DEFENDER_URL = os.environ.get('DEFENDER_URL', 'http://defender:5000')
    MODEL_PATH = os.environ.get('MODEL_PATH', '/app/models/ppo_ddos_defense')
    TRAINING_STEPS = int(os.environ.get('TRAINING_STEPS', '5000'))
    MODE = os.environ.get('MODE', 'train')  # 'train' or 'inference'
    
    print(f"配置:")
    print(f"  Defender URL: {DEFENDER_URL}")
    print(f"  Model Path: {MODEL_PATH}")
    print(f"  Training Steps: {TRAINING_STEPS}")
    print(f"  Mode: {MODE}")
    print("="*60)
    
    # 等待 Defender 启动
    if not wait_for_defender(DEFENDER_URL):
        print("[RL Agent] 无法连接到 Defender，退出")
        return
    
    # 创建模型目录
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    
    # 初始化环境
    print(f"\n[RL Agent] 初始化环境...")
    env = DDoSDefenseEnv(defender_url=DEFENDER_URL)
    
    if MODE == 'train':
        # 训练模式
        model = train_model(env, MODEL_PATH, TRAINING_STEPS)
        
        if model is None:
            print("[RL Agent] 训练失败，退出")
            return
        
        # 训练完成后询问是否进入推理模式
        print("\n训练完成！")
        
    elif MODE == 'inference':
        # 仅推理模式
        model_file = f"{MODEL_PATH}.zip"
        if not os.path.exists(model_file):
            print(f"[RL Agent] 模型文件不存在: {model_file}")
            return
        
        print(f"[RL Agent] 加载模型: {MODEL_PATH}")
        model = PPO.load(MODEL_PATH, env=env)
        inference_mode(env, model)
    
    else:
        print(f"[RL Agent] 未知模式: {MODE}")

if __name__ == "__main__":
    main()
