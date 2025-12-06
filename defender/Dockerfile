FROM ubuntu:22.04

RUN apt-get update && apt-get install -y iptables iproute2 procps iputils-ping python3 python3-pip tcpdump && \
    pip3 install scapy 
# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 安装必要的包
RUN apt-get update && apt-get install -y \
    nftables \
    iptables \
    iproute2 \
    procps \
    iputils-ping \
    python3 \
    python3-pip \
    conntrack \
    tcpdump \
    net-tools \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
RUN pip3 install flask requests

# 创建工作目录
WORKDIR /app

# 复制配置和脚本
COPY nftables_config.py /app/
COPY defense_api.py /app/
COPY start-defender.sh /usr/local/bin/start-defender.sh
COPY packet_monitor.py /usr/local/bin/packet_monitor.py

# 设置执行权限
RUN chmod +x /usr/local/bin/start-defender.sh
RUN chmod +x /usr/local/bin/packet_monitor.py

WORKDIR /usr/local/bin

# 暴露API端口
EXPOSE 5000

# 启动命令
CMD ["sh", "/usr/local/bin/start-defender.sh"]
