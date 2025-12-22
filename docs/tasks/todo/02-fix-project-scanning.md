Context
- The scraper currently fails to detect projects when scanning from an active project page (URL pattern: `https://chatgpt.com/g/g-p-.../project`).
- It also fails to pick up the active thread if it's a child of a project (URL pattern: `https://chatgpt.com/g/g-p-.../c/...`).
- `gui-output.md` confirms "Found 0 projects" and immediate termination, proving the current selectors (`nav a[href*="/project/"]`) or logic are insufficient for these contexts.
- User provided specific URL shapes in `project-example-urls.md`:
    - Parent: `.../g/g-p-.../project`
    - Child: `.../g/g-p-.../c/<UUID>`
- Screenshots show:
    - `project-sidebar-element.png`: Likely the link to a project or thread in the sidebar.
    - `project-chat-thread-child-element.png`: `li` elements representing threads.
    - `thought-element.png`: The thought bubble structure.

Success criteria
- The scraper correctly identifies "Project Parent" pages (`/project`) and scans their sidebar for child threads.
- The scraper correctly identifies "Project Child" threads (`/c/` inside a `/g/` path) and adds them to the queue.
- The scraper falls back to scanning "Recent" history (`nav a[href*="/c/"]`) if no project-specific threads are found.
- The scraper successfully extracts thoughts from the "Active Thread" even if sidebar scanning returns 0 results.

Deliverables
- Updated `selectors.json` with refined keys:
    - `SIDEBAR_PROJECT`: `nav a[href*="/project"]` (Refined to match `/g/.../project`)
    - `SIDEBAR_THREAD`: `nav a[href*="/c/"]` (Captures both standard and project-child threads)
- Updated `scraper_engine.py` to support these new keys.
- Updated `scrape_thoughts_final.py` (CLI) and `scraper_gui.py` (GUI) with:
    - **Context Awareness:** Check `page.url` at startup to determine if we are inside a project or thread.
    - **Smart Fallback:** If `scan_sidebar` yields 0 results, add the current page to the queue.

Approach
1) **Update Selectors:**
   - Verify `SIDEBAR_PROJECT` matches the new `.../project` suffix.
   - Add `SIDEBAR_THREAD` as `nav a[href*="/c/"]` to catch all chat links (Project children and Recent history).
2) **Implement Context Detection (Phase 0):**
   - In `run`/`run_scraper`, checks `page.url`.
   - If `"/project"` in url: We are at the root of a project. Scan sidebar for `SIDEBAR_THREAD`.
   - If `"/c/"` in url: We are in a specific thread. Add `current_url` to `all_chat_urls` immediately.
3) **Refine Scanning Logic (Phase 1):**
   - Use `SIDEBAR_PROJECT` to find *other* projects (if visible).
   - Use `SIDEBAR_THREAD` to find all visible threads (Recent or Project-scoped).
   - Deduplicate results.
4) **Safety Net:**
   - If `len(all_chat_urls) == 0` and current URL looks like a thread (matches `/c/`), add it.
   - Log explicit warnings if no threads are found but we proceed with the current page.

Risks / unknowns
- **Sidebar Visibility:** Does the "Recent" history disappear completely when inside a Project? If so, we can only scrape the active project's threads.
- **Selector Overlap:** `href*="/c/"` is very broad. It might match other UI elements. We will rely on it being inside `nav`.
- **Project Switching:** Can we navigate *out* of a project to scan others? The current plan assumes we scrape what is visible.

Testing & validation
- **Test Case 1 (Project Parent):** Navigate to `.../project`. Run scraper. Confirm it finds child threads in the sidebar.
- **Test Case 2 (Project Child):** Navigate to `.../c/<uuid>`. Run scraper. Confirm it finds the current thread AND siblings in the sidebar.
- **Test Case 3 (Standard):** Navigate to root `chatgpt.com`. Run scraper. Confirm it finds standard "Recent" threads.

Rollback / escape hatch
- Revert changes to `src/gpt_thinking_extractor/` files.
- Restore original `selectors.json`.

Owner/Date
- Unknown / 2025-12-22