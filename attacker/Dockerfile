FROM ubuntu:22.04

# 更新apt并安装必要的工具
RUN apt-get update && apt-get install -y python3 python3-pip iproute2 iputils-ping net-tools

RUN pip3 install scapy

COPY attack.py /app/attack.py
WORKDIR /app

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get install -y hping3

# 启动容器时保持运行
CMD ["sh", "-c", "ip route add 10.10.20.0/24 via 10.10.10.5 && tail -f /dev/null"]