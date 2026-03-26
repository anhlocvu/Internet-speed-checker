# Configuration management for Internet Speed Checker
import os
import json
from logHandler import log

CONFIG_FILE = os.path.join(os.path.dirname(__file__), "settings.json")

class Config:
    def __init__(self):
        self.defaults = {
            "unit": "Mbps" # Mbps or MB/s
        }
        self.data = self.defaults.copy()
        self.load()

    def load(self):
        if not os.path.exists(CONFIG_FILE):
            self.save()
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)
                self.data.update(loaded_data)
        except Exception as e:
            log.error(f"Internet Speed Checker: Error loading config: {e}")

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, indent=4)
        except Exception as e:
            log.error(f"Internet Speed Checker: Error saving config: {e}")

    @property
    def unit(self):
        return self.data.get("unit", "Mbps")

    @unit.setter
    def unit(self, value):
        self.data["unit"] = value
        self.save()

# Global config instance
conf = Config()
