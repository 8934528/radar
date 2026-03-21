import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import json
import logging
import threading
import time
import math

class RadarSystem:
    
    def __init__(self, frequency=24e9, power=10, antenna_gain=20, noise_figure=5):
        self.frequency = frequency
        self.power = power
        self.antenna_gain = antenna_gain
        self.noise_figure = noise_figure
        self.wavelength = 3e8 / frequency
        self.detections = []
        self.active_targets = []
        self.target_tracks = {}
        self.target_counter = 0
        self.is_scanning = False
        self.scan_thread = None
        self.logger = self._setup_logger()
        
    def _setup_logger(self):
        logger = logging.getLogger('RadarSystem')
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        return logger
    
    def calculate_range(self, time_delay):
        """Calculate range from time delay (seconds to meters)"""
        return (3e8 * time_delay) / 2
    
    def calculate_time_delay(self, range_meters):
        """Calculate time delay from range (meters to seconds)"""
        return (2 * range_meters) / 3e8
    
    def calculate_doppler(self, velocity):
        """Calculate Doppler frequency shift from velocity (m/s to Hz)"""
        return (2 * velocity) / self.wavelength
    
    def calculate_velocity(self, doppler_shift):
        """Calculate velocity from Doppler shift (Hz to m/s)"""
        return (doppler_shift * self.wavelength) / 2
    
    def calculate_radar_range(self, target_rcs=1.0, snr_min=10):

        # Constants
        k = 1.38e-23  # Boltzmann constant
        T = 290  # Temperature in Kelvin
        B = 1e6  # Bandwidth in Hz (1 MHz typical)
        
        # Convert dB values to linear
        G_linear = 10**(self.antenna_gain/10)
        SNR_linear = 10**(snr_min/10)
        NF_linear = 10**(self.noise_figure/10)
        
        # Noise power
        noise_power = k * T * B * NF_linear
        
        # Radar range equation
        numerator = self.power * G_linear**2 * self.wavelength**2 * target_rcs
        denominator = (4*np.pi)**3 * noise_power * SNR_linear
        
        max_range = (numerator / denominator) ** 0.25
        
        return max_range
    
    def generate_synthetic_target(self, target_type='car'):
        rcs_values = {
            'car': 5.0,
            'pedestrian': 0.3,
            'truck': 20.0,
            'motorcycle': 1.0,
            'bicycle': 0.5
        }
        
        rcs = rcs_values.get(target_type, 5.0)
        max_range = self.calculate_radar_range(target_rcs=rcs)
        
        # Generate realistic target parameters
        target = {
            'id': f"TGT-{self.target_counter + 1}",
            'range': np.random.uniform(10, max_range * 0.8),
            'velocity': np.random.uniform(-20, 30),  # -20 to 30 m/s
            'rcs': rcs,
            'type': target_type,
            'angle': np.random.uniform(0, 360),
            'snr': np.random.uniform(15, 35),
            'confidence': np.random.uniform(0.6, 0.95)
        }
        
        # Calculate radar coordinates (x, y) from range and angle
        angle_rad = math.radians(target['angle'])
        # Scale range to pixels
        max_range_px = 320  # Canvas radius
        scale_factor = max_range_px / max_range
        target['x'] = 350 + target['range'] * scale_factor * math.cos(angle_rad)
        target['y'] = 350 + target['range'] * scale_factor * math.sin(angle_rad)
        
        return target
    
    def simulate_target_detection(self, targets=None):
        """
        Simulate detection of multiple targets
        targets: list of dict with 'range', 'velocity', 'rcs' keys
        """
        if targets is None:
            # Generate random number of targets (0-4)
            num_targets = np.random.randint(0, 5)
            targets = []
            target_types = ['car', 'pedestrian', 'truck', 'motorcycle']
            for _ in range(num_targets):
                target_type = np.random.choice(target_types)
                targets.append(self.generate_synthetic_target(target_type))
        
        detections = []
        max_range = self.calculate_radar_range()
        
        for target in targets:
            range_m = target.get('range', 0)
            if range_m > max_range:
                continue
                
            # Add noise to measurements
            snr_db = target.get('snr', 20) + np.random.normal(0, 2)
            
            if snr_db > 10:  # 10 dB threshold
                # Calculate Doppler shift
                doppler = self.calculate_doppler(target.get('velocity', 0))
                
                detection = {
                    'id': target.get('id', f"TGT-{self.target_counter + 1}"),
                    'timestamp': datetime.now().isoformat(),
                    'range': range_m,
                    'velocity': target.get('velocity', 0),
                    'doppler': doppler,
                    'snr': snr_db,
                    'rcs': target.get('rcs', 1.0),
                    'type': target.get('type', 'unknown'),
                    'angle': target.get('angle', np.random.uniform(0, 360)),
                    'x': target.get('x', 350),
                    'y': target.get('y', 350),
                    'confidence': target.get('confidence', 0.8)
                }
                detections.append(detection)
                
                self.logger.debug(f"Target detected at {range_m:.1f}m, "
                                 f"velocity {target.get('velocity', 0):.1f}m/s, "
                                 f"SNR {snr_db:.1f}dB")
        
        # Update target counter for new unique targets
        for detection in detections:
            if detection['id'] not in [t.get('id') for t in self.active_targets]:
                self.target_counter += 1
                detection['id'] = f"TGT-{self.target_counter}"
        
        self.active_targets = detections
        self.detections.extend(detections)
        
        # Keep only last 100 detections
        if len(self.detections) > 100:
            self.detections = self.detections[-100:]
        
        return detections
    
    def track_targets(self, detections, time_step=0.5):

        tracked_targets = []
        
        for detection in detections:
            target_id = detection['id']
            
            if target_id in self.target_tracks:
                prev = self.target_tracks[target_id]
                # Simple prediction
                pred_range = prev['range'] + prev['velocity'] * time_step
                pred_x = prev['x'] + prev['velocity'] * math.cos(math.radians(prev['angle'])) * time_step
                pred_y = prev['y'] + prev['velocity'] * math.sin(math.radians(prev['angle'])) * time_step
                
                # Update with measurement 
                alpha = 0.7  # Weight for measurement
                beta = 0.3   # Weight for prediction
                
                tracked = {
                    'id': target_id,
                    'range': alpha * detection['range'] + beta * pred_range,
                    'velocity': detection['velocity'],
                    'x': alpha * detection['x'] + beta * pred_x,
                    'y': alpha * detection['y'] + beta * pred_y,
                    'angle': detection['angle'],
                    'type': detection.get('type', 'unknown'),
                    'confidence': detection['confidence'],
                    'snr': detection['snr']
                }
            else:
                tracked = {
                    'id': target_id,
                    'range': detection['range'],
                    'velocity': detection['velocity'],
                    'x': detection['x'],
                    'y': detection['y'],
                    'angle': detection['angle'],
                    'type': detection.get('type', 'unknown'),
                    'confidence': detection['confidence'],
                    'snr': detection['snr']
                }
            
            self.target_tracks[target_id] = tracked
            tracked_targets.append(tracked)
        
        # Remove old tracks (older than 5 seconds without update)
        current_time = time.time()
        stale_tracks = []
        for track_id, track in self.target_tracks.items():
            if track not in tracked_targets:
                # Mark for removal after 5 seconds
                if not hasattr(track, 'last_seen'):
                    track.last_seen = current_time
                elif current_time - track.last_seen > 5:
                    stale_tracks.append(track_id)
            else:
                track.last_seen = current_time
        
        for track_id in stale_tracks:
            del self.target_tracks[track_id]
        
        return tracked_targets
    
    def get_latest_detections(self):
        return {
            'targets': self.active_targets,
            'count': len(self.active_targets),
            'timestamp': datetime.now().isoformat()
        }
    
    def get_radar_cross_section(self, object_type):
        rcs_values = {
            'bicycle': 0.5,
            'car': 5.0,
            'truck': 20.0,
            'pedestrian': 0.3,
            'motorcycle': 1.0,
            'helicopter': 8.0,
            'drone': 0.01
        }
        return rcs_values.get(object_type, 1.0)
    
    def start_continuous_scan(self, callback=None, interval=0.5):
        if self.is_scanning:
            return
        
        self.is_scanning = True
        
        def scan_loop():
            while self.is_scanning:
                try:
                    # Simulate target detection
                    detections = self.simulate_target_detection()
                    tracked = self.track_targets(detections, interval)
                    
                    if callback:
                        callback(tracked)
                    
                    time.sleep(interval)
                except Exception as e:
                    self.logger.error(f"Error in scan loop: {e}")
                    time.sleep(1)
        
        self.scan_thread = threading.Thread(target=scan_loop, daemon=True)
        self.scan_thread.start()
        self.logger.info("Continuous radar scanning started")
    
    def stop_continuous_scan(self):
        self.is_scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=2)
        self.logger.info("Continuous radar scanning stopped")
    
    def save_detections(self, filename='radar_detections.json'):
        data = []
        for detection in self.detections:
            data.append({
                'timestamp': detection['timestamp'],
                'range': detection['range'],
                'velocity': detection['velocity'],
                'doppler': detection['doppler'],
                'snr': detection['snr'],
                'type': detection.get('type', 'unknown'),
                'angle': detection.get('angle', 0)
            })
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        self.logger.info(f"Detections saved to {filename}")
    
    def plot_detections(self):
        if not self.detections:
            print("No detections to plot")
            return
        
        ranges = [d['range'] for d in self.detections]
        velocities = [d['velocity'] for d in self.detections]
        snrs = [d['snr'] for d in self.detections]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        
        # Range vs Time
        times = range(len(ranges))
        scatter = ax1.scatter(times, ranges, c=snrs, cmap='viridis', 
                             s=50, alpha=0.6)
        ax1.set_xlabel('Detection Number')
        ax1.set_ylabel('Range (m)')
        ax1.set_title('Target Range Over Time')
        plt.colorbar(scatter, ax=ax1, label='SNR (dB)')
        ax1.grid(True, alpha=0.3)
        
        # Velocity vs Range
        ax2.scatter(ranges, velocities, c=snrs, cmap='coolwarm', 
                   s=50, alpha=0.6)
        ax2.set_xlabel('Range (m)')
        ax2.set_ylabel('Velocity (m/s)')
        ax2.set_title('Range-Doppler Map')
        plt.colorbar(scatter, ax=ax2, label='SNR (dB)')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
