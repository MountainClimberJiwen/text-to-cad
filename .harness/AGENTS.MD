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
- last_synced_by_iboss: `2026-05-20T16:23:02+08:00`

## Project Summary
- stored progress field: `0%`
- readme summary: <div align="center"> / <img src="assets/text-to-cad-demo.gif" alt="Demo of the text-to-cad harness generating and previewing CAD geometry" width="100%"> / <br> / # ⚙ Open Source Text to CAD Harness ⚙ / An open source harness for generating 3D models with your favorite coding agent / [![GitHub stars](https://img.shields.io/github/stars/earthtojake/text-to-cad?style=for-the-badge&logo=github&label=Stars)](https://github.com/earthtojake/text-to-cad/stargazers)

## Task Queue Snapshot
- pending: 0
- running: 0
- done: 0
- failed: 1
- total: 1
- matched task project_ids: text-to-cad
- latest task id: 87
- latest task project_id: text-to-cad
- latest task status: failed
- latest run status: failed
- latest session id: new-session
- latest progress text: ## Project Progress Summary — In-context RL × Industrial CAD Assembly
### 1) Latest Progress Highlights
**RL Module Fully Scaffolded (`skills/industrial_cad/rl/`)**
| Component | What Exists | Test Result |
|-----------|-------------|-------------|
| `env.py` — `CADEnv` | Gymnasium env with **continuous 24D action space** (placement deltas), OCP geometry verification, fast/slow two-stage checking | ✅ Zero-action baseline passes clean; random policy crashes into heavy interference |
| `optimize.py` | Scipy **Differential Evolution** + Nelder-Mead refinement as non-RL baseline | ⚠️ 1,605 evals in 163s, 0% all-passed from σ=15mm perturbation; best reward improved from -119 → -75 |
| `agent/skill_env.py` — `RepairSkillEnv` | **Discrete 12-action** repair primitives (MOVE_X/Y/Z, ROT_Z, INC/DEC_DIST, REORDER, DONE) + fast bbox-only proxy mode | ✅ Runs at ~10 steps/sec (vs ~0.3 for full OCP); action masking works |
| `agent/train_skill.py` | PPO training on discrete repair skills | ⚠️ 2,048 steps/208s; needs ~5k+ steps to converge (pass rate 0% at 2k) |
| `agent/auto_repair.py` | Unified CLI: `train` / `repair` / `evolve` | ✅ Functional entry point |
| `agent/evolve.py` | Continual learning loop with `ExperienceBuffer` + `CurriculumGenerator` (progressive perturbation σ: 5→30mm) | ✅ Code complete; not yet run end-to-end |
| `train.py` | Original PPO training on continuous placement space | ✅ Functional; suffers from dimensionality + OCP speed bottleneck |
**Key Architecture Decisions Already Made**
- **Reward design is hard-constraint based** (interference -10, gap -5, clearance -1, all-passed +100) — exactly matching the task payload's philosophy.
- **Two-stage verification** (fast constraint-gap check + periodic full OCP BRep check) cuts per-step time from ~1.7s → ~0.4s.
- **Allowed overlaps** configuration handles design-intent overlaps (bolts in holes, sliders in rails).
**Latest Git Activity**
- Most recent commit (`52a8a67`): added `industrial_cad` skill with automation device library, assembly examples, and the full RL module.
---
### 2) Current Status
| Area | Status | Notes |
|------|--------|-------|
| **Model-free RL for placement optimization** | ✅ Done | Both continuous (PPO) and discrete repair-primitive (PPO) environments run. |
| **Black-box optimization baseline** | ✅ Done | DE/Nelder-Mead works but converges poorly from large perturbations. |
| **Curriculum + experience buffer** | ✅ Code-complete | `CurriculumGenerator` and `ExperienceBuffer` implemented; awaiting longer training runs. |
| **Case-based / In-context retrieval** | ❌ Not started | The payload's core idea — a small retriever model selecting historical success/failure cases to prepend to LLM prompt — is **not yet implemented**. Current RL trains on raw parameters, not on prompt-context selection. |
| **LLM → CAD → verify → reward loop** | ⚠️ Partial | LLM generates assembly.py + constraints.json; RL optimizes placements after. No closed loop where LLM receives reward feedback and regenerates. |
| **Surrogate model for fast reward** | ⚠️ Partial | `RepairSkillEnv` has `fast_mode` (bbox-only proxy), but it's rule-based, not a learned neural surrogate. |
| **Constraint knowledge base** | ❌ Not started | TODO.md lists `.knowledge/` patterns.json + fixes.json as P1 priority. |
| **PyBullet / URDF motion validation** | ❌ Blocked | `PyBullet` not installed; joints.json exists but not wired to sim. |
**Blockers**
1. **Training compute**: Skill agent needs ~5k–10k steps to converge; each step is ~0.1s in fast mode but evaluations still need full OCP periodically.
2. **No LLM-in-the-loop**: The current pipeline is LLM generates → RL optimizes. The payload's "In-context RL" vision requires RL to control *what goes into the LLM prompt*, which is a different (and smaller) learning problem but needs new code.
---
### 3) Next Suggested Actions
**Immediate (MVP Step 1 from payload)**
1. **Build a minimal case library** — Manually curate 10–20 trajectories (success + failure) from `CADEnv` / `RepairSkillEnv` runs and save them as `skills/industrial_cad/rl/cases/case_library.json`. This unblocks all downstream in-context work.
2. **Run a longer `train_skill.py` session** — 10k–20k steps with curriculum to get a baseline converged model and measure true pass rate.
**Short-term (MVP Steps 2–3)**
3. **Implement a `ContextRetriever`** — A tiny scoring network (<1M params) or even a UCB Bandit that selects `top_k` cases from the library based on current state similarity (part types, error patterns). This is the "RL trains the retriever, not the LLM" step.
4. **Wire LLM prompt builder** — `build_cad_prompt(current_state, case_library, retriever_policy)` that injects selected cases into a structured prompt and calls the LLM for a JSON action plan. Validate that LLM output improves when relevant cases are present.
**Medium-term (MVP Step 4)**
5. **Close the simulation loop** — LLM generates action JSON → apply to `CADEnv` → OCP verify → compute reward → update retriever policy → iterate. This is the true In-context RL闭环 described in the payload.
6. **Replace bbox proxy with a learned surrogate** — Train a small MLP to predict interference/gap counts from placement vectors, cutting verification to <10ms and enabling massive rollouts.
**Optional but high-value**
7. **Populate `.knowledge/` constraint patterns** — Start with vibratory_feeder_assembly success patterns so the case library is semantically queryable (e.g., "cylinder+bracket → PlaneCoincident+AxialAlignment").
- created_at: 2026-05-15T13:44:32.094867+00:00
- started_at: 2026-05-15T13:45:28.946785+00:00
- finished_at: 2026-05-15T13:55:30.478959+00:00
- run_updated_at: 2026-05-15T13:55:30.483517+00:00

