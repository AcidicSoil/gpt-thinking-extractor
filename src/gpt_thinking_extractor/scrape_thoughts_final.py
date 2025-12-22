import os
import sys
import time
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
DATA_FOLDER = os.getenv("OUTPUT_FOLDER", "data")
CDP_URL = os.getenv("CHROME_DEBUG_URL", "http://localhost:9222")

def scrape_page_thoughts(page, thread_url, engine):
    """Scrapes all 'Thought' blocks on the current chat thread page."""
    
    # Wait for the chat to load
    try:
        page.wait_for_selector('div[data-message-author-role="assistant"]', timeout=5000)
    except:
        print("  [Info] Page loaded, but no standard messages found immediately.")

    # Find all "Thought" toggles using selector from engine
    toggle_selector = engine.get_selector("THOUGHT_TOGGLE")
    thought_toggles = page.locator(toggle_selector).all()

    if not thought_toggles:
        print("  [Info] No thoughts found in this thread.")
        return

    print(f"  [Found] {len(thought_toggles)} thought bubbles.")

    content_selector = engine.get_selector("THOUGHT_CONTENT")

    for index, toggle in enumerate(thought_toggles):
        try:
            # Scroll into view
            toggle.scroll_into_view_if_needed()
            
            # Click the toggle
            if toggle.is_visible():
                toggle.click(force=True)
                
            # Wait for content to appear (better than hard sleep)
            page.wait_for_timeout(600) 

            # LOCATE CONTENT
            content_locator = page.locator(content_selector)
            
            if index < content_locator.count():
                text_content = content_locator.nth(index).inner_text()
                saved_path = engine.save_thought(thread_url, index, text_content)
                if saved_path:
                    print(f"  [Saved] {saved_path}")
            else:
                text_content = content_locator.last.inner_text()
                saved_path = engine.save_thought(thread_url, index, text_content)
                if saved_path:
                    print(f"  [Saved] {saved_path}")

        except Exception as e:
            print(f"  [Error] Failed to scrape thought {index}: {e}")

def run():
    engine = ScraperEngine(output_folder=DATA_FOLDER)
    
    with sync_playwright() as p:
        try:
            browser = p.chromium.connect_over_cdp(CDP_URL)
        except Exception:
            print(f"❌ Could not connect to {CDP_URL}. Run Chrome with: --remote-debugging-port=9222")
            return

        context = browser.contexts[0]
        page = context.pages[0]
        page.bring_to_front() 
        print(f"✅ Connected to: {page.title()}")
        
        # --- PHASE 1: FIND PROJECTS ---
        print("🔍 Scanning sidebar for projects...")
        try:
            page.wait_for_selector('nav', timeout=5000)
        except:
            print("  [Warning] Nav not found or timed out.")

        sidebar_selector = engine.get_selector("SIDEBAR_PROJECT")
        project_elements = page.locator(sidebar_selector).all()
        project_urls = []
        
        for el in project_elements:
            href = el.get_attribute("href")
            if href:
                full_url = "https://chatgpt.com" + href if href.startswith("/") else href
                if full_url not in project_urls:
                    project_urls.append(full_url)
        
        print(f"📋 Found {len(project_urls)} unique projects.")

        # --- PHASE 2: GATHER CHAT THREADS ---
        all_chat_urls = set()
        thread_selector = engine.get_selector("PROJECT_PAGE_THREAD")

        for i, project_url in enumerate(project_urls):
            print(f"\n--- Scanning Project {i+1}/{len(project_urls)} ---")
            print(f"🔗 Going to: {project_url}")
            
            page.goto(project_url)
            page.wait_for_load_state("networkidle")
            time.sleep(1.5) # Wait for list to render
            
            thread_links = page.locator(thread_selector).all()
            
            found_count = 0
            for link in thread_links:
                url_path = link.get_attribute("href")
                if url_path and "/c/" in url_path:
                    full_url = "https://chatgpt.com" + url_path if url_path.startswith("/") else url_path
                    all_chat_urls.add(full_url)
                    found_count += 1
            
            print(f"   Found {found_count} threads in this project.")
        
        print(f"\n✅ Total unique chat threads gathered: {len(all_chat_urls)}")
        
        # --- PHASE 3: EXTRACT THOUGHTS ---
        sorted_urls = sorted(list(all_chat_urls))
        
        for i, url in enumerate(sorted_urls):
            if engine.is_url_scraped(url):
                print(f"Skipping already scraped: {url}")
                continue
                
            print(f"\n--- Scraping Thread {i+1}/{len(sorted_urls)} ---")
            print(f"🔗 Processing: {url}")
            
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2) 
            
            scrape_page_thoughts(page, url, engine)
            engine.mark_url_scraped(url)

        print("\n🎉 All scraping complete.")
    
    engine.close()

if __name__ == "__main__":
    run()