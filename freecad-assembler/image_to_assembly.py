#!/usr/bin/env python3
"""
Image-to-Assembly Pipeline (Kimi Vision + Sequential ICRL)
===========================================================

Validation workflow:
    1. Load a photo/rendering of an automation station (e.g. sample.jpg)
    2. Use Kimi k2 (vision-capable) to parse the image into structured BOM + relations
    3. Convert the vision output into an AssemblyIntent skeleton
    4. Run SequentialICRLAgent to ground each part topologically
    5. Output: solved AssemblyIntent + verification report

Usage:
    cd freecad-assembler
    export KIMI_API_KEY=sk-xxx
    python3 image_to_assembly.py --image ../skills/industrial_cad/sample.jpg
"""

import argparse
import base64
import copy
import json
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO_ROOT)

from framework.ontology import (
    AssemblyIntent, PartSpec, Relation,
    PartType, RelationType, get_defaults
)
from framework.solver import AssemblySolver
from framework.verifier import AssemblyVerifier
from sequential_icrl import SequentialICRLAgent, format_intent, save_intent

# ------------------------------------------------------------------
# LLM client (Doubao for vision, Kimi fallback)
# ------------------------------------------------------------------
from llm_http import call_llm as _call_llm


def _compress_image(image_path: str, max_width: int = 400, quality: int = 75) -> str:
    """Resize and compress image for API upload, return base64."""
    from PIL import Image
    import io
    img = Image.open(image_path)
    w, h = img.size
    if w > max_width:
        img = img.resize((max_width, int(h * max_width / w)), Image.LANCZOS)
    # Convert RGBA or P mode to RGB for JPEG compatibility
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _encode_image(image_path: str) -> str:
    return _compress_image(image_path)


def parse_image_with_kimi(image_path: str) -> Dict[str, Any]:
    """
    Send image + structured prompt to Kimi k2 vision model.
    Returns parsed JSON with parts, relations, and spatial analysis.
    """
    b64 = _encode_image(image_path)

    system_prompt = "You are a CAD engineer. Analyze images and output structured JSON only."

    user_prompt = """Analyze this automation equipment image. Output ONLY a JSON object (no markdown):

{
  "station_type": "...",
  "description": "...",
  "parts": [
    {"name": "english_name_with_underscores", "type": "cylinder|gripper|vibration_bowl|guide_rail|beam|column|slider|fixture|fixture_plate|sensor|motor|piston|base_plate|hopper|hopper_support|linear_track", "description": "...", "approximate_position": "left|right|top|bottom|center", "estimated_params": {"width": 800, "height": 100}}
  ],
  "relations": [
    {"type": "supported_by|mounted_on|aligned_center|guides|drives|reaches|clearance|connected_to", "source": "...", "target": "...", "axis": "x|y|z"}
  ],
  "key_constraints": ["..."],
  "interference_risks": ["..."]
}

Include ALL labeled parts."""

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": [
                {"type": "text", "text": user_prompt},
                {
                    "type": "image_url",
                    "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
                },
            ],
        },
    ]

    print("[Vision] Sending image to Kimi k2 for analysis...")
    result = _call_llm(messages, temperature=0.3, max_tokens=4096, provider="doubao")
    if not isinstance(result, dict):
        raise RuntimeError(f"Expected dict from vision parse, got {type(result).__name__}")
    return result


# ------------------------------------------------------------------
# Convert vision output → AssemblyIntent
# ------------------------------------------------------------------

