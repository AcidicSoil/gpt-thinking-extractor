Context
- **Scope Issue:** Scraper must strictly stay within the starting Project ID (`g-p-...`).
- **Missing Data:** User needs Chat Titles in the UI, not just UUIDs.
- **Accuracy Issue:** Audit reports inflated counts (16 vs 1 actual).
- **Extraction Failure:** Scraper times out waiting for thought content (`Locator.inner_text: Timeout`), implying the content selector is wrong or the toggle didn't work.
- **URL Shape:** `https://chatgpt.com/g/<PROJECT_ID>/c/<THREAD_ID>`

Success criteria
- **Strict Scoping:** Only scrape threads containing the current Project ID in their URL.
- **Titles:** Display "Thread Title" in the Audit table and GUI selection dialog.
- **Accurate Counts:** Report the true number of thought blocks (1 instead of 16).
- **Reliable Extraction:** Successfully click the toggle and read the text without timeout.

Deliverables
- Updated `src/gpt_thinking_extractor/selectors.json` (Refined/Stricter selectors).
- Updated `scraper_engine.py` (Title extraction, Scoping logic).
- Updated `scrape_thoughts_final.py` & `scraper_gui.py` (UI updates for titles).

Approach
1) **Strict Scoping:**
   - Extract `project_id` from the starting URL (regex: `g-p-[a-f0-9]+`).
   - When scanning sidebar, filter links: `if project_id in href`.
   - If in a child thread, parse parent ID from current URL to set the scope.
2) **Title Extraction:**
   - In `scan_sidebar`, grab `element.inner_text()` along with `href`.
   - Store as `{"url": url, "title": title}` in `all_chat_threads`.
3) **Fixing Counts (The "16 vs 1" issue):**
   - The current selector `div:has-text("Thought for")` is likely matching every parent div up the DOM tree.
   - **Fix:** Use a strictly leaf-node selector or `locator.first` logic.
   - Refine `THOUGHT_TOGGLE` to `div.truncate:has-text("Thought for")` (original) or `button`.
   - **Action:** We will verify uniqueness by checking `count()` on a specific class if possible.
4) **Fixing Extraction Timeout:**
   - The error `waiting for locator("...").last` suggests the content never appeared.
   - **Fix:** Update `THOUGHT_CONTENT` selector. It might be that the content is *sibling* to the toggle, not inside a specific `text-token-text-secondary` container in the way we expect.
   - Add logic to wait for the *expansion* animation (e.g., check for `aria-expanded="true"` if applicable).

Risks / unknowns
- **Selector Specificity:** Without a new DOM dump, we are guessing at the correct "tight" selector.
- **Virtual DOM:** If the list is virtual, "16" might be the total number of items *loaded* in memory, even if not visible? Unlikely for "Thought" toggles usually.

Testing & validation
- **Manual:** Run Audit on the specific thread mentioned in logs. Should show "1".
- **Manual:** Verify titles appear in the list.
- **Manual:** Verify scrape saves the file.

Rollback / escape hatch
- Revert to previous commit.

Owner/Date
- Unknown / 2025-12-22