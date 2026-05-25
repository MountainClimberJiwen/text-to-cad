# CAD Explorer

If you are modifying the viewer, start here.

This folder contains the CAD Explorer web app. The viewer is read-only with respect to files in the active CAD scan directory.

## Prompt Workflow

- The viewer discovers displayable entries by scanning the directory from the `?dir=` query param, defaulting to the harness CAD directory, then loads package-local render assets and generated URDF/authored DXF XML/text from that tree.
- Prompt-ready `@cad[...]` refs are expected output from the workspace. The full grammar lives in [CAD prompt references](../skills/cad/references/prompt-refs.md).
- Common copied ref shapes include whole entries, occurrences, shape/face/edge/corner selectors, and grouped same-occurrence selectors, such as `@cad[<repo-relative-cad-path>]`, `@cad[<repo-relative-cad-path>#o1.2]`, `@cad[<repo-relative-cad-path>#f12]`, and `@cad[<repo-relative-cad-path>#o1.2.f12,f13,e7,v4]`.
- The path inside `@cad[...]` is the repository-relative STEP path without `.step` or `.stp`.
- Assembly refs use generated assembly STEP topology, so face/edge/corner copy targets the assembly entry.
- Drawing tools and screenshots are communication aids, not source of truth.
- Agents interpreting `@cad[...]` refs should resolve them from source STEP data with `skills/cad/scripts/cadref`, not against viewer assets.

## Data Model

- The viewer discovers entries by scanning existing `.step`, `.stp`, `.stl`, `.dxf`, and `.urdf` files. It does not inspect Python generators for discovery.
- STEP part entries load:
  - package-local `<cad-dir>/.../.<step-filename>/model.glb` for display
  - package-local `<cad-dir>/.../.<step-filename>/topology.json`
  - package-local `<cad-dir>/.../.<step-filename>/topology.bin`
- STEP assembly entries require package-local `<cad-dir>/.../.<step-filename>/model.glb`, load package-local `<cad-dir>/.../.<step-filename>/topology.json`, and read assembly composition from `assembly.root`. Generated Python assemblies link to scanned part GLBs; imported native STEP assemblies use `.<step-filename>/components/*.glb` URLs embedded in the topology composition.
- DXF entries load:
  - authored `<cad-dir>/.../*.dxf` directly
- STL entries load:
  - standalone or configured exported `<cad-dir>/.../*.stl` meshes directly
- URDF entries load:
  - generated `<cad-dir>/.../*.urdf` XML directly
  - referenced URDF STL mesh filenames directly
- The viewer UI is in `viewer/components/CadViewer.js`.
- The flat-pattern viewer UI is in `viewer/components/DxfViewer.js`.
- The workspace UI is in `viewer/components/CadWorkspace.js`.

Do not hand-edit package-local generated CAD assets during normal CAD or viewer work.

## Persistence

- CAD Explorer persistence is browser-only and is owned by `viewer/lib/workbench/persistence.js`.
- URL query params are share state:
  - `?file=` selects the active CAD entry.
  - `?refs=` carries prompt references into the workspace.
  - `?resetPersistence=1` clears CAD Explorer browser state for the current origin, then removes itself from the URL before the app renders.
- `sessionStorage` key `cad-explorer:workbench-session:v2` stores the scratch workspace in the canonical shape `{ version, global, tabs: { selectedKey, openOrder, byKey } }`.
- `localStorage` key `cad-explorer:workbench-global:v1` stores the global workspace state used across reloads, including search query, expanded directories, sidebar state, and tool widths.
- `localStorage` key `cad-explorer:look-settings` stores visual look settings, `cad-explorer:workbench-glass-tone:v1` stores the workspace glass tone, and `cad-explorer-theme` stores the forced dark theme preference.
- `sessionStorage` key `cad-explorer:dxf-bend-overrides:v1` stores per-file DXF bend overrides for the active browser tab.
- Directory expansion no longer has a separate file-explorer storage key; it is part of workspace global state.
- React state updates immediately. Browser-storage writes are coalesced briefly and flushed on `pagehide`, `beforeunload`, and workspace unmount. If a write fails because storage is blocked or full, the workspace shows a status toast.

## Runtime

- `npm run dev` starts `vite dev`, scans `?dir=` dynamically, and updates the workspace when matching CAD files or per-STEP viewer assets are added, changed, or removed.
- `npm run build` scans `CAD_DIR` when provided, defaulting to `models`, and bakes that scan into the static app.
- `npm run build:app` runs an isolated verification build for viewer-only changes.
- Regenerate CAD assets outside the viewer package before these commands when CAD assets need to change.

## Hot Reload

- Real-time dev updates come from the Vite CAD catalog endpoint and websocket events, not browser polling.
- When external tools add, remove, or update `.step`, `.stp`, `.stl`, `.dxf`, `.urdf`, `.<step-filename>/*.glb`, `.<step-filename>/topology.json`, or `.<step-filename>/topology.bin` files under an active scan directory, Vite asks the client to rescan and remount the workspace.

## UX Contract

- STEP part and assembly entries expose face/edge/corner picking from selector proxy geometry.
- Shape and occurrence refs are exposed through inspector state, not a separate canvas pick mode.
- DXF entries are read-only flat-pattern views.
- URDF entries are read-only robot views with joint sliders; they do not expose picking, refs, or drawing tools.
- File pickers use canonical suffix labels: STEP parts and assemblies show `.step`, STL entries show `.stl`, URDF entries show `.urdf`, and DXF entries show `.dxf`.
- The workspace selects one file at a time. Per-file view, reference, drawing, and tool state is still restored from the existing session `tabs` state when a file is selected again.
- Sidebar grouping follows the exact directory structure under the active scan directory, not hardcoded part/assembly roots.

## Verification For Viewer Changes

- For pure viewer changes, run `cd viewer && npm run build:app`.
- Run `cd viewer && npm run test:node` when the change touches viewer logic, parsing, persistence, catalog scanning, selectors, or kinematics.
- Run `cd viewer && npm run build` when you need the normal production `dist/` output for the current generated CAD snapshot.
- If the change depends on fresh CAD-derived assets, regenerate the affected entries separately with `skills/cad/scripts/gen_step_part`, `skills/cad/scripts/gen_step_assembly`, `skills/cad/scripts/gen_dxf`, or `skills/urdf/scripts/gen_urdf` before viewer verification.
- For render-contract changes, inspect the relevant package-local `.<step-filename>/model.glb`, `.<step-filename>/topology.json`, `.<step-filename>/topology.bin`, native assembly `.<step-filename>/components/*.glb` meshes, visible `.stl`, visible `.dxf`, or visible `.urdf` files.

## Run

From repo root:

```bash
cd viewer
npm install
npm run dev
```

Then open:

- `http://localhost:4178`
