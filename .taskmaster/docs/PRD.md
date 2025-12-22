1. Overview

## Problem

A chatbot/web app exposes per-message expandable “thought blocks” (e.g., UI labels like “Thought for 29s”) whose contents only render after a click. Manual export is slow and inconsistent across many projects and chat threads. The goal is to automate: enumerate all projects → enumerate all threads per project → expand every thought block in each thread → extract text → save deterministically under `data/`.

## Target users

* QA / researchers: need complete, repeatable exports of visible thought blocks across many threads.
* Engineers: need a deterministic local export pipeline to feed downstream analysis jobs.

## Why current solutions fail

* Static scraping misses content because the thought text is not in the DOM until expanded via interaction.
* Sidebar-only enumeration is incomplete when threads are hidden behind project navigation or collapsed history; project-first enumeration is required.

## Success metrics

* Coverage: ≥ 99% of discoverable threads within scanned projects are visited once per run (deduped).
* Extraction: For threads with thought toggles, ≥ 95% of toggles produce a non-empty saved file.
* Determinism: Output paths stable (`data/<thread_id>/thought_<n>.txt` or JSONL equivalent) across reruns.
* Resilience: Script completes a full run with < 1% thread-level fatal failures (errors logged, run continues).

## Key assumptions

* An authenticated interactive session exists in a Chromium-based browser; automation attaches via CDP rather than automating login. ([Playwright][1])
* Routes or link patterns exist to identify projects and threads (e.g., `/project/` for projects and `/c/` for threads) and can be configured per deployment.

---

2. Capability Tree (Functional Decomposition)

### Capability: Session Attachment

#### Feature: CDP attach to existing browser (MVP)

* **Description**: Attach automation to a running authenticated Chromium session.
* **Inputs**: CDP endpoint URL (host, port), tab selection policy.
* **Outputs**: Playwright `browser`, `context`, `page` handles.
* **Behavior**: Connect via Playwright `connect_over_cdp`, select an active context/page, validate reachability. ([Playwright][1])

#### Feature: Session validation (MVP)

* **Description**: Verify the session is authenticated and on a supported domain.
* **Inputs**: `page`, expected base URL/domain, auth indicator selector(s).
* **Outputs**: Pass/fail + diagnostics.
* **Behavior**: Check current URL/domain; probe selectors that only appear when logged in; fail fast with actionable logs.

---

### Capability: Project Enumeration

#### Feature: Discover projects from navigation (MVP)

* **Description**: Gather project entry URLs from the UI.
* **Inputs**: `page`, project-link selector(s), base URL resolver.
* **Outputs**: List of canonical project URLs.
* **Behavior**: Locate project links, normalize relative URLs, dedupe, store in memory.

#### Feature: Project list completeness controls (Non-MVP)

* **Description**: Expand/scroll virtualized project lists to surface all projects.
* **Inputs**: `page`, “expand” selector(s), scroll strategy config.
* **Outputs**: Expanded set of project URLs + coverage stats.
* **Behavior**: Click “See all”/expand affordances; scroll containers until no new links appear; stop on stable count.

---

### Capability: Thread Enumeration

#### Feature: Discover threads from project home view (MVP)

* **Description**: From each project route, collect all thread URLs rendered in the main content area.
* **Inputs**: `page`, thread-link selector(s), URL normalizer.
* **Outputs**: Set of canonical thread URLs.
* **Behavior**: Navigate to project URL; wait for UI hydration; locate thread links within main content; dedupe globally.

#### Feature: Thread list pagination/virtualization handling (Non-MVP)

* **Description**: Ensure all threads load when lists are paginated or virtualized.
* **Inputs**: `page`, scroll container selector, pagination control selectors, max depth limits.
* **Outputs**: Thread URL set + completeness signal.
* **Behavior**: Scroll/next-page until stable; record last-seen cursor; stop on repetition or limits.

---

### Capability: Thought Block Extraction

#### Feature: Identify thought toggles by text pattern (MVP)

