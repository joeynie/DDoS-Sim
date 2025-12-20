#!/usr/bin/env python3
"""Test DDoS Defense RL environment"""

import sys
import time
import requests
import os
from dotenv import load_dotenv

load_dotenv()

def test_defender_connection(url=None):
    """Test Defender API connection"""
    if url is None:
        url = "http://defender:5000" if os.environ.get('ENVIRONMENT') == 'docker' else "http://localhost:5001"
    
    print(f"\n[Test 1] Defender API: {url}")
    try:
        resp = requests.get(f"{url}/api/health", timeout=5)
        if resp.status_code == 200:
            print("✓ Connected")
            return True
        else:
            print(f"✗ Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_rl_state_api(url=None):
    """Test RL state API"""
    if url is None:
        url = "http://defender:5000" if os.environ.get('ENVIRONMENT') == 'docker' else "http://localhost:5001"
    
    print(f"\n[Test 2] RL State API")
    try:
        resp = requests.get(f"{url}/api/rl/state", timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            state = data.get('state', {})
            obs = state.get('obs', {})
            counters = state.get('counters', {})
            
            print("✓ State API OK")
            print(f"  TP={counters.get('tp_count', 0)}, FP={counters.get('fp_count', 0)}, "
                  f"TN={counters.get('tn_count', 0)}, FN={counters.get('fn_count', 0)}")
            print(f"  Obs dims: {len(obs)} (expected 11)")
            return True
        else:
            print(f"✗ Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_rl_action_api(url=None):
    """Test RL action API"""
    if url is None:
        url = "http://defender:5000" if os.environ.get('ENVIRONMENT') == 'docker' else "http://localhost:5001"
    
    print(f"\n[Test 3] RL Action API")
    try:
        payload = {
            "actions": {
                "global_limit": 5000,
                "single_ip_limit": 300,
                "conn_limit": 50,
                "ban_threshold": 5
            }
        }
        resp = requests.post(f"{url}/api/rl/action", json=payload, timeout=5)
        if resp.status_code == 200:
            print("✓ Action API OK")
            return True
        else:
            print(f"✗ Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def test_rl_reset_api(url=None):
    """Test RL reset API"""
    if url is None:
        url = "http://defender:5000" if os.environ.get('ENVIRONMENT') == 'docker' else "http://localhost:5001"
    
    print(f"\n[Test 4] RL Reset API")
    try:
        resp = requests.post(f"{url}/api/rl/reset", timeout=5)
        if resp.status_code == 200:
            print("✓ Reset API OK")
            return True
        else:
            print(f"✗ Status {resp.status_code}")
            return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False

def show_obs(obs, reward=None):
    """Display observation in single line, updating in place"""
    line = f"\r[Obs] ADR={obs[0]:.3f} NDR={obs[1]:.3f} ABN={obs[2]:.3f} SYN={obs[3]:.3f} UDP={obs[4]:.3f} MIR={obs[5]:.3f} CPU={obs[6]:.3f} TI={obs[7]:.3f} GL={obs[8]:.3f} SL={obs[9]:.3f} CL={obs[10]:.3f}"
    if reward is not None:
        line += f" | R={reward:.3f}"
    print(line, end='', flush=True)

def test_gym_environment():
    """Test Gymnasium environment"""
    print(f"\n[Test 5] Gymnasium Environment")
    from ddos_env import DDoSDefenseEnv
    
    defender_url = "http://defender:5000" if os.environ.get('ENVIRONMENT') == 'docker' else "http://localhost:5001"
    
    env = DDoSDefenseEnv(defender_url=defender_url)
    print("✓ Init OK")
    print(f"  Obs space: {env.observation_space}")
    print(f"  Action space: {env.action_space}")
    
    obs, info = env.reset()
    print("✓ Reset OK")
    
    try:
        step = 0
        while True:
            action = env.action_space.sample()
            obs, reward, terminated, truncated, info = env.step(action)
            show_obs(obs, reward)
            step += 1
    except KeyboardInterrupt:
        print(f"\n✓ Stopped at step {step}")
    finally:
        env.close()
        return True

def main():
    """Main"""
    print("\n" + "="*50)
    print("DDoS Defense RL Environment Test")
    print("="*50)
    
    results = []
    results.append(("Defender", test_defender_connection()))
    
    if results[0][1]:
        results.append(("RL State", test_rl_state_api()))
        results.append(("RL Action", test_rl_action_api()))
        results.append(("RL Reset", test_rl_reset_api()))
        results.append(("Gym Env", test_gym_environment()))
    
    print("\n" + "="*50)
    print("Summary")
    print("="*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✓" if result else "✗"
        print(f"  {status} {name}")
    
    print(f"\nTotal: {passed}/{total} passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
