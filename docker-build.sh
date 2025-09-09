#!/bin/bash

# AI-Takeoff Docker Build Script
# This script helps build and manage Docker containers for the AI-Takeoff application

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default values
IMAGE_NAME="ai-takeoff-api"
TAG="latest"
PORT="5001"
ENV_FILE=".env"
DOCKERFILE="Dockerfile"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND] [OPTIONS]"
    echo ""
    echo "Commands:"
    echo "  build       Build the Docker image"
    echo "  run         Run the Docker container"
    echo "  dev         Run in development mode with hot reload"
    echo "  stop        Stop running containers"
    echo "  clean       Clean up Docker resources"
    echo "  logs        Show container logs"
    echo "  shell       Open shell in running container"
    echo "  test        Test the application"
    echo ""
    echo "Options:"
    echo "  -t, --tag TAG        Docker image tag (default: latest)"
    echo "  -p, --port PORT      Port to expose (default: 5001)"
    echo "  -e, --env FILE       Environment file (default: .env)"
    echo "  -f, --file FILE      Dockerfile to use (default: Dockerfile)"
    echo "  -h, --help           Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 build"
    echo "  $0 build -f Dockerfile.minimal"
    echo "  $0 run -p 8080"
    echo "  $0 dev"
    echo "  $0 clean"
}

# Function to check if .env file exists
check_env_file() {
    if [ ! -f "$ENV_FILE" ]; then
        print_warning "Environment file $ENV_FILE not found"
        if [ -f ".env.example" ]; then
            print_status "Copying .env.example to .env"
            cp .env.example .env
            print_warning "Please edit .env file with your actual environment variables"
        else
            print_error "No .env or .env.example file found"
            exit 1
        fi
    fi
}

# Function to build Docker image
build_image() {
    print_status "Building Docker image: $IMAGE_NAME:$TAG using $DOCKERFILE"
    if [ ! -f "$DOCKERFILE" ]; then
        print_error "Dockerfile $DOCKERFILE not found"
        exit 1
    fi
    docker build -f "$DOCKERFILE" -t "$IMAGE_NAME:$TAG" .
    print_success "Docker image built successfully"
}

# Function to run Docker container
run_container() {
    check_env_file
    print_status "Running Docker container on port $PORT"
    
    # Stop existing container if running
    docker stop "$IMAGE_NAME" 2>/dev/null || true
    docker rm "$IMAGE_NAME" 2>/dev/null || true
    
    docker run -d \
        --name "$IMAGE_NAME" \
        -p "$PORT:5001" \
        --env-file "$ENV_FILE" \
        -v "$(pwd)/files:/app/files" \
        -v "$(pwd)/data.json:/app/data.json" \
        -v "$(pwd)/utils/config.json:/app/utils/config.json" \
        "$IMAGE_NAME:$TAG"
    
    print_success "Container started successfully"
    print_status "Application available at: http://localhost:$PORT"
    print_status "Health check: http://localhost:$PORT/health"
    print_status "API docs: http://localhost:$PORT/docs"
}

# Function to run in development mode
run_dev() {
    check_env_file
    print_status "Running in development mode with hot reload"
    
    # Stop existing container if running
    docker stop "${IMAGE_NAME}-dev" 2>/dev/null || true
    docker rm "${IMAGE_NAME}-dev" 2>/dev/null || true
    
    docker run -d \
        --name "${IMAGE_NAME}-dev" \
        -p "$PORT:5001" \
        --env-file "$ENV_FILE" \
        -v "$(pwd):/app" \
        "$IMAGE_NAME:$TAG" \
        uvicorn main:app --host 0.0.0.0 --port 5001 --reload
    
    print_success "Development container started successfully"
    print_status "Application available at: http://localhost:$PORT"
    print_status "Changes will be automatically reloaded"
}

# Function to stop containers
stop_containers() {
    print_status "Stopping containers..."
    docker stop "$IMAGE_NAME" "${IMAGE_NAME}-dev" 2>/dev/null || true
    docker rm "$IMAGE_NAME" "${IMAGE_NAME}-dev" 2>/dev/null || true
    print_success "Containers stopped"
}

# Function to clean up Docker resources
clean_docker() {
    print_status "Cleaning up Docker resources..."
    
    # Stop and remove containers
    stop_containers
    
    # Remove images
    docker rmi "$IMAGE_NAME:$TAG" 2>/dev/null || true
    
    # Clean up unused resources
    docker system prune -f
    
    print_success "Docker cleanup completed"
}

# Function to show logs
show_logs() {
    print_status "Showing container logs..."
    if docker ps -q -f name="$IMAGE_NAME" | grep -q .; then
        docker logs -f "$IMAGE_NAME"
    elif docker ps -q -f name="${IMAGE_NAME}-dev" | grep -q .; then
        docker logs -f "${IMAGE_NAME}-dev"
    else
        print_error "No running containers found"
        exit 1
    fi
}

# Function to open shell in container
open_shell() {
    print_status "Opening shell in container..."
    if docker ps -q -f name="$IMAGE_NAME" | grep -q .; then
        docker exec -it "$IMAGE_NAME" /bin/bash
    elif docker ps -q -f name="${IMAGE_NAME}-dev" | grep -q .; then
        docker exec -it "${IMAGE_NAME}-dev" /bin/bash
    else
        print_error "No running containers found"
        exit 1
    fi
}

# Function to test the application
test_application() {
    print_status "Testing application..."
    
    # Wait for container to be ready
    sleep 5
    
    # Test health endpoint
    if curl -f "http://localhost:$PORT/health" > /dev/null 2>&1; then
        print_success "Health check passed"
    else
        print_error "Health check failed"
        exit 1
    fi
    
    # Test root endpoint
    if curl -f "http://localhost:$PORT/" > /dev/null 2>&1; then
        print_success "Root endpoint accessible"
    else
        print_error "Root endpoint not accessible"
        exit 1
    fi
    
    print_success "Application tests passed"
}

# Parse command line arguments
COMMAND=""
while [[ $# -gt 0 ]]; do
    case $1 in
        build|run|dev|stop|clean|logs|shell|test)
            COMMAND="$1"
            shift
            ;;
        -t|--tag)
            TAG="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -e|--env)
            ENV_FILE="$2"
            shift 2
            ;;
        -f|--file)
            DOCKERFILE="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Execute command
case $COMMAND in
    build)
        build_image
        ;;
    run)
        run_container
        ;;
    dev)
        run_dev
        ;;
    stop)
        stop_containers
        ;;
    clean)
        clean_docker
        ;;
    logs)
        show_logs
        ;;
    shell)
        open_shell
        ;;
    test)
        test_application
        ;;
    "")
        print_error "No command specified"
        show_usage
        exit 1
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        show_usage
        exit 1
        ;;
esac
