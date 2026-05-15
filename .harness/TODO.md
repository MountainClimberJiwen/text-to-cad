# industrial_cad Skill — 演进路线图

> 记录所有已讨论、有潜力但尚未 fully implement 的方向。
> 已固化的架构：build123d（零件建模）+ FreeCAD（装配约束）+ OCP（几何验证）

---

## P0 — 当前 sprint 优先级（已完成框架，待完善）

### 1. verify_assembly.py（几何验证）
- [x] 基础框架：干涉检测（BRepAlgoAPI_Common + 体积过滤）
- [x] 基础框架：间隙检查（BRepExtrema_DistShapeShape）
- [x] 基础框架：几何有效性（BRepCheck_Analyzer）
- [x] 支持直接 STEP 输入（不仅限于 Python 装配源）
- [x] 运动关节识别（--joints 参数 + .joints.json）
- [ ] **运动包络检查**：对 prismatic/revolute 关节，沿 axis 方向在 limits 范围内采样多个姿态，检查全行程干涉
- [ ] **包围盒快速排除优化**：当前 bbox 检查逻辑较保守，可优化以跳过更多无关零件对
- [ ] **导出格式验证**：STEP 输出后检查 `ISO-10303-21` header；渲染图检查非空白（借鉴 `vendor/cli-anything-freecad/test_full_e2e.py`）

### 2. FreeCAD 装配约束集成（路 B 架构）
- [x] 架构决策固化：build123d（零件）+ FreeCAD（装配约束）+ OCP（验证）
- [x] freecad_assemble.py 过渡框架（FreeCAD 1.0 Placement + OCP）
- [x] .constraints.json 格式定义
- [x] vibratory_feeder_assembly.constraints.json 示例
- [ ] **FreeCAD 1.1 升级**：当前 1.0 的 Assembly workbench 约束 API 不完整，等 1.1 后改用原生约束求解器（PlaneCoincident → solve → Placement）
- [ ] **约束求解正确性**：当前过渡实现的 PlaneCoincident 只做了面中心对齐，未处理法向翻转，导致 Placement 值不准确
- [ ] **约束冲突诊断**：FreeCAD solve 失败时，输出具体冲突的约束对

---

## P1 — 近期高价值方向

### 3. Auto-Reason 自我纠正系统
> 核心：约束知识库 + 生成→验证→修复→学习的反馈循环

- [ ] **约束知识库**（`skills/industrial_cad/.knowledge/`）：
  - patterns.json：零件类型 → 约束模板映射（如 cylinder+bracket → [PlaneCoincident, AxialAlignment]）
  - fixes.json：失败模式 → 修复策略记录（如 "clearance_below_threshold" → Distance.value × 1.5）
- [ ] **约束生成器**：读取零件清单 → 查询知识库 → 自动生成初始 .constraints.json
- [ ] **反馈分析器**：解析 verify_assembly.py JSON 报告，分类失败类型（interference / clearance / unsat / geometry_issue）
- [ ] **约束修复器**：
  - 间隙不足 → 增大 Distance
  - 实体穿透 → 添加 offset 或改为 Distance
  - FreeCAD solve 失败 → SMT 诊断冲突约束
- [ ] **迭代循环**：生成 → 求解 → 验证 → 自动修复（最多 3 轮）→ 人工介入
- [ ] **Session snapshot**：每次修改 constraints 前 deepcopy 保存，修复失败时一键回退（借鉴 `vendor/cli-anything-freecad/session.py`）
- [ ] **跨项目迁移**：知识库存储在 skill 级别，所有项目共享学习成果

### 4. SMT/Z3 约束诊断层
> 作为 FreeCAD 约束求解器的补充/backup，用于白盒诊断

- [ ] **约束建模**：将装配约束转化为 Z3 实数变量 + 约束公式
  - 变量：每个零件的 6 DOF（x, y, z, rx, ry, rz）
  - PlaneCoincident → z_offset = target_z
  - Distance → x_diff = target_value
- [ ] **过约束检测**：solver.check() == unsat 时，定位冲突约束对
- [ ] **欠约束检测**：solver.check() == sat 但存在自由变量 → 提示哪些零件 DOF 未锁定
- [ ] **多解枚举**：枚举可行装配姿态，推荐最小占地面积/最紧凑布局
- [ ] **与 FreeCAD 的集成**：SMT 给出初始猜测 → FreeCAD 精调 → 输出 STEP

### 5. URDF 集成
> URDF 与 industrial_cad 概念同构（link=零件, joint=约束/关节, origin=Placement）

- [ ] **constraints.json ↔ URDF 双向转换器**：
  - PlaneCoincident → `<joint type="fixed">`
  - prismatic → `<joint type="prismatic">` + `<limit>`
  - revolute → `<joint type="revolute">` + `<limit>`
