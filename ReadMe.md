# DDoS-Sim

DDoS攻击模拟和防护教学平台，包含HTTP洪水攻击、SYN洪水攻击、UDP洪水攻击和僵尸网络攻击的演示。

## 快速开始

### 僵尸网络攻击演示 (推荐)
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

docker-compose down
```

### SYN洪水攻击教学实验
```bash
docker-compose up -d --build

# 1. 配置受害者系统为易受攻击状态
docker exec -it victim bash
./setup_victim.sh vulnerable

# 2. 执行SYN攻击
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

docker-compose down
```

### 在defender上实时获取收到的所有包的信息
注：请单开一个终端，运行以下代码；同时可以在原终端中攻击，查看结果
docker-compose up -d --build
docker exec -it defender bash
python3 packet_monitor.py -i eth0

## 功能特性

### 🤖 僵尸网络攻击 (最新)
- **分布式攻击**: 5个独立bot节点，模拟真实僵尸网络
- **C&C控制**: Web控制面板，实时监控和控制
- **多源IP**: 来自不同IP的协同攻击，难以防御
- **实时统计**: 每个bot的攻击状态和流量统计

### 🎯 SYN洪水攻击
- **教学导向**: 详细解释TCP三次握手和SYN队列原理
- **参数调整**: 自动建议受害者系统TCP参数配置
- **增强攻击**: 针对缩短队列优化的高效攻击算法
- **安全恢复**: 提供参数恢复建议和脚本

### 📡 UDP洪水攻击
- **UDP放大攻击**: 模拟真实的UDP放大攻击
- **丢包检测**: UDP Echo服务器，实时检测丢包率
- **多种强度**: 可配置线程数和放大倍数

### 🌊 HTTP洪水攻击
- 多线程并发请求
- 可配置攻击强度和持续时间
- 支持带参数的API端点攻击

### 🛡️ 防护演示
- 展示不同参数配置对攻击效果的影响
- SYN Cookies防护机制演示
- 系统参数优化建议
- 分布式攻击防御挑战

## 详细教程

- [僵尸网络攻击教程](./Botnet_Tutorial.md) - 分布式DDoS攻击演示
- [SYN攻击教学实验](./SYN_Attack_Tutorial.md) - TCP SYN Flood攻击
- [UDP攻击测试指南](./UDP_Attack_Test_Guide.md) - UDP Flood攻击和丢包检测

## 测试访问
- 攻击前后，浏览器访问: http://localhost:8080/api/status
- 观察响应时间和可用性变化

## 系统兼容性

### Windows 用户
- 查看 [Windows使用指南](./Windows_Usage.md) 获取详细说明
- 使用PowerShell执行Docker命令
- 已解决bash不存在的问题

### Linux/macOS 用户
- 直接使用终端执行命令
- 支持所有功能特性