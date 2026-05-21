#!/usr/bin/env python3
"""
Autonomous Image-to-Assembly Pipeline
======================================

完全自主运行，无需人工干预：
  1. 从环境变量读取配置（API key、路径等）
  2. 自动重试不稳定的 Vision API（最多3次，取零件数最多的结果）
  3. 自动执行几何求解、连接件生成、CAD导出
  4. 自动验收（零件数检查 + 干涉检查 + 预览图生成）
  5. 失败时自动回退到备用方案
  6. 输出结构化结果（JSON报告 + CAD文件 + 预览图）

Usage:
    export DOUBAO_API_KEY=xxx
    export OUTPUT_DIR=/tmp/assemblies
    python autonomous_pipeline.py --image /path/to/station.jpg
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "freecad-assembler"))

from framework.ontology import AssemblyIntent, PartSpec, Relation, PartType, RelationType
from framework.solver import AssemblySolver
from framework.verifier import AssemblyVerifier


# ═══════════════════════════════════════════════════════
#  1. 配置管理（从环境变量读取，无需代码修改）
# ═══════════════════════════════════════════════════════

class Config:
    """所有配置从环境变量读取，支持 .env 文件。"""
    DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY", "")
    DOUBAO_MODEL = os.environ.get("DOUBAO_MODEL", "doubao-seed-2-0-pro-260215")
    DOUBAO_BASE_URL = os.environ.get("DOUBAO_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
    KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
    OUTPUT_DIR = Path(os.environ.get("OUTPUT_DIR", "/tmp/auto_assemblies"))
    MAX_RETRIES = int(os.environ.get("MAX_RETRIES", "3"))
    MIN_PARTS = int(os.environ.get("MIN_PARTS", "6"))
    MAX_PARTS = int(os.environ.get("MAX_PARTS", "20"))
    ENABLE_DSPY = os.environ.get("ENABLE_DSPY", "true").lower() == "true"
    VIEWER_PORT = int(os.environ.get("VIEWER_PORT", "4178"))


# ═══════════════════════════════════════════════════════
#  2. Vision API（带重试和结果选择）
# ═══════════════════════════════════════════════════════

def call_vision_api(image_path: str, api_key: str) -> Optional[dict]:
    """调用 Doubao Vision API，返回解析后的 JSON。"""
    import base64

    try:
        from llm_http import call_doubao
    except ImportError:
        # 如果 llm_http 不可用，直接用 urllib
        import urllib.request

        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        prompt = (
            "Analyze this industrial automation station image. "
            "Output ONLY a JSON object with: station_type, parts[], relations[]. "
            "Each part has: name, type (base_plate/cylinder/column/guide_rail/gripper/"
            "vibration_bowl/hopper/linear_track/sensor), approximate_position, estimated_params."
        )

        payload = json.dumps({
            "model": Config.DOUBAO_MODEL,
            "messages": [
                {"role": "system", "content": "You are an expert in industrial automation equipment."},
                {"role": "user", "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]}
            ],
            "temperature": 0.2,
        }).encode()

        req = urllib.request.Request(
            f"{Config.DOUBAO_BASE_URL}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )

        with urllib.request.urlopen(req, timeout=120) as resp:
            result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"]["content"]
            # 提取 JSON
            import re
            m = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if m:
                content = m.group(1)
            return json.loads(content)

    except Exception as e:
        print(f"[Vision API Error] {e}")
        return None


def robust_vision_parse(image_path: str) -> dict:
    """
    稳定版 Vision Parse：
      1. 最多重试 MAX_RETRIES 次
      2. 选择零件数最多的结果（过滤掉识别失败的）
      3. 如果都失败，返回 fallback 模板
    """
    if not Config.DOUBAO_API_KEY:
        raise RuntimeError("DOUBAO_API_KEY not set. Set it via environment variable.")

    best_result = None
    best_part_count = 0

    for attempt in range(Config.MAX_RETRIES):
        print(f"[Vision] Attempt {attempt + 1}/{Config.MAX_RETRIES}...")
        result = call_vision_api(image_path, Config.DOUBAO_API_KEY)

        if result is None:
            time.sleep(2)
            continue

        n_parts = len(result.get("parts", []))
        n_rels = len(result.get("relations", []))
        print(f"  → {n_parts} parts, {n_rels} relations")

        if n_parts >= Config.MIN_PARTS and n_parts <= Config.MAX_PARTS:
            # 合格结果，直接返回
            return result

        if n_parts > best_part_count:
            best_part_count = n_parts
            best_result = result

        time.sleep(2)

    if best_result and best_part_count >= 3:
        print(f"[Vision] Using best result ({best_part_count} parts) after {Config.MAX_RETRIES} retries")
        return best_result

    # Fallback：返回一个最小模板，保证 pipeline 不崩溃
    print("[Vision] All attempts failed. Using fallback template.")
    return {
        "station_type": "automatic_feeding_station",
        "parts": [
            {"name": "station_base_plate", "type": "base_plate", "approximate_position": "bottom", "estimated_params": {"width": 800, "height": 15}},
            {"name": "transfer_column", "type": "column", "approximate_position": "center", "estimated_params": {"width": 80, "height": 400}},
            {"name": "product_gripper", "type": "gripper", "approximate_position": "center", "estimated_params": {"width": 40, "height": 60}},
            {"name": "vibration_bowl", "type": "vibration_bowl", "approximate_position": "right", "estimated_params": {"width": 200, "height": 150}},
        ],
        "relations": [
            {"type": "supported_by", "source": "transfer_column", "target": "station_base_plate"},
            {"type": "supported_by", "source": "vibration_bowl", "target": "station_base_plate"},
        ]
    }


# ═══════════════════════════════════════════════════════
#  3. Intent Convert（整合手写规则 + DSPy）
# ═══════════════════════════════════════════════════════

def vision_to_intent(vision_data: dict) -> AssemblyIntent:
    """将 Vision JSON 转换为 AssemblyIntent（使用现有的稳定规则）。"""
    from image_to_assembly import vision_output_to_intent
    return vision_output_to_intent(vision_data)


def dspy_enhance_connections(intent: AssemblyIntent) -> AssemblyIntent:
    """用 DSPy 优化连接件决策（如果启用）。"""
    if not Config.ENABLE_DSPY:
        return intent

    try:
        from dspy_optimizer import choose_best_connections

        intent_dict = {
            "parts": [{"name": p.name, "type": p.part_type.value, "params": p.params} for p in intent.parts],
            "relations": [{"type": r.rel_type.value, "source": r.source, "target": r.target} for r in intent.relations],
        }

        result = choose_best_connections(intent_dict)
        print(f"[DSPy] ConnectionInfer: {result['eval']['score']} score, {result['eval']['total_fasteners']} fasteners")

        # 将 DSPy 决策保存到 intent 的 global_params 中，供 assembly_builder 使用
        intent.global_params["_dspy_connections"] = result["connections"]
        return intent

    except Exception as e:
        print(f"[DSPy] Fallback to rule-based: {e}")
        return intent


# ═══════════════════════════════════════════════════════
#  4. 几何求解与验证
# ═══════════════════════════════════════════════════════

def solve_and_verify(intent: AssemblyIntent) -> Tuple[Dict, List, bool]:
    """求解坐标并验证，返回 (boxes, violations, passed)。"""
    solver = AssemblySolver(intent)
    boxes = solver.solve()
    verifier = AssemblyVerifier(boxes, intent=intent)
    violations = verifier.verify_all()

    critical = [v for v in violations if v.severity == "CRITICAL"]
    warnings = [v for v in violations if v.severity == "WARNING"]
    passed = len(critical) == 0

    print(f"[Verify] {len(critical)} CRITICAL, {len(warnings)} WARNING, {len(violations) - len(critical) - len(warnings)} INFO")
    return boxes, violations, passed


# ═══════════════════════════════════════════════════════
#  5. CAD 生成（自动化封装）
# ═══════════════════════════════════════════════════════

def generate_cad(intent: AssemblyIntent, output_dir: Path, request_id: str) -> Path:
    """生成 CAD assembly 文件，返回 STEP 路径。"""
    from framework.assembly_builder import build_assembly_script

    script_path = output_dir / f"{request_id}_assembly.py"
    build_assembly_script(intent, script_path)

    # 调用 gen_step_assembly
    result = subprocess.run(
        ["./.venv/bin/python", "skills/cad/scripts/gen_step_assembly", str(script_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        raise RuntimeError(f"CAD generation failed: {result.stderr}")

    step_path = script_path.with_suffix(".step")
    print(f"[CAD] Generated: {step_path}")
    return step_path


def generate_preview(step_path: Path, output_dir: Path, request_id: str) -> Optional[Path]:
    """生成预览图。"""
    glb_path = step_path.parent / f".{step_path.name}" / "model.glb"
    if not glb_path.exists():
        print("[Preview] GLB not found, skipping snapshot")
        return None

    png_path = output_dir / f"{request_id}_preview.png"
    result = subprocess.run(
        ["./.venv/bin/python", "skills/cad/scripts/snapshot", str(glb_path),
         "--view", "isometric", "--out", str(png_path)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )

    if result.returncode == 0 and png_path.exists():
        print(f"[Preview] Generated: {png_path}")
        return png_path
    else:
        print(f"[Preview] Failed: {result.stderr[:200]}")
        return None


# ═══════════════════════════════════════════════════════
#  6. 验收（自动质量检查）
# ═══════════════════════════════════════════════════════

def auto_acceptance(intent: AssemblyIntent, violations: list, preview_path: Optional[Path]) -> dict:
    """自动验收，返回质量报告。"""
    report = {
        "part_count": len(intent.parts),
        "relation_count": len(intent.relations),
        "critical_count": len([v for v in violations if v.severity == "CRITICAL"]),
        "warning_count": len([v for v in violations if v.severity == "WARNING"]),
        "has_preview": preview_path is not None,
        "passed": False,
        "reasons": [],
    }

    if report["critical_count"] > 0:
        report["reasons"].append(f"{report['critical_count']} critical violations")
    if report["part_count"] < Config.MIN_PARTS:
        report["reasons"].append(f"Only {report['part_count']} parts (min {Config.MIN_PARTS})")
    if not report["has_preview"]:
        report["reasons"].append("Preview generation failed")

    report["passed"] = len(report["reasons"]) == 0
    return report


# ═══════════════════════════════════════════════════════
#  7. 主流程
# ═══════════════════════════════════════════════════════

def run_autonomous_pipeline(image_path: str) -> dict:
    """
    完全自主运行的主流程。

    Returns:
        {
            "request_id": str,
            "success": bool,
            "step_path": str,
            "preview_path": str,
            "report": dict,
            "intent": dict,
        }
    """
    import uuid
    request_id = f"asm_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    output_dir = Config.OUTPUT_DIR / request_id
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"[AutoPipeline] Request {request_id}")
    print(f"{'='*60}")

    try:
        # Step 1: Vision Parse（带重试）
        print("\n[Step 1/5] Vision Parse...")
        vision_data = robust_vision_parse(image_path)
        print(f"  → {len(vision_data.get('parts', []))} parts detected")

        # Step 2: Intent Convert
        print("\n[Step 2/5] Intent Convert...")
        intent = vision_to_intent(vision_data)
        intent = dspy_enhance_connections(intent)
        print(f"  → {len(intent.parts)} parts, {len(intent.relations)} relations")

        # Step 3: Solve & Verify
        print("\n[Step 3/5] Solve & Verify...")
        boxes, violations, passed = solve_and_verify(intent)

        # Step 4: CAD Generation
        print("\n[Step 4/5] CAD Generation...")
        step_path = generate_cad(intent, output_dir, request_id)

        # Step 5: Preview
        print("\n[Step 5/5] Preview Generation...")
        preview_path = generate_preview(step_path, output_dir, request_id)

        # Auto Acceptance
        report = auto_acceptance(intent, violations, preview_path)

        # Save full report
        report_data = {
            "request_id": request_id,
            "success": report["passed"],
            "step_path": str(step_path),
            "preview_path": str(preview_path) if preview_path else None,
            "report": report,
            "intent": {
                "parts": [{"name": p.name, "type": p.part_type.value, "params": p.params} for p in intent.parts],
                "relations": [{"type": r.rel_type.value, "source": r.source, "target": r.target} for r in intent.relations],
            },
            "violations": [
                {"severity": v.severity, "rule_id": v.rule_id, "message": v.message}
                for v in violations
            ],
        }
        report_path = output_dir / "report.json"
        with open(report_path, "w") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)

        print(f"\n{'='*60}")
        print(f"[Result] {'✓ PASSED' if report['passed'] else '✗ FAILED'}")
        print(f"  STEP: {step_path}")
        print(f"  Preview: {preview_path}")
        print(f"  Report: {report_path}")
        print(f"{'='*60}")

        return report_data

    except Exception as e:
        print(f"\n[ERROR] Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return {
            "request_id": request_id,
            "success": False,
            "error": str(e),
        }


# ═══════════════════════════════════════════════════════
#  CLI
# ═══════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="Autonomous Image-to-Assembly Pipeline")
    parser.add_argument("--image", required=True, help="Path to input image")
    parser.add_argument("--output-dir", default=None, help="Output directory (overrides env)")
    args = parser.parse_args()

    if args.output_dir:
        Config.OUTPUT_DIR = Path(args.output_dir)

    if not Config.DOUBAO_API_KEY:
        print("[ERROR] DOUBAO_API_KEY not set.")
        print("  export DOUBAO_API_KEY=your_key_here")
        sys.exit(1)

    result = run_autonomous_pipeline(args.image)
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
