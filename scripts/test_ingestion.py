import requests
import base64
import time
import json
import os

# Configuration
INGEST_URL = "http://localhost:3003/api/v1/ingest"
DRONE_ID = "DRN-TEST-123"
STREAM_ID = "test-stream-uuid"
PATROL_ID = "test-patrol-uuid"

def get_base64_image():
    # Construct a small dummy image or use an existing one if available
    # For testing, we'll just use a small valid base64 string
    return "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg=="

def send_frame(frame_number):
    payload = {
        "drone_id": DRONE_ID,
        "stream_id": STREAM_ID,
        "frame_data": get_base64_image(),
        "frame_number": frame_number,
        "timestamp": int(time.time() * 1000),
        "gps": {"lat": -1.2833, "lng": 36.8167}
    }
    
    try:
        response = requests.post(INGEST_URL, json=payload)
        if response.status_code == 202:
            print(f"✅ Frame {frame_number} accepted")
        else:
            print(f"❌ Failed to send frame {frame_number}: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    print(f"Starting test stream to {INGEST_URL}...")
    for i in range(5):
        send_frame(i)
        time.sleep(1)
