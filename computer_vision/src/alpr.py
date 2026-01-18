import cv2
import easyocr
import numpy as np
from ultralytics import YOLO

class LicensePlateReader:
    def __init__(self, plate_model_path='best.pt'):
        """
        Initialize the License Plate Reader.
        :param plate_model_path: Path to the YOLO model trained for license plate detection.
        """
        # Load specialized YOLO model for license plates
        try:
            self.plate_model = YOLO(plate_model_path)
            self.model_loaded = True
        except Exception as e:
            print(f"Warning: License plate model could not be loaded from {plate_model_path}: {e}")
            self.model_loaded = False
        
        # Initialize EasyOCR reader
        # gpu=True if you have a CUDA-enabled GPU
        self.reader = easyocr.Reader(['en'], gpu=False)
        
        # Cache for plate numbers to avoid flickering {track_id: "PLATE"}
        self.plate_cache = {}

    def detect_and_read(self, vehicle_frame, track_id):
        """
        Detect license plate within a vehicle crop and read the text.
        :param vehicle_frame: Cropped image of the vehicle.
        :param track_id: Tracking ID of the vehicle.
        :return: String representing the license plate text.
        """
        if track_id in self.plate_cache and self.plate_cache[track_id] != "Unknown":
            return self.plate_cache[track_id]

        if not self.model_loaded:
            return "N/A"

        # Detect license plates in the vehicle crop
        results = self.plate_model(vehicle_frame, verbose=False)
        
        best_plate_text = "Unknown"
        
        for result in results:
            boxes = result.boxes.xyxy.cpu().numpy()
            for box in boxes:
                x1, y1, x2, y2 = map(int, box)
                # Crop the license plate
                plate_crop = vehicle_frame[y1:y2, x1:x2]
                
                if plate_crop.size == 0:
                    continue
                
                # Perform OCR
                ocr_results = self.reader.readtext(plate_crop)
                
                if ocr_results:
                    # Sort results by confidence and pick the best one
                    # Result format: ([[x,y],...], text, confidence)
                    text = ocr_results[0][1]
                    confidence = ocr_results[0][2]
                    
                    if confidence > 0.4:
                        best_plate_text = text.upper().replace(" ", "")
                        break
        
        # Cache the result if we found something
        if best_plate_text != "Unknown":
            self.plate_cache[track_id] = best_plate_text
            
        return best_plate_text
