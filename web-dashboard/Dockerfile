FROM python:3.11-slim

# Install ping utility
RUN apt-get update && apt-get install -y iputils-ping && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY worker-manager/web-dashboard/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker-manager/web-dashboard/app.py .

# Environment variables (set via docker-compose or runtime)
# ENV API_URL - set at runtime
# ENV API_TOKEN - set at runtime

EXPOSE 5000

CMD ["python", "app.py"]