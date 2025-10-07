#!/bin/bash

# Startup script for AI-Takeoff Server
set -e

echo "🚀 Starting AI-Takeoff Server..."
echo "📋 Environment variables:"
echo "  PORT: $PORT"
echo "  PYTHONPATH: $PYTHONPATH"
echo "  PWD: $PWD"

# Set default port if not provided
export PORT=${PORT:-5001}

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p files utils

# List current directory contents
echo "📂 Current directory contents:"
ls -la

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo "❌ Error: main.py not found!"
    echo "📂 Available files:"
    ls -la *.py 2>/dev/null || echo "No Python files found"
    exit 1
fi

# Check Python version
echo "🐍 Python version:"
python --version

# Check if required Python packages are installed
echo "🔍 Checking Python dependencies..."
python -c "
try:
    import fastapi
    print('✅ FastAPI imported successfully')
    import uvicorn
    print('✅ Uvicorn imported successfully')
    import requests
    print('✅ Requests imported successfully')
    import cloudinary
    print('✅ Cloudinary imported successfully')
    print('✅ All dependencies available')
except ImportError as e:
    print(f'❌ Missing dependency: {e}')
    exit(1)
" || {
    echo "❌ Error: Missing required Python packages!"
    echo "Installing missing packages..."
    pip install -r requirements.txt
}

# Test the health endpoint before starting
echo "🧪 Testing health endpoint setup..."
python -c "
import sys
sys.path.append('.')
try:
    from main import app
    print('✅ FastAPI app imported successfully')
except Exception as e:
    print(f'❌ Error importing app: {e}')
    sys.exit(1)
"

# Start the application
echo "🌐 Starting server on port $PORT..."
echo "📋 Server will be available at: http://0.0.0.0:$PORT"
echo "📋 Health check at: http://0.0.0.0:$PORT/health"

# Use exec to replace the shell process
exec python main.py
