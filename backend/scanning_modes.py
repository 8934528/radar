import numpy as np
import matplotlib.pyplot as plt
import time
import threading
from collections import deque
import logging
import math

class ScanningMode:
    
    def __init__(self, azimuth_range=360, elevation_range=30, scan_speed=45):
        self.azimuth_range = azimuth_range
        self.elevation_range = elevation_range
        self.scan_speed = scan_speed
        self.current_azimuth = 0
        self.current_elevation = 0
        self.is_scanning = False
        self.scan_data = deque(maxlen=1000)
        self.scan_mode = 'circular'  # circular, sector, tracking
        self.sector_start = 0
        self.sector_end = 360
        self.sector_direction = 1
        self.logger = logging.getLogger('ScanningMode')
        self.callback = None
        self.scan_thread = None
        
    def set_callback(self, callback):
        self.callback = callback
        
    def start_sector_scan(self, start_angle, end_angle, elevation=0):
        self.stop_scan()
        self.scan_mode = 'sector'
        self.sector_start = start_angle
        self.sector_end = end_angle
        self.current_azimuth = start_angle
        self.current_elevation = elevation
        self.sector_direction = 1 if end_angle > start_angle else -1
        self.is_scanning = True
        
        self.scan_thread = threading.Thread(target=self._sector_scan_loop, daemon=True)
        self.scan_thread.start()
        self.logger.info(f"Sector scan started: {start_angle}° to {end_angle}°")
        return self.scan_thread
    
    def _sector_scan_loop(self):
        while self.is_scanning:
            try:
                # Update position
                self.current_azimuth += self.sector_direction * self.scan_speed * 0.05
                
                # Check boundaries
                if self.sector_direction > 0 and self.current_azimuth >= self.sector_end:
                    self.current_azimuth = self.sector_end
                    self.sector_direction = -1
                elif self.sector_direction < 0 and self.current_azimuth <= self.sector_start:
                    self.current_azimuth = self.sector_start
                    self.sector_direction = 1
                
                # Store scan position
                self.scan_data.append({
                    'timestamp': time.time(),
                    'azimuth': self.current_azimuth,
                    'elevation': self.current_elevation,
                    'mode': 'sector'
                })
                
                # Call callback with position update
                if self.callback:
                    self.callback({
                        'type': 'position_update',
                        'azimuth': self.current_azimuth,
                        'elevation': self.current_elevation,
                        'mode': 'sector'
                    })
                
                time.sleep(0.05)  # 20Hz update rate
                
            except Exception as e:
                self.logger.error(f"Error in sector scan loop: {e}")
                time.sleep(0.1)
    
    def start_circular_scan(self, elevation=0):
        self.stop_scan()
        self.scan_mode = 'circular'
        self.current_azimuth = 0
        self.current_elevation = elevation
        self.is_scanning = True
        
        self.scan_thread = threading.Thread(target=self._circular_scan_loop, daemon=True)
        self.scan_thread.start()
        self.logger.info("Circular scan started")
        return self.scan_thread
    
    def _circular_scan_loop(self):
        while self.is_scanning:
            try:
                # Update position
                self.current_azimuth += self.scan_speed * 0.05
                
                if self.current_azimuth >= 360:
                    self.current_azimuth -= 360
                
                # Store scan position
                self.scan_data.append({
                    'timestamp': time.time(),
                    'azimuth': self.current_azimuth,
                    'elevation': self.current_elevation,
                    'mode': 'circular'
                })
                
                # Call callback with position update
                if self.callback:
                    self.callback({
                        'type': 'position_update',
                        'azimuth': self.current_azimuth,
                        'elevation': self.current_elevation,
                        'mode': 'circular'
                    })
                
                time.sleep(0.05)  # 20Hz update rate
                
            except Exception as e:
                self.logger.error(f"Error in circular scan loop: {e}")
                time.sleep(0.1)
    
    def start_tracking_scan(self, target_angle=None):
        """
        Start tracking scan 
        """
        self.stop_scan()
        self.scan_mode = 'tracking'
        if target_angle is not None:
            self.current_azimuth = target_angle
        self.is_scanning = True
        
        self.scan_thread = threading.Thread(target=self._tracking_scan_loop, daemon=True)
        self.scan_thread.start()
        self.logger.info(f"Tracking scan started at {self.current_azimuth}°")
        return self.scan_thread
    
    def _tracking_scan_loop(self):
        while self.is_scanning:
            try:
                # Store scan position (stationary)
                self.scan_data.append({
                    'timestamp': time.time(),
                    'azimuth': self.current_azimuth,
                    'elevation': self.current_elevation,
                    'mode': 'tracking'
                })
                
                # Call callback with position update
                if self.callback:
                    self.callback({
                        'type': 'position_update',
                        'azimuth': self.current_azimuth,
                        'elevation': self.current_elevation,
                        'mode': 'tracking'
                    })
                
                time.sleep(0.1)  # 10Hz update rate
                
            except Exception as e:
                self.logger.error(f"Error in tracking scan loop: {e}")
                time.sleep(0.1)
    
    def stop_scan(self):
        self.is_scanning = False
        if self.scan_thread and self.scan_thread.is_alive():
            self.scan_thread.join(timeout=1)
        self.logger.info("Scan stopped")
    
    def set_scan_speed(self, speed):
        """Set scan speed in degrees per second"""
        self.scan_speed = max(10, min(90, speed))  # Limit between 10-90 deg/s
        self.logger.info(f"Scan speed set to {self.scan_speed}°/s")
    
    def get_current_position(self):
        return {
            'azimuth': self.current_azimuth,
            'elevation': self.current_elevation,
            'mode': self.scan_mode,
            'speed': self.scan_speed
        }
    
    def get_scan_data(self):
        return list(self.scan_data)
    
    def get_scan_status(self):
        return {
            'is_scanning': self.is_scanning,
            'mode': self.scan_mode,
            'current_azimuth': self.current_azimuth,
            'current_elevation': self.current_elevation,
            'scan_speed': self.scan_speed,
            'data_points': len(self.scan_data)
        }
    
    def plot_scan_map(self):
        if not self.scan_data:
            print("No scan data available")
            return
        
        # Extract data
        angles = [d['azimuth'] for d in self.scan_data]
        
        # Create polar plot
        plt.figure(figsize=(10, 8))
        ax = plt.subplot(111, projection='polar')
        
        # Plot scan positions
        angles_rad = np.deg2rad(angles)
        ax.scatter(angles_rad, [1] * len(angles), c='green', 
                  s=10, alpha=0.6, marker='.')
        
        ax.set_theta_zero_location('N')
        ax.set_theta_direction(-1)
        ax.set_title(f'Radar Scan Pattern - {self.scan_mode.upper()} Mode')
        ax.set_rmax(1.2)
        ax.set_rticks([])  # Hide radial ticks
        
        plt.tight_layout()
        plt.show()
