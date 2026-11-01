# ARM64-compatible non-root CPU image; the model downloads only on first startup.
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 \
    HF_HOME=/data/hf PORT=8091 SOCIALMARKET_EMBED_BIND=0.0.0.0 \
    HF_HUB_DISABLE_TELEMETRY=1 TOKENIZERS_PARALLELISM=false \
    OMP_NUM_THREADS=2 MKL_NUM_THREADS=2
RUN groupadd --gid 10001 e5 && useradd --uid 10001 --gid 10001 --create-home --shell /usr/sbin/nologin e5 \
    && mkdir -p /data/hf /app \
    && chown -R e5:e5 /data/hf /app
RUN python -m pip install --no-cache-dir \
    "sentence-transformers==5.1.2" "numpy==2.2.6" "psycopg[binary]==3.2.9"
COPY --chown=e5:e5 workers/product_intelligence/graphrag_multilingual_e5.py /app/graphrag_multilingual_e5.py
USER e5
WORKDIR /app
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
 CMD python -c "from urllib.request import urlopen; urlopen('http://127.0.0.1:8091/health',timeout=4).read()" || exit 1
CMD ["python","graphrag_multilingual_e5.py","query-service"]
