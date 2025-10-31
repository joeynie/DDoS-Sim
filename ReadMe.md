# DDoS-Sim

## quick demo
- 终端输入
```bash
docker-compose up -d --build

# 进行攻击
docker exec -it attacker bash
python3 http_flood.py http://10.10.20.20/api/status?delay=1000 10 100 60

docker-compose down
```
- 攻击前后，浏览器访问http://localhost:8080/api/status