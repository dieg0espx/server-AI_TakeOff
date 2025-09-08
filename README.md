# FastAPI Server

A simple and fast API server built with FastAPI.

## Features

- RESTful API endpoints for items and users
- Automatic API documentation
- CORS middleware enabled
- Health check endpoint
- Pydantic models for data validation

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure Cloudinary (optional but recommended):
   Create a `.env` file in the server directory with your Cloudinary credentials:
   ```bash
   # Cloudinary Configuration
   CLOUDINARY_CLOUD_NAME=your_cloud_name_here
   CLOUDINARY_API_KEY=your_api_key_here
   CLOUDINARY_API_SECRET=your_api_secret_here
   ```
   
   You can get these values from your Cloudinary dashboard: https://cloudinary.com/console
   
   If Cloudinary is not configured, the processing will still work but images won't be uploaded to the cloud.

3. Run the server:
```bash
python main.py
```

Or using uvicorn directly:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 5001
```

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
