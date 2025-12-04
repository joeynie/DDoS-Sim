FROM nginx:alpine

RUN apk update && apk add --no-cache tcpdump iproute2 apache2-utils bash
RUN apk add --no-cache python3 py3-pip
#流量监测
RUN apk add iftop 
RUN pip3 install --break-system-packages flask

# 网页文件复制到Nginx的网站根目录
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/nginx.conf
# 后端 app
COPY app.py /app/app.py
COPY udp_echo_server_9999.py /app/udp_echo_server_9999.py

WORKDIR /app

COPY start.sh /start.sh
COPY setup_victim.sh /app/setup_victim.sh
EXPOSE 80 9999/udp
CMD ["sh", "/start.sh"]