* **Description**: Find all expandable thought toggles in a thread.
* **Inputs**: `page`, toggle selector strategy (text/regex), optional per-message scope selector.
* **Outputs**: Ordered list of toggle locators.
* **Behavior**: Use Playwright text/locator matching to find elements containing the “Thought for …s” pattern; maintain stable ordering. ([Playwright][2])

#### Feature: Expand toggle and wait for content render (MVP)

* **Description**: Click each toggle and wait until the corresponding content becomes visible.
* **Inputs**: Toggle locator, content locator strategy, wait strategy (auto-wait + explicit).
* **Outputs**: Expanded state + extracted text block.
* **Behavior**: Scroll into view; click (optionally force); wait for content visibility or count change; handle animations/timeouts. ([Playwright][3])

#### Feature: Map toggles to content blocks deterministically (MVP)

* **Description**: Associate each toggle with the correct rendered content.
* **Inputs**: Toggle index, list of matching content nodes, fallback policy.
* **Outputs**: One text payload per toggle index.
* **Behavior**: Primary mapping by index order; fallback to “last visible/newly added” content on mismatch; log mapping anomalies.

#### Feature: Robust selector adaptation (Non-MVP)

* **Description**: Minimize breakage from DOM/class drift.
* **Inputs**: Selector profiles, heuristic matchers (role/aria/text), optional “selector recorder”.
* **Outputs**: Best-effort matches + selector health report.
* **Behavior**: Try selector profiles in priority order; downgrade to text/role-based locators; emit selector failure diagnostics.

---

### Capability: Persistence and Export

#### Feature: Write per-thread files (MVP)

* **Description**: Persist extracted thought blocks under a deterministic directory structure.
* **Inputs**: Output root, thread ID, thought index, extracted text, metadata.
* **Outputs**: Files written (TXT and/or JSON), manifest entries.
* **Behavior**: Create `data/<thread_id>/thought_<index>.txt` in UTF-8; optionally write `thread.jsonl` with metadata.

#### Feature: Run manifest + resume (Non-MVP)

* **Description**: Support resuming and avoiding rework across runs.
* **Inputs**: Manifest path, URL set, per-thread status.
* **Outputs**: Updated manifest, skip decisions.
* **Behavior**: Record visited threads, extracted counts, errors; skip completed threads on rerun unless forced.

---

### Capability: Operator UI

#### Feature: Desktop GUI runner (MVP)

* **Description**: Provide a simple UI to start/stop scraping and view live logs.
* **Inputs**: CDP URL, output folder, selector profile selection, run options.
* **Outputs**: Run state, progress indicators, log stream.
* **Behavior**: Run scraper in background thread/process; marshal log updates to UI thread via scheduled callbacks (Tkinter is not thread-safe). ([Python Assets][4])

#### Feature: CLI runner (MVP)

* **Description**: Headless operator interface for automation and CI-like runs (still attaching to a live browser).
* **Inputs**: Flags/config file.
* **Outputs**: Exit codes, logs, artifacts.
* **Behavior**: Execute orchestrator with structured logging; return nonzero only for systemic failures.

---

### Capability: Observability and Safety

#### Feature: Structured logging + error taxonomy (MVP)

* **Description**: Make failures diagnosable without stopping the run.
* **Inputs**: Events from discovery/extraction/persistence.
* **Outputs**: Log records, summary report.
* **Behavior**: Thread-level try/catch boundaries; classify as selector failure, navigation failure, timeout, persistence error; continue.

#### Feature: Rate limiting and polite waits (Non-MVP)

* **Description**: Reduce UI flakiness and detection risk.
* **Inputs**: Delay policy, backoff settings.
* **Outputs**: Stabilized interaction cadence.
* **Behavior**: Add jittered waits between navigations/clicks; exponential backoff on transient errors.

---

3. Repository Structure + Module Definitions (Structural Decomposition)

(Structure aligns to the “WHAT→HOW” mapping approach.  )

## Repository structure

