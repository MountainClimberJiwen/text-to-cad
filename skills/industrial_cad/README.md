# Industrial CAD Skill

工业自动化产线 CAD 装配设计 Skill，采用 **build123d（零件建模）+ FreeCAD（装配约束求解）+ OCP（几何验证）** 三层架构。

## Architecture

```
零件建模      装配约束         几何验证
build123d  →  FreeCAD 1.1  →  OCP (verify_assembly.py)
   .py          .constraints.json      .step
   ↓            ↓                      ↓
  .step       .step (solved)         报告
```

- **零件层**：build123d 快速生成标准设备 STEP，代码简洁，agent 友好
- **装配层**：FreeCAD Assembly workbench 约束求解，替代手动 transform 矩阵
- **验证层**：OCP 几何算法检查干涉/间隙/有效性，与后端无关

## What It Can Do

- 定义工业自动化产线的**全局基准坐标系**和**安装基准**
- 引用**标准第三方设备台账**：PLC、伺服电机、气泵、气缸、传感器、直线滑台等
- 应用**机械装配约束**：贴合、同轴、平行、垂直、中心对齐、面距离（通过 FreeCAD 约束求解器自动定位）
- 规范**电气/气动接口**位置、规格和管路走向
- 提供**产线装配约束描述模板**，输出结构统一、可直接用于 CAD 建模落地
- 定义**紧固件力矩、加工公差、间隙规范、验收标准**

## Workflow

1. **零件建模**：`./.venv/bin/python skills/cad/scripts/gen_step_part models/automation_parts/<part>.py`
2. **装配约束**：`./.venv/bin/python skills/industrial_cad/scripts/freecad_assemble.py --constraints ...`
3. **几何验证**：`./.venv/bin/python skills/industrial_cad/scripts/verify_assembly.py <assembly>.step`

## References

- [工业自动化设备标准化参考库](references/automation-device-lib.md)
- [装配约束描述格式](references/assembly-constraints.md)
- [产线装配描述模板](references/line-assembly-template.md)

## Requirements

- Python 3.10+ with build123d + OCP (`./.venv/bin/python`)
- FreeCAD ≥1.1（完整 Assembly 约束求解器）
  - FreeCAD 1.0 可通过 Placement+OCP 过渡（约束求解能力有限）

## Project Harness

For agent-facing workflow rules, use [SKILL.md](SKILL.md).
