import os
import django
import sys
import secrets

# Setup Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')
django.setup()

from apps.drones.models import Drone, DroneAPIKey

def generate_key_for_drone(drone_id, key_name="ESP32-CAM Key"):
    try:
        drone = Drone.objects.get(drone_id=drone_id)
    except Drone.DoesNotExist:
        print(f"❌ Error: Drone with ID '{drone_id}' not found.")
        return

    # Deactivate old keys for this drone if any
    DroneAPIKey.objects.filter(drone=drone, is_active=True).update(is_active=False)

    # Create new key
    api_key_obj = DroneAPIKey(drone=drone, name=key_name)
    api_key_obj.save()
    
    # We retrieve the raw key from the temporary attribute set during save
    raw_key = getattr(api_key_obj, '_raw_key', None)
    
    if raw_key:
        print("\n" + "="*50)
        print(f"✅ API Key generated for Drone: {drone.name} ({drone_id})")
        print("="*50)
        print(f"🔑 RAW KEY: {raw_key}")
        print("="*50)
        print("⚠️  IMPORTANT: Copy this key now! It will not be shown again.")
        print("Paste this into your 'wifi_config.h' file in the firmware folder.")
        print("="*50 + "\n")
    else:
        print("❌ Error: Failed to retrieve raw key.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python generate_drone_key.py <drone_id>")
        sys.exit(1)
    
    drone_id = sys.argv[1]
    name = sys.argv[2] if len(sys.argv) > 2 else "ESP32-CAM Key"
    generate_key_for_drone(drone_id, name)
