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
        self.root.geometry("750x850")
        
        self.is_running = False
        self.stop_event = threading.Event()
        self.engine = None
        self.global_scan_var = tk.BooleanVar(value=False)
        self.sidebar_scan_var = tk.BooleanVar(value=False) # Sidebar scan opt-in

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
        
        ttk.Checkbutton(config_frame, text="Scan Project Sidebar (Find siblings)", variable=self.sidebar_scan_var).grid(row=2, column=0, columnspan=2, sticky="w", pady=2)
        ttk.Checkbutton(config_frame, text="Include Global Scan (Navigate Home)", variable=self.global_scan_var).grid(row=3, column=0, columnspan=2, sticky="w", pady=2)
        
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
        self.log_area.tag_config("debug", foreground="gray")

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
        if self.engine: self.engine.close()
        self.log("--- Process Stopped/Finished ---")

    def open_data_folder(self):
        folder = self.folder_entry.get()
        if not os.path.exists(folder): os.makedirs(folder)
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
            cb = ttk.Checkbutton(scroll_frame, text=f"{res['title']} ({res['count']} thoughts)", variable=var)
            cb.pack(anchor="w", padx=5, pady=2)
        def on_confirm():
            selected = [v[1] for v in vars if v[0].get()]
            dialog.destroy()
            t = threading.Thread(target=self.run_execution_pipeline, args=(selected,))
            t.daemon = True
            t.start()
        def on_cancel():
            dialog.destroy()
            self.finish_scraping()
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", pady=10)
        ttk.Button(btn_frame, text="Proceed", command=on_confirm).pack(side="right", padx=10)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="right", padx=10)

    def run_audit_pipeline(self):
        try:
            self.engine = ScraperEngine(output_folder=self.folder_entry.get())
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.url_entry.get())
                context = browser.contexts[0]
                page = next((pg for pg in context.pages if "chatgpt.com" in pg.url), context.pages[0])
                page.bring_to_front()
                
                all_chat_threads = {}
                active_project_id = self.engine.extract_project_id(page.url)
                self.log(f"📍 URL: {page.url}", "debug")
                if active_project_id: self.log(f"🔒 Project Scope: {active_project_id}", "success")
                
                # --- PHASE 0: SIDEBAR SCAN (OPTIONAL) ---
                if self.sidebar_scan_var.get():
                    self.log("🔍 Scanning sidebar (Opt-in enabled)...", "info")
                    try:
                        page.wait_for_selector('nav', timeout=3000)
                        links = page.locator(self.engine.get_selector("SIDEBAR_THREAD")).all()
                        for link in links:
                            href = link.get_attribute("href")
                            title = link.inner_text().split('\n')[0]
                            if href and "/c/" in href:
                                # If we have a project scope, only include links matching that scope
                                if active_project_id and active_project_id not in href: continue
                                all_chat_threads["https://chatgpt.com" + href] = title
                        self.log(f"   Found {len(all_chat_threads)} threads in sidebar.", "info")
                    except Exception as e: self.log(f"Scan failed: {e}", "warning")
                
                # --- PHASE 1: CURRENT PAGE ---
                if "/c/" in page.url:
                     # Always include the current page if it's a thread
                     all_chat_threads[page.url] = "Current Page"
                elif not self.sidebar_scan_var.get():
                     self.log("📄 Not on a thread page and Sidebar Scan is OFF.", "warning")
                     messagebox.showwarning("Logic Error", "You are not on a chat thread page.\nPlease navigate to a thread or enable 'Scan Project Sidebar'.")
                
                if not all_chat_threads:
                    self.log("⚠️ No threads found to audit.", "warning")
                    self.root.after(0, self.finish_scraping)
                    return

                audit_results = []
                for url, title in all_chat_threads.items():
                    if self.stop_event.is_set(): break
                    page.goto(url)
                    time.sleep(1.5)
                    count, sel = self.engine.audit_thread(page, url)
                    audit_results.append({"url": url, "title": title, "count": count, "selector": sel})
                
                self.root.after(0, lambda: self.show_audit_dialog(audit_results))
        except Exception as e:
            self.log(f"Error: {e}", "error")
            self.root.after(0, self.finish_scraping)

    def run_execution_pipeline(self, to_scrape):
        try:
            with sync_playwright() as p:
                browser = p.chromium.connect_over_cdp(self.url_entry.get())
                context = browser.contexts[0]
                page = next((pg for pg in context.pages if "chatgpt.com" in pg.url), context.pages[0])
                
                for item in to_scrape:
                    if self.stop_event.is_set(): break
                    if self.engine.is_url_scraped(item['url']): continue
                    self.log(f"Processing: {item['title']}")
                    page.goto(item['url'])
                    time.sleep(2)
                    
                    unique_toggles = self.engine.get_unique_toggles(page, item['selector'] or self.engine.get_selector("THOUGHT_TOGGLE_CANDIDATES")[0])
                    for idx, toggle in enumerate(unique_toggles):
                        if self.stop_event.is_set(): break
                        duration = "Unknown"
                        try: duration = toggle.inner_text().split('\n')[0].strip() or "Unknown"
                        except: pass
                        
                        toggle.scroll_into_view_if_needed()
                        toggle.click(force=True)
                        page.wait_for_timeout(1000)
                        
                        data = self.engine.extract_structured_content(page)
                        if data:
                            self.engine.save_thought(item['url'], idx, data, duration=duration)
                            self.log(f"  [Saved] thought_{idx}.json ({duration})", "success")
                    self.engine.mark_url_scraped(item['url'], item['title'])
                self.root.after(0, self.finish_scraping)
        except Exception as e:
            self.log(f"Error: {e}", "error")
            self.root.after(0, self.finish_scraping)

def main():
    root = tk.Tk()
    app = ScraperApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
