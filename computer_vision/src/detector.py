import cv2
import torch
import logging
from ultralytics import YOLO

logger = logging.getLogger(__name__)

# Allow YOLO models to be unpickled in PyTorch 2.6+
torch.serialization.add_safe_globals([
    'ultralytics.nn.tasks.DetectionModel',
])

try:
    from ultralytics.nn.tasks import DetectionModel
    torch.serialization.add_safe_globals([DetectionModel])
except ImportError:
    pass

class VehicleDetector:
    def __init__(self, model_name='yolov8n.pt'):
        """
        Initialize the YOLOv8 model for vehicle detection.
        :param model_name: Name of the YOLOv8 model file.
        """
        try:
            self.model = YOLO(model_name)
            logger.info(f"Loaded detection model: {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise RuntimeError(f"Could not initialize VehicleDetector: {e}")
            
    
        self.vehicle_classes = [2, 3, 5, 7]

    def detect_vehicles(self, frame):

        results = self.model.track(
            frame, 
            classes=self.vehicle_classes, 
            persist=True, 
            verbose=False,
            tracker="botsort.yaml"
        )
        return results
