import numpy as np
import cv2
from dataclasses import dataclass
from typing import List, Dict, Tuple
import math

@dataclass
class Position:
    x: float
    y: float
    theta: float  # orientation in radians

@dataclass
class Room:
    id: str
    features: np.ndarray  # Feature descriptors for room recognition
    position: Position    # Known position in global map
    
class RobotNavigator:
    def __init__(self, initial_position: Position):
        self.current_position = initial_position
        self.known_rooms: Dict[str, Room] = {}
        self.movement_history: List[Position] = [initial_position]
        
        # Feature detection and matching
        self.feature_detector = cv2.SIFT_create()
        self.feature_matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=True)
        
    def register_room(self, room_id: str, depth_image: np.ndarray, position: Position):
        """Register a new room with its features and known position"""
        # Extract features from depth image
        keypoints, descriptors = self.feature_detector.detectAndCompute(depth_image, None)
        
        # Create and store room
        room = Room(
            id=room_id,
            features=descriptors,
            position=position
        )
        self.known_rooms[room_id] = room
        
    def recognize_room(self, depth_image: np.ndarray) -> Tuple[str, float]:
        """Try to recognize current room from depth image"""
        # Get features of current view
        _, current_descriptors = self.feature_detector.detectAndCompute(depth_image, None)
        
        best_match = None
        best_score = 0.0
        
        # Compare with known rooms
        for room_id, room in self.known_rooms.items():
            matches = self.feature_matcher.match(current_descriptors, room.features)
            score = len(matches) / max(len(current_descriptors), len(room.features))
            
            if score > best_score:
                best_score = score
                best_match = room_id
                
        return best_match, best_score
    
    def plan_trajectory(self, target_position: Position) -> List[Position]:
        """Plan trajectory from current position to target"""
        # Simplified A* planning - in reality would need more complex planning
        # considering obstacles and robot constraints
        
        start = (self.current_position.x, self.current_position.y)
        goal = (target_position.x, target_position.y)
        
        # Create waypoints (simplified)
        distance = math.sqrt((goal[0] - start[0])**2 + (goal[1] - start[1])**2)
        num_waypoints = max(2, int(distance / 0.5))  # One waypoint every 0.5 meters
        
        waypoints = []
        for i in range(num_waypoints + 1):
            t = i / num_waypoints
            x = start[0] + t * (goal[0] - start[0])
            y = start[1] + t * (goal[1] - start[1])
            theta = math.atan2(goal[1] - start[1], goal[0] - start[0])
            waypoints.append(Position(x, y, theta))
            
        return waypoints
    
    def execute_trajectory(self, trajectory: List[Position], depth_sensor_callback):
        """Execute planned trajectory while monitoring position"""
        for target in trajectory:
            while not self._at_position(target):
                # Get latest depth frame
                depth_frame = depth_sensor_callback()
                
                # Check for obstacles
                if self._check_obstacles(depth_frame):
                    print("Obstacle detected, replanning...")
                    new_trajectory = self.plan_trajectory(trajectory[-1])
                    return self.execute_trajectory(new_trajectory, depth_sensor_callback)
                
                # Move towards target
                self._move_towards(target)
                
                # Update position history
                self.movement_history.append(self.current_position)
    
    def _at_position(self, target: Position, tolerance: float = 0.1) -> bool:
        """Check if robot is at target position within tolerance"""
        distance = math.sqrt(
            (target.x - self.current_position.x)**2 + 
            (target.y - self.current_position.y)**2
        )
        return distance < tolerance
    
    def _check_obstacles(self, depth_frame: np.ndarray) -> bool:
        """Check for obstacles in depth frame"""
        # Simplified obstacle detection
        min_distance = np.min(depth_frame[depth_frame > 0])
        return min_distance < 0.5  # 0.5 meters minimum clearance
    
    def _move_towards(self, target: Position):
        """Update robot position moving towards target"""
        # In real implementation, this would interface with robot's motors
        # This is simplified movement
        speed = 0.1  # meters per update
        dx = target.x - self.current_position.x
        dy = target.y - self.current_position.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance > speed:
            # Move in direction of target
            ratio = speed / distance
            self.current_position.x += dx * ratio
            self.current_position.y += dy * ratio
            
        # Update orientation
        self.current_position.theta = math.atan2(dy, dx)

# Example usage
def main():
    # Initialize robot at starting position
    start_pos = Position(0, 0, 0)
    robot = RobotNavigator(start_pos)
    
    # Register known rooms (would be done during setup/mapping phase)
    def mock_depth_sensor():
        # Mock depth sensor data
        return np.random.rand(480, 640)
    
    robot.register_room(
        "Room A", 
        mock_depth_sensor(), 
        Position(5, 5, 0)
    )
    
    # Main operation loop
    def run_navigation():
        while True:
            # Get depth frame
            depth_frame = mock_depth_sensor()
            
            # Try to recognize room
            room_id, confidence = robot.recognize_room(depth_frame)
            
            if confidence > 0.8:  # High confidence match
                print(f"Recognized {room_id}")
                target_position = robot.known_rooms[room_id].position
                
                # Plan and execute trajectory
                trajectory = robot.plan_trajectory(target_position)
                robot.execute_trajectory(trajectory, mock_depth_sensor)
                
                print(f"Arrived at {room_id}")
                
    return robot

if __name__ == "__main__":
    main()