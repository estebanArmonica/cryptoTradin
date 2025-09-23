import requests

def test_all_routes():
    base_url = "http://localhost:8000"
    
    endpoints = [
        "/",
        "/api/v1/status",
        "/api/v1/ping",
        "/docs",
        "/redoc",
        
        # Endpoints de trading que deberían funcionar
        "/api/v1/trading/test",
        "/api/v1/trading/coins/available",
        "/api/v1/trading/bitcoin/price",
        "/api/v1/trading/ethereum/price",
        
        # Endpoints que NO deberían existir (para comparar)
        "/api/trading/test",
        "/trading/test",
        "/v1/trading/test",
    ]
    
    print("🔍 Testing all routes...")
    print("=" * 60)
    
    for endpoint in endpoints:
        try:
            response = requests.get(base_url + endpoint, timeout=3)
            print(f"🌐 {endpoint}: {response.status_code}")
            if response.status_code != 200:
                print(f"   📄 Response: {response.text[:100]}...")
        except Exception as e:
            print(f"❌ {endpoint}: ERROR - {e}")
        
        print("-" * 40)

if __name__ == "__main__":
    test_all_routes()