import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
from scipy.fft import fft, fftshift
import logging
import threading
import time

class MicroDopplerAnalyzer:
    
    def __init__(self, sampling_rate=1000, pulse_repetition_freq=1000):
        self.sampling_rate = sampling_rate
        self.prf = pulse_repetition_freq
        self.logger = logging.getLogger('MicroDoppler')
        self.classification_results = []
        self.real_time_data = []
        self.is_analyzing = False
        self.analysis_thread = None
        self.callback = None
        
    def set_callback(self, callback):
        """Set callback for analysis results"""
        self.callback = callback
        
    def extract_micro_doppler(self, radar_data):
        if len(radar_data) < 256:
            return None, None, None
            
        # Compute spectrogram for micro-Doppler analysis
        window_size = min(256, len(radar_data) // 2)
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
        if spectrogram is None or spectrogram.size == 0:
            return {}
            
        features = {}
        
        # Mean Doppler shift
        features['mean_doppler'] = float(np.mean(spectrogram, axis=1).mean())
        
        # Doppler spread (standard deviation)
        features['doppler_spread'] = float(np.std(spectrogram))
        
        # Energy distribution
        total_energy = np.sum(spectrogram) + 1e-10
        third = len(spectrogram) // 3
        
        features['low_freq_energy'] = float(np.sum(spectrogram[:third]) / total_energy)
        features['mid_freq_energy'] = float(np.sum(spectrogram[third:2*third]) / total_energy)
        features['high_freq_energy'] = float(np.sum(spectrogram[2*third:]) / total_energy)
        
        # Micro-Doppler modulation depth
        max_doppler = np.max(spectrogram, axis=0)
        min_doppler = np.min(spectrogram, axis=0)
        modulation = (max_doppler - min_doppler) / (max_doppler + min_doppler + 1e-10)
        features['modulation_depth'] = float(np.mean(modulation))
        
        return features
    
    def analyze_data(self, radar_data):
        if len(radar_data) < 64:
            return {'error': 'Insufficient data'}
        
        try:
            # Extract micro-Doppler
            freqs, times, spectrogram = self.extract_micro_doppler(radar_data)
            
            if spectrogram is None:
                return {'error': 'Spectrogram extraction failed'}
            
            # Extract features
            features = self.extract_features(spectrogram)
            
            result = {
                'features': features,
                'timestamp': time.time(),
                'data_points': len(radar_data)
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
            return {'error': str(e)}
    
    def start_real_time_analysis(self, data_source, interval=0.5):
        if self.is_analyzing:
            return
            
        self.is_analyzing = True
        
        def analysis_loop():
            while self.is_analyzing:
                try:
                    # Get data from source
                    radar_data = data_source() if callable(data_source) else None
                    
                    if radar_data is not None and len(radar_data) > 0:
                        # Analyze data
                        result = self.analyze_data(radar_data)
                        
                        # Emit via callback if available
                        if self.callback and result and 'error' not in result:
                            self.callback(result)
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    self.logger.error(f"Analysis loop error: {e}")
                    time.sleep(1)
        
        self.analysis_thread = threading.Thread(target=analysis_loop, daemon=True)
        self.analysis_thread.start()
        self.logger.info("Real-time micro-Doppler analysis started")
    
    def stop_analysis(self):
        self.is_analyzing = False
        if self.analysis_thread:
            self.analysis_thread.join(timeout=2)
        self.logger.info("Micro-Doppler analysis stopped")
    
    def get_latest_analysis(self):
        if self.classification_results:
            return self.classification_results[-1]
        return None
    
    def get_analysis_history(self, limit=50):

        return self.classification_results[-limit:]
    
    def plot_spectrogram(self, radar_data, title="Micro-Doppler Spectrogram"):

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
