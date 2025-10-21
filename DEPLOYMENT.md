# FinBot Deployment Guide

## 🚀 Production Deployment Options

### Option 1: Docker Deployment (Recommended)

1. **Clone and Setup**
   ```bash
   git clone <your-repo>
   cd FinBot
   cp .env.example .env
   # Edit .env with your production values
   ```

2. **Deploy with Docker Compose**
   ```bash
   docker-compose up -d
   ```

3. **Access the Application**
   - Main App: http://localhost:5000
   - ICT Dashboard: http://localhost:5000/api/ict/

### Option 2: Traditional Server Deployment

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   ```bash
   export FLASK_ENV=production
   export SECRET_KEY=your-secret-key
   export REDIS_HOST=localhost
   ```

3. **Run with Gunicorn**
   ```bash
   gunicorn --bind 0.0.0.0:5000 --workers 4 wsgi:application
   ```

### Option 3: Cloud Platform Deployment

#### Heroku
1. Create `Procfile`:
   ```
   web: gunicorn wsgi:application
   ```

2. Deploy:
   ```bash
   git push heroku main
   ```

#### Railway
1. Connect your GitHub repo
2. Set environment variables in Railway dashboard
3. Deploy automatically

#### DigitalOcean App Platform
1. Connect GitHub repo
2. Configure build settings
3. Set environment variables
4. Deploy

## 🔧 Environment Variables

Create a `.env` file with:

```env
# Flask Configuration
FLASK_ENV=production
SECRET_KEY=your-super-secret-key-change-this-in-production

# Database Configuration
DATABASE_URL=sqlite:///finbot.db

# Redis Configuration (Optional)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=
REDIS_URL=redis://localhost:6379/0

# API Keys (Optional - will fallback to free services)
FMP_API_KEY=your_fmp_api_key_here
TWELVE_DATA_API_KEY=your_twelve_data_api_key_here

# CORS Configuration
CORS_ORIGINS=http://localhost:3000,http://localhost:5000

# Logging
LOG_LEVEL=INFO

# Production Settings
DEBUG=False
TESTING=False
```

## 📱 Mobile Optimization

The app is now optimized for mobile devices with:
- ✅ Responsive sidebar navigation
- ✅ Touch-friendly mobile menu
- ✅ Mobile-optimized ICT dashboard
- ✅ Proper viewport configuration
- ✅ Accessible navigation

## 🔒 Security Features

- CSRF protection
- Secure session cookies
- Security headers
- Input validation
- SQL injection protection
- XSS protection

## 📊 Monitoring & Health Checks

- Health check endpoint: `/api/ict/health`
- System status indicators
- Error logging
- Performance monitoring

## 🎯 ICT Trading Features

- Real-time market analysis
- Premium/Discount level calculations
- Trading journal with CRUD operations
- Backtesting engine
- Multi-symbol market overview
- Mobile-responsive design

## 📞 Support

For deployment issues or questions, check:
1. Application logs
2. Health check endpoint
3. Environment variable configuration
4. Database connectivity
5. Redis connectivity (if using caching)
