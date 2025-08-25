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

2. Run the server:
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

## API Documentation

Once the server is running, visit http://localhost:5001/docs to see the interactive API documentation powered by Swagger UI.
