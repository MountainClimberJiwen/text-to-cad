#!/usr/bin/env python3
"""
Detailed industrial automation station — vision-guided parametric CAD.

Reconstructed from: skills/industrial_cad/sample.jpg
Station type: small-part automatic feeding + pick-and-place transfer

Total solids: ~70  (each top-level assembly exploded into realistic sub-parts)
"""
from __future__ import annotations

import math

from build123d import (
    Box, Cylinder, Pos, Rot, Compound, Color,
)

# ──────────────────────────────────────────────────────────
#  Station-level parameters (mm)
# ──────────────────────────────────────────────────────────
BASE_W, BASE_D, BASE_H = 800, 500, 40       # extrusion frame outer size
PANEL_TH = 15                               # top panel thickness
COLUMN_W, COLUMN_D, COLUMN_H = 80, 60, 380  # center support column

# Positions on base plate (origin at base center)
POS_COLUMN = (0, 0)
POS_LEFT_SLIDE = (-280, 80)
POS_VIB_BOWL = (260, -120)
POS_HOPPER = (320, 120)
POS_TRACK = (100, -120)


def _gray(v: float) -> tuple:
    return (v, v, v)


# ═══════════════════════════════════════════════════════
#  1. BASE FRAME (aluminum extrusion + panel + feet)
# ═══════════════════════════════════════════════════════
def build_base_frame() -> list:
    s = []
    col = _gray(0.70)      # aluminum extrusion
    panel = _gray(0.88)    # white panel
    foot = _gray(0.12)     # black rubber foot

    prof = 40  # 40x40 extrusion
    z_extr = prof / 2

    # 4 longitudinal bars (along X)
    for dy in [-BASE_D/2 + prof/2, BASE_D/2 - prof/2]:
        s.append((Pos(0, dy, z_extr) * Box(BASE_W, prof, prof), col))
    # 4 transverse bars (along Y)
    for dx in [-BASE_W/2 + prof/2, BASE_W/2 - prof/2]:
        s.append((Pos(dx, 0, z_extr) * Box(prof, BASE_D, prof), col))
    # Center cross bars
    s.append((Pos(0, 0, z_extr) * Box(BASE_W - 80, prof, prof), col))
    s.append((Pos(0, 0, z_extr) * Box(prof, BASE_D - 80, prof), col))

    # Top panel
    s.append((Pos(0, 0, BASE_H + PANEL_TH/2) * Box(BASE_W - 10, BASE_D - 10, PANEL_TH), panel))

    # 4 leveling feet with pads
    for dx in [-BASE_W/2 + 40, BASE_W/2 - 40]:
        for dy in [-BASE_D/2 + 40, BASE_D/2 - 40]:
            s.append((Pos(dx, dy, -25) * Cylinder(12, 50), _gray(0.30)))   # metal stem
            s.append((Pos(dx, dy, -52) * Cylinder(22, 4), foot))          # rubber pad
    return s


# ═══════════════════════════════════════════════════════
#  2. CENTER COLUMN + TOP STRUCTURE
# ═══════════════════════════════════════════════════════
def build_center_column(x, y, z_base) -> list:
    s = []
    beige = (0.80, 0.77, 0.70)
    dark = _gray(0.35)
    steel = _gray(0.55)

    # Main column
    s.append((Pos(x, y, z_base + COLUMN_H/2) * Box(COLUMN_W, COLUMN_D, COLUMN_H), beige))

    # Base plate (wider mounting flange)
    bp_w, bp_d, bp_t = COLUMN_W + 60, COLUMN_D + 60, 15
    s.append((Pos(x, y, z_base + bp_t/2) * Box(bp_w, bp_d, bp_t), dark))
    # Top plate
    s.append((Pos(x, y, z_base + COLUMN_H + bp_t/2) * Box(bp_w, bp_d, bp_t), dark))

    # 4 gussets at base (triangular braces)
    for dx in [-COLUMN_W/2 - 5, COLUMN_W/2 + 5]:
        for dy in [-COLUMN_D/2 - 5, COLUMN_D/2 + 5]:
            gus = Pos(x + dx, y + dy, z_base + 40) * Box(8, 35, 80)
            s.append((gus, dark))

    # Side mounting rails on column (for vertical slide)
    rail_w, rail_d, rail_h = 12, 8, COLUMN_H * 0.7
    for dy in [-COLUMN_D/2 - 6, COLUMN_D/2 + 6]:
        s.append((Pos(x, y + dy, z_base + COLUMN_H*0.5) * Box(rail_w, rail_d, rail_h), steel))
    return s


