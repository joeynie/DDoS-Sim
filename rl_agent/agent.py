#!/usr/bin/env python3
"""RL Agent - PPO training for DDoS defense"""

from stable_baselines3 import PPO
from ddos_env import DDoSDefenseEnv
import time
import os
import requests
from dotenv import load_dotenv

load_dotenv()

def wait_for_defender(defender_url, max_retries=30):
    """Wait for Defender API to start"""
    print(f"[Agent] Wait for Defender...")
    
    for i in range(max_retries):
        try:
            if requests.get(f"{defender_url}/api/health", timeout=2).status_code == 200:
                print(f"[Agent] ✓ Connected to Defender")
                return True
        except:
            pass
        
        print(f"[Agent] Retry {i+1}/{max_retries}...")
        time.sleep(3)
    
    print(f"[Agent] ✗ Failed to connect to Defender")
    return False

def train_model(env, model_path, total_timesteps=10000, resume=False, log_dir="./logs"):
    learning_rate = float(os.environ.get('LEARNING_RATE', '0.0003'))
    n_steps = int(os.environ.get('N_STEPS', '2048'))
    batch_size = int(os.environ.get('BATCH_SIZE', '64'))
    model_file = f"{model_path}.zip"
    
    os.makedirs(log_dir, exist_ok=True)
    
    # 决定是加载还是创建模型
    if os.path.exists(model_file) and resume:
        print(f"[Agent] Resume from: {model_path}")
        model = PPO.load(model_path, env=env, tensorboard_log=log_dir, device="cpu")
        reset_num_timesteps = False
        print(f"[Agent] Keep n_steps={model.n_steps} from checkpoint")
    else:
        print(f"[Agent] Create new model (LR={learning_rate}, n_steps={n_steps}, batch={batch_size})")
        model = PPO("MlpPolicy", env, verbose=1, learning_rate=learning_rate, 
                    n_steps=n_steps, batch_size=batch_size, n_epochs=10, 
                    gamma=0.99, gae_lambda=0.95, clip_range=0.2, ent_coef=0.01,
                    tensorboard_log=log_dir, device="cpu")
        reset_num_timesteps = True
    
    print(f"[Agent] Training for {total_timesteps} steps...")
    print(f"[Agent] Tensorboard: tensorboard --logdir={log_dir}")
    
    try:
        model.learn(total_timesteps=total_timesteps, reset_num_timesteps=reset_num_timesteps)
        model.save(model_path)
        print(f"[Agent] ✓ Model saved: {model_path}")
        return model
    except KeyboardInterrupt:
        model.save(model_path)
        print(f"[Agent] Interrupted, model saved")
        return model
    except Exception as e:
        print(f"[Agent] ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        model.save(f"{model_path}_error")
        return None

def infer(env, model, delay=5):
    """Inference mode - real-time defense"""
    print(f"\n{'='*50}\nInference Mode\n{'='*50}\n")
    
    obs, info = env.reset()
    episode_reward = 0
    step = 0
    episodes = 0
    
    try:
        while True:
            action, _ = model.predict(obs, deterministic=True)
            obs, reward, terminated, truncated, info = env.step(action)
            episode_reward += reward
            step += 1
            
            metrics = info.get('metrics', {})
            attack_drop = metrics.get('attack_drop_rate', 0)
            normal_drop = metrics.get('normal_drop_rate', 0)
            
            if step % 10 == 0:
                print(f"[Ep {episodes} Step {step}] R={reward:.3f} Cum={episode_reward:.2f} | "
                      f"Attack={attack_drop:.2f} | Normal={normal_drop:.2f}")
            
            if terminated or truncated:
                episodes += 1
                print(f"[Episode {episodes}] Done | Total Reward={episode_reward:.2f}")
                obs, info = env.reset()
                episode_reward = 0
                step = 0
            
            if delay > 0:
                time.sleep(delay)
    except KeyboardInterrupt:
        print(f"\nInference stopped after {episodes} episodes")

def main():
    """Main"""
    print("="*50)
    print("DDoS Defense RL Agent")
    print("="*50)
    
    DEFENDER_URL = os.environ.get('DEFENDER_URL', 'http://defender:5000')
    MODEL_PATH = os.environ.get('MODEL_PATH', '/app/models/ppo_ddos_defense')
    TRAINING_STEPS = int(os.environ.get('TRAINING_STEPS', '5000'))
    MODE = os.environ.get('MODE', 'train')
    RESUME = os.environ.get('RESUME', 'false').lower() == 'true'
    LOG_DIR = os.environ.get('LOG_DIR', './logs')
    
    print(f"Defender: {DEFENDER_URL}")
    print(f"Model: {MODEL_PATH}")
    print(f"Steps: {TRAINING_STEPS}")
    print(f"Mode: {MODE}")
    print(f"Resume: {RESUME}")
    print(f"Logs: {LOG_DIR}")
    print("="*50)
    
    if not wait_for_defender(DEFENDER_URL):
        print("[Agent] Cannot connect to Defender")
        return
    
    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    print(f"\n[Agent] Init environment...")
    env = DDoSDefenseEnv(defender_url=DEFENDER_URL)
    
    if MODE == 'train':
        model = train_model(env, MODEL_PATH, TRAINING_STEPS, resume=RESUME, log_dir=LOG_DIR)
    elif MODE == 'infer':
        model_file = f"{MODEL_PATH}.zip"
        if not os.path.exists(model_file):
            print(f"[Agent] Model not found: {model_file}")
            return
        print(f"[Agent] Load model: {MODEL_PATH}")
        model = PPO.load(MODEL_PATH, env=env, device="cpu")
        infer(env, model)
    else:
        print(f"[Agent] Unknown mode: {MODE}")

if __name__ == "__main__":
    main()
