"""Prompt templates for the ARC-Bench adapter.

All prompts are written for a workspace-relative tool loop where run_command
is available. Wording follows the ARC-Bench grading contract: file-first
generation, strict UI conventions and absolute grading-port safety.
"""

UI_CONTRACT = """UI CONTRACT (violations fail grading; follow strictly):
- Every text input element uses type="text". Never type="date" or type="number".
- Every input field has a visible <label>, and the label text matches the requirement wording verbatim.
- Buttons are plain <button> elements containing only text (no icons, no images).
- Validation happens in your own JavaScript. Render errors as visible in-page text whose wording contains keywords like "required" or "invalid".
- Never use the HTML5 "required" or "pattern" attributes.
- Strict mode on displayed values: any value the requirement says must be shown back on the page must appear in exactly one visible element. Remove duplicates (including titles, headers, breadcrumbs, <title>) so the value is unique.
- Every concrete record, label, seed row or option value given in a requirement appears verbatim in the seed data and in the matching <option>/select lists.
- After a successful action, redirect to the page the requirement mentions; the header then shows the logged-in user's name plus a visible "logout" link.
- Show at most one error message element on a page at a time.
- Reference images (if any are attached) are illustrative layout only; never OCR them for text.
- Highest priority: write files first, analyze later. A turn that only reasons about the problem without creating or editing files is wasted."""

PORT_SAFETY = """PORT SAFETY (the grading runner SIGTERMs any run that holds the grading port):
- NEVER bind or smoke-test on port {web_port}. That port belongs to the grader.
- During your whole session, any server you start must use the smoke port: run it with PORT={smoke_port} (the environment already sets PORT={smoke_port}).
- Stop any server you started before you finish your turn."""

SKELETON_PROMPT = """Create the base web application skeleton in the current workspace (the output directory). Write real files with your tools immediately; do not answer with analysis.

Required layout inside the workspace root:
- frontend/ : a static HTML/CSS/JS app (plain JavaScript; TypeScript is forbidden). Include a package.json with a "build" script that copies the sources into frontend/dist using plain node/coreutils commands (npm dependency count must stay zero). "npm install" and "npm run build" in frontend/ must both exit 0.
- backend/ : a zero-npm-dependency Node.js server using only the built-in modules (http, fs, path, crypto). Include package.json with a "start" script running the server. The server must:
  * read PORT from env (fallback {web_port}) and keep running after binding;
  * persist all state as JSON in backend/data/db.json;
  * hash passwords with node crypto scrypt (never plaintext);
  * serve the frontend from ../frontend/dist (fallback ../frontend when dist is absent) and expose JSON APIs under /api;
  * seed demo data on first start, idempotently, so the app is immediately usable.
- The backend also serves any uploaded static assets itself, so a single graded port can show the whole app.

{ui_contract}

{port_safety}

Finish with a short summary of the files you wrote once both frontend/ and backend/ exist on disk."""

NODE_PROMPT = """The web app skeleton already exists in this workspace. Implement the following requirement node on top of it. Extend frontend sources, the backend API and the seed data as needed, keeping everything that already works.

{description}

Workflow: inspect files briefly, then edit/write files. When done, build the frontend (npm run build in frontend/) and smoke-test the backend with PORT={smoke_port}; remember PORT SAFETY rules. Finish with a one-paragraph summary.

{ui_contract}

{port_safety}"""

NUDGE_PROMPT = """Your previous turn produced no files on disk: the required output directories are still missing. Stop analyzing and write the files now, starting with the skeleton layout (frontend/package.json, frontend/index.html, backend/package.json, backend/server.js). Tool calls only; no prose."""

FINAL_CHECK_PROMPT = """Final verification pass for the generated web app in this workspace.

{node_list}

For each requirement check the delivered pages against its scenarios: labels match the requirement text verbatim, inputs are type="text", validation errors render in-page, seeded records and option values are present, unique-visibility rule holds, success paths redirect with the username and logout link in the header. Fix any gap you find by editing files directly. Then run the frontend build once to confirm it exits 0.

When you are done, answer with exactly one final line: VERDICT: PASS or VERDICT: FAIL (optionally followed by a short reason). {port_safety}"""

REHEARSAL_REPAIR_PROMPT = """The generated app failed its pre-grading startup rehearsal with this error:

```
{error}
```

Fix the root cause by editing files in this workspace. Common causes: missing npm scripts, build script that does not produce frontend/dist, backend crash on startup, port/PORT handling. For your own checks run servers with PORT={smoke_port} only, then run the exact grading commands (npm install, npm run build in frontend/; PORT unset for `npm run start` reading process.env.PORT). Finish with a one-line summary."""

OFFICIAL_TESTS_HEADER = """OFFICIAL ACCEPTANCE TESTS take priority over your own interpretation.
Directory: {tests_dir}
Spec files:
{file_list}

Read the relevant spec files FIRST and treat their assertions and selectors as the ground truth for wording, ids and behavior. Where a spec contradicts a requirement paraphrase, follow the spec."""

DUAL_PORT_CONTRACT = """DUAL-PORT LISTENING CONTRACT: the acceptance specs reference these fixed ports: {ports}. The grader exposes the app on port {web_port} (= its PORT env). Additionally, when the environment variable ARC_EXTRA_PORTS is set and is not "0", your backend must ALSO listen, with the exact same request handler, on every comma-separated port in ARC_EXTRA_PORTS. Never bind extra ports during your own smoke runs (use ARC_EXTRA_PORTS=0 with PORT={smoke_port}).."""


def skeleton_prompt(smoke_port: int, web_port: int) -> str:
    return SKELETON_PROMPT.format(
        web_port=web_port,
        ui_contract=UI_CONTRACT,
        port_safety=PORT_SAFETY.format(web_port=web_port, smoke_port=smoke_port),
    )


def node_prompt(description: str, smoke_port: int, web_port: int) -> str:
    return NODE_PROMPT.format(
        description=description,
        ui_contract=UI_CONTRACT,
        port_safety=PORT_SAFETY.format(web_port=web_port, smoke_port=smoke_port),
    )


def nudge_prompt() -> str:
    return NUDGE_PROMPT


def final_check_prompt(node_list: str, smoke_port: int, web_port: int) -> str:
    return FINAL_CHECK_PROMPT.format(
        node_list=node_list,
        port_safety=PORT_SAFETY.format(web_port=web_port, smoke_port=smoke_port),
    )


def repair_prompt(error: str, smoke_port: int) -> str:
    return REHEARSAL_REPAIR_PROMPT.format(error=error, smoke_port=smoke_port)


def official_tests_prompt(tests_dir, specs, extra_ports, smoke_port: int, web_port: int) -> str:
    parts = [
        OFFICIAL_TESTS_HEADER.format(
            tests_dir=tests_dir,
            file_list="\n".join(f"- {p}" for p in specs),
        )
    ]
    if extra_ports:
        parts.append(
            DUAL_PORT_CONTRACT.format(
                ports=", ".join(str(p) for p in extra_ports),
                web_port=web_port,
                smoke_port=smoke_port,
            )
        )
    return "\n\n".join(parts)
