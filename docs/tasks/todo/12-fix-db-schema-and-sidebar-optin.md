Context
- **DB Error:** `table scraped_urls has no column named title`. The local DB is stale (schema drift).
- **Extraction Error:** `[Warning] No visible thought container found.` The drawer isn't appearing or being detected fast enough.
- **Workflow Change:** User wants sidebar scanning (finding *other* threads in the project) to be **optional/opt-in**. Default should likely be "Current Page Only".

Success criteria
- **DB Auto-Migration:** The engine automatically adds the `title` column to existing databases without crashing.
- **Container Robustness:** The scraper retries finding the drawer container to handle animation delays.
- **Opt-in Scanning:** Sidebar scanning is disabled by default; only the active thread is audited unless the user checks "Scan Project Sidebar".

Deliverables
- Updated `src/gpt_thinking_extractor/scraper_engine.py`:
    - `_migrate_db()` method.
    - Retry loop in `extract_structured_content`.
- Updated `src/gpt_thinking_extractor/scrape_thoughts_final.py` & `scraper_gui.py`:
    - Logic to skip sidebar scan unless flag/checkbox is set.

Approach
1) **Fix DB Schema:**
   - In `_init_db`: Check if `title` column exists. If not, run `ALTER TABLE scraped_urls ADD COLUMN title TEXT`.
2) **Fix Container Visibility:**
   - In `extract_structured_content`: Wrap the "Find Container" logic in a `for attempt in range(3):` loop with `time.sleep(1)`.
   - Add `div[role="dialog"]` to container candidates as a fallback.
3) **Implement Opt-in Scanning:**
   - **GUI:** Add "Scan Sidebar for More Threads" checkbox (Default: Unchecked).
   - **CLI:** Add `--scan-sidebar` flag.
   - **Logic:** If `scan_sidebar` is False, skip the `SIDEBAR_THREAD` loop and just add `page.url` (if it matches scope).

Risks / unknowns
- **Container Selector:** If `div.h-full...` is wrong, retries won't help. We rely on the Geometry fallback which should be robust.

Testing & validation
- **Manual:** Run on a machine with an old `.db` file. Verify no crash.
- **Manual:** Run without "Scan Sidebar". Verify only 1 thread is audited.

Rollback / escape hatch
- Revert changes.

Owner/Date
- Unknown / 2025-12-22