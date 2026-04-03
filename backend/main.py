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

# Background threads storage
background_threads = []


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


# ========== SOCKET.IO EVENT HANDLERS ==========

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    logger.info(f"Client connected")
    emit('connected', {'status': 'connected', 'message': 'Radar system connected'})
    
    # Send initial status of all systems
    if scanner:
        status = scanner.get_scan_status()
        emit('scan_status', status)
    
    # Send firewall status
    if firewall:
        firewall_status = firewall.get_status() if hasattr(firewall, 'get_status') else {}
        emit('firewall_status', {
            'status': firewall_status,
            'rules_count': len(firewall.rules) if hasattr(firewall, 'rules') else 0,
            'timestamp': time.time()
        })
    
    # Send packet sniffer stats
    if sniffer:
        emit('sniffer_stats', sniffer.get_stats())
    
    # Send micro-doppler status
    if micro_doppler:
        latest = micro_doppler.get_latest_analysis()
        if latest:
            emit('doppler_data', latest)


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
    """Request micro-doppler analysis data"""
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
    """Request mining/construction site data"""
    if mining:
        try:
            status = mining.get_site_status()
            emit('site_data', status)
        except Exception as e:
            logger.error(f"Error getting site data: {e}")
            emit('error', {'message': str(e)})


@socketio.on('request_wifi_scan')
def handle_wifi_scan():
    """Request WiFi scan"""
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
    """Start continuous WiFi scan"""
    if wifi:
        interval = data.get('interval', 5)
        wifi.start_continuous_scan(interval)
        emit('scan_started', {'status': 'success', 'interval': interval})


@socketio.on('stop_continuous_scan')
def handle_stop_continuous_scan():
    """Stop continuous WiFi scan"""
    if wifi:
        wifi.stop_scanning()
        emit('scan_stopped', {'status': 'success'})


@socketio.on('request_adas_data')
def handle_adas_data():
    """Request ADAS system data"""
    if adas:
        try:
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
    """Request firewall status"""
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


@socketio.on('request_sniffer_stats')
def handle_sniffer_stats():
    """Request packet sniffer statistics"""
    if sniffer:
        try:
            stats = sniffer.get_stats()
            packets = sniffer.get_packets(count=20)
            emit('sniffer_stats', {'stats': stats, 'recent_packets': packets})
        except Exception as e:
            logger.error(f"Error getting sniffer stats: {e}")
            emit('error', {'message': str(e)})


@socketio.on('start_packet_sniffing')
def handle_start_sniffing(data):
    """Start packet sniffing"""
    if sniffer:
        try:
            count = data.get('count', None)
            timeout = data.get('timeout', None)
            sniffer.start_sniffing(count=count, timeout=timeout)
            emit('sniffing_started', {'status': 'success'})
        except Exception as e:
            logger.error(f"Error starting sniffing: {e}")
            emit('error', {'message': str(e)})


@socketio.on('stop_packet_sniffing')
def handle_stop_sniffing():
    """Stop packet sniffing"""
    if sniffer:
        try:
            sniffer.stop_sniffing()
            emit('sniffing_stopped', {'status': 'success'})
        except Exception as e:
            logger.error(f"Error stopping sniffing: {e}")
            emit('error', {'message': str(e)})


@socketio.on('add_firewall_rule')
def handle_add_rule(data):
    """Add firewall rule"""
    if firewall:
        try:
            action = data.get('action', 'BLOCK')
            protocol = data.get('protocol', '*')
            src_ip = data.get('src_ip', '*')
            dst_ip = data.get('dst_ip', '*')
            port = data.get('port', '*')
            
            rule_id = firewall.add_rule(action, protocol, src_ip, dst_ip, port)
            emit('rule_added', {'rule_id': rule_id, 'status': 'success'})
        except Exception as e:
            logger.error(f"Error adding firewall rule: {e}")
            emit('error', {'message': str(e)})


@socketio.on('remove_firewall_rule')
def handle_remove_rule(data):
    """Remove firewall rule"""
    if firewall:
        try:
            rule_id = data.get('rule_id')
            success = firewall.remove_rule(rule_id)
            emit('rule_removed', {'rule_id': rule_id, 'success': success})
        except Exception as e:
            logger.error(f"Error removing firewall rule: {e}")
            emit('error', {'message': str(e)})


# ========== CALLBACK FUNCTIONS ==========

def scanner_callback(scan_data):
    """Callback for scanner updates"""
    if scan_data.get('type') == 'position_update':
        socketio.emit('scan_position', {
            'azimuth': scan_data['azimuth'],
            'elevation': scan_data['elevation'],
            'mode': scan_data['mode']
        })