```
thought-scraper/
├── src/
│   ├── foundation/
│   │   ├── errors.py
│   │   ├── logging.py
│   │   ├── config.py
│   │   └── types.py
│   ├── browser/
│   │   ├── cdp_attach.py
│   │   └── page_waits.py
│   ├── selectors/
│   │   ├── profiles.py
│   │   └── matchers.py
│   ├── discovery/
│   │   ├── projects.py
│   │   └── threads.py
│   ├── extraction/
│   │   ├── toggles.py
│   │   ├── content.py
│   │   └── mapping.py
│   ├── export/
│   │   ├── filesystem.py
│   │   └── manifest.py
│   ├── orchestration/
│   │   ├── runner.py
│   │   └── resume.py
│   ├── ui/
│   │   ├── gui_tk.py
│   │   └── cli.py
│   └── __init__.py
├── tests/
│   ├── unit/
│   ├── integration/
│   └── e2e/
├── docs/
│   ├── selectors.md
│   ├── operations.md
│   └── troubleshooting.md
└── pyproject.toml
```

## Module definitions

### Module: `foundation/errors.py`

* **Responsibility**: Define error classes and error codes used across the system.
* **Exports**: `ScraperError`, `NavigationError`, `SelectorError`, `ExtractionError`, `PersistenceError`, `ErrorCode`.

### Module: `foundation/logging.py`

* **Responsibility**: Structured logging and event sinks (console/file/UI callback).
* **Exports**: `get_logger()`, `log_event(event)`, `RunSummary`.

### Module: `foundation/config.py`

* **Responsibility**: Load/validate config (CDP URL, base URL, selectors, output paths).
* **Exports**: `load_config(path|env)`, `ScraperConfig`.

### Module: `foundation/types.py`

* **Responsibility**: Shared dataclasses/types (URL models, selector profile, extracted block).
* **Exports**: `ProjectURL`, `ThreadURL`, `SelectorProfile`, `ThoughtBlock`, `ThreadResult`.

---

### Module: `browser/cdp_attach.py`

* **Maps to capability**: Session Attachment
* **Responsibility**: Attach Playwright to a live Chromium session via CDP.
* **Exports**: `attach(cdp_url) -> (browser, context, page)`. ([Playwright][1])

### Module: `browser/page_waits.py`

* **Responsibility**: Centralize UI hydration/wait policies.
* **Exports**: `wait_for_hydration(page)`, `wait_for_network_idle(page)`, `wait_for_content_change(locator)`.

---

### Module: `selectors/profiles.py`

* **Responsibility**: Store selector sets per app/version (projects, threads, toggles, content).
* **Exports**: `load_profiles()`, `get_profile(name)`.

### Module: `selectors/matchers.py`

* **Responsibility**: Provide locator builders (text/regex/role-based) for robust matching.
* **Exports**: `project_links(page, profile)`, `thread_links(page, profile)`, `thought_toggles(page, profile)`. ([Playwright][2])

---

### Module: `discovery/projects.py`

* **Maps to capability**: Project Enumeration
* **Responsibility**: Enumerate project URLs from UI.
* **Exports**: `discover_projects(page, profile) -> list[ProjectURL]`.

### Module: `discovery/threads.py`

* **Maps to capability**: Thread Enumeration
* **Responsibility**: Enumerate thread URLs per project page and normalize/dedupe.
* **Exports**: `discover_threads(page, project_url, profile) -> set[ThreadURL]`.

---

### Module: `extraction/toggles.py`

* **Maps to capability**: Thought Block Extraction
* **Responsibility**: Find and interact with thought toggles.
* **Exports**: `list_toggles(page, profile)`, `expand_toggle(toggle, policy)`.

### Module: `extraction/content.py`

* **Responsibility**: Locate content containers and extract text safely.
* **Exports**: `list_contents(page, profile)`, `extract_text(content_locator)`.

### Module: `extraction/mapping.py`

* **Responsibility**: Deterministically map toggles to content blocks with fallbacks.
* **Exports**: `map_toggle_to_content(idx, contents, fallback_policy)`.

---

### Module: `export/filesystem.py`

* **Maps to capability**: Persistence and Export
* **Responsibility**: Write thread artifacts to disk with deterministic layout.
* **Exports**: `write_thought_block(out_root, thread_id, idx, text, meta) -> path`.

