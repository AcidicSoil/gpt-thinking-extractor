Context
- **Error:** "[Warning] Extracted text empty."
    - This happens when `extract_ordered_content` finds no matching rows (`THOUGHT_ROW`) inside the container, or the specific text/code selectors inside the rows fail.
    - Since the container *was* found (otherwise we'd get a different warning), the issue is likely the **Row Selector** specificity.
- **Requirement:** Capture "Thought Duration" (e.g., "Thought for 10m 19s").
    - This information is visible on the toggle button itself.

Success criteria
- **No Empty Files:** If structured row extraction fails, the scraper falls back to a raw text dump of the container (`innerText`), ensuring data is always captured.
- **Duration Capture:** The "Thought for X" text is extracted from the toggle and saved as metadata in the output file header.

Deliverables
- Updated `src/gpt_thinking_extractor/scraper_engine.py` (Fallback logic, Metadata support).
- Updated `src/gpt_thinking_extractor/scrape_thoughts_final.py` & `scraper_gui.py` (Pass duration to engine).

Approach
1) **Enhance `extract_ordered_content`:**
   - If `rows` loop yields empty `extracted_text`:
     - Log "Row extraction failed, attempting raw container dump."
     - `raw_text = target_container.inner_text()`
     - Return `raw_text` (labeled as "[RAW DUMP]").
2) **Capture Duration:**
   - In `scrape_page_thoughts` (CLI/GUI):
     - Before clicking, `duration = toggle.inner_text().split('\n')[0]` (clean up newlines).
     - Pass `duration` to `engine.save_thought`.
3) **Update `save_thought`:**
   - Accept `duration` arg.
   - Write `Duration: {duration}\n\n` at the top of the file.

Risks / unknowns
- **Raw Dump Quality:** Raw dump won't separate code blocks nicely (no ` ``` ` fencing), but it's better than empty.
- **Toggle Text:** Sometimes the toggle text changes state (e.g., "Finished" vs "Thought for..."). We grab whatever is visible at click time.

Testing & validation
- **Manual:** Run on the thread that produced the empty warning. Check if file now has content.
- **Manual:** Verify file header has "Duration: ...".

Rollback / escape hatch
- Revert changes.

Owner/Date
- Unknown / 2025-12-22
