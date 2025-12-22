Context
- The user requires a strict, interactive workflow centered on the **Active Project**.
- **Current Behavior:** The scraper auto-navigates to global, scans everything, and immediately attempts to scrape, but currently fails to find thoughts ("No thoughts found" in 6 threads).
- **New Requirement 1 (Project Focus):** Work explicitly within the parent project context first. Navigate back and forth through its child threads.
- **New Requirement 2 (Optional Global):** Global navigation/scanning should be optional and disabled by default to prevent "out of control" scraping.
- **New Requirement 3 (Audit & Confirm):**
    1.  Scan for thread links in the project.
    2.  **Audit Phase:** Visit each thread, **count** the matches for "Thought" elements (do not save yet).
    3.  **Report & Prompt:** Display the counts to the user (e.g., "Thread A: 5 thoughts, Thread B: 0 thoughts").
    4.  **Confirmation:** Wait for user approval to proceed with saving the data.
- **Root Cause of "No thoughts found":** The `gui-output.md` shows 0 thoughts found despite finding threads. This implies the `THOUGHT_TOGGLE` selector (`div.truncate:has-text("Thought for")`) is failing or the wait timing is insufficient. The "Audit Phase" is the perfect mechanism to debug this visibility issue without generating empty files.

Success criteria
- **Audit Mode:** The system visits threads and accurately counts "Thought" toggles without saving data.
- **Interactive UI/CLI:** The user is presented with a summary (`Thread ID -> Thought Count`) and must explicitly confirm to proceed.
- **Optional Global Scan:** The "Navigate to Global" step is disabled by default and controlled via a flag/checkbox.
- **Fix "No Thoughts" Issue:** The audit phase reliably detects thought elements (likely requiring selector refinement or better wait logic).

Deliverables
- Updated `scrape_thoughts_final.py` (CLI) with `--audit` flow and `--global` flag.
- Updated `scraper_gui.py` (GUI) with an "Audit & Scrape" button and "Include Global" checkbox.
- Refined `THOUGHT_TOGGLE` selector in `selectors.json` (likely needs to be more generic or robust).

Approach
1) **Selector Refinement:**
   - Relax `THOUGHT_TOGGLE` to `div:has-text("Thought for")` or similar to ensure we aren't missing it due to class name changes (`truncate` might be gone).
2) **Implement Audit Logic:**
   - Create `audit_project_threads(engine, page, thread_urls)` function.
   - For each URL: `goto(url)` -> `wait_for_selector` -> `count(THOUGHT_TOGGLE)`.
   - Return list of `(url, count)`.
3) **Update CLI Workflow:**
   - Step 1: Context Scan (Active Project).
   - Step 2: (Optional) Global Scan.
   - Step 3: **Audit Loop**: Run audit on found URLs. Print table.
   - Step 4: `input("Proceed with scraping? [y/N]")`.
   - Step 5: If Yes, run `scrape_page_thoughts` (which saves data).
4) **Update GUI Workflow:**
   - Add "Audit Project" button.
   - On click: Run Audit -> Show Popup with Table -> "Scrape" or "Cancel".
   - Add "Include Global Search" checkbox (Unchecked by default).

Risks / unknowns
- **Double Traffic:** Visiting every thread to count, then visiting again to scrape doubles the network requests and time.
  - *Mitigation:* We will accept this trade-off for correctness/safety as requested.
- **Selector Fragility:** If the selector is wrong, the Audit will still show "0 thoughts".
  - *Mitigation:* We will test multiple selector variations in the Audit phase if count is 0.

Testing & validation
- **Manual Test:** Run Audit on "Gemini CLI" project. Verify it reports > 0 thoughts for known threads.
- **Confirmation Flow:** Verify clicking "Cancel" aborts the process.
- **Global Flag:** Verify global navigation does NOT happen unless requested.

Rollback / escape hatch
- Revert script changes to previous commit.

Owner/Date
- Unknown / 2025-12-22