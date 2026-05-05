# ── Builder ────────────────────────────────────────────────────────
FROM python:3.12-slim AS builder

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ── Production ─────────────────────────────────────────────────────
FROM python:3.12-slim AS prod

# Runtime deps: curl (health probe) + Firefox shared libraries for camoufox
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 \
        libxcomposite1 libxdamage1 libxrandr2 libxss1 \
        libasound2 libpangocairo-1.0-0 libatk1.0-0 libcairo-gobject2 \
        libgdk-pixbuf-2.0-0 libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /install /usr/local
WORKDIR /app
COPY . .

# Pre-download the camoufox browser binary so it is baked into the image.
# Set CAMOUFOX_SKIP_FETCH=1 at build time to skip (e.g. in CI / slim builds).
ARG CAMOUFOX_SKIP_FETCH=0
RUN if [ "${CAMOUFOX_SKIP_FETCH}" != "1" ]; then \
        python -m camoufox fetch; \
    fi

EXPOSE 8000
CMD ["gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]

# ── Dev (hot-reload) ───────────────────────────────────────────────
FROM python:3.12-slim AS dev

# Same shared libraries needed in dev
RUN DEBIAN_FRONTEND=noninteractive apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
        curl \
        libgtk-3-0 libdbus-glib-1-2 libxt6 libx11-xcb1 \
        libxcomposite1 libxdamage1 libxrandr2 libxss1 \
        libasound2 libpangocairo-1.0-0 libatk1.0-0 libcairo-gobject2 \
        libgdk-pixbuf-2.0-0 libpango-1.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

ARG CAMOUFOX_SKIP_FETCH=0
RUN if [ "${CAMOUFOX_SKIP_FETCH}" != "1" ]; then \
        python -m camoufox fetch; \
    fi

COPY . .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