### Module: `export/manifest.py`

* **Responsibility**: Persist run manifests for resume/skip logic.
* **Exports**: `load_manifest(path)`, `record_thread_result(manifest, result)`, `save_manifest(...)`.

---

### Module: `orchestration/runner.py`

* **Responsibility**: End-to-end orchestration across projects → threads → toggles → persistence.
* **Exports**: `run(config) -> RunSummary`.

### Module: `orchestration/resume.py`

* **Responsibility**: Dedup/resume policies across runs.
* **Exports**: `should_skip(thread_url, manifest, policy)`.

---

### Module: `ui/gui_tk.py`

* **Maps to capability**: Operator UI
* **Responsibility**: Tkinter UI wrapper around `orchestration.runner`.
* **Exports**: `launch_gui()`. ([Python Assets][4])

### Module: `ui/cli.py`

* **Responsibility**: CLI entrypoint for config-driven runs.
* **Exports**: `main(argv)`.

---

4. Dependency Chain (layers, explicit “Depends on: […]”)

### Foundation Layer

* **foundation/errors.py**: No dependencies
* **foundation/types.py**: No dependencies
* **foundation/config.py**: Depends on: [foundation/types.py, foundation/errors.py]
* **foundation/logging.py**: Depends on: [foundation/types.py]

### Browser Layer

* **browser/cdp_attach.py**: Depends on: [foundation/config.py, foundation/errors.py, foundation/logging.py] ([Playwright][1])
* **browser/page_waits.py**: Depends on: [foundation/logging.py, foundation/errors.py]

### Selector Layer

* **selectors/profiles.py**: Depends on: [foundation/config.py, foundation/types.py]
* **selectors/matchers.py**: Depends on: [selectors/profiles.py, foundation/types.py] ([Playwright][2])

### Discovery Layer

* **discovery/projects.py**: Depends on: [selectors/matchers.py, browser/page_waits.py, foundation/logging.py]
* **discovery/threads.py**: Depends on: [selectors/matchers.py, browser/page_waits.py, foundation/logging.py]

### Extraction Layer

* **extraction/toggles.py**: Depends on: [selectors/matchers.py, browser/page_waits.py, foundation/errors.py, foundation/logging.py]
* **extraction/content.py**: Depends on: [selectors/matchers.py, foundation/logging.py]
* **extraction/mapping.py**: Depends on: [foundation/types.py, foundation/logging.py]

### Export Layer

* **export/filesystem.py**: Depends on: [foundation/config.py, foundation/errors.py, foundation/logging.py]
* **export/manifest.py**: Depends on: [foundation/types.py, export/filesystem.py, foundation/logging.py]

### Orchestration Layer

* **orchestration/resume.py**: Depends on: [export/manifest.py, foundation/logging.py]
* **orchestration/runner.py**: Depends on: [browser/cdp_attach.py, discovery/projects.py, discovery/threads.py, extraction/toggles.py, extraction/content.py, extraction/mapping.py, export/filesystem.py, orchestration/resume.py, foundation/logging.py]

### UI Layer

* **ui/cli.py**: Depends on: [orchestration/runner.py, foundation/config.py, foundation/logging.py]
* **ui/gui_tk.py**: Depends on: [orchestration/runner.py, foundation/config.py, foundation/logging.py] ([Python Assets][4])

Acyclic by construction: every higher layer depends only on lower layers.

---

5. Development Phases (Phase 0…N; entry/exit criteria; tasks with dependencies + acceptance criteria + test strategy)

### Phase 0: Foundation primitives

**Entry Criteria**: Repo created; Python packaging baseline.
**Tasks**:

* [ ] Implement `foundation/errors.py` (depends on: none)

  * Acceptance criteria: Error classes exist; serialized error codes usable in logs.
  * Test strategy: Unit tests asserting type hierarchy and code mapping.
* [ ] Implement `foundation/types.py` (depends on: none)

  * Acceptance criteria: Dataclasses validate and serialize deterministically.
  * Test strategy: Unit tests for parsing/normalizing thread IDs.
