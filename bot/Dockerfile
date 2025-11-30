FROM python:3.11-alpine

RUN apk add --no-cache iproute2

RUN pip install --no-cache-dir requests

WORKDIR /app

COPY bot_agent.py /app/
COPY udp_attack.py /app/
COPY start_bot.sh /app/

RUN chmod +x /app/start_bot.sh

CMD ["/app/start_bot.sh"]
