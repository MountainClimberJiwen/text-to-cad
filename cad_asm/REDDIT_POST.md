# I built a declarative CAD assembly tool that turns LLM agents into mechanical engineers — thoughts?

Hey r/cad 👋 (cross-posting to r/Python too)

I've been hacking on a problem that keeps coming up in my workflow: **how do you get an AI to do real CAD assembly work**, not just generate individual parts?

Most text-to-CAD demos stop at "here's a single STEP file." But real engineering is about **constraints, mating, and assemblies**. So I built `cad-asm` — a Python toolchain that treats CAD assembly as a state machine an LLM agent can execute step-by-step.

## What it does

You describe an assembly in a JSON "task file" (parts + constraints), and `cad-asm`:

1. **Initializes** a workspace
2. **Steps** through placing each part, solving geometric constraints
3. **Checks** for interference between parts
4. **Reviews** each placement (optional human-in-the-loop gate)
5. **Exports** STEP / STL / URDF + three-view orthographic renders

## A concrete example

Here's a pneumatic gripper assembly:

```json
{
  "task_id": "gripper-001",
  "parts": [
    {
      "id": "base",
      "source": {"type": "library", "path": "base_plate"},
      "shape": {"type": "library", "params": {
        "ref": "base_plate",
        "width": 100, "depth": 60, "thickness": 5,
        "mounting_hole_diameter": 4, "hole_spacing": 20
      }}
    },
    {
      "id": "cylinder",
      "shape": {"type": "library", "params": {
        "ref": "pneumatic_cylinder", "bore": 20, "stroke": 40
      }}
    },
    {
      "id": "jaw-left",
      "shape": {"type": "library", "params": {
        "ref": "gripper_jaw", "width": 30, "height": 20, "depth": 10
      }}
    }
  ],
  "constraints": [
    {"type": "place_at", "part1": "world", "part2": "base",
     "params": {"position": {"x": 0, "y": 0, "z": 0}}},
    {"type": "align_face", "part1": "base", "part2": "cylinder",
     "params": {"face1": "top", "face2": "bottom"}},
    {"type": "coaxial", "part1": "base", "part2": "cylinder",
     "params": {"axis1": "outer_cylinder", "axis2": "outer_cylinder"}}
  ]
}
```

Run it:

```bash
cad-asm init --task gripper.json --workspace ./ws
cad-asm step --workspace ./ws   # repeat until done
cad-asm check --workspace ./ws  # front/top/right PNGs
cad-asm export --workspace ./ws
```

## The constraint solver

Built on [build123d](https://github.com/gumyr/build123d) (OCP-backed). Supports:

- **`place_at`** — absolute placement at origin
- **`align_face`** — coplanar face mating (e.g., "bolt head sits on bracket top")
- **`coaxial`** — cylindrical axis alignment (e.g., "shaft goes through bearing")
- **`distance`** — fixed gap between faces

Face selectors: `top`, `bottom`, `front`, `back`, `left`, `right`, `outer_cylinder`, `inner_cylinder`. The solver automatically computes the `Location` transform to satisfy the constraint.

## Standard parts library

40+ pre-built parts searchable by natural language (works in English and Chinese):

- Pneumatic: cylinders, valves, air pumps, tubes
- Electrical: PLC modules, servo motors, sensors, DIN rails
- Mechanical: grippers, linear guides, rollers, vibratory bowls
- Structural: base plates, brackets, frame bases
- Fasteners: M6/M8 bolts, nuts, washers

```bash
cad-asm lib-search "pneumatic cylinder"
cad-asm lib-search "光电传感器"   # works too
```

## Where it gets interesting: Agent architecture

I recently refactored this into a **subagent** for [Kimi Code CLI](https://moonshotai.github.io/kimi-cli/) (think Claude Code / Cursor but open). Now there are two roles:

- **Planner subagent** — analyzes your natural-language request, picks standard parts from the catalog, designs the constraint strategy, and outputs a draft `task.json`
- **Coder subagent** — executes the plan: writes files, runs the pipeline, handles review loops, exports results

This mirrors how a human engineer works: **think first, then build**.

The parent agent can call the planner like:

```
Agent(description="Plan gripper assembly",
      prompt="Build a pneumatic gripper with ...",
      subagent_type="plan")
```

Then hand the plan to the executor.

## Why this approach?

| Traditional CAD | cad-asm |
|---|---|
| GUI-driven, mouse-heavy | Declarative, text-driven |
| Hard to version control | `task.json` diffs like code |
| AI can't "see" the screen | AI reads/writes structured text |
| One-shot part generation | Step-by-step assembly with verification |

It's not replacing SolidWorks/Fusion — it's for **scripted/parametric assembly generation** and **AI-driven workflows**.

## Current limitations (honest)

- Constraint solver is MVP-level: only handles the first applicable constraint per part, no over-constrained systems yet
- URDF export is basic (box approximations)
- No kinematic simulation
- Face selectors are heuristic (normal-vector based), not true B-rep topology IDs

## What I'm looking for

I'd love feedback from this community:

1. **Would you use a declarative assembly DSL?** What syntax would you prefer — JSON, YAML, Python API, or something else?
2. **Constraint modeling** — am I missing critical constraint types? I'm thinking about adding `parallel`, `perpendicular`, `tangent`, `gear_mate` next.
3. **AI integration** — for those experimenting with LLM + CAD, what's your biggest pain point? Mine was "the AI generates one part and stops" — hence the assembly focus.
4. **build123d vs CadQuery vs OpenSCAD** — I chose build123d for its OCP foundation and Pythonic API. Would a different kernel make more sense?

The repo is still early (harness-level code, not a polished product), but the core ideas are working end-to-end. Happy to share more details if anyone's interested.

---

**Tech stack**: Python 3.11+, build123d, OCP, Pydantic
**License**: MIT (when I clean it up for release)

*Edit: Added cross-post note, fixed typo in constraint example.*
