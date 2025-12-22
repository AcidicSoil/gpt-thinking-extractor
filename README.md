# GPT Thinking Extractor

Tools to scrape and extract the "Thinking" process data from ChatGPT threads and projects.

## Prerequisites

- Python 3.13+
- Chrome/Chromium browser (for remote debugging)

## Installation

1. **Install dependencies:**

   ```bash
   pip install .
   ```

2. **Install Playwright browsers:**

   ```bash
   playwright install chromium
   ```

## Usage

### 1. Launch Chrome in Debug Mode

The scraper connects to an existing Chrome instance via the Chrome DevTools Protocol (CDP). You must launch Chrome with remote debugging enabled.

**Windows:**

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Linux / macOS:**

```bash
google-chrome --remote-debugging-port=9222
```

**Windows Subsystem for Linux (WSL):**
If you are running the scraper inside WSL, you should launch Chrome on the **Windows host** (using the command above). The scraper in WSL can then connect to the Windows host IP.

- Identify your Windows host IP: `cat /etc/resolv.conf | grep nameserver`
- In the GUI or script, update the CDP URL to `http://<WINDOWS_IP>:9222`

### 2. Run the Scraper

**GUI Version:**

```bash
python scraper_gui.py
```

**CLI Version:**

```bash
python scrape_thoughts_final.py
```

## WSL Specific Notes

- **GUI Support:** If you are using the `scraper_gui.py` inside WSL, ensure you have an X-Server (like GWSL or VcXsrv) installed and configured on Windows, or use WSLg (Windows 11).
- **Networking:** By default, `localhost:9222` inside WSL refers to the WSL instance itself. Since Chrome is usually running on the Windows side, use the Windows host IP address instead of `localhost`.
- **Permissions:** Ensure the `data/` directory has write permissions for your WSL user.

## Project Structure

- `scraper_gui.py`: Tkinter-based graphical interface.
- `scrape_thoughts_final.py`: Standalone CLI script.
- `pyproject.toml`: Project metadata and dependencies.
- `data/`: Default output directory for extracted thoughts.
