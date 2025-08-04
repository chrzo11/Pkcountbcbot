FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y \
    chromium \
    chromium-driver \
    && apt-get clean && \
    rm -rf /var/lib/apt/lists/*

ENV CHROMIUM_BIN=/usr/bin/chromium \
    CHROMEDRIVER_BIN=/usr/bin/chromedriver

WORKDIR /app

COPY . /app

RUN pip install --no-cache-dir --break-system-packages -r requirements.txt

CMD gunicorn app:app & python3 bot.py & python3 ping.py
