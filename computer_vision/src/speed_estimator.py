import cv2
import numpy as np

class SpeedEstimator:
    def __init__(self, source_points=None, real_length=30.0):
        """
        Initialize the Speed Estimator with perspective mapping.
        :param source_points: 4 points in the image [x, y] representing a ground rectangle.
        :param real_length: The real-world length of the ROI in meters.
        """
        # Default source points for a generic traffic perspective
        # These are [top-left, top-right, bottom-right, bottom-left]
        if source_points is None:
            self.source_points = np.float32([
                [500, 400], [800, 400], 
                [1100, 700], [200, 700]
            ])
        else:
            self.source_points = np.float32(source_points)

        # Mapping to a bird's-eye view rectangle (meters representation)
        # Width doesn't strictly matter for speed if we only move along length, 
        # but let's define a 10m x real_length rectangle.
        self.target_points = np.float32([
            [0, 0], [10, 0], 
            [10, real_length], [0, real_length]
        ])

        # Calculate Transformation Matrix
        self.M = cv2.getPerspectiveTransform(self.source_points, self.target_points)
        
        # Track entry/exit data: {track_id: {'start_frame': N, 'start_pos': (x,y), 'speed': S}}
        self.tracker_data = {}

    def get_real_world_pos(self, point):
        """
        Transform image coordinates to bird's-eye view coordinates (meters).
        """
        point_arr = np.array([[[point[0], point[1]]]], dtype=np.float32)
        transformed = cv2.perspectiveTransform(point_arr, self.M)
        return transformed[0][0]

    def estimate_speed(self, track_id, current_pos, current_frame, fps):
        """
        Calculate speed based on distance traveled in the warped perspective.
        """
        # Get ground coordinates
        ground_pos = self.get_real_world_pos(current_pos)

        if track_id not in self.tracker_data:
            self.tracker_data[track_id] = {
                'start_frame': current_frame,
                'start_pos': ground_pos,
                'current_speed': 0
            }
            return 0

        data = self.tracker_data[track_id]
        
        # Calculate displacement in meters
        dist = np.linalg.norm(ground_pos - data['start_pos'])
        
        # Calculate time elapsed
        frames_elapsed = current_frame - data['start_frame']
        if frames_elapsed <= 0:
            return data['current_speed']

        time_elapsed = frames_elapsed / fps # seconds
        
        # Speed = Distance / Time (m/s)
        speed_ms = dist / time_elapsed
        
        # Convert to km/h
        speed_kmh = speed_ms * 3.6
        
        # Update speed (could use moving average here, but keeping it simple)
        self.tracker_data[track_id]['current_speed'] = round(speed_kmh, 2)
        
        return self.tracker_data[track_id]['current_speed']
