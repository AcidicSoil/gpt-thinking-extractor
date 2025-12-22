# GPT Thinking Extractor

Tools to scrape and extract the "Thinking" process data from ChatGPT threads and projects.

## Prerequisites

- Python 3.13+
- Chrome/Chromium browser (for remote debugging)

## Installation

1. **Clone the repository:**
   ```bash
   git clone <repository_url>
   cd gpt-thinking-extractor
   ```

2. **Create and activate a virtual environment (Optional but recommended):**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install the package:**
   ```bash
   pip install .
   ```

4. **Install Playwright browsers:**
   ```bash
   playwright install chromium
   ```

## Usage

### 1. Launch Chrome in Debug Mode

The scraper connects to an existing Chrome instance via the Chrome DevTools Protocol (CDP). You must launch Chrome with remote debugging enabled and ensure you are **logged in to ChatGPT**.

**Windows:**
```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222
```

**Linux / macOS:**
```bash
google-chrome --remote-debugging-port=9222
```

**Windows Subsystem for Linux (WSL):**
If you are running the scraper inside WSL, launch Chrome on the **Windows host** (using the command above). The scraper in WSL needs to connect to the Windows host IP.
- Identify your Windows host IP: `cat /etc/resolv.conf | grep nameserver`
- In the GUI configuration, update the CDP URL to `http://<WINDOWS_IP>:9222`

### 2. Run the Scraper

After installation, two commands are available in your shell:

**GUI Version (Recommended):**
```bash
gpt-scrape-gui
```
*Provides a graphical interface to monitor progress and stop the scraper easily.*

**CLI Version:**
```bash
gpt-scrape
```
*Runs the scraping process in the terminal.*

## Configuration & Persistence

- **Selectors:** The scraper uses a `selectors.json` file (located in the package) to find elements on the page. You can modify this if ChatGPT's UI changes.
- **Persistence:** Scraped URLs are tracked in a local SQLite database (`scraped_urls.db`) to prevent re-scraping the same threads after a restart.
- **Output:** By default, data is saved to the `data/` folder in your current working directory.

## Development

If you want to modify the code or run it without installing:

1. **Install dev dependencies:**
   ```bash
   pip install -e .[dev]
   ```

2. **Run tests:**
   ```bash
   pytest tests/
   ```

3. **Run scripts directly:**
   ```bash
   # Make sure to set PYTHONPATH to src
   export PYTHONPATH=$PYTHONPATH:$(pwd)/src
   python src/gpt_thinking_extractor/scraper_gui.py
   ```

## WSL Specific Notes

- **GUI Support:** To use `gpt-scrape-gui` inside WSL, ensure you have an X-Server (like GWSL or VcXsrv) installed on Windows, or use WSLg (Windows 11).
- **Networking:** By default, `localhost:9222` inside WSL refers to the WSL instance itself. Use the Windows host IP if Chrome is running on Windows.
- **Permissions:** Ensure the output directory has write permissions.

## Project Structure

- `src/gpt_thinking_extractor/`: Source code package.
  - `scraper_engine.py`: Core logic for scraping, persistence, and file I/O.
  - `scraper_gui.py`: Tkinter-based graphical interface.
  - `scrape_thoughts_final.py`: Standalone CLI entry point.
  - `selectors.json`: Externalized CSS selectors configuration.
- `tests/`: Unit tests.
- `data/`: Default output directory for extracted thoughts.
- `scraped_urls.db`: SQLite database tracking processed URLs.

```bash
/mnt/c/Program\ Files/Google/Chrome/Application/chrome.exe   --remote-debugging-address=0.0.0.0   --remote-debugging-port=9222   --user-data-dir=/tmp/chrome-cdp   --no-first-run --no-default-browser-check
```


```ps
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-address=0.0.0.0 `
  --remote-debugging-port=9222 `
  --user-data-dir="$env:LOCALAPPDATA\Google\Chrome\User Data" `
  --profile-directory="Default"

```
