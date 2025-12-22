import pytest
from unittest.mock import MagicMock
from gpt_thinking_extractor.scraper_engine import ScraperEngine

@pytest.fixture
def engine(tmp_path):
    output = tmp_path / "data"
    db = tmp_path / "test.db"
    selectors = tmp_path / "selectors.json"
    # Update to new structure with CANDIDATES
    with open(selectors, "w") as f:
        f.write('{"THOUGHT_TOGGLE_CANDIDATES": ["div.primary", "div.fallback"]}')
    return ScraperEngine(str(output), str(selectors), str(db))

def create_mock_element(x, y):
    el = MagicMock()
    el.is_visible.return_value = True
    el.bounding_box.return_value = {'x': x, 'y': y, 'width': 10, 'height': 10}
    return el

def test_audit_thread_primary_success(engine):
    mock_page = MagicMock()
    mock_locator = MagicMock()
    
    # Create 5 unique elements
    elements = [create_mock_element(i*20, 0) for i in range(5)]
    mock_locator.all.return_value = elements
    mock_locator.count.return_value = 5 # Used for quick check inside get_unique_toggles if needed, mostly .all() matters

    # Setup: Primary selector finds elements
    def get_locator(selector):
        if selector == "div.primary":
            return mock_locator
        return MagicMock(all=lambda: [])
        
    mock_page.locator.side_effect = get_locator
    
    count, selector = engine.audit_thread(mock_page, "http://example.com")
    
    assert count == 5
    assert selector == "div.primary"

def test_audit_thread_fallback_success(engine):
    mock_page = MagicMock()
    fallback_loc = MagicMock()
    
    # Create 3 unique elements
    elements = [create_mock_element(i*20, 0) for i in range(3)]
    fallback_loc.all.return_value = elements

    # Setup: Primary finds 0, Fallback finds 3
    def get_locator(selector):
        if selector == "div.primary":
            return MagicMock(all=lambda: [])
        if selector == "div.fallback":
            return fallback_loc
        return MagicMock(all=lambda: [])
        
    mock_page.locator.side_effect = get_locator
    
    count, selector = engine.audit_thread(mock_page, "http://example.com")
    
    assert count == 3
    assert selector == "div.fallback"

def test_audit_thread_none_found(engine):
    mock_page = MagicMock()
    # Return empty lists for all calls
    mock_page.locator.return_value.all.return_value = []
    
    count, selector = engine.audit_thread(mock_page, "http://example.com")
    
    assert count == 0
    assert selector is None
