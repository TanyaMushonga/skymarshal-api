from computer_vision.src.speed_estimator import SpeedEstimator
from computer_vision.src.alpr import LicensePlateReader
import cv2
import os
import numpy as np
import base64

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

    def process_frame_data(self, frame_data, frame_number, fps=30.0, annotate=True):
        """
        Process a single frame from Kafka stream.
        """
        # Decode base64
        jpg_original = base64.b64decode(frame_data)
        jpg_as_np = np.frombuffer(jpg_original, dtype=np.uint8)
        frame = cv2.imdecode(jpg_as_np, flags=1)

        detections = []
        annotated_frame_data = None
        
        # Detect
        results = self.detector.detect_vehicles(frame)

        if len(results) > 0 and results[0].boxes is not None:
            boxes_obj = results[0].boxes
            
            # Tracking check
            if boxes_obj.id is not None:
                boxes = boxes_obj.xyxy.cpu().numpy()
                track_ids = boxes_obj.id.int().cpu().tolist()
                confs = boxes_obj.conf.cpu().tolist()
                cls_ids = boxes_obj.cls.int().cpu().tolist()
                names = results[0].names

                for box, track_id, conf, cls_id in zip(boxes, track_ids, confs, cls_ids):
                    x1, y1, x2, y2 = map(int, box)
                    bottom_center = (int((x1 + x2) / 2), y2)
                    
                    # Estimate speed
                    speed = self.speed_estimator.estimate_speed(
                        track_id, bottom_center, frame_number, fps
                    )
                    
                    # ALPR
                    vehicle_crop = frame[y1:y2, x1:x2]
                    plate_text = None
                    if vehicle_crop.size > 0:
                        read_plate = self.alpr_reader.detect_and_read(vehicle_crop, track_id)
                        if read_plate and read_plate != "Scanning...":
                            plate_text = read_plate

                    vehicle_type = names[cls_id]

                    detections.append({
                        'track_id': track_id,
                        'vehicle_type': vehicle_type,
                        'confidence': conf,
                        'box_coordinates': [x1, y1, x2, y2],
                        'license_plate': plate_text,
                        'speed': speed
                    })

                    if annotate:
                        # Draw bounding box
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                        
                        # Label: ID: 1 | ABC-123 | 60 km/h
                        label_parts = [f"ID: {track_id}"]
                        if plate_text:
                            label_parts.append(plate_text)
                        label_parts.append(f"{speed} km/h")
                        
                        label = " | ".join(label_parts)
                        font_scale = 0.4
                        thickness = 1
                        (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                        
                        # Draw label background
                        cv2.rectangle(frame, (x1, y1 - h - 6), (x1 + w + 4, y1), (0, 255, 0), -1)
                        cv2.putText(frame, label, (x1 + 2, y1 - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)
            else:
                # Optional: log if we find vehicles but no IDs (means tracking failed)
                pass

        if annotate:
            # Reduce quality for throughput
            _, buffer = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 65])
            annotated_frame_data = base64.b64encode(buffer).decode('utf-8')

        return detections, annotated_frame_data

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
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 1)
                    
                    # Draw ID, Speed, and Plate label
                    label_parts = [f"ID: {track_id}"]
                    if plate_text and plate_text != "Scanning...":
                        label_parts.append(plate_text)
                    label_parts.append(f"{speed} km/h")
                    
                    label = " | ".join(label_parts)
                    font_scale = 0.45
                    thickness = 1
                    (w, h), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, thickness)
                    
                    # Ensure label stays within frame
                    label_y = max(y1, h + 10)
                    cv2.rectangle(frame, (x1, label_y - h - 6), (x1 + w + 4, label_y), (0, 255, 0), -1)
                    cv2.putText(frame, label, (x1 + 2, label_y - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (0, 0, 0), thickness)
            
            # Write the frame to the output video
            out.write(frame)
            frame_idx += 1

        cap.release()
        out.release()
        print(f"Processing complete. Result saved to: {output_path}")
