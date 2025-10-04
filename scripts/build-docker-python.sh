#!/bin/bash

# Build script for Python raalisence Docker images

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Default values
IMAGE_NAME="raalisence-python"
TAG="latest"
BUILD_TYPE="standard"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            TAG="$2"
            shift 2
            ;;
        --prod)
            BUILD_TYPE="production"
            shift
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  --tag TAG     Set the image tag (default: latest)"
            echo "  --prod        Build production image (distroless)"
            echo "  --help        Show this help message"
            exit 0
            ;;
        *)
            print_error "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Determine Dockerfile to use
if [[ "$BUILD_TYPE" == "production" ]]; then
    DOCKERFILE="Dockerfile.python.prod"
    IMAGE_NAME="${IMAGE_NAME}-prod"
    print_status "Building production image with distroless base"
else
    DOCKERFILE="Dockerfile.python"
    print_status "Building standard image with Python slim base"
fi

# Check if Dockerfile exists
if [[ ! -f "$DOCKERFILE" ]]; then
    print_error "Dockerfile not found: $DOCKERFILE"
    exit 1
fi

# Check if required files exist
REQUIRED_FILES=("pyproject.toml" "requirements.txt" "config.yaml" "python_raalisence/main.py")
for file in "${REQUIRED_FILES[@]}"; do
    if [[ ! -f "$file" ]]; then
        print_error "Required file not found: $file"
        exit 1
    fi
done

print_status "Building Docker image: ${IMAGE_NAME}:${TAG}"
print_status "Using Dockerfile: $DOCKERFILE"

# Build the image
if docker build -f "$DOCKERFILE" -t "${IMAGE_NAME}:${TAG}" .; then
    print_status "Successfully built ${IMAGE_NAME}:${TAG}"
    
    # Show image info
    print_status "Image information:"
    docker images "${IMAGE_NAME}:${TAG}"
    
    # Test the image
    print_status "Testing the image..."
    if docker run --rm "${IMAGE_NAME}:${TAG}" python -c "import python_raalisence; print('Import successful')"; then
        print_status "Image test passed"
    else
        print_warning "Image test failed - there may be runtime issues"
    fi
    
else
    print_error "Failed to build image"
    exit 1
fi

print_status "Build completed successfully!"
print_status "To run the container:"
echo "  docker run -p 8080:8080 -v \$(pwd)/data:/app/data -v \$(pwd)/config.yaml:/app/config.yaml:ro ${IMAGE_NAME}:${TAG}"
