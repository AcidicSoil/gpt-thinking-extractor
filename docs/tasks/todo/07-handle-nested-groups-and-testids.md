Context
- The `@Activity Drawer Spec.md` confirms nested groups.
- User feedback emphasizes **Robustness** over specific selectors:
    - Use `scrollHeight > clientHeight` to find containers (Geometry-first).
    - Use JS-dispatched `click()` for expansion (State-safe).
    - Avoid `networkidle`; rely on DOM changes.

Success criteria
- **Geometry-First Targeting:** Identify the activity container by its scroll properties if class selectors fail.
- **Nested Expansion:** Successfully expand "Reading documents" and other groups using trusted events.
- **Complete Capture:** Capture content that requires expansion/scrolling.

Deliverables
- Updated `scraper_engine.py`:
    - `find_scrollable_container(page)`: Implements the geometry check.
    - `expand_nested_groups(page, container)`: Uses JS click.
    - `scroll_container(page, container)`: Updated to wait for stability/mutations.

Approach
1) **Implement Geometry Finder:**
   - In `scraper_engine.py`, add logic to find elements where `scrollHeight > clientHeight` inside the thought toggle's context.
2) **Implement JS Expansion:**
   - `page.evaluate` script to find `details > summary` or specific group headers and `el.click()`.
3) **Refine Extraction Pipeline:**
   - Locate Container (Candidate List -> Geometry Fallback).
   - Expand Nested Groups.
   - Scroll to Bottom (with stability check).
   - Extract Rows.

Risks / unknowns
- **Multiple Scrollbars:** There might be multiple scrollable areas (e.g., code blocks). We need to filter for the *main* drawer (e.g., `clientHeight > 500` or largest area).

Testing & validation
- **Manual:** Run on complex thread. Verify expansion logs.

Rollback / escape hatch
- Revert changes.

Owner/Date
- Unknown / 2025-12-22