from src.speed_estimator import SpeedEstimator
from src.alpr import LicensePlateReader
import cv2
import os

class VideoProcessor:
    def __init__(self, detector, output_dir='output', speed_estimator=None, alpr_reader=None):
        """
        Initialize the VideoProcessor.
        :param detector: An instance of a vehicle detector.
        :param output_dir: Directory where processed videos will be saved.
        :param speed_estimator: An optional SpeedEstimator instance.
        :param alpr_reader: An optional LicensePlateReader instance.
        """
        self.detector = detector
        self.output_dir = output_dir
        self.speed_estimator = speed_estimator if speed_estimator else SpeedEstimator()
        self.alpr_reader = alpr_reader if alpr_reader else LicensePlateReader()
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

    def process_video(self, input_path):
        """
        Process a video file, detect vehicles, track them, and estimate speed.
        :param input_path: Path to the input video file.
        """
        if not os.path.exists(input_path):
            print(f"Error: Input video file {input_path} not found.")
            return

        cap = cv2.VideoCapture(input_path)
        if not cap.isOpened():
            print(f"Error: Could not open video {input_path}")
            return

        # Get video properties
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        # Prepare output video writer
        output_filename = os.path.basename(input_path)
        output_path = os.path.join(self.output_dir, f"speed_{output_filename}")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, fps, (width, height))

        print(f"Processing video with speed estimation: {input_path}...")
        
        frame_idx = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            # Detect and track vehicles
            results = self.detector.detect_vehicles(frame)
            
            # Extract detection results
            if results[0].boxes.id is not None:
                boxes = results[0].boxes.xyxy.cpu().numpy()
                track_ids = results[0].boxes.id.int().cpu().tolist()
                
                for box, track_id in zip(boxes, track_ids):
                    x1, y1, x2, y2 = map(int, box)
                    bottom_center = (int((x1 + x2) / 2), y2)
                    
                    # Estimate speed
                    speed = self.speed_estimator.estimate_speed(
                        track_id, bottom_center, frame_idx, fps
                    )
                    
                    # Identify License Plate
                    # Crop vehicle for ALPR
                    vehicle_crop = frame[y1:y2, x1:x2]
                    plate_text = "Scanning..."
                    if vehicle_crop.size > 0:
                        plate_text = self.alpr_reader.detect_and_read(vehicle_crop, track_id)

                    # Draw bounding box
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    
                    # Draw ID, Speed, and Plate label
                    label = f"ID: {track_id} | {plate_text} | {speed} km/h"
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
                    
                    # Ensure label stays within frame
                    label_y = max(y1, h + 10)
                    cv2.rectangle(frame, (x1, label_y - h - 10), (x1 + w, label_y), (0, 255, 0), -1)
                    cv2.putText(frame, label, (x1, label_y - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            
            # Write the frame to the output video
            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()
        print(f"Processing complete. Result saved to: {output_path}")
