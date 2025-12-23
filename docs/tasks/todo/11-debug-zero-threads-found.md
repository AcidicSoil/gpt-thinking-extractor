Context
- **Issue:** "No threads found to audit" persists.
- **Network:** User confirms `localhost` works (ignore WSL host IP advice).
- **State:** Scraper connects but fails to find Project ID or any threads.
    - "No active project ID" -> URL regex `g-p-...` failed.
    - "No threads found" -> `SIDEBAR_THREAD` selector returned 0 elements.

Success criteria
- **Diagnose URL:** Capture exactly what URL the scraper sees (is it a redirect? login page?).
- **Diagnose DOM:** Capture the HTML of the page when scanning fails to verify if the sidebar exists and what its structure is.

Deliverables
- Updated `src/gpt_thinking_extractor/scraper_gui.py` with:
    - URL logging.
    - Page title logging (detect "Log in").
    - HTML dump on failure (`debug_page_dump.html`).

Approach
1) **Instrumentation:**
   - Log `page.url` and `page.title()` at the start of `run_audit_pipeline`.
   - If `all_chat_threads` is empty at the end of scanning:
     - Log "Dumping page content to debug_dump.html..."
     - Save `page.content()` to file.
2) **Logic Check:**
   - Verify if `SIDEBAR_THREAD` selector (`nav a[href*="/c/"]`) is still valid in the dumped HTML.

Risks / unknowns
- **Sensitive Data:** The dump might contain chat snippets. User should be aware (it's local).

Testing & validation
- **Manual:** Run scraper. If it fails, check `debug_dump.html`.

Rollback / escape hatch
- Revert changes.

Owner/Date
- Unknown / 2025-12-22