- [ ] **PyBullet 运动仿真验证**：加载 URDF → 驱动关节全行程 → 检测瞬时碰撞（比静态 OCP 检查更严格）
  - 验证 h_cylinder 从 -100 到 100 的运动包络
  - 验证 v_cylinder 从 0 到 200 的升降轨迹
- [ ] **RViz 可视化**：ROS 数字孪生直接从同一套约束数据生成
- [ ] **URDF parent-child 层级优化约束求解**：借用 URDF 的树结构做 forward kinematics，修改父零件位置时子零件自动跟随

---

## P2 — 中期扩展方向

### 6. 装配描述中间层（JSON/DSL）
> 降低 agent 出错率，减少从文本模板到代码的手动转换

- [ ] **装配描述 DSL**：结构化表达设备清单、位置、约束（比手写 `_t()` 矩阵更安全）
- [ ] **line-assembly-template.md → DSL 自动解析**：把填空模板转成机器可读的 JSON
- [ ] **DSL → build123d Python 自动生成**：agent 写 DSL，脚本自动输出 gen_step() 代码
- [ ] **版本 diff 友好**：DSL JSON 的 diff 比 Python 代码的 diff 更易读

### 7. TechDraw / 工程图
> FreeCAD 独有的能力，build123d 无法替代

- [ ] **从 STEP 自动生成 2D 工程图**：
  - 三视图（前视/俯视/左视）
  - 等角视图
  - 关键尺寸标注（从约束 JSON 中提取 Distance/offset）
- [ ] **DXF/PDF 导出**：用于车间装配指导
- [ ] **与装配约束联动**：修改约束后工程图自动更新

### 8. 零件库标准化
- [ ] **automation-device-lib.md 自动化注册**：新增零件通过 gen_step_part 后自动提取参数写入注册表
- [ ] **零件参数校验脚本**：检查新零件是否满足 Z=0 基准、安装孔、BRep 有效性等规范
- [ ] **零件搜索/推荐**：根据外形尺寸自动推荐最接近的标准件

---

## P3 — 长期/探索性方向

### 9. 形式化验证（Coq / Lean）
> 证明约束求解器本身的正确性

- [ ] **PlaneCoincident 正确性证明**：如果两平面法向相反且中心重合，则 distance = 0
- [ ] **约束求解完备性**：证明求解器在有限步内终止
- [ ] **适用条件**：仅在 skill 平台化、面向安全关键行业（航空/核电）时引入
- [ ] **当前判断**：过度设计，暂不实施

### 10. Session / 状态管理
> 模式借鉴：`vendor/cli-anything-freecad/session.py` 的 deepcopy snapshot + FIFO limit

- [ ] **装配状态快照**：保存/恢复装配的 constraints + placements（比 git 更轻量）
- [ ] **undo/redo 链**：迭代过程中的安全回退
- [ ] **分支探索**：同时维护多个约束方案（A/B test）

### 11. FEM / CAM 集成
- [ ] **有限元分析**：从装配 STEP 导出 → FreeCAD FEM → 应力/变形分析（大型框架结构）
- [ ] **加工路径生成**：CAM workbench 生成非标零件的 G-code
- [ ] **适用条件**：仅当项目从"设计"阶段进入"制造"阶段时引入

---

## 已完成（v2.0 里程碑）

- [x] SKILL.md v2.0：三层架构固化
- [x] README.md 同步更新
- [x] verify_assembly.py（干涉+间隙+几何有效性）
- [x] freecad_assemble.py（过渡框架）
- [x] assembly-constraints.md（约束格式规范）
- [x] automation-device-lib.md（14 个设备注册）
- [x] vibratory_feeder_assembly.constraints.json（示例）
- [x] vibratory_feeder_assembly.joints.json（5 个运动关节）

---

## 关键依赖

| 依赖 | 当前状态 | 阻塞项 |
|------|---------|--------|
| FreeCAD 1.1 | 未发布（当前 1.0.2） | 完整 Assembly 约束求解器 |
| z3-solver | 未安装 | SMT 诊断层 |
| PyBullet | 未安装 | URDF 运动仿真 |
| ROS/RViz | 未安装 | 数字孪生可视化 |

---

## 决策记录

**2026-05-11**：固化路 B 架构（build123d + FreeCAD + OCP），不切换零件建模层到 FreeCAD。
**2026-05-11**：确认 Coq 形式化验证当前过度设计，暂不引入。
**2026-05-11**：确认 SMT/Z3 作为诊断层有补充价值，优先级低于 FreeCAD 1.1 升级。
**2026-05-11**：确认 URDF 作为装配描述转换格式和运动仿真验证有明确价值。
**2026-05-07**：cli-anything-freecad 深度分析完成。结论：它没有专门的"矫正设计"机制，验证层很浅（仅参数正性+文件存在性）。但其 JSON→Macro→Headless 管道、deferred measurement、session snapshot 模式有参考价值。详见 `vendor-analysis-cli-anything-freecad.md`。
