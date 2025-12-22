
\[Fix Playwright selector bug: remove invalid `re.compile(...)` from CSS selector strings and use `has_text=re.compile(...)` to prevent selector parse errors.\]

src

    import os
    import re
    import time
    from playwright.sync_api import sync_playwright

    # --- CONFIGURATION ---
    DATA_FOLDER = "data"
    CDP_URL = "http://localhost:9222"
    BASE_URL = "https://chatgpt.com"

    # Set to store URLs we have already scraped to prevent duplication
    SCRAPED_URLS = set()

    # --- SELECTORS ---
    SIDEBAR_PROJECT_SELECTOR = 'nav a[href*="/project/"]'
    PROJECT_PAGE_THREAD_SELECTOR = 'main a[href*="/c/"]'

    # Use locator(..., has_text=regex) instead of embedding re.compile(...) in selector strings.
    TOGGLE_CONTAINER_SELECTOR = "div.truncate"
    THOUGHT_TOGGLE_TEXT_RE = re.compile(r"Thought for\s*\d+\s*s", re.IGNORECASE)

    CONTENT_SELECTOR = "div.text-token-text-secondary div.markdown.prose"


    def save_thought_data(thread_id: str, thought_index: int, text: str) -> None:
        """Saves the scraped text to a file."""
        safe_thread_id = thread_id.rstrip("/").split("/")[-1]
        folder_path = os.path.join(DATA_FOLDER, safe_thread_id)
        os.makedirs(folder_path, exist_ok=True)

        filename = os.path.join(folder_path, f"thought_{thought_index}.txt")
        with open(filename, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"  [Saved] {filename}")


    def scrape_page_thoughts(page, thread_url: str) -> None:
        """Scrapes all 'Thought' blocks on the current chat thread page."""
        try:
            page.wait_for_selector('div[data-message-author-role="assistant"]', timeout=5000)
        except Exception:
            print("  [Info] Page loaded, but no standard messages found immediately.")

        thought_toggles = page.locator(
            TOGGLE_CONTAINER_SELECTOR,
            has_text=THOUGHT_TOGGLE_TEXT_RE,
        ).all()

        if not thought_toggles:
            print("  [Info] No thoughts found in this thread.")
            return

        print(f"  [Found] {len(thought_toggles)} thought bubbles.")

        content_locator = page.locator(CONTENT_SELECTOR)

        for index, toggle in enumerate(thought_toggles):
            try:
                toggle.scroll_into_view_if_needed()

                before_count = content_locator.count()

                if toggle.is_visible():
                    toggle.click(force=True)

                page.wait_for_timeout(300)

                # Prefer newly-rendered content if clicking increased count.
                try:
                    page.wait_for_function(
                        "([sel, before]) => document.querySelectorAll(sel).length > before",
                        arg=[CONTENT_SELECTOR, before_count],
                        timeout=2500,
                    )
                except Exception:
                    pass

                after_count = content_locator.count()
                if after_count <= 0:
                    continue

                if after_count > before_count:
                    target_idx = before_count
                elif index < after_count:
                    target_idx = index
                else:
                    target_idx = after_count - 1

                text_content = content_locator.nth(target_idx).inner_text()
                save_thought_data(thread_url, index, text_content)

            except Exception as e:
                print(f"  [Error] Failed to scrape thought {index}: {e}")


    def run() -> None:
        global SCRAPED_URLS

        with sync_playwright() as p:
            try:
                browser = p.chromium.connect_over_cdp(CDP_URL)
            except Exception:
                print("❌ Could not connect. Run Chrome with: --remote-debugging-port=9222")
                return

            context = browser.contexts[0] if browser.contexts else browser.new_context()
            page = context.pages[0] if context.pages else context.new_page()
            page.bring_to_front()
            print(f"✅ Connected to: {page.title()}")

            print("🔍 Scanning sidebar for projects...")
            page.wait_for_selector("nav", timeout=5000)

            project_elements = page.locator(SIDEBAR_PROJECT_SELECTOR).all()
            project_urls = []

            for el in project_elements:
                href = el.get_attribute("href")
                if not href:
                    continue

                full_url = (BASE_URL + href) if href.startswith("/") else href
                if full_url not in project_urls:
                    project_urls.append(full_url)

            print(f"📋 Found {len(project_urls)} unique projects.")

            all_chat_urls = set()

            for i, project_url in enumerate(project_urls):
                print(f"\n--- Scanning Project {i+1}/{len(project_urls)} ---")
                print(f"🔗 Going to: {project_url}")

                page.goto(project_url)
                page.wait_for_load_state("networkidle")
                time.sleep(1.5)

                thread_links = page.locator(PROJECT_PAGE_THREAD_SELECTOR).all()
                found_count = 0

                for link in thread_links:
                    url_path = link.get_attribute("href")
                    if not url_path or "/c/" not in url_path:
                        continue

                    full_url = (BASE_URL + url_path) if url_path.startswith("/") else url_path
                    if full_url not in all_chat_urls:
                        all_chat_urls.add(full_url)
                        found_count += 1

                print(f"   Found {found_count} threads in this project.")

            print(f"\n✅ Total unique chat threads gathered: {len(all_chat_urls)}")

            sorted_urls = sorted(all_chat_urls)

            for i, url in enumerate(sorted_urls):
                if url in SCRAPED_URLS:
                    continue

                print(f"\n--- Scraping Thread {i+1}/{len(sorted_urls)} ---")
                print(f"🔗 Processing: {url}")

                page.goto(url)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2)

                scrape_page_thoughts(page, url)
                SCRAPED_URLS.add(url)

            print("\n🎉 All scraping complete.")


    if __name__ == "__main__":
        run()


