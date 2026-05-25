# cad-asm Standard Parts Library (STEP)

This directory contains pre-built STEP models for common automation standard parts,
organized by category. All files are symlinked from `models/automation_parts/`.

## Categories

| Category | Parts |
|----------|-------|
| `pneumatic/` | air_pump, pneumatic_cylinder, large_cylinder, solenoid_valve, air_tube_6mm |
| `electrical/` | plc_module, servo_motor, terminal_block, din_rail, photo_sensor, proximity_sensor, sensor_cable |
| `mechanical/` | gripper, linear_guide, push_slide, roller, vibrating_bowl, feeder_base, transfer_column, work_platform |
| `structural/` | frame_base, mounting_plate, small_base_plate, cylinder_bracket, roller_bracket |
| `fasteners/` | bolt_m6x20, bolt_m8x25, hex_nut_m6, flat_washer_m6 |
| `conveyor/` | cable_tray_channel |

## Usage

From Python:
```python
from cad_asm.library import build_library_part
part = build_library_part("step_plc_module", {})
```

From CLI:
```bash
python -m cad_asm.cli lib-search "PLC"
python -m cad_asm.cli lib-list
```

From assembly task JSON:
```json
{
  "source": {"type": "step", "path": "cad_asm/lib/electrical/plc_module.step"}
}
```
