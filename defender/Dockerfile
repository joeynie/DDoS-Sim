FROM ubuntu:22.04

RUN apt-get update && apt-get install -y iptables iproute2 procps iputils-ping 

# 复制并赋予启动脚本执行权限
COPY start-defender.sh /usr/local/bin/start-defender.sh
RUN chmod +x /usr/local/bin/start-defender.sh

CMD ["/usr/local/bin/start-defender.sh"]