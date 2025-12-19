FROM ubuntu:22.04

RUN apt-get update && apt-get install -y python3 python3-pip iproute2 iputils-ping net-tools && \
    pip3 install requests

WORKDIR /app

# 复制脚本文件
COPY user_traffic_simulator.py start.sh ./
RUN chmod +x user_traffic_simulator.py start.sh

ENTRYPOINT ["./start.sh"]
