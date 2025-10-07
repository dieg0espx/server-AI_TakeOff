#!/usr/bin/env python3
"""
Simple health check test script
"""
import requests
import sys
import time
import os

def test_health_endpoint(port=5001, max_attempts=30):
    """Test the health endpoint with retries"""
    url = f"http://localhost:{port}/health"
    
    print(f"🔍 Testing health endpoint: {url}")
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                print(f"✅ Health check passed! Status: {response.status_code}")
                print(f"📊 Response: {response.json()}")
                return True
            else:
                print(f"⚠️  Attempt {attempt}: Status {response.status_code}")
        except requests.exceptions.RequestException as e:
            print(f"❌ Attempt {attempt}: {e}")
        
        if attempt < max_attempts:
            print(f"⏳ Waiting 2 seconds before retry {attempt + 1}...")
            time.sleep(2)
    
    print(f"❌ Health check failed after {max_attempts} attempts")
    return False

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5001))
    success = test_health_endpoint(port)
    sys.exit(0 if success else 1)
