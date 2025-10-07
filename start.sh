#!/bin/bash

# Startup script for AI-Takeoff Server
set -e

echo "🚀 Starting AI-Takeoff Server..."

# Set default port if not provided
export PORT=${PORT:-5001}

# Create necessary directories
mkdir -p files utils

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found!"
    exit 1
fi

# Check if required Python packages are installed
echo "🔍 Checking Python dependencies..."
python -c "import fastapi, uvicorn, requests, cloudinary" || {
    echo "❌ Error: Missing required Python packages!"
    echo "Installing missing packages..."
    pip install -r requirements.txt
}

# Start the application
echo "🌐 Starting server on port $PORT..."
exec python main.py
