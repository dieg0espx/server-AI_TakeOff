# Railway Deployment Checklist

## ✅ Pre-Deployment Checklist

### 1. Files Created
- [x] `Dockerfile` - Multi-stage Docker build with all system dependencies
- [x] `.dockerignore` - Excludes unnecessary files from Docker image
- [x] `railway.toml` - Railway-specific configuration
- [x] `DEPLOYMENT.md` - Complete deployment guide

### 2. Prepare Your Repository

```bash
# Add all new files
git add Dockerfile .dockerignore railway.toml DEPLOYMENT.md README.md RAILWAY_CHECKLIST.md

# Commit changes
git commit -m "Add Docker configuration for Railway deployment"

# Push to GitHub (master branch)
git push origin master
```

### 3. Get Your API Keys

- [ ] **Convertio API Key** - Get from https://convertio.co/api/
  - Sign up for free account
  - Copy your API key
  - Required for PDF to SVG conversion

- [ ] **OpenAI API Key** - Get from https://platform.openai.com/api-keys
  - Sign up for OpenAI account
  - Create a new API key
  - Required for professionally rewriting extracted text from PDFs

### 4. Railway Setup

#### Create New Project
1. Go to https://railway.app/dashboard
2. Click "New Project"
3. Select "Deploy from GitHub repo"
4. Authorize Railway to access your repositories
5. Select your `server-AI_TakeOff` repository

#### Set Environment Variables
In Railway dashboard → Variables tab, add:

```
CONVERTIO_API_KEY=your_actual_api_key_here
OPENAI_API_KEY=your_openai_api_key_here
API_URL=https://ttfconstruction.com/ai-takeoff-results/create.php
```

**Note:** Railway automatically sets `PORT` - don't override it!

### 5. Deploy & Verify

After deployment completes, test these endpoints:

```bash
# Replace YOUR_APP_URL with your Railway app URL

# 1. Health check
curl https://YOUR_APP_URL/health
# Expected: {"status":"healthy","service":"AI-Takeoff Server"}

# 2. Root endpoint
curl https://YOUR_APP_URL/
# Expected: {"message":"AI-Takeoff Server is running!","status":"running"}

# 3. API docs
# Visit: https://YOUR_APP_URL/docs
```

## 🔧 Local Docker Testing (Optional)

Test your Docker setup locally before deploying:

```bash
# 1. Build the image
docker build -t ai-takeoff-server .

# 2. Run the container
docker run -p 5001:5001 \
  -e CONVERTIO_API_KEY=your_key_here \
  -e OPENAI_API_KEY=your_openai_key_here \
  -e API_URL=https://ttfconstruction.com/ai-takeoff-results/create.php \
  ai-takeoff-server

# 3. Test in another terminal
curl http://localhost:5001/health

# 4. Stop the container (Ctrl+C)
```

## 📊 Expected Build Time

- **First deployment:** 8-12 minutes
  - Installing system dependencies
  - Installing Python packages
  - Building Docker image

- **Subsequent deployments:** 3-5 minutes
  - Railway caches layers for faster builds

## 🚨 Common Issues

### Issue: Build fails with "No space left on device"
**Solution:** Railway free tier has 1GB build storage. If exceeded:
- Optimize Dockerfile (already done)
- Upgrade to Railway Pro plan

### Issue: Health check fails
**Solution:** 
- Check logs in Railway dashboard
- Verify PORT is not manually set in environment variables
- Railway auto-sets PORT - the app reads it from `os.getenv("PORT", 5001)`

### Issue: PDF conversion not working
**Solution:**
- Verify CONVERTIO_API_KEY is set correctly
- Check Convertio account has available quota

### Issue: Text is not being rewritten by OpenAI
**Solution:**
- Verify OPENAI_API_KEY is set correctly in Railway environment variables
- Check OpenAI account has available credits
- View logs to see if OpenAI API call is succeeding

### Issue: 502 Bad Gateway
**Solution:**
- Check deployment logs for errors
- Verify all system dependencies are in Dockerfile (already included)
- Service may be restarting - wait 30 seconds and retry

## 📝 Post-Deployment

### Get Your Railway URL
1. Go to your Railway project
2. Click on your service
3. Go to "Settings" tab
4. Find the public URL (e.g., `https://your-app.railway.app`)

### Add Custom Domain (Optional)
1. In Railway Settings → Networking
2. Click "Generate Domain" for a custom Railway subdomain
3. Or add your own domain

### Monitor Your App
- **Logs:** Railway Dashboard → Deployments → Click deployment → View logs
- **Metrics:** Railway Dashboard → Metrics tab
- **Health:** Check `/health` endpoint regularly

## 💰 Railway Pricing

- **Free Tier:** $5 free credit per month
- **Estimated Usage:** ~$2-8/month for low-medium traffic
- **Billing:** Pay-as-you-go after free credits

## 🎉 You're Done!

Your AI-Takeoff Server is now deployed and ready to process construction drawings!

**Need Help?**
- Check [DEPLOYMENT.md](DEPLOYMENT.md) for detailed guide
- Railway Discord: https://discord.gg/railway
- Railway Docs: https://docs.railway.app

