# DDoS-Sim

DDoS攻击模拟和防护教学平台，包含HTTP洪水攻击、SYN洪水攻击、UDP洪水攻击和僵尸网络攻击的演示。

## 攻击

### 僵尸网络攻击演示
```bash
# 启动所有容器（包括5个bot）
docker-compose up -d --build

# 访问Web控制面板
# 浏览器打开: http://localhost:5000

# 配置攻击参数并点击"开始攻击"
# 观察实时统计和攻击效果

docker-compose down
```

### HTTP洪水攻击演示
```bash
docker-compose up -d --build

# 进行HTTP攻击
docker exec -it attacker bash
python3 http_flood.py http://10.10.20.20/api/status?delay=1000 10 100 60
python3 http_flood.py http://10.10.20.20/api/status?delay=1000 10 100 0

docker-compose down
```

### SYN洪水攻击
```bash
docker-compose up -d --build

# 1. 执行SYN攻击
docker exec -it attacker bash
python3 attack.py 10.10.20.20 80

# 3. 恢复安全配置
docker exec -it victim bash
./setup_victim.sh secure

docker-compose down
```

### UDP洪水攻击测试
```bash
docker-compose up -d --build

# 终端1：监控丢包率
docker exec -it attacker bash
python3 udp_test_client.py 10.10.20.20 ping

# 终端2：启动UDP攻击
docker exec -it attacker bash
python3 udp_amplification_9999.py 10.10.20.20 50 60 100
python3 udp_amplification_9999.py 10.10.20.20 5 0 10
docker-compose down
```

## 防御
防御监控平台： http://10.10.10.5:5000/ 
ps by nx：之后可以换个port，与僵尸网络错开；以及c2应该可以整合进attacker 

### 在defender上实时获取收到的所有包的信息
注：请单开一个终端，运行以下代码；同时可以在原终端中攻击，查看结果
```bash
docker-compose up -d --build
docker exec -it defender bash
python3 packet_monitor.py -i eth0
```

### 控制 NFTables 防御 (手动/API)

防御 API 默认运行在宿主机端口 5001。

查看当前防御统计 (包含 F1 Score):
```bash
curl http://localhost:5001/api/stats
```
手动调整防御参数 (模拟 RL 动作)的示例:
```bash
curl -X POST http://localhost:5001/api/params/update \
  -H "Content-Type: application/json" \
  -d '{"batch":{"global_limit":5000,"single_ip_limit":50}}'
```


### 测试访问
- 攻击前后，浏览器访问: http://localhost:8888/api/status
- 观察响应时间和可用性变化


## 🆕 强化学习自适应防御

### 快速启动 RL 防御
- docker版
```bash
docker-compose up -d
docker-compose logs -f rl_agent
```
- 本地版
```bash
# 修改rl_agent/.env， 选择train/infer
python rl_agent/agent.py
```

### 访问面板
- 🎯 Victim 服务: http://localhost:8888
- 🛡️ Defender 面板: http://localhost:5001
- 🤖 C&C 控制台: http://localhost:5000