import requests
import os
import io
import time
from PIL import Image, ImageDraw
import json

BASE_URL = "http://localhost:8003/api/v1"

def create_test_image():
    # Create a simple image with text
    img = Image.new('RGB', (800, 600), color='white')
    d = ImageDraw.Draw(img)
    # Add text
    d.text((100, 100), "Total Usage: 123.45 kWh", fill=(0, 0, 0))
    d.text((100, 200), "Total Cost: 456.78 RMB", fill=(0, 0, 0))
    d.text((100, 300), "User ID: 1234567890", fill=(0, 0, 0))
    
    # Save to buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return buf

def test_analyze():
    print("Testing /layout/analyze endpoint...")
    img_buf = create_test_image()
    
    try:
        files = {'file': ('test_bill.png', img_buf, 'image/png')}
        response = requests.post(f"{BASE_URL}/layout/analyze", files=files)
        
        if response.status_code == 200:
            data = response.json()
            print("Analyze Success!")
            print(f"File Token: {data.get('file_token')}")
            print(f"Regions Count: {len(data.get('regions', []))}")
            if data.get('regions'):
                print(f"Sample Region: {data['regions'][0]}")
            return data.get('file_token')
        else:
            print(f"Analyze Failed: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Analyze Exception: {e}")
        return None

def test_extract(token):
    if not token:
        print("Skipping extract test (no token)")
        return

    print("\nTesting /layout/extract endpoint...")
    try:
        payload = {'file_token': token}
        response = requests.post(f"{BASE_URL}/layout/extract", data=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("Extract Success!")
            print(f"Extracted Usage: {data.get('usage')}")
            # print(f"Full Result: {json.dumps(data, indent=2, ensure_ascii=False)}")
        else:
            print(f"Extract Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Extract Exception: {e}")

if __name__ == "__main__":
    # Wait for server to start if needed
    time.sleep(5) 
    token = test_analyze()
    test_extract(token)
