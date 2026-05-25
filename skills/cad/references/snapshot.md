# Snapshot Tool

`scripts/snapshot` renders verification PNGs from generated GLB outputs and STL meshes.

Run commands from the project or workspace directory that makes your target paths resolve.

## Canonical Command

```bash
python <cad-skill>/scripts/snapshot --help
```

## Supported Inputs

- a single part or generated assembly GLB such as `path/to/.part.step/model.glb` or `path/to/.assembly.step/model.glb`
- a single part STL such as `path/to/part.stl`

GLB/STL inputs must already exist. `snapshot` does not generate missing mesh artifacts and does not require a harness root.

For generated assemblies, use the generated assembly GLB. If the GLB is missing or stale, first regenerate the explicit assembly target with `gen_step_assembly`, then snapshot the generated GLB.

## Examples

```bash
# Render a part GLB
python <cad-skill>/scripts/snapshot path/to/.part.step/model.glb \
  --out /tmp/cad-renders/part-glb.png

# Render a generated assembly GLB
python <cad-skill>/scripts/gen_step_assembly path/to/assembly.py
python <cad-skill>/scripts/snapshot path/to/.assembly.step/model.glb \
  --out /tmp/cad-renders/assembly.png

# Render a part STL
python <cad-skill>/scripts/snapshot path/to/part.stl \
  --out /tmp/cad-renders/part-stl.png

# Render several views from one mesh load
python <cad-skill>/scripts/snapshot path/to/.part.step/model.glb \
  --views isometric,top,right --out-dir /tmp/cad-renders

# Choose the closest orthographic view from a face ref
python <cad-skill>/scripts/snapshot path/to/.part.step/model.glb \
  --align-ref '@cad[models/path/to/part#f2]' \
  --out /tmp/cad-renders/part-aligned.png
```

## Notes

- GLB/STL meshes must already exist; missing inputs are errors.
- For generated assemblies, use the generated assembly GLB because it matches the viewer-consumed artifact.
- Python assembly source inputs are not supported by `snapshot`.
- Supported fixed views are `front`, `back`, `right`, `left`, `top`, `bottom`, and `isometric`.
- Use `--views <comma-list>` or `--views all` with `--out-dir` to render multiple fixed views from one mesh load.
- `--align-ref @cad[...]` resolves one face or edge ref and chooses the closest orthographic view automatically.
- Renders are cropped tightly to content and reserve a small axis inset when axes are enabled.
- Mesh previews are decimated for readability and speed; `snapshot` is a verification view, not a full-fidelity mesh viewer.
- `snapshot` is intended as a quick mesh verification tool, not the source of truth for geometry.
