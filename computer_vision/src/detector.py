import cv2
import torch
from ultralytics import YOLO

# Allow YOLO models to be unpickled in PyTorch 2.6+
torch.serialization.add_safe_globals([
    'ultralytics.nn.tasks.DetectionModel',
    'ultralytics.nn.tasks.DetectionModel' # Duplicate if needed or add more specific ones if found
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
        self.model = YOLO(model_name)
        # COCO class IDs for vehicles: 2: car, 3: motorcycle, 5: bus, 7: truck
        self.vehicle_classes = [2, 3, 5, 7]

    def detect_vehicles(self, frame):
        """
        Detect and track vehicles in a single frame.
        :param frame: The input frame (numpy array).
        :return: Results object containing detections and tracking IDs.
        """
        # Run tracking on the frame, filtering for vehicle classes
        # persist=True ensures IDs are maintained across frames
        # tracker='botsort.yaml' is the default and good for occlusion
        results = self.model.track(
            frame, 
            classes=self.vehicle_classes, 
            persist=True, 
            verbose=False,
            tracker="botsort.yaml"
        )
        return results
