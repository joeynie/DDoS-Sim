FROM ubuntu:22.04

RUN apt-get update && apt-get install -y iptables iproute2 procps iputils-ping python3 python3-pip tcpdump && \
    pip3 install scapy 

# 复制并赋予启动脚本执行权限
COPY start-defender.sh /usr/local/bin/start-defender.sh
COPY packet_monitor.py /usr/local/bin/packet_monitor.py
RUN chmod +x /usr/local/bin/start-defender.sh
RUN chmod +x /usr/local/bin/packet_monitor.py

WORKDIR /usr/local/bin

CMD ["sh", "/usr/local/bin/start-defender.sh"]