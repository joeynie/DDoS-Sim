FROM nginx:alpine

RUN apk update && apk add --no-cache tcpdump iproute2 apache2-utils
RUN apk add --no-cache python3 py3-pip
RUN pip3 install --break-system-packages flask

# 网页文件复制到Nginx的网站根目录
COPY index.html /usr/share/nginx/html/index.html
COPY nginx.conf /etc/nginx/nginx.conf
# 后端 app
COPY app.py /app/app.py

WORKDIR /app

COPY start.sh /start.sh
RUN chmod +x /start.sh
EXPOSE 80
CMD ["/start.sh"]