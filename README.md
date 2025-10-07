# AI-Takeoff Server

A FastAPI-based server for processing construction drawings and performing AI-based takeoff analysis.

## Features

- PDF to SVG conversion
- Multi-step processing pipeline for construction drawings
- Detection of various construction elements (X-shores, squares, frames, etc.)
- Cloudinary integration for result storage
- Automatic API documentation
- CORS middleware enabled
- Health check endpoint for monitoring
- Docker support for easy deployment

## Environment Variables

Create a `.env` file in the root directory:

```bash
# Server Configuration
PORT=5001

# Convertio API (for PDF to SVG conversion)
CONVERTIO_API_KEY=your_convertio_api_key_here

# External API Configuration
API_URL=https://ttfconstruction.com/ai-takeoff-results/create.php
```

Get your Convertio API key from: https://convertio.co/api/

## Local Development Setup

### Option 1: Using Python Virtual Environment

1. **Create and activate virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. **Install system dependencies (macOS):**
```bash
brew install poppler tesseract cairo pango gdk-pixbuf
```

**Install system dependencies (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install -y poppler-utils tesseract-ocr libcairo2 libpango-1.0-0
```

3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run the server:**
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5001
```

### Option 2: Using Docker (Recommended)

1. **Build the Docker image:**
```bash
docker build -t ai-takeoff-server .
```

2. **Run the container:**
```bash
docker run -p 5001:5001 \
  -e CONVERTIO_API_KEY=your_key_here \
  -e API_URL=https://ttfconstruction.com/ai-takeoff-results/create.php \
  ai-takeoff-server
```

3. **Test the server:**
```bash
curl http://localhost:5001/health
```

## Deployment to Railway

This application is optimized for deployment on Railway. See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed instructions.

**Quick Deploy:**

1. Push your code to GitHub
2. Connect your repo to Railway
3. Set environment variables in Railway dashboard
4. Deploy automatically

Railway will use the `Dockerfile` and `railway.toml` configuration files.

## API Endpoints

### Base URLs
- **Server**: http://localhost:5001
- **API Documentation**: http://localhost:5001/docs
- **Alternative Docs**: http://localhost:5001/redoc

### Available Endpoints

#### Root & Health
- `GET /` - Welcome message
- `GET /health` - Health check

#### Items
- `GET /items` - Get all items
- `GET /items/{item_id}` - Get specific item
- `POST /items` - Create new item
- `PUT /items/{item_id}` - Update item
- `DELETE /items/{item_id}` - Delete item

#### Users
- `GET /users` - Get all users
- `GET /users/{user_id}` - Get specific user
- `POST /users` - Create new user

#### AI-Takeoff Endpoints
- `GET /AI-Takeoff/{upload_id}` - Get AI processing result for specific upload

#### Example Data
- `GET /example-data` - Get sample data

## Example Usage

### Test AI-Takeoff endpoints
```bash
# Get AI processing result
curl "http://localhost:5001/AI-Takeoff/test123"
```

### Create an item
```bash
curl -X POST "http://localhost:5001/items" \
     -H "Content-Type: application/json" \
     -d '{"name": "Test Item", "description": "A test item", "price": 19.99}'
```

### Get all items
```bash
curl "http://localhost:5001/items"
```

### Create a user
```bash
curl -X POST "http://localhost:5001/users" \
     -H "Content-Type: application/json" \
     -d '{"username": "testuser", "email": "test@example.com"}'
```

## Cloudinary Integration

The server automatically uploads processing result images to Cloudinary in the `final_AI_TakeOff` folder after the processing pipeline completes. The Cloudinary manager is located in `api/cloudinary_manager.py` and is called from the processors pipeline. This includes:

- Original SVG drawing
- Step-by-step processing results (Step1.svg through Step8.svg)
- Detection result images (Step4-results.png through Step8-results.png)

The Cloudinary URLs are stored in the `data.json` file under the `cloudinary_urls` section, making them easily accessible for the frontend application.

### Cloudinary Folder Structure
```
final_AI_TakeOff/
├── original_drawing
├── step1_duplicate_removal
├── step2_color_modification
├── step3_background_addition
├── step4_color_coding
├── step5_blue_x_detection
├── step6_red_squares_detection
├── step7_pink_shapes_detection
├── step8_green_rectangles_detection
├── step4_results
├── step5_results
├── step6_results
├── step7_results
└── step8_results
```

### Testing Cloudinary Integration
To test the Cloudinary integration, run:
```bash
python test_cloudinary.py
```

This will verify your environment variables and test uploading a sample file if available.

## API Documentation

Once the server is running, visit http://localhost:5001/docs to see the interactive API documentation powered by Swagger UI.
