FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/opt/huggingface

WORKDIR /app

COPY requirements-runtime.txt ./

# Install a CPU-only PyTorch wheel before the remaining runtime dependencies.
RUN python -m pip install --no-cache-dir \
        --index-url https://download.pytorch.org/whl/cpu \
        "torch>=2.0,<3.0" \
    && python -m pip install --no-cache-dir -r requirements-runtime.txt

# Cache the exact embedding model during the build so RAG does not depend on a
# developer cache or a first-request download in the deployed container.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', device='cpu')"

RUN addgroup --system app \
    && adduser --system --ingroup app --home /home/app app \
    && mkdir -p /app/runtime \
    && chown -R app:app /app/runtime /opt/huggingface

COPY --chown=app:app app ./app
COPY --chown=app:app knowledge ./knowledge

ENV CUSTOMER_OWNERSHIP_DATABASE_PATH=/app/runtime/customer_ownership.db \
    PREDICTIVE_MAINTENANCE_ARTIFACT_DIRECTORY=/app/runtime/predictive_maintenance \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1 \
    PORT=8000

USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8000') + '/health', timeout=3)" || exit 1

CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port \"${PORT:-8000}\""]
