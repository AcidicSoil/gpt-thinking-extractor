import os
import re
import time
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- CONFIGURATION ---
DATA_FOLDER = os.getenv("OUTPUT_FOLDER", "data")
CDP_URL = os.getenv("CHROME_DEBUG_URL", "http://localhost:9222")

# Set to store URLs we have already scraped to prevent duplication
SCRAPED_URLS = set()

# --- SELECTORS (Derived from screenshots) ---

# 1. Sidebar Project Links
SIDEBAR_PROJECT_SELECTOR = 'nav a[href*="/project/"]'

# 2. Project Page Thread Links
# We look inside the 'main' content area for links containing '/c/' (chat threads)
PROJECT_PAGE_THREAD_SELECTOR = 'main a[href*="/c/"]'

# 3. Thought Toggle Button
# Matches "Thought for 23s", "Thought for 120s", etc.
TOGGLE_SELECTOR = 'div.truncate:has-text(re.compile(r"Thought for \d+s"))'

# 4. Thinking Content
# The text lives inside a markdown div within a secondary text container
CONTENT_SELECTOR = 'div.text-token-text-secondary div.markdown.prose'


def save_thought_data(thread_id, thought_index, text):
    """Saves the scraped text to a file."""
    # Creates a clean filename from the chat ID
    safe_thread_id = thread_id.split('/')[-1]
    folder_path = os.path.join(DATA_FOLDER, safe_thread_id)
    os.makedirs(folder_path, exist_ok=True)
    
    filename = f"{folder_path}/thought_{thought_index}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"  [Saved] {filename}")

def scrape_page_thoughts(page, thread_url):
    """Scrapes all 'Thought' blocks on the current chat thread page."""
    
    # Wait for the chat to load (look for the message container)
    try:
        page.wait_for_selector('div[data-message-author-role="assistant"]', timeout=5000)
    except:
        print("  [Info] Page loaded, but no standard messages found immediately.")

    # Find all "Thought" toggles
    thought_toggles = page.locator(TOGGLE_SELECTOR).all()

    if not thought_toggles:
        print("  [Info] No thoughts found in this thread.")
        return

    print(f"  [Found] {len(thought_toggles)} thought bubbles.")

    for index, toggle in enumerate(thought_toggles):
        try:
            # Scroll into view
            toggle.scroll_into_view_if_needed()
            
            # Click the toggle
            if toggle.is_visible():
                toggle.click(force=True)
                
            # Small buffer for the expansion animation
            page.wait_for_timeout(600) 

            # LOCATE CONTENT
            content_locator = page.locator(CONTENT_SELECTOR)
            
            # We assume sequential order (1st toggle opens 1st content block)
            if index < content_locator.count():
                text_content = content_locator.nth(index).inner_text()
                save_thought_data(thread_url, index, text_content)
            else:
                # If indices desync, try grabbing the last visible one
                text_content = content_locator.last.inner_text()
                save_thought_data(thread_url, index, text_content)

        except Exception as e:
            print(f"  [Error] Failed to scrape thought {index}: {e}")

def run():
    global SCRAPED_URLS
    
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
        page.wait_for_selector('nav', timeout=5000)
        
        # Get all project links
        project_elements = page.locator(SIDEBAR_PROJECT_SELECTOR).all()
        project_urls = []
        
        for el in project_elements:
            href = el.get_attribute("href")
            if href:
                # Build full URL
                full_url = "https://chatgpt.com" + href if href.startswith("/") else href
                if full_url not in project_urls:
                    project_urls.append(full_url)
        
        print(f"📋 Found {len(project_urls)} unique projects.")

        # --- PHASE 2: GATHER CHAT THREADS ---
        all_chat_urls = set()
        
        for i, project_url in enumerate(project_urls):
            print(f"\n--- Scanning Project {i+1}/{len(project_urls)} ---")
            print(f"🔗 Going to: {project_url}")
            
            page.goto(project_url)
            page.wait_for_load_state("networkidle")
            time.sleep(1.5) # Wait for list to render
            
            # Find chat links in the MAIN area (ignoring sidebar)
            thread_links = page.locator(PROJECT_PAGE_THREAD_SELECTOR).all()
            
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
        # Sort urls to make progress predictable
        sorted_urls = sorted(list(all_chat_urls))
        
        for i, url in enumerate(sorted_urls):
            if url in SCRAPED_URLS:
                continue
                
            print(f"\n--- Scraping Thread {i+1}/{len(sorted_urls)} ---")
            print(f"🔗 Processing: {url}")
            
            page.goto(url)
            page.wait_for_load_state("domcontentloaded")
            time.sleep(2) # Wait for dynamic elements (thought bubbles) to hydrate
            
            scrape_page_thoughts(page, url)
            SCRAPED_URLS.add(url)

        print("\n🎉 All scraping complete.")

if __name__ == "__main__":
    run()