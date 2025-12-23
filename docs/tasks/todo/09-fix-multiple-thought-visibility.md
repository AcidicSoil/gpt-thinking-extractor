Context
- **Issue:** "No visible thoughts found" or missing thoughts when multiple exist in a single thread.
- **Cause:**
    - ChatGPT threads lazy-load messages as you scroll.
    - Playwright's `locator.all()` only captures elements currently in the DOM.
    - `is_visible()` returns false for off-screen elements in some contexts, causing `get_unique_toggles` to discard valid (but off-screen) thoughts.
- **Evidence:** User report "not finding the element when there's more than one".

Success criteria
- **Full Discovery:** The scraper finds ALL "Thought" toggles in a long conversation, not just the currently visible ones.
- **Scraping:** Successfully iterates through multiple thoughts in sequence.

Deliverables
- Updated `src/gpt_thinking_extractor/scraper_engine.py` with `scan_page_for_toggles`.

Approach
1) **Implement Main Page Scroll:**
   - Add `scroll_chat_to_bottom(page)` to `ScraperEngine`.
   - Logic: Scroll `main` or `html` element incrementally to trigger lazy loading of all messages.
   - Wait for `networkidle` or stability between scrolls.
2) **Update Discovery Logic:**
   - In `scrape_page_thoughts` (CLI/GUI), call `scroll_chat_to_bottom` *before* querying for toggles.
   - Or, query, scroll to last, query again until count stabilizes.
3) **Refine `get_unique_toggles`:**
   - If `is_visible()` is too strict for off-screen elements, rely on `scroll_into_view_if_needed()` *during* the click loop, rather than filtering upfront.
   - We still need to filter *duplicates* (nested divs), but maybe relax the "must be visible right now" constraint for the *list* generation.

Risks / unknowns
- **Memory:** Very long threads might be slow to scroll.
- **Detached Elements:** Scrolling up/down might detach top elements (virtualization).
    - *Mitigation:* We might need to scroll-and-scrape in passes (find current, scrape, scroll down, find new, scrape).

Testing & validation
- **Manual:** Open a long thread with multiple thoughts. Verify count > 1.

Rollback / escape hatch
- Revert changes.

Owner/Date
- Unknown / 2025-12-22