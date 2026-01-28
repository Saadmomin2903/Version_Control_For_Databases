FROM apache/superset:latest

USER root

# Install OS dependencies for SASL (required by Hive/Impala)
RUN apt-get update && apt-get install -y \
    build-essential \
    libsasl2-dev \
    libsasl2-modules \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

RUN /app/.venv/bin/python -m ensurepip
RUN /app/.venv/bin/python -m pip install --no-cache-dir \
    pyhive \
    "thrift==0.16.0" \
    sasl \
    thrift_sasl \
    impyla \
    trino \
    sqlalchemy-trino \
    psycopg2-binary \
    gevent

# Copy custom config
COPY superset_config.py /app/pythonpath/superset_config.py

# Switch back to superset user
ENV PYTHONPATH=/app/pythonpath
USER superset
