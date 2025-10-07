#!/usr/bin/env python3
"""
Test script to verify the application can start properly
"""
import sys
import os
import traceback

def test_imports():
    """Test all required imports"""
    print("🔍 Testing imports...")
    
    try:
        import fastapi
        print("✅ FastAPI imported")
    except ImportError as e:
        print(f"❌ FastAPI import failed: {e}")
        return False
    
    try:
        import uvicorn
        print("✅ Uvicorn imported")
    except ImportError as e:
        print(f"❌ Uvicorn import failed: {e}")
        return False
    
    try:
        import requests
        print("✅ Requests imported")
    except ImportError as e:
        print(f"❌ Requests import failed: {e}")
        return False
    
    try:
        import cloudinary
        print("✅ Cloudinary imported")
    except ImportError as e:
        print(f"❌ Cloudinary import failed: {e}")
        return False
    
    return True

def test_app_creation():
    """Test if the FastAPI app can be created"""
    print("🔍 Testing FastAPI app creation...")
    
    try:
        # Add current directory to path
        sys.path.insert(0, os.getcwd())
        
        # Import the app
        from main import app
        print("✅ FastAPI app imported successfully")
        
        # Test if app has the health endpoint
        routes = [route.path for route in app.routes]
        if "/health" in routes:
            print("✅ Health endpoint found")
        else:
            print("⚠️  Health endpoint not found")
            print(f"Available routes: {routes}")
        
        return True
        
    except Exception as e:
        print(f"❌ App creation failed: {e}")
        print("Full traceback:")
        traceback.print_exc()
        return False

def test_port_config():
    """Test port configuration"""
    print("🔍 Testing port configuration...")
    
    port = os.getenv("PORT", "5001")
    print(f"Port from environment: {port}")
    
    try:
        port_int = int(port)
        print(f"✅ Port {port_int} is valid")
        return True
    except ValueError as e:
        print(f"❌ Invalid port: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing AI-Takeoff Server startup...")
    print("=" * 50)
    
    success = True
    
    # Test imports
    if not test_imports():
        success = False
    
    print()
    
    # Test port config
    if not test_port_config():
        success = False
    
    print()
    
    # Test app creation
    if not test_app_creation():
        success = False
    
    print()
    print("=" * 50)
    
    if success:
        print("✅ All tests passed! Server should start successfully.")
        sys.exit(0)
    else:
        print("❌ Some tests failed! Check the errors above.")
        sys.exit(1)
