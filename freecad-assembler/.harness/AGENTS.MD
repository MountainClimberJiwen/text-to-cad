# freecad-assembler · Project Agent Context

This file is the local grounding context for skill `freecad-assembler-project`.
The skill should read this file before answering project-specific questions or executing project-specific commands.
If `/Users/jiwen/PycharmProjects/freecad-assembler/.harness/work-notes.md` exists, read it too for session-derived progress notes and lessons learned.

## Identity
- project_id: `freecad-assembler`
- skill_name: `freecad-assembler-project`
- repo_path: `/Users/jiwen/PycharmProjects/freecad-assembler`
- aliases: `freecad-assembler, freecad assembler, freecad 装配, 装配项目, freecad 项目, freecad 工程, 装配仓库`
- source: `manual`
- project_table_updated_at: `2026-04-04T14:53:14.794343+00:00`
- last_synced_by_iboss: `2026-05-11T11:16:13+08:00`

## Project Summary
- stored progress field: `0%`
- readme summary: # Open STEP Viewer / This project includes a local web app that reads STEP files from `models/step`, parses them in the browser with `occt-import-js`, and renders them with `three.js`. / ## Run / 1. Install dependencies with `npm install` / 2. Start the app with `npm run start` / 3. Open `http://127.0.0.1:3000`

## Task Queue Snapshot
- pending: 0
- running: 0
- done: 1
- failed: 0
- total: 1
- matched task project_ids: freecad-assembler
- latest task id: 13
- latest task project_id: freecad-assembler
- latest task status: done
- latest run status: done
- latest session id: 019d6074-97c4-7060-98c6-3527f49b73e0
- latest progress text: -
- created_at: 2026-04-06T01:33:11.591264+00:00
- started_at: 2026-04-06T01:42:26.904662+00:00
- finished_at: 2026-04-06T01:44:27.006906+00:00
- run_updated_at: 2026-04-06T01:44:27.010254+00:00

## Workspace Snapshot
- branch: main
- last commit: 7478878 2026-04-02 Tune camera framing to avoid STEP clipping in viewer
- dirty summary:
  - D dist/assets/index-BUWl-psO.css
  -  D dist/assets/index-Cu4InBrB.js
  -  M dist/index.html
  -  D harness/DEVELOPER.MD
  -  D harness/LLM-MODELS.MD
  -  D harness/QA.MD
  -  D harness/UX.MD
  -  D harness/WORKFLOW.MD
  -  D harness/config.toml
  -  M package-lock.json
  -  M package.json
  -  M server.js
  -  M src/App.vue
  -  M src/components/StepViewer.vue
  -  M src/styles.css
  - ?? .DS_Store
  - ?? .harness/
  - ?? URS-MANUAL/
  - ?? checkpoint/
  - ?? data/

## Agent Operating Rules
1. When this project skill is invoked, start by reading this file and then run live checks in `/Users/jiwen/PycharmProjects/freecad-assembler` if the user asks about current status.
2. Use `/Users/jiwen/PycharmProjects/freecad-assembler` as the default working directory for shell commands, code inspection, and edits unless the user explicitly redirects elsewhere.
3. For progress questions, combine this file with live signals: `git status`, recent commits, relevant logs, tests, and task queue data.
4. When the user sends a new idea, design note, or command for this project, execute it in this repo context rather than giving generic advice.
5. After meaningful work, update this file's `Project Summary`, `Task Queue Snapshot`, `Workspace Snapshot`, and `Latest Notes` sections so the project skill stays stateful across sessions.
6. Do not overwrite the `Manual Notes` section unless the user asks or you are clearly appending a new durable fact.
7. To refresh this file without touching other projects, run `python3 /Users/jiwen/PycharmProjects/iboss/scripts/sync_project_agents.py --project freecad-assembler-project`.

## Suggested First Checks
- `pwd`
- `git status --short`
- `git log -1 --oneline`
- inspect repo README and entry scripts
- inspect task queue / dashboard state if the question is about dispatcher progress

## Latest Notes
- Auto-refreshed by `iboss/scripts/sync_project_agents.py` at 2026-05-11T11:16:13+08:00
- 2026-05-08: Attempted a v3 POC for pharmaceutical assembly line 3D generation. Used pure FreeCAD Box primitives with hand-written coordinates. User judged it "差的更远了" (going in the wrong direction). Checkpoint saved at `checkpoint/2026-05-08/`.
- 2026-05-08: Key lesson: hand-written coordinates in FreeCAD API is not the right path. Need constraint-based parametric modeling + formal verification approach instead.
- 2026-04-24: Verified local setup in `/Users/jiwen/PycharmProjects/freecad-assembler` with Node `v22.14.0`, npm `11.2.0`, Codex CLI `0.122.0`, and FreeCADCmd at `/Applications/FreeCAD.app/Contents/Resources/bin/FreeCADCmd`.
- 2026-04-24: `npm run build` passes; app responds on `http://127.0.0.1:3000/`; `/api/health` reports configured chat/codegen models from local `.env`.
- 2026-04-24: Port `3000` was already occupied by an existing project node process (`PID 7464`), so `npm run start` currently collides unless that process is stopped first.
- Initialized by `iboss/scripts/sync_project_agents.py`.
- This file is a seed context; refresh it after real project work.

## Manual Notes
- Current bring-up path: ensure `.env` exists with `PORT=3001`, run `npm install`, `npm run build`, then `npm run start`; keep the unrelated service on `127.0.0.1:3000` running.
- Codex works inside this repo with `codex exec --sandbox workspace-write ...`; current machine has `codex-cli 0.122.0`.
