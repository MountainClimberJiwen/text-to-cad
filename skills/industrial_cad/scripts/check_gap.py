#!/usr/bin/env python3
"""
check_gap.py — 装配一致性验证脚本

对比三层数据：
  1. 设计意图 (constraints.json)
  2. 实际输出 (placements.json + STEP)
  3. 目标参考 (assembly.py 中的手动 transform)

输出结构化 gap report，指出每条约束的满足度和缺失项。
"""

from __future__ import annotations

import argparse
import ast
import json
import math
import sys
from pathlib import Path
from typing import Any


def _load_assembly_py_targets(assembly_py: Path) -> dict[str, dict[str, Any]]:
    """从 assembly.py 中提取目标 transforms。"""
    code = assembly_py.read_text(encoding="utf-8")
    
    # Find the gen_step() function body
    tree = ast.parse(code)
    
    targets = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Dict):
            # Look for dicts with "name" and "transform" keys
            name = None
            transform = None
            for k, v in zip(node.keys, node.values):
                if isinstance(k, ast.Constant) and k.value == "name":
                    if isinstance(v, ast.Constant):
                        name = v.value
                if isinstance(k, ast.Constant) and k.value == "transform":
                    transform = _eval_transform_call(v)
            if name and transform:
                targets[name] = transform
    
    return targets


def _eval_ast_number(node: ast.AST) -> float | None:
    """从 AST 节点中提取数值（支持负数）。"""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.Num):  # Python < 3.8
        return float(node.n)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        val = _eval_ast_number(node.operand)
        return -val if val is not None else None
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _eval_ast_number(node.operand)
    return None


def _eval_transform_call(node: ast.AST) -> dict[str, Any] | None:
    """评估 _t(tx,ty,tz,rx,ry,rz) 调用。"""
    if not isinstance(node, ast.Call):
        return None
    
    # Extract arguments
    args = {}
    arg_names = ["tx", "ty", "tz", "rx", "ry", "rz"]
    for i, arg in enumerate(node.args):
        if i < len(arg_names):
            val = _eval_ast_number(arg)
            if val is not None:
                args[arg_names[i]] = val
    
    # Handle keyword args
    for kw in node.keywords:
        if kw.arg in arg_names:
            val = _eval_ast_number(kw.value)
            if val is not None:
                args[kw.arg] = val
    
    return {
        "x": args.get("tx", 0.0),
        "y": args.get("ty", 0.0),
        "z": args.get("tz", 0.0),
        "rx": args.get("rx", 0.0),
        "ry": args.get("ry", 0.0),
        "rz": args.get("rz", 0.0),
    }


def _compute_expected_from_constraints(constraints_data: dict) -> dict[str, dict[str, Any]]:
    """从 constraints.json 计算期望 Placement（简化版本）。
    
    规则：
    - Fix → (0,0,0)
    - PlaneCoincident(bottom, top) + Distance → 根据零件 bbox 和约束计算
    - CenterOfMass → 对齐 bbox 中心
    """
    import build123d
    from OCP.BRepBndLib import BRepBndLib
    from OCP.Bnd import Bnd_Box
    
    repo_root = Path.cwd()
    
    # Load all parts
    parts = {}
    for pc in constraints_data.get("parts", []):
        pid = pc["id"]
        step_path = repo_root / pc["file"]
        shape = build123d.import_step(step_path)
        bb = shape.bounding_box()
        parts[pid] = {
            "shape": shape,
            "min": (bb.min.X, bb.min.Y, bb.min.Z),
            "max": (bb.max.X, bb.max.Y, bb.max.Z),
            "center": ((bb.min.X + bb.max.X)/2, (bb.min.Y + bb.max.Y)/2, (bb.min.Z + bb.max.Z)/2),
        }
    
    # Compute expected placements
    expected = {pid: {"x": 0.0, "y": 0.0, "z": 0.0, "rx": 0.0, "ry": 0.0, "rz": 0.0} for pid in parts}
    
    constraints = constraints_data.get("constraints", [])
    
    # Sort: Fix first, then PlaneCoincident, then CenterOfMass, then Distance
    def priority(c):
        return {"Fix": 0, "PlaneCoincident": 1, "CenterOfMass": 2, "Distance": 3}.get(c["type"], 99)
    
    for c in sorted(constraints, key=priority):
        ctype = c["type"]
        
        if ctype == "Fix":
            pid = c["part"]
            expected[pid] = {"x": 0, "y": 0, "z": 0, "rx": 0, "ry": 0, "rz": 0}
        
        elif ctype == "PlaneCoincident":
            pa = c["part_a"]
            pb = c["part_b"]
            face_a = c.get("face_a", "bottom")
            face_b = c.get("face_b", "top")
            
            # Simple: if both faces are horizontal, offset Z so that face_a.Z aligns with face_b.Z
            # For now, assume all parts have bottom at min.Z and top at max.Z
            if face_a == "bottom" and face_b == "top":
                z_offset = parts[pb]["max"][2] - parts[pa]["min"][2]
                expected[pa]["z"] = z_offset
            elif face_a == "top" and face_b == "bottom":
                z_offset = parts[pb]["min"][2] - parts[pa]["max"][2]
                expected[pa]["z"] = z_offset
        
        elif ctype == "Distance":
            pa = c["part_a"]
            axis = c.get("axis", "z")
            value = float(c.get("value", 0))
            expected[pa][axis] = value
        
        elif ctype == "CenterOfMass":
            pa = c["part_a"]
            pb = c["part_b"]
            axis = c.get("axis", "x")
            # Align bbox centers
            offset = parts[pb]["center"][{"x": 0, "y": 1, "z": 2}[axis]] - parts[pa]["center"][{"x": 0, "y": 1, "z": 2}[axis]]
            expected[pa][axis] = offset
        
        elif ctype == "Rotation":
            pa = c["part"]
            axis = c.get("axis", "z")
            value = float(c.get("value", 0))
            expected[pa][{"x": "rx", "y": "ry", "z": "rz"}[axis]] = value
    
    return expected


