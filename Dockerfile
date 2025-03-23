FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
    graphviz \
    libgraphviz-dev \
    wget \
    ca-certificates \
    x11vnc \
    xvfb \
    fluxbox \
    novnc \
    websockify \
    wkhtmltopdf \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libx11-xcb1 \
    libxcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    xauth \
    libgtk-3-0 \
    libxcb-xinerama0 \
    dbus-x11 \
    libxtst6 \
    fonts-noto \
    x11-apps \
    portaudio19-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps

RUN python -m spacy download en_core_web_sm

COPY . .

EXPOSE 5901 6901 5000

COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

CMD ["/app/entrypoint.sh"]