# ═══════════════════════════════════════════════════════
#  3. PNEUMATIC CYLINDER (detailed)
# ═══════════════════════════════════════════════════════
def build_pneumatic_cylinder(x, y, z, body_dia, stroke, axis="z", color=(0.82, 0.15, 0.15)) -> list:
    """Returns: body, front cap, rear cap, piston rod, rod end, bracket, 2 sensors."""
    s = []
    body_len = stroke * 1.6
    cap_col = _gray(0.22)
    rod_col = _gray(0.93)
    bracket_col = _gray(0.52)
    sensor_col = (0.12, 0.32, 0.72)

    if axis == "z":
        # Body
        s.append((Pos(x, y, z) * Cylinder(body_dia/2, body_len), color))
        # Front cap (with rod seal)
        s.append((Pos(x, y, z + body_len/2 + 4) * Cylinder(body_dia/2 + 3, 8), cap_col))
        # Rear cap (with air ports)
        s.append((Pos(x, y, z - body_len/2 - 4) * Cylinder(body_dia/2 + 3, 8), cap_col))
        # Air port nipples on rear cap
        for dx2 in [-body_dia/2 - 6, body_dia/2 + 6]:
            s.append((Pos(x + dx2, y, z - body_len/2 - 8) * Cylinder(4, 10), _gray(0.15)))
        # Piston rod
        s.append((Pos(x, y, z + body_len/2 + stroke/2 + 8) * Cylinder(body_dia/5, stroke), rod_col))
        # Rod end clevis / fitting
        s.append((Pos(x, y, z + body_len/2 + stroke + 12) * Cylinder(body_dia/3, 8), cap_col))
        s.append((Pos(x, y, z + body_len/2 + stroke + 18) * Box(body_dia/1.5, body_dia/1.5, 6), cap_col))
        # Mounting bracket (rear, L-shaped foot)
        s.append((Pos(x, y + body_dia/2 + 10, z - body_len*0.05) * Box(body_dia + 16, 10, body_len*0.45), bracket_col))
        # 2 magnetic reed sensors on body
        for sz in [z - body_len*0.15, z + body_len*0.25]:
            s.append((Pos(x + body_dia/2 + 5, y, sz) * Box(10, 12, 7), sensor_col))
            # Sensor LED
            s.append((Pos(x + body_dia/2 + 10, y, sz) * Cylinder(2, 2), (0.9, 0.1, 0.1)))

    elif axis == "x":
        # Horizontal version
        s.append((Pos(x, y, z) * Rot(0, 90, 0) * Cylinder(body_dia/2, body_len), color))
        s.append((Pos(x + body_len/2 + 4, y, z) * Rot(0, 90, 0) * Cylinder(body_dia/2 + 3, 8), cap_col))
        s.append((Pos(x - body_len/2 - 4, y, z) * Rot(0, 90, 0) * Cylinder(body_dia/2 + 3, 8), cap_col))
        for dy2 in [-body_dia/2 - 6, body_dia/2 + 6]:
            s.append((Pos(x - body_len/2 - 8, y + dy2, z) * Rot(90, 0, 90) * Cylinder(4, 10), _gray(0.15)))
        s.append((Pos(x + body_len/2 + stroke/2 + 8, y, z) * Rot(0, 90, 0) * Cylinder(body_dia/5, stroke), rod_col))
        s.append((Pos(x + body_len/2 + stroke + 12, y, z) * Rot(0, 90, 0) * Cylinder(body_dia/3, 8), cap_col))
        # Bracket below
        s.append((Pos(x - body_len*0.05, y, z - body_dia/2 - 10) * Box(body_len*0.45, body_dia + 16, 10), bracket_col))
        for sx in [x - body_len*0.15, x + body_len*0.25]:
            s.append((Pos(sx, y + body_dia/2 + 5, z) * Box(7, 10, 12), sensor_col))
    return s


