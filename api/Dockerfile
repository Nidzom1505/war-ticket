FROM python:3.12-slim

WORKDIR /app

# Install dependencies first (layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

# Development: Flask dev server with hot-reload
# Production:  switch to gunicorn
CMD ["python", "run.py"]
