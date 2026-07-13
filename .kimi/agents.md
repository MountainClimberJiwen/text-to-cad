# Kimi Agent Configuration for text-to-cad-assembly

This directory defines custom agents for the text-to-cad-assembly project.

## Usage

```bash
# Load the project agent (includes cad-asm subagent)
kimi --agent-file .kimi/project-agent.yaml

# Or load just the cad-asm subagent directly
kimi --agent-file cad_asm/agent.yaml
```

## Subagents

### `cad-asm` — CAD Assembly Specialist

- **Path**: `cad_asm/agent.yaml`
- **Purpose**: Executes CAD assembly tasks using the `cad-asm` Python toolchain
- **Capabilities**:
  - Parses natural-language or structured assembly requirements
  - Generates `task.json` with parts, constraints, and outputs
  - Runs the full assembly pipeline: `init → step → export → check`
  - Handles per-step review/approval loops
  - Searches and reuses standard parts from the built-in library
  - Produces STEP / STL / URDF exports and three-view check images
  - Provides viewer links for generated artifacts

**How the parent agent invokes it:**

```
Agent(
    description="Build gripper assembly",
    prompt="""
Build a pneumatic gripper assembly with:
- A base plate (100x60x5 mm) with M4 mounting holes on 20mm grid
- A pneumatic cylinder (bore=20, stroke=40) mounted on top, centered
- Two gripper jaws (width=30, height=20, depth=10) on either side of the cylinder rod

Place all parts in models/assemblies/gripper_asm/.
Run full pipeline: init → all steps → export STEP → check.
""",
    subagent_type="coder",
)
```

The cad-asm subagent will:
1. Search the library for matching parts
2. Write `task.json`
3. Run `cad-asm init`
4. Loop `cad-asm step` (handling review automatically since review_each_step defaults to true — the subagent reads pending.json and writes decisions)
5. Run `cad-asm export` and `cad-asm check`
6. Return viewer links and file paths

**Workspace convention**: cad-asm subagent creates workspaces under `models/` or wherever the parent specifies. Each workspace is self-contained with `task.json`, `state.json`, `parts/`, `review/`, `decisions/`, `output/`, `log/`.
