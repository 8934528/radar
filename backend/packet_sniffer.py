import socket
import struct
import threading
import time
from datetime import datetime
from collections import deque
import json
import logging

class PacketSniffer:
    
    def __init__(self, interface=None, max_packets=1000): 
        self.interface = interface
        self.max_packets = max_packets
        self.packets = deque(maxlen=max_packets)
        self.is_sniffing = False
        self.sniff_thread = None
        self.socket = None
        self.logger = logging.getLogger('PacketSniffer')
        self.callback = None
        self.stats = {
            'total_packets': 0,
            'tcp_packets': 0,
            'udp_packets': 0,
            'icmp_packets': 0,
            'other_packets': 0,
            'start_time': None,
            'bytes_captured': 0
        }
    
    def set_callback(self, callback):
        # Set callback for packet capture
        self.callback = callback
        
    def start_sniffing(self, count=None, timeout=None):
        if self.is_sniffing:
            self.logger.warning("Sniffing already in progress")
            return
        
        self.is_sniffing = True
        self.stats['start_time'] = datetime.now()
        self.sniff_thread = threading.Thread(target=self._sniff_loop, 
                                            args=(count, timeout), daemon=True)
        self.sniff_thread.start()
        self.logger.info(f"Packet sniffing started on {self.interface or 'all interfaces'}")
    
    def _sniff_loop(self, count, timeout):
        try:
            # Create raw socket (requires root/admin privileges)
            self.socket = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.ntohs(3))
            self.socket.settimeout(1)
            
            start_time = time.time()
            packets_captured = 0
            
            while self.is_sniffing:
                try:
                    # Receive packet
                    packet_data, addr = self.socket.recvfrom(65535)
                    self.stats['bytes_captured'] += len(packet_data)
                    
                    # Parse packet
                    packet = self._parse_packet(packet_data, addr)
                    self.packets.append(packet)
                    
                    # Update stats
                    self.stats['total_packets'] += 1
                    protocol = packet['protocol']
                    if protocol == 'TCP':
                        self.stats['tcp_packets'] += 1
                    elif protocol == 'UDP':
                        self.stats['udp_packets'] += 1
                    elif protocol == 'ICMP':
                        self.stats['icmp_packets'] += 1
                    else:
                        self.stats['other_packets'] += 1
                    
                    packets_captured += 1
                    
                    # Call callback if set
                    if self.callback:
                        self.callback({
                            'type': 'packet_captured',
                            'packet': packet,
                            'stats': self.get_stats()
                        })
                    
                    # Check capture limits
                    if count and packets_captured >= count:
                        self.logger.info(f"Captured {count} packets, stopping...")
                        self.stop_sniffing()
                        break
                    
                    if timeout and (time.time() - start_time) >= timeout:
                        self.logger.info(f"Capture timeout ({timeout}s) reached, stopping...")
                        self.stop_sniffing()
                        break
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    self.logger.error(f"Error capturing packet: {e}")
                    continue
                    
        except PermissionError:
            self.logger.error("Permission denied. Please run with root/admin privileges.")
            self.is_sniffing = False
        except Exception as e:
            self.logger.error(f"Failed to create socket: {e}")
            self.is_sniffing = False
        finally:
            if self.socket:
                self.socket.close()
    
    def _parse_packet(self, data, addr):
        packet = {
            'timestamp': datetime.now().isoformat(),
            'length': len(data),
            'source': None,
            'destination': None,
            'protocol': 'UNKNOWN',
            'info': {}
        }
        
        try:
            # Parse Ethernet header (14 bytes)
            eth_header = data[:14]
            eth = struct.unpack('!6s6sH', eth_header)
            eth_protocol = socket.ntohs(eth[2])
            
            # Check for IP packets (IPv4 = 0x0800)
            if eth_protocol == 0x0800:
                # Parse IP header (20 bytes minimum)
                ip_header = data[14:34]
                ip = struct.unpack('!BBHHHBBH4s4s', ip_header)
                
                version = ip[0] >> 4
                ihl = ip[0] & 0xF
                protocol = ip[6]
                src_ip = socket.inet_ntoa(ip[8])
                dst_ip = socket.inet_ntoa(ip[9])
                
                packet['source'] = src_ip
                packet['destination'] = dst_ip
                
                # Protocol mapping
                proto_map = {1: 'ICMP', 6: 'TCP', 17: 'UDP'}
                packet['protocol'] = proto_map.get(protocol, f'IP-{protocol}')
                
                # Calculate header length
                ip_header_len = ihl * 4
                
                # Parse transport layer based on protocol
                if protocol == 6:  # TCP
                    tcp_header = data[14 + ip_header_len:14 + ip_header_len + 20]
                    tcp = struct.unpack('!HHLLBBHHH', tcp_header)
                    packet['info'] = {
                        'src_port': tcp[0],
                        'dst_port': tcp[1],
                        'flags': self._parse_tcp_flags(tcp[5])
                    }
                    
                elif protocol == 17:  # UDP
                    udp_header = data[14 + ip_header_len:14 + ip_header_len + 8]
                    udp = struct.unpack('!HHHH', udp_header)
                    packet['info'] = {
                        'src_port': udp[0],
                        'dst_port': udp[1],
                        'length': udp[2]
                    }
                    
                elif protocol == 1:  # ICMP
                    icmp_header = data[14 + ip_header_len:14 + ip_header_len + 4]
                    icmp = struct.unpack('!BBH', icmp_header)
                    packet['info'] = {
                        'type': icmp[0],
                        'code': icmp[1]
                    }
                    
        except Exception as e:
            packet['error'] = str(e)
            
        return packet
    
    def _parse_tcp_flags(self, flags_byte):
        # Parse TCP flags
        flags = []
        flag_map = {
            0x01: 'FIN',
            0x02: 'SYN',
            0x04: 'RST',
            0x08: 'PSH',
            0x10: 'ACK',
            0x20: 'URG',
            0x40: 'ECE',
            0x80: 'CWR'
        }
        
        for mask, name in flag_map.items():
            if flags_byte & mask:
                flags.append(name)
        
        return flags
    
    def stop_sniffing(self):
        self.is_sniffing = False
        if self.sniff_thread:
            self.sniff_thread.join(timeout=2)
        if self.socket:
            self.socket.close()
        self.logger.info("Packet sniffing stopped")
    
    def get_packets(self, count=None, protocol=None, source=None, destination=None):
        filtered = list(self.packets)
        
        if protocol:
            filtered = [p for p in filtered if p['protocol'] == protocol]
        if source:
            filtered = [p for p in filtered if p.get('source') == source]
        if destination:
            filtered = [p for p in filtered if p.get('destination') == destination]
        
        if count:
            filtered = filtered[-count:]
        
        return filtered
    
    def get_stats(self):
        # sniffing stats
        duration = None
        if self.stats['start_time']:
            duration = (datetime.now() - self.stats['start_time']).total_seconds()
        
        stats = self.stats.copy()
        stats['duration'] = duration
        stats['packet_rate'] = self.stats['total_packets'] / duration if duration else 0
        
        return stats
    
    def analyze_traffic(self):
        if not self.packets:
            return None
        
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'total_packets': len(self.packets),
            'protocol_distribution': {},
            'top_sources': {},
            'top_destinations': {},
            'top_ports': {}
        }
        
        # Protocol distribution
        for packet in self.packets:
            proto = packet['protocol']
            analysis['protocol_distribution'][proto] = analysis['protocol_distribution'].get(proto, 0) + 1
            
            # Source IPs
            src = packet.get('source')
            if src:
                analysis['top_sources'][src] = analysis['top_sources'].get(src, 0) + 1
            
            # Destination IPs
            dst = packet.get('destination')
            if dst:
                analysis['top_destinations'][dst] = analysis['top_destinations'].get(dst, 0) + 1
            
            # Ports
            port = packet['info'].get('dst_port')
            if port:
                analysis['top_ports'][port] = analysis['top_ports'].get(port, 0) + 1
        
        # Sort and limit to top 10
        analysis['top_sources'] = dict(sorted(analysis['top_sources'].items(), 
                                              key=lambda x: x[1], reverse=True)[:10])
        analysis['top_destinations'] = dict(sorted(analysis['top_destinations'].items(), 
                                                   key=lambda x: x[1], reverse=True)[:10])
        analysis['top_ports'] = dict(sorted(analysis['top_ports'].items(), 
                                           key=lambda x: x[1], reverse=True)[:10])
        
        return analysis
    
    def export_packets(self, filename='packets.json', limit=100):
        packets_to_export = list(self.packets)[-limit:]
        
        data = {
            'timestamp': datetime.now().isoformat(),
            'count': len(packets_to_export),
            'stats': self.get_stats(),
            'packets': packets_to_export
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2, default=str)
        
        self.logger.info(f"Exported {len(packets_to_export)} packets to {filename}")
