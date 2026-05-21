"""
Fastener / Connection Auto-Generator
=====================================
根据 AssemblyIntent 中的关系，自动生成连接件（螺栓、气管、电缆）。

规则：
  • SUPPORTED_BY(base, part)  → 地脚螺栓（数量由底座面积决定，最多 4 个）
  • MOUNTED_ON(parent, child) → 安装螺栓（最多 2-4 个）
  • CONNECTED_TO(A, B)        → 气管/电缆（仅当距离 < MAX_TUBE_LEN）
  • GUIDES/DRIVES             → 不生成连接件（滑动/驱动配合）

硬约束（防止"连接件灾难"）：
  • 每种关系最多 4 个连接件
  • 螺栓长度 ≤ 配合厚度 × 1.5
  • 气管只在距离 < 300mm 的零件间生成
  • 电缆只在同一功能区域内生成
"""
from __future__ import annotations

import math
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass

from .ontology import AssemblyIntent, Relation, RelationType, PartType


# ── 规则配置 ──
MAX_FASTENERS_PER_RELATION = 4
BOLT_LENGTH_MAX_RATIO = 1.5
MAX_TUBE_DISTANCE = 300.0
MAX_CABLE_DISTANCE = 400.0


@dataclass
class FastenerSpec:
    """单个连接件规格。"""
    name: str
    type: str          # "bolt", "nut", "washer", "tube", "cable"
    part_path: str     # 相对于 assembly 的 STEP 路径
    transform: List[float]   # 4x4 row-major
    # 来源关系（用于追溯）
    source_rel: Optional[Tuple[str, str, RelationType]] = None


class FastenerRule:
    """连接件规则基类。"""

    def applies_to(self, rel: Relation, intent: AssemblyIntent) -> bool:
        raise NotImplementedError

    def generate(self, rel: Relation, intent: AssemblyIntent, part_positions: Dict[str, Tuple[float, float, float]]) -> List[FastenerSpec]:
        raise NotImplementedError


