CoPilot Handover Notes
======================

Date: 2026-02-27T18:09:00Z

Overview
--------
This note documents the LearnPress installation and detection work performed in the MCP server and frontend, what was validated by tests, the debugging and container work done to get tests passing in the production docker-compose environment, and recommended next steps and suggestions.

What was implemented (high-level)
---------------------------------
- Detection: GraphQL introspection (look for LearnPress types like "course"/"learnpress") plus REST discovery against common LearnPress namespaces (learnpress/v1, lp/v1).
- Install flow: best-effort attempts in order — GraphQL mutation (speculative) → REST install endpoint (best-effort) → SSH/wp-cli fallback using scripts/setup-remote-wordpress.py.
- Input hardening: plugin_slug sanitization to ^[a-z0-9_-]+$ to avoid path traversal and unsafe input.
- Backend: added run_subprocess_exec wrapper to centralize subprocess handling for easier testing and deterministic monkeypatching.
- Backend: added error_response helper to return structured errors with machine-readable codes and human-friendly messages (error_info).
- Frontend: Next.js API wrappers added (web/src/app/api/...) and an "Install LearnPress" button wired to the MCP install endpoint; updated to surface error_info and show an error modal with copy-to-clipboard for full JSON details.

What was done during testing and debugging (this session)
--------------------------------------------------------
- Added unit tests: mcp-server/tests/test_learnpress.py covering GraphQL detection, invalid plugin slug, and SSH fallback behavior.
- Observed a failing test (test_install_learnpress_ssh_fallback returning HTTP 500) during container runs due to a missing setup script in the image.
- Added an auxiliary debug test (mcp-server/tests/test_learnpress_debug.py) to capture and print response bodies when running inside the container.
- Fixed Docker image so the scripts are present inside the container: updated docker/mcp-server/Dockerfile to COPY scripts/ into /app/scripts and also to /scripts so module-level relative lookup succeeds.
- Refactored subprocess invocation to use a module-level wrapper (run_subprocess_exec) and updated tests to monkeypatch that helper for deterministic behavior.
- Added structured error responses (error_response) on endpoints and updated frontend wrappers to surface error_info; added an error modal + copy-to-clipboard UX in the connections UI.
- Rebuilt the mcp-server image using docker-compose.production.yml and re-ran the tests inside the articulate-mcp container; verified the relevant LearnPress tests pass in-container (3 passed at last run).

Repro steps (what was run)
-------------------------
1. Rebuild and start the production-like mcp-server service:
   COMPOSE_FILE=docker-compose.production.yml
   docker compose -f $COMPOSE_FILE build --no-cache mcp-server
   docker compose -f $COMPOSE_FILE up -d --no-deps mcp-server

2. Run tests inside the running container and view server logs:
   docker exec -u 0 articulate-mcp sh -lc "pytest -q -s tests/test_learnpress.py || true"
   docker logs articulate-mcp --tail 400

Key files changed in this work
-----------------------------
- mcp-server/src/articulate_mcp/routes/learnpress.py  (new endpoints, install flow, sanitization, run_subprocess_exec wrapper, error_response)
- mcp-server/tests/test_learnpress.py  (unit tests)
- mcp-server/tests/test_learnpress_debug.py  (temporary debug helper to print outputs)
- docker/mcp-server/Dockerfile  (copies scripts/ into the image and /scripts for reliable lookup)
- scripts/setup-remote-wordpress.py  (extended to accept --plugins; used by SSH fallback)
- web/src/app/api/... (Next.js API wrappers) and web/src/app/connections/page.tsx (UI button wiring, error modal + copy UX)

Remaining/planned work (kept from previous plan)
------------------------------------------------
1. Add more unit tests for REST/GraphQL failure modes, and tests asserting the plugin_slug sanitization rules.
2. Implement a mu-plugin push fallback (upload a mu-plugin that bootstraps plugin install) as an alternate for environments without WP-CLI.
3. E2E validation: run the complete install flow against a dev WP instance with WP-CLI present; document prerequisites.
4. UI improvements: surface streamed install logs, show install status, and provide actionable error messages to users.

My additional suggestions (prioritized)
--------------------------------------
1. Strengthen test isolation: keep subprocess invocation behind the run_subprocess_exec wrapper and always monkeypatch that helper in tests; add tests that assert temporary key file handling and cleanup.
2. Add structured logging and attach correlation IDs to install attempts so frontend and backend logs can be correlated when debugging remote installs.
3. Use a CI job that builds the mcp-server image and runs the pytest suite inside that image (mirrors local dev steps). This prevents the "works locally but fails in container" situations.
4. For local development and E2E: prefer running WP-CLI inside the WordPress container (docker exec) for installs during CI/dev rather than SSHing into the host; this is faster, more reproducible, and avoids uploading keys in tests.
5. Secrets & audit: ensure SSH private keys or passwords are transient and removed after use; consider encrypting long-lived credentials and include audit records for remote installs (who triggered, when, outcome).
6. UX: implement streamed logs (SSE or websockets) for installs so users can see progress instead of a silent success/failure.

Actionable next steps (recommended immediate tasks)
-------------------------------------------------
- Ensure all tests patch run_subprocess_exec and add assertions for key-file lifecycle.
- Add structured error codes to the install/check endpoints and update frontend handlers to display error_info.message and expose copyable details in the modal.
- Implement the mu-plugin fallback and add unit tests for that path (simulate a WP without WP-CLI).
- Create an E2E job (or documented playbook) that runs the full install flow against a disposable WP instance with WP-CLI available; record the steps required and expected outputs.

Hand-off notes for Claude
------------------------
- The detection and install order is implemented; GraphQL install is speculative and may rarely work; REST install is best-effort; SSH/wp-cli fallback is the reliable path and is covered by unit tests.
- Recent fixes: made the setup script available in the container image, refactored subprocess invocation to a testable wrapper, and added structured error responses and UI modal to surface actionable messages.
- Next hand-off suggestions: implement mu-plugin fallback, add streamed install logs, and create CI that runs tests inside the built image.

If you want, next actions I can take now:
- Run through the test matrix and add missing REST/GraphQL failure-mode tests, then run tests in-container and push changes.
- Implement the mu-plugin fallback and add unit tests for that path.

