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

    # 1. Get Metadata (ISP, Location, IP) & Ping
    # We use Cloudflare meta endpoint which is fast and gives us the nearest colo info.
    # Cloudflare uses Anycast, so this automatically connects to the nearest server.
    try:
        start_ping = time.perf_counter()
        req = urllib.request.Request("https://speed.cloudflare.com/meta", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as response:
            content = response.read().decode('utf-8')
            # Calculate ping immediately after read
            results['ping'] = int((time.perf_counter() - start_ping) * 1000)
            
            data = json.loads(content)
            results['isp'] = data.get('asOrganization', 'Unknown ISP')
            # Fallback for city/country if missing
            city = data.get('city', 'Unknown City')
            country = data.get('country', 'Unknown Country')
            results['location'] = f"{city}, {country}"
            results['ip'] = data.get('clientIp', data.get('ip', 'Unknown IP'))
    except Exception as e:
        results['ping'] = "N/A"
        results['isp'] = "Unknown"
        results['location'] = "Unknown"
        results['ip'] = "Unknown"

    # 2. Measure Download Speed
    # Download 10MB from Cloudflare (Anycast - automatically nearest server)
    try:
        # 10 MB
        bytes_to_download = 10 * 1024 * 1024
        url = f"https://speed.cloudflare.com/__down?bytes={bytes_to_download}"
        
        start_dl = time.perf_counter()
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            total_downloaded = 0
            chunk_size = 64 * 1024 # 64KB chunks
            while True:
                chunk = response.read(chunk_size)
                if not chunk: break
                total_downloaded += len(chunk)
        
        duration = time.perf_counter() - start_dl
        # Avoid division by zero
        if duration > 0:
            results['download'] = (total_downloaded * 8) / (duration * 1000000)
        else:
            results['download'] = 0.0
    except Exception as e:
        results['download'] = 0.0

    # 3. Measure Upload Speed
    # Upload 2MB to Cloudflare
    # Using 2MB to be a bit more substantial than 1MB but quick enough
    try:
        data_size = 2 * 1024 * 1024
        data = b'0' * data_size
        url = "https://speed.cloudflare.com/__up"
        
        start_ul = time.perf_counter()
        req = urllib.request.Request(url, data=data, method='POST', headers=headers)
        with urllib.request.urlopen(req, timeout=30) as response:
            response.read() # Ensure request completes
            
        duration_ul = time.perf_counter() - start_ul
        if duration_ul > 0:
            results['upload'] = (data_size * 8) / (duration_ul * 1000000)
        else:
            results['upload'] = 0.0
    except Exception as e:
        results['upload'] = 0.0
        
    return results
