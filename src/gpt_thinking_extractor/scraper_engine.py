import os
import json
import sqlite3
import re
import platform
import time
from pathlib import Path

class ScraperEngine:
    def __init__(self, output_folder="data", selectors_path=None, db_path="scraped_urls.db"):
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
            "THOUGHT_ROW": "div.relative.flex.w-full.items-start.gap-2",
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
        """Scrolls the main chat window to ensure all messages are loaded."""
        try:
            page.keyboard.press("Home")
            time.sleep(1)
            page.keyboard.press("End")
            time.sleep(1)
            
            js = (
                "() => {"
                "const mainScroll = document.querySelector('main div.overflow-y-auto');"
                "if (mainScroll) { mainScroll.scrollTop = 0; }"
                "}"
            )
            page.evaluate(js)
            time.sleep(1)
            
            js2 = (
                "() => {"
                "const mainScroll = document.querySelector('main div.overflow-y-auto');"
                "if (mainScroll) { mainScroll.scrollTop = mainScroll.scrollHeight; }"
                "}"
            )
            page.evaluate(js2)
            time.sleep(1)
        except:
            pass

    def get_unique_toggles(self, page, selector):
        self.scroll_main_chat(page)
        
        all_elements = page.locator(selector).all()
        unique_elements = []
        seen_bounding_boxes = set()

        for el in all_elements:
            try:
                el.scroll_into_view_if_needed()
                if not el.is_visible(): continue
                
                box = el.bounding_box()
                if box:
                    center = (box['x'] + box['width']/2, box['y'] + box['height']/2)
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
        if not isinstance(candidates, list): candidates = [candidates]

        for selector in candidates:
            try:
                unique_toggles = self.get_unique_toggles(page, selector)
                if unique_toggles:
                    return len(unique_toggles), selector
            except Exception:
                continue
        return 0, None

    def find_scrollable_container(self, page):
        js = (
            "() => {"
            "const allDivs = Array.from(document.querySelectorAll('div'));"
            "return allDivs.filter(el => {"
            "    const style = window.getComputedStyle(el);"
            "    const isOverflow = style.overflowY === 'auto' || style.overflowY === 'scroll';"
            "    const hasScroll = el.scrollHeight > el.clientHeight;"
            "    const isLarge = el.clientHeight > 300;"
            "    const rect = el.getBoundingClientRect();"
            "    const isRightSide = rect.left > (window.innerWidth * 0.5); "
            "    return hasScroll && isLarge && isRightSide;"
            "}).sort((a, b) => b.scrollHeight - a.scrollHeight)[0];"
            "}"
        )
        handle = page.evaluate_handle(js)
        return handle.as_element() if handle else None

    def expand_nested_groups(self, page, container_locator):
        try:
            js1 = (
                "container => {"
                "container.querySelectorAll('details:not([open]) > summary').forEach(el => el.click());"
                "}"
            )
            container_locator.evaluate(js1)
            
            js2 = (
                'container => {'
                'const toggles = Array.from(container.querySelectorAll("div[class*=\'group\'], div[role=\'button\']"));'
                'toggles.forEach(el => {'
                '    if (el.innerHTML.includes("svg") && !el.getAttribute("aria-expanded")) {'
                '         el.click();'
                '    }'
                '});'
                '}'
            )
            container_locator.evaluate(js2)
            time.sleep(1) 
        except Exception:
            pass

    def scroll_container(self, page, container_locator):
        try:
            previous_height = 0
            for _ in range(10): 
                container_locator.evaluate("el => el.scrollTop = el.scrollHeight")
                time.sleep(0.5)
                new_height = container_locator.evaluate("el => el.scrollHeight")
                if new_height == previous_height:
                    time.sleep(0.5)
                    final = container_locator.evaluate("el => el.scrollHeight")
                    if final == new_height: break 
                previous_height = new_height
        except Exception:
            pass

    def extract_structured_content(self, page):
        candidates = self.get_selector("THOUGHT_CONTAINER_CANDIDATES")
        if not isinstance(candidates, list): candidates = [candidates]

        target_container = None
        for selector in candidates:
            containers = page.locator(selector).all()
            for c in containers:
                if c.is_visible():
                    target_container = c
                    break
            if target_container: break
        
        if not target_container:
            handle = self.find_scrollable_container(page)
            if handle: target_container = handle

        if not target_container:
            print("  [Warning] No visible thought container found.")
            return None

        # --- The Scroll-Scrape Loop ---
        self.expand_nested_groups(page, target_container)
        
        timeline = []
        seen_content_hashes = set()
        
        row_selector = self.get_selector("THOUGHT_ROW")
        
        try:
            target_container.evaluate("el => el.scrollTop = 0")
            time.sleep(0.5)
        except: pass

        previous_scroll_top = -1
        
        while True:
            rows = page.locator(row_selector).all()
            for row in rows:
                if not row.is_visible(): continue
                try:
                    content_hash = ""
                    item = {}
                    
                    code_container_sel = self.get_selector("THOUGHT_CODE_CONTAINER")
                    is_code = row.locator(code_container_sel).count() > 0
                    
                    if is_code:
                        desc_sel = self.get_selector("THOUGHT_TEXT_SECONDARY")
                        description = row.locator(desc_sel).first.inner_text().strip()
                        payload_sel = f"{code_container_sel} {self.get_selector('THOUGHT_CODE_PAYLOAD')}"
                        code = row.locator(payload_sel).first.inner_text()
                        
                        item = {"type": "tool_use", "tool_name": "bash" if "bash" in description.lower() else "unknown", "description": description, "command": code}
                        content_hash = f"code:{description}:{code[:50]}"
                    else:
                        text_sel = self.get_selector("THOUGHT_TEXT_SECONDARY")
                        text = row.locator(text_sel).first.inner_text().strip()
                        if text:
                            item = {"type": "thought", "content": text}
                            content_hash = f"thought:{text[:50]}"
                    
                    if content_hash and content_hash not in seen_content_hashes:
                        seen_content_hashes.add(content_hash)
                        timeline.append(item)
                except:
                    continue

            try:
                current_scroll = target_container.evaluate("el => el.scrollTop")
                if current_scroll == previous_scroll_top:
                    break 
                
                previous_scroll_top = current_scroll
                target_container.evaluate("el => el.scrollBy(0, 500)")
                time.sleep(0.5) 
                
                at_bottom = target_container.evaluate("el => Math.abs(el.scrollHeight - el.scrollTop - el.clientHeight) < 1")
                if at_bottom:
                    pass 
                
            except Exception:
                break

        if not timeline:
             try:
                 raw = target_container.evaluate("el => el.innerText") if hasattr(target_container, 'evaluate') else target_container.inner_text()
                 return {"meta": {"fallback": True}, "timeline": [{"type": "raw", "content": raw}]}
             except: pass

        return {"meta": {"count": len(timeline)}, "timeline": timeline}

    def save_thought(self, thread_id_or_url, thought_index, data, duration=None):
        if "/c/" in thread_id_or_url:
            raw_id = thread_id_or_url.split("/c/")[-1]
        else:
            raw_id = thread_id_or_url.split('/')[-1]

        safe_id = self.sanitize_filename(raw_id)
        folder_path = os.path.join(self.output_folder, safe_id)
        os.makedirs(folder_path, exist_ok=True)
        
        filename = os.path.join(folder_path, f"thought_{thought_index}.json")
        
        output = {
            "meta": {
                "duration": duration,
                "url": thread_id_or_url,
                "scraped_at": time.time()
            },
            **data 
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
