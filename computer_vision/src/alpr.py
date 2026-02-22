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
            # Fallback to direct OCR on vehicle crop if no specialized model
            return self._fallback_ocr(vehicle_frame, track_id, now)

        # Detect license plates in the vehicle crop
        results = self.plate_model(vehicle_frame, verbose=False)
        
        best_plate_text = None
        
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                plate_crop = vehicle_frame[y1:y2, x1:x2]
                
                if plate_crop.size == 0:
                    continue
                
                # Perform OCR on the plate crop
                ocr_results = self.reader.readtext(plate_crop)
                
                if ocr_results:
                    text = ocr_results[0][1]
                    confidence = ocr_results[0][2]
                    
                    if confidence > 0.3:
                        best_plate_text = self._clean_plate_text(text)
                        break
        
        # If specialized model found nothing, try fallback OCR on lower half of vehicle
        if not best_plate_text or best_plate_text == "Scanning...":
            best_plate_text = self._fallback_ocr(vehicle_frame, track_id, now)
        
        # Update cache with timestamp
        if best_plate_text:
            self.plate_cache[track_id] = {
                'text': best_plate_text,
                'last_attempt': now
            }
            
        return best_plate_text if best_plate_text else "Scanning..."

    def _fallback_ocr(self, vehicle_frame, track_id, now):
        """
        Fallback to OCR-ing the entire vehicle frame (or just the bottom half)
        if the specialized plate detector fails.
        """
        if not self.reader:
            return None
            
        # Focus on bottom 60% of the vehicle where plates usually are
        h, w = vehicle_frame.shape[:2]
        bottom_half = vehicle_frame[int(h*0.4):, :]
        
        if bottom_half.size == 0:
            return None
            
        ocr_results = self.reader.readtext(bottom_half)
        best_text = None
        best_conf = 0
        
        for (_, text, conf) in ocr_results:
            cleaned = self._clean_plate_text(text)
            # Zimbabwe/Standard plates are usually 6-8 chars
            if len(cleaned) >= 5 and conf > best_conf:
                best_text = cleaned
                best_conf = conf
        
        if best_text:
            logger.info(f"Fallback OCR detected plate for ID {track_id}: {best_text} (conf: {best_conf:.2f})")
            return best_text
            
        return None

    def _clean_plate_text(self, text):
        """Clean and normalize plate text."""
        # Remove non-alphanumeric characters and spaces
        import re
        cleaned = re.sub(r'[^A-Z0-9]', '', text.upper())
        return cleaned
