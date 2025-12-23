Spec 1: Activity Drawer (Thinking / Tooling Timeline)
=====================================================

Type
----

* Component+Feature

Goal / user outcome
-------------------

* Provide a dedicated, scrollable right-side panel that shows the model’s in-progress and completed “Thinking” timeline, including tool invocations and their outputs, with a visible elapsed duration and completion markers.

Evidence summary
----------------

* Observed:

  * Right-side panel titled “Activity · <duration>” (examples: “5m 23s”, “3m 20s”, “8s”) with a close “X” in the header.

  * Section header “Thinking”.

  * A collapsible/indented group labeled “Reading documents” with nested entries beneath it.

  * Timeline entries mixing: short step titles, paragraph explanations, and command/output blocks (monospace) labeled with “bash -lc …”.

  * Some entries appear highlighted with a blue selection background.

  * End-of-run status lines like “Thought for 15s” and “Done”, and a “Sources · <count>” line (example: 35).

  * Internal scrolling within the panel (panel-level scrollbar visible).

* Stated:

  * None.

* Inferred:

  * Duration in the header updates as the activity runs, then stops once done.

  * “Reading documents” functions as an expandable grouping for related sub-steps (collapsed/expanded state).

  * Highlight state corresponds to hover/focus/selection of a specific entry.

Scope
-----

* In scope:

  * Right-side drawer container with header, scrollable body, and optional footer/status area.

  * Display of “Thinking” section and nested groups/entries.

  * Rendering of tool command blocks and captured stdout/stderr output blocks.

  * Visual states: running vs done, selected/highlighted entry, collapsed/expanded groups.

* Out of scope:

  * The main chat message composer and message feed outside the drawer.

  * Browser DevTools overlays shown in the screenshots (not part of the product UI).

Placement / layout
------------------

* Surface: app-wide side drawer (overlaying or occupying the right side of the main layout).

* Anchor: right.

* Relationship to content: overlay or docked side panel (content remains visible to the left).

* Sizing:

  * Default: narrow fixed width (observed ~305–329px overlays).

  * Responsive: Unknown.

* Stacking: Above main chat content; below browser chrome (z-index specifics Unknown).

Structural parts (regions)
--------------------------

* Root container:

  * Purpose: Contain the activity timeline for the current assistant run.

  * Notes: Independent scroll region from the main page.

* Primary panel/area:

  * Purpose: Display sections and entries for the run.

  * Notes: Vertical list with nested grouping.

* Header region (optional):

  * Purpose: Show “Activity” title, elapsed duration, and close control.

* Body region (scroll/overflow rules):

  * Purpose: Scrollable list of timeline content (sections, groups, entries, blocks).

  * Notes: Entries can include titles, paragraphs, and code/output blocks.

* Footer region (optional):

  * Purpose: Show completion markers (e.g., “Thought for 15s”, “Done”) and source count.

* Supporting regions (optional):

  * Actions/controls: group expand/collapse affordances; close button.

Primary elements and controls
-----------------------------

* Control 1: Close (X)

  * Type: icon button

  * Label/content: “X” icon

  * Triggered action: closes the Activity drawer

  * States: enabled; hover/focus; disabled Unknown

* Control 2: Group toggle (e.g., “Reading documents”)

  * Type: disclosure row (clickable header)

  * Label/content: group name; small leading icon observed

  * Triggered action: expands/collapses nested entries for the group

  * States: expanded/collapsed; hover/focus; selected Unknown

Item model (if list/grid/menu)
------------------------------

* Item types:

  * Section header (e.g., “Thinking”)

  * Group header (e.g., “Reading documents”)

  * Entry title row (short sentence describing a step)

  * Entry body paragraph(s)

  * Tool invocation block (command) + tool output block

  * Run status line(s) (e.g., “Thought for 15s”, “Done”, “Sources · 35”)

* Item fields:

  * Required: id, type, timestamp or sequence order, primary text

  * Optional: group id, icon, selection state, tool name, command string, output text, status (running/done), source count

* Hierarchy:

  * Nested (Section → Group → Entries/Blocks). Nesting depth observed: at least 2.

States
------

* Default:

  * Drawer open, shows current run timeline.