* [ ] Implement `foundation/config.py` (depends on: [foundation/types.py, foundation/errors.py])

  * Acceptance criteria: Loads config from file/env; validates required fields; defaults applied.
  * Test strategy: Unit tests with valid/invalid configs.
* [ ] Implement `foundation/logging.py` (depends on: [foundation/types.py])

  * Acceptance criteria: Structured logs emitted; UI sink callback supported.
  * Test strategy: Unit tests capturing log events.

**Exit Criteria**: All foundation modules import cleanly; unit tests pass.
**Delivers**: Stable config/log/error/type contracts.

---

### Phase 1: CDP attach + minimal CLI skeleton (usable path)

**Entry Criteria**: Phase 0 complete.
**Tasks**:

* [ ] Implement `browser/cdp_attach.py` (depends on: [foundation/config.py, foundation/errors.py, foundation/logging.py])

  * Acceptance criteria: Attaches to CDP; selects a page; fails with clear diagnostics on mismatch. ([Playwright][1])
  * Test strategy: Integration test with a locally launched Chromium in CDP mode (skippable in CI).
* [ ] Implement `ui/cli.py` (depends on: [foundation/config.py, foundation/logging.py])

  * Acceptance criteria: `--config` runs and prints run summary; returns nonzero only on systemic errors.
  * Test strategy: Unit tests for argument parsing and config wiring.

**Exit Criteria**: CLI can attach to an interactive session and report basic status.
**Delivers**: First end-to-end executable entrypoint.

---

### Phase 2: Project-first discovery

**Entry Criteria**: Phase 1 complete.
**Tasks**:

* [ ] Implement `selectors/profiles.py` + `selectors/matchers.py` (depends on: [foundation/config.py, foundation/types.py])

  * Acceptance criteria: Selector profile resolves to concrete locators; supports text/regex where needed. ([Playwright][2])
  * Test strategy: Unit tests with HTML fixtures; locator builders validated in Playwright against fixture pages.
* [ ] Implement `discovery/projects.py` (depends on: [selectors/matchers.py, browser/page_waits.py, foundation/logging.py])

  * Acceptance criteria: Returns deduped project URLs; normalizes relative URLs.
  * Test strategy: Integration tests with a mocked page/fixture route.
* [ ] Implement `discovery/threads.py` (depends on: [selectors/matchers.py, browser/page_waits.py, foundation/logging.py])

  * Acceptance criteria: From each project page, returns deduped thread URLs across projects.
  * Test strategy: Integration tests with fixture project pages including virtualized/partial lists.

**Exit Criteria**: Given a selector profile, the system can enumerate (projects, threads) reproducibly.
**Delivers**: Coverage across projects rather than sidebar-only enumeration.

---

### Phase 3: Thought extraction + deterministic export

**Entry Criteria**: Phase 2 complete.
**Tasks**:

* [ ] Implement `extraction/toggles.py` + `extraction/content.py` (depends on: [selectors/matchers.py, browser/page_waits.py, foundation/logging.py])

  * Acceptance criteria: Finds all toggles; expands each; extracts visible content text. ([Playwright][3])
  * Test strategy: Integration tests on controlled fixture app that reveals content after click.
* [ ] Implement `extraction/mapping.py` (depends on: [foundation/types.py, foundation/logging.py])

  * Acceptance criteria: Index-based mapping works; fallback used and logged on mismatch.
  * Test strategy: Unit tests over synthetic content sequences.
* [ ] Implement `export/filesystem.py` (depends on: [foundation/config.py, foundation/logging.py])

  * Acceptance criteria: Writes deterministic file paths; UTF-8; safe folder creation.
  * Test strategy: Unit tests using temp dirs; verify exact paths and contents.

**Exit Criteria**: For a single thread URL, extracted thought blocks are saved to disk deterministically.
**Delivers**: Core value path (extract → files).

---

### Phase 4: Orchestrated full run + resume

**Entry Criteria**: Phase 3 complete.
**Tasks**:

* [ ] Implement `export/manifest.py` (depends on: [export/filesystem.py, foundation/logging.py])

  * Acceptance criteria: Records per-thread results; reload supports skip logic.
  * Test strategy: Unit tests for manifest read/write and idempotency.