def vision_output_to_intent(data: Dict[str, Any]) -> AssemblyIntent:
    """
    Convert Kimi vision parser output into a formal AssemblyIntent,
    applying default parameters where estimates are missing.
    """
    intent = AssemblyIntent()

    # Global params
    intent.global_params["station_type"] = data.get("station_type", "unknown")
    intent.global_params["description"] = data.get("description", "")

    # Parts
    for pdata in data.get("parts", []):
        try:
            ptype = PartType(pdata["type"])
        except ValueError:
            # Fuzzy fallback
            ptype = PartType.BASE_PLATE
            search = pdata["type"].lower().replace(" ", "_")
            for pt in PartType:
                if search in pt.value or pt.value in search:
                    ptype = pt
                    break

        # Merge defaults with estimated params
        params = copy.deepcopy(get_defaults(ptype))
        est = pdata.get("estimated_params", {})
        if isinstance(est, dict):
            params.update(est)

        part = PartSpec(
            name=pdata["name"],
            part_type=ptype,
            params=params,
        )
        intent.parts.append(part)

    # Ensure base_plate exists
    has_base = any(p.part_type == PartType.BASE_PLATE for p in intent.parts)
    if not has_base:
        intent.parts.insert(0, PartSpec(
            name="base_plate",
            part_type=PartType.BASE_PLATE,
            params=get_defaults(PartType.BASE_PLATE),
        ))

    # Relations
    for rdata in data.get("relations", []):
        if not isinstance(rdata, dict):
            continue
        try:
            rtype = RelationType(rdata["type"])
        except (ValueError, KeyError):
            continue
        # Validate part names exist
        src = rdata.get("source", "")
        tgt = rdata.get("target", "")
        part_names = {p.name for p in intent.parts}
        if src not in part_names or tgt not in part_names:
            # Skip dangling relations for now; could auto-add placeholder parts
            continue

        rel = Relation(
            rel_type=rtype,
            source=src,
            target=tgt,
            axis=rdata.get("axis"),
            min_dist=rdata.get("min_dist"),
        )
        intent.relations.append(rel)

    # Auto-add common engineering relations if missing
    _auto_complete_relations(intent)

    # Assign initial x,y coordinates based on approximate_position to avoid stacking at (0,0)
    _assign_positions_from_approximate(intent)

    return intent


def _assign_positions_from_approximate(intent: AssemblyIntent):
    """Map approximate_position + part_type to reasonable x,y on base_plate."""
    base_w = 800
    base_d = 500

    for p in intent.parts:
        if p.part_type == PartType.BASE_PLATE:
            continue
        if "x" in p.params and "y" in p.params:
            continue

        pos = p.params.get("approximate_position", "")
        name = p.name.lower()
        ptype = p.part_type

        # ── Vibration system (far right, spread vertically) ──
        if ptype == PartType.VIBRATION_BOWL:
            p.params["x"] = base_w * 0.78
            p.params["y"] = base_d * 0.22
            # Clamp to reasonable size for small-part feeding station
            p.params["diameter"] = min(p.params.get("diameter", 150), base_w * 0.20, 180)
            p.params["height"] = min(p.params.get("height", 100), base_w * 0.15, 120)
        elif ptype == PartType.HOPPER:
            p.params["x"] = base_w * 0.78
            p.params["y"] = base_d * 0.72
        elif ptype == PartType.HOPPER_SUPPORT:
            p.params["x"] = base_w * 0.78
            p.params["y"] = base_d * 0.48

        # ── Central gantry / pick-and-place (stacked on center column) ──
        # ONLY parts explicitly named as *transfer* cylinders belong here
        elif ptype in (PartType.COLUMN, PartType.GANTRY) and ("column" in name or "support" in name or "gantry" in name):
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.45
        elif "horizontal_transfer" in name:
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.45
        elif "vertical_transfer" in name:
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.45
        elif "gripper" in name:
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.45

        # ── Guide rails (offset AWAY from the parts they guide) ──
        elif ptype == PartType.GUIDE_RAIL:
            if "horiz_transfer" in name or "horizontal_transfer" in name:
                p.params["x"] = base_w * 0.58
                p.params["y"] = base_d * 0.45
            elif "vert_transfer" in name or "vertical_transfer" in name:
                p.params["x"] = base_w * 0.45
                p.params["y"] = base_d * 0.58
            elif "horiz" in name or "horizontal" in name:
                p.params["x"] = base_w * 0.08
                p.params["y"] = base_d * 0.75
            elif "guide" in name:
                p.params["x"] = base_w * 0.08
                p.params["y"] = base_d * 0.55
            else:
                p.params["x"] = base_w * 0.55
                p.params["y"] = base_d * 0.55

        # ── Left-side positioning / actuation system (spread out) ──
        elif "guide" in name and ptype == PartType.GUIDE_RAIL and "cyl" not in name:
            p.params["x"] = base_w * 0.15
            p.params["y"] = base_d * 0.30
        elif "guide_cyl" in name or ("guide" in name and ptype == PartType.CYLINDER):
            p.params["x"] = base_w * 0.15
            p.params["y"] = base_d * 0.55
        elif ptype == PartType.CYLINDER and "actuation" in name:
            p.params["x"] = base_w * 0.15
            p.params["y"] = base_d * 0.75
        elif "horizontal" in name and "push" in name:
            p.params["x"] = base_w * 0.15
            p.params["y"] = base_d * 0.80
        elif ptype == PartType.CYLINDER and "position" in name:
            p.params["x"] = base_w * 0.15
            p.params["y"] = base_d * 0.80

        # ── Linear track (between vibration bowl and center) ──
        elif ptype == PartType.LINEAR_TRACK:
            p.params["x"] = base_w * 0.60
            p.params["y"] = base_d * 0.22

        # ── Fallback by position keyword ──
        elif "right_lower" in pos:
            p.params["x"] = base_w * 0.78
            p.params["y"] = base_d * 0.22
        elif "right" in pos or "bottom_right" in pos:
            p.params["x"] = base_w * 0.78
            p.params["y"] = base_d * 0.55
        elif "left_lower" in pos:
            p.params["x"] = base_w * 0.15
            p.params["y"] = base_d * 0.25
        elif "left" in pos:
            p.params["x"] = base_w * 0.15
            p.params["y"] = base_d * 0.55
        elif "center_lower" in pos:
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.65
        elif "center" in pos or "top" in pos:
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.45
        elif "bottom" in pos:
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.45
        else:
            p.params["x"] = base_w * 0.45
            p.params["y"] = base_d * 0.45


