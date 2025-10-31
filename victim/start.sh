#!/bin/sh
# 启动后端与 nginx
python3 /app/app.py &
nginx -g "daemon off;"
