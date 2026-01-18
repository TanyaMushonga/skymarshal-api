from src.detector import VehicleDetector
from src.processor import VideoProcessor
import os

def main():
    """
    Main entry point for the SkyMarshal IATOS project.
    """
    # Initialize the vehicle detector
    # By default it uses yolov8n.pt
    detector = VehicleDetector()

    # Initialize the video processor
    processor = VideoProcessor(detector)

    # Path to the input video
    video_path = 'traffic_sample.mp4'

    # Check if the video file exists before processing
    if os.path.exists(video_path):
        processor.process_video(video_path)
    else:
        print(f"Warning: '{video_path}' not found in the project root.")
        print("Please place the video file in the project directory to begin detection.")
        print("Example structure:")
        print("  - SkyMarshal/")
        print("    - traffic_sample.mp4")
        print("    - main.py")
        print("    - src/...")

if __name__ == "__main__":
    main()
