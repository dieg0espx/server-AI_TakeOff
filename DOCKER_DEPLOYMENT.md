# Docker Deployment Guide

This guide covers how to containerize and deploy your AI-Takeoff FastAPI application using Docker.

## 📦 Docker Files Created

### 1. **Dockerfile**
- **Base Image**: Python 3.11 slim for optimal size and performance
- **System Dependencies**: Includes all required libraries for OpenCV, Tesseract, and image processing
- **Multi-stage Optimization**: Efficient layer caching and minimal final image size
- **Health Checks**: Built-in health monitoring
- **Security**: Non-root user and minimal attack surface

### 2. **.dockerignore**
- **Optimized Builds**: Excludes unnecessary files from Docker context
- **Faster Builds**: Reduces build time and image size
- **Security**: Prevents sensitive files from being included

### 3. **docker-compose.yml**
- **Local Development**: Easy local development setup
- **Environment Variables**: Secure environment variable management
- **Volume Mounting**: Persistent data storage
- **Health Monitoring**: Built-in health checks

### 4. **docker-compose.prod.yml**
- **Production Ready**: Optimized for production deployment
- **Resource Limits**: Memory and CPU constraints
- **Persistent Volumes**: Data persistence across container restarts
- **High Availability**: Restart policies and health monitoring

## 🚀 Quick Start

### Prerequisites
- Docker Desktop installed
- Docker Compose installed
- Environment variables configured

### 1. **Local Development**

```bash
# Clone and navigate to project
cd server-AI_TakeOff

# Create .env file with your environment variables
cp .env.example .env
# Edit .env with your actual values

# Start the application
docker-compose up --build

# Or start in development mode with hot reload
docker-compose --profile dev up --build
```

### 2. **Production Deployment**

```bash
# Build and start production containers
docker-compose -f docker-compose.prod.yml up --build -d

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Stop services
docker-compose -f docker-compose.prod.yml down
```

## 🐳 Docker Commands

### **Build and Run Manually**

```bash
# Build the Docker image
docker build -t ai-takeoff-api .

# Run the container
docker run -p 5001:5001 \
  -e CLOUDINARY_CLOUD_NAME=your_cloud_name \
  -e CLOUDINARY_API_KEY=your_api_key \
  -e CLOUDINARY_API_SECRET=your_api_secret \
  -e CONVERTIO_API_KEY=your_convertio_key \
  ai-takeoff-api

# Run with volume mounting for development
docker run -p 5001:5001 \
  -v $(pwd)/files:/app/files \
  -v $(pwd)/data.json:/app/data.json \
  -e CLOUDINARY_CLOUD_NAME=your_cloud_name \
  ai-takeoff-api
```

### **Container Management**

```bash
# List running containers
docker ps

# View container logs
docker logs <container_id>

# Execute commands in running container
docker exec -it <container_id> /bin/bash

# Stop and remove container
docker stop <container_id>
docker rm <container_id>

# Remove image
docker rmi ai-takeoff-api
```

## 🌐 Railway Deployment with Docker

### **Automatic Docker Detection**
Railway will automatically detect your `Dockerfile` and build your application using Docker.

### **Deployment Steps**
1. **Push to GitHub**: Your Docker configuration is already committed
2. **Connect to Railway**: Railway will detect the Dockerfile
3. **Set Environment Variables**: Configure your API keys in Railway dashboard
4. **Deploy**: Railway will build and deploy your Docker container

### **Railway Configuration**
The `railway.json` file is configured to use Docker:
```json
{
  "build": {
    "builder": "DOCKERFILE"
  }
}
```

## 🔧 Environment Variables

### **Required Variables**
```bash
# Cloudinary Configuration
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here

# Convertio API (for PDF to SVG conversion)
CONVERTIO_API_KEY=your_convertio_api_key_here

# Google Drive API (if needed)
GOOGLE_DRIVE_API_KEY=your_google_drive_api_key_here
```

### **Optional Variables**
```bash
# Port (defaults to 5001)
PORT=5001

# Python environment
PYTHONPATH=/app
PYTHONDONTWRITEBYTECODE=1
PYTHONUNBUFFERED=1
```

## 📊 Monitoring and Health Checks

### **Health Check Endpoint**
- **URL**: `http://localhost:5001/health`
- **Response**: `{"status": "healthy", "service": "AI-Takeoff Server"}`

### **Docker Health Checks**
```bash
# Check container health
docker inspect <container_id> | grep -A 10 "Health"

# View health check logs
docker logs <container_id> 2>&1 | grep -i health
```

## 🛠️ Development Workflow

### **Hot Reload Development**
```bash
# Start development container with hot reload
docker-compose --profile dev up --build

# The container will automatically reload when you make changes
```

### **Debugging**
```bash
# Run container in interactive mode
docker run -it --rm -p 5001:5001 \
  -v $(pwd):/app \
  ai-takeoff-api /bin/bash

# Inside container, run with debug mode
uvicorn main:app --host 0.0.0.0 --port 5001 --reload --log-level debug
```

## 🔒 Security Considerations

### **Image Security**
- **Base Image**: Uses official Python slim image
- **Non-root User**: Runs as non-privileged user
- **Minimal Dependencies**: Only required packages installed
- **No Secrets**: Environment variables used for sensitive data

### **Network Security**
- **Port Binding**: Only necessary ports exposed
- **Internal Communication**: Services communicate via internal network
- **Health Checks**: Regular health monitoring

## 📈 Performance Optimization

### **Image Size Optimization**
- **Multi-stage Builds**: Minimal final image size
- **Layer Caching**: Efficient Docker layer caching
- **Alpine Base**: Lightweight base image when possible

### **Runtime Optimization**
- **Gunicorn Workers**: Multiple worker processes
- **Resource Limits**: Memory and CPU constraints
- **Health Monitoring**: Automatic restart on failure

## 🚨 Troubleshooting

### **Common Issues**

#### **Build Failures**
```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker build --no-cache -t ai-takeoff-api .
```

#### **Permission Issues**
```bash
# Fix file permissions
sudo chown -R $USER:$USER files/
chmod -R 755 files/
```

#### **Port Conflicts**
```bash
# Check port usage
lsof -i :5001

# Use different port
docker run -p 5002:5001 ai-takeoff-api
```

#### **Environment Variables**
```bash
# Check environment variables in container
docker exec <container_id> env | grep CLOUDINARY
```

### **Logs and Debugging**
```bash
# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f ai-takeoff-api

# Follow logs in real-time
docker logs -f <container_id>
```

## 🎯 Best Practices

### **Development**
1. **Use docker-compose** for local development
2. **Mount volumes** for code changes without rebuilds
3. **Use .env files** for environment variables
4. **Regular cleanup** of unused images and containers

### **Production**
1. **Use production compose file** with resource limits
2. **Implement proper logging** and monitoring
3. **Use secrets management** for sensitive data
4. **Regular security updates** of base images

### **CI/CD**
1. **Automated builds** on code changes
2. **Security scanning** of Docker images
3. **Automated testing** in containers
4. **Blue-green deployments** for zero downtime

Your AI-Takeoff application is now fully containerized and ready for deployment! 🎉
