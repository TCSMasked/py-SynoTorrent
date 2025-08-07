# SynoTorrent Automation Script

A Python automation tool that searches for movies on **[YTS.mx](https://yts.mx)**, fetches the best available magnet links, and sends them directly to your **Synology NAS Download Station**.

## Features
- Reads movie titles from a `.txt` file (one movie per line)
- Searches YTS for the best quality (2160p → 1080p → 720p)
- Automatically sends magnet links to Synology Download Station
- Logs movies that could not be found or downloaded
- Color-coded console output for better readability

---

## Requirements

### **Python**
- Python 3.11+ (recommended)

### **PIP Packages**
Install the required dependencies:
```bash
pip install -r requirements.txt
