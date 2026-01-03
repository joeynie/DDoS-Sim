FROM ubuntu:22.04
# 避免交互式安装
ENV DEBIAN_FRONTEND=noninteractive

# 安装必要的包
RUN apt-get update && apt-get install -y nftables iptables iproute2 procps iputils-ping python3 python3-pip \
    conntrack tcpdump net-tools vim \
    && rm -rf /var/lib/apt/lists/*

RUN pip3 install scapy

# 安装Python依赖
RUN pip3 install flask requests psutil

# 创建工作目录
WORKDIR /app

# 复制配置和脚本
COPY nftables_config.py /app/
COPY defense_api.py /app/
COPY packet_monitor.py /app/packet_monitor.py
COPY start-defender.sh /usr/local/bin/start-defender.sh

# 复制前端文件
COPY templates/ /app/templates/
COPY static/ /app/static/

# 设置执行权限
RUN chmod +x /app/packet_monitor.py
RUN chmod +x /usr/local/bin/start-defender.sh

EXPOSE 5000

CMD ["sh", "/usr/local/bin/start-defender.sh"]
# CMD ["tail", "-f", "/dev/null"]