# Internet Speed Engine for NVDA
# A lightweight speed test logic compatible with NVDA's Python environment.

import time
import urllib.request
import urllib.parse
import threading

def get_speed_results():
    results = {}
    
    # 1. Measure Ping (Latency to Google)
    try:
        start_ping = time.perf_counter()
        urllib.request.urlopen("https://www.google.com", timeout=5).read(1)
        results['ping'] = int((time.perf_counter() - start_ping) * 1000)
    except:
        results['ping'] = "N/A"

    # 2. Get ISP and Location info
    try:
        info = urllib.request.urlopen("http://ip-api.com/json", timeout=5).read().decode('utf-8')
        import json
        data = json.loads(info)
        results['isp'] = data.get('isp', 'Unknown ISP')
        results['location'] = f"{data.get('city', 'Unknown City')}, {data.get('country', 'Unknown Country')}"
        results['ip'] = data.get('query', 'Unknown IP')
    except:
        results['isp'] = "Unknown"
        results['location'] = "Unknown"
        results['ip'] = "Unknown"

    # 3. Measure Download Speed (Download 5MB from a fast CDN)
    # Using a 10MB test file from Hetzner (a very reliable host)
    test_url = "https://speed.hetzner.de/10MB.bin"
    try:
        start_dl = time.perf_counter()
        response = urllib.request.urlopen(test_url, timeout=20)
        chunk_size = 1024 * 1024 # 1MB chunks
        total_downloaded = 0
        while True:
            chunk = response.read(chunk_size)
            if not chunk: break
            total_downloaded += len(chunk)
            # Limit to 10MB for a quick test
            if total_downloaded >= 10 * 1024 * 1024: break
            
        duration = time.perf_counter() - start_dl
        # Convert to Mbps: (Bytes * 8 bits) / (duration * 1,000,000)
        results['download'] = (total_downloaded * 8) / (duration * 1000000)
    except Exception as e:
        results['download'] = 0.0

    # 4. Measure Upload Speed (Upload 1MB of dummy data)
    try:
        data = b'0' * (1024 * 1024) # 1MB of dummy data
        start_ul = time.perf_counter()
        req = urllib.request.Request("http://httpbin.org/post", data=data, method='POST')
        urllib.request.urlopen(req, timeout=20)
        duration_ul = time.perf_counter() - start_ul
        results['upload'] = (len(data) * 8) / (duration_ul * 1000000)
    except:
        results['upload'] = 0.0
        
    return results
