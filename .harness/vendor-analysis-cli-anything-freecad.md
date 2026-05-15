# CLI-Anything-FreeCAD 深度分析 — 可借鉴与不可借鉴

> 研究目标：cli-anything-freecad 是否有"矫正设计"机制，哪些模式可迁移到 industrial_cad skill。
> 代码来源：`skills/industrial_cad/vendor/cli-anything-freecad/`
> 结论：**它没有专门的矫正设计机制**，但其 JSON→Macro→Headless 管道和 deferred measurement 模式有参考价值。

---

## 一、cli-anything-freecad 架构概览

```
JSON project state ──► freecad_macro_gen.py ──► .py macro ──► freecadcmd ──► .FCStd/STEP/STL
        │                                            │
        ▼                                            ▼
  Session (undo/redo)                      export_headless()
  Measure (deferred)                         └── verify: file exists,
  Parts/Sketch/Body                              size > 0, magic bytes
```

**本质**：一个轻量级的 **JSON state 到 FreeCAD macro 的桥梁**，而非完整的 CAD 约束求解器。

### 数据模型

```json
{
  "version": "1.0",
  "name": "project",
  "parts": [{"id":0, "name":"Box", "type":"box", "params":{}, "placement":{}}],
  "sketches": [],
  "bodies": [],
  "materials": [],
  "boolean_ops": [],
  "measurements": []
}
```

---

## 二、它的"验证"机制有多深？

### 2.1 宏观验证（export_headless）

在 `freecad_backend.py` 的 `export_headless()` 中，验证只到文件级别：

- ✅ 宏执行返回码 == 0
- ✅ 输出文件存在
- ✅ 文件大小 > 0
- ✅ 格式 magic bytes 正确（STEP: `ISO-10303-21`, STL: `solid`/binary header, PNG: `\x89PNG`）

**评价**：这是"输出是否生成"的验证，不是"几何是否正确"的验证。

### 2.2 微观验证（check_geometry）

在 `measure.py` 的 `check_geometry()` 中，验证只到参数级别：

- ✅ 零件类型在 `PRIMITIVES` 中
- ✅ 数值参数 > 0（angle 除外）
- ✅ placement 包含 position 和 rotation

**评价**：这是"数据是否合法"的验证，不是"几何是否有效"的验证。没有 BRep validity、没有干涉检测、没有间隙检查。

### 2.3 装配约束（assembly.py）

```python
def solve_assembly(project, asm_index):
    assembly["solved"] = True
    dof = max(0, 6 * num_components - num_constraints)
    return {"solved": True, "dof": dof}
```

**评价**：`solve_assembly()` 只是一个**标记函数**。它用 `6N - C` 估算自由度，**完全没有实际求解**。真正的约束求解依赖 FreeCAD 1.1 Assembly workbench 的 macro 生成。

---

## 三、可借鉴的模式

### 3.1 ✅ JSON State → Macro Generation → Headless Execution

**文件**：`freecad_macro_gen.py`

cli-anything-freecad 的核心创新是将所有操作累积到一个 JSON state，然后一次性生成完整的 FreeCAD Python macro，通过 `freecadcmd` 无头执行。

```python
# 我们的 freecad_assemble.py 是直接写 Python 脚本然后调用 subprocess
# cli-anything-freecad 的方式是：中间 JSON → 宏生成器 → 宏执行
```

**借鉴价值**：
- **解耦**：JSON state 是稳定的中间表示，不依赖任何 Python 包版本
- **可调试**：生成的 `.py` macro 可以直接在 FreeCAD GUI 中打开调试
- **可复现**：同样的 JSON 总是生成同样的 macro
- **我们的场景**：`.constraints.json` 已经是中间表示，但可以借鉴 macro 生成模式，让 `freecad_assemble.py` 不再直接调用 FreeCAD API，而是生成 macro 后执行

### 3.2 ✅ Deferred Measurement（延迟测量）

**文件**：`measure.py` 的 `deferred` 标记

对于简单几何（box/cylinder/sphere），在纯 Python 层面用公式直接计算体积/面积/bbox。对于复杂几何（boolean 结果、compound），标记为 `deferred=True`，在 macro 执行后解析。

```python
# 简单几何 → 直接计算
if t == "box":
    volume = length * width * height
    return {"volume": volume, "deferred": False}

# 复杂/未知几何 → 延迟到 macro 执行后
return {"volume": None, "deferred": True}
```

**借鉴价值**：
- 我们的 `verify_assembly.py` 目前对所有输入都做完整的 OCP BRep 分析（heavy）
- 对于简单 box/cylinder，可以用公式快速估算 bbox 和体积，跳过 BRep 解析
- 对于 boolean 结果，保持 OCP 分析不变

### 3.3 ✅ Session Undo/Redo 快照

**文件**：`session.py`

```python
class Session:
    MAX_UNDO = 50
    def snapshot(self, description=""):
        self._undo_stack.append({"timestamp": time.time(), "state": copy.deepcopy(project)})
    def undo(self):
        # pop undo, push current to redo
```

**借鉴价值**：
- 我们的 Auto-Reason 迭代循环（生成→求解→验证→修复）需要安全回退
- 在每次修改 `.constraints.json` 前做 snapshot，修复失败时一键回退
- 可以扩展到"分支探索"：同时维护多个约束方案 A/B

### 3.4 ✅ Export Format Verification（格式验证）

