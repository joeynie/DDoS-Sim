FROM python:3.9-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制代码
COPY . .

ENV ENVIRONMENT=docker

# 启动训练
# CMD ["python", "-u", "agent.py"]
CMD ["tail", "-f", "/dev/null"]
