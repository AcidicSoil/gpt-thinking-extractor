import os
import pytest
from gpt_thinking_extractor.scraper_engine import ScraperEngine

@pytest.fixture
def engine(tmp_path):
    output = tmp_path / "data"
    db = tmp_path / "test.db"
    selectors = tmp_path / "selectors.json"
    with open(selectors, "w") as f:
        f.write('{"TEST": "div.test"}')
    return ScraperEngine(str(output), str(selectors), str(db))

def test_sanitize_filename(engine):
    assert engine.sanitize_filename("foo:bar") == "foo_bar"
    assert engine.sanitize_filename("foo?bar") == "foo_bar"
    assert engine.sanitize_filename("../foo") == "_foo"
    assert engine.sanitize_filename("  clean  ") == "clean"

def test_extract_project_id(engine):
    # With name slug
    url1 = "https://chatgpt.com/g/g-p-69407bf8ed248191abe7f211741f7db9-transcript-cleaner-v2/project"
    assert engine.extract_project_id(url1) == "g-p-69407bf8ed248191abe7f211741f7db9"
    
    # Without name slug
    url2 = "/g/g-p-69407bf8ed248191abe7f211741f7db9/c/694a1150-e88c-8326-a1ad-8bc57455e363"
    assert engine.extract_project_id(url2) == "g-p-69407bf8ed248191abe7f211741f7db9"
    
    # Non-project URL
    url3 = "https://chatgpt.com/c/69420496-2e70-832e-a287-c3f8d6e9be36"
    assert engine.extract_project_id(url3) is None

def test_db_persistence(engine):
    url = "https://example.com/c/123"
    assert not engine.is_url_scraped(url)
    engine.mark_url_scraped(url, "Title")
    assert engine.is_url_scraped(url)
    engine.close()
    eng2 = ScraperEngine(engine.output_folder, engine.selectors_path, engine.db_path)
    assert eng2.is_url_scraped(url)
    eng2.close()
