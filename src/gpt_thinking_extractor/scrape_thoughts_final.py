import os
import sys
import time
import argparse
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv

try:
    from .scraper_engine import ScraperEngine
except ImportError:
    from scraper_engine import ScraperEngine

load_dotenv()

DATA_FOLDER = os.getenv("OUTPUT_FOLDER", "data")
CDP_URL = os.getenv("CHROME_DEBUG_URL", "http://localhost:9222")

def scrape_page_thoughts(page, thread_url, engine, selector=None):
    try:
        page.wait_for_selector('div[data-message-author-role="assistant"]', timeout=5000)
    except:
        print("  [Info] Page loaded, but no standard messages found immediately.")

    if not selector:
        candidates = engine.get_selector("THOUGHT_TOGGLE_CANDIDATES")
        selector = candidates[0] if isinstance(candidates, list) else candidates

    unique_toggles = engine.get_unique_toggles(page, selector)

    if not unique_toggles:
        print(f"  [Info] No visible thoughts found using selector: {selector}")
        return

    print(f"  [Found] {len(unique_toggles)} unique thought blocks.")

    for index, toggle in enumerate(unique_toggles):
        try:
            toggle.scroll_into_view_if_needed()
            toggle.click(force=True)
            
            # Wait for content to appear (Mutation await)
            content_selector = engine.get_selector("THOUGHT_CONTENT")
            try:
                page.wait_for_selector(content_selector, state="visible", timeout=5000)
                
                # Extract all content nodes for this block, sorted chronologically
                full_text = engine.extract_ordered_content(page)
                
                if full_text:
                    saved_path = engine.save_thought(thread_url, index, full_text)
                    if saved_path:
                        print(f"  [Saved] {saved_path}")
                else:
                    print(f"  [Warning] Thought block {index} was empty.")
                    
            except Exception as e:
                print(f"  [Error] Content extraction timed out: {e}")

        except Exception as e:
            print(f"  [Error] Failed to interact with toggle {index}: {e}")

def run():
    parser = argparse.ArgumentParser(description="GPT Thinking Extractor CLI")
    parser.add_argument("--global-scan", action="store_true", help="Enable global project/history scanning")
    args = parser.parse_args()

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
        
        all_chat_threads = {}
        current_url = page.url
        active_project_id = engine.extract_project_id(current_url)
        
        if active_project_id:
            print(f"🔒 Scoping to Project ID: {active_project_id}")
        else:
            print("🔓 Global mode (No specific project scope).")

        if "/project" in current_url or "/g/" in current_url:
            print("🚀 Active Project Context Detected.")
            try:
                page.wait_for_selector('nav', timeout=3000)
                thread_selector = engine.get_selector("SIDEBAR_THREAD")
                thread_links = page.locator(thread_selector).all()
                for link in thread_links:
                    href = link.get_attribute("href")
                    # Capture title (text of the link)
                    title = link.inner_text().split('\n')[0]
                    
                    if href and "/c/" in href:
                        if active_project_id and active_project_id not in href:
                            continue
                        full_url = "https://chatgpt.com" + href if href.startswith("/") else href
                        all_chat_threads[full_url] = title
                print(f"   Found {len(all_chat_threads)} threads in active project.")
            except Exception as e:
                print(f"   [Warning] Failed to scan sidebar: {e}")
        
        if "/c/" in current_url:
             if not active_project_id or (active_project_id in current_url):
                 all_chat_threads[current_url] = "Current Page"

        if not all_chat_threads:
             print("⚠️ No threads found matching scope.")
             return

        # --- AUDIT ---
        print("\n🕵️ Starting Audit Phase...")
        sorted_urls = sorted(list(all_chat_threads.keys()))
        audit_results = []
        
        for i, url in enumerate(sorted_urls):
            title = all_chat_threads[url]
            print(f"   [{i+1}/{len(sorted_urls)}] Auditing: {title[:20]}...", end="\r")
            try:
                page.goto(url)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(1.5)
                
                count, selector = engine.audit_thread(page, url)
                audit_results.append({
                    "url": url, "title": title, "count": count, "selector": selector
                })
            except Exception as e:
                print(f"\n   [Error] Audit failed for {url}: {e}")
        
        print("\n\n📊 Audit Summary:")
        print(f"{ 'Title':<30} | {'Thoughts':<8} | {'UUID'}")
        print("-" * 70)
        
        to_scrape = []
        for res in audit_results:
            uuid = res["url"].split('/')[-1][:8]
            print(f"{res['title'][:30]:<30} | {res['count']:<8} | {uuid}")
            if res["count"] > 0:
                to_scrape.append(res)
        
        print("-" * 70)
        
        if not to_scrape:
            print("❌ No thoughts found. Aborting.")
            return

        confirm = input(f"\nProceed to scrape {len(to_scrape)} threads? [y/N]: ").strip().lower()
        if confirm != 'y': return

        # --- EXECUTION ---
        for i, item in enumerate(to_scrape):
            url = item["url"]
            if engine.is_url_scraped(url): continue
            print(f"\n--- Scraping [{i+1}/{len(to_scrape)}]: {item['title']} ---")
            try:
                page.goto(url)
                page.wait_for_load_state("domcontentloaded")
                time.sleep(2) 
                scrape_page_thoughts(page, url, engine, selector=item["selector"])
                engine.mark_url_scraped(url, item['title'])
            except Exception as e:
                 print(f"   [Error] Failed: {e}")

    engine.close()

if __name__ == "__main__":
    run()
