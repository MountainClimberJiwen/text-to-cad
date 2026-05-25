# Orthographic Three-View Check

`scripts/ortho_check` is a standalone inspection module that validates generated CAD results by rendering standard orthographic views and running geometry sanity checks.

## Purpose

After `gen_step_part` or `gen_step_assembly` produces a STEP file and its GLB sidecar, run `ortho_check` to:

1. Render **front**, **top**, and **right** orthographic snapshots.
2. Verify the mesh is non-empty (vertex / triangle counts).
3. Verify topology is sane (bbox dimensions, face/edge/shape counts).
4. Emit a structured JSON report for CI or manual review.

## Canonical Command

```bash
python <cad-skill>/scripts/ortho_check --help
```

## Usage

### Basic three-view check

```bash
python <cad-skill>/scripts/ortho_check models/path/to/part.py \
  --out-dir /tmp/cad-checks
```

### Check a direct STEP file

```bash
python <cad-skill>/scripts/ortho_check models/path/to/part.step \
  --out-dir /tmp/cad-checks
```

### Custom views and JSON report

```bash
python <cad-skill>/scripts/ortho_check models/path/to/assembly.py \
  --out-dir /tmp/cad-checks \
  --views front,top,left \
  --report /tmp/cad-checks/report.json \
  --json
```

## Arguments

| Flag | Description |
|------|-------------|
| `targets...` | One or more Python generators, STEP/STP paths, or `@cad[...]` refs. |
| `--out-dir` | **Required.** Directory to write PNG snapshots and reports. |
| `--views` | Comma-separated views. Default: `front,top,right`. |
| `--width` | Image width in pixels. Default: `1200`. |
| `--height` | Image height in pixels. Default: `900`. |
| `--color` | Model RGB in `0..1`. Default: `0.80,0.84,0.90`. |
| `--background` | Background RGB in `0..1`. Default: `0.98,0.985,0.99`. |
| `--no-edges` | Disable feature-edge overlay. |
| `--no-axes` | Disable orientation axes inset. |
| `--json` | Print structured JSON report to stdout. |
| `--report` | Write JSON report to a file. |

## Output

For each target, the tool writes:

- `{stem}-{view}.png` per view into `--out-dir`
- Console lines showing `PASS`/`FAIL`, image paths, geometry checks, and errors
- Optional JSON report with `ok`, `results[].ok`, `results[].images`, `results[].checks`, and `results[].errors`

## Checks Performed

- **Mesh presence** — GLB must exist and contain vertices / triangles.
- **BBox validity** — Bounding-box dimensions must be strictly positive.
- **Topology presence** — Topology manifest (`.topology.json`) must exist and report non-zero face/edge/shape counts.

## Integration Into Validation Flow

Add `ortho_check` as an explicit post-generation step:

```bash
# 1. Generate
python <cad-skill>/scripts/gen_step_part models/path/to/part.py

# 2. Inspect (optional)
python <cad-skill>/scripts/cadref inspect '@cad[models/path/to/part]' --json

# 3. Three-view validation
python <cad-skill>/scripts/ortho_check models/path/to/part.py \
  --out-dir /tmp/cad-checks \
  --report /tmp/cad-checks/report.json
```

In CI pipelines, inspect the JSON report `ok` field; non-zero exit code indicates failure.

## Notes

- `ortho_check` does **not** generate missing GLBs. Run `gen_step_part` / `gen_step_assembly` first.
- It reuses the same rasterizer as `snapshot`, so renders are cropped, decimated previews — not full-fidelity meshes.
- Write temporary check outputs to `/tmp/...` or another scratch directory, not into `models/`.