\[Fix GUI scraper to use correct regex-based toggle selection + always call `finish_scraping()` via `finally` to avoid stuck UI state.\]

    import tkinter as tk
    from tkinter import ttk, scrolledtext
    import threading
    import os
    import time
    import re
    import platform
    import subprocess
    from playwright.sync_api import sync_playwright

    # --- SCRAPING CONFIGURATION & SELECTORS ---
    CDP_URL_DEFAULT = "http://localhost:9222"
    BASE_URL = "https://chatgpt.com"

    SIDEBAR_PROJECT_SELECTOR = 'nav a[href*="/project/"]'
    PROJECT_PAGE_THREAD_SELECTOR = 'main a[href*="/c/"]'

    TOGGLE_CONTAINER_SELECTOR = "div.truncate"
    THOUGHT_TOGGLE_TEXT_RE = re.compile(r"Thought for\s*\d+\s*s", re.IGNORECASE)

    CONTENT_SELECTOR = "div.text-token-text-secondary div.markdown.prose"


    class ScraperApp:
        def __init__(self, root: tk.Tk):
            self.root = root
            self.root.title("Chatbot Thought Scraper")
            self.root.geometry("600x700")

            self.is_running = False
            self.stop_event = threading.Event()
            self.scraped_urls: set[str] = set()

            # --- UI LAYOUT ---
            config_frame = ttk.LabelFrame(root, text="Configuration", padding=10)
            config_frame.pack(fill="x", padx=10, pady=5)

            ttk.Label(config_frame, text="Chrome Debug URL:").grid(row=0, column=0, sticky="w")
            self.url_entry = ttk.Entry(config_frame, width=30)
            self.url_entry.insert(0, CDP_URL_DEFAULT)
            self.url_entry.grid(row=0, column=1, padx=5, sticky="ew")

            ttk.Label(config_frame, text="Output Folder:").grid(row=1, column=0, sticky="w")
            self.folder_entry = ttk.Entry(config_frame, width=30)
            self.folder_entry.insert(0, "data")
            self.folder_entry.grid(row=1, column=1, padx=5, sticky="ew")

            ctrl_frame = ttk.Frame(root, padding=10)
            ctrl_frame.pack(fill="x", padx=10)

            self.start_btn = ttk.Button(ctrl_frame, text="Start Scraping", command=self.start_thread)
            self.start_btn.pack(side="left", padx=5)

            self.stop_btn = ttk.Button(ctrl_frame, text="Stop", command=self.stop_scraping, state="disabled")
            self.stop_btn.pack(side="left", padx=5)

            self.open_btn = ttk.Button(ctrl_frame, text="Open Data Folder", command=self.open_data_folder)
            self.open_btn.pack(side="right", padx=5)

            log_frame = ttk.LabelFrame(root, text="Live Logs", padding=10)
            log_frame.pack(fill="both", expand=True, padx=10, pady=5)

            self.log_area = scrolledtext.ScrolledText(log_frame, state="disabled", height=20)
            self.log_area.pack(fill="both", expand=True)
            self.log_area.tag_config("info", foreground="black")
            self.log_area.tag_config("success", foreground="green")
            self.log_area.tag_config("error", foreground="red")
            self.log_area.tag_config("warning", foreground="#cc6600")

        def log(self, message: str, level: str = "info") -> None:
            def _log():
                self.log_area.config(state="normal")
                self.log_area.insert(tk.END, message + "\n", level)
                self.log_area.see(tk.END)
                self.log_area.config(state="disabled")

            self.root.after(0, _log)

        def start_thread(self) -> None:
            self.is_running = True
            self.stop_event.clear()
            self.start_btn.config(state="disabled")
            self.stop_btn.config(state="normal")
            self.url_entry.config(state="disabled")
            self.folder_entry.config(state="disabled")

            t = threading.Thread(target=self.run_scraper, daemon=True)
            t.start()

        def stop_scraping(self) -> None:
            if self.is_running:
                self.log("Stopping... finishing current action.", "warning")
                self.stop_event.set()

        def finish_scraping(self) -> None:
            self.is_running = False
            self.start_btn.config(state="normal")
            self.stop_btn.config(state="disabled")
            self.url_entry.config(state="normal")
            self.folder_entry.config(state="normal")
            self.log("--- Process Stopped/Finished ---", "info")

        def open_data_folder(self) -> None:
            folder = self.folder_entry.get()
            os.makedirs(folder, exist_ok=True)

            if platform.system() == "Windows":
                os.startfile(folder)
            elif platform.system() == "Darwin":
                subprocess.Popen(["open", folder])
            else:
                subprocess.Popen(["xdg-open", folder])

        def save_thought_data(self, folder: str, thread_id: str, thought_index: int, text: str) -> None:
            safe_thread_id = thread_id.rstrip("/").split("/")[-1]
            folder_path = os.path.join(folder, safe_thread_id)
            os.makedirs(folder_path, exist_ok=True)

            filename = os.path.join(folder_path, f"thought_{thought_index}.txt")
            with open(filename, "w", encoding="utf-8") as f:
                f.write(text)
            self.log(f"  [Saved] {filename}", "success")

        def run_scraper(self) -> None:
            cdp_url = self.url_entry.get().strip()
            data_folder = self.folder_entry.get().strip() or "data"

            try:
                with sync_playwright() as p:
                    try:
                        self.log(f"Connecting to Chrome at {cdp_url}...", "info")
                        browser = p.chromium.connect_over_cdp(cdp_url)
                    except Exception as e:
                        self.log(f"Connection Failed: {e}", "error")
                        self.log("Ensure Chrome is running with --remote-debugging-port=9222", "error")
                        return

                    context = browser.contexts[0] if browser.contexts else browser.new_context()
                    page = context.pages[0] if context.pages else context.new_page()
                    page.bring_to_front()
                    self.log(f"Connected to tab: {page.title()}", "success")

                    if self.stop_event.is_set():
                        return

                    self.log("Scanning sidebar for projects...", "info")
                    try:
                        page.wait_for_selector("nav", timeout=5000)
                        project_elements = page.locator(SIDEBAR_PROJECT_SELECTOR).all()
                        project_urls: list[str] = []

                        for el in project_elements:
                            href = el.get_attribute("href")
                            if not href:
                                continue
                            full_url = (BASE_URL + href) if href.startswith("/") else href
                            if full_url not in project_urls:
                                project_urls.append(full_url)

                        self.log(f"Found {len(project_urls)} projects.", "info")
                    except Exception as e:
                        self.log(f"Error scanning projects: {e}", "error")
                        project_urls = []

                    all_chat_urls: set[str] = set()
                    for i, p_url in enumerate(project_urls):
                        if self.stop_event.is_set():
                            break

                        self.log(f"Scanning Project {i+1}/{len(project_urls)}...", "info")
                        try:
                            page.goto(p_url)
                            page.wait_for_load_state("networkidle")
                            time.sleep(1)

                            thread_links = page.locator(PROJECT_PAGE_THREAD_SELECTOR).all()
                            count = 0
                            for link in thread_links:
                                url_path = link.get_attribute("href")
                                if not url_path or "/c/" not in url_path:
                                    continue
                                full_url = (BASE_URL + url_path) if url_path.startswith("/") else url_path
                                if full_url not in all_chat_urls:
                                    all_chat_urls.add(full_url)
                                    count += 1

                            self.log(f"  Found {count} threads.", "info")
                        except Exception as e:
                            self.log(f"  Failed to scan project: {e}", "error")

                    sorted_urls = sorted(all_chat_urls)
                    self.log(f"Starting scrape of {len(sorted_urls)} threads...", "success")

                    content_locator = page.locator(CONTENT_SELECTOR)

                    for i, url in enumerate(sorted_urls):
                        if self.stop_event.is_set():
                            break
                        if url in self.scraped_urls:
                            continue

                        self.log(f"[{i+1}/{len(sorted_urls)}] Processing: {url.split('/')[-1]}", "info")

                        try:
                            page.goto(url)
                            page.wait_for_load_state("domcontentloaded")
                            time.sleep(2)

                            toggles = page.locator(
                                TOGGLE_CONTAINER_SELECTOR,
                                has_text=THOUGHT_TOGGLE_TEXT_RE,
                            ).all()

                            if not toggles:
                                self.log("  No thoughts found.", "warning")
                            else:
                                self.log(f"  Found {len(toggles)} thoughts.", "info")

                                for idx, toggle in enumerate(toggles):
                                    if self.stop_event.is_set():
                                        break

                                    try:
                                        toggle.scroll_into_view_if_needed()
                                        before_count = content_locator.count()

                                        if toggle.is_visible():
                                            toggle.click(force=True)

                                        page.wait_for_timeout(250)

                                        try:
                                            page.wait_for_function(
                                                "([sel, before]) => document.querySelectorAll(sel).length > before",
                                                arg=[CONTENT_SELECTOR, before_count],
                                                timeout=2500,
                                            )
                                        except Exception:
                                            pass

                                        after_count = content_locator.count()
                                        if after_count <= 0:
                                            continue

                                        if after_count > before_count:
                                            target_idx = before_count
                                        elif idx < after_count:
                                            target_idx = idx
                                        else:
                                            target_idx = after_count - 1

                                        txt = content_locator.nth(target_idx).inner_text()
                                        self.save_thought_data(data_folder, url, idx, txt)

                                    except Exception as e:
                                        self.log(f"  Error scraping thought {idx}: {e}", "error")

                            self.scraped_urls.add(url)

                        except Exception as e:
                            self.log(f"  Error on thread: {e}", "error")

            except Exception as e:
                self.log(f"Unhandled error: {e}", "error")
            finally:
                self.root.after(0, self.finish_scraping)


    if __name__ == "__main__":
        root = tk.Tk()
        app = ScraperApp(root)
        root.mainloop()

