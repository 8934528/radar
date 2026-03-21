import numpy as np
import matplotlib.pyplot as plt
import time
import threading
import json
import subprocess
import platform
from datetime import datetime
from collections import deque
import logging

class WiFiScanner:
    
    def __init__(self, interface=None):
        self.interface = interface or self._detect_interface()
        self.scan_results = deque(maxlen=100)
        self.signal_history = deque(maxlen=1000)
        self.is_scanning = False
        self.scan_thread = None
        self.callback = None
        self.logger = logging.getLogger('WiFiScanner')
        
        # Channel frequencies mapping
        self.channels = {
            1: 2412, 2: 2417, 3: 2422, 4: 2427, 5: 2432,
            6: 2437, 7: 2442, 8: 2447, 9: 2452, 10: 2457,
            11: 2462, 12: 2467, 13: 2472, 14: 2484,
            36: 5180, 40: 5200, 44: 5220, 48: 5240,
            52: 5260, 56: 5280, 60: 5300, 64: 5320,
            100: 5500, 104: 5520, 108: 5540, 112: 5560,
            116: 5580, 120: 5600, 124: 5620, 128: 5640,
            132: 5660, 136: 5680, 140: 5700, 149: 5745,
            153: 5765, 157: 5785, 161: 5805, 165: 5825
        }
        
        self.logger.info(f"WiFi Scanner initialized on interface: {self.interface}")
    
    def set_callback(self, callback):
        self.callback = callback
    
    def _detect_interface(self):
        system = platform.system()
        
        if system == 'Linux':
            try:
                result = subprocess.run(['iwconfig'], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if 'IEEE 802.11' in line:
                        return line.split()[0]
            except:
                pass
        elif system == 'Darwin':  # macOS
            try:
                result = subprocess.run(['ifconfig'], capture_output=True, text=True, timeout=5)
                for line in result.stdout.split('\n'):
                    if 'awdl' in line or ('en' in line and 'media:' in line):
                        return line.split(':')[0]
            except:
                pass
        elif system == 'Windows':
            return 'Wi-Fi'
        
        return 'wlan0'  # Default fallback
    
    def perform_scan(self):
        networks = []
        system = platform.system()
        
        try:
            if system == 'Linux':
                result = subprocess.run(['sudo', 'iwlist', self.interface, 'scan'], 
                                      capture_output=True, text=True, timeout=10)
                networks = self._parse_iwlist_output(result.stdout)
                
            elif system == 'Darwin':
                # Try airport command
                airport_path = '/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport'
                result = subprocess.run([airport_path, '-s'], 
                                      capture_output=True, text=True, timeout=10)
                networks = self._parse_airport_output(result.stdout)
                
            elif system == 'Windows':
                result = subprocess.run(['netsh', 'wlan', 'show', 'networks', 'mode=bssid'], 
                                      capture_output=True, text=True, timeout=10)
                networks = self._parse_netsh_output(result.stdout)
                
        except subprocess.TimeoutExpired:
            self.logger.error("Scan timeout")
            networks = self._get_mock_networks()
        except Exception as e:
            self.logger.error(f"Scan error: {e}")
            networks = self._get_mock_networks()
        
        return networks
    
    def _get_mock_networks(self):
        return []
    
    def _parse_iwlist_output(self, output):
        networks = []
        current_network = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            if 'ESSID:' in line:
                if current_network:
                    networks.append(current_network)
                current_network = {}
                essid = line.split('ESSID:')[1].strip('"')
                if essid:
                    current_network['ssid'] = essid
                
            elif 'Address:' in line and 'bssid' not in current_network:
                current_network['bssid'] = line.split('Address:')[1].strip()
                
            elif 'Signal level=' in line:
                signal = line.split('Signal level=')[1].split(' ')[0]
                if 'dBm' in signal:
                    current_network['rssi'] = int(signal.replace('dBm', ''))
                else:
                    try:
                        current_network['rssi'] = int(signal)
                    except:
                        pass
                    
            elif 'Encryption key:' in line and 'security' not in current_network:
                current_network['security'] = 'WEP' if 'on' in line else 'Open'
                
            elif 'IE: WPA' in line and 'security' not in current_network:
                current_network['security'] = 'WPA/WPA2'
        
        if current_network and 'ssid' in current_network:
            networks.append(current_network)
        
        return networks
    
    def _parse_airport_output(self, output):
        """Parse macOS airport scan output"""
        networks = []
        lines = output.split('\n')[1:]  # Skip header
        
        for line in lines:
            if line.strip():
                parts = line.split()
                if len(parts) >= 5:
                    network = {
                        'ssid': parts[0],
                        'bssid': parts[1],
                        'rssi': int(parts[2]),
                        'channel': int(parts[3].split(',')[0]),
                        'security': parts[4]
                    }
                    
                    # Add frequency
                    if network['channel'] in self.channels:
                        network['frequency'] = self.channels[network['channel']]
                    
                    networks.append(network)
        
        return networks
    
    def _parse_netsh_output(self, output):
        """Parse Windows netsh output"""
        networks = []
        current_network = {}
        
        for line in output.split('\n'):
            line = line.strip()
            
            if 'SSID' in line and ':' in line and 'ssid' not in current_network:
                if current_network:
                    networks.append(current_network)
                current_network = {}
                current_network['ssid'] = line.split(':')[1].strip()
                
            elif 'BSSID' in line and 'bssid' not in current_network:
                current_network['bssid'] = line.split(':')[1].strip()
                
            elif 'Signal' in line and 'rssi' not in current_network:
                signal_str = line.split(':')[1].strip().replace('%', '')
                try:
                    signal_percent = int(signal_str)
                    current_network['rssi'] = (signal_percent / 2) - 100
                except:
                    pass
                    
            elif 'Channel' in line and 'channel' not in current_network:
                try:
                    current_network['channel'] = int(line.split(':')[1].strip())
                except:
                    pass
        
        if current_network and 'ssid' in current_network:
            networks.append(current_network)
        
        return networks
    
    def start_continuous_scan(self, interval=5):
        if self.is_scanning:
            return
        
        self.is_scanning = True
        self.scan_thread = threading.Thread(target=self._continuous_scan_loop, 
                                           args=(interval,), daemon=True)
        self.scan_thread.start()
        self.logger.info(f"Continuous scanning started (interval: {interval}s)")
    
    def _continuous_scan_loop(self, interval):
        """Continuous scanning loop"""
        while self.is_scanning:
            try:
                networks = self.perform_scan()
                
                scan_record = {
                    'timestamp': datetime.now().isoformat(),
                    'networks': networks
                }
                self.scan_results.append(scan_record)
                
                # Update signal history
                for net in networks:
                    self.signal_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'ssid': net.get('ssid', 'Unknown'),
                        'rssi': net.get('rssi', 0),
                        'channel': net.get('channel', 0)
                    })
                
                # Call callback if set
                if self.callback:
                    self.callback({
                        'type': 'scan_result',
                        'networks': networks,
                        'network_count': len(networks),
                        'timestamp': datetime.now().isoformat()
                    })
                
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Scan loop error: {e}")
                time.sleep(interval)
    
    def stop_scanning(self):
        self.is_scanning = False
        if self.scan_thread:
            self.scan_thread.join(timeout=2)
        self.logger.info("Scanning stopped")
    
    def get_current_networks(self):
        """Get most recent scan results"""
        if self.scan_results:
            return self.scan_results[-1]['networks']
        return []
    
    def analyze_signal_quality(self):
        networks = self.get_current_networks()
        
        if not networks:
            return {}
        
        analysis = {}
        
        for net in networks:
            ssid = net.get('ssid', 'Unknown')
            rssi = net.get('rssi', -100)
            
            # Determine quality
            if rssi > -50:
                quality = 'Excellent'
                grade = 'A'
            elif rssi > -60:
                quality = 'Good'
                grade = 'B'
            elif rssi > -70:
                quality = 'Fair'
                grade = 'C'
            elif rssi > -80:
                quality = 'Poor'
                grade = 'D'
            else:
                quality = 'Very Poor'
                grade = 'F'
            
            analysis[ssid] = {
                'rssi': rssi,
                'quality': quality,
                'grade': grade,
                'channel': net.get('channel', 'Unknown'),
                'security': net.get('security', 'Unknown'),
                'bssid': net.get('bssid', 'Unknown')
            }
        
        return analysis
    
    def detect_interference(self, threshold=-70):
        networks = self.get_current_networks()
        
        if not networks:
            return []
        
        # Group by channel
        channel_congestion = {}
        
        for net in networks:
            channel = net.get('channel')
            if channel:
                if channel not in channel_congestion:
                    channel_congestion[channel] = []
                channel_congestion[channel].append(net.get('rssi', -100))
        
        # Analyze congestion
        interference = []
        for channel, signals in channel_congestion.items():
            avg_signal = np.mean(signals)
            if avg_signal > threshold:
                interference.append({
                    'channel': channel,
                    'network_count': len(signals),
                    'avg_signal': float(avg_signal),
                    'severity': 'high' if avg_signal > -60 else 'medium'
                })
        
        return interference
    
    def export_scan_data(self, filename='wifi_scan.json'):
        """Export scan data to JSON"""
        data = {
            'timestamp': datetime.now().isoformat(),
            'scans': []
        }
        
        for scan in self.scan_results[-10:]:
            data['scans'].append(scan)
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Scan data exported to {filename}")
