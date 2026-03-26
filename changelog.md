## 1.0.2

* **New Speed Test Engine:** Migrated to the professional **Speedtest.net (Ookla)** engine for maximum accuracy.

  * Automatically finds the nearest server (Vietnamese servers for VN users, local servers for international users).
  * Uses a robust, time-limited measurement method to prevent the add-on from hanging.
* **NVDA Settings Integration:** The add-on settings are now integrated into the standard NVDA Settings dialog (NVDA Menu -> Preferences -> Settings).
* **Unit Selection:** Added a setting to choose between **Megabits (Mbps)** and **Megabytes (MB/s)**.
* **Improved Results Dialog:**

  * Added a **"Copy Results"** button to easily copy the test report to the clipboard.
  * Confirmation voice message: "The result has been copied to the clipboard".
  * Optimized accessibility and focus management for screen readers.
* **Performance \& Stability:**

  * Switched to pure HTTP/TCP measurements to avoid SSL/TLS handshake delays and high pings.
  * Improved memory usage and buffer management.

