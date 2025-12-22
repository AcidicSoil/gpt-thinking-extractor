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
        
        # Resolve selectors_path relative to this file if not provided
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
        """Loads selectors from a JSON file."""
        try:
            with open(self.selectors_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"[Warning] {self.selectors_path} not found. Using defaults.")
            return {
                "SIDEBAR_PROJECT": 'nav a[href*="/project/"]',
                "PROJECT_PAGE_THREAD": 'main a[href*="/c/"]',
                "THOUGHT_TOGGLE": 'div.truncate:has-text("Thought for")',
                "THOUGHT_CONTENT": 'div.text-token-text-secondary div.markdown.prose'
            }
        except json.JSONDecodeError as e:
            print(f"[Error] Failed to parse {self.selectors_path}: {e}")
            raise

    def _init_db(self):
        """Initializes the SQLite database for tracking scraped URLs."""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.cursor = self.conn.cursor()
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS scraped_urls (
                url TEXT PRIMARY KEY,
                scraped_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def _ensure_output_folder(self):
        os.makedirs(self.output_folder, exist_ok=True)

    def is_url_scraped(self, url):
        """Checks if a URL has already been scraped."""
        self.cursor.execute("SELECT 1 FROM scraped_urls WHERE url = ?", (url,))
        return self.cursor.fetchone() is not None

    def mark_url_scraped(self, url):
        """Marks a URL as scraped in the database."""
        try:
            self.cursor.execute("INSERT OR IGNORE INTO scraped_urls (url) VALUES (?)", (url,))
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"[Error] DB Write Failed: {e}")

    def sanitize_filename(self, name):
        """Sanitizes a string to be safe for filenames on all OSes."""
        safe_name = re.sub(r'[<>:"/\\|?*]', '_', name)
        safe_name = safe_name.strip().strip('.')
        return safe_name[:100] if safe_name else "unknown_thread"

    def get_selector(self, key):
        return self.selectors.get(key)

    def save_thought(self, thread_id_or_url, thought_index, text):
        """Saves the scraped thought text to a file."""
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