def _rotation_matrix(rx: float, ry: float, rz: float) -> list[list[float]]:
    """XYZ Euler rotation matrix (degrees)."""
    cx, cy, cz = math.cos(math.radians(rx)), math.cos(math.radians(ry)), math.cos(math.radians(rz))
    sx, sy, sz = math.sin(math.radians(rx)), math.sin(math.radians(ry)), math.sin(math.radians(rz))
    return [
        [cy*cz, sx*sy*cz - cx*sz, cx*sy*cz + sx*sz],
        [cy*sz, sx*sy*sz + cx*cz, cx*sy*sz - sx*cz],
        [-sy,   sx*cy,            cx*cy],
    ]


def _compare_transforms(
    actual: dict[str, Any],
    expected: dict[str, Any],
    target: dict[str, Any] | None,
    part_id: str,
    tolerance: float = 0.5,
) -> list[dict[str, Any]]:
    """对比 actual vs expected vs target，返回 gap items。"""
    gaps = []
    
    axes = [("x", "X"), ("y", "Y"), ("z", "Z")]
    rot_axes = [("rx", "RX"), ("ry", "RY"), ("rz", "RZ")]
    
    for key, label in axes:
        a = actual.get(key, 0.0)
        e = expected.get(key, 0.0)
        t = target.get(key, 0.0) if target else None
        
        # Compare against expected (from constraints)
        err = abs(a - e)
        if err > tolerance:
            gaps.append({
                "part": part_id,
                "axis": label,
                "expected_from_constraints": round(e, 2),
                "actual": round(a, 2),
                "error_mm": round(err, 2),
                "target_from_assembly_py": round(t, 2) if t is not None else None,
                "severity": "ERROR" if err > 5.0 else "WARNING",
                "reason": f"Constraint-derived {label} not satisfied",
            })
        
        # Also flag if target differs from expected (constraint missing)
        if t is not None and abs(e - t) > tolerance:
            gaps.append({
                "part": part_id,
                "axis": label,
                "expected_from_constraints": round(e, 2),
                "actual": round(a, 2),
                "target_from_assembly_py": round(t, 2),
                "error_mm": round(abs(a - t), 2),
                "severity": "MISSING_CONSTRAINT",
                "reason": f"assembly.py target {label}={t} but no matching constraint (expected from constraints: {e})",
            })
    
    for key, label in rot_axes:
        a = actual.get(key, 0.0)
        e = expected.get(key, 0.0)
        t = target.get(key, 0.0) if target else None
        
        err = abs(a - e)
        # Handle 360° wrap
        if err > 180:
            err = 360 - err
        
        if err > tolerance:
            gaps.append({
                "part": part_id,
                "axis": label,
                "expected_from_constraints": round(e, 2),
                "actual": round(a, 2),
                "error_deg": round(err, 2),
                "target_from_assembly_py": round(t, 2) if t is not None else None,
                "severity": "ERROR" if err > 5.0 else "WARNING",
                "reason": f"Constraint-derived rotation {label} not satisfied",
            })
        
        if t is not None:
            t_err = abs(e - t)
            if t_err > 180:
                t_err = 360 - t_err
            if t_err > tolerance:
                gaps.append({
                    "part": part_id,
                    "axis": label,
                    "expected_from_constraints": round(e, 2),
                    "actual": round(a, 2),
                    "target_from_assembly_py": round(t, 2),
                    "error_deg": round(t_err, 2),
                    "severity": "MISSING_CONSTRAINT",
                    "reason": f"assembly.py target rotation {label}={t}deg but no matching constraint",
                })
    
    return gaps


