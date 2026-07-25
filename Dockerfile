FROM python:3.11-slim

WORKDIR /app

COPY linuxbot.py run.sh ./
COPY data ./data
COPY utils ./utils
COPY scripts ./scripts

RUN chmod +x run.sh

CMD ["./run.sh"]