# ═══════════════════════════════════════════════════════
#  4. LINEAR GUIDE RAIL (rail + slider + caps + screws)
# ═══════════════════════════════════════════════════════
def build_guide_rail(x, y, z, length, width=12, depth=10, axis="z") -> list:
    s = []
    rail_col = _gray(0.20)
    slider_col = _gray(0.58)
    cap_col = _gray(0.30)
    screw_col = _gray(0.75)

    if axis == "z":
        # Rail body
        s.append((Pos(x, y, z) * Box(width, depth, length), rail_col))
        # Ball groove detail (2 lines on top)
        for dx in [-width*0.25, width*0.25]:
            s.append((Pos(x + dx, y - depth/2 - 1, z) * Box(2, 2, length), _gray(0.10)))
        # Slider block (wider, rides on rail)
        s.append((Pos(x, y + depth*0.4, z + length*0.15) * Box(width*1.6, depth*1.8, length*0.35), slider_col))
        # 2 end caps
        for dz in [-length/2 + 5, length/2 - 5]:
            s.append((Pos(x, y - depth*0.3, z + dz) * Box(width*1.2, depth*0.6, 10), cap_col))
        # 4 mounting screws (counter-bored)
        for dx in [-width*0.3, width*0.3]:
            for dz in [-length*0.35, length*0.35]:
                s.append((Pos(x + dx, y + depth/2 + 2, z + dz) * Cylinder(3, 6), screw_col))
                s.append((Pos(x + dx, y + depth/2 + 5, z + dz) * Cylinder(5, 2), _gray(0.40)))
    elif axis == "x":
        s.append((Pos(x, y, z) * Box(length, depth, width), rail_col))
        s.append((Pos(x + length*0.15, y + depth*0.4, z) * Box(length*0.35, depth*1.8, width*1.6), slider_col))
        for dx2 in [-length/2 + 5, length/2 - 5]:
            s.append((Pos(x + dx2, y - depth*0.3, z) * Box(10, depth*0.6, width*1.2), cap_col))
    return s


# ═══════════════════════════════════════════════════════
#  5. PRODUCT GRIPPER (body + jaws + drive + pins)
# ═══════════════════════════════════════════════════════
def build_gripper(x, y, z, w=50, d=35, h=30) -> list:
    s = []
    body_col = (0.18, 0.52, 0.22)   # green anodized
    jaw_col = _gray(0.82)
    pin_col = _gray(0.60)
    cyl_col = _gray(0.18)

    # Main body block
    s.append((Pos(x, y, z) * Box(w, d, h), body_col))
    # Top mini cylinder (drive)
    s.append((Pos(x, y, z + h/2 + 8) * Cylinder(w/3.5, 18), cyl_col))
    s.append((Pos(x, y, z + h/2 + 20) * Cylinder(w/5, 6), _gray(0.40)))  # cap
    # Left jaw (with grip teeth)
    jw, jd, jh = w*0.22, d*0.55, h*1.3
    s.append((Pos(x - w*0.32, y, z - h*0.05) * Box(jw, jd, jh), jaw_col))
    # Grip teeth on left jaw
    for tz in [z - h*0.3, z + h*0.3]:
        s.append((Pos(x - w*0.32 - jw/2 - 2, y, tz) * Box(3, jd*0.8, 4), _gray(0.45)))
    # Right jaw
    s.append((Pos(x + w*0.32, y, z - h*0.05) * Box(jw, jd, jh), jaw_col))
    for tz in [z - h*0.3, z + h*0.3]:
        s.append((Pos(x + w*0.32 + jw/2 + 2, y, tz) * Box(3, jd*0.8, 4), _gray(0.45)))
    # 2 guide pins
    for dx in [-w*0.15, w*0.15]:
        s.append((Pos(x + dx, y + d*0.25, z + h*0.25) * Cylinder(2.5, d*0.45), pin_col))
    # Air hose connector
    s.append((Pos(x + w/2 + 4, y, z) * Cylinder(4, 8), _gray(0.15)))
    return s


