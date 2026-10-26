FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
COPY business_info.txt ./business_info.txt
RUN mkdir -p /app/data
EXPOSE 8000
# A single worker is required with this SQLite-based job queue.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
