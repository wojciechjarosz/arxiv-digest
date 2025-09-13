# Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
      tzdata \
      libgomp1 \
      libstdc++6 \
      libblas3 \
      liblapack3 \
      libgfortran5 && \
    rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md ./
COPY app ./app
COPY main.py ./
COPY db ./db
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN pip install --upgrade pip && pip install .

RUN useradd -m appuser
USER appuser

ENTRYPOINT ["/entrypoint.sh"]
