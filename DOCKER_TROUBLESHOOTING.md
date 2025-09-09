# Docker Build Troubleshooting Guide

This guide helps resolve common Docker build issues for the AI-Takeoff application.

## 🚨 Common Build Errors

### **Error: Package Installation Failed (Exit Code 100)**

**Problem**: `apt-get install` fails with exit code 100
```
ERROR: failed to build: failed to solve: process "/bin/sh -c apt-get update && apt-get install -y ..." did not complete successfully: exit code: 100
```

**Solutions**:

#### **Solution 1: Use Minimal Dockerfile**
```bash
# Use the minimal Dockerfile instead
./docker-build.sh build -f Dockerfile.minimal
```

#### **Solution 2: Update Package Lists**
```bash
# Clear Docker cache and rebuild
docker system prune -a
docker build --no-cache -f Dockerfile.minimal -t ai-takeoff-api .
```

#### **Solution 3: Install Packages Individually**
If specific packages are causing issues, you can modify the Dockerfile to install them one by one:

```dockerfile
# Install packages individually to identify problematic ones
RUN apt-get update && apt-get install -y gcc g++ && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y curl && apt-get clean && rm -rf /var/lib/apt/lists/*
RUN apt-get update && apt-get install -y tesseract-ocr && apt-get clean && rm -rf /var/lib/apt/lists/*
```

### **Error: OpenCV Dependencies Missing**

**Problem**: OpenCV fails to import or work properly
```
ImportError: libGL.so.1: cannot open shared object file
```

**Solution**: Use the full Dockerfile with OpenCV dependencies:
```bash
./docker-build.sh build -f Dockerfile
```

### **Error: Tesseract Not Found**

**Problem**: Tesseract OCR is not available
```
FileNotFoundError: [Errno 2] No such file or directory: 'tesseract'
```

**Solution**: Ensure Tesseract is installed:
```dockerfile
RUN apt-get update && apt-get install -y tesseract-ocr tesseract-ocr-eng
```

### **Error: PDF Processing Tools Missing**

**Problem**: PDF to image conversion fails
```
pdf2image.exceptions.PDFPageCountError
```

**Solution**: Install poppler-utils:
```dockerfile
RUN apt-get update && apt-get install -y poppler-utils
```

## 🔧 Build Optimization

### **Reduce Build Time**
```bash
# Use Docker BuildKit for faster builds
export DOCKER_BUILDKIT=1
docker build -f Dockerfile.minimal -t ai-takeoff-api .
```

### **Multi-stage Builds**
For production, consider using multi-stage builds to reduce final image size:

```dockerfile
# Build stage
FROM python:3.11-slim as builder
WORKDIR /app
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Runtime stage
FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /root/.local /root/.local
COPY . .
ENV PATH=/root/.local/bin:$PATH
CMD ["gunicorn", "main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:5001"]
```

## 🐛 Debugging Build Issues

### **Step-by-step Debugging**

1. **Test Base Image**:
```bash
docker run -it python:3.11-slim /bin/bash
# Inside container, test package installation
apt-get update && apt-get install -y curl
```

2. **Test Individual Packages**:
```bash
# Test each package individually
docker run -it python:3.11-slim /bin/bash
apt-get update
apt-get install -y gcc
apt-get install -y tesseract-ocr
# etc.
```

3. **Build with Verbose Output**:
```bash
docker build --progress=plain --no-cache -f Dockerfile.minimal -t ai-takeoff-api .
```

### **Check Package Availability**
```bash
# Check if packages exist in the repository
docker run -it python:3.11-slim /bin/bash
apt-cache search tesseract-ocr
apt-cache search poppler-utils
```

## 🚀 Alternative Solutions

### **Use Different Base Image**
If Python 3.11 slim has issues, try:

```dockerfile
# Option 1: Use full Python image
FROM python:3.11

# Option 2: Use Ubuntu base
FROM ubuntu:22.04
RUN apt-get update && apt-get install -y python3.11 python3.11-pip
```

### **Use Pre-built Images**
Consider using pre-built images with dependencies:

```dockerfile
FROM jrottenberg/ffmpeg:4.4-alpine
FROM python:3.11-slim
# Copy from ffmpeg image if needed
```

### **Use Conda/Mamba**
For complex dependencies:

```dockerfile
FROM continuumio/miniconda3:latest
RUN conda install -c conda-forge opencv tesseract
```

## 📋 Build Checklist

Before building, ensure:

- [ ] Docker is running
- [ ] Sufficient disk space (at least 2GB free)
- [ ] Internet connection for package downloads
- [ ] No conflicting containers running
- [ ] Environment variables are set correctly

## 🔍 Build Commands Reference

```bash
# Basic build
docker build -t ai-takeoff-api .

# Build with specific Dockerfile
docker build -f Dockerfile.minimal -t ai-takeoff-api .

# Build without cache
docker build --no-cache -t ai-takeoff-api .

# Build with verbose output
docker build --progress=plain -t ai-takeoff-api .

# Build with BuildKit
DOCKER_BUILDKIT=1 docker build -t ai-takeoff-api .

# Multi-platform build
docker buildx build --platform linux/amd64,linux/arm64 -t ai-takeoff-api .
```

## 🆘 Getting Help

If you continue to have issues:

1. **Check Docker logs**: `docker logs <container_id>`
2. **Test minimal setup**: Use `Dockerfile.minimal`
3. **Check system requirements**: Ensure Docker has enough resources
4. **Update Docker**: Use the latest Docker version
5. **Check network**: Ensure internet access for package downloads

## 📝 Common Solutions Summary

| Error | Solution |
|-------|----------|
| Package installation fails | Use `Dockerfile.minimal` |
| OpenCV import error | Use full `Dockerfile` |
| Tesseract not found | Install `tesseract-ocr` |
| PDF processing fails | Install `poppler-utils` |
| Build timeout | Increase Docker resources |
| Permission denied | Check file permissions |

Remember: Start with `Dockerfile.minimal` and add dependencies as needed!
