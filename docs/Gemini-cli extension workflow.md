## You asked:

src.md

File

output a workflow for user for the following: gemini-cli extension `https://github.com/shrwnsan/clix-dev-flow` INPUT="users source code"

---

## ChatGPT Replied:

Thought for 1m 0s

Dev Flow (clix-dev-flow) user workflow (INPUT = local source code)
------------------------------------------------------------------

### 1) Install the extension (outside Gemini CLI)

    gemini extensions install https://github.com/shrwnsan/clix-dev-flow.git
    

Restart Gemini CLI after installation. [GitHub](https://github.com/shrwnsan/clix-dev-flow)

Compatibility target: Gemini CLI v0.8.2+ (per repo README). [GitHub](https://github.com/shrwnsan/clix-dev-flow)

### 2) Enter the codebase you want to work on

    cd /path/to/your-project
    

### 3) Start Gemini CLI in the project root

    gemini
    

### 4) Ensure the extension is enabled (outside Gemini CLI)

    gemini extensions enable dev-flow
    

If needed, confirm extensions inside Gemini CLI with `/extensions list`. [GitHub+1](https://github.com/shrwnsan/clix-dev-flow)

* * *

Core loop: Plan → Tasks → Execute (source-code-aware)
-----------------------------------------------------

### 5) Create a PRD (Gemini CLI slash command)

Run this in Gemini CLI (it will write a PRD under `tasks/`):

    /dev:create-prd "Implement <feature> in this repo. Constrain design to existing patterns in <folders/files>. Include acceptance criteria and edge cases."
    

Command and workflow pattern are defined by the extension. [GitHub](https://github.com/shrwnsan/clix-dev-flow)

Expected output location/naming pattern:

*   `tasks/0001-prd-<feature-name>.md` (example pattern shown in repo) [GitHub](https://github.com/shrwnsan/clix-dev-flow)
    

### 6) Generate implementation tasks from the PRD (Gemini CLI)

    /dev:generate-tasks "tasks/0001-prd-<feature-name>.md"
    

This creates a task list file in `tasks/` (pattern shown in repo). [GitHub](https://github.com/shrwnsan/clix-dev-flow)

### 7) Execute the task list step-by-step against the codebase (Gemini CLI)

    /dev:process-task-list "tasks/tasks-0001-prd-<feature-name>.md"
    

This drives implementation iteratively using the repo as working context. [GitHub](https://github.com/shrwnsan/clix-dev-flow)

* * *

Operational controls (during the loop)
--------------------------------------

### Progress visibility (Gemini CLI)

    /dev:list-prds
    /dev:list-tasks
    

Utilities are part of the extension. [GitHub](https://github.com/shrwnsan/clix-dev-flow)

### Close-out / housekeeping (Gemini CLI)

    /dev:cleanup
    

The extension’s default structure includes an archive area for completed work. [GitHub](https://github.com/shrwnsan/clix-dev-flow)

* * *

Resulting workspace layout (in your repo)
-----------------------------------------

    your-project/
    ├── tasks/
    │   ├── 0001-prd-<feature-name>.md
    │   ├── tasks-0001-prd-<feature-name>.md
    │   └── completed/
    └── .gemini/extensions/dev-flow/
    

The repo documents this structure and that `tasks/` is created automatically by commands (or can be created manually). [GitHub](https://github.com/shrwnsan/clix-dev-flow)

---

