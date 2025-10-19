# Railway Deployment Guide

This guide will help you deploy the AI-Takeoff Server to Railway using Docker.

## Prerequisites

- A [Railway](https://railway.app) account
- Your codebase pushed to GitHub (or GitLab/Bitbucket)
- A Convertio API key (optional but recommended for PDF to SVG conversion)

## Environment Variables

Before deploying, you need to set up the following environment variables in Railway:

### Required Variables

1. **PORT** (Railway sets this automatically, but defaults to 5001)
2. **CONVERTIO_API_KEY** - Get from https://convertio.co/api/
   - Required for PDF to SVG conversion
3. **OPENAI_API_KEY** - Get from https://platform.openai.com/api-keys
   - Required for professionally rewriting extracted text from PDFs

### Optional Variables

3. **API_URL** - Defaults to `https://ttfconstruction.com/ai-takeoff-results/create.php`
   - Only change if you have a different API endpoint

## Deployment Steps

### Option 1: Deploy from GitHub (Recommended)

1. **Push your code to GitHub**
   ```bash
   git add .
   git commit -m "Add Docker configuration for Railway"
   git push origin master
   ```

2. **Create a new project in Railway**
   - Go to [Railway Dashboard](https://railway.app/dashboard)
   - Click "New Project"
   - Select "Deploy from GitHub repo"
   - Authorize Railway to access your repositories
   - Select your `server-AI_TakeOff` repository

3. **Railway will automatically detect the Dockerfile**
   - It will use the `Dockerfile` in the root directory
   - The `railway.toml` file provides additional configuration

4. **Set Environment Variables**
   - In your Railway project dashboard, go to the "Variables" tab
   - Add the following variables:
     ```
     CONVERTIO_API_KEY=your_actual_api_key_here
     OPENAI_API_KEY=your_openai_api_key_here
     API_URL=https://ttfconstruction.com/ai-takeoff-results/create.php
     ```

5. **Deploy**
   - Railway will automatically build and deploy your application
   - Wait for the build to complete (may take 5-10 minutes on first deploy)

6. **Get your deployment URL**
   - Once deployed, Railway will provide a public URL like `https://your-app.railway.app`
   - You can also add a custom domain in Railway settings

### Option 2: Deploy using Railway CLI

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Login to Railway**
   ```bash
   railway login
   ```

3. **Initialize Railway project**
   ```bash
   railway init
   ```

4. **Set environment variables**
   ```bash
   railway variables set CONVERTIO_API_KEY=your_actual_api_key_here
   railway variables set OPENAI_API_KEY=your_openai_api_key_here
   railway variables set API_URL=https://ttfconstruction.com/ai-takeoff-results/create.php
   ```

5. **Deploy**
   ```bash
   railway up
   ```

## Verify Deployment

Once deployed, test your endpoints:

1. **Health Check**
   ```bash
   curl https://your-app.railway.app/health
   ```
   Should return: `{"status":"healthy","service":"AI-Takeoff Server"}`

2. **Root Endpoint**
   ```bash
   curl https://your-app.railway.app/
   ```
   Should return: `{"message":"AI-Takeoff Server is running!","status":"running"}`

3. **API Documentation**
   Visit: `https://your-app.railway.app/docs`

## Monitoring & Logs

- View logs in Railway dashboard under the "Deployments" tab
- Click on any deployment to see real-time logs
- Railway automatically restarts your service if it crashes

## Troubleshooting

### Build Failures

1. **System dependency issues**: The Dockerfile installs all required dependencies (poppler, tesseract, cairo)
2. **Python package issues**: Check `requirements.txt` is up to date

### Runtime Issues

1. **Check logs** in Railway dashboard
2. **Verify environment variables** are set correctly
3. **Check health endpoint** at `/health`

### Common Issues

**Issue: PDF conversion not working**
- Solution: Make sure `CONVERTIO_API_KEY` is set in Railway environment variables

**Issue: Service crashes on startup**
- Solution: Check logs for missing dependencies or configuration errors

**Issue: Timeout on long-running requests**
- Solution: Railway has no timeout limits (unlike Vercel), but check if the issue is with external API calls

## Costs

- Railway offers a free tier with 500 hours of usage per month
- After free tier, you pay for:
  - vCPU usage
  - Memory usage
  - Bandwidth
- Estimated cost: $5-15/month for low-medium traffic

## Auto-Deployments

Railway automatically deploys when you push to your connected branch (usually `master` or `main`).

To disable auto-deployments:
- Go to Settings → Service
- Turn off "Automatic Deployments"

## Scaling

Railway automatically scales based on demand. To adjust:
- Go to Settings → Service → Resources
- Adjust memory and CPU limits as needed

## Support

- Railway Discord: https://discord.gg/railway
- Railway Docs: https://docs.railway.app

