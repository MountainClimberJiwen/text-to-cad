#!/usr/bin/env python3
"""
Kimi Code Integration Layer
============================

把 autonomous pipeline 包装成 Kimi Code Agent 可以直接调用的工具函数。

使用方式（在 Kimi Code 对话中）：
    >>> from freecad-assembler.kimi_integration import analyze_image, generate_cad, preview
    >>> result = analyze_image("skills/industrial_cad/sample.jpg")
    >>> result = generate_cad("skills/industrial_cad/sample.jpg")
    >>> preview(result["step_path"])
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

# 确定 repo root
REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "freecad-assembler"))

# 懒加载，避免 import 时触发网络请求
_AssemblyIntent = None
_AssemblySolver = None
_AssemblyVerifier = None


def _ensure_imports():
    """延迟导入 framework 模块。"""
    global _AssemblyIntent, _AssemblySolver, _AssemblyVerifier
    if _AssemblyIntent is None:
        from framework.ontology import AssemblyIntent
        from framework.solver import AssemblySolver
        from framework.verifier import AssemblyVerifier
        _AssemblyIntent = AssemblyIntent
        _AssemblySolver = AssemblySolver
        _AssemblyVerifier = AssemblyVerifier


# ═══════════════════════════════════════════════════════
#  配置
# ═══════════════════════════════════════════════════════

DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY", "")
OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/kimi_assemblies"))


# ═══════════════════════════════════════════════════════
#  工具 1: 分析图片（vision parse + intent convert）
# ═══════════════════════════════════════════════════════

def analyze_image(image_path: str) -> dict:
    """
    分析工业自动化站图片，返回识别到的零件和关系。

    Args:
        image_path: 图片路径（相对于 repo root 或绝对路径）

    Returns:
        {
            "parts": [{"name": "...", "type": "...", "params": {...}}],
            "relations": [{"type": "...", "source": "...", "target": "..."}],
            "vision_raw": {...},  # Doubao 原始输出
            "summary": "识别到 N 个零件，M 个关系..."
        }
    """
    from image_to_assembly import parse_image_with_kimi as parse_image_with_llm, vision_output_to_intent

    path = Path(image_path)
    if not path.is_absolute():
        path = REPO_ROOT / path

    print(f"[KimiTool] Analyzing image: {path}")

    # Vision parse
    vision_data = parse_image_with_llm(str(path))
    n_parts = len(vision_data.get("parts", []))
    n_rels = len(vision_data.get("relations", []))
    print(f"[KimiTool] Vision: {n_parts} parts, {n_rels} relations")

    # Intent convert
    intent = vision_output_to_intent(vision_data)
    print(f"[KimiTool] Intent: {len(intent.parts)} parts, {len(intent.relations)} relations")

    # 返回结构化结果
    return {
        "parts": [{"name": p.name, "type": p.part_type.value, "params": p.params} for p in intent.parts],
        "relations": [{"type": r.rel_type.value, "source": r.source, "target": r.target} for r in intent.relations],
        "vision_raw": vision_data,
        "summary": f"识别到 {len(intent.parts)} 个零件，{len(intent.relations)} 个关系。关键零件: {', '.join(set(p.part_type.value for p in intent.parts))}",
    }


# ═══════════════════════════════════════════════════════
#  工具 2: 生成 CAD（完整 pipeline）
# ═══════════════════════════════════════════════════════

def generate_cad(image_path: str, output_dir: Optional[str] = None) -> dict:
    """
    从图片生成完整 CAD 装配体。

    Args:
        image_path: 图片路径
        output_dir: 输出目录（默认 /tmp/kimi_assemblies/<request_id>）

    Returns:
        {
            "success": True/False,
            "step_path": "...",
            "preview_path": "...",
            "report": {"part_count": N, "critical_issues": 0, ...},
            "viewer_link": "http://127.0.0.1:4178/?..."
        }
    """
    from image_to_assembly import parse_image_with_llm, vision_output_to_intent
    from framework.assembly_builder import build_assembly_script
    _ensure_imports()

    path = Path(image_path)
    if not path.is_absolute():
        path = REPO_ROOT / path

    request_id = f"kimi_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}"
    out_dir = Path(output_dir) if output_dir else OUTPUT_DIR / request_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"[KimiTool] generate_cad: {path.name} → {out_dir}")
    print(f"{'='*60}")

    try:
        # Step 1: Vision + Intent
        print("\n[Step 1/4] Vision & Intent...")
        vision = parse_image_with_llm(str(path))
        intent = vision_output_to_intent(vision)
        print(f"  → {len(intent.parts)} parts, {len(intent.relations)} relations")

        # Step 2: Solve & Verify
        print("\n[Step 2/4] Solve & Verify...")
        solver = _AssemblySolver(intent)
        boxes = solver.solve()
        verifier = _AssemblyVerifier(boxes, intent=intent)
        violations = verifier.verify_all()
        critical = len([v for v in violations if v.severity == "CRITICAL"])
        print(f"  → {critical} CRITICAL, {len(violations)-critical} other")

        # Step 3: Build Assembly Script
        print("\n[Step 3/4] Build Assembly...")
        asm_script = out_dir / "assembly.py"
        build_assembly_script(intent, asm_script)

        # Step 4: Generate STEP
        print("\n[Step 4/4] Generate STEP...")
        result = subprocess.run(
            ["./.venv/bin/python", "skills/cad/scripts/gen_step_assembly", str(asm_script)],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"STEP generation failed: {result.stderr[:300]}")

        step_path = asm_script.with_suffix(".step")
        print(f"  → STEP: {step_path}")

        # Step 5: Preview
        preview_path = None
        glb_path = step_path.parent / f".{step_path.name}" / "model.glb"
        if glb_path.exists():
            preview_path = out_dir / "preview.png"
            subprocess.run(
                ["./.venv/bin/python", "skills/cad/scripts/snapshot", str(glb_path),
                 "--view", "isometric", "--out", str(preview_path)],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
            )
            if preview_path.exists():
                print(f"  → Preview: {preview_path}")

        # Report
        rel_step = step_path.relative_to(REPO_ROOT)
        report = {
            "success": critical == 0,
            "step_path": str(step_path),
            "preview_path": str(preview_path) if preview_path else None,
            "report_path": str(out_dir / "report.json"),
            "part_count": len(intent.parts),
            "relation_count": len(intent.relations),
            "critical_issues": critical,
            "viewer_link": f"http://127.0.0.1:4178/?dir={rel_step.parent}&file={rel_step.name}",
        }

        with open(out_dir / "report.json", "w") as f:
            json.dump(report, f, indent=2)

        print(f"\n{'='*60}")
        print(f"[KimiTool] {'✓ PASSED' if critical == 0 else '✗ FAILED'} ({critical} critical)")
        print(f"  STEP:     {step_path}")
        print(f"  Preview:  {preview_path}")
        print(f"  Viewer:   {report['viewer_link']}")
        print(f"{'='*60}")

        return report

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# ═══════════════════════════════════════════════════════
#  工具 3: 启动预览
# ═══════════════════════════════════════════════════════

def preview(step_path: str, open_browser: bool = False) -> str:
    """
    启动或返回 CAD 预览链接。

    Args:
        step_path: STEP 文件路径
        open_browser: 是否尝试打开浏览器（默认 False，只返回链接）

    Returns:
        viewer URL 字符串
    """
    path = Path(step_path)
    if not path.is_absolute():
        path = REPO_ROOT / path

    rel = path.relative_to(REPO_ROOT)
    url = f"http://127.0.0.1:4178/?dir={rel.parent}&file={rel.name}"

    # 确保 viewer 在运行
    viewer_check = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "http://127.0.0.1:4178"],
        capture_output=True,
        text=True,
    )
    if viewer_check.stdout.strip() != "200":
        print("[KimiTool] Viewer not running. Start with:")
        print(f"  cd {REPO_ROOT}/viewer && npm run dev:ensure")

    print(f"[KimiTool] Preview URL: {url}")
    return url


# ═══════════════════════════════════════════════════════
#  工具 4: 快速迭代（分析 + 生成 + 预览一站式）
# ═══════════════════════════════════════════════════════

def quick_build(image_path: str) -> dict:
    """
    一站式：分析图片 → 生成 CAD → 返回预览链接。

    这是最高频的用法，相当于 analyze + generate + preview 的组合。
    """
    result = generate_cad(image_path)
    if result.get("success") and result.get("step_path"):
        result["viewer_url"] = preview(result["step_path"])
    return result


# ═══════════════════════════════════════════════════════
#  CLI（方便直接测试）
# ═══════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", required=True)
    parser.add_argument("--mode", choices=["analyze", "cad", "quick"], default="quick")
    args = parser.parse_args()

    if args.mode == "analyze":
        print(json.dumps(analyze_image(args.image), indent=2, ensure_ascii=False))
    elif args.mode == "cad":
        print(json.dumps(generate_cad(args.image), indent=2, ensure_ascii=False))
    else:
        print(json.dumps(quick_build(args.image), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