* Hover:

  * Entry row hover styling Unknown (not directly evidenced).

* Focus:

  * Keyboard focus styling Unknown.

* Active/selected:

  * Selected entry shows blue highlight background.

* Disabled:

  * Unknown.

* Loading:

  * During run, entries appear progressively (inferred).

* Empty:

  * Unknown.

* Error:

  * Tool output can include error-like content (general), but explicit error state styling Unknown.

* Expanded/collapsed (if applicable):

  * “Reading documents” group shows nested items when expanded; collapsed behavior Unknown but inferred.

* Mobile/desktop variants (if applicable):

  * Desktop shown; mobile Unknown.

Interactions / behavior
-----------------------

* Open/close rules:

  * Close via header X; open trigger Unknown.

* Navigation/activation rules:

  * Clicking an entry may set highlight/selection (inferred from highlight state).

* Expand/collapse rules:

  * Clicking group header toggles visibility of nested items (inferred).

* Scroll behavior:

  * Panel body scrolls independently; content remains readable while main page stays static behind.

* Overflow handling:

  * Long commands/outputs wrap or scroll within blocks (exact behavior Unknown; truncated command strings are visible).

* Animation/transition:

  * Duration/easing: Unknown.

  * What animates: drawer open/close and group expand/collapse (inferred).

* Persistence:

  * Whether open state or expanded groups persist across navigation/sessions: Unknown.

Responsiveness
--------------

* Desktop behavior:

  * Fixed-width right drawer with internal scroll.

* Tablet behavior:

  * Unknown.

* Mobile behavior:

  * Unknown.

* Touch targets and gesture rules (if applicable):

  * Unknown.

Accessibility
-------------

* Landmarks/roles:

  * Drawer should be exposed as a dialog/complementary panel with an accessible name (inferred best practice).

* Keyboard support:

  * Tab order: close button then interactive group headers then interactive entries (inferred).

  * Arrow key behavior (if applicable): Unknown.

  * Escape behavior (if applicable): likely closes drawer (inferred; not evidenced).

* Focus management:

  * On open, focus moves into drawer; on close, returns to invoker (inferred).

* Screen reader labeling:

  * Header should announce “Activity” and elapsed duration; group headers announced as expandable (inferred).

* Color/contrast and non-color indicators:

  * Selection uses blue background; ensure additional indication for non-color users (inferred requirement).

* Reduced motion expectations:

  * Drawer/group transitions respect reduced motion (inferred requirement).

Content rules
-------------

* Copy rules (labels, headings, tooltips):

  * Header format: “Activity · <elapsed>”.

  * Section header: “Thinking”.

  * Groups and entries use sentence-case step descriptions.

* Truncation/wrapping:

  * Long command lines may truncate (observed: “bash -lc …” clipped).

  * Outputs remain multi-line and readable in block form.

* Localization considerations:

  * Duration format and pluralization (s/m) localized (inferred).

* Theming/dark mode considerations:

  * Dark theme shown; light theme Unknown.

Data and permissions (if applicable)
------------------------------------

* Data sources:

  * Run timeline events (thinking steps), tool invocation metadata (tool name/command), tool outputs, run duration, source count.

* Loading strategy (user-visible, not technical):

  * Entries append/refresh as work proceeds; final status shows done.

* Permissions/visibility rules:

  * Whether all tool details are shown to all users: Unknown.

* Audit/logging needs (user-visible outcomes only):

  * Provide a readable trace of what actions were taken and what outputs were produced.

Analytics and telemetry (if applicable)
---------------------------------------

* Trackable events:

  * activity\_drawer\_open — trigger: open — properties: run\_id, model, timestamp

  * activity\_drawer\_close — trigger: close X/Escape — properties: run\_id, elapsed

  * activity\_group\_toggle — trigger: group header click — properties: group\_id, new\_state

  * activity\_entry\_select — trigger: click/keyboard select — properties: entry\_id, type

* Impressions vs clicks:

  * Impression: drawer shown; Click: group toggle, close, entry select.

* Error tracking signals (user-facing):

  * Tool output block contains an error marker/state (Unknown styling).

Test hooks
----------

