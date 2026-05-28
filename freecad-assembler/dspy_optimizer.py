#!/usr/bin/env python3
"""
DSPy Optimizer — 生产级集成
===========================

适用场景评估：
  ✓ ConnectionInfer:  输入短、推理型任务 → DSPy 效果极好
  ✗ IntentConvert:    输入太长（vision JSON）、格式要求严格 → 手写规则更可靠
  ○ Prompt 优化:      让 DSPy 自动测试不同 prompt → 找到最优后固化到代码

最佳实践：
  1. IntentConvert: 保留手写 _vision_params_to_spec，但用 DSPy 优化其 prompt
  2. ConnectionInfer: 完全用 DSPy 替代 rule-based fasteners.py
  3. 每次运行后自动对比 zero-shot vs few-shot，选择高分方案
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from typing import Dict, List

REPO_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "freecad-assembler"))

import dspy

# ═══════════════════════════════════════════════════════
#  1. LLM 配置
# ═══════════════════════════════════════════════════════

lm = dspy.LM(
    "openai/doubao-seed-2-0-pro-260215",
    api_key=os.environ.get("DOUBAO_API_KEY", ""),
    api_base="https://ark.cn-beijing.volces.com/api/v3",
    max_tokens=4096,
    temperature=0.1,  # 低温度确保确定性输出
)
dspy.configure(lm=lm)


# ═══════════════════════════════════════════════════════
#  2. ConnectionInfer（DSPy 核心模块）
# ═══════════════════════════════════════════════════════

class ConnectionInfer(dspy.Signature):
    """根据 AssemblyIntent 中的零件和关系，推断物理连接件。

    输出格式：{"connections": [{"source": "...", "target": "...", "rel_type": "...",
    "fastener_type": "bolt|tube|cable|none", "count": int, "spec": "M8x25|Φ6|...", "reason": "..."}]}

    核心规则：
    - supported_by(column→base) → bolt 4×M8x25（重型承重）
    - supported_by(other→base) → bolt 2-4×M6x20
    - mounted_on → bolt 2×M6x20
    - guides/drives → none（滑动/驱动配合，不生成螺栓）
    - connected_to(valve,pump) → tube 1×Φ6（仅当零件距离<300mm）
    - 传感器→控制器 → cable 1×（仅当距离<400mm）
    - 硬约束：总连接件数 ≤ 20，超过时舍弃次要连接
    """
    intent_json = dspy.InputField()
    connections_json = dspy.OutputField()


# Few-shot 示例（让模型学习正确的决策模式）
FEWSHOT_CONNECTION = """Example:
Intent: {"parts": [{"name":"base","type":"base_plate"},{"name":"col","type":"column"},{"name":"grip","type":"gripper"},{"name":"rail","type":"guide_rail"},{"name":"cyl","type":"cylinder"}],"relations":[{"type":"supported_by","source":"col","target":"base"},{"type":"mounted_on","source":"grip","target":"col"},{"type":"guides","source":"rail","target":"cyl"}]}
Output: {"connections": [
  {"source":"col","target":"base","rel_type":"supported_by","fastener_type":"bolt","count":4,"spec":"M8x25","reason":"column is heavy load-bearing"},
  {"source":"grip","target":"col","rel_type":"mounted_on","fastener_type":"bolt","count":2,"spec":"M6x20","reason":"gripper mounted on slide"},
  {"source":"rail","target":"cyl","rel_type":"guides","fastener_type":"none","count":0,"spec":null,"reason":"sliding guide fit, no fasteners needed"}
]}"""


def _extract_json(text: str) -> str:
    m = re.search(r'```json\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r'```\s*(.*?)\s*```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    m = re.search(r'\{.*\}', text, re.DOTALL)
    if m:
        return m.group(0).strip()
    return text.strip()


def run_connection_infer(intent_dict: dict, use_fewshot: bool = True) -> dict:
    """运行 DSPy ConnectionInfer，返回解析后的连接件决策。"""
    predictor = dspy.Predict(ConnectionInfer)
    intent_str = json.dumps(intent_dict, ensure_ascii=False)

    if use_fewshot:
        prompt = f"{FEWSHOT_CONNECTION}\n\nNow infer connections for this intent:\n{intent_str}"
    else:
        prompt = intent_str

    result = predictor(intent_json=prompt)
    raw = _extract_json(result.connections_json)

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"connections": [], "error": "Failed to parse model output", "raw": raw[:500]}


# ═══════════════════════════════════════════════════════
#  3. 评估与选择逻辑
# ═══════════════════════════════════════════════════════

def evaluate_connections(conn_data: dict) -> dict:
    """评估连接件决策质量。"""
    conns = conn_data.get("connections", [])
    total = sum(c.get("count", 0) for c in conns)
    score = 0.0

    if total <= 20:
        score += 0.4
    elif total <= 30:
        score += 0.2

    wrong = [c for c in conns if c.get("fastener_type") == "bolt" and c.get("rel_type") in ("guides", "drives")]
    if not wrong:
        score += 0.3

    valid = all(c.get("fastener_type") in ("bolt", "tube", "cable", "none") for c in conns)
    if valid:
        score += 0.3

    return {
        "score": round(min(score, 1.0), 2),
        "total_fasteners": total,
        "connection_count": len(conns),
        "wrong_bolts_on_slides": len(wrong),
    }


def choose_best_connections(intent_dict: dict) -> dict:
    """对比 zero-shot vs few-shot，返回最优连接件决策。"""
    # Zero-shot
    r0 = run_connection_infer(intent_dict, use_fewshot=False)
    e0 = evaluate_connections(r0)

    # Few-shot
    r1 = run_connection_infer(intent_dict, use_fewshot=True)
    e1 = evaluate_connections(r1)

    best = r1 if e1["score"] >= e0["score"] else r0
    best_eval = e1 if e1["score"] >= e0["score"] else e0
    best_name = "few-shot" if e1["score"] >= e0["score"] else "zero-shot"

    return {
        "connections": best.get("connections", []),
        "eval": best_eval,
        "mode": best_name,
        "zero_shot_eval": e0,
        "few_shot_eval": e1,
    }


# ═══════════════════════════════════════════════════════
#  4. 与 fasteners.py 的桥接（替换 rule-based）
# ═══════════════════════════════════════════════════════

def dspy_generate_fasteners(intent_dict: dict) -> List[dict]:
    """用 DSPy 替代 framework/fasteners.py 的 rule-based 生成。"""
    result = choose_best_connections(intent_dict)
    connections = result.get("connections", [])

    # 转换为 FastenerSpec 格式（供 assembly_builder 使用）
    fasteners = []
    for c in connections:
        if c.get("fastener_type") == "none" or c.get("count", 0) == 0:
            continue

        # 映射到 STEP 路径
        spec = c.get("spec", "M6x20")
        if "M8" in spec:
            part_path = "../automation_parts/bolt_m8x25.step"
        elif "M6" in spec:
            part_path = "../automation_parts/bolt_m6x20.step"
        elif "Φ6" in spec or "tube" in c.get("fastener_type", ""):
            part_path = "../automation_parts/air_tube_6mm.step"
        elif "cable" in c.get("fastener_type", ""):
            part_path = "../automation_parts/sensor_cable.step"
        else:
            continue

        # 简化的 transform（实际应从零件位置计算）
        fasteners.append({
            "name": f"conn_{c['source']}_{c['target']}",
            "type": c["fastener_type"],
            "part_path": part_path,
            "count": c["count"],
            "spec": spec,
            "reason": c.get("reason", ""),
        })

    return fasteners


# ═══════════════════════════════════════════════════════
#  5. 主入口 / 测试
# ═══════════════════════════════════════════════════════

def main():
    print("=" * 60)
    print("DSPy ConnectionInfer — Production Integration")
    print("=" * 60)

    # 读取当前 checkpoint intent
    intent_path = Path(__file__).parent / "checkpoint" / "image_assembly_intent.json"
    if intent_path.exists():
        with open(intent_path) as f:
            intent = json.load(f)
    else:
        # fallback test data
        intent = {
            "parts": [
                {"name": "base_plate", "type": "base_plate", "params": {"width": 800, "depth": 500, "thickness": 15, "x": 0, "y": 0}},
                {"name": "transfer_column", "type": "column", "params": {"width": 80, "depth": 60, "height": 380, "x": 0, "y": -50}},
                {"name": "gripper", "type": "gripper", "params": {"body_width": 50, "body_depth": 30, "body_height": 45, "x": 0, "y": -50}},
                {"name": "push_slide", "type": "slider", "params": {"width": 180, "depth": 60, "height": 12, "x": -280, "y": 80}},
                {"name": "vib_bowl", "type": "vibration_bowl", "params": {"diameter": 150, "height": 90, "x": 260, "y": -120}},
                {"name": "guide_cyl", "type": "cylinder", "params": {"body_dia": 20, "body_length": 80, "x": -350, "y": 80}},
                {"name": "guide_rail", "type": "guide_rail", "params": {"width": 12, "depth": 15, "height": 200, "x": -280, "y": 80}},
            ],
            "relations": [
                {"type": "supported_by", "source": "transfer_column", "target": "base_plate"},
                {"type": "mounted_on", "source": "gripper", "target": "transfer_column"},
                {"type": "supported_by", "source": "push_slide", "target": "base_plate"},
                {"type": "supported_by", "source": "vib_bowl", "target": "base_plate"},
                {"type": "supported_by", "source": "guide_cyl", "target": "base_plate"},
                {"type": "guides", "source": "guide_rail", "target": "guide_cyl"},
            ]
        }

    print(f"\nInput intent: {len(intent['parts'])} parts, {len(intent['relations'])} relations")

    # 运行对比
    print("\n[Zero-shot]")
    r0 = run_connection_infer(intent, use_fewshot=False)
    e0 = evaluate_connections(r0)
    print(f"  Score: {e0['score']}, Fasteners: {e0['total_fasteners']}, Connections: {e0['connection_count']}")

    print("\n[Few-shot]")
    r1 = run_connection_infer(intent, use_fewshot=True)
    e1 = evaluate_connections(r1)
    print(f"  Score: {e1['score']}, Fasteners: {e1['total_fasteners']}, Connections: {e1['connection_count']}")

    # 选择最优
    best = choose_best_connections(intent)
    print(f"\n✓ Winner: {best['mode']} (score={best['eval']['score']})")
    print(f"  Total fasteners: {best['eval']['total_fasteners']}")

    print("\nConnection details:")
    for c in best["connections"]:
        icon = "🔩" if c.get("fastener_type") == "bolt" else "📎" if c.get("fastener_type") == "tube" else "🔌" if c.get("fastener_type") == "cable" else "⛔"
        print(f"  {icon} {c['rel_type']:12s} {c['source']:20s} -> {c['target']:15s} = {c['fastener_type']}×{c['count']} ({c.get('spec', '-')})")

    # 保存
    out_dir = Path(__file__).parent / "checkpoint"
    out_dir.mkdir(exist_ok=True)
    out_path = out_dir / "dspy_optimized_connections.json"
    with open(out_path, "w") as f:
        json.dump(best, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to: {out_path}")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
