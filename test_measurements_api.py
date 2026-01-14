import requests
import json

def test_measurements_api():
    try:
        response = requests.get('http://127.0.0.1:8000/api/v1/production/measurements?skip=0&limit=10', timeout=5)
        
        if response.status_code == 200:
            print("SUCCESS: Measurements API endpoint is working!")
            data = response.json()
            print(f"Returned {len(data)} measurements")
            if data:
                print("Sample data:", json.dumps(data[0], indent=2, default=str)[:300])
            return True
        else:
            print(f"ERROR: API returned status {response.status_code}")
            print("Response:", response.text[:500])
            return False
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to API server. Is it running?")
        return False
    except Exception as e:
        print(f"ERROR: {e}")
        return False

if __name__ == "__main__":
    test_measurements_api()
