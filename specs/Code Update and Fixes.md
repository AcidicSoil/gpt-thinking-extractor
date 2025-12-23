## You asked

\_Scraping App Improvement Steps .md

File

src.md

File

---

## ChatGPT Replied

Thought for 8m 18s

* Fixed `SyntaxError: unterminated string literal` caused by multi-line `page.evaluate(...)` / `evaluate_handle(...)` / `locator.evaluate(...)` strings.

    src

* `find_scrollable_container()` now returns a **Locator** (not an `ElementHandle`) so downstream `.locator(...)` calls do not crash.

    src

* `save_thought()` now supports both:

  * `str` → writes raw `.txt` (matches unit test expectations)

        src

  * `dict` → writes structured `.json`

    src/
      gpt_thinking_extractor/
        scraper_engine.py

    # path: src/gpt_thinking_extractor/scraper_engine.py

    import os
    import json
    import sqlite3
    import re
    import platform
    import time
    from pathlib import Path

    class ScraperEngine:
        def **init**(self, output_folder="data", selectors_path=None, db_path="scraped_urls.db"):
            self.output_folder = output_folder

            if selectors_path is None:
                base_dir = os.path.dirname(os.path.abspath(__file__))
                self.selectors_path = os.path.join(base_dir, "selectors.json")
            else:
                self.selectors_path = selectors_path

            self.db_path = db_path
            self.selectors = self._load_selectors()
            self._init_db()
            self._ensure_output_folder()

        def _load_selectors(self):
            defaults = {
                "SIDEBAR_PROJECT": 'nav a[href*="/project/"]',
                "SIDEBAR_RECENT": 'nav a[href*="/c/"]',
                "SIDEBAR_THREAD": 'nav a[href*="/c/"]',
                "PROJECT_PAGE_THREAD": 'main a[href*="/c/"]',
                "THOUGHT_TOGGLE_CANDIDATES": [
                    'div.truncate:has-text("Thought for")',
                    'button:has-text("Thought for")',
                    'div:has-text("Thought for")'
                ],
                "THOUGHT_CONTAINER_CANDIDATES": [
                    "div.h-full.flex.flex-col.overflow-y-auto",
                    "div.flex.flex-col.overflow-y-auto"
                ],
                "THOUGHT_ROW": "div.text-token-text-primary, code, div.markdown",
                "THOUGHT_TEXT_SECONDARY": "div.text-token-text-secondary",
                "THOUGHT_CODE_CONTAINER": "div.mt-1",
                "THOUGHT_CODE_PAYLOAD": "div.text-token-text-primary"
            }

            try:
                with open(self.selectors_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    return {**defaults, **loaded}
            except FileNotFoundError:
                return defaults
            except json.JSONDecodeError:
                raise

        def _init_db(self):
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.cursor = self.conn.cursor()
            self.cursor.execute("""
                CREATE TABLE IF NOT EXISTS scraped_urls (
                    url TEXT PRIMARY KEY,
                    title TEXT,
                    scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            self.conn.commit()

        def _ensure_output_folder(self):
            os.makedirs(self.output_folder, exist_ok=True)

        def is_url_scraped(self, url):
            self.cursor.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,))
            return self.cursor.fetchone() is not None

        def mark_url_scraped(self, url, title=None):
            try:
                self.cursor.execute(
                    "INSERT OR REPLACE INTO scraped_urls (url, title) VALUES (?, ?)",
                    (url, title)
                )
                self.conn.commit()
            except sqlite3.Error as e:
                print(f"[Error] DB Write Failed: {e}")

        def sanitize_filename(self, name):
            safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
            safe_name = safe_name.strip().strip('.')
            return safe_name[:100] if safe_name else "unknown_thread"

        def get_selector(self, key):
            return self.selectors.get(key)

        def extract_project_id(self, url):
            match = re.search(r'/(g-p-[a-zA-Z0-9-]+)', url)
            return match.group(1) if match else None

        def scroll_main_chat(self, page):
            """Ensures the main chat is at the bottom to find toggles."""
            try:
                page.evaluate(
                    """() => {
                        const main = document.querySelector('main div.overflow-y-auto');
                        if (main) main.scrollTop = main.scrollHeight;
                    }"""
                )
                time.sleep(0.5)
            except:
                pass

        def get_unique_toggles(self, page, selector):
            self.scroll_main_chat(page)

            all_elements = page.locator(selector).all()
            unique_elements = []
            seen_bounding_boxes = set()

            for el in all_elements:
                try:
                    if not el.is_visible():
                        continue
                    box = el.bounding_box()
                    if box:
                        center = (box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                        found = False
                        for existing in seen_bounding_boxes:
                            if abs(existing[0] - center[0]) < 5 and abs(existing[1] - center[1]) < 5:
                                found = True
                                break
                        if not found:
                            seen_bounding_boxes.add(center)
                            unique_elements.append(el)
                except:
                    continue
            return unique_elements

        def audit_thread(self, page, thread_url):
            candidates = self.get_selector("THOUGHT_TOGGLE_CANDIDATES")
            if not isinstance(candidates, list):
                candidates = [candidates]
            for selector in candidates:
                try:
                    unique_toggles = self.get_unique_toggles(page, selector)
                    if unique_toggles:
                        return len(unique_toggles), selector
                except:
                    continue
            return 0, None

        def find_scrollable_container(self, page):
            """
            Best-effort heuristic to locate the right-side scrollable drawer container.
            Returns a Locator (not an ElementHandle) so downstream code can use .locator() safely.
            """
            try:
                page.evaluate(
                    """() => {
                        document.querySelectorAll('[data-gte-scroll-container]').forEach(el => {
                            el.removeAttribute('data-gte-scroll-container');
                        });
                        const allDivs = Array.from(document.querySelectorAll('div'));
                        const best = allDivs.filter(el => {
                            const style = window.getComputedStyle(el);
                            const isOverflow = style.overflowY === 'auto' || style.overflowY === 'scroll';
                            const hasScroll = el.scrollHeight > el.clientHeight;
                            const isLarge = el.clientHeight > 300;
                            const rect = el.getBoundingClientRect();
                            const isRightSide = rect.left > (window.innerWidth * 0.5);
                            return isOverflow && hasScroll && isLarge && isRightSide;
                        }).sort((a, b) => b.scrollHeight - a.scrollHeight)[0];
                        if (best) best.setAttribute('data-gte-scroll-container', 'true');
                    }"""
                )
                locator = page.locator('[data-gte-scroll-container="true"]')
                if locator.count() > 0:
                    return locator.first
            except Exception:
                pass
            return None

        def expand_nested_groups(self, page, container_locator):
            """Clicks common disclosure controls inside the container to expand nested sections."""
            try:
                container_locator.evaluate(
                    """(container) => {
                        container.querySelectorAll('details:not([open]) > summary').forEach(el => el.click());
                        const buttons = container.querySelectorAll('button[aria-expanded="false"]');
                        buttons.forEach(b => b.click());
                    }"""
                )
                time.sleep(0.5)
            except Exception:
                pass

        def extract_structured_content(self, page):
            """
            Robust Incremental Extraction:
            Scroll drawer -> Scrape visible new items -> Deduplicate.
            """
            # 1. Locate Drawer
            candidates = self.get_selector("THOUGHT_CONTAINER_CANDIDATES")
            if not isinstance(candidates, list):
                candidates = [candidates]
            target_container = None
            for selector in candidates:
                try:
                    containers = page.locator(selector).all()
                    for c in containers:
                        if c.is_visible():
                            target_container = c
                            break
                    if target_container:
                        break
                except:
                    continue

            if not target_container:
                # Fallback: guess the right-side scrollable div
                target_container = self.find_scrollable_container(page)

            if not target_container:
                return {"meta": {"count": 0}, "timeline": []}

            # 2. Expand nested disclosure groups
            self.expand_nested_groups(page, target_container)

            row_selector = self.get_selector("THOUGHT_ROW") or "div.text-token-text-primary, code, div.markdown"

            timeline = []
            seen_content_hashes = set()

            # Scroll to top of container
            try:
                target_container.evaluate("el => el.scrollTop = 0")
            except:
                pass

            previous_scroll_top = -1

            # 3. Incremental Scroll-Scrape Loop
            for _ in range(20):  # Max 20 "pages" of scrolling
                # A. Scrape Visible Leaf Nodes
                elements = target_container.locator(row_selector).all()

                for el in elements:
                    try:
                        if not el.is_visible():
                            continue
                        text = el.inner_text().strip()
                        if not text:
                            continue

                        content_hash = hash(text)
                        if content_hash in seen_content_hashes:
                            continue
                        seen_content_hashes.add(content_hash)

                        is_code = el.evaluate(
                            "(node) => node.tagName === 'CODE' || node.classList.contains('text-token-text-primary') || node.closest('pre') !== null"
                        )

                        if is_code:
                            timeline.append({"type": "tool_use", "content": text})
                        else:
                            timeline.append({"type": "thought", "content": text})
                    except:
                        continue

                # B. Scroll Down
                try:
                    current_scroll = target_container.evaluate("el => el.scrollTop")
                    if current_scroll == previous_scroll_top:
                        at_bottom = target_container.evaluate(
                            "el => Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) < 5"
                        )
                        if at_bottom:
                            break

                    previous_scroll_top = current_scroll
                    target_container.evaluate("el => el.scrollBy(0, 400)")
                    time.sleep(0.8)
                except:
                    break

            return {"meta": {"count": len(timeline)}, "timeline": timeline}

        def save_thought(self, thread_id_or_url, thought_index, data, duration=None):
            """
            Persists one thought to disk under output_folder/<thread_id>/thought_<n>.*

            - If data is a string, writes raw text to .txt (used by unit tests).
            - If data is a dict, writes structured JSON to .json.
            """
            if "/c/" in thread_id_or_url:
                raw_id = thread_id_or_url.split("/c/")[-1]
            else:
                raw_id = thread_id_or_url.split('/')[-1]

            safe_id = self.sanitize_filename(raw_id)
            folder_path = os.path.join(self.output_folder, safe_id)
            os.makedirs(folder_path, exist_ok=True)

            # Raw text path (backward-compatible)
            if isinstance(data, str):
                filename = os.path.join(folder_path, f"thought_{thought_index}.txt")
                try:
                    with open(filename, "w", encoding="utf-8") as f:
                        f.write(data)
                    return filename
                except OSError as e:
                    print(f"[Error] Failed to save file {filename}: {e}")
                    return None

            # Structured JSON path
            if not isinstance(data, dict):
                data = {"content": data}

            filename = os.path.join(folder_path, f"thought_{thought_index}.json")
            output = {
                "meta": {
                    "duration": duration,
                    "url": thread_id_or_url,
                    "scraped_at": time.time(),
                },
                **data,
            }

            try:
                with open(filename, "w", encoding="utf-8") as f:
                    json.dump(output, f, indent=2)
                return filename
            except OSError as e:
                print(f"[Error] Failed to save file {filename}: {e}")
                return None

        def close(self):
            if self.conn:
                self.conn.close()

---
