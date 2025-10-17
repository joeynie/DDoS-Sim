FROM nginx:alpine

RUN apk update && apk add --no-cache tcpdump iproute2

# 网页文件复制到Nginx的网站根目录
COPY index.html /usr/share/nginx/html/index.html

# 创建脚本来降低系统的DDoS防护能力
RUN echo '#!/bin/sh' > /usr/local/bin/weaken-defenses.sh && \
    echo '# 降低SYN队列大小，使系统更容易受到SYN Flood攻击' >> /usr/local/bin/weaken-defenses.sh && \
    echo 'sysctl -w net.ipv4.tcp_max_syn_backlog=128' >> /usr/local/bin/weaken-defenses.sh && \
    echo '# 禁用SYN Cookies防护' >> /usr/local/bin/weaken-defenses.sh && \
    echo 'sysctl -w net.ipv4.tcp_syncookies=0' >> /usr/local/bin/weaken-defenses.sh && \
    echo '# 减少TCP重试次数' >> /usr/local/bin/weaken-defenses.sh && \
    echo 'sysctl -w net.ipv4.tcp_syn_retries=3' >> /usr/local/bin/weaken-defenses.sh && \
    echo '# 减少连接超时时间' >> /usr/local/bin/weaken-defenses.sh && \
    echo 'sysctl -w net.ipv4.tcp_synack_retries=3' >> /usr/local/bin/weaken-defenses.sh && \
    echo 'echo "System defenses weakened for DDoS simulation"' >> /usr/local/bin/weaken-defenses.sh && \
    chmod +x /usr/local/bin/weaken-defenses.sh