Context
- **Issue 1:** "No visible thoughts found" during scrape, even after passing audit. This suggests the specific selector passed from Audit might be stale or the element is momentarily hidden/detached.
- **Issue 2:** Incomplete extraction ("stopped after five steps"). This points to the `scroll_container` logic being insufficient for long/lazy-loaded lists.
- **Current Scroll Logic:** Fixed loop of 5 scrolls with 0.5s sleep. This is too brittle for network-heavy lazy loading.

Success criteria
- **Resilient Toggle:** If the expected selector fails to find visible toggles, the scraper attempts all other candidates before giving up.
- **Complete Scrolling:** The scroll logic continues until the container height stops increasing (with a reasonable safety limit), ensuring all items are loaded.
- **Debug Visibility:** Logs confirm whether the scroll container was found and if scrolling is actually having an effect.

Deliverables
- Updated `src/gpt_thinking_extractor/scraper_engine.py` with:
    - Enhanced `scroll_container` (adaptive loop).
    - Robust `extract_ordered_content` (verify container visibility).
- Updated `src/gpt_thinking_extractor/scrape_thoughts_final.py` (and GUI) to retry selectors if the primary one fails.

Approach
1) **Enhance Scroll Logic (`scraper_engine.py`):**
   - Change loop to `while True` with `max_retries` (e.g., 20).
   - Scroll, Wait (1s), Check Height.
   - If height == prev_height for 3 consecutive attempts -> Stop.
   - Log "Scrolled to X pixels..." for debugging.
2) **Enhance Toggle Logic (`scrape_thoughts_final.py` / GUI):**
   - Wrap the toggle finding in a retry block.
   - If `visible_toggles` is empty, log warning and iterate through `THOUGHT_TOGGLE_CANDIDATES` again to find a fallback.
3) **Safety Check:**
   - In `extract_ordered_content`, count rows *before* and *after* scrolling to confirm new items were loaded.

Risks / unknowns
- **Infinite Scroll:** If the page has a glitch where height keeps changing, we might loop too long. `max_retries` handles this.
- **Wrong Container:** If we scroll the wrong div, we still won't get content. We need to validate `THOUGHT_CONTAINER` candidates.

Testing & validation
- **Manual:** Run on the problematic thread. Check logs for "Scrolled..." messages. Verify output file size.

Rollback / escape hatch
- Revert changes.

Owner/Date
- Unknown / 2025-12-22