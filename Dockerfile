FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src/ ./src/
RUN python -m pip install --no-cache-dir .
RUN useradd --system --uid 10001 --home /app ai && mkdir -p /data && chown ai:ai /data
USER ai
ENV GOREEAI_DATABASE_PATH=/data/ai.sqlite
EXPOSE 8765
CMD ["uvicorn", "goreecloud_ai.app:app", "--host", "0.0.0.0", "--port", "8765"]
