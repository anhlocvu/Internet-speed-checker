# Internet Speed Engine for NVDA
# A lightweight speed test logic compatible with NVDA's Python environment.

import time
import urllib.request
import json
import socket

def get_speed_results():
    results = {}
    
    # Common headers
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    host = "speed.cloudflare.com"

    # 1. Measure TCP Ping (Latency)
    # Using a socket connection to port 443 gives a much closer approximation 
    # to ICMP ping than a full HTTP request.
    try:
        ip = socket.gethostbyname(host)
        start_ping = time.perf_counter()
        s = socket.create_connection((ip, 443), timeout=5)
        s.close()
        results['ping'] = int((time.perf_counter() - start_ping) * 1000)
    except:
        results['ping'] = "N/A"

    # 2. Get Metadata (ISP, Location, IP)
    # We still fetch this, but separate from the ping measurement.
    try:
        req = urllib.request.Request(f"https://{host}/meta", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode('utf-8'))
            results['isp'] = data.get('asOrganization', 'Unknown ISP')
            city = data.get('city', 'Unknown City')
            country = data.get('country', 'Unknown Country')
            results['location'] = f"{city}, {country}"
            results['ip'] = data.get('clientIp', data.get('ip', 'Unknown IP'))
    except Exception as e:
        if 'isp' not in results: results['isp'] = "Unknown"
        if 'location' not in results: results['location'] = "Unknown"
        if 'ip' not in results: results['ip'] = "Unknown"

    # 3. Measure Download Speed
    # Download 50MB. Larger size allows TCP window to scale up for accurate high-speed results.
    try:
        bytes_to_download = 50 * 1024 * 1024
        url = f"https://{host}/__down?bytes={bytes_to_download}"
        
        start_dl = time.perf_counter()
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=45) as response:
            total_downloaded = 0
            # Larger chunk size (1MB) reduces CPU overhead in Python loop
            chunk_size = 1024 * 1024 
            while True:
                chunk = response.read(chunk_size)
                if not chunk: break
                total_downloaded += len(chunk)
        
        duration = time.perf_counter() - start_dl
        if duration > 0:
            results['download'] = (total_downloaded * 8) / (duration * 1000000)
        else:
            results['download'] = 0.0
    except Exception as e:
        results['download'] = 0.0

    # 4. Measure Upload Speed
    # Upload 10MB.
    try:
        data_size = 10 * 1024 * 1024
        # Create a large byte array (efficiently)
        data = bytearray(data_size) 
        url = f"https://{host}/__up"
        
        start_ul = time.perf_counter()
        req = urllib.request.Request(url, data=data, method='POST', headers=headers)
        with urllib.request.urlopen(req, timeout=45) as response:
            response.read() # Ensure request completes
            
        duration_ul = time.perf_counter() - start_ul
        if duration_ul > 0:
            results['upload'] = (data_size * 8) / (duration_ul * 1000000)
        else:
            results['upload'] = 0.0
    except Exception as e:
        results['upload'] = 0.0
        
    return results
