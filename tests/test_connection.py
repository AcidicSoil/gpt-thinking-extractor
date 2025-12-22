import os
import pytest
from unittest.mock import MagicMock, patch
from playwright.sync_api import Error as PlaywrightError
from gpt_thinking_extractor.scrape_thoughts_final import run

# Mock the ScraperEngine to avoid file I/O and DB ops during connection tests
@pytest.fixture
def mock_engine():
    with patch('gpt_thinking_extractor.scrape_thoughts_final.ScraperEngine') as MockEngine:
        instance = MockEngine.return_value
        # Mock selector retrieval to return dummy strings
        instance.get_selector.return_value = "div.test"
        instance.is_url_scraped.return_value = False
        yield instance

def test_custom_cdp_url_connection(mock_engine):
    """
    Test that the scraper connects to the specific CDP URL provided.
    This verifies the mechanism used for WSL (connecting to Windows Host IP).
    """
    custom_ip = "http://172.17.0.1:9222"
    
    # Since CDP_URL is a module-level global loaded at import time, 
    # we must patch it directly rather than setting os.environ.
    with patch('gpt_thinking_extractor.scrape_thoughts_final.CDP_URL', custom_ip):
        with patch('gpt_thinking_extractor.scrape_thoughts_final.sync_playwright') as mock_playwright:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()
            
            # Setup mock chain
            mock_p = mock_playwright.return_value.__enter__.return_value
            mock_p.chromium.connect_over_cdp.return_value = mock_browser
            mock_browser.contexts = [mock_context]
            mock_context.pages = [mock_page]
            mock_page.title.return_value = "Mock ChatGPT"
            
            # Run the script logic (will use the mocked URL)
            with patch('builtins.print'):
                run()
                
            # ASSERTION: Verify connect_over_cdp was called with our custom "WSL" IP
            mock_p.chromium.connect_over_cdp.assert_called_once_with(custom_ip)

def test_connection_failure_handling(mock_engine):
    """
    Test that the application handles connection failures gracefully.
    Critical for WSL users where networking issues are common.
    """
    # Patch CDP_URL to ensure we control the connection target
    with patch('gpt_thinking_extractor.scrape_thoughts_final.CDP_URL', "http://bad-url:9222"):
        with patch('gpt_thinking_extractor.scrape_thoughts_final.sync_playwright') as mock_playwright:
            mock_p = mock_playwright.return_value.__enter__.return_value
            
            # Simulate a connection error
            mock_p.chromium.connect_over_cdp.side_effect = Exception("Connection refused")
            
            with patch('builtins.print') as mock_print:
                run()
                
                # ASSERTION: Verify that the error was caught and logged
                # We look for the specific error message defined in scrape_thoughts_final.py
                args, _ = mock_print.call_args
                assert "Could not connect to" in args[0]