* [ ] Implement `orchestration/resume.py` + `orchestration/runner.py` (depends on: discovery + extraction + export + manifest)

  * Acceptance criteria: Runs projects→threads→extraction; continues on thread-level failures; outputs run summary.
  * Test strategy: Integration tests with a small fixture corpus; fault injection (timeouts/selector failures) confirms continuation.

**Exit Criteria**: Full run over multiple projects completes with summary and artifacts.
**Delivers**: Repeatable end-to-end scraper.

---

### Phase 5: Desktop GUI runner

**Entry Criteria**: Phase 4 complete.
**Tasks**:

* [ ] Implement `ui/gui_tk.py` (depends on: [orchestration/runner.py, foundation/logging.py, foundation/config.py])

  * Acceptance criteria: Start/Stop; live logs; output folder selection; UI remains responsive (no UI thread blocking). ([Python Assets][4])
  * Test strategy: Manual smoke tests + automated “headless” unit tests for state transitions (logic separated from UI widgets).

**Exit Criteria**: Operators can run and monitor scraping without the terminal.
**Delivers**: Usable UI wrapper.

---

6. User Experience

## Personas

* **Operator (QA/research)**: Wants “Start → watch progress → open output folder”, minimal configuration.
* **Power user (engineer)**: Wants CLI + config files, selector profiles, resume manifests, structured logs.

## Key flows

1. **GUI run**

   * Enter/confirm CDP URL and output folder.
   * Select selector profile.
   * Start.
   * View logs: projects found, threads found, per-thread thought counts, saved paths, errors.
   * Stop (graceful: finish current action, then exit loop).
2. **CLI run**

   * Provide config path.
   * Run.
   * Receive summary + manifest + artifacts.

## UI/UX notes

* Show counts: projects discovered, threads discovered, threads completed, thoughts extracted, errors.
* Always display the active thread ID being processed.
* Provide a single consolidated “Run Summary” section at completion.

---

7. Technical Architecture

## System components

* **Local operator app** (Python):

  * Playwright automation attaching to existing Chromium via CDP. ([Playwright][1])
  * Discovery (projects/threads) and extraction (toggles/content).
  * Export layer writing files and manifest.
  * Optional Tkinter GUI wrapper; UI updates via event queue/callback to main loop. ([Python Assets][4])

## Data models

* `ProjectURL`: canonical string + source metadata.
* `ThreadURL`: canonical string + derived `thread_id`.
* `ThoughtBlock`: `{ thread_id, index, text, toggle_label, extracted_at, selectors_used }`
* `ThreadResult`: `{ thread_id, url, thought_count, files_written, errors[] }`
* `RunManifest`: `{ run_id, started_at, config_hash, threads: { url: status } }`

## APIs and integrations

* Playwright Locator API (auto-wait, robust element targeting). ([Playwright][3])
* Chromium CDP endpoint; relies on launching Chrome with `--remote-debugging-port`. ([Chrome for Developers][5])

## Decisions, trade-offs, alternatives

* **Decision: CDP attach instead of scripted login**

  * Rationale: Avoids CAPTCHA/SSO complexity; reuses authenticated session. ([Playwright][1])
  * Trade-off: Requires operator to launch/maintain the browser session and CDP port.
* **Decision: Project-first enumeration**

  * Rationale: Higher completeness than sidebar-only enumeration in UIs where threads surface under project routes.
  * Trade-off: Requires extra navigation and wait time; more exposure to pagination/virtualization.
* **Decision: Tkinter GUI**

  * Rationale: Zero external UI runtime; fits local operator tool.
  * Trade-off: Threading constraints; must marshal updates to main thread. ([Python Assets][4])

---

8. Test Strategy

## Test pyramid targets

* Unit: ~70%
* Integration (Playwright against fixture pages/local minimal app): ~25%
* E2E (real CDP session): ~5% (manual or gated)

## Coverage minimums

* Line: 85%
* Branch: 75%
* Function: 85%

## Critical scenarios per module