## Workspace Snapshot
- branch: main
- last commit: b5b84cd 2026-05-15 feat: discrete-action Repair Skill Agent + continual evolution
- dirty summary:
  - M .harness/AGENTS.MD
  - ?? .harness/.env
  - ?? freecad-assembler/
  - ?? models/.auto_station_from_image.step/
  - ?? models/.bracket.step/
  - ?? models/assemblies/.auto_feed_assembly.step/
  - ?? models/assemblies/.auto_station_assembly.step/
  - ?? models/assemblies/.auto_station_from_vision.step/
  - ?? models/assemblies/.automation_control_unit.step/
  - ?? models/assemblies/.test_auto_assembly.step/
  - ?? models/assemblies/.vibratory_feeder_assembly.step/
  - ?? models/assemblies/auto_station_assembly.py
  - ?? models/assemblies/auto_station_assembly.step
  - ?? models/assemblies/auto_station_from_vision.py
  - ?? models/assemblies/auto_station_from_vision.step
  - ?? models/assemblies/test_auto_assembly.py
  - ?? models/assemblies/test_auto_assembly.step
  - ?? models/assemblies/vibratory_feeder_assembly_freecad.20260514-001317.FCBak
  - ?? models/assemblies/vibratory_feeder_assembly_freecad.FCStd
  - ?? models/assemblies/vibratory_feeder_from_constraints.20260511-233411.FCBak

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
- Auto-refreshed by `iboss/scripts/sync_project_agents.py` at 2026-05-20T16:23:02+08:00
- 2026-05-07 16:05 CST: mapped how `autoresearch` / `autoreason` can apply to this repo. Best fit is a hybrid loop: use objective gates on source-targeted CAD generation (`gen_step_part`, `gen_step_assembly`, `gen_urdf`, `cadref inspect`, model-local assertions like `bounding_box()` / `len(solids())`, and bundled CLI tests) before running subjective A/B/AB judging on shape quality, prompt/spec fidelity, and design tradeoffs.
- This file is a seed context; refresh it after real project work.

## Manual Notes
- Add durable project-specific context here: current milestone, blocked issues, important commands, env quirks, deployment URLs, test commands.
