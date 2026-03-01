FROM python:3.13-slim AS base

WORKDIR /app

# Install system dependencies (TA-Lib C library required by TA-Lib Python package)
RUN apt-get update && \
    apt-get install -y --no-install-recommends build-essential wget && \
    wget -q https://github.com/TA-Lib/ta-lib/releases/download/v0.6.4/ta-lib-0.6.4-src.tar.gz && \
    tar xzf ta-lib-0.6.4-src.tar.gz && \
    cd ta-lib-0.6.4 && ./configure --prefix=/usr && make -j$(nproc) && make install && \
    cd .. && rm -rf ta-lib-0.6.4 ta-lib-0.6.4-src.tar.gz && \
    apt-get purge -y --auto-remove build-essential wget && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["gunicorn", "main:create_wsgi_app()", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "120"]
