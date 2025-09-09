# Railway Deployment Guide

This guide will help you deploy your FastAPI application to Railway.

## Files Created/Modified for Railway Deployment

### 1. Procfile
- **Purpose**: Tells Railway how to start your application
- **Content**: Uses gunicorn with uvicorn workers for production deployment

### 2. railway.json
- **Purpose**: Railway-specific configuration
- **Features**: 
  - Health check configuration
  - Restart policy
  - Build configuration

### 3. Updated main.py
- **Changes**:
  - Dynamic port configuration using `$PORT` environment variable
  - Added `/health` endpoint for Railway health checks

### 4. Updated requirements.txt
- **Added**: `gunicorn>=21.2.0` for production WSGI server

## Deployment Steps

### 1. Connect to Railway
1. Go to [Railway.app](https://railway.app)
2. Sign in with your GitHub account
3. Click "New Project"
4. Select "Deploy from GitHub repo"
5. Choose your repository

### 2. Configure Environment Variables
In your Railway project dashboard, add these environment variables:

```
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
CONVERTIO_API_KEY=your_convertio_api_key_here
```

**Note**: Railway automatically sets the `PORT` environment variable, so you don't need to set it manually.

### 3. Deploy
1. Railway will automatically detect your Python project
2. It will install dependencies from `requirements.txt`
3. It will use the `Procfile` to start your application
4. Your app will be available at the provided Railway URL

## Important Notes

### Port Configuration
- Railway automatically assigns a port via the `$PORT` environment variable
- Your app is configured to use this port dynamically
- The app binds to `0.0.0.0` to accept connections from Railway's load balancer

### Health Checks
- Railway will use the `/health` endpoint to monitor your application
- The endpoint returns `{"status": "healthy", "service": "AI-Takeoff Server"}`

### CORS Configuration
- Your app is configured with CORS middleware allowing all origins
- This is suitable for development but consider restricting origins for production

### File Storage
- Railway provides ephemeral file storage
- Files created during processing will be lost when the container restarts
- Consider using external storage (like Cloudinary) for persistent files

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check that all dependencies in `requirements.txt` are compatible
   - Ensure your Python version is supported by Railway

2. **Port Issues**
   - Make sure your app uses `$PORT` environment variable
   - Bind to `0.0.0.0`, not `localhost` or `127.0.0.1`

3. **Health Check Failures**
   - Verify the `/health` endpoint is accessible
   - Check application logs in Railway dashboard

4. **Environment Variables**
   - Ensure all required environment variables are set in Railway
   - Check that variable names match exactly (case-sensitive)

### Logs
- View application logs in the Railway dashboard
- Logs will show startup messages and any errors

## Testing Your Deployment

Once deployed, test these endpoints:

1. **Health Check**: `GET https://your-app.railway.app/health`
2. **Root**: `GET https://your-app.railway.app/`
3. **API Docs**: `GET https://your-app.railway.app/docs`

## Production Considerations

1. **Security**: Consider restricting CORS origins for production
2. **Monitoring**: Set up proper logging and monitoring
3. **Scaling**: Railway can auto-scale based on traffic
4. **Backups**: Ensure important data is stored in external services
5. **SSL**: Railway provides SSL certificates automatically

Your FastAPI application should now be successfully deployed to Railway!
