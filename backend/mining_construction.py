import numpy as np
import matplotlib.pyplot as plt
import time
import threading
import json
from datetime import datetime
from collections import deque
import logging

class MiningConstructionMonitor:
    
    def __init__(self):
        self.slope_monitoring_points = {}
        self.vehicle_positions = {}
        self.collision_alerts = deque(maxlen=100)
        self.slope_history = deque(maxlen=1000)
        self.logger = logging.getLogger('MiningMonitor')
        self.monitoring = False
        self.monitor_thread = None
        self.callback = None
        
    def set_callback(self, callback):
        self.callback = callback
        
    def add_monitoring_point(self, point_id, x, y, z=0, threshold=0.05):
        """Add a slope monitoring point"""
        self.slope_monitoring_points[point_id] = {
            'id': point_id,
            'x': x,
            'y': y,
            'z': z,
            'threshold': threshold,
            'displacement_history': deque(maxlen=100),
            'current_displacement': 0.0,
            'last_update': None
        }
        self.logger.info(f"Added monitoring point {point_id} at ({x}, {y}, {z})")
    
    def update_displacement(self, point_id, displacement):
        if point_id not in self.slope_monitoring_points:
            self.logger.error(f"Monitoring point {point_id} not found")
            return
        
        point = self.slope_monitoring_points[point_id]
        point['displacement_history'].append(displacement)
        point['current_displacement'] = displacement
        point['last_update'] = datetime.now()
        
        # Check threshold
        if abs(displacement) > point['threshold']:
            self._log_slope_alert(point_id, displacement)
    
    def monitor_slope_stability(self):
        results = {}
        
        for point_id, point in self.slope_monitoring_points.items():
            history = list(point['displacement_history'])
            
            if len(history) < 5:
                results[point_id] = {
                    'status': 'insufficient_data', 
                    'trend': 0,
                    'current_displacement': point['current_displacement']
                }
                continue
            
            # Calculate displacement rate
            x = np.array(range(len(history[-10:])))
            y = np.array(history[-10:])
            
            if len(x) > 1:
                slope, intercept = np.polyfit(x, y, 1)
                displacement_rate = float(slope * 24)  # per day
            else:
                displacement_rate = 0
            
            # Determine stability status
            current = abs(point['current_displacement'])
            threshold = point['threshold']
            
            if current > threshold * 1.5:
                status = 'critical'
                alert_level = 'red'
            elif current > threshold:
                status = 'warning'
                alert_level = 'yellow'
            elif displacement_rate > threshold / 24:
                status = 'trending_warning'
                alert_level = 'orange'
            else:
                status = 'stable'
                alert_level = 'green'
            
            results[point_id] = {
                'status': status,
                'alert_level': alert_level,
                'current_displacement': float(current),
                'displacement_rate': float(displacement_rate),
                'threshold': float(threshold)
            }
            
            # Log if warning or critical
            if status in ['warning', 'critical']:
                self._log_slope_alert(point_id, current, status)
        
        return results
    
    def _log_slope_alert(self, point_id, displacement, status='warning'):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert = {
            'timestamp': timestamp,
            'point_id': point_id,
            'displacement': displacement,
            'status': status,
            'type': 'slope_stability'
        }
        
        self.collision_alerts.append(alert)
        
        if self.callback:
            self.callback({'type': 'alert', 'data': alert})
        
        self.logger.warning(f"Slope alert at point {point_id}: {displacement:.3f}m - {status}")
    
    def update_vehicle_position(self, vehicle_id, x, y, vx=0, vy=0):
        current_time = time.time()
        
        if vehicle_id not in self.vehicle_positions:
            self.vehicle_positions[vehicle_id] = {
                'id': vehicle_id,
                'x': x,
                'y': y,
                'vx': vx,
                'vy': vy,
                'last_update': current_time,
                'path': deque(maxlen=100)
            }
        else:
            vehicle = self.vehicle_positions[vehicle_id]
            dt = current_time - vehicle['last_update']
            
            # Calculate velocity if not provided
            if vx == 0 and vy == 0 and dt > 0:
                vehicle['vx'] = (x - vehicle['x']) / dt
                vehicle['vy'] = (y - vehicle['y']) / dt
            else:
                vehicle['vx'] = vx
                vehicle['vy'] = vy
            
            # Store position in path
            vehicle['path'].append((vehicle['x'], vehicle['y']))
            
            # Update current position
            vehicle['x'] = x
            vehicle['y'] = y
            vehicle['last_update'] = current_time
    
    def check_collisions(self, safe_distance=10):
        """
        Check for potential collisions between vehicles
        """
        collisions = []
        vehicles = list(self.vehicle_positions.values())
        
        for i in range(len(vehicles)):
            for j in range(i+1, len(vehicles)):
                v1 = vehicles[i]
                v2 = vehicles[j]
                
                # Current distance
                dx = v1['x'] - v2['x']
                dy = v1['y'] - v2['y']
                distance = np.sqrt(dx**2 + dy**2)
                
                if distance < safe_distance:
                    # Immediate collision risk
                    severity = 'immediate'
                    action = 'emergency_stop'
                    
                    collision = {
                        'vehicles': [v1['id'], v2['id']],
                        'distance': float(distance),
                        'time_to_collision': 0,
                        'severity': severity,
                        'action': action
                    }
                    collisions.append(collision)
                    self._log_collision_alert(v1['id'], v2['id'], distance, severity)
        
        return collisions
    
    def _log_collision_alert(self, v1_id, v2_id, distance, severity):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        alert = {
            'timestamp': timestamp,
            'vehicles': [v1_id, v2_id],
            'distance': float(distance),
            'severity': severity,
            'type': 'collision'
        }
        
        self.collision_alerts.append(alert)
        
        if self.callback:
            self.callback({'type': 'collision_alert', 'data': alert})
        
        self.logger.critical(f"COLLISION: {v1_id} and {v2_id} - {distance:.1f}m")
    
    def start_monitoring(self, interval=1.0):
        if self.monitoring:
            return
            
        self.monitoring = True
        
        def monitor_loop():
            while self.monitoring:
                try:
                    # Check slope stability
                    slope_status = self.monitor_slope_stability()
                    
                    # Check collisions
                    collisions = self.check_collisions()
                    
                    # Send status update
                    if self.callback:
                        status = {
                            'type': 'site_status',
                            'slope_status': slope_status,
                            'collisions': collisions,
                            'active_vehicles': len(self.vehicle_positions),
                            'monitoring_points': len(self.slope_monitoring_points),
                            'timestamp': datetime.now().isoformat()
                        }
                        self.callback(status)
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Monitoring loop error: {e}")
                    time.sleep(1)
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
        self.logger.info("Site monitoring started")
    
    def stop_monitoring(self):
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self.logger.info("Site monitoring stopped")
    
    def get_site_status(self):
        return {
            'timestamp': datetime.now().isoformat(),
            'slope_monitoring': self.monitor_slope_stability(),
            'collision_risks': self.check_collisions(),
            'active_vehicles': len(self.vehicle_positions),
            'monitoring_points': len(self.slope_monitoring_points),
            'recent_alerts': list(self.collision_alerts)[-10:]
        }
    
    def get_vehicle_positions(self):
        positions = {}
        for vid, vehicle in self.vehicle_positions.items():
            positions[vid] = {
                'x': vehicle['x'],
                'y': vehicle['y'],
                'vx': vehicle['vx'],
                'vy': vehicle['vy']
            }
        return positions
    
    def get_slope_data(self):
        data = {}
        for point_id, point in self.slope_monitoring_points.items():
            data[point_id] = {
                'current_displacement': point['current_displacement'],
                'threshold': point['threshold'],
                'history': list(point['displacement_history'])[-20:]
            }
        return data
    
    def export_site_data(self, filename='site_data.json'):
        """Export site monitoring data to JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'slope_points': {},
            'vehicles': {},
            'alerts': list(self.collision_alerts)
        }
        
        for pid, point in self.slope_monitoring_points.items():
            data['slope_points'][pid] = {
                'x': point['x'],
                'y': point['y'],
                'z': point['z'],
                'threshold': point['threshold'],
                'current_displacement': point['current_displacement'],
                'history': list(point['displacement_history'])
            }
        
        for vid, vehicle in self.vehicle_positions.items():
            data['vehicles'][vid] = {
                'x': vehicle['x'],
                'y': vehicle['y'],
                'vx': vehicle['vx'],
                'vy': vehicle['vy'],
                'path': list(vehicle['path'])
            }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Site data exported to {filename}")
