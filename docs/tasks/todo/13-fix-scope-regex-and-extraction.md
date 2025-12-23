Context
- **Scope Error:** `active_project_id` captures the full slug (`g-p-UUID-name`), but sidebar links only contain `g-p-UUID`. String matching fails.
- **Extraction Error:** "Extracted data empty" implies the container is empty or not found.
- **Evidence:** Logs showing "Skipping link (Scope mismatch)" for valid links.

Success criteria
- **Scope Matching:** The scraper correctly identifies links belonging to the active project, regardless of whether the URL contains the name slug.
- **Content Capture:** The scraper waits long enough for the drawer to populate or finds the correct container.

Deliverables
- Updated `src/gpt_thinking_extractor/scraper_engine.py`:
    - Refined `extract_project_id` regex.
    - Increased wait/stability checks in extraction.

Approach
1) **Fix Regex:**
   - Change regex from `g-p-[a-zA-Z0-9-]+` (greedy, grabs name) to `g-p-[a-f0-9]{32}` (assuming 32-char hex UUID) OR `g-p-[a-f0-9]+(?=-|/)` to stop at the separator.
   - Actually, looking at the log: `g-p-69407bf8ed248191abe7f211741f7db9`. It looks like a standard hex string.
   - New Regex: `(g-p-[a-f0-9]+)` works if we don't match the hyphen-name.
2) **Fix Extraction:**
   - In `scrape_page_thoughts` (GUI/CLI), increase post-click wait to 2000ms.
   - In `extract_structured_content`, add a check: if container found, print its `innerHTML` length to debug log.

Risks / unknowns
- **UUID Format:** Is `g-p-` always followed by hex? The "transcript cleaner" ID looks hex. The "universal codebase analyzer" ID looks hex.

Testing & validation
- **Manual:** Run scan. Verify sidebar links are NOT skipped.

Rollback / escape hatch
- Revert regex.

Owner/Date
- Unknown / 2025-12-22