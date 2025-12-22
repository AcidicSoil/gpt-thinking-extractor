# Codebase Strategy Questions

## Immediate Exploration (High ROI, Fixes Reliability & Debt)

1. **Why is the core scraping logic duplicated between `scrape_thoughts_final.py` and `scraper_gui.py`?**
   - **Reference:** `scrape_thoughts_final.py:scrape_page_thoughts` vs `scraper_gui.py:run_scraper`
   - **Rationale:** Any fix to selectors or logic must be applied twice, doubling maintenance effort and risk of divergence.
   - **Experiment:** Run `diff scrape_thoughts_final.py scraper_gui.py` to identify exact distinct lines.

2. **How can we externalize `TOGGLE_SELECTOR` and `CONTENT_SELECTOR` to a config file?**
   - **Reference:** `scrape_thoughts_final.py:TOGGLE_SELECTOR`
   - **Rationale:** Hardcoded selectors make the scraper brittle to minor UI changes by the target site; config allows hot-fixes.
   - **Experiment:** Create a `selectors.json` file and try reading `TOGGLE_SELECTOR` from it in a Python shell.

3. **Can `time.sleep(2.5)` be replaced with explicit `wait_for_selector` or state checks?**
   - **Reference:** `scraper_gui.py:run_scraper` (Line 161)
   - **Rationale:** Fixed sleeps are flaky on slow connections and wasteful on fast ones; explicit waits are robust.
   - **Experiment:** Replace `time.sleep(2.5)` with `page.wait_for_load_state("networkidle", timeout=3000)` and measure success rate.

4. **Why is `SCRAPED_URLS` in-memory only, causing re-scraping of processed threads upon restart?**
   - **Reference:** `scrape_thoughts_final.py:SCRAPED_URLS`
   - **Rationale:** Users losing progress on crash or restart wastes significant time and bandwidth.
   - **Experiment:** Write a 5-line script to check if a local `scraped_urls.txt` exists and load it into a set.

5. **Is `safe_thread_id = thread_id.split('/')[-1]` robust enough for Windows filenames?**
   - **Reference:** `scraper_gui.py:save_thought_data`
   - **Rationale:** URL slugs can contain characters illegal in NTFS (e.g., `:`, `?`) or be excessively long.
   - **Experiment:** Call `save_thought_data` with a mock `thread_id` containing `foo:bar` and check if it crashes.

6. **Does `ScraperApp.log` handle race conditions when called from the background thread?**
   - **Reference:** `scraper_gui.py:ScraperApp.log`
   - **Rationale:** Tkinter widgets are generally not thread-safe; calling `config` from a worker thread can cause crashes.
   - **Experiment:** Create a loop that calls `app.log` 100 times from a thread and observe if the UI freezes or errors.

7. **How does the system behave if `p.chromium.connect_over_cdp` hangs?**
   - **Reference:** `scrape_thoughts_final.py:run`
   - **Rationale:** Network glitches or a zombie Chrome process could cause the script to hang indefinitely without feedback.
   - **Experiment:** Run the script with `CDP_URL` set to a non-existent IP and time how long it takes to fail.

8. **Where are the unit tests for `save_thought_data`?**
   - **Reference:** `Unknown:tests/` (Missing directory)
   - **Rationale:** File encoding and path logic are critical for data integrity and should be verified automatically.
   - **Experiment:** Run `pytest` in the root directory to confirm no tests are discovered.

9. **Does `scrape_page_thoughts` mask `KeyboardInterrupt` with its broad exception handler?**
   - **Reference:** `scrape_thoughts_final.py:scrape_page_thoughts`
   - **Rationale:** Catching `Exception` prevents the user from cleanly aborting the script with Ctrl+C during a loop.
   - **Experiment:** Add a `raise KeyboardInterrupt` inside the `try` block and see if it's caught as a generic error.

