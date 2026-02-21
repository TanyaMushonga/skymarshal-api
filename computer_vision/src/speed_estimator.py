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
            # Tuned for more stability in the downward-facing highway angle
            self.source_points = np.float32([
                [450, 450], [850, 450], 
                [1280, 720], [0, 720]
            ])
        else:
            self.source_points = np.float32(source_points)

        # ROI length (meters) - increased for better perspective stretch
        self.target_points = np.float32([
            [0, 0], [12, 0], 
            [12, real_length + 20], [0, real_length + 20]
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
        ground_pos = self.get_real_world_pos(current_pos)
        
        if track_id not in self.tracker_data:
            self.tracker_data[track_id] = {
                'last_frame': current_frame,
                'last_pos': ground_pos,
                'speed_history': [],
                'current_speed': 0,
                'stable_frames': 0,
                'hits': 0
            }
            return 0
        
        data = self.tracker_data[track_id]
        frames_elapsed = current_frame - data['last_frame']
        
        # Only calculate if at least one frame has passed
        if frames_elapsed <= 0:
            return data['current_speed']
            
        # Calculate instantaneous distance and time
        dist = np.linalg.norm(ground_pos - data['last_pos'])
        time_elapsed = frames_elapsed / fps
        
        # Calculate speed in km/h
        speed_ms = dist / time_elapsed
        inst_speed_kmh = speed_ms * 3.6
        
        # Sanity check: ignore unrealistic jumps (e.g. > 200 km/h)
        if 5 < inst_speed_kmh < 220:
            data['speed_history'].append(inst_speed_kmh)
            if len(data['speed_history']) > 25: # Increased window from 10 to 25 for better smoothing
                data['speed_history'].pop(0)
            
            # Use median filtering to remove outliers then average
            sorted_history = sorted(data['speed_history'])
            mid = len(sorted_history) // 2
            avg_speed = sum(sorted_history[mid-5:mid+5]) / 10 if len(sorted_history) > 15 else sum(sorted_history) / len(sorted_history)
            
            # Clamp to a realistic highway maximum for display
            data['current_speed'] = min(round(avg_speed, 1), 160.0)
            data['stable_frames'] += frames_elapsed
            data['hits'] += 1
        
        # Update last position and frame
        data['last_pos'] = ground_pos
        data['last_frame'] = current_frame
        
        # Only show speed after a short grace period to allow for stabilization
        # Only show speed after a short grace period and enough hits for stabilization
        if data['stable_frames'] < 15 or data['hits'] < 8:
            return 0
            
        return data['current_speed']
