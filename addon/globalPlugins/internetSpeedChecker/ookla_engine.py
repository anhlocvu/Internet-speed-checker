# Ookla Speedtest Engine for NVDA
# Based on sivel/speedtest-cli logic but optimized for NVDA Addon.

import time
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import math
import threading
from queue import Queue
import ssl

class SpeedtestEngine:
    def __init__(self):
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) speedtest-cli/2.1.3',
            'Cache-Control': 'no-cache'
        }
        # Bypass SSL verification to ensure compatibility across all network providers/ISPs
        try:
            self.ssl_context = ssl._create_unverified_context()
        except AttributeError:
            self.ssl_context = None
        
    def open_url_with_redirect(self, req, timeout, max_redirects=3):
        """Helper to open urllib request, automatically following redirects (even for POST).
        Falls back to HTTP if HTTPS connection fails due to SSL/connection errors.
        """
        redirects = 0
        try_http_fallback = False
        
        while redirects < max_redirects:
            try:
                # Use context only if it is HTTPS
                ctx = self.ssl_context if req.full_url.startswith('https') else None
                with urllib.request.urlopen(req, timeout=timeout, context=ctx) as res:
                    data = res.read()
                    final_url = res.geturl()
                    return data, final_url
            except urllib.error.HTTPError as e:
                if e.code in (301, 302, 303, 307, 308):
                    new_url = e.headers.get('Location')
                    if not new_url:
                        raise e
                    # Create a new Request preserving method and data (important for POST redirects)
                    req = urllib.request.Request(
                        new_url, 
                        data=req.data, 
                        headers=req.headers, 
                        method=req.method
                    )
                    redirects += 1
                else:
                    raise e
            except Exception as e:
                # If HTTPS fails, fallback to HTTP
                if req.full_url.startswith('https') and not try_http_fallback:
                    new_url = req.full_url.replace('https://', 'http://')
                    req = urllib.request.Request(
                        new_url,
                        data=req.data,
                        headers=req.headers,
                        method=req.method
                    )
                    try_http_fallback = True
                    continue
                else:
                    raise e

    def get_config(self):
        """Fetches Ookla configuration and client info with Cache Buster."""
        try:
            t = int(time.time() * 1000)
            url = f"https://www.speedtest.net/speedtest-config.php?x={t}"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_context) as res:
                root = ET.fromstring(res.read())
                client = root.find('client').attrib
                return client
        except:
            return {}

    def get_best_server(self, client_country=None):
        """Finds the nearest/best Speedtest.net server with Cache Buster.
        Filters servers belonging to the client's country to avoid routing across borders.
        """
        try:
            t = int(time.time() * 1000)
            # Get nearby servers
            url = f"https://c.speedtest.net/speedtest-servers-static.php?x={t}"
            req = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(req, timeout=5, context=self.ssl_context) as res:
                root = ET.fromstring(res.read())
                servers = root.findall('.//server')
                
                if not servers:
                    raise Exception("No servers found")
                
                # Filter servers belonging to the client's country (e.g. cc matches client_country)
                country_servers = []
                if client_country:
                    cc_upper = client_country.upper()
                    country_servers = [s for s in servers if s.attrib.get('cc', '').upper() == cc_upper]
                
                # Fallback to all servers if no country-specific servers are found
                test_list = country_servers if country_servers else servers
                
                # Perform a quick latency check on the first 3 servers to pick the best one
                candidates = test_list[:3]
                best_ping = 999999
                best = candidates[0].attrib
                
                for c in candidates:
                    attrib = c.attrib
                    try:
                        srv_url = attrib['url']
                        host_parts = srv_url.split('/')[2].split(':')
                        host = host_parts[0]
                        port = int(host_parts[1]) if len(host_parts) > 1 else (443 if srv_url.startswith('https') else 80)
                        
                        import socket
                        start = time.perf_counter()
                        s = socket.create_connection((host, port), timeout=1.5)
                        s.close()
                        latency = (time.perf_counter() - start) * 1000
                        if latency < best_ping:
                            best_ping = latency
                            best = attrib
                    except:
                        pass
                
                # Ensure URL is correct
                best['url'] = best['url'].replace('http://', 'https://')
                return best
        except:
            # Fallback server in Singapore if Ookla list fails
            return {'url': 'https://speedtest.singapore.linode.com/upload.php', 'name': 'Singapore', 'sponsor': 'Linode'}

    def measure_download(self, server_url, duration=8):
        """Measures download speed using Cache Buster and automatic redirect follow."""
        # Standard Ookla test sizes
        sizes = [350, 500, 750, 1000, 1500, 2000, 2500, 3000, 3500, 4000]
        base_url = server_url.rsplit('/', 1)[0]
        
        total_received = 0
        start_time = time.perf_counter()
        
        for size in sizes:
            if time.perf_counter() - start_time > duration: break
            try:
                url = f"{base_url}/random{size}x{size}.jpg"
                
                # Cache buster for download
                t = int(time.time() * 1000)
                url_with_cb = f"{url}?x={t}.0"
                
                req = urllib.request.Request(url_with_cb, headers=self.headers)
                res_data, final_url = self.open_url_with_redirect(req, timeout=10)
                total_received += len(res_data)
            except:
                pass
            
        elapsed = time.perf_counter() - start_time
        return (total_received * 8) / (elapsed * 1000000) if elapsed > 0 else 0

    def measure_upload(self, server_url, duration=5):
        """Measures upload speed using Cache Buster, formatted data and automatic redirect follow."""
        # Use 256KB chunk size to fit all servers' limits and format with content1=
        size = 256 * 1024
        data = b'content1=' + b'0' * (size - 9)
        total_sent = 0
        start_time = time.perf_counter()
        
        while time.perf_counter() - start_time < duration:
            try:
                t = int(time.time() * 1000)
                url_with_cb = f"{server_url}?x={t}.0"
                req = urllib.request.Request(url_with_cb, data=data, method='POST', headers=self.headers)
                
                # Auto follow redirects and fallback to HTTP if needed
                res_data, final_url = self.open_url_with_redirect(req, timeout=10)
                total_sent += len(data)
            except:
                pass
                
        elapsed = time.perf_counter() - start_time
        return (total_sent * 8) / (elapsed * 1000000) if elapsed > 0 else 0

def run_test():
    engine = SpeedtestEngine()
    config = engine.get_config()
    client_country = config.get('country')
    server = engine.get_best_server(client_country)
    
    # Measure Ping to the best server
    ping = "N/A"
    try:
        # Dynamically extract host and port from server URL to ensure connectivity across all ISPs
        url = server['url']
        host_parts = url.split('/')[2].split(':')
        host = host_parts[0]
        port = int(host_parts[1]) if len(host_parts) > 1 else (443 if url.startswith('https') else 80)
        
        import socket
        start = time.perf_counter()
        s = socket.create_connection((host, port), timeout=3)
        s.close()
        ping = int((time.perf_counter() - start) * 1000)
    except:
        pass
        
    download = engine.measure_download(server['url'])
    upload = engine.measure_upload(server['url'])
    
    # Format server location to show Sponsor - Name (ID) for complete details
    sponsor = server.get('sponsor', 'Unknown')
    name = server.get('name', 'Unknown')
    server_id = server.get('id', 'Unknown')
    location_str = f"{sponsor} - {name} (ID {server_id})"
    
    return {
        'download': download,
        'upload': upload,
        'ping': ping,
        'isp': config.get('isp', 'Unknown ISP'),
        'location': location_str,
        'ip': config.get('ip', 'Unknown IP')
    }
