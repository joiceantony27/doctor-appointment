#!/bin/bash

# Local Testing Script for Doctor Appointment System
# This script helps test the complete Docker setup locally

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    print_error "Docker is not running. Please start Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    print_error "docker-compose is not installed. Please install it first."
    exit 1
fi

print_status "Starting local testing of Doctor Appointment System..."

# Clean up any existing containers
print_step "Cleaning up existing containers..."
docker-compose down -v 2>/dev/null || true

# Build and start services
print_step "Building and starting services..."
docker-compose up --build -d

# Wait for services to be ready
print_step "Waiting for services to be ready..."
sleep 30

# Check service health
print_step "Checking service health..."

# Check if database is ready
if docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; then
    print_status "✓ PostgreSQL database is ready"
else
    print_error "✗ PostgreSQL database is not ready"
fi

# Check if Redis is ready
if docker-compose exec -T redis redis-cli ping > /dev/null 2>&1; then
    print_status "✓ Redis is ready"
else
    print_error "✗ Redis is not ready"
fi

# Check if web service is ready
if curl -f http://localhost:8000/health/ > /dev/null 2>&1; then
    print_status "✓ Web service is ready"
else
    print_warning "✗ Web service health check failed, checking logs..."
    docker-compose logs web | tail -20
fi

# Run database migrations
print_step "Running database migrations..."
docker-compose exec -T web python manage.py migrate

# Create superuser (non-interactive)
print_step "Creating superuser..."
docker-compose exec -T web python manage.py shell << EOF
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
EOF

# Collect static files
print_step "Collecting static files..."
docker-compose exec -T web python manage.py collectstatic --noinput

# Run basic tests
print_step "Running basic application tests..."
if docker-compose exec -T web python manage.py test > /dev/null 2>&1; then
    print_status "✓ Basic tests passed"
else
    print_warning "✗ Some tests failed, check logs for details"
fi

# Test endpoints
print_step "Testing application endpoints..."

endpoints=(
    "http://localhost:8000/health/"
    "http://localhost:8000/"
    "http://localhost:8000/login/"
    "http://localhost:8000/register/"
)

for endpoint in "${endpoints[@]}"; do
    if curl -f -s "$endpoint" > /dev/null; then
        print_status "✓ $endpoint is accessible"
    else
        print_warning "✗ $endpoint is not accessible"
    fi
done

# Show service status
print_step "Service status:"
docker-compose ps

# Show logs summary
print_step "Recent logs (last 10 lines per service):"
echo "=== Web Service Logs ==="
docker-compose logs --tail=10 web

echo "=== Database Logs ==="
docker-compose logs --tail=10 db

echo "=== Redis Logs ==="
docker-compose logs --tail=10 redis

# Final status
print_status "Local testing completed!"
echo "=================================================="
echo "Application URL: http://localhost:8000"
echo "Admin Panel: http://localhost:8000/admin"
echo "Admin Credentials: admin / admin123"
echo "=================================================="
echo ""
echo "To stop services: docker-compose down"
echo "To view logs: docker-compose logs -f"
echo "To restart: docker-compose restart"