**文件**：`test_full_e2e.py` 的 `_assert_png`, `_assert_images_differ`

```python
def _assert_png(path):
    with open(path, "rb") as fh:
        assert fh.read(8) == PNG_MAGIC

def _assert_png_not_blank(path):
    image = Image.open(path).convert("L")
    assert image.getextrema() != (255, 255)  # 不是全白
```

**借鉴价值**：
- 我们的 `verify_assembly.py` 输出 JSON 报告后，可以加入"报告非空"和"关键字段存在"的检查
- FreeCAD 导出 STEP 后，可以检查 STEP header 是否为 `ISO-10303-21`
- 渲染 review image 后，可以检查 PNG 不是全白/全黑（防止渲染失败但文件存在）

### 3.5 ✅ Multi-format Export

cli-anything-freecad 支持 STEP / IGES / STL / OBJ / BREP / FCStd，通过一个统一的 `generate_macro()` 接口：

```python
def generate_macro(project, output_path, export_format="step"):
    sections = [
        _gen_header(),      # imports + newDocument
        _gen_parts(),       # Part primitives
        _gen_boolean_ops(), # Cut/Fuse/Common
        _gen_bodies(),      # PartDesign bodies
        _gen_placements(),  # Position/rotation
        _gen_export(),      # Part.export / Mesh.export / doc.saveAs
    ]
```

**借鉴价值**：
- 我们的 `freecad_assemble.py` 目前只输出 STEP 和 FCStd
- 可以扩展为同时输出 STL（用于 3D 打印）、BREP（用于精确几何交换）
- 但优先级不高，STEP 已满足当前需求

---

## 四、不可借鉴 / 已被超越的部分

### 4.1 ❌ Assembly Constraint Solving

cli-anything-freecad 的 `assembly.py` 只是一个 JSON 结构管理器：
- 支持定义约束（fixed/coincident/distance/angle/parallel/...）
- 支持 motion joint（revolute/prismatic/...）
- 但 `solve_assembly()` 只是估算 DOF，**没有真正求解**

**我们的状态**：
- `freecad_assemble.py` 已经有了基于 OCP + Placement 的过渡求解器（虽然有 bug）
- 等 FreeCAD 1.1 后，我们的求解器将远强于 cli-anything-freecad 的标记函数

### 4.2 ❌ Geometry Validation Depth

cli-anything-freecad 的 `check_geometry()` 只检查参数正性，而我们的 `verify_assembly.py`：
- BRep validity（BRepCheck_Analyzer）
- Interference detection（BRepAlgoAPI_Common + 体积过滤）
- Clearance check（BRepExtrema_DistShapeShape）
- Face-contact vs real penetration 区分

**结论**：我们在几何验证层已经超越了 cli-anything-freecad。

### 4.3 ❌ Motion Envelope / 运动包络

cli-anything-freecad 的 motion 只是 JSON 记录（`create_simulation()`, `add_simulation_step()`），没有实际的运动仿真或包络检查。

**我们的状态**：
- `.joints.json` 已定义 5 个运动关节
- `verify_assembly.py` 的 `--joints` 参数框架已就位
- 下一步是采样关节 limit 范围内的多个姿态，检查全行程干涉

---

## 五、对 industrial_cad 的具体建议

### 立即可做的（P0-P1）

| 建议 | 优先级 | 工作量 | 说明 |
|------|--------|--------|------|
| **Macro generation 模式** | P1 | 中等 | 让 `freecad_assemble.py` 从"直接调用 FreeCAD API"改为"生成 macro + 执行"，提升可调试性 |
| **Deferred measurement** | P1 | 小 | `verify_assembly.py` 对简单 primitive 用公式快速算 bbox，跳过 BRep 解析 |
| **Session snapshot** | P1 | 小 | Auto-Reason 循环每次修改 constraints 前做 deepcopy snapshot |
| **Export format verify** | P0 | 极小 | STEP 输出后检查 header、渲染图检查非空白 |

### 不做的

| 方向 | 原因 |
|------|------|
| 引入 cli-anything-freecad 的 `assembly.py` 约束模型 | 它只有 JSON 结构管理，没有求解能力，不如等 FreeCAD 1.1 |
| 用它的 `check_geometry()` 替代我们的验证 | 深度太浅，无 BRep/干涉/间隙检查 |
| 完全切换到它的 JSON state 模型 | 我们的 `.constraints.json` + build123d 零件层已经足够表达力 |

---

## 六、关键代码索引

| 文件 | 功能 | 借鉴价值 |
|------|------|---------|
| `freecad_macro_gen.py` | JSON → FreeCAD macro 生成 | ⭐⭐⭐ 高 |
| `freecad_backend.py` | freecadcmd 调用 + export verify | ⭐⭐ 中 |
| `session.py` | undo/redo + 持久化 | ⭐⭐ 中 |
| `measure.py` | 测量 + deferred 标记 | ⭐⭐ 中 |
| `parts.py` | 零件增删改 + bbox 计算 | ⭐ 低（我们的零件层在 build123d） |
| `assembly.py` | 装配约束 JSON 管理 | ❌ 无求解能力 |
| `body.py` | PartDesign body 特征 | ⭐⭐ 中（TechDraw 方向可参考） |
| `test_full_e2e.py` | E2E 测试 + 格式验证 | ⭐⭐ 中 |

---

*分析时间：2026-05-07*
*分析人：Kimi Code CLI*
