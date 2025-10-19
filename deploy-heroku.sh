#!/bin/bash

# Heroku Deployment for Django Doctor Appointment System
# Alternative deployment while waiting for Azure quota approval

set -e

echo "🚀 Deploying Django Doctor Appointment System to Heroku"
echo "====================================================="

# Check if Heroku CLI is installed
if ! command -v heroku &> /dev/null; then
    echo "❌ Heroku CLI is not installed."
    echo "📥 Install from: https://devcenter.heroku.com/articles/heroku-cli"
    echo "💡 Or run: curl https://cli-assets.heroku.com/install.sh | sh"
    exit 1
fi

# Login to Heroku
echo "🔐 Logging into Heroku..."
heroku login

# Create Heroku app
APP_NAME="doctor-appointment-$(openssl rand -hex 3)"
echo "📱 Creating Heroku app: ${APP_NAME}"
heroku create ${APP_NAME}

# Add PostgreSQL addon
echo "🐘 Adding PostgreSQL database..."
heroku addons:create heroku-postgresql:mini --app ${APP_NAME}

# Add Redis addon
echo "🔴 Adding Redis cache..."
heroku addons:create heroku-redis:mini --app ${APP_NAME}

# Set environment variables
echo "⚙️  Setting environment variables..."
heroku config:set --app ${APP_NAME} \
    DJANGO_SETTINGS_MODULE=doctor_appointment.settings_prod \
    DEBUG=False \
    ALLOWED_HOSTS=${APP_NAME}.herokuapp.com \
    SECRET_KEY=$(openssl rand -base64 32)

# Login to Heroku Container Registry
echo "🐳 Logging into Heroku Container Registry..."
heroku container:login

# Build and push Docker image
echo "🔨 Building and pushing Docker image..."
heroku container:push web --app ${APP_NAME}

# Release the image
echo "🚀 Releasing the application..."
heroku container:release web --app ${APP_NAME}

# Run database migrations
echo "📊 Running database migrations..."
heroku run --app ${APP_NAME} python manage.py migrate

# Create superuser (optional)
echo "👤 Creating superuser..."
heroku run --app ${APP_NAME} python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
if not User.objects.filter(username='admin').exists():
    User.objects.create_superuser('admin', 'admin@example.com', 'admin123')
    print('Superuser created: admin/admin123')
else:
    print('Superuser already exists')
"

echo
echo "🎉 Deployment completed successfully!"
echo "======================================"
echo
echo "🌐 Your app is live at: https://${APP_NAME}.herokuapp.com"
echo "👤 Admin login: https://${APP_NAME}.herokuapp.com/admin"
echo "   Username: admin"
echo "   Password: admin123"
echo
echo "📊 Monitor your app:"
echo "   heroku logs --tail --app ${APP_NAME}"
echo "   heroku ps --app ${APP_NAME}"
echo
echo "🔧 Useful commands:"
echo "   heroku run python manage.py shell --app ${APP_NAME}"
echo "   heroku run python manage.py createsuperuser --app ${APP_NAME}"
echo
echo "🚀 Your Django Doctor Appointment System is now live on Heroku!"