def run_check(
    constraints_path: Path,
    placements_path: Path,
    assembly_py_path: Path | None,
    tolerance: float = 0.5,
) -> dict[str, Any]:
    """运行完整的一致性检查。"""
    
    # Load data
    constraints_data = json.loads(constraints_path.read_text(encoding="utf-8"))
    placements_data = json.loads(placements_path.read_text(encoding="utf-8"))
    
    target_transforms = {}
    if assembly_py_path and assembly_py_path.exists():
        target_transforms = _load_assembly_py_targets(assembly_py_path)
    
    # Compute expected from constraints
    expected = _compute_expected_from_constraints(constraints_data)
    
    # Convert placements.json to simple dict
    actual = {}
    for pid, p in placements_data.items():
        base = p["base"]
        # Convert rotation axis+angle to Euler (simplified)
        axis = p["rotation_axis"]
        angle = p["rotation_angle"]
        
        # If rotation is around Z only
        if abs(axis[2]) > 0.99:
            rz = angle if axis[2] > 0 else -angle
            actual[pid] = {"x": base[0], "y": base[1], "z": base[2], "rx": 0, "ry": 0, "rz": rz}
        elif abs(axis[0]) > 0.99:
            rx = angle if axis[0] > 0 else -angle
            actual[pid] = {"x": base[0], "y": base[1], "z": base[2], "rx": rx, "ry": 0, "rz": 0}
        elif abs(axis[1]) > 0.99:
            ry = angle if axis[1] > 0 else -angle
            actual[pid] = {"x": base[0], "y": base[1], "z": base[2], "rx": 0, "ry": ry, "rz": 0}
        else:
            # General case - approximate
            actual[pid] = {"x": base[0], "y": base[1], "z": base[2], "rx": 0, "ry": 0, "rz": 0}
    
    # Compare
    all_gaps = []
    for pid in expected:
        a = actual.get(pid, {})
        e = expected[pid]
        t = target_transforms.get(pid)
        gaps = _compare_transforms(a, e, t, pid, tolerance)
        all_gaps.extend(gaps)
    
    # Summary
    errors = [g for g in all_gaps if g["severity"] == "ERROR"]
    warnings = [g for g in all_gaps if g["severity"] == "WARNING"]
    missing = [g for g in all_gaps if g["severity"] == "MISSING_CONSTRAINT"]
    
    return {
        "summary": {
            "parts_checked": len(expected),
            "errors": len(errors),
            "warnings": len(warnings),
            "missing_constraints": len(missing),
            "total_gaps": len(all_gaps),
        },
        "errors": errors,
        "warnings": warnings,
        "missing_constraints": missing,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check assembly constraint satisfaction gaps.")
    parser.add_argument("--constraints", type=Path, required=True, help=".constraints.json file")
    parser.add_argument("--placements", type=Path, required=True, help=".placements.json file")
    parser.add_argument("--target-assembly", type=Path, default=None, help="Target assembly.py for reference")
    parser.add_argument("--tolerance", type=float, default=0.5, help="Position tolerance in mm")
    parser.add_argument("--json-out", type=Path, default=None, help="Write JSON report")
    args = parser.parse_args(argv)
    
    report = run_check(args.constraints, args.placements, args.target_assembly, args.tolerance)
    
    # Print report
    summary = report["summary"]
    print("=" * 60)
    print("  Assembly Constraint Satisfaction Gap Report")
    print("=" * 60)
    print(f"  Parts checked:          {summary['parts_checked']}")
    print(f"  Errors:                 {summary['errors']}")
    print(f"  Warnings:               {summary['warnings']}")
    print(f"  Missing constraints:    {summary['missing_constraints']}")
    print()
    
    if report["errors"]:
        print(f"  ERRORS ({len(report['errors'])}):")
        for g in report["errors"]:
            print(f"    🔴 {g['part']}.{g['axis']}: expected={g.get('expected_from_constraints')}, actual={g['actual']}, err={g.get('error_mm', g.get('error_deg'))}")
        print()
    
    if report["warnings"]:
        print(f"  WARNINGS ({len(report['warnings'])}):")
        for g in report["warnings"]:
            print(f"    🟡 {g['part']}.{g['axis']}: expected={g.get('expected_from_constraints')}, actual={g['actual']}, err={g.get('error_mm', g.get('error_deg'))}")
        print()
    
    if report["missing_constraints"]:
        print(f"  MISSING CONSTRAINTS ({len(report['missing_constraints'])}):")
        for g in report["missing_constraints"]:
            print(f"    ⬜ {g['part']}.{g['axis']}: target={g.get('target_from_assembly_py')}, constraint_derived={g.get('expected_from_constraints')}")
            print(f"       → {g['reason']}")
        print()
    
    if not any([report["errors"], report["warnings"], report["missing_constraints"]]):
        print("  ✅ All constraints satisfied within tolerance!")
    
    print("=" * 60)
    
    if args.json_out:
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(f"Report saved to: {args.json_out}")
    
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
