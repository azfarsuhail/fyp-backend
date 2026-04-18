import requests

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
REGISTER_ENDPOINT = f"{BASE_URL}/auth/register"

# User Data for Saima
# Note: Password meets March 2026 security hardening requirements
saima_data = {
    "email": "saima.medical@example.com",
    "password": "SecurePassword123!", 
    "full_name": "Saima Rahman",
    "role": "patient",  # Options: patient, gp
    "age": 45,
    "pain_level": 6,
    "mobility_level": "moderate",
    "has_support": True
}

def create_user():
    print(f"Attempting to register user: {saima_data['full_name']}...")
    
    try:
        response = requests.post(REGISTER_ENDPOINT, json=saima_data)
        
        if response.status_code == 201 or response.status_code == 200:
            print("✅ Success: User 'Saima' has been created.")
            print(f"Response: {response.json()}")
        elif response.status_code == 400:
            print("❌ Failed: User might already exist or validation failed.")
            print(f"Detail: {response.json().get('detail')}")
        else:
            print(f"❌ Failed with status code: {response.status_code}")
            print(response.text)
            
    except requests.exceptions.ConnectionError:
        print("❌ Error: Could not connect to the backend. Is FastAPI running on port 8000?")

if __name__ == "__main__":
    create_user()