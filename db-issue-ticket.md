Title:

* Store scraped content payloads; `scraped_urls.db` currently holds only URL metadata

Summary:

* User expected transcripts/HTML/JSON “data” inside `scraped_urls.db` but the DB schema only tracks `url`, `scraped_at`, and `title`, so no payload exists there.
* Current setup appears to use SQLite as a URL index/queue rather than a content store, leaving users unable to locate captured artifacts.

Background / Context:

* User asked: “Where’s the data at or do I need to configure more fields? … for all the data types?”
* Assistant identified `scraped_urls.db` as a tracker DB (URL index/queue) and suggested the actual payload is likely written to the filesystem (e.g., `data/`, `archive/`) with some existing dumps like `debug_page_dump.html`, `activity_drawer.html`, `gui-output.md`.

Current Behavior (Actual):

* `scraped_urls.db` has no transcript/HTML/JSON payload fields; only URL metadata is stored (`url`, `scraped_at`, `title`).
* `title` is “mostly NULL,” indicating title extraction isn’t happening for those pages or the metadata extraction step isn’t being run.

Expected Behavior:

* Scraped page payloads (or pointers to those payload files) are discoverable and queryable.
* Metadata fields needed to support “all data types” are persisted consistently (status, HTTP status, content type, artifact location, etc.).

Requirements:

* Clarify and standardize where scraped payloads are stored (filesystem vs SQLite) so users can reliably find the “data.”
* If using SQLite for tracking only: ensure the filesystem output location is consistent and documented, and per-URL records link to saved artifacts (path/ID).
* If using SQLite to index artifacts: expand schema to persist metadata and artifact pointers (minimal approach; avoid huge blobs).

  * Suggested columns:

    * `status` (TEXT)
    * `http_status` (INTEGER)
    * `content_type` (TEXT)
    * `artifact_path` (TEXT)
    * `sha256` (TEXT)
    * `extracted_text` (TEXT, optional)

Out of Scope:

* Not provided (no explicit exclusions beyond the “not huge blobs” preference implied by recommending pointers over large payload storage).

Reproduction Steps:

1. Run the scraper that generates/updates `scraped_urls.db`.
2. Open `scraped_urls.db` expecting stored page payloads.
3. Inspect `scraped_urls` schema and observe only `url`, `scraped_at`, `title` with no payload fields; observe `title` often NULL.

Environment:

* Storage: SQLite database `scraped_urls.db`.
* OS / runtime / scraper implementation: Unknown.

Evidence:

* Observed schema intent: `scraped_urls` tracks `url`, `scraped_at`, `title` only (no transcript/HTML/JSON storage).
* Suggested verification commands:

  * `sqlite3 scraped_urls.db` → `.tables`, `.schema scraped_urls`, `SELECT COUNT(*), MIN(scraped_at), MAX(scraped_at) FROM scraped_urls;`
* Suggested artifact discovery commands:

  * `find data archive . -maxdepth 3 -type f \( -iname '*.html' -o -iname '*.json' -o -iname '*.md' \) ...`
  * `find . -maxdepth 3 -type f -name '*.db' ...`
* Suggested schema changes (if persisting artifact pointers/metadata in SQLite):

  * `ALTER TABLE scraped_urls ADD COLUMN status TEXT;`
  * `ALTER TABLE scraped_urls ADD COLUMN http_status INTEGER;`
  * `ALTER TABLE scraped_urls ADD COLUMN content_type TEXT;`
  * `ALTER TABLE scraped_urls ADD COLUMN artifact_path TEXT;`
  * `ALTER TABLE scraped_urls ADD COLUMN sha256 TEXT;`
  * `ALTER TABLE scraped_urls ADD COLUMN extracted_text TEXT;`

Decisions / Agreements:

* `scraped_urls.db` is a URL index/queue and not the content store (per assistant).
* Recommended approach is to store pointers/metadata in SQLite rather than large payload blobs (per assistant).

Open Items / Unknowns:

* Actual current output location for page payloads (filesystem path(s) not confirmed).
* Which “data types” must be supported and how they should be normalized/persisted.
* Whether the product direction is “filesystem artifacts + DB index” or “DB as primary content store.”

Risks / Dependencies:

* Requires schema migration and scraper writer changes to populate new fields.
* Storing large payload blobs in SQLite risks DB bloat/performance; pointer-based storage mitigates this.

Acceptance Criteria:

* After a scrape, each scraped URL has a discoverable payload location:

  * Either: saved artifact files exist under standardized directories (e.g., `data/` or `archive/`) and can be found via the recommended `find` scan, and/or
  * The DB row includes `artifact_path` (or equivalent) pointing to the saved artifact.
* If schema is expanded, the new columns exist and are populated for new runs (`status`, `http_status`, `content_type`, `artifact_path`, `sha256`; `extracted_text` optional).
* `title` is populated when available or the pipeline explicitly records why it is missing (status/parse outcome).

Priority & Severity (if inferable from text):

* Not provided.

Labels (optional):

* bug, data-storage, sqlite, scraper, schema, artifacts
