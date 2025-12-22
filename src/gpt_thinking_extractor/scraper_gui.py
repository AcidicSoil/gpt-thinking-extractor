import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, Toplevel
import threading
import os
import sys
import time
import platform
import subprocess
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

try:
    from .scraper_engine import ScraperEngine
except ImportError:
    from scraper_engine import ScraperEngine

load_dotenv()

CDP_URL_DEFAULT = os.getenv("CHROME_DEBUG_URL", "http://localhost:9222")
OUTPUT_FOLDER_DEFAULT = os.getenv("OUTPUT_FOLDER", "data")

class ScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Chatbot Thought Scraper")
        self.root.geometry("750x800")
        
        self.is_running = False
        self.stop_event = threading.Event()
        self.engine = None
        self.global_scan_var = tk.BooleanVar(value=False)

        # UI Construction
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
        
        ttk.Checkbutton(config_frame, text="Include Global Scan (Navigate Home)", variable=self.global_scan_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=5)
        
        ctrl_frame = ttk.Frame(root, padding=10)
        ctrl_frame.pack(fill="x", padx=10)
        
        self.start_btn = ttk.Button(ctrl_frame, text="Start Audit & Scrape", command=self.start_audit_thread)
        self.start_btn.pack(side="left", padx=5)
        
        self.stop_btn = ttk.Button(ctrl_frame, text="Stop", command=self.stop_scraping, state="disabled")
        self.stop_btn.pack(side="left", padx=5)

        self.open_btn = ttk.Button(ctrl_frame, text="Open Data Folder", command=self.open_data_folder)
        self.open_btn.pack(side="right", padx=5)

        log_frame = ttk.LabelFrame(root, text="Live Logs", padding=10)
        log_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.log_area = scrolledtext.ScrolledText(log_frame, state='disabled', height=20)
        self.log_area.pack(fill="both", expand=True)
        self.log_area.tag_config("info", foreground="black")
        self.log_area.tag_config("success", foreground="green")
        self.log_area.tag_config("error", foreground="red")
        self.log_area.tag_config("warning", foreground="#cc6600")

    def log(self, message, level="info"):
        def _log():
            self.log_area.config(state='normal')
            self.log_area.insert(tk.END, message + "\n", level)
            self.log_area.see(tk.END)
            self.log_area.config(state='disabled')
        self.root.after(0, _log)

    def start_audit_thread(self):
        self.is_running = True
        self.stop_event.clear()
        self.start_btn.config(state="disabled")
        self.stop_btn.config(state="normal")
        self.url_entry.config(state="disabled")
        t = threading.Thread(target=self.run_audit_pipeline)
        t.daemon = True
        t.start()

    def stop_scraping(self):
        if self.is_running:
            self.log("🛑 Stopping...", "warning")
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
        if platform.system() == "Windows": os.startfile(folder)
        elif platform.system() == "Darwin": subprocess.Popen(["open", folder])
        else: subprocess.Popen(["xdg-open", folder])

    def show_audit_dialog(self, results):
        dialog = Toplevel(self.root)
        dialog.title("Audit Results - Confirm Scrape")
        dialog.geometry("700x500")
        
        ttk.Label(dialog, text="Select threads to scrape:").pack(pady=10)
        
        canvas = tk.Canvas(dialog)
        scrollbar = ttk.Scrollbar(dialog, orient="vertical", command=canvas.yview)
        scroll_frame = ttk.Frame(canvas)
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=10)
        scrollbar.pack(side="right", fill="y")
        
        vars = []
        for res in results:
            var = tk.BooleanVar(value=res['count'] > 0)
            vars.append((var, res))
            title = res['title']
            txt = f"{title} ({res['count']} thoughts)"
            cb = ttk.Checkbutton(scroll_frame, text=txt, variable=var)
            cb.pack(anchor="w", padx=5, pady=2)
            
        def on_confirm():
            selected = [v[1] for v in vars if v[0].get()]
            dialog.destroy()
            self.log(f"✅ User confirmed {len(selected)} threads.", "success")
            t = threading.Thread(target=self.run_execution_pipeline, args=(selected,))
            t.daemon = True
            t.start()
            
        def on_cancel():
            dialog.destroy()
            self.log("🛑 Cancelled.", "warning")
            self.finish_scraping()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Proceed", command=on_confirm).pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="right", padx=10)

    def run_audit_pipeline(self):
        cdp_url = self.url_entry.get()
        data_folder = self.folder_entry.get()
        
        try:
            self.engine = ScraperEngine(output_folder=data_folder)
        except Exception as e:
            self.log(f"Error initializing engine: {e}", "error")
            self.root.after(0, self.finish_scraping)
            return

        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(cdp_url)
            except Exception as e:
                self.log(f"❌ Connection Failed: {e}", "error")
                self.root.after(0, self.finish_scraping)
                return

            context = browser.contexts[0]
            page = context.pages[0]
            page.bring_to_front()
            
            # {url: title}
            all_chat_threads = {}
            active_project_id = self.engine.extract_project_id(page.url)
            
            if active_project_id:
                self.log(f"🔒 Scoping to Project: {active_project_id}", "success")
            
            # --- PHASE 0: CONTEXT ---
            current_url = page.url
            if "/project/" in current_url or "/g/" in current_url:
                try:
                    page.wait_for_selector('nav', timeout=3000)
                    thread_selector = self.engine.get_selector("SIDEBAR_THREAD")
                    thread_links = page.locator(thread_selector).all()
                    for link in thread_links:
                        if self.stop_event.is_set(): break
                        href = link.get_attribute("href")
                        title = link.inner_text().split('\n')[0]
                        if href and "/c/" in href:
                            if active_project_id and active_project_id not in href:
                                continue
                            full_url = "https://chatgpt.com" + href if href.startswith("/") else href
                            all_chat_threads[full_url] = title
                    self.log(f"   Found {len(all_chat_threads)} threads in active project.", "info")
                except Exception as e:
                    self.log(f"   [Warning] Scan failed: {e}", "warning")
            
            if "/c/" in current_url:
                 if not active_project_id or (active_project_id in current_url):
                     self.log("📄 Active Thread Detected.", "success")
                     all_chat_threads[current_url] = "Current Page"

            # --- PHASE 2: AUDIT ---
            if not all_chat_threads:
                self.log("⚠️ No threads found to audit.", "warning")
                self.root.after(0, self.finish_scraping)
                return

            self.log(f"🕵️ Auditing {len(all_chat_threads)} threads...", "info")
            sorted_urls = sorted(list(all_chat_threads.keys()))
            audit_results = []

            for i, url in enumerate(sorted_urls):
                if self.stop_event.is_set(): break
                title = all_chat_threads[url]
                self.log(f"   Auditing [{i+1}/{len(sorted_urls)}]: {title[:20]}...", "info")
                try:
                    page.goto(url)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(1.5)
                    count, sel = self.engine.audit_thread(page, url)
                    audit_results.append({"url": url, "title": title, "count": count, "selector": sel})
                except Exception as e:
                    self.log(f"   Audit failed for {url}: {e}", "error")

            self.root.after(0, lambda: self.show_audit_dialog(audit_results))

    def run_execution_pipeline(self, to_scrape):
        cdp_url = self.url_entry.get()
        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(cdp_url)
                context = browser.contexts[0]
                page = context.pages[0]
                page.bring_to_front()
            except Exception as e:
                self.log(f"❌ Re-connection Failed: {e}", "error")
                self.root.after(0, self.finish_scraping)
                return

            self.log(f"🚀 Starting Scrape of {len(to_scrape)} threads...", "success")
            
            for i, item in enumerate(to_scrape):
                if self.stop_event.is_set(): break
                url = item["url"]
                sel = item["selector"]
                title = item["title"]
                
                if self.engine.is_url_scraped(url):
                    self.log(f"Skipping: {title}", "info")
                    continue

                self.log(f"[{i+1}/{len(to_scrape)}] Processing: {title}", "info")
                try:
                    page.goto(url)
                    page.wait_for_load_state("domcontentloaded")
                    time.sleep(2) 

                    if not sel:
                        candidates = self.engine.get_selector("THOUGHT_TOGGLE_CANDIDATES")
                        sel = candidates[0] if isinstance(candidates, list) else candidates

                    # Force visibility check again just in case
                    unique_toggles = self.engine.get_unique_toggles(page, sel)
                    
                    if not unique_toggles:
                         self.log(f"  No visible thoughts found using {sel}", "warning")
                    else:
                         content_selector = self.engine.get_selector("THOUGHT_CONTENT")
                         for idx, toggle in enumerate(unique_toggles):
                            if self.stop_event.is_set(): break
                            toggle.scroll_into_view_if_needed()
                            toggle.click(force=True)
                            
                            # Increased wait for expansion
                            page.wait_for_timeout(1000)
                            
                            try:
                                # Wait for content to be visible
                                page.wait_for_selector(content_selector, state="visible", timeout=5000)
                                full_text = self.engine.extract_ordered_content(page)
                                
                                if full_text:
                                    saved_path = self.engine.save_thought(url, idx, full_text)
                                    if saved_path:
                                        self.log(f"  [Saved] {os.path.basename(saved_path)}", "success")
                                else:
                                    self.log(f"  [Warning] Extracted text empty.", "warning")
                                    
                            except Exception as e:
                                self.log(f"  Extraction timeout: {e}", "error")
                                
                    self.engine.mark_url_scraped(url, title)
                except Exception as e:
                    self.log(f"  Error on thread: {e}", "error")

            self.root.after(0, self.finish_scraping)

def main():
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()