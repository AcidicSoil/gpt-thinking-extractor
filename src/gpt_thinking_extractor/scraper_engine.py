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
                'button:has-text("Thought for")'
            ],
            "THOUGHT_CONTAINER_CANDIDATES": [
                "div.h-full.flex.flex-col.overflow-y-auto",
                "div.flex.flex-col.overflow-y-auto"
            ],
            "THOUGHT_CONTENT": 'div.text-token-text-secondary.markdown.prose',
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

    def get_unique_toggles(self, page, selector):
        all_elements = page.locator(selector).all()
        unique_elements = []
        seen_bounding_boxes = set()

        for el in all_elements:
            if not el.is_visible():
                continue
            box = el.bounding_box()
            if box:
                center = (box['x'] + box['width']/2, box['y'] + box['height']/2)
                if center not in seen_bounding_boxes:
                    seen_bounding_boxes.add(center)
                    unique_elements.append(el)
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
            except Exception:
                continue
        return 0, None

    def scroll_container(self, page, container_locator):
        """
        Scrolls the container to bottom to trigger lazy loading.
        """
        try:
            if not container_locator.is_visible():
                return

            previous_height = 0
            for _ in range(5):
                container_locator.evaluate("el => el.scrollTop = el.scrollHeight")
                time.sleep(0.5)
                
                new_height = container_locator.evaluate("el => el.scrollHeight")
                if new_height == previous_height:
                    break 
                previous_height = new_height
        except Exception as e:
            print(f"  [Warning] Scroll failed: {e}")

    def extract_ordered_content(self, page):
        """
        Scrolls the thought container and extracts content row-by-row.
        """
        candidates = self.get_selector("THOUGHT_CONTAINER_CANDIDATES")
        if not isinstance(candidates, list):
            candidates = [candidates]

        target_container = None
        for selector in candidates:
            containers = page.locator(selector).all()
            for c in containers:
                if c.is_visible():
                    target_container = c
                    break
            if target_container:
                break
        
        # Fallback to generic if specific candidates fail but we see *something*
        # (This logic is implicit in trying the list)

        if target_container:
            self.scroll_container(page, target_container)
        else:
            print("  [Warning] No visible thought container found to scroll.")
        
        row_selector = self.get_selector("THOUGHT_ROW")
        rows = page.locator(row_selector).all()
        
        extracted_text = []
        
        for row in rows:
            if not row.is_visible():
                continue
                
            try:
                code_container_sel = self.get_selector("THOUGHT_CODE_CONTAINER")
                is_code = row.locator(code_container_sel).count() > 0
                
                if is_code:
                    desc_sel = self.get_selector("THOUGHT_TEXT_SECONDARY")
                    description = row.locator(desc_sel).first.inner_text().strip()
                    
                    payload_sel = f"{code_container_sel} {self.get_selector('THOUGHT_CODE_PAYLOAD')}"
                    code = row.locator(payload_sel).first.inner_text()
                    
                    block = f"[CODE EXECUTION]\nDescription: {description}\nCommand:\n```\n{code}\n```"
                    extracted_text.append(block)
                else:
                    text_sel = self.get_selector("THOUGHT_TEXT_SECONDARY")
                    text = row.locator(text_sel).first.inner_text().strip()
                    extracted_text.append(text)
                    
            except Exception:
                continue
        
        return "\n\n".join(extracted_text)

    def save_thought(self, thread_id_or_url, thought_index, text):
        if "/c/" in thread_id_or_url:
            raw_id = thread_id_or_url.split("/c/")[-1]
        else:
            raw_id = thread_id_or_url.split('/')[-1]

        safe_id = self.sanitize_filename(raw_id)
        folder_path = os.path.join(self.output_folder, safe_id)
        os.makedirs(folder_path, exist_ok=True)
        
        filename = os.path.join(folder_path, f"thought_{thought_index}.txt")
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            return filename
        except OSError as e:
            print(f"[Error] Failed to save file {filename}: {e}")
            return None

    def close(self):
        if self.conn:
            self.conn.close()