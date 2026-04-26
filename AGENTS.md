# AGENTS.md

This repository is a harness for script-driven CAD generation with coding agents like Codex and Claude Code.

If you are modifying the viewer app itself, go to `viewer/README.md`.

## Skill Routing

Use the bundled skills for workflow details:

- `skills/cad/SKILL.md` for STEP, STL, DXF, GLB/topology artifacts, snapshots, and `@cad[...]` prompt references.
- `skills/urdf/SKILL.md` for generated URDF files, `gen_urdf()`, robot links, joints, limits, and URDF mesh references.
- `viewer/README.md` for viewer behavior, rendering UI, prompt capture UX, and frontend development. Do not read it just to form final CAD Explorer links; use the Viewer Handoff rules below.

`AGENTS.md` is intentionally harness-focused. Reusable CAD and URDF workflow rules live inside the skills.

## Harness Context

Project CAD files live under `models/`.

The CAD and URDF skill tools are file-targeted. They do not depend on this harness's `models/` directory; `models/` is this repo's project layout.

Project-specific context may live under `models/`. Keep project-local notes compact and do not copy reusable generator contracts, prompt-ref rules, validation policy, image review policy, or full CLI syntax into them; link to the CAD and URDF skill references instead.

## Python Environment

Prefer the repo-local CAD runtime when it exists:

```bash
./.venv/bin/python
```

This environment has the CAD dependencies required by the skill tools, including
`build123d` and `OCP`. If `.venv` is missing or cannot import those modules,
create/install it from the repo root before running CAD tools:

```bash
python3.11 -m venv .venv
./.venv/bin/pip install -r requirements-cad.txt
```

## Source Of Truth

- Generated CAD and URDF outputs are derived artifacts.
- Package-local render, topology, component, and review-image artifacts are derived artifacts.
- Do not hand-edit generated artifacts unless explicitly instructed. Edit the owning source file or imported source file first, then regenerate explicit targets with the relevant skill tool.
- If regenerated output differs from checked-in generated files, the regenerated output is authoritative.

## Prompt Artifacts

The viewer may provide annotated screenshots and `@cad[...]` references. Treat screenshots as supporting context and `@cad[...]` refs as stable handles. If they disagree, trust the ref and source geometry, then use the screenshot to understand intent.

Copied `@cad[...]` paths include the `models/` directory and omit the `.step` or `.stp` suffix. For ref grammar, selector semantics, stale-ref handling, and geometry-fact workflows, read `skills/cad/references/prompt-refs.md` and use `skills/cad/scripts/cadref`.

Do not inspect viewer runtime assets to interpret prompt refs. Resolve refs from source STEP data through the CAD skill.

## Viewer Handoff

After editing or regenerating any viewer-displayable `.step`, `.stp`, `.stl`, `.dxf`, or `.urdf` entry, make CAD Explorer available and include links for the affected entries in the final response.

Ensure the viewer server first:

```bash
npm --prefix viewer run dev:ensure
```

Viewer link rule: `file` is always relative to `dir`, and entry links must include `file=`.

- Default scan root: `http://127.0.0.1:4178/?dir=models&file=<path-under-models-with-extension>`
- Only use another scan root when it is intentional: `http://127.0.0.1:4178/?dir=<repo-relative-scan-dir>&file=<path-relative-to-that-dir-with-extension>`

For CAD prompt refs, keep the entry `file=` and append URL-encoded `refs=` parameters. Python generators are not viewer entries; link their generated outputs. If only viewer app code changed, link the base viewer URL.

## Repo Policies

- Keep project CAD files under `models/`.
- Do not store generated review images under `models/`; use `/tmp/...`.
- Use explicit generation targets. Do not run directory-wide generation.
- Let the split generation tools own viewer-consumed render assets. Do not build or edit separate viewer cache files.
- Generation tools write and overwrite current configured outputs. They do not delete stale outputs when paths change.
- Update project-local documentation only when project focus, entry roles, inventory, dependency notes, durable quirks, or preferred rebuild roots change.
- Do not create per-entry README files.

## Common Harness Commands

Run from the repository root unless you intentionally want paths to resolve from another directory.

```bash
# Regenerate a CAD source
./.venv/bin/python skills/cad/scripts/gen_step_part models/path/to/source.py

# Regenerate an assembly source
./.venv/bin/python skills/cad/scripts/gen_step_assembly models/path/to/assembly.py

# Regenerate a URDF sidecar
./.venv/bin/python skills/urdf/scripts/gen_urdf models/path/to/source.py

# Inspect a CAD prompt ref
./.venv/bin/python skills/cad/scripts/cadref inspect '@cad[models/path/to/entry]' --json

# Render a quick review image
./.venv/bin/python skills/cad/scripts/snapshot models/path/to/source.py \
  --view isometric --out /tmp/cad-renders/review.png
```

## Execution Notes

- Start with the narrowest source-only search that can identify directly affected files.
- Exclude generated artifacts, binary CAD files, caches, and build outputs from default searches unless the task explicitly targets them.
- If the first pass makes scope clear, edit the source first and validate after.
- Do not run generation tools, `cadref`, and `snapshot` in parallel against geometry that is still changing in the same edit loop. Rebuild first, then inspect, then render.
- In cloud or constrained environments, avoid full-repo hydration when affected entries are known. Fetch only the needed inputs, generated outputs, and LFS objects for the entries being edited and explicitly regenerated.
