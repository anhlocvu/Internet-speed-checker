# Ookla Speedtest Engine for NVDA
# Based on sivel/speedtest-cli logic but optimized for NVDA Addon.

import time
import urllib.request
import xml.etree.ElementTree as ET
import math
import threading
from queue import Queue

class SpeedtestEngine:
    def __init__(self):
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) speedtest-cli/2.1.3'}
        
    def get_config(self):
        """Fetches Ookla configuration and client info."""
        try:
            req = urllib.request.Request("https://www.speedtest.net/speedtest-config.php", headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as res:
                root = ET.fromstring(res.read())
                client = root.find('client').attrib
                return client
        except:
            return {}

    def get_best_server(self):
        """Finds the nearest/best Speedtest.net server (usually in Vietnam)."""
        try:
            # Get nearby servers
            req = urllib.request.Request("https://c.speedtest.net/speedtest-servers-static.php", headers=self.headers)
            with urllib.request.urlopen(req, timeout=5) as res:
                root = ET.fromstring(res.read())
                servers = root.findall('.//server')
                
                # For simplicity in this lightweight version, we take the first server
                # which is usually very close. In a full version, we'd ping them all.
                best = servers[0].attrib
                # Ensure URL is correct
                best['url'] = best['url'].replace('http://', 'https://')
                return best
        except:
            # Fallback server in Singapore if Ookla list fails
            return {'url': 'https://speedtest.singapore.linode.com/upload.php', 'name': 'Singapore', 'sponsor': 'Linode'}

    def measure_download(self, server_url, duration=8):
        """Measures download speed using Ookla's method."""
        # Standard Ookla test sizes
        sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
        base_url = server_url.rsplit('/', 1)[0]
        
        total_received = 0
        start_time = time.perf_counter()
        
        try:
            for size in sizes:
                if time.perf_counter() - start_time > duration: break
                url = f"{base_url}/random{size}x{size}.jpg"
                req = urllib.request.Request(url, headers=self.headers)
                with urllib.request.urlopen(req, timeout=10) as res:
                    total_received += len(res.read())
            
            elapsed = time.perf_counter() - start_time
            return (total_received * 8) / (elapsed * 1000000) if elapsed > 0 else 0
        except:
            return 0

    def measure_upload(self, server_url, duration=5):
        """Measures upload speed."""
        # Uploading 1MB chunks
        data = b'0' * (1024 * 1024)
        total_sent = 0
        start_time = time.perf_counter()
        
        try:
            while time.perf_counter() - start_time < duration:
                req = urllib.request.Request(server_url, data=data, method='POST', headers=self.headers)
                with urllib.request.urlopen(req, timeout=10) as res:
                    res.read()
                total_sent += len(data)
                
            elapsed = time.perf_counter() - start_time
            return (total_sent * 8) / (elapsed * 1000000) if elapsed > 0 else 0
        except:
            return 0

def run_test():
    engine = SpeedtestEngine()
    config = engine.get_config()
    server = engine.get_best_server()
    
    # Measure Ping to the best server
    ping = "N/A"
    try:
        host = server['url'].split('/')[2].split(':')[0]
        import socket
        start = time.perf_counter()
        s = socket.create_connection((host, 80), timeout=3)
        s.close()
        ping = int((time.perf_counter() - start) * 1000)
    except:
        pass
        
    download = engine.measure_download(server['url'])
    upload = engine.measure_upload(server['url'])
    
    return {
        'download': download,
        'upload': upload,
        'ping': ping,
        'isp': config.get('isp', 'Unknown ISP'),
        'location': f"{server.get('name', 'Unknown')}, {server.get('country', 'Unknown')}",
        'ip': config.get('ip', 'Unknown IP')
    }
