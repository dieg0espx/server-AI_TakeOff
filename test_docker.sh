#!/bin/bash

# Test Docker setup for AI-Takeoff Server
# This script builds and tests the Docker container locally

set -e  # Exit on error

echo "🚀 AI-Takeoff Server - Docker Test Script"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Error: Docker is not installed${NC}"
    echo "Please install Docker from: https://www.docker.com/get-started"
    exit 1
fi

echo -e "${GREEN}✅ Docker is installed${NC}"
echo ""

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Warning: .env file not found${NC}"
    echo "Creating a sample .env file..."
    cat > .env << EOF
PORT=5001
CONVERTIO_API_KEY=your_convertio_api_key_here
API_URL=https://ttfconstruction.com/ai-takeoff-results/create.php
EOF
    echo -e "${YELLOW}Please update .env with your actual API keys${NC}"
    echo ""
fi

# Build Docker image
echo "🔨 Building Docker image..."
echo "This may take 5-10 minutes on first run..."
echo ""

if docker build -t ai-takeoff-server:test .; then
    echo -e "${GREEN}✅ Docker image built successfully${NC}"
else
    echo -e "${RED}❌ Docker build failed${NC}"
    exit 1
fi

echo ""
echo "🏃 Starting container..."
echo ""

# Stop any existing container
docker stop ai-takeoff-test 2>/dev/null || true
docker rm ai-takeoff-test 2>/dev/null || true

# Start the container
docker run -d \
    --name ai-takeoff-test \
    -p 5001:5001 \
    --env-file .env \
    ai-takeoff-server:test

echo -e "${GREEN}✅ Container started${NC}"
echo ""

# Wait for server to start
echo "⏳ Waiting for server to start..."
sleep 5

# Test health endpoint
echo "🔍 Testing health endpoint..."
echo ""

HEALTH_RESPONSE=$(curl -s http://localhost:5001/health || echo "failed")

if [[ $HEALTH_RESPONSE == *"healthy"* ]]; then
    echo -e "${GREEN}✅ Health check passed!${NC}"
    echo "Response: $HEALTH_RESPONSE"
else
    echo -e "${RED}❌ Health check failed${NC}"
    echo "Response: $HEALTH_RESPONSE"
    echo ""
    echo "Container logs:"
    docker logs ai-takeoff-test
fi

echo ""
echo "🔍 Testing root endpoint..."
ROOT_RESPONSE=$(curl -s http://localhost:5001/ || echo "failed")

if [[ $ROOT_RESPONSE == *"running"* ]]; then
    echo -e "${GREEN}✅ Root endpoint working!${NC}"
    echo "Response: $ROOT_RESPONSE"
else
    echo -e "${RED}❌ Root endpoint failed${NC}"
    echo "Response: $ROOT_RESPONSE"
fi

echo ""
echo "=========================================="
echo "🎉 Docker test complete!"
echo ""
echo "Your server is running at: http://localhost:5001"
echo "API Documentation: http://localhost:5001/docs"
echo ""
echo "View logs:"
echo "  docker logs ai-takeoff-test"
echo ""
echo "Stop container:"
echo "  docker stop ai-takeoff-test"
echo ""
echo "Remove container:"
echo "  docker rm ai-takeoff-test"
echo ""
echo "=========================================="

