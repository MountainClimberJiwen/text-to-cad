#!/usr/bin/env python3
"""
CADEnv — Gymnasium environment for CAD assembly optimization via RL.

State:  current placements (x,y,z,rz per part) + verification metrics
Action: per-part displacement (dx,dy,dz,drz) scaled by step_size
Reward: based on interference count, constraint gaps, clearance warnings
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import build123d
import gymnasium as gym
import numpy as np

from OCP.Bnd import Bnd_Box
from OCP.BRepAlgoAPI import BRepAlgoAPI_Common
from OCP.BRepBndLib import BRepBndLib
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.BRepGProp import BRepGProp
from OCP.GProp import GProp_GProps
from OCP.gp import gp_Trsf


def _get_bbox(shape) -> Bnd_Box:
    box = Bnd_Box()
    BRepBndLib.AddOptimal_s(shape.wrapped, box, False, False)
    return box


def _intersection_volume(shape_a, shape_b) -> float:
    common = BRepAlgoAPI_Common(shape_a.wrapped, shape_b.wrapped)
    common.Build()
    if common.Shape().IsNull():
        return 0.0
    props = GProp_GProps()
    BRepGProp.VolumeProperties_s(common.Shape(), props)
    return float(props.Mass())


def _compute_exact_distance(shape_a, shape_b) -> float:
    dist = BRepExtrema_DistShapeShape(shape_a.wrapped, shape_b.wrapped)
    dist.Perform()
    if dist.IsDone():
        return float(dist.Value())
    return float("inf")


def _bbox_min_gap(box_a: Bnd_Box, box_b: Bnd_Box) -> float:
    ax1, ay1, az1, ax2, ay2, az2 = box_a.Get()
    bx1, by1, bz1, bx2, by2, bz2 = box_b.Get()
    gaps = []
    if ax2 < bx1:
        gaps.append(bx1 - ax2)
    elif bx2 < ax1:
        gaps.append(ax1 - bx2)
    else:
        gaps.append(0.0)
    if ay2 < by1:
        gaps.append(by1 - ay2)
    elif by2 < ay1:
        gaps.append(ay1 - by2)
    else:
        gaps.append(0.0)
    if az2 < bz1:
        gaps.append(bz1 - az2)
    elif bz2 < az1:
        gaps.append(az1 - bz2)
    else:
        gaps.append(0.0)
    if all(g == 0.0 for g in gaps):
        return 0.0
    return max(gaps)


class CADEnv(gym.Env):
    """
    Model-free RL environment for CAD assembly placement optimization.

    The agent learns to adjust part placements to eliminate interferences
    and satisfy constraints, without any prior model of CAD geometry.
    """

    metadata = {"render_modes": ["human", "json"]}

    def __init__(
        self,
        constraints_path: str | Path,
        parts_dir: str | Path | None = None,
        step_size: float = 2.0,
        rot_step_size: float = 2.0,
        min_gap_threshold: float = 5.0,
        motion_gap_threshold: float = 20.0,
        max_steps: int = 100,
        geometry_check_interval: int = 5,
        allowed_overlaps: list[dict[str, Any]] | None = None,
        reward_weights: dict[str, float] | None = None,
        render_mode: str | None = None,
    ):
        super().__init__()
        self.constraints_path = Path(constraints_path)
        self.parts_dir = Path(parts_dir) if parts_dir else self.constraints_path.parent
        self.step_size = step_size
        self.rot_step_size = rot_step_size
        self.min_gap_threshold = min_gap_threshold
        self.motion_gap_threshold = motion_gap_threshold
        self.max_steps = max_steps
        self.geometry_check_interval = geometry_check_interval
        self.allowed_overlaps = allowed_overlaps or []
        self.render_mode = render_mode

        # Default reward weights
        self.reward_weights = {
            "interference": -10.0,
            "gap_error": -5.0,
            "clearance_warning": -1.0,
            "action_magnitude": -0.01,
            "all_passed": 100.0,
            "step_penalty": -0.1,
            **(reward_weights or {}),
        }

        # Load constraints
        with open(self.constraints_path, encoding="utf-8") as f:
            self.constraints_data = json.load(f)

        # Identify fixed parts (they should not be moved by the agent)
        all_part_ids = [p["id"] for p in self.constraints_data.get("parts", [])]
        fixed_parts = set()
        for c in self.constraints_data.get("constraints", []):
            if c.get("type") == "Fix":
                fixed_parts.add(c.get("part"))
        self.fixed_parts = fixed_parts
        self.movable_part_ids = [pid for pid in all_part_ids if pid not in fixed_parts]
        self.part_ids = all_part_ids
        self.n_parts = len(self.part_ids)
        self.n_movable = len(self.movable_part_ids)
        if self.n_parts == 0:
            raise ValueError("No parts in constraints file")

        # Load original shapes (unplaced)
        self.original_shapes: dict[str, Any] = {}
        self.part_bboxes: dict[str, tuple[float, ...]] = {}
        for pc in self.constraints_data["parts"]:
            pid = pc["id"]
            step_path = self.parts_dir / pc["file"]
            if not step_path.exists():
                # Try relative to repo root
                step_path = Path.cwd() / pc["file"]
            shape = build123d.import_step(str(step_path))
            self.original_shapes[pid] = shape
            bb = shape.bounding_box()
            self.part_bboxes[pid] = (bb.min.X, bb.min.Y, bb.min.Z, bb.max.X, bb.max.Y, bb.max.Z)

        # Action space: per-movable-part (dx, dy, dz, drz) in [-1, 1]
        self.action_space = gym.spaces.Box(
            low=-1.0, high=1.0, shape=(self.n_movable * 4,), dtype=np.float32
        )

        # Observation space: per-part (x, y, z, rz) + 3 metrics
        obs_dim = self.n_parts * 4 + 3
        self.observation_space = gym.spaces.Box(
            low=-np.inf, high=np.inf, shape=(obs_dim,), dtype=np.float32
        )

        # Internal state
        self.placements: dict[str, dict[str, float]] = {}
        self.step_count = 0
        self.best_reward = -float("inf")
        self.best_placements: dict[str, dict[str, float]] | None = None
        self._cached_report: dict[str, Any] | None = None

    # ------------------------------------------------------------------
    # Constraint parsing (same logic as check_gap.py)
    # ------------------------------------------------------------------
    def _initial_placements(self) -> dict[str, dict[str, float]]:
        """Derive initial placements from constraints.json."""
        expected = {pid: {"x": 0.0, "y": 0.0, "z": 0.0, "rz": 0.0} for pid in self.part_ids}
        constraints = self.constraints_data.get("constraints", [])

        def priority(c):
            return {"Fix": 0, "PlaneCoincident": 1, "CenterOfMass": 2, "Distance": 3, "Rotation": 4}.get(
                c["type"], 99
            )

        for c in sorted(constraints, key=priority):
            ctype = c["type"]
            if ctype == "Fix":
                expected[c["part"]] = {"x": 0.0, "y": 0.0, "z": 0.0, "rz": 0.0}
            elif ctype == "PlaneCoincident":
                pa = c["part_a"]
                pb = c["part_b"]
                face_a = c.get("face_a", "bottom")
                face_b = c.get("face_b", "top")
                if face_a == "bottom" and face_b == "top":
                    z_offset = self.part_bboxes[pb][5] - self.part_bboxes[pa][2]
                    expected[pa]["z"] = z_offset
                elif face_a == "top" and face_b == "bottom":
                    z_offset = self.part_bboxes[pb][2] - self.part_bboxes[pa][5]
                    expected[pa]["z"] = z_offset
            elif ctype == "Distance":
                pa = c.get("part_a") or c.get("part")
                axis = c.get("axis", "z")
                value = float(c.get("value", 0))
                expected[pa][axis] = value
            elif ctype == "CenterOfMass":
                pa = c["part_a"]
                pb = c["part_b"]
                axis = c.get("axis", "x")
                idx = {"x": 0, "y": 1, "z": 2}[axis]
                center_a = (self.part_bboxes[pa][idx] + self.part_bboxes[pa][idx + 3]) / 2
                center_b = (self.part_bboxes[pb][idx] + self.part_bboxes[pb][idx + 3]) / 2
                expected[pa][axis] = center_b - center_a
            elif ctype == "Rotation":
                pa = c["part"]
                axis = c.get("axis", "z")
                value = float(c.get("value", 0))
                if axis == "z":
                    expected[pa]["rz"] = value
                elif axis == "y":
                    pass  # ry not in state
                elif axis == "x":
                    pass  # rx not in state
        return expected

    # ------------------------------------------------------------------
    # Gymnasium API
    # ------------------------------------------------------------------
    def reset(self, seed: int | None = None, options: dict | None = None):
        super().reset(seed=seed)
        self.step_count = 0
        self._cached_report = None

        # Initialize placements from constraints
        self.placements = self._initial_placements()

        # Optional perturbation for training diversity
        perturb = (options or {}).get("perturbation", 0.0)
        if perturb > 0.0:
            for pid in self.movable_part_ids:
                self.placements[pid]["x"] += self.np_random.normal(0, perturb)
                self.placements[pid]["y"] += self.np_random.normal(0, perturb)
                self.placements[pid]["z"] += self.np_random.normal(0, perturb)
                self.placements[pid]["rz"] += self.np_random.normal(0, perturb)

        # Run initial verification
        initial_report = self._verify()
        obs = self._get_obs(initial_report)
        info = self._get_info(initial_report)
        return obs, info

    def step(self, action: np.ndarray):
        self.step_count += 1

        # Scale action
        action = np.clip(action, -1.0, 1.0)
        deltas = action.reshape(self.n_movable, 4)

        # Apply to movable placements only
        for i, pid in enumerate(self.movable_part_ids):
            d = deltas[i]
            self.placements[pid]["x"] += d[0] * self.step_size
            self.placements[pid]["y"] += d[1] * self.step_size
            self.placements[pid]["z"] += d[2] * self.step_size
            self.placements[pid]["rz"] += d[3] * self.rot_step_size
            # Normalize rz to [-180, 180]
            while self.placements[pid]["rz"] > 180:
                self.placements[pid]["rz"] -= 360
            while self.placements[pid]["rz"] < -180:
                self.placements[pid]["rz"] += 360

        # Update shapes
        # Verify: full geometry check only every N steps for speed
        if self.step_count % self.geometry_check_interval == 0 or self._cached_report is None:
            report = self._verify()
            self._cached_report = report
        else:
            # Fast check: only constraint gaps (geometry from cache)
            report = self._fast_verify()
            # Merge cached geometry results
            report["interferences"] = self._cached_report["interferences"]
            report["clearance_warnings"] = self._cached_report["clearance_warnings"]
            # Recompute all_passed
            report["all_passed"] = (
                len(report["interferences"]) == 0
                and len(report["gap_errors"]) == 0
                and len(report["clearance_warnings"]) == 0
            )

        # Compute reward
        reward = self._compute_reward(report, action)
        if reward > self.best_reward:
            self.best_reward = reward
            self.best_placements = {pid: p.copy() for pid, p in self.placements.items()}

        # Termination
        terminated = bool(report["all_passed"])
        truncated = self.step_count >= self.max_steps

        obs = self._get_obs(report)
        info = self._get_info(report)

        return obs, float(reward), terminated, truncated, info

    def render(self):
        if self.render_mode == "json":
            return {
                "placements": self.placements,
                "step": self.step_count,
                "best_reward": self.best_reward,
                "best_placements": self.best_placements,
            }
        elif self.render_mode == "human":
            print(f"Step {self.step_count}: placements={self.placements}")
        return None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _get_moved_shape(self, pid: str) -> Any:
        """Lazy-create moved shape for a single part."""
        orig = self.original_shapes[pid]
        p = self.placements[pid]
        rz = math.radians(p["rz"])
        trsf = gp_Trsf()
        trsf.SetValues(
            math.cos(rz), -math.sin(rz), 0.0, p["x"],
            math.sin(rz), math.cos(rz), 0.0, p["y"],
            0.0, 0.0, 1.0, p["z"],
        )
        loc = build123d.Location(trsf)
        return orig.moved(loc)

    def _is_allowed_overlap(self, name_a: str, name_b: str) -> bool:
        for ao in self.allowed_overlaps:
            pair = ao.get("pair", [])
            if len(pair) == 2:
                if (pair[0] == name_a and pair[1] == name_b) or (pair[0] == name_b and pair[1] == name_a):
                    return True
        return False

    def _transformed_bbox(self, pid: str) -> tuple[float, ...]:
        """Compute transformed bbox without creating the full moved shape."""
        p = self.placements[pid]
        bb = self.part_bboxes[pid]
        rz = math.radians(p["rz"])
        cr, sr = math.cos(rz), math.sin(rz)
        tx, ty, tz = p["x"], p["y"], p["z"]

        corners = [
            (bb[0], bb[1], bb[2]), (bb[0], bb[1], bb[5]),
            (bb[0], bb[4], bb[2]), (bb[0], bb[4], bb[5]),
            (bb[3], bb[1], bb[2]), (bb[3], bb[1], bb[5]),
            (bb[3], bb[4], bb[2]), (bb[3], bb[4], bb[5]),
        ]
        xs, ys, zs = [], [], []
        for x, y, z in corners:
            xs.append(cr * x - sr * y + tx)
            ys.append(sr * x + cr * y + ty)
            zs.append(z + tz)
        return (min(xs), min(ys), min(zs), max(xs), max(ys), max(zs))

    def _bbox_min_gap_fast(self, bb_a: tuple, bb_b: tuple) -> float:
        ax1, ay1, az1, ax2, ay2, az2 = bb_a
        bx1, by1, bz1, bx2, by2, bz2 = bb_b
        gaps = []
        if ax2 < bx1:
            gaps.append(bx1 - ax2)
        elif bx2 < ax1:
            gaps.append(ax1 - bx2)
        else:
            gaps.append(0.0)
        if ay2 < by1:
            gaps.append(by1 - ay2)
        elif by2 < ay1:
            gaps.append(ay1 - by2)
        else:
            gaps.append(0.0)
        if az2 < bz1:
            gaps.append(bz1 - az2)
        elif bz2 < az1:
            gaps.append(az1 - bz2)
        else:
            gaps.append(0.0)
        if all(g == 0.0 for g in gaps):
            return 0.0
        return max(gaps)

    def _verify(self) -> dict[str, Any]:
        """Run geometric verification (optimized with lazy shape creation)."""
        n = self.n_parts
        interferences = []
        clearance_warnings = []

        # Precompute transformed bboxes (fast, no OCP calls)
        bboxes = {pid: self._transformed_bbox(pid) for pid in self.part_ids}

        # Pairwise checks
        moved_shapes_cache: dict[str, Any] = {}
        for i in range(n):
            for j in range(i + 1, n):
                pa = self.part_ids[i]
                pb = self.part_ids[j]
                bbox_a = bboxes[pa]
                bbox_b = bboxes[pb]

                # Fast bbox rejection
                bbox_gap = self._bbox_min_gap_fast(bbox_a, bbox_b)
                if bbox_gap > max(self.min_gap_threshold, self.motion_gap_threshold):
                    continue

                # Lazy-create moved shapes only for pairs that need exact check
                if pa not in moved_shapes_cache:
                    moved_shapes_cache[pa] = self._get_moved_shape(pa)
                if pb not in moved_shapes_cache:
                    moved_shapes_cache[pb] = self._get_moved_shape(pb)

                shape_a = moved_shapes_cache[pa]
                shape_b = moved_shapes_cache[pb]

                        # Interference check (skip allowed overlaps)
                vol = _intersection_volume(shape_a, shape_b)
                if vol > 0.1 and not self._is_allowed_overlap(pa, pb):
                    interferences.append({
                        "part_a": pa,
                        "part_b": pb,
                        "volume": round(vol, 3),
                    })
                    continue

                # Exact distance check
                exact_dist = _compute_exact_distance(shape_a, shape_b)
                if 0.01 < exact_dist < self.min_gap_threshold:
                    clearance_warnings.append({
                        "part_a": pa,
                        "part_b": pb,
                        "distance": round(exact_dist, 3),
                        "threshold": self.min_gap_threshold,
                    })

        # Constraint gap check (fast, no geometry)
        expected = self._initial_placements()
        gap_errors = []
        for pid in self.part_ids:
            e = expected[pid]
            a = self.placements[pid]
            for axis in ("x", "y", "z"):
                err = abs(a[axis] - e[axis])
                if err > 0.5:
                    gap_errors.append({
                        "part": pid,
                        "axis": axis,
                        "expected": round(e[axis], 2),
                        "actual": round(float(a[axis]), 2),
                        "error": round(err, 2),
                    })
            rz_err = abs(a["rz"] - e["rz"])
            if rz_err > 180:
                rz_err = 360 - rz_err
            if rz_err > 0.5:
                gap_errors.append({
                    "part": pid,
                    "axis": "rz",
                    "expected": round(e["rz"], 2),
                    "actual": round(float(a["rz"]), 2),
                    "error": round(rz_err, 2),
                })

        all_passed = len(interferences) == 0 and len(gap_errors) == 0 and len(clearance_warnings) == 0

        return {
            "interferences": interferences,
            "gap_errors": gap_errors,
            "clearance_warnings": clearance_warnings,
            "all_passed": all_passed,
        }

    def _fast_verify(self) -> dict[str, Any]:
        """Fast verification: only constraint gaps, no OCP geometry calls."""
        expected = self._initial_placements()
        gap_errors = []
        for pid in self.part_ids:
            e = expected[pid]
            a = self.placements[pid]
            for axis in ("x", "y", "z"):
                err = abs(a[axis] - e[axis])
                if err > 0.5:
                    gap_errors.append({
                        "part": pid,
                        "axis": axis,
                        "expected": round(e[axis], 2),
                        "actual": round(float(a[axis]), 2),
                        "error": round(err, 2),
                    })
            rz_err = abs(a["rz"] - e["rz"])
            if rz_err > 180:
                rz_err = 360 - rz_err
            if rz_err > 0.5:
                gap_errors.append({
                    "part": pid,
                    "axis": "rz",
                    "expected": round(e["rz"], 2),
                    "actual": round(float(a["rz"]), 2),
                    "error": round(rz_err, 2),
                })
        return {
            "interferences": [],
            "gap_errors": gap_errors,
            "clearance_warnings": [],
            "all_passed": len(gap_errors) == 0,
        }

    def _compute_reward(self, report: dict, action: np.ndarray) -> float:
        w = self.reward_weights
        r = 0.0
        r += w["interference"] * len(report["interferences"])
        r += w["gap_error"] * len(report["gap_errors"])
        r += w["clearance_warning"] * len(report["clearance_warnings"])
        r += w["step_penalty"]
        r += w["action_magnitude"] * float(np.linalg.norm(action))
        if report["all_passed"]:
            r += w["all_passed"]
        return r

    def _get_obs(self, report: dict | None = None) -> np.ndarray:
        if report is None:
            report = {"interferences": [], "gap_errors": [], "clearance_warnings": []}
        obs = []
        for pid in self.part_ids:
            p = self.placements[pid]
            obs.extend([p["x"], p["y"], p["z"], p["rz"]])
        obs.extend([
            len(report["interferences"]),
            len(report["gap_errors"]),
            len(report["clearance_warnings"]),
        ])
        return np.array(obs, dtype=np.float32)

    def _get_info(self, report: dict | None = None) -> dict:
        if report is None:
            report = {"interferences": [], "gap_errors": [], "clearance_warnings": [], "all_passed": True}
        return {
            "placements": {pid: p.copy() for pid, p in self.placements.items()},
            "report": report,
            "step": self.step_count,
            "best_reward": self.best_reward,
            "best_placements": self.best_placements,
        }

    def export_best_placements(self, out_path: str | Path):
        """Export best-found placements as placements.json format."""
        if self.best_placements is None:
            raise RuntimeError("No best placements recorded (environment not run yet)")
        data = {}
        for pid, p in self.best_placements.items():
            data[pid] = {
                "base": [float(round(p["x"], 6)), float(round(p["y"], 6)), float(round(p["z"], 6))],
                "rotation_axis": [0.0, 0.0, 1.0],
                "rotation_angle": float(round(p["rz"], 6)),
            }
        Path(out_path).write_text(json.dumps(data, indent=2), encoding="utf-8")
