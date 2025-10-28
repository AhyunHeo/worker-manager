#!/bin/bash
set -e

echo "Starting Worker Manager API..."

# Wait for database
echo "Waiting for database..."
sleep 5

# Start the API server
cd /app
exec uvicorn main:app --host 0.0.0.0 --port 8090 --reload
