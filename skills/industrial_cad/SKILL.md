# 工业自动化产线 CAD精准描述 Skill
# Version: 2.0
# 架构：build123d（零件建模）+ FreeCAD（装配约束求解）+ OCP（几何验证）
# 适用：机械设计、CAD建模、AI生成CAD、车间装配落地

## 核心架构（三层分离）

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1: 零件建模（build123d）                              │
│  ├─ 标准设备: models/automation_parts/*.py → .step           │
│  └─ 非标结构件: 机架/支架/连接板（直接 build123d 建模）        │
├─────────────────────────────────────────────────────────────┤
│  Layer 2: 装配约束（FreeCAD）                                │
│  ├─ 导入零件 STEP → FreeCAD Document                         │
│  ├─ 定义约束（贴合/同轴/平行/距离）→ FreeCAD Assembly         │
│  └─ 约束求解 → 导出装配 STEP                                 │
├─────────────────────────────────────────────────────────────┤
│  Layer 3: 几何验证（OCP）                                    │
│  └─ verify_assembly.py → 干涉/间隙/有效性检查                │
└─────────────────────────────────────────────────────────────┘
```

**关键决策**：
- 零件层继续用 **build123d**（代码简洁、agent 友好、已验证 27+ 零件）
- 装配层引入 **FreeCAD Assembly workbench**（约束求解器替代手动 transform 矩阵）
- 验证层用 **OCP**（与后端无关、已在 verify_assembly.py 实现）
- FreeCAD 版本要求：**≥1.1**（完整约束求解器）。当前 1.0 可通过 Placement+OCP 过渡。

---

## 核心强制结构（固定顺序）
1. 产线名称 & 功能用途
2. 全局坐标系+安装基准（必写）
3. 第三方设备台账：型号/外形/安装孔/复用模型
4. 机械装配约束：贴合、同轴、平行、距离（不再手写坐标）
5. 气动/电气接口位置与规格
6. 紧固件规格、锁紧力矩、加工公差
7. 运动干涉、安全间隙、验收标准

---

## 统一描述规则

### 1. 基准规则
- 必须定义：XY基准面、产线中心X轴、坐标原点、Z轴垂直向上
- 所有部件定位，全部通过**约束系统**自动求解，禁止手写 transform 矩阵硬编码坐标

### 2. 第三方设备规则
每台设备必填：品牌型号、外形长宽高、安装孔规格&孔距、官方3D模型引用名
设备信息注册在 `references/automation-device-lib.md`

### 3. 装配约束标准术语（替代手写坐标）

**固定用词**：贴合、同轴、平行、垂直、中心对齐、面距离、边距

**约束描述格式**（JSON，用于 FreeCAD Assembly）：
```json
{
  "constraints": [
    {
      "type": "PlaneCoincident",
      "part_a": "VibratingBowl",
      "face_a": "bottom",
      "part_b": "BasePlate",
      "face_b": "top"
    },
    {
      "type": "PlaneAlignment",
      "part_a": "GuideCylinder",
      "axis_a": "rod_axis",
      "part_b": "world",
      "axis_b": "z_axis"
    },
    {
      "type": "Distance",
      "part_a": "SensorPick",
      "point_a": "sensor_face",
      "part_b": "VibratingBowl",
      "point_b": "bowl_surface",
      "value": 5.0
    }
  ]
}
```

**约束类型映射**（build123d skill 术语 → FreeCAD Assembly 术语）：
| build123d skill | FreeCAD Assembly | OCP 检查方法 |
|----------------|-----------------|-------------|
| 贴合 | `PlaneCoincident` | 两面距离 < 0.01mm |
| 同轴 | `AxialAlignment` | 两轴夹角 < 0.1° |
| 平行 | `PlaneAlignment` | 两方向夹角 < 0.1° |
| 面距离 | `Distance` | `BRepExtrema_DistShapeShape` |
| 中心对齐 | `CenterOfMass` | 质心距离 < 0.01mm |

#### 3a. 运动关节（Motion Joint）
气动执行机构、滑台、旋转台等运动部件必须在装配描述中标注关节类型：
- **prismatic（移动副）**：气缸、滑台、电缸、夹爪。需指定 `axis` 方向向量、`limits` 行程范围（mm）。
- **revolute（旋转副）**：旋转台、翻转机构。需指定 `axis` 方向向量、`limits` 角度范围（°）。

关节通过独立的 `.joints.json` 文件描述：
```json
{
  "joints": [
    {"part": "h_cylinder", "type": "prismatic", "axis": [1,0,0], "limits": [-100, 100]},
    {"part": "v_cylinder", "type": "prismatic", "axis": [0,0,1], "limits": [0, 200]},
    {"part": "gripper",    "type": "prismatic", "axis": [0,1,0], "limits": [-8, 8]}
  ]
}
```

### 4. 工业通用力矩标准
- M5：8 N·m
- M6：12 N·m
- M8：20~25 N·m
- M10：35~40 N·m
- M12：45~50 N·m

### 5. 公差&形位要求
- 安装孔常规公差：H7
- 框架平行度/垂直度：≤0.1mm/m
- 旋转类部件同轴度：0.05~0.2mm

### 6. 间隙规范
- 固定设备最小间隙：≥5mm
- 运动机构安全间隙：≥20mm
- 检修开门预留间隙：≥30mm

### 7. 管线描述规范
- 电气：线槽固定高度、线径、接口对应关系
- 气动：气管外径、接口规格、管路走向、最小弯曲半径

---

## 工作流（三步）

### Step 1: 零件建模（build123d）
```bash
# 生成标准设备 STEP
./.venv/bin/python skills/cad/scripts/gen_step_part models/automation_parts/<part>.py
```
- 输出：`.step` + `.step/model.glb` + `.step/topology.json`
- 零件源文件必须定义 `gen_step()` 返回 `shape` + `step_output`
- Z=0 为安装基准面

### Step 2: 装配约束（FreeCAD）
```bash
# 约束描述文件：assembly.constraints.json
# 运行 FreeCAD 约束求解
./.venv/bin/python skills/industrial_cad/scripts/freecad_assemble.py \
    --parts-dir models/automation_parts \
    --constraints models/assemblies/<assembly>.constraints.json \
    --output models/assemblies/<assembly>.step
```

约束求解流程：
1. 读取所有零件 STEP
2. 解析约束 JSON
3. 在 FreeCAD 中创建 Assembly + 添加约束
4. 运行约束求解器（solve）
5. 导出装配 STEP

**禁止**：在装配源文件中手写 `instances` + `_t(x,y,z,rx,ry,rz)` transform 矩阵。
**历史兼容**：v1.0 的 `instances` 格式仍可读（用于已生成装配的维护），新装配必须用约束系统。

### Step 3: 几何验证（OCP）
```bash
./.venv/bin/python skills/industrial_cad/scripts/verify_assembly.py \
    models/assemblies/<assembly>.step \
    --min-gap 5.0 \
    --joints models/assemblies/<assembly>.joints.json
```
验证项：
- **几何有效性**：每个零件的 BRep 无退化面/边
- **干涉检测**：零件间实体穿透（交集体积 > 0.1mm³）。面接触（贴合）不计入干涉
- **间隙检查**：非贴合零件对的最短距离 < `min_gap` 时报警告
- **运动包络**（如有 joints.json）：运动部件全行程范围内是否与其他零件干涉

---

## 安装载体与刚性连接规范（强制）
- **所有第三方设备必须通过安装板 / 支架与机架的横梁、立柱或底板进行刚性连接**，严禁仅以坐标定位将设备悬空放置。
- 每个设备必须有明确的安装载体：
  - PLC → PLC 安装板（与机架顶框螺栓固定）
  - 电机 → 电机安装支架（与机架立柱螺栓固定，法兰面贴合支架）
  - 气泵 → 气泵安装平台（与机架立柱焊接或螺栓固定，底座全贴合平台）
  - 气缸 → 气缸安装板（与机架前端立柱螺栓固定，耳座底面贴合）
  - 电磁阀 → 阀安装板（与机架顶框螺栓固定）
- **设备坐标系必须以安装基准面为 Z=0**：零件源文件中，设备的安装底面 / 法兰贴合面必须位于 Z=0（XY 平面）。
- **安装高度必须包含载体厚度**：设备底面坐标 = 载体顶面坐标，不得忽略载体厚度导致悬空。
- 载体与机架之间必须有完整的贴合约束和螺栓连接关系。

---

## 版本演进
- **v1.0**：手动 `instances` + `_t()` transform 矩阵（当前兼容）
- **v2.0**：约束驱动装配（本版本）
  - 零件层：build123d（不变）
  - 装配层：FreeCAD Assembly（新引入）
  - 验证层：OCP verify_assembly.py（已存在）
