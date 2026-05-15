# text-to-cad · Project Agent Context

This file is the local grounding context for skill `text-to-cad-project`.
The skill should read this file before answering project-specific questions or executing project-specific commands.
If `/Users/jiwen/PycharmProjects/text-to-cad/.harness/work-notes.md` exists, read it too for session-derived progress notes and lessons learned.

## Identity
- project_id: `text-to-cad`
- skill_name: `text-to-cad-project`
- repo_path: `/Users/jiwen/PycharmProjects/text-to-cad`
- aliases: `text-to-cad,text-to-cad`
- source: `manual`
- project_table_updated_at: `2026-05-11T15:20:35.530805+00:00`
- last_synced_by_iboss: `2026-05-15T16:22:34+08:00`

## Project Summary
- stored progress field: `0%`
- readme summary: <div align="center"> / <img src="assets/text-to-cad-demo.gif" alt="Demo of the text-to-cad harness generating and previewing CAD geometry" width="100%"> / <br> / # ⚙ Open Source Text to CAD Harness ⚙ / An open source harness for generating 3D models with your favorite coding agent / [![GitHub stars](https://img.shields.io/github/stars/earthtojake/text-to-cad?style=for-the-badge&logo=github&label=Stars)](https://github.com/earthtojake/text-to-cad/stargazers)

## Task Queue Snapshot
- pending: 0
- running: 0
- done: 0
- failed: 0
- total: 0
- matched task project_ids: (none)
- latest task: none recorded in task_queue.db

## Workspace Snapshot
- branch: main
- last commit: 52a8a67 2026-04-28 feat: add industrial-cad skill with automation device library and assembly examples
- dirty summary:
  - M skills/industrial_cad/README.md
  -  M skills/industrial_cad/SKILL.md
  -  M skills/industrial_cad/references/automation-device-lib.md
  - ?? .harness/
  - ?? cli-anything-freecad/
  - ?? freecad-assembler/
  - ?? models/.bracket.step/
  - ?? models/assemblies/.auto_feed_assembly.step/
  - ?? models/assemblies/.automation_control_unit.step/
  - ?? models/assemblies/.vibratory_feeder_assembly.step/
  - ?? models/assemblies/auto_feed_assembly.step
  - ?? models/assemblies/automation_control_unit.step
  - ?? models/assemblies/vibratory_feeder_assembly.allowed_overlaps.json
  - ?? models/assemblies/vibratory_feeder_assembly.constraints.json
  - ?? models/assemblies/vibratory_feeder_assembly.joints.json
  - ?? models/assemblies/vibratory_feeder_assembly.py
  - ?? models/assemblies/vibratory_feeder_assembly.step
  - ?? models/assemblies/vibratory_feeder_assembly_freecad.20260514-001317.FCBak
  - ?? models/assemblies/vibratory_feeder_assembly_freecad.FCStd
  - ?? models/assemblies/vibratory_feeder_assembly_freecad.placements.json

## Agent Operating Rules
1. When this project skill is invoked, start by reading this file and then run live checks in `/Users/jiwen/PycharmProjects/text-to-cad` if the user asks about current status.
2. Use `/Users/jiwen/PycharmProjects/text-to-cad` as the default working directory for shell commands, code inspection, and edits unless the user explicitly redirects elsewhere.
3. For progress questions, combine this file with live signals: `git status`, recent commits, relevant logs, tests, and task queue data.
4. When the user sends a new idea, design note, or command for this project, execute it in this repo context rather than giving generic advice.
5. After meaningful work, update this file's `Project Summary`, `Task Queue Snapshot`, `Workspace Snapshot`, and `Latest Notes` sections so the project skill stays stateful across sessions.
6. Do not overwrite the `Manual Notes` section unless the user asks or you are clearly appending a new durable fact.
7. To refresh this file without touching other projects, run `python3 /Users/jiwen/PycharmProjects/iboss/scripts/sync_project_agents.py --project text-to-cad-project`.

## Suggested First Checks
- `pwd`
- `git status --short`
- `git log -1 --oneline`
- inspect repo README and entry scripts
- inspect task queue / dashboard state if the question is about dispatcher progress

## Latest Notes
- Auto-refreshed by `iboss/scripts/sync_project_agents.py` at 2026-05-15T16:22:34+08:00
- 2026-05-07 16:05 CST: mapped how `autoresearch` / `autoreason` can apply to this repo. Best fit is a hybrid loop: use objective gates on source-targeted CAD generation (`gen_step_part`, `gen_step_assembly`, `gen_urdf`, `cadref inspect`, model-local assertions like `bounding_box()` / `len(solids())`, and bundled CLI tests) before running subjective A/B/AB judging on shape quality, prompt/spec fidelity, and design tradeoffs.
- This file is a seed context; refresh it after real project work.

## Manual Notes
- Add durable project-specific context here: current milestone, blocked issues, important commands, env quirks, deployment URLs, test commands.