def mining_callback(data):
    """Callback for mining monitor updates"""
    if data.get('type') == 'alert' or data.get('type') == 'collision_alert':
        socketio.emit('mining_alert', data)
    elif data.get('type') == 'site_status':
        socketio.emit('site_update', data)


def wifi_callback(data):
    """Callback for WiFi scanner updates"""
    if data.get('type') == 'scan_result':
        socketio.emit('wifi_scan_update', data)


def firewall_callback(data):
    """Callback for firewall events"""
    socketio.emit('firewall_event', data)


def packet_callback(data):
    """Callback for packet sniffer events"""
    socketio.emit('packet_event', data)


def doppler_callback(data):
    """Callback for micro-doppler analysis"""
    socketio.emit('doppler_update', data)


# ========== SYSTEM INITIALIZATION ==========

def initialize_systems():
    """Initialize all radar system components"""
    global radar, micro_doppler, scanner, adas, mining, wifi, sniffer, firewall
    
    logger.info("=" * 60)
    logger.info("INITIALIZING RADAR SYSTEMS")
    logger.info("=" * 60)
    
    success_count = 0
    total_systems = 7
    
    try:
        # 1. Radar System
        logger.info("[1/7] Initializing Radar System...")
        radar = RadarSystem(frequency=24e9, power=10, antenna_gain=20)
        logger.info(f"✓ Radar System initialized: {radar.frequency/1e9:.1f} GHz")
        success_count += 1
        
        # 2. Scanning Mode Controller
        logger.info("[2/7] Initializing Scanning Mode Controller...")
        scanner = ScanningMode(scan_speed=45)
        scanner.set_callback(scanner_callback)
        scanner.start_circular_scan()
        logger.info("✓ Scanning Mode Controller initialized (Circular Scan Active)")
        success_count += 1
        
        # 3. Micro-Doppler Analyzer (ACTIVE IMMEDIATELY)
        logger.info("[3/7] Initializing Micro-Doppler Analyzer...")
        micro_doppler = MicroDopplerAnalyzer(sampling_rate=1000)
        micro_doppler.set_callback(doppler_callback)
        logger.info("✓ Micro-Doppler Analyzer initialized and ready")
        success_count += 1
        
        # 4. ADAS System
        logger.info("[4/7] Initializing ADAS System...")
        adas = ADASSystem(radar=radar)
        logger.info("✓ ADAS System initialized")
        success_count += 1
        
        # 5. Mining Monitor
        logger.info("[5/7] Initializing Mining Monitor...")
        mining = MiningConstructionMonitor()
        mining.set_callback(mining_callback)
        logger.info("✓ Mining Monitor initialized")
        success_count += 1
        
        # 6. WiFi Scanner
        logger.info("[6/7] Initializing WiFi Scanner...")
        wifi = WiFiScanner()
        wifi.set_callback(wifi_callback)
        logger.info("✓ WiFi Scanner initialized")
        success_count += 1
        
        # 7. Packet Sniffer and Firewall (ACTIVE IMMEDIATELY)
        logger.info("[7/7] Initializing Packet Sniffer & Firewall...")
        sniffer = PacketSniffer()
        sniffer.set_callback(packet_callback)
        
        firewall = Firewall()
        firewall.set_callback(firewall_callback)
        
        # Add default firewall rules
        if hasattr(firewall, 'add_rule'):
            firewall.add_rule('ALLOW', 'TCP', '*', '*', '80')
            firewall.add_rule('ALLOW', 'TCP', '*', '*', '443')
            firewall.add_rule('ALLOW', 'UDP', '*', '*', '53')
            firewall.add_rule('BLOCK', 'TCP', '*', '*', '23')   # Telnet
            firewall.add_rule('BLOCK', 'TCP', '*', '*', '3389') # RDP
            firewall.add_rule('BLOCK', 'TCP', '*', '*', '445')  # SMB
            logger.info("✓ Default firewall rules added (5 rules)")
        
        logger.info("✓ Packet Sniffer initialized")
        success_count += 1
        
        logger.info("=" * 60)
        logger.info(f"✓ ALL SYSTEMS INITIALIZED ({success_count}/{total_systems})")
        logger.info("=" * 60)
        
        return True
        
    except Exception as e:
        logger.error(f"Error initializing systems: {e}")
        return False


