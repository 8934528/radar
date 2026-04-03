import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.fft import fft, fftshift
import logging
import threading
import time
import random

class MicroDopplerAnalyzer:
    """Micro-Doppler signature analyzer for radar target classification"""
    
    def __init__(self, sampling_rate=1000, pulse_repetition_freq=1000):
        self.sampling_rate = sampling_rate
        self.prf = pulse_repetition_freq
        self.logger = logging.getLogger('MicroDoppler')
        self.classification_results = []
        self.real_time_data = []
        self.is_analyzing = False
        self.analysis_thread = None
        self.callback = None
        self.synthetic_data_generator = None
        
    def set_callback(self, callback):
        """Set callback for analysis results"""
        self.callback = callback
        
    def generate_synthetic_radar_data(self, target_type=None):
        """Generate synthetic radar data with micro-Doppler signatures"""
        t = np.linspace(0, 1, self.sampling_rate)
        
        # Different micro-Doppler signatures for different target types
        if target_type == 'vehicle':
            # Vehicle signature - low frequency, moderate amplitude
            data = np.sin(2 * np.pi * 30 * t) + 0.2 * np.sin(2 * np.pi * 120 * t)
            data += 0.1 * np.sin(2 * np.pi * 250 * t)
        elif target_type == 'pedestrian':
            # Pedestrian signature - higher frequency components
            data = np.sin(2 * np.pi * 50 * t) + 0.4 * np.sin(2 * np.pi * 180 * t)
            data += 0.15 * np.sin(2 * np.pi * 300 * t)
        elif target_type == 'drone':
            # Drone signature - very high frequency
            data = np.sin(2 * np.pi * 100 * t) + 0.5 * np.sin(2 * np.pi * 400 * t)
            data += 0.3 * np.sin(2 * np.pi * 800 * t)
        else:
            # Mixed/general signature
            data = np.sin(2 * np.pi * 50 * t) + 0.3 * np.sin(2 * np.pi * 200 * t)
            data += 0.1 * np.random.normal(0, 0.1, len(t))
        
        # Add noise
        data += np.random.normal(0, 0.08, len(data))
        
        return data
    
    def extract_micro_doppler(self, radar_data):
        """Extract micro-Doppler signature using spectrogram"""
        if len(radar_data) < 64:
            return None, None, None
            
        # Compute spectrogram for micro-Doppler analysis
        window_size = min(256, len(radar_data) // 2)
        if window_size < 32:
            window_size = 32
            
        frequencies, times, spectrogram = signal.spectrogram(
            radar_data,
            fs=self.sampling_rate,
            window='hamming',
            nperseg=window_size,
            noverlap=window_size - window_size//4,
            mode='magnitude'
        )
        
        # Convert to dB
        spectrogram_db = 10 * np.log10(spectrogram + 1e-10)
        
        return frequencies, times, spectrogram_db
    
    def extract_features(self, spectrogram):
        """Extract features from micro-Doppler spectrogram"""
        if spectrogram is None or spectrogram.size == 0:
            return {}
            
        features = {}
        
        # Mean Doppler shift
        features['mean_doppler'] = float(np.mean(spectrogram, axis=1).mean())
        
        # Doppler spread (standard deviation)
        features['doppler_spread'] = float(np.std(spectrogram))
        
        # Energy distribution
        total_energy = np.sum(spectrogram) + 1e-10
        third = max(1, len(spectrogram) // 3)
        
        features['low_freq_energy'] = float(np.sum(spectrogram[:third]) / total_energy)
        features['mid_freq_energy'] = float(np.sum(spectrogram[third:2*third]) / total_energy)
        features['high_freq_energy'] = float(np.sum(spectrogram[2*third:]) / total_energy)
        
        # Micro-Doppler modulation depth
        max_doppler = np.max(spectrogram, axis=0)
        min_doppler = np.min(spectrogram, axis=0)
        modulation = (max_doppler - min_doppler) / (max_doppler + min_doppler + 1e-10)
        features['modulation_depth'] = float(np.mean(modulation))
        
        # Peak frequency
        freq_axis_mean = np.mean(spectrogram, axis=1)
        peak_idx = np.argmax(freq_axis_mean)
        features['peak_frequency'] = float(peak_idx / len(freq_axis_mean))
        
        # Classify target type based on features
        features['classification'] = self._classify_target(features)
        
        return features
    
    def _classify_target(self, features):
        """Simple classification based on micro-Doppler features"""
        modulation = features.get('modulation_depth', 0)
        high_freq = features.get('high_freq_energy', 0)
        doppler_spread = features.get('doppler_spread', 0)
        low_freq = features.get('low_freq_energy', 0)
        
        if modulation > 0.6:
            if high_freq > 0.4:
                return 'drone'
            else:
                return 'pedestrian'
        elif doppler_spread > 20:
            return 'vehicle'
        elif low_freq > 0.6:
            return 'stationary'
        else:
            return 'unknown'
    
    def analyze_data(self, radar_data):
        """Analyze radar data for micro-Doppler features"""
        if len(radar_data) < 64:
            return {'error': 'Insufficient data', 'status': 'waiting'}
        
        try:
            # Extract micro-Doppler
            freqs, times, spectrogram = self.extract_micro_doppler(radar_data)
            
            if spectrogram is None:
                return {'error': 'Spectrogram extraction failed', 'status': 'error'}
            
            # Extract features
            features = self.extract_features(spectrogram)
            
            result = {
                'features': features,
                'timestamp': time.time(),
                'data_points': len(radar_data),
                'status': 'active',
                'classification': features.get('classification', 'unknown'),
                'mean_doppler': features.get('mean_doppler', 0),
                'doppler_spread': features.get('doppler_spread', 0),
                'modulation_depth': features.get('modulation_depth', 0)
            }
            
            # Store result
            self.classification_results.append(result)
            if len(self.classification_results) > 100:
                self.classification_results.pop(0)
            
            # Call callback if set
            if self.callback:
                self.callback(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Analysis error: {e}")
            return {'error': str(e), 'status': 'error'}
    
    def start_real_time_analysis(self, data_source=None, interval=0.5):
        """Start real-time micro-Doppler analysis"""
        if self.is_analyzing:
            self.logger.warning("Analysis already running")
            return
            
        self.is_analyzing = True
        self.synthetic_data_generator = data_source
        
        def analysis_loop():
            counter = 0
            while self.is_analyzing:
                try:
                    # Get data from source or generate synthetic
                    if self.synthetic_data_generator and callable(self.synthetic_data_generator):
                        radar_data = self.synthetic_data_generator()
                    else:
                        # Generate synthetic data with varying target types
                        target_types = ['vehicle', 'pedestrian', 'drone', None]
                        target_type = target_types[counter % len(target_types)]
                        radar_data = self.generate_synthetic_radar_data(target_type)
                        counter += 1
                    
                    if radar_data is not None and len(radar_data) > 0:
                        # Analyze data
                        result = self.analyze_data(radar_data)
                        
                        # Log analysis results
                        if result and result.get('status') == 'active':
                            self.logger.debug(f"Micro-Doppler analysis: {result.get('classification', 'unknown')}")
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Analysis loop error: {e}")
                    time.sleep(1)
        
        self.analysis_thread = threading.Thread(target=analysis_loop, daemon=True)
        self.analysis_thread.start()
        self.logger.info("Real-time micro-Doppler analysis started")
    
    def stop_analysis(self):
        """Stop micro-Doppler analysis"""
        self.is_analyzing = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2)
        self.logger.info("Micro-Doppler analysis stopped")
    
    def get_latest_analysis(self):
        """Get the latest analysis result"""
        if self.classification_results:
            return self.classification_results[-1]
        return {'status': 'no_data', 'message': 'No analysis data available yet'}
    
    def get_analysis_history(self, limit=50):
        """Get analysis history"""
        return self.classification_results[-limit:]
    
    def get_status(self):
        """Get analyzer status"""
        return {
            'is_analyzing': self.is_analyzing,
            'results_count': len(self.classification_results),
            'sampling_rate': self.sampling_rate,
            'prf': self.prf
        }
    
    def plot_spectrogram(self, radar_data=None, title="Micro-Doppler Spectrogram"):
        """Plot micro-Doppler spectrogram"""
        if radar_data is None:
            radar_data = self.generate_synthetic_radar_data()
            
        freqs, times, spectrogram = self.extract_micro_doppler(radar_data)
        
        if spectrogram is None:
            print("Cannot plot: insufficient data")
            return
        
        plt.figure(figsize=(12, 6))
        plt.pcolormesh(times, freqs, 10 * np.log10(spectrogram + 1e-10), 
                      shading='gouraud', cmap='jet')
        plt.xlabel('Time (s)')
        plt.ylabel('Doppler Frequency (Hz)')
        plt.title(title)
        plt.colorbar(label='Intensity (dB)')
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        plt.show()
