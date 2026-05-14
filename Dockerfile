FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY scripts/ ./scripts/

# data/ and credentials/ are mounted at runtime — not baked into image
RUN mkdir -p /app/data /app/credentials

CMD ["python", "-m", "src.main"]