10. **Can `open_data_folder` support Linux desktop environments beyond `xdg-open`?**
    - **Reference:** `scraper_gui.py:open_data_folder`
    - **Rationale:** Fallback reliability ensures the "Open Folder" button works across diverse Linux setups.
    - **Experiment:** Check for `xdg-open` presence with `which xdg-open` in the terminal.

11. **Is `toggle.scroll_into_view_if_needed()` sufficient for lazy-loaded virtual lists?**
    - **Reference:** `scrape_thoughts_final.py:scrape_page_thoughts`
    - **Rationale:** Complex SPAs often detach DOM elements; simple scrolling might not trigger re-hydration.
    - **Experiment:** Manually scroll a long thread in the browser and watch if "Thought" toggles disappear/reappear from the DOM.

12. **Why is `OUTPUT_FOLDER` logic coupled to `dotenv` instead of command-line args?**
    - **Reference:** `scrape_thoughts_final.py:DATA_FOLDER`
    - **Rationale:** CLI args offer better composability for automation scripts than editing a `.env` file.
    - **Experiment:** Run `python scrape_thoughts_final.py --output=./test` and verify it ignores the flag (fails).

## Strategic Planning (Long-term Stability & Features)

13. **Can we refactor `ScraperApp` to use a shared `ScraperEngine` class?**
    - **Reference:** `scraper_gui.py:ScraperApp`
    - **Rationale:** Decoupling UI from logic allows for headless CLI, GUI, and potential API wrappers to share a single, tested core.
    - **Experiment:** Create a `engine.py` file, move `save_thought_data` there, and import it in `scrape_thoughts_final.py`.

14. **Should we implement a local SQLite database instead of flat files?**
    - **Reference:** `scraper_gui.py:save_thought_data`
    - **Rationale:** A DB enables querying, easier resumption, de-duplication, and structured metadata storage.
    - **Experiment:** Create a prototype `sqlite3` script that creates a table for `thoughts` and inserts one record.

15. **Could `playwright` manage the browser instance directly?**
    - **Reference:** `scrape_thoughts_final.py:run`
    - **Rationale:** Removing the requirement for a pre-launched Chrome instance lowers the barrier to entry for users.
    - **Experiment:** Modify `run` to use `p.chromium.launch_persistent_context` instead of `connect_over_cdp`.

16. **Is it feasible to parallelize processing of `all_chat_urls`?**
    - **Reference:** `scrape_thoughts_final.py:run` (Loop over `sorted_urls`)
    - **Rationale:** Serial scraping is slow; async processing could significantly reduce runtime for large histories.
    - **Experiment:** Benchmark processing 5 threads serially vs. using `asyncio.gather` with dummy sleeps.

17. **Can we implement a "dry-run" mode to validate selectors?**
    - **Reference:** `scrape_thoughts_final.py:run`
    - **Rationale:** Validating selectors against the current site structure before starting a long scrape prevents wasted time.
    - **Experiment:** Add a `--dry-run` flag that prints found counts but skips `save_thought_data`.

18. **Should the scraper emit structured events for observability?**
    - **Reference:** `scrape_thoughts_final.py:print`
    - **Rationale:** Structured logs (JSON) allow for easier parsing and monitoring of scrape health/progress.
    - **Experiment:** Replace one `print` statement with `logging.info(json.dumps({...}))`.

19. **How can we update selectors remotely without code deployment?**
    - **Reference:** `scrape_thoughts_final.py:SIDEBAR_PROJECT_SELECTOR`
    - **Rationale:** Fetching a config JSON from a remote URL on startup would allow instant fixes for broken selectors.
    - **Experiment:** Write a snippet to `requests.get` a raw JSON file from GitHub and parse a selector.

20. **How can we package this as a standalone executable?**
    - **Reference:** `pyproject.toml`
    - **Rationale:** Non-technical users struggle with Python/Pipenv setup; an `.exe`/`AppImage` simplifies distribution.
    - **Experiment:** Run `pyinstaller --onefile scraper_gui.py` and test the resulting binary size/startup.
