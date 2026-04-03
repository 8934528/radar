import threading
import time
import json
import re
from datetime import datetime
from collections import deque
import logging

class Firewall:
    
    def __init__(self):
        self.rules = []
        self.blocked_ips = set()
        self.allowed_ips = set()
        self.packet_log = deque(maxlen=1000)
        self.stats = {
            'packets_processed': 0,
            'packets_allowed': 0,
            'packets_blocked': 0,
            'alerts': 0,
            'start_time': None
        }
        self.logger = logging.getLogger('Firewall')
        self.is_active = False
        self.monitor_thread = None
        self.callback = None
        
        # Default rules (allow all)
        self.add_rule('ALLOW', '*', '*', '*', '*')
    
    def set_callback(self, callback):
        """Set callback for firewall events"""
        self.callback = callback
    
    def add_rule(self, action, protocol='*', src_ip='*', dst_ip='*', port='*'):
        rule = {
            'id': len(self.rules) + 1,
            'action': action.upper(),
            'protocol': protocol.upper(),
            'src_ip': src_ip,
            'dst_ip': dst_ip,
            'port': str(port),
            'created': datetime.now(),
            'hits': 0
        }
        
        self.rules.append(rule)
        self.logger.info(f"Added rule #{rule['id']}: {action} {protocol} {src_ip} -> {dst_ip}:{port}")
        
        # Notify via callback
        if self.callback:
            self.callback({
                'type': 'rule_added',
                'rule': rule
            })
        
        return rule['id']
    
    def add_block_rule(self, ip=None, port=None, protocol=None):
        if ip:
            self.add_rule('BLOCK', protocol or '*', ip, '*', port or '*')
            self.blocked_ips.add(ip)
        elif port:
            self.add_rule('BLOCK', protocol or '*', '*', '*', port)
    
    def remove_rule(self, rule_id):
        for i, rule in enumerate(self.rules):
            if rule['id'] == rule_id:
                self.rules.pop(i)
                self.logger.info(f"Removed rule #{rule_id}")
                
                if self.callback:
                    self.callback({
                        'type': 'rule_removed',
                        'rule_id': rule_id
                    })
                return True
        return False
    
    def check_packet(self, packet):
        """Check packet against firewall rules"""
        self.stats['packets_processed'] += 1
        
        protocol = packet.get('protocol', 'UNKNOWN')
        src_ip = packet.get('source')
        dst_ip = packet.get('destination')
        src_port = packet['info'].get('src_port') if packet.get('info') else None
        dst_port = packet['info'].get('dst_port') if packet.get('info') else None
        
        # Check rules in order
        for rule in self.rules:
            # Check protocol
            if rule['protocol'] != '*' and rule['protocol'] != protocol:
                continue
            
            # Check source IP
            if rule['src_ip'] != '*' and not self._ip_matches(src_ip, rule['src_ip']):
                continue
            
            # Check destination IP
            if rule['dst_ip'] != '*' and not self._ip_matches(dst_ip, rule['dst_ip']):
                continue
            
            # Check port
            if rule['port'] != '*':
                port_match = False
                if dst_port and str(dst_port) == rule['port']:
                    port_match = True
                if src_port and str(src_port) == rule['port']:
                    port_match = True
                if not port_match:
                    continue
            
            # Rule matches
            rule['hits'] += 1
            
            if rule['action'] == 'ALLOW':
                self.stats['packets_allowed'] += 1
                return True, rule['id'], f"Matched rule #{rule['id']}"
            else:
                self.stats['packets_blocked'] += 1
                self._log_blocked_packet(packet, rule)
                return False, rule['id'], f"Blocked by rule #{rule['id']}"
        
        # Default deny 
        self.stats['packets_blocked'] += 1
        self._log_blocked_packet(packet, None)
        return False, None, "No matching rule (default deny)"
    
    def _ip_matches(self, ip, pattern):
        """Check if IP matches pattern (supports CIDR and wildcard)"""
        if not ip:
            return False
        
        if pattern == '*':
            return True
        
        # Check CIDR notation
        if '/' in pattern:
            try:
                import ipaddress
                return ipaddress.ip_address(ip) in ipaddress.ip_network(pattern, strict=False)
            except:
                pass
        
        # Check wildcard (e.g., 192.168.*.*)
        if '*' in pattern:
            pattern_regex = '^' + re.escape(pattern).replace(r'\*', '.*') + '$'
            return re.match(pattern_regex, ip) is not None
        
        # Exact match
        return ip == pattern
    
    def _log_blocked_packet(self, packet, rule):
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'packet': {
                'source': packet.get('source'),
                'destination': packet.get('destination'),
                'protocol': packet.get('protocol'),
                'info': packet.get('info', {})
            },
            'rule_id': rule['id'] if rule else None
        }
        self.packet_log.append(log_entry)
        
        # Notify via callback
        if self.callback:
            self.callback({
                'type': 'packet_blocked',
                'packet': log_entry['packet'],
                'rule_id': log_entry['rule_id']
            })
        
        # Check for attack patterns
        self._check_attack_pattern(packet)
    
    def _check_attack_pattern(self, packet):
        # potential attack patterns
        src_ip = packet.get('source')
        if not src_ip:
            return 
        
        # Count recent blocks from this IP
        recent_blocks = []
        for p in self.packet_log:
            if p['packet'].get('source') == src_ip:
                try:
                    log_time = datetime.fromisoformat(p['timestamp'])
                    if (datetime.now() - log_time).seconds < 60:
                        recent_blocks.append(p)
                except:
                    pass
        
        if len(recent_blocks) >= 10:
            self.stats['alerts'] += 1
            
            alert_msg = f"ALERT: Possible attack from {src_ip} - {len(recent_blocks)} blocks in 60 seconds"
            self.logger.warning(alert_msg)
            
            if self.callback:
                self.callback({
                    'type': 'security_alert',
                    'message': alert_msg,
                    'source_ip': src_ip,
                    'block_count': len(recent_blocks)
                })
            
            # Auto-block if threshold exceeded
            if len(recent_blocks) >= 20 and src_ip not in self.blocked_ips:
                self.add_block_rule(ip=src_ip)
                block_msg = f"AUTO-BLOCKED: {src_ip} for suspicious activity"
                self.logger.critical(block_msg)
                
                if self.callback:
                    self.callback({
                        'type': 'auto_blocked',
                        'message': block_msg,
                        'source_ip': src_ip
                    })
    
    def start_monitoring(self, sniffer, interval=1):
        self.is_active = True
        self.stats['start_time'] = datetime.now()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, 
                                              args=(sniffer, interval), daemon=True)
        self.monitor_thread.start()
        self.logger.info("Firewall monitoring started")
        
        if self.callback:
            self.callback({
                'type': 'monitoring_started',
                'timestamp': datetime.now().isoformat()
            })
    
    def _monitor_loop(self, sniffer, interval):
        last_packet_count = 0
        
        while self.is_active:
            try:
                # Get new packets
                current_packets = list(sniffer.packets)
                new_packets = current_packets[last_packet_count:]
                
                # Check each new packet
                blocked_packets = []
                for packet in new_packets:
                    allowed, rule_id, reason = self.check_packet(packet)
                    
                    if not allowed:
                        blocked_packets.append({
                            'packet': packet,
                            'rule_id': rule_id,
                            'reason': reason
                        })
                
                # Send batch update
                if blocked_packets and self.callback:
                    self.callback({
                        'type': 'batch_blocked',
                        'count': len(blocked_packets),
                        'blocked': blocked_packets[:10]  # Send first 10
                    })
                
                last_packet_count = len(current_packets)
                time.sleep(interval)
                
            except Exception as e:
                self.logger.error(f"Monitoring error: {e}")
    
    def stop_monitoring(self):
        self.is_active = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        self.logger.info("Firewall monitoring stopped")
        
        if self.callback:
            self.callback({
                'type': 'monitoring_stopped',
                'timestamp': datetime.now().isoformat()
            })
    
    def get_stats(self):
        stats = self.stats.copy()
        duration = None
        if stats['start_time']:
            duration = (datetime.now() - stats['start_time']).total_seconds()
        stats['duration'] = duration
        stats['rules'] = len(self.rules)
        stats['blocked_ips'] = len(self.blocked_ips)
        
        return stats
    
    def get_blocked_packets(self, count=100):
        return list(self.packet_log)[-count:]
    
    def get_rules(self):
        return self.rules
    
    def get_status(self):
        return {
            'is_active': self.is_active,
            'stats': self.get_stats(),
            'rules_count': len(self.rules),
            'blocked_ips_count': len(self.blocked_ips),
            'recent_blocks': len(self.packet_log)
        }
    
    def save_rules(self, filename='firewall_rules.json'):
        """Save firewall rules to file"""
        rules_data = []
        for rule in self.rules:
            rules_data.append({
                'id': rule['id'],
                'action': rule['action'],
                'protocol': rule['protocol'],
                'src_ip': rule['src_ip'],
                'dst_ip': rule['dst_ip'],
                'port': rule['port'],
                'created': rule['created'].isoformat(),
                'hits': rule['hits']
            })
        
        with open(filename, 'w') as f:
            json.dump(rules_data, f, indent=2)
        
        self.logger.info(f"Rules saved to {filename}")
    
    def print_rules(self):
        # all firewall rules
        print("\n" + "="*80)
        print(f"{'ID':<4} {'ACTION':<8} {'PROTOCOL':<8} {'SOURCE':<20} {'DESTINATION':<20} {'PORT':<8} {'HITS':<8}")
        print("-"*80)
        
        for rule in self.rules:
            print(f"{rule['id']:<4} {rule['action']:<8} {rule['protocol']:<8} "
                  f"{rule['src_ip']:<20} {rule['dst_ip']:<20} {rule['port']:<8} "
                  f"{rule['hits']:<8}")
        print("="*80)
    
    def print_stats(self):

        # print firewall stats
        stats = self.get_stats()

        print("\n" + "="*50)
        print("FIREWALL STATISTICS")
        print("="*50)

        print(f"Uptime: {stats['duration']:.0f} seconds" if stats['duration'] else "Uptime: N/A")
        print(f"Rules: {stats['rules']}")
        print(f"Blocked IPs: {stats['blocked_ips']}")

        print(f"Packets Processed: {stats['packets_processed']}")
        print(f"Packets Allowed: {stats['packets_allowed']}")
        print(f"Packets Blocked: {stats['packets_blocked']}")
        print(f"Alerts: {stats['alerts']}")
        print("="*50)
