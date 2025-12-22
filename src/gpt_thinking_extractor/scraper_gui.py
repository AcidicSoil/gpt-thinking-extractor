import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import os
import sys
import time
import platform
import subprocess
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Relative import for package structure
try:
    from .scraper_engine import ScraperEngine
except ImportError:
    from scraper_engine import ScraperEngine

# Load environment variables
load_dotenv()

# --- CONFIGURATION ---
CDP_URL_DEFAULT = os.getenv("CHROME_DEBUG_URL", "http://localhost:9222")
OUTPUT_FOLDER_DEFAULT = os.getenv("OUTPUT_FOLDER", "data")

class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chatbot Thought Scraper")
        self.root.geometry("600x700")
        
        # State
        self.is_running = False
        self.stop_event = threading.Event()
        self.engine = None

        # --- UI LAYOUT ---
        
        # 1. Configuration Frame
        config_frame = ttk.LabelFrame(root, text="Configuration", padding=10)
        config_frame.pack(fill="x", padx=10, pady=5)
        
        ttk.Label(config_frame, text="Chrome Debug URL:").grid(row=0, column=0, sticky="w")
        self.url_entry = ttk.Entry(config_frame, width=30)
        self.url_entry.insert(0, CDP_URL_DEFAULT)
        self.url_entry.grid(row=0, column=1, padx=5, sticky="ew")

        ttk.Label(config_frame, text="Output Folder:").grid(row=1, column=0, sticky="w")
        self.folder_entry = ttk.Entry(config_frame, width=30)
        self.folder_entry.insert(0, OUTPUT_FOLDER_DEFAULT)
        self.folder_entry.grid(row=1, column=1, padx=5, sticky="ew")
        
        # 2. Control Frame
        ctrl_frame = ttk.Frame(root, padding=10)
        ctrl_frame.pack(fill="x", padx=10)
        
        self.start_btn = ttk.Button(ctrl_frame, text="Start Scraping", command=self.start_thread)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(ctrl_frame, text="Stop", command=self.stop_scraping, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.open_btn = ttk.Button(ctrl_frame, text="Open Data Folder", command=self.open_data_folder)
        self.open_btn.pack(side="right", padx=5)

        # 3. Log Window
        log_frame = ttk.LabelFrame(root, text="Live Logs", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=20)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.tag_config("info", foreground="black")
        self.log_area.tag_config("success", foreground="green")
        self.log_area.tag_config("error", foreground="red")
        self.log_area.tag_config("warning", foreground="#cc6600")

    def log(self, message, level="info"):
        """Thread-safe logging to the text area."""
        def _log():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, message + "\n", level)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, _log)

    def start_thread(self):
        self.is_running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.url_entry.config(state="disabled")
        
        # Run scraping in background thread
        t = threading.Thread(target=self.run_scraper)
        t.daemon = True
        t.start()

    def stop_scraping(self):
        if self.is_running:
            self.log("🛑 Stopping... finishing current action.", "warning")
            self.stop_event.set()

    def finish_scraping(self):
        self.is_running = False
        self.start_btn.config(state="normal")
        self.stop_btn.config(state="disabled")
        self.url_entry.config(state="normal")
        if self.engine:
            self.engine.close()
        self.log("--- Process Stopped/Finished ---")

    def open_data_folder(self):
        folder = self.folder_entry.get()
        if not os.path.exists(folder):
            os.makedirs(folder)
        
        if platform.system() == "Windows":
            os.startfile(folder)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", folder])
        else:
            # Basic fallback for Linux
            subprocess.Popen(["xdg-open", folder])

    def run_scraper(self):
        cdp_url = self.url_entry.get()
        data_folder = self.folder_entry.get()
        
        # Initialize Engine
        try:
            self.engine = ScraperEngine(output_folder=data_folder)
        except Exception as e:
            self.log(f"Error initializing engine: {e}", "error")
            self.root.after(0, self.finish_scraping)
            return

        with sync_playwright() as p:
            try:
                self.log(f"Connecting to Chrome at {cdp_url}...")
                browser = p.chromium.connect_over_cdp(cdp_url)
            except Exception as e:
                self.log(f"❌ Connection Failed: {e}", "error")
                self.log("Ensure Chrome is running with --remote-debugging-port=9222", "error")
                self.root.after(0, self.finish_scraping)
                return

            context = browser.contexts[0]
            page = context.pages[0]
            page.bring_to_front()
            self.log(f"✅ Connected to tab: {page.title()}", "success")

            # --- PHASE 1: PROJECTS ---
            if self.stop_event.is_set(): return
            self.log("🔍 Scanning sidebar for projects...")
            
            try:
                page.wait_for_selector('nav', timeout=5000)
                sidebar_selector = self.engine.get_selector("SIDEBAR_PROJECT")
                project_elements = page.locator(sidebar_selector).all()
                project_urls = []
                for el in project_elements:
                    href = el.get_attribute("href")
                    if href:
                        full_url = "https://chatgpt.com" + href if href.startswith("/") else href
                        if full_url not in project_urls:
                            project_urls.append(full_url)
                self.log(f"📋 Found {len(project_urls)} projects.", "info")
            except Exception as e:
                self.log(f"Error scanning projects: {e}", "error")
                project_urls = []

            # --- PHASE 2: GATHER THREADS ---
            all_chat_urls = set()
            thread_selector = self.engine.get_selector("PROJECT_PAGE_THREAD")

            for i, p_url in enumerate(project_urls):
                if self.stop_event.is_set(): break
                self.log(f"Scanning Project {i+1}/{len(project_urls)}...", "info")
                
                try:
                    page.goto(p_url)
                    page.wait_for_load_state("networkidle")
                    time.sleep(1)
                    
                    thread_links = page.locator(thread_selector).all()
                    count = 0
                    for link in thread_links:
                        url_path = link.get_attribute("href")
                        if url_path and "/c/" in url_path:
                            full_url = "https://chatgpt.com" + url_path if url_path.startswith("/") else url_path
                            all_chat_urls.add(full_url)
                            count += 1
                    self.log(f"   Found {count} threads.", "info")
                except Exception as e:
                    self.log(f"   Failed to scan project: {e}", "error")

            # --- PHASE 3: SCRAPE THOUGHTS ---
            sorted_urls = sorted(list(all_chat_urls))
            self.log(f"Starting scrape of {len(sorted_urls)} threads...", "success")
            
            for i, url in enumerate(sorted_urls):
                if self.stop_event.is_set(): break
                
                if self.engine.is_url_scraped(url):
                    self.log(f"Skipping already scraped: {url.split('/')[-1]}", "info")
                    continue

                self.log(f"[{i+1}/{len(sorted_urls)}] Processing: {url.split('/')[-1]}", "info")
                
                try:
                    page.goto(url)
                    time.sleep(2.5) 

                    # Find Toggles
                    toggle_selector = self.engine.get_selector("THOUGHT_TOGGLE")
                    toggles = page.locator(toggle_selector).all()
                    
                    if not toggles:
                        self.log("  No thoughts found.", "warning")
                    else:
                        self.log(f"  Found {len(toggles)} thoughts.", "info")
                        content_selector = self.engine.get_selector("THOUGHT_CONTENT")
                        
                        for idx, toggle in enumerate(toggles):
                            if self.stop_event.is_set(): break
                            
                            # Click
                            if toggle.is_visible():
                                toggle.scroll_into_view_if_needed()
                                toggle.click(force=True)
                                time.sleep(0.5)
                            
                            # Scrape
                            content_loc = page.locator(content_selector)
                            txt = ""
                            if idx < content_loc.count():
                                txt = content_loc.nth(idx).inner_text()
                            else:
                                txt = content_loc.last.inner_text()
                            
                            saved_path = self.engine.save_thought(url, idx, txt)
                            if saved_path:
                                self.log(f"  [Saved] {os.path.basename(saved_path)}", "success")
                                
                    self.engine.mark_url_scraped(url)
                    
                except Exception as e:
                    self.log(f"  Error on thread: {e}", "error")

            self.root.after(0, self.finish_scraping)

def main():
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()