* Stable selectors:

  * data-test-id: activity-drawer

  * data-test-id: activity-header, activity-close

  * data-test-id: activity-section-thinking

  * data-test-id: activity-group-<id>

  * data-test-id: activity-entry-<id>

  * data-test-id: activity-tool-block-<id>

  * data-test-id: activity-footer-status, activity-sources

* Critical user flows to validate:

  * Open drawer → view “Thinking” → expand “Reading documents” → scroll through tool blocks → close drawer.

  * During run: observe duration updates and new entries append; after run: “Done” and “Sources” visible.

Acceptance criteria
-------------------

* Functional:

  * Header displays “Activity · <elapsed>” and a working close button.

  * “Thinking” section renders and supports grouped nested entries.

  * Tool blocks show tool label (“bash -lc …”) and multi-line output.

  * Selected entry displays a distinct highlight state.

  * Completion state shows “Done” and “Sources · <count>” when available.

* Visual/layout:

  * Drawer remains fixed on the right with independent scrolling.

  * Text blocks and tool output blocks maintain readable spacing and alignment.

* Accessibility:

  * Close button has an accessible name.

  * Group headers expose expanded/collapsed state to assistive tech.

  * Keyboard users can reach and operate close and group toggles.

* Responsive:

  * Desktop layout matches fixed right drawer; other breakpoints Unknown.

* Performance (user-visible):

  * Drawer opens without noticeable jank; threshold Unknown.

Edge cases
----------

* Very long tool outputs (thousands of lines) causing heavy scroll.

* Long command strings requiring wrapping/truncation.

* Many grouped entries creating deep scroll.

* Mixed content types (paragraph + multiple tool blocks) within one entry.

* Run interrupted or partially complete timeline.

Unknowns and defaults applied
-----------------------------

* Unknowns:

  * How the drawer is opened (button, keyboard shortcut, automatic).

  * Whether entries are individually collapsible beyond group level.

  * Exact hover/focus styling and keyboard navigation behavior.

  * Mobile/tablet presentation and gestures.

  * Copy/share controls for commands/outputs (not visible).

  * Error-state styling for failed tools.

* Defaults applied:

  * Treat “Reading documents” as a disclosure group with toggle behavior.

  * Treat the drawer as a keyboard-accessible region with Escape-to-close behavior.

  * Treat selection highlight as click/keyboard selection of an entry.

* * *

Spec 2: Tool Invocation + Output Block (within Activity Timeline)
=================================================================

Type
----

* Component

Goal / user outcome
-------------------

* Display a single executed tool/command with its invocation label and the resulting textual output in a compact, scannable, monospace block inside the activity timeline.

Evidence summary
----------------

* Observed:

  * Blocks labeled with “bash -lc …” followed by a multi-line output region.

  * Output includes directory listings, grep results, and file excerpts (multi-line, preserved line breaks).

  * Command label can be visually truncated when long.

* Stated:

  * None.

* Inferred:

  * Block represents a single tool execution event with captured stdout/stderr.

Scope
-----

* In scope:

  * Command label row and output container.

  * Multi-line rendering with preserved whitespace/line breaks.

* Out of scope:

  * Executing commands; this is display-only.

Placement / layout
------------------

* Surface: inside Activity drawer body, nested under an entry.

* Anchor: inline within the vertical timeline flow.

* Relationship to content: inline block, separated from surrounding paragraphs by spacing.

* Sizing:

  * Default: full available drawer width.

  * Responsive: Unknown.

* Stacking: same layer as other entries.

Structural parts (regions)
--------------------------

* Root container:

  * Purpose: Wrap command label and output.

  * Notes: Visually distinct from plain text entries (block styling).

* Header/label region:

  * Purpose: Show tool type and invocation string (e.g., “bash -lc …”).

* Body/output region (scroll/overflow rules):

  * Purpose: Render multi-line output.

  * Notes: Handles long output; internal scrolling vs wrapping Unknown.

Primary elements and controls
-----------------------------

* Control 1: None observed (display-only).

  * Type: N/A

  * Label/content: N/A

  * Triggered action: N/A

  * States: N/A

Item model (if list/grid/menu)
------------------------------

* Item types:

  * command\_label

  * output\_text

