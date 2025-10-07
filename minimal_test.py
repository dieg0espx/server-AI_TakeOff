#!/usr/bin/env python3
"""
Minimal test server to isolate Railway deployment issues
"""
import os
import sys
from fastapi import FastAPI
import uvicorn

# Create minimal FastAPI app
app = FastAPI(title="Minimal Test Server")

@app.get("/")
async def root():
    return {"message": "Minimal test server is running!"}

@app.get("/health")
async def health():
    return {"status": "healthy", "service": "Minimal Test Server"}

if __name__ == "__main__":
    print("=" * 50)
    print("🧪 Starting Minimal Test Server...")
    print("=" * 50)
    
    # Debug environment
    print(f"📋 Environment:")
    print(f"  PORT: {os.getenv('PORT', 'NOT SET')}")
    print(f"  PYTHONPATH: {os.getenv('PYTHONPATH', 'NOT SET')}")
    print(f"  PWD: {os.getcwd()}")
    print(f"  Python: {sys.version}")
    
    # Debug file system
    print(f"📂 Directory Contents:")
    try:
        for item in os.listdir('.'):
            print(f"  - {item}")
    except Exception as e:
        print(f"  Error: {e}")
    
    # Get port
    port = int(os.getenv("PORT", 5001))
    print(f"🌐 Starting on port {port}")
    print("=" * 50)
    
    try:
        uvicorn.run(app, host="0.0.0.0", port=port)
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        raise
