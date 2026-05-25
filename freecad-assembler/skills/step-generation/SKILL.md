---
name: step-generation
description: FreeCAD 生成并导出 STEP/STP 的执行 skill。用于把用户建模需求转成可运行 Python，并稳定产出 models/step 下的文件。
triggers:
  - step
  - stp
  - 导出step
  - 导出stp
  - 生成step
  - generate step
---

# Step Generation Skill

用于“自然语言 -> FreeCAD Python -> STEP/STP 文件”全过程。

## Execution Rules

1. 代码必须可在 FreeCADCmd 下执行，禁止依赖网络或外部私有路径。
2. 脚本至少包含：
- `import FreeCAD as App`
- `import Part`
3. 脚本必须创建可导出的实体对象，并完成 `doc.recompute()`。
4. 优先让 runner 统一导出；脚本中允许本地导出日志，但不能影响主流程。
5. 输出命名应稳定可追踪，文件名仅包含安全字符。
6. 若用户要求是简单几何（如立方体/圆柱），优先输出最小可运行脚本。

## Output Contract

- 返回 JSON 字段：`summary`, `file_name`, `assumptions`, `code`
- `code` 必须是完整 Python 脚本，不能是伪代码。