def _auto_complete_relations(intent: AssemblyIntent):
    """
    Auto-add relations that are logically implied but may have been missed by vision parser.
    """
    part_names = {p.name for p in intent.parts}

    # Every non-base part should have at least one support relation
    for p in intent.parts:
        if p.part_type == PartType.BASE_PLATE:
            continue
        has_support = any(
            (r.source == p.name and r.rel_type in (RelationType.SUPPORTED_BY, RelationType.MOUNTED_ON))
            for r in intent.relations
        )
        if not has_support and "base_plate" in part_names:
            # Heuristic: guess what supports this part
            intent.relations.append(Relation(
                rel_type=RelationType.SUPPORTED_BY,
                source=p.name,
                target="base_plate",
            ))

    # Cylinders with stroke > 50 should have guide rails
    for p in intent.parts:
        if p.part_type == PartType.CYLINDER:
            stroke = float(p.params.get("stroke", 0) or 0)
            if stroke > 50:
                has_guide = any(
                    r.rel_type == RelationType.GUIDES and r.target == p.name
                    for r in intent.relations
                )
                if not has_guide:
                    guide_name = f"{p.name}_guide"
                    if guide_name not in part_names:
                        # Auto-add guide rail part
                        guide = PartSpec(
                            name=guide_name,
                            part_type=PartType.GUIDE_RAIL,
                            params={"width": 10, "depth": 15, "height": p.params.get("body_length", 120) * 1.2},
                        )
                        intent.parts.append(guide)
                    intent.relations.append(Relation(
                        rel_type=RelationType.GUIDES,
                        source=guide_name,
                        target=p.name,
                    ))


# ------------------------------------------------------------------
# Full pipeline
# ------------------------------------------------------------------