# ═══════════════════════════════════════════════════════
#  6. VIBRATION BOWL FEEDER (bowl + spiral + base + controller)
# ═══════════════════════════════════════════════════════
def build_vibration_bowl(x, y, z, od=160, h=100) -> list:
    s = []
    steel = _gray(0.68)
    track = _gray(0.78)
    base_col = _gray(0.32)
    ctrl = _gray(0.12)

    # Main bowl (outer shell)
    s.append((Pos(x, y, z + h/2) * Cylinder(od/2, h), steel))
    # Inner hollow rim (darker)
    s.append((Pos(x, y, z + h + 2) * Cylinder(od*0.35, 4), _gray(0.55)))
    # Spiral track (5 rising rings)
    for i in range(5):
        r = od*0.37 + (od*0.13) * (i / 4)
        rh = 3
        rz = z + h * 0.25 + i * h * 0.12
        s.append((Pos(x, y, rz) * Cylinder(r, rh), track))
        # Track wall
        s.append((Pos(x, y, rz + 4) * Cylinder(r + 2, 2), _gray(0.50)))
    # Center cone
    s.append((Pos(x, y, z + h/2) * Cylinder(od*0.18, h), steel))
    # Electromagnetic base (heavy cylinder)
    s.append((Pos(x, y, z - 20) * Cylinder(od/2 + 15, 40), base_col))
    # Base mounting feet
    for angle in [0, 90, 180, 270]:
        fx = x + math.cos(math.radians(angle)) * (od/2 + 5)
        fy = y + math.sin(math.radians(angle)) * (od/2 + 5)
        s.append((Pos(fx, fy, z - 42) * Box(15, 15, 8), _gray(0.25)))
    # Controller box
    s.append((Pos(x + od/2 + 35, y, z + 25) * Box(45, 35, 60), ctrl))
    # Cable bundle
    s.append((Pos(x + od/2 + 12, y, z + 15) * Box(20, 8, 8), _gray(0.08)))
    return s


# ═══════════════════════════════════════════════════════
#  7. HOPPER (4 walls + bottom + flange + 4 legs)
# ═══════════════════════════════════════════════════════
def build_hopper(x, y, z, tw=140, td=140, h=110) -> list:
    s = []
    wall = _gray(0.78)
    leg = _gray(0.50)
    flange = _gray(0.65)

    bw, bd = tw * 0.65, td * 0.65
    wt = 3  # wall thickness

    # 4 walls (tapered approx with vertical boxes)
    s.append((Pos(x, y - td/2 + wt/2, z + h/2) * Box(tw, wt, h), wall))
    s.append((Pos(x, y + td/2 - wt/2, z + h/2) * Box(tw, wt, h), wall))
    s.append((Pos(x - tw/2 + wt/2, y, z + h/2) * Box(wt, td, h), wall))
    s.append((Pos(x + tw/2 - wt/2, y, z + h/2) * Box(wt, td, h), wall))
    # Bottom (smaller)
    s.append((Pos(x, y, z + wt/2) * Box(bw, bd, wt), wall))
    # Top flange (rim)
    s.append((Pos(x, y, z + h + wt/2) * Box(tw + 12, td + 12, wt), flange))
    # 4 support legs
    for dx in [-tw/2 + 18, tw/2 - 18]:
        for dy in [-td/2 + 18, td/2 - 18]:
            s.append((Pos(x + dx, y + dy, z - 35) * Box(22, 22, 70), leg))
    return s


