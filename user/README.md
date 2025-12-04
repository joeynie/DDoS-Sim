# User 组件 - 正常用户流量模拟器

## 概述

User组件模拟正常用户的网络活动，向victim服务器发送少量的TCP和UDP包。这些包通过defender转发，设置TTL为33。

## 功能特性

- **TCP流量**: 连接到victim的TCP服务器（8888端口），发送正常的用户请求
- **UDP流量**: 发送UDP包到victim的UDP回显服务器（9999端口）
- **TTL控制**: 所有包的TTL都设置为33
- **真实模拟**: 包含随机延迟，模拟真实用户行为
- **多种模式**: 支持自动运行和交互模式

## 网络拓扑

```
User (10.10.10.20) → Defender (10.10.10.5) → Victim (10.10.20.20)
```

User连接到`attack_net`，发送的包通过defender转发到victim。

## 使用方法

### 1. 启动环境
```bash
# 启动所有容器（包括user）
docker-compose up -d

# 或者只启动user
docker-compose up -d user
```

### 2. 运行模拟器

#### 自动模式（默认）
```bash
# 运行10个循环，每10秒一个循环
docker exec -it user python3 /usr/local/bin/user_traffic_simulator.py

# 自定义参数
docker exec -it user python3 /usr/local/bin/user_traffic_simulator.py --cycles 5 --interval 15
```

#### 交互模式
```bash
docker exec -it user python3 /usr/local/bin/user_traffic_simulator.py --interactive
```

在交互模式中，你可以选择：
- 发送TCP包
- 发送UDP包
- 运行完整模拟
- 退出

### 3. 查看日志
```bash
# 查看user容器日志
docker logs user

# 实时查看日志
docker logs -f user
```

## 技术细节

### TCP流量
- **目标**: victim:8888 (TCP服务器)
- **行为**: 建立连接 → 发送数据 → 接收响应 → 随机等待 → 关闭连接
- **TTL**: 33
- **消息示例**: "USER_TCP_REQUEST: Hello from normal user!"

### UDP流量
- **目标**: victim:9999 (UDP回显服务器)
- **行为**: 发送UDP包 → 尝试接收响应 → 随机等待
- **TTL**: 33
- **消息示例**: "USER_UDP_PACKET: DNS query from user | SEQ:1 | TIME:14:30:25"

### 包结构
所有包都包含：
- 时间戳
- 序列号
- 描述性消息
- TTL=33

## 监控和调试

### 在defender中查看包
```bash
# 进入defender查看实时包监控
docker exec -it defender python3 /usr/local/bin/packet_monitor.py -i any
```

### 检查网络连接
```bash
# 检查user到victim的连通性
docker exec user ping -c 3 10.10.20.20

# 检查user的网络配置
docker exec user ip route
docker exec user ip addr
```

### 验证TTL设置
```bash
# 在defender中抓包验证TTL
docker exec defender tcpdump -i any -v 'host 10.10.10.20' | grep ttl
```

## 参数说明

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--victim-ip` | 10.10.20.20 | 受害者服务器IP |
| `--tcp-port` | 8888 | TCP服务器端口 |
| `--udp-port` | 9999 | UDP服务器端口 |
| `--cycles` | 10 | 模拟循环次数 |
| `--interval` | 10 | 循环间隔（秒） |
| `--interactive` | False | 启用交互模式 |

## 示例输出

```
🏠 用户流量模拟器启动
🎯 目标: 10.10.20.20
🔌 TCP端口: 8888, UDP端口: 9999
⏰ TTL: 33
--------------------------------------------------

🚀 开始用户流量模拟
🔄 循环次数: 10
⏱️  循环间隔: 10秒
==================================================

🎯 循环 1/10 - 14:30:15

🔄 发送 3 个TCP包到 10.10.20.20:8888
  [1] 连接到 10.10.20.20:8888...
      ✓ 连接成功 (0.023s)
      📤 发送: USER_TCP_REQUEST: Hello from normal user!
      📥 响应: [ECHO 1703856615.234] USER_TCP_REQUEST: Hello from normal user!
      ⏱️  等待 2.3秒...
      ✓ TCP包 1 发送完成
  ...

📡 发送 5 个UDP包到 10.10.20.20:9999
  [1] 发送UDP包: USER_UDP_PACKET: DNS query from user | SEQ:1 | TIME:14:30:25
      📥 响应: [1] USER_UDP_PACKET: DNS query from user | SEQ:1 | TIME:14:30:25
      ⏱️  等待 1.1秒...
      ✓ UDP包 1 发送完成
  ...
```

## 故障排除

### 连接失败
- 检查defender是否正在运行转发规则
- 确认victim的服务正在监听相应端口
- 检查网络配置：`docker exec defender iptables -L FORWARD`

### 包未到达
- 在defender上运行包监控器确认包是否通过
- 检查TTL设置是否正确
- 验证网络路由配置

### 性能问题
- 减少循环间隔或包数量
- 检查系统资源使用情况
- 确认没有其他进程干扰网络

## 扩展功能

可以扩展user组件来：
- 添加更多协议（HTTP, ICMP等）
- 模拟不同的用户行为模式
- 添加流量模式配置文件
- 集成到C2服务器的控制面板中