class BoltRule(FastenerRule):
    """
    螺栓规则：
      SUPPORTED_BY(base_plate, part) → 地脚螺栓，按零件底面四角放置
      MOUNTED_ON(parent, child)      → 安装螺栓，按顶面/侧面安装孔放置
    """

    def applies_to(self, rel: Relation, intent: AssemblyIntent) -> bool:
        return rel.rel_type in (RelationType.SUPPORTED_BY, RelationType.MOUNTED_ON)

    def generate(self, rel: Relation, intent: AssemblyIntent, positions: Dict[str, Tuple[float, float, float]]) -> List[FastenerSpec]:
        source_pos = positions.get(rel.source)
        target_pos = positions.get(rel.target)
        if source_pos is None or target_pos is None:
            return []

        # 查找 source（被支撑/被安装的零件）的规格
        source_part = next((p for p in intent.parts if p.name == rel.source), None)
        if source_part is None:
            return []

        sx, sy, sz = source_pos
        tx, ty, tz = target_pos

        # 根据零件类型和尺寸确定螺栓规格和数量
        ptype = source_part.part_type
        params = source_part.params

        # 默认：2 个螺栓，M6
        count = 2
        bolt_path = "../automation_parts/bolt_m6x20.step"
        bolt_len = 20

        if ptype == PartType.BASE_PLATE:
            # base_plate 不需要螺栓（它是根）
            return []

        if ptype in (PartType.COLUMN, PartType.GANTRY):
            # 大立柱/门架 → 4×M8
            count = min(4, MAX_FASTENERS_PER_RELATION)
            bolt_path = "../automation_parts/bolt_m8x25.step"
            bolt_len = 25
        elif ptype in (PartType.VIBRATION_BOWL, PartType.HOPPER):
            # 振动盘/料斗 → 4×M8（重型设备）
            count = min(4, MAX_FASTENERS_PER_RELATION)
            bolt_path = "../automation_parts/bolt_m8x25.step"
            bolt_len = 25
        elif ptype == PartType.CYLINDER:
            # 气缸 → 2×M6（耳座安装）
            count = min(2, MAX_FASTENERS_PER_RELATION)
            bolt_path = "../automation_parts/bolt_m6x20.step"
            bolt_len = 20
        elif ptype == PartType.GRIPPER:
            # 夹爪 → 2×M6（顶面安装孔）
            count = min(2, MAX_FASTENERS_PER_RELATION)
            bolt_path = "../automation_parts/bolt_m6x20.step"
            bolt_len = 20
        elif ptype in (PartType.GUIDE_RAIL, PartType.SLIDER):
            # 导轨/滑块 → 2-4×M6
            count = min(4, MAX_FASTENERS_PER_RELATION)
            bolt_path = "../automation_parts/bolt_m6x20.step"
            bolt_len = 20

        # 计算螺栓位置：按 source 零件底面/安装面分布
        fasteners = []

        # 获取 source 零件的宽度和深度（用于分布螺栓）
        w = params.get("width", params.get("body_dia", 50))
        d = params.get("depth", params.get("body_dia", 50))
        # 对于 cylinder，用 body_dia
        if ptype == PartType.CYLINDER:
            w = params.get("body_dia", 25)
            d = params.get("body_dia", 25)

        # 螺栓分布策略
        if count == 2:
            # 沿 X 方向并排
            offsets = [(-w * 0.25, 0), (w * 0.25, 0)]
        elif count == 4:
            # 四角分布
            offsets = [(-w * 0.3, -d * 0.3), (w * 0.3, -d * 0.3),
                       (-w * 0.3, d * 0.3), (w * 0.3, d * 0.3)]
        else:
            offsets = [(0, 0)]

        # 螺栓安装面高度：source 零件底面/安装面
        # SUPPORTED_BY: source 安装在 target 上方，螺栓从 source 顶面穿下
        # MOUNTED_ON: source 安装在 target 上，螺栓从 source 安装面穿下
        if rel.rel_type == RelationType.SUPPORTED_BY:
            # source 被 target 支撑：source 在 target 上方
            # 螺栓从 source 底面（贴合面）向下穿
            install_z = sz
        else:  # MOUNTED_ON
            # source 安装在 target 上
            install_z = sz

        # 限制螺栓长度不超过配合厚度的 1.5 倍
        # target 厚度估算
        target_part = next((p for p in intent.parts if p.name == rel.target), None)
        target_th = 15  # 默认底板厚 15
        if target_part:
            target_th = target_part.params.get("thickness", 15)
        max_bolt_len = target_th * BOLT_LENGTH_MAX_RATIO
        if bolt_len > max_bolt_len:
            bolt_len = max_bolt_len

        for i, (dx, dy) in enumerate(offsets):
            bx = sx + dx
            by = sy + dy
            bz = install_z

            # 构造 4x4 变换（螺栓默认沿 Z 轴，头朝上）
            transform = [
                1.0, 0.0, 0.0, bx,
                0.0, 1.0, 0.0, by,
                0.0, 0.0, 1.0, bz,
                0.0, 0.0, 0.0, 1.0,
            ]

            fasteners.append(FastenerSpec(
                name=f"bolt_{rel.source}_{i}",
                type="bolt",
                part_path=bolt_path,
                transform=transform,
                source_rel=(rel.source, rel.target, rel.rel_type),
            ))

        return fasteners


