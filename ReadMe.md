# DDoS-Sim

DDoS攻击模拟和防护教学平台，包含HTTP洪水攻击和SYN洪水攻击的演示。

## 快速开始

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

## 功能特性

### 🎯 SYN洪水攻击 (新增)
- **教学导向**: 详细解释TCP三次握手和SYN队列原理
- **参数调整**: 自动建议受害者系统TCP参数配置
- **增强攻击**: 针对缩短队列优化的高效攻击算法
- **安全恢复**: 提供参数恢复建议和脚本

### 🌊 HTTP洪水攻击
- 多线程并发请求
- 可配置攻击强度和持续时间
- 支持带参数的API端点攻击

### 🛡️ 防护演示
- 展示不同参数配置对攻击效果的影响
- SYN Cookies防护机制演示
- 系统参数优化建议

## 详细教程

查看 [SYN攻击教学实验](./SYN_Attack_Tutorial.md) 获取完整的实验指导。

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