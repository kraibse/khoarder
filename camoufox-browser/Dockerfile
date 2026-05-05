FROM python:3.12-slim

# Firefox shared libraries required by camoufox's headless browser
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 \
        libxcomposite1 libxdamage1 libxrandr2 libxss1 \
        libasound2 libpangocairo-1.0-0 libatk1.0-0 libcairo-gobject2 \
        libgdk-pixbuf-2.0-0 libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the camoufox browser binary and bake it into the image
RUN python -m camoufox fetch

COPY server.py .

EXPOSE 3392
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:3392/health')"

CMD ["python", "server.py"]
