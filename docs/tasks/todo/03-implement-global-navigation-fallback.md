Context
- The scraper currently respects the user's active context. If started inside a Project, it only sees that Project's sidebar.
- The user has explicitly requested ("yes") that the scraper should *also* attempt to navigate back to the global view to scan all projects, even if it starts inside a specific one.
- This ensures a comprehensive scrape (Current Project + All Other Projects + Recent History) regardless of the starting URL.

Success criteria
- If the scraper starts in a Project context (`/g/g-p-...`), it first scans/queues the threads visible in that context.
- After scanning the active project, the scraper automatically navigates to the global root (`https://chatgpt.com`).
- Once at the global root, it performs a full scan of the "Projects" list and "Recent" history.
- All discovered URLs (Project-specific and Global) are aggregated and deduplicated before the scraping phase begins.

Deliverables
- Updated `src/gpt_thinking_extractor/scrape_thoughts_final.py` (CLI) implementing the "Scan & Navigate" workflow.
- Updated `src/gpt_thinking_extractor/scraper_gui.py` (GUI) implementing the same workflow.
- Updated `src/gpt_thinking_extractor/scraper_engine.py` (if shared navigation logic is needed).

Approach
1) **Phase 1: Initial Context Scan**
   - Check `page.url`.
   - If in Project (`/g/`): Scan visible sidebar threads (`SIDEBAR_THREAD`) and add to `all_chat_urls`. Log "Scanned active project."
   - If in Thread (`/c/`): Add current URL.
2) **Phase 2: Global Navigation**
   - Check if we are already at Global Root. If not:
     - Log "Navigating to Global View for full scan..."
     - `page.goto("https://chatgpt.com")`
     - `page.wait_for_load_state("networkidle")`
3) **Phase 3: Global Scan**
   - Scan `SIDEBAR_PROJECT` to find all available projects.
   - Scan `SIDEBAR_THREAD` (Recent History) to find standard chats.
   - Add all distinct URLs to `all_chat_urls`.
4) **Phase 4: Project Iteration (Existing Logic)**
   - Iterate through the discovered Project URLs (from Phase 3), navigate to them, and scan their threads.
5) **Phase 5: Execution**
   - Process the final deduplicated list of `all_chat_urls`.

Risks / unknowns
- **Navigation Timing:** Navigating to root might take time or trigger Cloudflare checks. We need robust waits.
- **Session State:** Navigating away *shouldn't* log the user out, but we must ensure the session is preserved (Playwright CDP handles this naturally).
- **Duplicate Scans:** The active project might be listed in the Global "Projects" list. Deduplication logic (Set) handles this, but we should verify.

Testing & validation
- **Test Case 1:** Start inside "Project A".
    - Verify "Project A" threads are found.
    - Verify navigation to `chatgpt.com`.
    - Verify "Project B" and "Recent History" are found.
- **Test Case 2:** Start at Global Root.
    - Verify navigation step is skipped (or is a no-op).
    - Verify standard scan proceeds.

Rollback / escape hatch
- Revert logic in `scrape_thoughts_final.py` and `scraper_gui.py` to remove the automatic navigation step.

Owner/Date
- Unknown / 2025-12-22