* Item fields:

  * Required: tool\_name/type, command\_string, output\_text

  * Optional: exit\_status, duration, error\_flag, truncated\_flag

States
------

* Default:

  * Command label + output visible.

* Hover:

  * Unknown.

* Focus:

  * Unknown.

* Active/selected:

  * Block may appear within a selected entry (highlighting handled by parent).

* Disabled:

  * Unknown.

* Loading:

  * Output streaming-in vs final Unknown.

* Empty:

  * Output empty state Unknown.

* Error:

  * Error output rendering style Unknown.

* Expanded/collapsed (if applicable):

  * Unknown.

Interactions / behavior
-----------------------

* Open/close rules:

  * Always visible when its parent entry is visible.

* Navigation/activation rules:

  * None observed.

* Scroll behavior:

  * Output may require scrolling when long (exact mechanism Unknown).

* Overflow handling:

  * Long command label truncates (observed).

* Animation/transition:

  * Unknown.

* Persistence:

  * Remains visible as part of the saved run trace (inferred).

Responsiveness
--------------

* Desktop behavior:

  * Fits drawer width; maintains monospace readability.

* Tablet behavior:

  * Unknown.

* Mobile behavior:

  * Unknown.

* Touch targets and gesture rules (if applicable):

  * Not applicable (no controls observed).

Accessibility
-------------

* Landmarks/roles:

  * Expose as a grouped region within the timeline (inferred).

* Keyboard support:

  * If selectable/copyable, ensure focusable regions (Unknown).

* Focus management:

  * Not applicable unless interactive.

* Screen reader labeling:

  * Announce tool type and that following text is output (inferred).

* Color/contrast and non-color indicators:

  * Ensure block contrast meets minimums in dark mode (inferred).

* Reduced motion expectations:

  * Not applicable.

Content rules
-------------

* Copy rules (labels, headings, tooltips):

  * Label begins with tool type “bash -lc”.

* Truncation/wrapping:

  * Command label truncates; output preserves line breaks.

* Localization considerations:

  * Not applicable; command/output are raw.

* Theming/dark mode considerations:

  * Dark theme styling implied; light theme Unknown.

Data and permissions (if applicable)
------------------------------------

* Data sources:

  * Tool invocation string and captured output.

* Loading strategy (user-visible, not technical):

  * Output appears as soon as available.

* Permissions/visibility rules:

  * Whether sensitive outputs are redacted: Unknown.

* Audit/logging needs (user-visible outcomes only):

  * Output must match what was produced, preserving ordering.

Analytics and telemetry (if applicable)
---------------------------------------

* Trackable events:

  * tool\_block\_render — trigger: block appears — properties: tool\_type, has\_output, output\_length

* Impressions vs clicks:

  * Impression only (no clicks observed).

* Error tracking signals (user-facing):

  * Output flagged as error (Unknown).

Test hooks
----------

* Stable selectors:

  * data-test-id: activity-tool-block

  * data-test-id: activity-tool-command

  * data-test-id: activity-tool-output

* Critical user flows to validate:

  * Render long command label → truncates without breaking layout.

  * Render long multi-line output → remains readable and scrollable/wrappable per design.

Acceptance criteria
-------------------

* Functional:

  * Displays tool label and output text for each tool event.

  * Preserves output line breaks and ordering.

* Visual/layout:

  * Block is visually distinct from paragraph entries.

  * Command label truncation does not overlap other UI.

* Accessibility:

  * Screen readers can distinguish label vs output text.

* Responsive:

  * Block fits available drawer width without horizontal overflow causing unreadable layout (exact rules Unknown).

* Performance (user-visible):

  * Large outputs do not freeze scrolling (threshold Unknown).

Edge cases
----------

* Empty output.

* Extremely large output.

* Output containing long unbroken strings.

* Mixed stdout/stderr.

* Sensitive data needing redaction (policy Unknown).

Unknowns and defaults applied
-----------------------------

* Unknowns:

  * Copy-to-clipboard control presence.

  * Whether output region has internal scroll vs wraps.

  * Error styling conventions and exit-status display.

* Defaults applied:

  * Treat the block as non-interactive, display-only, with truncation for the command label and preserved formatting for output.

---
