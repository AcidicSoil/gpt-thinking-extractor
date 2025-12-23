Context
- **Issue:** Scraper finds unique toggles (3 detected) but fails to extract content from them ("[Warning] Extracted data empty").
- **Diagnosis:** The failure is inside `extract_structured_content`.
    - It likely finds a container (otherwise "No visible thought container" warning).
    - But it finds 0 rows matching `THOUGHT_ROW`, or filtering removes them all.
- **Evidence:** `gui-output.md` shows the warning repeating 3 times, confirming the toggle interaction loop is working.

Success criteria
- **Visibility:** Logs confirm exactly which step of extraction fails (Container vs Rows vs Text).
- **Data:** Content is extracted from the "Universal Codebase Analyzer" threads.

Deliverables
- Updated `src/gpt_thinking_extractor/scraper_engine.py` with debug logging and relaxed row selectors.

Approach
1) **Add Debug Logs:**
   - In `extract_structured_content`:
     - Print "Container found: Yes/No".
     - Print "Row count: X".
     - Print "Visible row count: Y".
2) **Refine Selectors:**
   - Add `THOUGHT_ROW_CANDIDATES` to `selectors.json`.
   - Candidate 1: `div.relative.flex.w-full.items-start.gap-2` (Existing)
   - Candidate 2: `div.text-token-text-secondary` (Target text directly if wrapper fails)
   - Candidate 3: `div[data-testid]` (if available)
3) **Enhance Fallback:**
   - The current fallback to `raw_dump` only happens if `timeline` is empty AND `target_container` is valid.
   - We will ensure `raw_dump` tries harder (e.g. `body` innerText limited to the drawer area) if container logic is iffy.

Risks / unknowns
- **False Positives:** Relaxing row selectors might grab garbage UI text.
- **Console Noise:** Debug logs will be chatty; we'll use a `debug=True` flag or conditional print.

Testing & validation
- **Manual:** Run on the failing thread. Check console for "Row count".

Rollback / escape hatch
- Revert changes.

Owner/Date
- Unknown / 2025-12-22