FROM python:3.11-alpine

RUN pip install --no-cache-dir flask requests

WORKDIR /app

COPY c2_server.py /app/
COPY templates/ /app/templates/

EXPOSE 5000

CMD ["python3", "c2_server.py"]
