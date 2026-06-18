#!/bin/bash
set -e   # exit immediately on any error

echo "⏳ Running Alembic migrations..."
alembic upgrade head
echo "✅ Migrations applied."

echo "🚀 Starting dev server..."
exec uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