def run_pipeline(image_path: str, output_dir: str = "checkpoint") -> AssemblyIntent:
    """
    Complete pipeline: image → vision parse → intent skeleton → sequential ICRL.
    """
    print("=" * 60)
    print("Image-to-Assembly Pipeline")
    print("=" * 60)

    # Validate API key
    from kimi_http import KIMI_API_KEY
    if not KIMI_API_KEY:
        print("ERROR: No Kimi API key found.")
        sys.exit(1)

    # Step 1: Vision parse
    print("\n[Step 1/4] Parsing image with Kimi Vision...")
    vision_data = parse_image_with_kimi(image_path)
    print(f"  Detected station type: {vision_data.get('station_type', 'unknown')}")
    print(f"  Parts from vision: {len(vision_data.get('parts', []))}")
    print(f"  Relations from vision: {len(vision_data.get('relations', []))}")

    # Step 2: Convert to AssemblyIntent
    print("\n[Step 2/4] Converting vision output to AssemblyIntent...")
    skeleton = vision_output_to_intent(vision_data)
    print(f"  Intent parts: {len(skeleton.parts)}")
    print(f"  Intent relations: {len(skeleton.relations)}")

    # Print vision-derived constraints
    for c in vision_data.get("key_constraints", []):
        print(f"  Constraint: {c}")
    for r in vision_data.get("interference_risks", []):
        print(f"  Risk: {r}")

    # Step 3: Sequential ICRL refinement using the vision skeleton directly
    # NOTE: Doubao generates reasonable params directly, so we skip expensive
    # per-part LLM refinement and go straight to geometric solve.
    print("\n[Step 3/4] Using Doubao-generated skeleton (skipping per-part LLM refinement)")
    best_intent = skeleton
    best_reward = 0.0

    # Step 4: Final verification & save
    print("\n[Step 4/4] Final verification...")
    solver = AssemblySolver(best_intent)
    boxes = solver.solve()
    verifier = AssemblyVerifier(boxes, intent=best_intent)
    violations = verifier.verify_all()
    verifier.print_report()

    out_dir = Path(REPO_ROOT) / output_dir
    out_dir.mkdir(exist_ok=True)

    # Save intent
    intent_path = out_dir / "image_assembly_intent.json"
    save_intent(best_intent, str(intent_path), {
        "source_image": str(Path(image_path).resolve()),
        "vision_parse": vision_data,
        "best_reward": best_reward,
        "violations": [
            {"severity": v.severity, "rule_id": v.rule_id, "message": v.message, "parts": v.parts_involved}
            for v in violations
        ],
    })
    print(f"\nSaved intent to: {intent_path}")

    # Save vision parse raw
    vision_path = out_dir / "image_vision_parse.json"
    with open(vision_path, "w") as f:
        json.dump(vision_data, f, indent=2, ensure_ascii=False)
    print(f"Saved vision parse to: {vision_path}")

    # ── Step 5: Auto-generate CAD assembly with fasteners ──
    print("\n[Step 5/5] Auto-generating CAD assembly with fasteners...")
    try:
        from framework.assembly_builder import build_assembly_script

        repo_root = Path(REPO_ROOT).parent  # go up to text-to-cad root
        asm_script_path = repo_root / "models" / "assemblies" / "auto_station_from_vision.py"
        asm_script_path.parent.mkdir(parents=True, exist_ok=True)

        build_assembly_script(best_intent, asm_script_path)

        # Generate STEP
        import subprocess
        gen_result = subprocess.run(
            ["./.venv/bin/python", "skills/cad/scripts/gen_step_assembly", str(asm_script_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
        if gen_result.returncode == 0:
            print(f"  Generated STEP: {asm_script_path.with_suffix('.step')}")
        else:
            print(f"  STEP generation warning: {gen_result.stderr[:200]}")

        # Snapshot preview
        glb_path = asm_script_path.parent / f".{asm_script_path.name.replace('.py', '.step')}" / "model.glb"
        if glb_path.exists():
            snap_result = subprocess.run(
                ["./.venv/bin/python", "skills/cad/scripts/snapshot", str(glb_path),
                 "--view", "isometric", "--out", "/tmp/auto_station_preview.png"],
                cwd=repo_root,
                capture_output=True,
                text=True,
            )
            if snap_result.returncode == 0:
                print(f"  Preview saved: /tmp/auto_station_preview.png")
            else:
                print(f"  Snapshot warning: {snap_result.stderr[:200]}")

        print(f"\n  Viewer link: http://127.0.0.1:4178/?dir=models/assemblies&file={asm_script_path.name.replace('.py', '.step')}")
    except Exception as e:
        print(f"  Assembly generation skipped: {e}")

    return best_intent


# ------------------------------------------------------------------
# CLI
# ------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Image-to-Assembly Pipeline")
    parser.add_argument("--image", required=True, help="Path to input image (JPG/PNG)")
    parser.add_argument("--output-dir", default="checkpoint", help="Output directory")
    args = parser.parse_args()

    run_pipeline(args.image, args.output_dir)


if __name__ == "__main__":
    main()
