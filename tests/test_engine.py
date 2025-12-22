import os
import pytest
from gpt_thinking_extractor.scraper_engine import ScraperEngine

@pytest.fixture
def engine(tmp_path):
    # Use temporary paths for db and output
    output = tmp_path / "data"
    db = tmp_path / "test.db"
    selectors = tmp_path / "selectors.json"
    
    # Create dummy selectors file
    with open(selectors, "w") as f:
        f.write('{"TEST": "div.test"}')
        
    eng = ScraperEngine(str(output), str(selectors), str(db))
    yield eng
    eng.close()

def test_sanitize_filename(engine):
    # Windows reserved chars
    assert engine.sanitize_filename("foo:bar") == "foo_bar"
    assert engine.sanitize_filename("foo?bar") == "foo_bar"
    assert engine.sanitize_filename('foo"bar') == "foo_bar"
    assert engine.sanitize_filename("foo/bar") == "foo_bar"
    assert engine.sanitize_filename("foo\\bar") == "foo_bar"
    
    # Path traversal attempt
    assert engine.sanitize_filename("../foo") == "_foo"
    
    # Edge cases
    assert engine.sanitize_filename("  clean  ") == "clean"
    assert engine.sanitize_filename("toolong" * 20) == ("toolong" * 20)[:100]

def test_db_persistence(engine):
    url = "https://example.com/c/123"
    assert not engine.is_url_scraped(url)
    
    engine.mark_url_scraped(url)
    assert engine.is_url_scraped(url)
    
    # Re-connect to verify persistence
    engine.close()
    
    # New engine instance connected to same DB
    eng2 = ScraperEngine(engine.output_folder, engine.selectors_path, engine.db_path)
    assert eng2.is_url_scraped(url)
    eng2.close()

def test_save_thought(engine):
    url = "https://example.com/c/uuid-1234:5678"
    content = "Thinking..."
    
    saved_path = engine.save_thought(url, 0, content)
    
    assert saved_path is not None
    assert os.path.exists(saved_path)
    
    # Check content
    with open(saved_path, "r", encoding="utf-8") as f:
        read_content = f.read()
    assert read_content == content
    
    # Check folder name sanitization
    folder_name = os.path.basename(os.path.dirname(saved_path))
    assert ":" not in folder_name
    assert "uuid-1234_5678" in folder_name