* `browser/cdp_attach.py`

  * Happy: attaches and selects a usable page.
  * Error: unreachable CDP; no contexts; wrong browser type.
* `discovery/projects.py` / `discovery/threads.py`

  * Happy: extracts all links; normalizes relative URLs.
  * Edge: duplicates, missing hrefs, virtualized lists partially visible.
* `extraction/toggles.py` / `extraction/content.py`

  * Happy: multiple toggles; content appears after click.
  * Error: click intercepted; content never appears (timeout); selector drift.
* `export/filesystem.py`

  * Happy: writes expected paths.
  * Error: permission denied; invalid thread id characters sanitized.
* `orchestration/runner.py`

  * Happy: continues across many threads.
  * Error: one thread fails; run continues and summary reflects failures.

## Integration points

* Selector profiles + matcher logic with Playwright locators. ([Playwright][3])
* UI-thread marshaling for GUI logging. ([Python Assets][4])

---

9. Risks and Mitigations

## DOM/selector drift

* **Impact**: High
* **Likelihood**: High
* **Mitigation**: Selector profiles + heuristics (text/role-based) + selector health reporting; fast failure per feature with fallback profiles.
* **Fallback**: Manual update of selector profile, rerun with resume manifest.

## Virtualized/paginated thread lists

* **Impact**: High (coverage loss)
* **Likelihood**: Medium
* **Mitigation**: Scroll/pagination strategies; stable-count termination criteria; completeness telemetry.
* **Fallback**: Provide a “depth-limited scan” mode plus manual seed thread URLs.

## UI flakiness (timing, overlays, animations)

* **Impact**: Medium
* **Likelihood**: High
* **Mitigation**: Centralized wait policies, retry-once for click/timeout, jittered delays.
* **Fallback**: Lower concurrency (single-thread), longer timeouts, operator re-run for failed threads.

## Session expiration / auth changes

* **Impact**: Medium
* **Likelihood**: Medium
* **Mitigation**: Session validation checkpoints; fail fast before a long run.
* **Fallback**: Operator re-authenticates; resume via manifest.

## Data sensitivity and access scope

* **Impact**: High
* **Likelihood**: Medium
* **Mitigation**: Local-only storage; explicit output directory; avoid scraping beyond authenticated scope; redact config secrets from logs.
* **Fallback**: Disable persistence of raw text; store only hashes/metadata.

---

10. Appendix

## Prior context incorporated

* Project-first scraping strategy; selectors and output layout; optional GUI runner.
* RPG methodology template used to enforce explicit dependencies and topo-ordered phases.

## External technical references

* Playwright `connect_over_cdp` attaches to an existing Chromium instance via CDP. ([Playwright][1])
* Playwright locators support robust matching and auto-wait behaviors; text matching can use regex. ([Playwright][2])
* Tkinter UI updates must occur on the main thread; use scheduled callbacks (`after`) to safely update from worker threads. ([Python Assets][4])
* Chrome remote debugging uses `--remote-debugging-port`; CDP protocol details can be inspected from the local endpoint. ([Chrome for Developers][5])

## Open questions (tracked, not blocking MVP)

* Exact base URL and route patterns for projects/threads in the target app (defaults must be configurable).
* Whether thread lists require deep infinite scrolling, server-side pagination, or filtering.
* Whether thought content shares markup with non-thought markdown blocks requiring stronger disambiguation.

[1]: https://playwright.dev/python/docs/api/class-browsertype?utm_source=chatgpt.com "BrowserType | Playwright Python"
[2]: https://playwright.dev/python/docs/locators?utm_source=chatgpt.com "Locators | Playwright Python"
[3]: https://playwright.dev/python/docs/api/class-locator?utm_source=chatgpt.com "Locator | Playwright Python"
[4]: https://pythonassets.com/posts/background-tasks-with-tk-tkinter/?utm_source=chatgpt.com "Background Tasks With Tk (tkinter) - Python Assets"
[5]: https://developer.chrome.com/docs/devtools/remote-debugging/local-server?utm_source=chatgpt.com "Access local servers and Chrome instances with port forwarding"
