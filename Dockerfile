FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=1 \
    TELRAAM_CACHE_DIR=/data/cache

WORKDIR /app

# Install runtime dependencies from pyproject.toml (single source of truth)
# before copying source so the layer is cached across code changes.
COPY pyproject.toml ./
RUN python -c "import tomllib, subprocess, sys; deps = tomllib.load(open('pyproject.toml', 'rb'))['project']['dependencies']; subprocess.run([sys.executable, '-m', 'pip', 'install', '--upgrade', 'pip'], check=True); subprocess.run([sys.executable, '-m', 'pip', 'install', *deps], check=True)"

COPY . .

RUN useradd --create-home --uid 1000 appuser \
    && mkdir -p /data/cache \
    && chown -R appuser:appuser /app /data

USER appuser

EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import sys, urllib.request; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8501/_stcore/health').read() == b'ok' else 1)"

CMD ["streamlit", "run", "app.py", "--server.address=0.0.0.0", "--server.port=8501"]