# ═══════════════════════════════════════════════════════
#  8. LINEAR FEEDING TRACK (track + vibrator + legs + fence)
# ═══════════════════════════════════════════════════════
def build_linear_track(x, y, z, length=220, w=18, d=12) -> list:
    s = []
    track_col = _gray(0.62)
    vibrator = _gray(0.22)
    leg_col = _gray(0.48)
    fence = _gray(0.38)

    # Track U-channel body
    s.append((Pos(x, y, z) * Box(w, d, length), track_col))
    # Bottom flat
    s.append((Pos(x, y, z - d/2 - 2) * Box(w + 8, 5, length), track_col))
    # Vibrator unit underneath
    s.append((Pos(x, y, z - d/2 - 22) * Box(35, 28, 45), vibrator))
    # 2 support legs
    for dx in [-w*0.35, w*0.35]:
        s.append((Pos(x + dx, y, z - d/2 - 40) * Box(16, 16, 55), leg_col))
    # Side guide fences
    for dy in [-d/2 - 4, d/2 + 4]:
        s.append((Pos(x, y + dy, z + 6) * Box(w, 4, length), fence))
    # End stop at far end
    s.append((Pos(x, y, z + length/2 + 3) * Box(w, d + 8, 6), _gray(0.25)))
    return s


# ═══════════════════════════════════════════════════════
#  9. HOPPER SUPPORT (box frame + panels)
# ═══════════════════════════════════════════════════════
def build_hopper_support(x, y, z, w=100, d=100, h=90) -> list:
    s = []
    frame = _gray(0.58)
    panel = _gray(0.82)

    # Main box
    s.append((Pos(x, y, z + h/2) * Box(w, d, h), frame))
    # Top mounting plate
    s.append((Pos(x, y, z + h + 6) * Box(w + 15, d + 15, 12), panel))
    # Front panel (removable door look)
    s.append((Pos(x, y + d/2 + 2, z + h/2) * Box(w - 12, 4, h - 12), panel))
    # Side ventilation slots (represented as dark strips)
    for sz in [z + h*0.3, z + h*0.5, z + h*0.7]:
        s.append((Pos(x + w/2 + 2, y, sz) * Box(3, d*0.6, 8), _gray(0.20)))
    return s


# ═══════════════════════════════════════════════════════
#  10. LEFT SLIDE TABLE (large positioning mechanism)
# ═══════════════════════════════════════════════════════
def build_slide_table(x, y, z, w=160, d=90, h=25) -> list:
    """Large linear slide / positioning table."""
    s = []
    body = _gray(0.72)
    rail = _gray(0.20)
    slider = _gray(0.60)
    cover = _gray(0.85)

    # Base body
    s.append((Pos(x, y, z + h/2) * Box(w, d, h), body))
    # 2 parallel rails on top
    for dy in [-d*0.3, d*0.3]:
        s.append((Pos(x, y + dy, z + h + 4) * Box(w*0.9, 8, 8), rail))
    # Moving slider plate
    s.append((Pos(x + w*0.1, y, z + h + 10) * Box(w*0.5, d*0.8, 6), slider))
    # End covers
    for dx in [-w/2 + 8, w/2 - 8]:
        s.append((Pos(x + dx, y, z + h + 8) * Box(12, d*0.9, 16), cover))
    # Limit switches at ends
    for dx in [-w/2 + 15, w/2 - 15]:
        s.append((Pos(x + dx, y + d/2 + 6, z + h + 5) * Box(10, 8, 12), (0.9, 0.2, 0.1)))
    return s


# ═══════════════════════════════════════════════════════
#  11. PIPING & CABLES (air tubes, wiring)
# ═══════════════════════════════════════════════════════
def build_piping(cx, cy, cz) -> list:
    """Air tube bundles running from valves to cylinders."""
    s = []
    tube_blue = (0.1, 0.25, 0.65)
    tube_clear = (0.85, 0.90, 0.95)

    # Main air manifold (horizontal pipe along back)
    s.append((Pos(cx, cy - 180, cz + 220) * Rot(90, 0, 0) * Cylinder(6, 360), tube_blue))
    # Branch tubes to various cylinders (simplified as small cylinders)
    # To horizontal transfer cylinders
    for dx in [-30, 30]:
        s.append((Pos(cx + dx, cy - 100, cz + 280) * Cylinder(3, 80), tube_clear))
    # To vertical cylinder
    s.append((Pos(cx + 50, cy, cz + 200) * Cylinder(3, 120), tube_clear))
    # To left cylinders
    s.append((Pos(cx - 200, cy + 80, cz + 150) * Rot(0, 90, 0) * Cylinder(3, 100), tube_clear))
    return s


# ═══════════════════════════════════════════════════════
#  ASSEMBLE EVERYTHING
# ═══════════════════════════════════════════════════════

