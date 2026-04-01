#!/usr/bin/env bash
set -e

echo "================================================"
echo "  IMEET.AI Development Environment Setup"
echo "================================================"

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Python 3 is required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js is required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker is required"; exit 1; }

echo ""
echo "[1/5] Starting Docker services (PostgreSQL, Redis, MinIO)..."
cd "$(dirname "$0")/../deploy"
docker compose up -d
cd ..

echo ""
echo "[2/5] Installing server dependencies..."
cd packages/server
pip install poetry 2>/dev/null || true
poetry install
cd ../..

echo ""
echo "[3/5] Installing local engine dependencies..."
cd packages/local-engine
poetry install
cd ../..

echo ""
echo "[4/5] Installing desktop dependencies..."
cd packages/desktop
npm install
cd ../..

echo ""
echo "[5/5] Copying environment file..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "  Created .env from .env.example - please update with your API keys"
fi

echo ""
echo "================================================"
echo "  Setup complete!"
echo ""
echo "  Start development:"
echo "    make server    # Start backend API"
echo "    make engine    # Start local engine"
echo "    make desktop   # Start Electron app"
echo ""
echo "  Or start everything:"
echo "    make dev"
echo "================================================"
