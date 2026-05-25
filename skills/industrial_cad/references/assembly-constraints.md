# 装配约束描述格式（FreeCAD Assembly）

约束描述文件为 JSON 格式，与装配输出同名，扩展名 `.constraints.json`。

## 文件结构

```json
{
  "name": "vibratory_feeder",
  "base_frame": {
    "origin": [0, 0, 0],
    "z_up": true
  },
  "parts": [
    {
      "id": "BasePlate",
      "file": "models/automation_parts/feeder_base.step",
      "z_top": 30,
      "fixed": true
    },
    {
      "id": "VibratingBowl",
      "file": "models/automation_parts/vibrating_bowl.step"
    },
    {
      "id": "TransferGantry",
      "file": "models/automation_parts/transfer_column.step"
    }
  ],
  "constraints": [
    {
      "type": "PlaneCoincident",
      "part_a": "VibratingBowl",
      "face_a": "bottom",
      "part_b": "BasePlate",
      "face_b": "top"
    },
    {
      "type": "Distance",
      "part_a": "VibratingBowl",
      "point_a": "origin",
      "part_b": "BasePlate",
      "point_b": "origin",
      "axis": "x",
      "value": 380
    }
  ]
}
```

## 字段说明

### `parts`
零件清单。每个零件必须定义 `id`（唯一标识）和 `file`（STEP 文件路径）。

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | 是 | 零件实例名，用于约束引用 |
| `file` | string | 是 | STEP 文件路径（相对 repo root） |
| `fixed` | boolean | 否 | 是否固定到地面（默认 false） |
| `z_top` | number | 否 | 零件顶面 Z 坐标（用于约束求解初始猜测） |

### `constraints`
约束数组。FreeCAD Assembly 按顺序求解。

#### PlaneCoincident（面贴合）
两个平面重合（法向相反或相同）。用于"零件底面贴合底座顶面"。

```json
{
  "type": "PlaneCoincident",
  "part_a": "VibratingBowl",
  "face_a": "bottom",
  "part_b": "BasePlate",
  "face_b": "top"
}
```

`face_a`/`face_b` 取值：
- `"top"` / `"bottom"` — Z 轴方向最大/最小面
- `"front"` / `"back"` — Y 轴方向最大/最小面
- `"left"` / `"right"` — X 轴方向最大/最小面
- `"face_N"` — 第 N 个面（通过拓扑索引）

#### PlaneAlignment（面平行/轴对齐）
两个方向平行。用于"气缸轴线与 Z 轴平行"。

```json
{
  "type": "PlaneAlignment",
  "part_a": "GuideCylinder",
  "axis_a": "rod_axis",
  "part_b": "world",
  "axis_b": "z_axis"
}
```

`axis_a`/`axis_b` 取值：
- `"x_axis"` / `"y_axis"` / `"z_axis"` — 零件局部坐标轴
- `"rod_axis"` — 气缸/活塞杆轴线（需零件预定义）
- `world` — 全局坐标系

#### AxialAlignment（同轴）
两个轴线重合。用于"电机输出轴与负载同轴"。

```json
{
  "type": "AxialAlignment",
  "part_a": "ServoMotor",
  "axis_a": "shaft_axis",
  "part_b": "Roller",
  "axis_b": "shaft_axis"
}
```

#### Distance（距离）
两点/两面之间的距离约束。用于"传感器距料斗表面 5mm"。

```json
{
  "type": "Distance",
  "part_a": "SensorPick",
  "point_a": "sensor_face",
  "part_b": "VibratingBowl",
  "point_b": "bowl_surface",
  "axis": "z",
  "value": 5.0
}
```

#### CenterOfMass（中心对齐）
两个零件的质心在指定轴上对齐。用于"气缸中心与支架中心在 X 方向对齐"。

```json
{
  "type": "CenterOfMass",
  "part_a": "HorizontalPushCylinder",
  "part_b": "PushSlide",
  "axis": "x"
}
```

#### Fix（固定）
将零件固定在当前位置（相对于全局坐标系）。通常用于底座。

```json
{
  "type": "Fix",
  "part": "BasePlate"
}
```

## 约束求解顺序

FreeCAD Assembly 按约束数组顺序求解。推荐顺序：
1. **Fix** 底座（提供全局锚点）
2. **PlaneCoincident** 主要贴合面（确定 Z 位置）
3. **CenterOfMass** / **Distance** 平面位置（确定 X/Y 位置）
4. **PlaneAlignment** / **AxialAlignment** 方向约束（确定旋转）
5. **Distance** 间隙微调

## 与 `.joints.json` 的关系

- `.constraints.json`：描述**静态装配约束**（零件之间如何固定连接）
- `.joints.json`：描述**运动关节**（哪些零件可以动、动的方向和范围）

两者独立但互补。约束求解器先确定静态装配姿态，验证脚本再用 joints 做运动包络检查。

## FreeCAD 版本差异

| 版本 | 约束能力 | 说明 |
|------|---------|------|
| FreeCAD 1.0 | 基础 Placement + OCP | 无完整约束求解器，需脚本辅助计算 Placement |
| FreeCAD 1.1 | 完整 Assembly workbench | 支持全部约束类型 + solve + 过约束检测 |

当前过渡方案：脚本读取 `.constraints.json`，用 OCP 几何算法计算每个零件的 Placement，然后在 FreeCAD 中应用。等 FreeCAD 1.1 正式发布后，直接调用 Assembly workbench 的约束求解器。
