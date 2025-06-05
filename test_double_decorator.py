#!/usr/bin/env python3
"""
Test if double decorators cause route registration issues
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Test app with double decorators (current problematic code)
app_double = FastAPI()

@app_double.get("/healthz")
@app_double.get("/healthz/", include_in_schema=False)
async def health_check_double():
    return {"status": "healthy", "service": "test", "version": "1.0.0"}

# Test app with single decorator (proposed fix)
app_single = FastAPI()

@app_single.get("/healthz")
async def health_check_single():
    return {"status": "healthy", "service": "test", "version": "1.0.0"}

def test_decorators():
    print("🧪 Testing FastAPI Double Decorator Issue")
    print("=" * 50)
    
    # Test double decorator
    print("\n🔍 Testing DOUBLE decorator pattern (current code):")
    client_double = TestClient(app_double)
    try:
        response = client_double.get("/healthz")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json() if response.status_code == 200 else 'FAILED'}")
        
        # Check if route is in OpenAPI
        openapi = client_double.get("/openapi.json").json()
        healthz_in_openapi = "/healthz" in openapi.get("paths", {})
        print(f"   Route in OpenAPI: {healthz_in_openapi}")
        
    except Exception as e:
        print(f"   ERROR: {e}")
    
    # Test single decorator
    print("\n🔍 Testing SINGLE decorator pattern (proposed fix):")
    client_single = TestClient(app_single)
    try:
        response = client_single.get("/healthz")
        print(f"   Status Code: {response.status_code}")
        print(f"   Response: {response.json() if response.status_code == 200 else 'FAILED'}")
        
        # Check if route is in OpenAPI
        openapi = client_single.get("/openapi.json").json()
        healthz_in_openapi = "/healthz" in openapi.get("paths", {})
        print(f"   Route in OpenAPI: {healthz_in_openapi}")
        
    except Exception as e:
        print(f"   ERROR: {e}")

if __name__ == "__main__":
    test_decorators()