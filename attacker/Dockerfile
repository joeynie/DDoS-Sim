FROM ubuntu:22.04

# 更新apt并安装必要的工具
RUN apt-get update && apt-get install -y python3 python3-pip iproute2 iputils-ping net-tools

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y hping3 vim
RUN pip3 install scapy requests

COPY attack.py /app/attack.py
COPY http_flood.py /app/http_flood.py
COPY hping_attack.sh /app/hping_attack.sh
COPY setup_victim.sh /app/setup_victim.sh
COPY simulated_reflection_attack.py /app/simulated_reflection_attack.py
COPY monitor_response.py /app/monitor_response.py
RUN chmod +x /app/simulated_reflection_attack.py
RUN chmod +x /app/*.sh /app/*.py
WORKDIR /app


# 启动容器时保持运行
CMD ["sh", "-c", "ip route add 10.10.20.0/24 via 10.10.10.5 && tail -f /dev/null"]