def start_background_threads():
    """Start all background monitoring threads"""
    global radar_thread_running, background_threads
    
    logger.info("Starting background services...")
    radar_thread_running = True
    
    # Start mining monitoring
    if mining:
        mining.start_monitoring(interval=2.0)
        logger.info("✓ Mining monitoring started (interval: 2.0s)")
    
    # Start WiFi scanning
    if wifi:
        wifi.start_continuous_scan(interval=10)
        logger.info("✓ WiFi scanning started (interval: 10.0s)")
    
    # Start packet sniffing (runs in background)
    if sniffer:
        sniffer.start_sniffing()
        logger.info("✓ Packet sniffing started (capturing all interfaces)")
    
    # Start micro-doppler analysis with synthetic data generator
    if micro_doppler:
        def generate_synthetic_radar_data():
            """Generate synthetic radar data for micro-doppler analysis"""
            t = np.linspace(0, 1, 1000)
            # Simulate micro-Doppler signature
            data = np.sin(2 * np.pi * 50 * t) + 0.3 * np.sin(2 * np.pi * 200 * t)
            data += np.random.normal(0, 0.1, len(t))
            return data
        
        micro_doppler.start_real_time_analysis(generate_synthetic_radar_data, interval=0.5)
        logger.info("✓ Micro-Doppler analysis started (interval: 0.5s)")
    
    # Start firewall monitoring (connects to sniffer)
    if firewall and sniffer:
        firewall.start_monitoring(sniffer, interval=1)
        logger.info("✓ Firewall monitoring started (interval: 1.0s)")
    
    logger.info("All background services are running")
    logger.info("=" * 60)


def cleanup():
    """Cleanup all resources on shutdown"""
    global radar_thread_running
    
    logger.info("=" * 60)
    logger.info("SHUTTING DOWN RADAR SYSTEM")
    logger.info("=" * 60)
    
    radar_thread_running = False
    
    if scanner:
        scanner.stop_scan()
        logger.info("✓ Scanner stopped")
    
    if mining:
        mining.stop_monitoring()
        logger.info("✓ Mining monitor stopped")
    
    if wifi:
        wifi.stop_scanning()
        logger.info("✓ WiFi scanner stopped")
    
    if micro_doppler:
        micro_doppler.stop_analysis()
        logger.info("✓ Micro-Doppler analyzer stopped")
    
    if sniffer:
        sniffer.stop_sniffing()
        logger.info("✓ Packet sniffer stopped")
    
    if firewall:
        firewall.stop_monitoring()
        logger.info("✓ Firewall stopped")
    
    logger.info("All systems shutdown complete")
    logger.info("=" * 60)


# ========== MAIN ENTRY POINT ==========

if __name__ == "__main__":
    # Print banner
    print("\n" + "=" * 70)
    print("╔══════════════════════════════════════════════════════════════════╗")
    print("║                    MILI RADAR SYSTEM                             ║")
    print("║                         Web Interface                            ║")
    print("╚══════════════════════════════════════════════════════════════════╝")
    print("=" * 70)
    print("\n[INFO] Initializing radar system components...")
    print("[INFO] Firewall will be activated immediately")
    print("[INFO] Packet sniffer will start capturing traffic")
    print("[INFO] Micro-Doppler analyzer will begin processing\n")
    
    try:
        # Initialize all systems
        if initialize_systems():
            # Start background threads
            start_background_threads()
            
            # Get local IP address
            import socket
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            
            print("\n" + "=" * 70)
            print("✓ RADAR SYSTEM FULLY ACTIVE")
            print("=" * 70)
            print("\n[ACTIVE SERVICES]")
            print("  • Firewall: ACTIVE (monitoring traffic)")
            print("  • Packet Sniffer: ACTIVE (capturing packets)")
            print("  • Micro-Doppler: ACTIVE (analyzing signatures)")
            print("  • Radar Scanner: ACTIVE (circular scan)")
            print("  • WiFi Scanner: ACTIVE (background scan)")
            print("  • Mining Monitor: ACTIVE")
            print("  • ADAS System: ACTIVE")
            print("\n[ACCESS INTERFACE]")
            print(f"  • Local:   http://127.0.0.1:5000")
            print(f"  • Network: http://{local_ip}:5000")
            print("\n[CONTROLS]")
            print("  • Press Ctrl+C to stop the server")
            print("=" * 70)
            
            # Start Flask server
            socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
        else:
            print("\n[ERROR] Failed to initialize radar systems. Please check the logs.")
            sys.exit(1)
        
    except KeyboardInterrupt:
        print("\n" + "=" * 70)
        print("\n[INFO] Shutdown signal received...")
        cleanup()
        print("\n[INFO] System shutdown complete. Goodbye!")
        print("=" * 70)
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        print(f"\n[ERROR] Fatal error starting server: {e}")
        sys.exit(1)
