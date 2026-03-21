import numpy as np
import matplotlib.pyplot as plt
import time
import threading
from collections import deque
import logging

class ADASSystem:
    
    def __init__(self, radar=None):
        """
        Initialize ADAS system
        """
        self.radar = radar
        self.cruise_speed = 0
        self.follow_distance = 30  # meters
        self.warning_active = False
        self.tracked_vehicles = {}
        self.alert_history = deque(maxlen=100)
        self.logger = logging.getLogger('ADAS')
        self.monitoring = False
        self.monitor_thread = None
        
    def start_monitoring(self, interval=0.1):
        """Start continuous monitoring of surroundings"""
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_loop, args=(interval,))
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        self.logger.info("ADAS monitoring started")
    
    def _monitor_loop(self, interval):
        """Continuous monitoring loop"""
        while self.monitoring:
            # Simulate radar detection
            detections = self._simulate_detections()
            
            # Process detections
            self.process_vehicles(detections)
            
            # Check safety conditions
            self.check_collision_risk()
            self.check_blind_spots()
            
            time.sleep(interval)
    
    def _simulate_detections(self):
        """Simulate radar detections for testing"""
        # In real system, this would come from radar hardware
        import random
        
        detections = []
        
        # Simulate leading vehicle
        if random.random() > 0.1:
            detections.append({
                'range': random.uniform(20, 80),
                'velocity': random.uniform(-5, 5),
                'angle': random.uniform(-10, 10),
                'type': 'vehicle'
            })
        
        # Simulate vehicles in adjacent lanes
        for side in [-1, 1]:
            if random.random() > 0.3:
                detections.append({
                    'range': random.uniform(10, 50),
                    'velocity': random.uniform(-2, 8),
                    'angle': random.uniform(15 + side*10, 45 + side*10),
                    'type': 'vehicle'
                })
        
        return detections
    
    def process_vehicles(self, detections):
        """Process detected vehicles and update tracks"""
        current_time = time.time()
        
        for det in detections:
            # Simple tracking by range and angle
            vehicle_id = f"v{int(det['range'])}{int(det['angle'])}"
            
            if vehicle_id not in self.tracked_vehicles:
                self.tracked_vehicles[vehicle_id] = {
                    'first_seen': current_time,
                    'last_seen': current_time,
                    'range': det['range'],
                    'velocity': det['velocity'],
                    'angle': det['angle']
                }
            else:
                # Update track
                prev = self.tracked_vehicles[vehicle_id]
                dt = current_time - prev['last_seen']
                
                # Smooth with Kalman-like filter
                alpha = 0.7  # Measurement weight
                prev['range'] = alpha * det['range'] + (1-alpha) * prev['range']
                prev['velocity'] = alpha * det['velocity'] + (1-alpha) * prev['velocity']
                prev['angle'] = alpha * det['angle'] + (1-alpha) * prev['angle']
                prev['last_seen'] = current_time
        
        # Remove old tracks
        timeout = 2.0  # seconds
        expired = [vid for vid, track in self.tracked_vehicles.items() 
                  if current_time - track['last_seen'] > timeout]
        for vid in expired:
            del self.tracked_vehicles[vid]
    
    def adaptive_cruise_control(self, current_speed, set_speed):
        """
        Adaptive cruise control with real-time adjustment
        """
        # Find closest vehicle in same lane
        lead_vehicle = None
        min_range = float('inf')
        
        for vid, vehicle in self.tracked_vehicles.items():
            if abs(vehicle['angle']) < 5:  # Same lane
                if vehicle['range'] < min_range:
                    min_range = vehicle['range']
                    lead_vehicle = vehicle
        
        if lead_vehicle:
            distance = lead_vehicle['range']
            relative_velocity = current_speed/3.6 - lead_vehicle['velocity']
            
            # Time to collision
            if relative_velocity > 0:
                ttc = distance / relative_velocity
            else:
                ttc = float('inf')
            
            # Adjust speed based on distance
            safe_distance = self.follow_distance + 0.5 * current_speed/3.6
            
            if distance < safe_distance * 0.5:
                # Emergency: brake hard
                new_speed = max(0, current_speed - 20)
                self._log_alert(f"Emergency braking! Distance: {distance:.1f}m")
                return new_speed, "EMERGENCY"
            
            elif distance < safe_distance:
                # Adjust speed to maintain distance
                speed_adjustment = (distance / safe_distance) * set_speed
                new_speed = max(0, min(set_speed, speed_adjustment))
                self._log_alert(f"Adjusting speed to {new_speed:.0f} km/h")
                return new_speed, "ADJUSTING"
            
            else:
                # Accelerate to set speed
                new_speed = min(set_speed, current_speed + 5)
                return new_speed, "ACCELERATING"
        
        # No lead vehicle, maintain set speed
        new_speed = min(set_speed, current_speed + 5)
        return new_speed, "CRUISING"
    
    def automatic_emergency_braking(self, speed):
        """
        Automatic emergency braking system
        """
        speed_ms = speed / 3.6
        
        # Find all obstacles
        for vid, vehicle in self.tracked_vehicles.items():
            distance = vehicle['range']
            relative_velocity = speed_ms - vehicle['velocity']
            
            # Calculate stopping distance
            deceleration = 9.8  # m/s^2
            stopping_distance = (speed_ms ** 2) / (2 * deceleration)
            
            if relative_velocity > 0 and distance < stopping_distance:
                self._log_alert(f"AEB ACTIVATED! Distance: {distance:.1f}m, "
                              f"Speed: {speed} km/h")
                return True, "BRAKE"
        
        return False, "NORMAL"
    
    def blind_spot_detection(self):
        """
        Detect vehicles in blind spots
        """
        warnings = []
        
        for vid, vehicle in self.tracked_vehicles.items():
            angle = vehicle['angle']
            distance = vehicle['range']
            
            # Blind spot zones
            if (20 < angle < 45 or -45 < angle < -20) and distance < 15:
                side = "LEFT" if angle < 0 else "RIGHT"
                warnings.append({
                    'side': side,
                    'distance': distance,
                    'angle': angle
                })
                self._log_alert(f"Vehicle in {side} blind spot at {distance:.1f}m")
        
        return warnings
    
    def check_collision_risk(self):
        """
        Check for potential collisions with all vehicles
        """
        for vid, vehicle in self.tracked_vehicles.items():
            distance = vehicle['range']
            angle = abs(vehicle['angle'])
            
            # Risk increases for vehicles in path
            risk_factor = 1.0 if angle < 10 else max(0, 1 - angle/90)
            
            if distance < 20 and risk_factor > 0.5:
                self._log_alert(f"Collision risk: {distance:.1f}m, angle: {angle:.1f}°")
                return True
        
        return False
    
    def check_blind_spots(self):
        """Check and log blind spot alerts"""
        warnings = self.blind_spot_detection()
        if warnings:
            for warning in warnings:
                print(f"⚠️ {warning['side']} blind spot alert - "
                      f"Vehicle at {warning['distance']:.1f}m")
    
    def _log_alert(self, message):
        """Log alert with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        alert = f"[{timestamp}] {message}"
        self.alert_history.append(alert)
        self.logger.warning(message)
    
    def get_tracked_vehicles(self):
        """Return currently tracked vehicles"""
        return self.tracked_vehicles
    
    def get_alerts(self):
        """Return recent alerts"""
        return list(self.alert_history)
    
    def visualize_scenario(self, ego_speed):
        """
        Visualize current ADAS scenario
        """
        plt.figure(figsize=(12, 8))
        
        # Plot ego vehicle
        ax = plt.subplot(111)
        ax.scatter(0, 0, s=200, c='blue', marker='s', label='Ego Vehicle', zorder=5)
        
        # Plot tracked vehicles
        for vid, vehicle in self.tracked_vehicles.items():
            # Convert angle to x,y
            angle_rad = np.deg2rad(vehicle['angle'])
            x = vehicle['range'] * np.sin(angle_rad)
            y = vehicle['range'] * np.cos(angle_rad)
            
            # Color based on risk
            if abs(vehicle['angle']) < 15 and vehicle['range'] < 30:
                color = 'red'
                size = 150
            elif 15 < abs(vehicle['angle']) < 45 and vehicle['range'] < 20:
                color = 'orange'
                size = 100
            else:
                color = 'gray'
                size = 80
            
            ax.scatter(x, y, s=size, c=color, marker='s', alpha=0.7)
            ax.text(x, y+2, f"{vehicle['range']:.0f}m", ha='center', fontsize=8)
        
        # Draw blind spot zones
        for angle in [30, 45]:
            theta = np.deg2rad(angle)
            x = [0, 20 * np.sin(theta)]
            y = [0, 20 * np.cos(theta)]
            ax.plot(x, y, 'k--', alpha=0.3)
            ax.plot(-np.array(x), y, 'k--', alpha=0.3)
        
        # Add text annotations
        ax.text(-5, -5, f"Speed: {ego_speed} km/h", fontsize=12, 
               bbox=dict(boxstyle="round", facecolor='white', alpha=0.8))
        
        ax.set_xlim(-40, 40)
        ax.set_ylim(-5, 80)
        ax.set_xlabel('Lateral Distance (m)')
        ax.set_ylabel('Longitudinal Distance (m)')
        ax.set_title('ADAS Scenario - Vehicle Detection')
        ax.grid(True, alpha=0.3)
        ax.legend()
        
        plt.tight_layout()
        plt.show()
    
    def stop_monitoring(self):
        """Stop ADAS monitoring"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        self.logger.info("ADAS monitoring stopped")
