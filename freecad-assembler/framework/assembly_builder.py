"""
Assembly Builder — 从 AssemblyIntent + 连接件 自动生成 CAD assembly 脚本。

输入：
  • AssemblyIntent（零件 + 关系）
  • part_positions: {name: (x, y, z)} — 求解后的全局坐标
  • fasteners: List[FastenerSpec] — 自动生成的连接件
  • part_step_map: {part_name: step_path} — 零件到 STEP 文件的映射

输出：
  • Python assembly 脚本（可直接运行 gen_step_assembly）
  • 脚本中包含所有 instance 的 transform 和层级关系
"""
from __future__ import annotations

import math
from typing import Dict, List, Tuple
from pathlib import Path

from .ontology import AssemblyIntent, Relation, RelationType
from .fasteners import FastenerSpec, generate_fasteners


# 零件类型 → 默认 STEP 路径映射
DEFAULT_PART_STEP_MAP = {
    "base_plate": "../automation_parts/small_base_plate.step",
    "column": "../automation_parts/transfer_column.step",
    "cylinder": "../automation_parts/pneumatic_cylinder.step",
    "large_cylinder": "../automation_parts/large_cylinder.step",
    "guide_rail": "../automation_parts/linear_guide.step",
    "gripper": "../automation_parts/gripper.step",
    "vibration_bowl": "../automation_parts/vibrating_bowl.step",
    "hopper": "../automation_parts/vibrating_bowl.step",
    "linear_track": "../automation_parts/work_platform.step",
    "push_slide": "../automation_parts/push_slide.step",
    "sensor": "../automation_parts/proximity_sensor.step",
    "photo_sensor": "../automation_parts/photo_sensor.step",
    "air_pump": "../automation_parts/air_pump.step",
    "solenoid_valve": "../automation_parts/solenoid_valve.step",
    "plc_module": "../automation_parts/plc_module.step",
    "cable_tray": "../automation_parts/cable_tray_channel.step",
    "din_rail": "../automation_parts/din_rail.step",
    "terminal_block": "../automation_parts/terminal_block.step",
}


