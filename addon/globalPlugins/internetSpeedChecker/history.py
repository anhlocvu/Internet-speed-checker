# -*- coding: utf-8 -*-
# History management for Internet Speed Checker

import os
import json
import datetime
from logHandler import log
import globalVars

# Determine the history directory and file path
# globalVars.appArgs.configPath points to the NVDA user configuration directory.
# This prevents losing history when upgrading or reinstalling the add-on.
config_path = getattr(globalVars.appArgs, "configPath", None) if hasattr(globalVars, "appArgs") else None
if not config_path:
    # Fallback to user profile or document folder if running outside NVDA context (e.g. testing)
    config_path = os.path.expandvars(r"%APPDATA%\nvda")
    if not os.path.exists(config_path):
        config_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

HISTORY_DIR = os.path.join(config_path, "internet_speed_checker")
HISTORY_FILE = os.path.join(HISTORY_DIR, "history.json")

def _ensure_dir():
    if not os.path.exists(HISTORY_DIR):
        try:
            os.makedirs(HISTORY_DIR)
        except Exception as e:
            log.error(f"Internet Speed Checker: Error creating history directory: {e}")

def load_history():
    _ensure_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        log.error(f"Internet Speed Checker: Error loading history: {e}")
        return []

def save_history(history_data):
    _ensure_dir()
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(history_data, f, indent=4, ensure_ascii=False)
        return True
    except Exception as e:
        log.error(f"Internet Speed Checker: Error saving history: {e}")
        return False

def add_history_entry(download, upload, ping, unit, isp, location, ip):
    now = datetime.datetime.now()
    # Format: DD/MM/YYYY HH:MM:SS
    timestamp_str = now.strftime("%d/%m/%Y %H:%M:%S")
    
    entry = {
        "timestamp": timestamp_str,
        "download": download,
        "upload": upload,
        "ping": ping,
        "unit": unit,
        "isp": isp,
        "location": location,
        "ip": ip
    }
    
    history = load_history()
    # Insert at the beginning to show the newest entries first
    history.insert(0, entry)
    
    # Limit history to 100 entries to prevent performance issues
    if len(history) > 100:
        history = history[:100]
        
    save_history(history)

def clear_history():
    _ensure_dir()
    return save_history([])
