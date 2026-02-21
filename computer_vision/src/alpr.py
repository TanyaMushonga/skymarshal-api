import cv2
import os
import easyocr
import numpy as np
import logging
import time
from ultralytics import YOLO

logger = logging.getLogger(__name__)

class LicensePlateReader:
    def __init__(self, plate_model_path=None):
        """
        Initialize the License Plate Reader.
        :param plate_model_path: Path to the YOLO model trained for license plate detection.
        """
        if plate_model_path is None:
            # Default to best.pt in the same directory as this file's parent (computer_vision root)
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            plate_model_path = os.path.join(base_dir, 'best.pt')

        # Load specialized YOLO model for license plates
        self.model_loaded = False
        try:
            self.plate_model = YOLO(plate_model_path)
            self.model_loaded = True
            logger.info(f"Loaded license plate model: {plate_model_path}")
        except Exception as e:
            logger.warning(f"License plate model could not be loaded from {plate_model_path}: {e}. ALPR will be disabled.")
        
        # Initialize EasyOCR reader
        try:
            # gpu=True if you have a CUDA-enabled GPU
            self.reader = easyocr.Reader(['en'], gpu=False)
            logger.info("EasyOCR initialized.")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR: {e}")
            self.reader = None
        
        # Cache for plate numbers to avoid flickering {track_id: "PLATE"}
        self.plate_cache = {}

    def detect_and_read(self, vehicle_frame, track_id):
        """
        Detect license plate within a vehicle crop and read the text.
        :param vehicle_frame: Cropped image of the vehicle.
        :param track_id: Tracking ID of the vehicle.
        :return: String representing the license plate text or None.
        """
        now = time.time()
        
        # Check cache
        if track_id in self.plate_cache:
            data = self.plate_cache[track_id]
            # If we already have a successful read, return it
            if data['text'] and data['text'] != "Unknown":
                return data['text']
            
            # If we recently failed or are "Scanning", only retry every 2 seconds (60 frames at 30fps)
            if now - data['last_attempt'] < 2.0:
                return data['text']

        if not self.model_loaded:
            return None

        # Detect license plates in the vehicle crop
        results = self.plate_model(vehicle_frame, verbose=False)
        
        best_plate_text = "Scanning..."
        
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                plate_crop = vehicle_frame[y1:y2, x1:x2]
                
                if plate_crop.size == 0:
                    continue
                
                # Perform OCR
                ocr_results = self.reader.readtext(plate_crop)
                
                if ocr_results:
                    text = ocr_results[0][1]
                    confidence = ocr_results[0][2]
                    
                    if confidence > 0.4:
                        best_plate_text = text.upper().replace(" ", "")
                        break
        
        # Update cache with timestamp
        self.plate_cache[track_id] = {
            'text': best_plate_text,
            'last_attempt': now
        }
            
        return best_plate_text
