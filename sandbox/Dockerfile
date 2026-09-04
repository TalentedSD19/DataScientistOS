FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV MPLCONFIGDIR=/tmp/mpl
ENV MPLBACKEND=Agg

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir \
    pandas \
    numpy \
    scipy \
    scikit-learn \
    matplotlib \
    duckdb \
    xgboost

WORKDIR /workspace

RUN useradd \
    --create-home \
    --uid 10001 \
    sandboxuser

RUN mkdir -p /tmp/mpl /workspace/input /workspace/output \
    && chown -R sandboxuser:sandboxuser /tmp/mpl /workspace

USER sandboxuser

CMD ["python"]