def _t(tx: float = 0.0, ty: float = 0.0, tz: float = 0.0,
       rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> list:
    """构造 4x4 row-major 变换矩阵。角度为度。"""
    cx, cy, cz = math.cos(math.radians(rx)), math.cos(math.radians(ry)), math.cos(math.radians(rz))
    sx, sy, sz = math.sin(math.radians(rx)), math.sin(math.radians(ry)), math.sin(math.radians(rz))
    return [
        cy * cz,  sx * sy * cz - cx * sz,  cx * sy * cz + sx * sz,  tx,
        cy * sz,  sx * sy * sz + cx * cz,  cx * sy * sz - sx * cz,  ty,
        -sy,      sx * cy,                 cx * cy,                 tz,
        0.0,      0.0,                     0.0,                     1.0,
    ]


def _position_from_params(part) -> Tuple[float, float, float]:
    """从 part params 中提取 (x, y, z)。"""
    params = part.params
    x = float(params.get("x", 0))
    y = float(params.get("y", 0))
    z = float(params.get("z", 0))
    return x, y, z


def _z_height(part) -> float:
    """估算零件在 Z 方向的高度（用于堆叠计算）。"""
    ptype = part.part_type
    params = part.params
    if ptype.value == "base_plate":
        return float(params.get("thickness", 15))
    if ptype.value == "column":
        return float(params.get("height", 250))
    if ptype.value == "cylinder":
        return float(params.get("body_length", 120))
    if ptype.value == "guide_rail":
        return float(params.get("height", 120))
    if ptype.value == "gripper":
        return float(params.get("body_height", 20))
    if ptype.value == "vibration_bowl":
        return float(params.get("height", 80))
    if ptype.value == "hopper":
        return float(params.get("height", 100))
    if ptype.value == "linear_track":
        return float(params.get("length", 200))
    return 50.0


def compute_part_positions(intent: AssemblyIntent) -> Dict[str, Tuple[float, float, float]]:
    """
    根据 intent 中的零件参数和关系，计算每个零件的全局 (x, y, z)。
    
    策略：
      1. base_plate 在 Z=0（底面）
      2. 其他零件的 (x, y) 来自 params
      3. z 根据 SUPPORTED_BY / MOUNTED_ON 关系堆叠计算
    """
    positions = {}
    base_plate = None
    base_z = 0.0

    # 找底板
    for p in intent.parts:
        if p.part_type.value == "base_plate":
            base_plate = p
            base_z = float(p.params.get("thickness", 15))
            positions[p.name] = (0.0, 0.0, 0.0)
            break

    # 初始 z：非底板零件放在底板上方
    for p in intent.parts:
        if p.name in positions:
            continue
        x, y, _ = _position_from_params(p)
        z = base_z
        positions[p.name] = (x, y, z)

    # 根据关系堆叠 z（BFS）
    for _ in range(5):
        for rel in intent.relations:
            if rel.rel_type in (RelationType.SUPPORTED_BY, RelationType.MOUNTED_ON):
                src = rel.source
                tgt = rel.target
                if tgt in positions and src in positions:
                    tx, ty, tz = positions[tgt]
                    src_h = _z_height(next(p for p in intent.parts if p.name == src))
                    tgt_h = _z_height(next(p for p in intent.parts if p.name == tgt))
                    # source 放在 target 上方：source 底面贴合 target 顶面
                    new_z = tz + tgt_h
                    sx, sy, _ = positions[src]
                    positions[src] = (sx, sy, new_z)

    return positions


def build_assembly_script(
    intent: AssemblyIntent,
    output_path: Path,
    part_step_map: Dict[str, str] | None = None,
) -> Path:
    """
    自动生成 assembly Python 脚本并写入文件。

    Args:
        intent: 装配意图
        output_path: 输出脚本路径（如 models/assemblies/xxx.py）
        part_step_map: 零件名到 STEP 路径的映射（可选，覆盖默认映射）

    Returns:
        写入的脚本路径
    """
    part_step_map = part_step_map or {}

    # 1. 计算零件位置
    positions = compute_part_positions(intent)

    # 2. 生成连接件
    fasteners = generate_fasteners(intent, positions)
    fastener_counts = {}
    for f in fasteners:
        fastener_counts[f.type] = fastener_counts.get(f.type, 0) + 1

    # 3. 构建 instance 列表
    instances = []

    # 零件 instances
    for part in intent.parts:
        name = part.name
        ptype = part.part_type.value
        x, y, z = positions.get(name, (0, 0, 0))

        # 确定 STEP 路径
        step_path = part_step_map.get(name)
        if step_path is None:
            # 按类型匹配默认路径
            step_path = DEFAULT_PART_STEP_MAP.get(ptype)
        if step_path is None:
            continue  # 跳过没有 STEP 的零件

        instances.append({
            "name": name.replace("-", "_").replace(" ", "_"),
            "path": step_path,
            "transform": _t(x, y, z),
        })

    # 连接件 instances
    for f in fasteners:
        instances.append({
            "name": f.name,
            "path": f.part_path,
            "transform": f.transform,
        })

    # 4. 生成 Python 脚本内容
    lines = [
        '#!/usr/bin/env python3',
        '"""Auto-generated assembly from AssemblyIntent."""',
        'from __future__ import annotations',
        '',
        'import math',
        '',
        'def _t(tx: float = 0.0, ty: float = 0.0, tz: float = 0.0,',
        '       rx: float = 0.0, ry: float = 0.0, rz: float = 0.0) -> list[float]:',
        '    cx, cy, cz = math.cos(math.radians(rx)), math.cos(math.radians(ry)), math.cos(math.radians(rz))',
        '    sx, sy, sz = math.sin(math.radians(rx)), math.sin(math.radians(ry)), math.sin(math.radians(rz))',
        '    return [',
        '        cy * cz,  sx * sy * cz - cx * sz,  cx * sy * cz + sx * sz,  tx,',
        '        cy * sz,  sx * sy * sz + cx * cz,  cx * sy * sz - sx * cz,  ty,',
        '        -sy,      sx * cy,                 cx * cy,                 tz,',
        '        0.0,      0.0,                     0.0,                     1.0,',
        '    ]',
        '',
        'def gen_step() -> dict[str, object]:',
        '    return {',
        f'        "step_output": "{output_path.stem}.step",',
        '        "instances": [',
    ]

    for i, inst in enumerate(instances):
        t = inst["transform"]
        t_str = ", ".join(f"{v:.1f}" if isinstance(v, float) else str(v) for v in t)
        comma = "," if i < len(instances) - 1 else ""
        lines.append(f'            {{')
        lines.append(f'                "name": "{inst["name"]}",')
        lines.append(f'                "path": "{inst["path"]}",')
        lines.append(f'                "transform": [{t_str}],')
        lines.append(f'            }}{comma}')

    lines.extend([
        '        ],',
        '    }',
        '',
    ])

    # 添加生成信息注释
    lines.insert(3, f'# Generated from AssemblyIntent: {len(intent.parts)} parts, {len(intent.relations)} relations')
    lines.insert(4, f'# Auto-generated fasteners: {dict(fastener_counts)}')
    lines.insert(5, '')

    script_content = "\n".join(lines)
    output_path.write_text(script_content, encoding="utf-8")

    print(f"[AssemblyBuilder] Wrote {len(intent.parts)} parts + {len(fasteners)} fasteners to {output_path}")
    print(f"[AssemblyBuilder] Fastener counts: {fastener_counts}")

    return output_path
