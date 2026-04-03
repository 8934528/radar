import numpy as np
import logging
import time
import threading
from flask import Flask, send_from_directory, request, Response
from flask_socketio import SocketIO, emit
import os
import sys
import math

# Import existing modules
from radar_system import RadarSystem
from micro_doppler import MicroDopplerAnalyzer
from scanning_modes import ScanningMode
from automotive_adas import ADASSystem
from mining_construction import MiningConstructionMonitor
from wifi_scanner import WiFiScanner
from packet_sniffer import PacketSniffer
from firewall import Firewall

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('radar_system.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('WebServer')

# Initialize Flask app
app = Flask(__name__, 
            static_folder='../frontend',
            template_folder='../frontend')
app.config['SECRET_KEY'] = 'radar_system_secret_key_2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Global variables for radar system
radar = None
micro_doppler = None
scanner = None
adas = None
mining = None
wifi = None
sniffer = None
firewall = None

# Threading control
radar_thread_running = False

@app.route('/')
def index():
    try:
        return send_from_directory('../frontend', 'rador.html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return "Radar system starting... Please check if rador.html exists in the frontend directory."

@app.route('/favicon.ico')
def favicon():
    """Browsers request this by default; no asset in repo — avoid noisy 404 logs."""
    return Response(status=204)

@app.route('/<path:filename>')
def serve_static(filename):
    # Serve static (CSS, JS)
    try:
        return send_from_directory('../frontend', filename)
    except Exception as e:
        logger.error(f"Error serving static file {filename}: {e}")
        return "File not found", 404

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected")
    emit('connected', {'status': 'connected', 'message': 'Radar system connected'})
    
    # Send initial status
    if scanner:
        status = scanner.get_scan_status()
        emit('scan_status', status)

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    logger.info(f"Client disconnected")

@socketio.on('change_radar_mode')
def handle_mode_change(data):
    """Change radar scanning mode"""
    payload = data or {}
    mode = payload.get('mode', 'circular')
    logger.info(f"Changing radar mode to: {mode}")

    if not scanner:
        emit('error', {'message': 'Scanner not available'})
        return

    try:
        if mode == 'circular':
            scanner.start_circular_scan()
        elif mode == 'sector':
            scanner.start_sector_scan(45, 135)
        elif mode == 'tracking':
            scanner.start_tracking_scan()
        elif mode == 'adas':
            scanner.set_scan_speed(75)
            scanner.start_circular_scan()
        elif mode == 'mining':
            scanner.set_scan_speed(25)
            scanner.start_sector_scan(0, 180)
        elif mode == 'wifi':
            scanner.set_scan_speed(50)
            scanner.start_circular_scan()
        else:
            emit('error', {'message': f'Unknown radar mode: {mode}'})
            return

        emit('mode_changed', {'mode': mode, 'status': 'success'})

    except Exception as e:
        logger.error(f"Error changing radar mode: {e}")
        emit('error', {'message': str(e)})

@socketio.on('set_scan_speed')
def handle_set_speed(data):
    """Set scan speed"""
    speed = data.get('speed', 45)
    if scanner:
        scanner.set_scan_speed(speed)
        emit('speed_changed', {'speed': speed})

@socketio.on('request_doppler_data')
def handle_doppler_request(data):
    # micro-doppler analysis data
    if micro_doppler:
        try:
            # Get latest analysis
            analysis = micro_doppler.get_latest_analysis()
            emit('doppler_data', analysis if analysis else {'status': 'no_data'})
        except Exception as e:
            logger.error(f"Error getting doppler data: {e}")
            emit('error', {'message': str(e)})

@socketio.on('request_site_data')
def handle_site_data():
    # mining/construction site data
    if mining:
        try:
            status = mining.get_site_status()
            emit('site_data', status)
        except Exception as e:
            logger.error(f"Error getting site data: {e}")
            emit('error', {'message': str(e)})

@socketio.on('request_wifi_scan')
def handle_wifi_scan():
    if wifi:
        try:
            networks = wifi.get_current_networks()
            quality = wifi.analyze_signal_quality()
            interference = wifi.detect_interference()
            
            wifi_data = {
                'networks': networks,
                'network_count': len(networks),
                'signal_quality': quality,
                'interference': interference,
                'timestamp': time.time()
            }
            emit('wifi_data', wifi_data)
        except Exception as e:
            logger.error(f"Error scanning WiFi: {e}")
            emit('error', {'message': str(e)})

@socketio.on('start_continuous_scan')
def handle_start_continuous_scan(data):
    if wifi:
        interval = data.get('interval', 5)
        wifi.start_continuous_scan(interval)
        emit('scan_started', {'status': 'success', 'interval': interval})

@socketio.on('stop_continuous_scan')
def handle_stop_continuous_scan():
    if wifi:
        wifi.stop_scanning()
        emit('scan_stopped', {'status': 'success'})

@socketio.on('request_adas_data')
def handle_adas_data():
    # ADAS system data
    if adas:
        try:
            # Get current vehicle status
            vehicle_status = adas.get_vehicle_status() if hasattr(adas, 'get_vehicle_status') else {}
            
            adas_data = {
                'status': vehicle_status,
                'timestamp': time.time()
            }
            emit('adas_data', adas_data)
        except Exception as e:
            logger.error(f"Error getting ADAS data: {e}")
            emit('error', {'message': str(e)})

@socketio.on('request_firewall_status')
def handle_firewall_status():
    # firewall status
    if firewall:
        try:
            firewall_status = firewall.get_status() if hasattr(firewall, 'get_status') else {}
            firewall_data = {
                'status': firewall_status,
                'rules_count': len(firewall.rules) if hasattr(firewall, 'rules') else 0,
                'timestamp': time.time()
            }
            emit('firewall_status', firewall_data)
        except Exception as e:
            logger.error(f"Error getting firewall status: {e}")
            emit('error', {'message': str(e)})

@socketio.on('update_monitoring_point')
def handle_update_monitoring_point(data):
    if mining:
        try:
            point_id = data.get('point_id')
            displacement = data.get('displacement', 0)
            mining.update_displacement(point_id, displacement)
            emit('monitoring_updated', {'status': 'success', 'point_id': point_id})
        except Exception as e:
            logger.error(f"Error updating monitoring point: {e}")
            emit('error', {'message': str(e)})

@socketio.on('update_vehicle_position')
def handle_update_vehicle_position(data):
    if mining:
        try:
            vehicle_id = data.get('vehicle_id')
            x = data.get('x', 0)
            y = data.get('y', 0)
            vx = data.get('vx', 0)
            vy = data.get('vy', 0)
            mining.update_vehicle_position(vehicle_id, x, y, vx, vy)
            emit('vehicle_updated', {'status': 'success', 'vehicle_id': vehicle_id})
        except Exception as e:
            logger.error(f"Error updating vehicle position: {e}")
            emit('error', {'message': str(e)})

def scanner_callback(scan_data):
    if scan_data.get('type') == 'position_update':
        # Emit scan position to frontend
        socketio.emit('scan_position', {
            'azimuth': scan_data['azimuth'],
            'elevation': scan_data['elevation'],
            'mode': scan_data['mode']
        })

def mining_callback(data):
    if data.get('type') == 'alert' or data.get('type') == 'collision_alert':
        socketio.emit('mining_alert', data)
    elif data.get('type') == 'site_status':
        socketio.emit('site_update', data)

def wifi_callback(data):
    if data.get('type') == 'scan_result':
        socketio.emit('wifi_scan_update', data)

def initialize_systems():
    # start all radar system components
    global radar, micro_doppler, scanner, adas, mining, wifi, sniffer, firewall
    
    logger.info("Initializing radar systems...")
    
    try:
        # radar system
        radar = RadarSystem(frequency=24e9, power=10, antenna_gain=20)
        logger.info(f"Radar System initialized: {radar.frequency/1e9:.1f} GHz")
        
        # scanning mode with callback
        scanner = ScanningMode(scan_speed=45)
        scanner.set_callback(scanner_callback)
        logger.info("Scanning mode controller initialized")
        
        # Start circular scan by default
        scanner.start_circular_scan()
        
        # micro-doppler analyzer
        micro_doppler = MicroDopplerAnalyzer(sampling_rate=1000)
        logger.info("Micro-Doppler analyzer initialized")
        
        # ADAS system
        adas = ADASSystem(radar=radar)
        logger.info("ADAS system initialized")
        
        # mining monitor with callback
        mining = MiningConstructionMonitor()
        mining.set_callback(mining_callback)
        logger.info("Mining monitor initialized")
        
        # WiFi scanner with callback
        wifi = WiFiScanner()
        wifi.set_callback(wifi_callback)
        logger.info("WiFi scanner initialized")
        
        # packet sniffer and firewall
        sniffer = PacketSniffer()
        firewall = Firewall()
        
        # Add firewall rules
        if hasattr(firewall, 'add_rule'):
            firewall.add_rule('ALLOW', 'TCP', '*', '*', '80')
            firewall.add_rule('ALLOW', 'TCP', '*', '*', '443')
            firewall.add_rule('ALLOW', 'UDP', '*', '*', '53')
            firewall.add_rule('BLOCK', 'TCP', '*', '*', '23')
            firewall.add_rule('BLOCK', 'TCP', '*', '*', '3389')
        
        logger.info("All systems initialized successfully")
        return True
        
    except Exception as e:
        logger.error(f"Error initializing systems: {e}")
        return False

def start_background_threads():
    global radar_thread_running
    
    radar_thread_running = True
    
    # mining monitoring
    if mining:
        mining.start_monitoring(interval=2.0)
    
    # WiFi scanning
    if wifi:
        wifi.start_continuous_scan(interval=10)
    
    logger.info("Background threads started")

def cleanup():
    global radar_thread_running
    
    logger.info("Cleaning up...")
    radar_thread_running = False
    
    if scanner:
        scanner.stop_scan()
    
    if mining:
        mining.stop_monitoring()
    
    if wifi:
        wifi.stop_scanning()
    
    if micro_doppler:
        micro_doppler.stop_analysis()
    
    logger.info("Cleanup complete")

if __name__ == "__main__":
    # Print banner
    print("=" * 70)
    print("MILI RADAR SYSTEM - Web Interface")
    print("=" * 70)
    print("\nInitializing radar system components...")
    
    try:
        # all systems
        if initialize_systems():
            # Start background threads
            start_background_threads()
            
            # Get local IP address
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            print("\n" + "=" * 70)
            print("RADAR SYSTEM READY")
            print("=" * 70)
            print("\nAccess the radar interface at:")
            print(f"  Local:   http://127.0.0.1:5000")
            print(f"  Network: http://{local_ip}:5000")
            print("\nPress Ctrl+C to stop the server")
            print("=" * 70)
            
            # Start Flask server
            socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        else:
            print("\nFailed to initialize radar systems. Please check the logs.")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("\nShutting down radar system...")
        cleanup()
        logger.info("System shutdown complete")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\nError starting server: {e}")
        sys.exit(1)