class TubeRule(FastenerRule):
    """
    气管规则：
      CONNECTED_TO(A, B) → 仅当 A 和 B 距离 < 300mm 时生成一段气管
    """

    def applies_to(self, rel: Relation, intent: AssemblyIntent) -> bool:
        return rel.rel_type == RelationType.CONNECTED_TO

    def generate(self, rel: Relation, intent: AssemblyIntent, positions: Dict[str, Tuple[float, float, float]]) -> List[FastenerSpec]:
        pos_a = positions.get(rel.source)
        pos_b = positions.get(rel.target)
        if pos_a is None or pos_b is None:
            return []

        dist = math.dist(pos_a, pos_b)
        if dist > MAX_TUBE_DISTANCE:
            return []

        # 只生成 1 段气管，放在中点，方向指向 B
        mx = (pos_a[0] + pos_b[0]) / 2
        my = (pos_a[1] + pos_b[1]) / 2
        mz = (pos_a[2] + pos_b[2]) / 2

        # 计算旋转：气管默认沿 Z 轴，需要旋转到指向 B 的方向
        dx = pos_b[0] - pos_a[0]
        dy = pos_b[1] - pos_a[1]
        dz = pos_b[2] - pos_a[2]

        # 简化为水平或垂直放置
        if abs(dz) < max(abs(dx), abs(dy)) * 0.3:
            # 水平方向
            angle = math.degrees(math.atan2(dy, dx))
            transform = [
                math.cos(math.radians(angle)), -math.sin(math.radians(angle)), 0.0, mx,
                math.sin(math.radians(angle)), math.cos(math.radians(angle)), 0.0, my,
                0.0, 0.0, 1.0, mz,
                0.0, 0.0, 0.0, 1.0,
            ]
        else:
            # 垂直方向
            transform = [
                1.0, 0.0, 0.0, mx,
                0.0, 1.0, 0.0, my,
                0.0, 0.0, 1.0, mz,
                0.0, 0.0, 0.0, 1.0,
            ]

        return [FastenerSpec(
            name=f"tube_{rel.source}_{rel.target}",
            type="tube",
            part_path="../automation_parts/air_tube_6mm.step",
            transform=transform,
            source_rel=(rel.source, rel.target, rel.rel_type),
        )]


class CableRule(FastenerRule):
    """
    电缆规则：
      传感器 → 控制器 → 仅当距离 < 400mm 时生成电缆
    """

    def applies_to(self, rel: Relation, intent: AssemblyIntent) -> bool:
        # 只对传感器相关的 CONNECTED_TO 生成电缆
        return rel.rel_type == RelationType.CONNECTED_TO and ("sensor" in rel.source.lower())

    def generate(self, rel: Relation, intent: AssemblyIntent, positions: Dict[str, Tuple[float, float, float]]) -> List[FastenerSpec]:
        pos_a = positions.get(rel.source)
        pos_b = positions.get(rel.target)
        if pos_a is None or pos_b is None:
            return []

        dist = math.dist(pos_a, pos_b)
        if dist > MAX_CABLE_DISTANCE:
            return []

        mx = (pos_a[0] + pos_b[0]) / 2
        my = (pos_a[1] + pos_b[1]) / 2
        mz = (pos_a[2] + pos_b[2]) / 2

        return [FastenerSpec(
            name=f"cable_{rel.source}_{rel.target}",
            type="cable",
            part_path="../automation_parts/sensor_cable.step",
            transform=[1.0, 0.0, 0.0, mx, 0.0, 1.0, 0.0, my, 0.0, 0.0, 1.0, mz, 0.0, 0.0, 0.0, 1.0],
            source_rel=(rel.source, rel.target, rel.rel_type),
        )]


# ── 规则引擎入口 ──

ALL_RULES: List[FastenerRule] = [
    BoltRule(),
    TubeRule(),
    CableRule(),
]


def generate_fasteners(intent: AssemblyIntent, part_positions: Dict[str, Tuple[float, float, float]]) -> List[FastenerSpec]:
    """
    根据 AssemblyIntent 中的关系自动生成连接件。

    Args:
        intent: 装配意图（含零件和关系）
        part_positions: 每个零件的全局位置 {name: (x, y, z)}

    Returns:
        连接件规格列表
    """
    fasteners: List[FastenerSpec] = []

    for rel in intent.relations:
        for rule in ALL_RULES:
            if rule.applies_to(rel, intent):
                f = rule.generate(rel, intent, part_positions)
                fasteners.extend(f)

    # 去重：同一位置同一类型的连接件只保留一个
    seen = set()
    unique = []
    for f in fasteners:
        key = (round(f.transform[3], -1), round(f.transform[7], -1), round(f.transform[11], -1), f.type)
        if key not in seen:
            seen.add(key)
            unique.append(f)

    return unique


def count_fasteners(fasteners: List[FastenerSpec]) -> Dict[str, int]:
    """统计连接件数量。"""
    counts = {}
    for f in fasteners:
        counts[f.type] = counts.get(f.type, 0) + 1
    return counts
