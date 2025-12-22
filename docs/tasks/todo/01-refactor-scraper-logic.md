Context
- Core scraping logic is duplicated between `scrape_thoughts_final.py` (`scrape_page_thoughts`) and `scraper_gui.py` (`run_scraper`), doubling maintenance effort.
- CSS selectors (`TOGGLE_SELECTOR`, `CONTENT_SELECTOR`, etc.) are hardcoded in both files (`scrape_thoughts_final.py:TOGGLE_SELECTOR`), making the scraper brittle to target site changes.
- `SCRAPED_URLS` is in-memory only (`scrape_thoughts_final.py:SCRAPED_URLS`), causing re-scraping of already processed threads after a restart.
- Thread ID sanitization (`thread_id.split('/')[-1]`) in `scraper_gui.py:save_thought_data` is likely insufficient for Windows filenames (e.g., handling invalid characters).
- Explicit `time.sleep(2.5)` calls (`scraper_gui.py:run_scraper`) are unreliable; they should be replaced with `wait_for` logic.
- No unit tests exist (`Unknown:tests/`), increasing regression risk during refactoring.

Success criteria
- A shared `ScraperEngine` class encapsulates core logic, used by both CLI and GUI scripts.
- Selectors are loaded from an external `selectors.json` file.
- Scraped URLs are persisted to a local file (`scraped_urls.txt` or `scraped.json`) to allow resumption.
- Filenames derived from thread IDs are sanitized to be safe for all filesystems (Windows/Linux/macOS).
- Fixed sleep delays are replaced with Playwright's `wait_for_selector` or `wait_for_load_state`.

Deliverables
- `selectors.json`: Configuration file for CSS selectors.
- `scraper_engine.py`: New module containing the shared scraping logic, state management, and file I/O.
- Updated `scrape_thoughts_final.py`: Refactored to import and use `ScraperEngine`.
- Updated `scraper_gui.py`: Refactored to import and use `ScraperEngine` (ensuring UI updates remain thread-safe).
- `tests/test_engine.py`: Basic unit tests for file saving and sanitization.

Approach
1) Extract hardcoded selectors from `scrape_thoughts_final.py` into a new `selectors.json` file.
2) Create `scraper_engine.py` and implement a `ScraperEngine` class:
   - Move `save_thought_data` logic here and add robust filename sanitization (replace invalid chars).
   - Implement loading/saving of `SCRAPED_URLS` to a persistence file.
   - Implement `load_selectors` to read from `selectors.json`.
3) Refactor `scrape_thoughts_final.py` to remove duplicate logic and instantiate `ScraperEngine`.
4) Refactor `scraper_gui.py` to use `ScraperEngine`:
   - Ensure `log` callbacks or event emitters are used so the engine can report progress to the Tkinter UI without freezing it.
5) Replace `time.sleep(2.5)` in the engine with `page.wait_for_load_state("domcontentloaded")` or specific selector waits.
6) Add `tests/` directory and create a test for `save_thought_data` sanitization logic.

Risks / unknowns
- **Tkinter Thread Safety:** Refactoring `scraper_gui.py` might introduce race conditions if the engine calls UI methods directly from a background thread (`scraper_gui.py:ScraperApp.log`).
- **Selector Validity:** Moving selectors to JSON doesn't validate them; invalid JSON could crash the app at startup.
- **Windows Path Length:** Even with sanitization, deep folder paths + long thread IDs might exceed Windows MAX_PATH.

Testing & validation
- **Unit Test:** Run `pytest` on `tests/test_engine.py` to verify filename sanitization and selector loading.
- **Manual CLI Test:** Run `python scrape_thoughts_final.py` and verify it reads `selectors.json` and skips already scraped URLs.
- **Manual GUI Test:** Run `python scraper_gui.py`, start a scrape, and verify logs appear and the UI remains responsive.

Rollback / escape hatch
- `git checkout .` to revert changes to the Python scripts.
- Delete `selectors.json` and `scraper_engine.py` if the refactor fails.

Owner/Date
- Unknown / 2025-12-22