def _build_shape():
    shapes = []
    z0 = BASE_H + PANEL_TH  # parts sit on top of base panel

    # 1. Base frame
    shapes.extend(build_base_frame())

    # 2. Center column
    cx, cy = POS_COLUMN
    shapes.extend(build_center_column(cx, cy, z0))

    # 3. Horizontal transfer cylinders (top of column, 2 side-by-side)
    # Mounted on top plate at z0 + COLUMN_H + 15
    top_z = z0 + COLUMN_H + 15
    for dx in [-25, 25]:
        shapes.extend(build_pneumatic_cylinder(
            cx + dx, cy, top_z + 30, body_dia=22, stroke=120, axis="z",
            color=(0.75, 0.12, 0.12)
        ))

    # 4. Vertical transfer cylinder + slide (on column front face)
    # Green slide-type linear actuator
    slide_z = z0 + COLUMN_H * 0.55
    # Vertical guide rails on column
    shapes.extend(build_guide_rail(cx + COLUMN_W/2 + 8, cy, slide_z, length=220, width=10, depth=8, axis="z"))
    # Vertical cylinder body (green)
    shapes.extend(build_pneumatic_cylinder(
        cx + COLUMN_W/2 + 20, cy, slide_z, body_dia=28, stroke=150, axis="z",
        color=(0.15, 0.55, 0.20)  # green
    ))
    # Slide plate
    shapes.append((Pos(cx + COLUMN_W/2 + 20, cy, slide_z + 20) * Box(50, 35, 8), _gray(0.55)))

    # 5. Product gripper (at bottom of vertical slide)
    grip_z = z0 + COLUMN_H * 0.25
    shapes.extend(build_gripper(cx + COLUMN_W/2 + 20, cy, grip_z, w=45, d=30, h=25))

    # 6. Left slide table + positioning system
    lx, ly = POS_LEFT_SLIDE
    shapes.extend(build_slide_table(lx, ly, z0, w=140, d=80, h=20))
    # Guide cylinder (standing on slide table)
    shapes.extend(build_pneumatic_cylinder(
        lx - 30, ly, z0 + 35, body_dia=18, stroke=80, axis="z",
        color=(0.12, 0.45, 0.65)  # blue-ish
    ))
    # Horizontal pushing cylinder (mounted on slide, horizontal)
    shapes.extend(build_pneumatic_cylinder(
        lx + 20, ly, z0 + 35, body_dia=20, stroke=100, axis="x",
        color=(0.82, 0.15, 0.15)
    ))
    # Guide rail for horizontal cylinder
    shapes.extend(build_guide_rail(lx + 20, ly, z0 + 20, length=120, width=8, depth=6, axis="x"))
    # Small sensors on left slide
    for dx in [-60, 60]:
        shapes.append((Pos(lx + dx, ly - 50, z0 + 30) * Box(8, 8, 15), (0.9, 0.3, 0.1)))

    # 7. Vibration bowl (right side)
    vx, vy = POS_VIB_BOWL
    shapes.extend(build_vibration_bowl(vx, vy, z0, od=150, h=90))

    # 8. Linear feeding track (between vibration bowl and center)
    tx, ty = POS_TRACK
    shapes.extend(build_linear_track(tx, ty, z0 + 15, length=200, w=16, d=10))

    # 9. Hopper support + hopper (right rear)
    hx, hy = POS_HOPPER
    shapes.extend(build_hopper_support(hx, hy, z0, w=120, d=120, h=80))
    shapes.extend(build_hopper(hx, hy, z0 + 80 + 15, tw=130, td=130, h=100))

    # 10. Piping & cables
    shapes.extend(build_piping(cx, cy, z0))

    # Colorize all
    colored = []
    for shape, color in shapes:
        shape.color = color
        colored.append(shape)

    return Compound(colored)


def gen_step():
    shape = _build_shape()
    return {
        "step_output": "auto_station_from_image.step",
        "shape": shape,
    }


if __name__ == "__main__":
    shape = _build_shape()
    print(f"Built assembly with {len(list(shape.solids()))} solids")
