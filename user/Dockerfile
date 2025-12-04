FROM ubuntu:22.04

RUN apt-get update && apt-get install -y python3 python3-pip iproute2 iputils-ping net-tools && \
    pip3 install requests

# 复制脚本文件
COPY user_traffic_simulator.py /usr/local/bin/user_traffic_simulator.py
RUN chmod +x /usr/local/bin/user_traffic_simulator.py

COPY start.sh /usr/local/bin/start.sh
RUN chmod +x /usr/local/bin/start.sh

WORKDIR /usr/local/bin

ENTRYPOINT ["/usr/local/bin/start.sh"]
