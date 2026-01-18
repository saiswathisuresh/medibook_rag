import os
import requests
from dotenv import load_dotenv

load_dotenv()

GROK_API_KEY = os.getenv("GROK_API_KEY")
print(f"API Key (first 10 chars): {GROK_API_KEY[:10]}...")
print(f"API Key length: {len(GROK_API_KEY) if GROK_API_KEY else 0}")

GROK_URL = "https://api.x.ai/v1/chat/completions"

headers = {
    "Authorization": f"Bearer {GROK_API_KEY}",
    "Content-Type": "application/json"
}

# Simple test
payload = {
    "model": "grok-3",
    "messages": [{"role": "user", "content": "Say hello in one word"}],
    "max_tokens": 50,
    "temperature": 0.7
}

print("\n--- Sending request to Grok API ---")
try:
    r = requests.post(GROK_URL, headers=headers, json=payload, timeout=30)
    print(f"Status Code: {r.status_code}")
    print(f"Response Headers: {dict(r.headers)}")
    print(f"Response Body: {r.text}")
    
    if r.status_code == 200:
        data = r.json()
        print(f"\n✅ SUCCESS!")
        print(f"Answer: {data['choices'][0]['message']['content']}")
    else:
        print(f"\n❌ FAILED!")
        print(f"Error: {r.text}")
        
except Exception as e:
    print(f"\n❌ EXCEPTION: {str(e)}")