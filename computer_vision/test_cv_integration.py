import os
import sys
import cv2
import base64
import argparse
import logging

# Setup Python path to include project root
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Django settings module if needed (though components are mostly standalone here)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.settings")

from computer_vision.src.detector import VehicleDetector
from computer_vision.src.processor import VideoProcessor

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Test CV Integration with an image.")
    parser.add_argument("--image", required=True, help="Path to the sample image.")
    parser.add_argument("--output", default="computer_vision/output/test_result.jpg", help="Path to save the output.")
    args = parser.parse_args()

    if not os.path.exists(args.image):
        logger.error(f"Image not found: {args.image}")
        return

    # Load image
    frame = cv2.imread(args.image)
    if frame is None:
        logger.error(f"Failed to load image: {args.image}")
        return

    logger.info(f"Loaded image {args.image} of size {frame.shape}")

    # Initialize components
    try:
        detector = VehicleDetector()
        processor = VideoProcessor(detector)
    except Exception as e:
        logger.error(f"Failed to initialize CV components: {e}")
        return

    # Encode to base64 to simulate Kafka payload (how processor.process_frame_data expects it)
    _, buffer = cv2.imencode('.jpg', frame)
    frame_base64 = base64.b64encode(buffer).decode('utf-8')

    # Process frame
    logger.info("Processing image through VideoProcessor...")
    detections = processor.process_frame_data(frame_base64, frame_number=0)

    # Annotate results
    logger.info(f"Processing complete. Found {len(detections)} detections.")
    
    for det in detections:
        x1, y1, x2, y2 = det['box_coordinates']
        # Truncate box coordinates to ints
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        
        label = f"{det['vehicle_type']} ({det['confidence']:.2f})"
        if det.get('license_plate') and det['license_plate'] != "Scanning...":
            label += f" | {det['license_plate']}"
        if det.get('speed', 0) > 0:
            label += f" | {det['speed']} km/h"
        
        # Color based on confidence (Green to Red gradient or just Green for simplicity)
        color = (0, 255, 0)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        
        # Draw label background
        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
        cv2.rectangle(frame, (x1, y1 - h - 10), (x1 + w, y1), color, -1)
        cv2.putText(frame, label, (x1, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 2)
        
        logger.info(f"Detection: {label}")

    # Save output
    output_dir = os.path.dirname(args.output)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    cv2.imwrite(args.output, frame)
    logger.info(f"Annotated image saved to: {args.output}")

if __name__ == "__main__":
    main()
