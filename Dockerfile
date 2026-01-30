FROM python:3.9-alpine AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple/ && \
    pip install --no-cache-dir -r requirements.txt

FROM python:3.9-alpine

WORKDIR /app

ENV TZ=Asia/Shanghai

COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

COPY . .

EXPOSE 5001

CMD ["python", "main.py"]
