# freecad-assembler work notes

- repo_path: `/Users/jiwen/PycharmProjects/freecad-assembler`
- skill_name: `freecad-assembler-project`

> Auto-appended from Codex session sync. Do not edit old entries in place; add follow-up notes below.
## 2026-04-08T17:14:07+08:00 · Codex session `019d6c1d-887e-7223-adb6-30b04d4311bd`
- completion: `task_complete`
- session_start: `2026-04-08T16:02:48+08:00`
- last_event: `2026-04-08T17:14:07+08:00`
- cwd: `/Users/jiwen/PycharmProjects/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/04/08/rollout-2026-04-08T16-02-48-019d6c1d-887e-7223-adb6-30b04d4311bd.jsonl`
- summary:
  已按你的要求接入：`Word` 解析继续在后端完成，并把 `word skill` 放进当前项目让 agent runtime 可用。
  已完成：
  - 新增 skill 文件
  [SKILL.md](/Users/jiwen/PycharmProjects/freecad-assembler/skills/word-parser/SKILL.md)
  - runtime 自动启用 skill
  在 [server.js](/Users/jiwen/PycharmProjects/freecad-assembler/server.js) 里：
  - 有 `wordContext` 时启用 `word-parser`
  - 始终启用 `urs-manual`
  - 两个 skill 内容会一起注入 LLM 的系统上下文（`Runtime skills` 段）
  - `invokedSkills` / memory 记录也会带上真实启用的 skill 列表
  - 输入链路保持后端解析
  前端仍先调用 `/api/word/parse`，再把 `wordContext + 用户需求` 发到 `/api/agent/chat`。
  校验情况：
  - `node --check server.js` 通过
  - 代码检索确认 `word-parser` 已接入 runtime
  - 我这边无法在当前沙箱里直接拉起服务做在线联调（端口监听受限），你本地重启后即可验证
  你可以直接测：
  1. 上传 Word
  2. 提问题
  3. 看 `/api/agent/chat` 返回里的 `invokedSkills` 是否包含 `word-parser`。
## 2026-04-06T09:43:39+08:00 · Codex session `019d6074-97c4-7060-98c6-3527f49b73e0`
- completion: `task_complete`
- session_start: `2026-04-06T09:42:27+08:00`
- last_event: `2026-04-06T09:43:39+08:00`
- cwd: `/Users/jiwen/PycharmProjects/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/04/06/rollout-2026-04-06T09-42-27-019d6074-97c4-7060-98c6-3527f49b73e0.jsonl`
- summary:
  1) Latest Progress Highlights
  - 最近 8 次提交显示项目主线在持续打磨前端与 3D 预览体验：包括 STEP 模型居中、桌面布局高度/聊天可见性、相机视角防裁剪，以及默认模型切换。
  - 从当前工作区状态看，仓库本身已存在较多未提交改动（`src/`、`server.js`、`dist/`、`models/`、`scripts/` 等），说明项目处于活跃迭代阶段；本次仅对 `harness` 做了定向清空，没有触碰其他目录内容。
  2) Current Status
  - `done`：已按要求清空 `harness` 文件夹内容，且保留了 `harness` 目录本身。
  - 执行与检查结果：
    - `codex --version` -> `codex-cli 0.118.0`
    - `git rev-parse --is-inside-work-tree` -> `true`
    - `find harness -mindepth 1 -delete` -> 执行成功
    - `ls -la harness` -> 仅剩 `.` 和 `..`，目录为空
    - `git status --short harness` / `git diff --name-status -- harness` -> 6 个已跟踪文件标记为删除
  - 本次变更文件（删除）：
    - `harness/DEVELOPER.MD`
    - `harness/LLM-MODELS.MD`
    - `harness/QA.MD`
    - `harness/UX.MD`
    - `harness/WORKFLOW.MD`
    - `harness/config.toml`
  3) Next Suggested Actions
  1. 若你要保留空目录可跟踪，新增 `harness/.gitkeep` 后再提交。
  2. 运行一次你常用的项目检查（如 `npm run lint` / `npm test`），确认现有大工作区改动与本次删除一起不会影响流程。
  3. 按任务范围提交：`git add -A harness && git commit -m "chore: clear harness directory contents"`（避免把无关改动一起提交）。
## 2026-04-02T23:29:02+08:00 · Codex session `019d4d0b-a0f5-7940-ab07-f446b340ea57`
- completion: `task_complete`
- session_start: `2026-04-02T15:15:00+08:00`
- last_event: `2026-04-02T23:29:02+08:00`
- cwd: `/Users/jiwen/PycharmProjects/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/04/02/rollout-2026-04-02T15-15-00-019d4d0b-a0f5-7940-ab07-f446b340ea57.jsonl`
- summary:
  已加好，前后端都支持“下载当前 STEP 模型”。
  改动内容：
  - 后端新增下载接口
    `GET /api/models/:fileName/download`
    位置：[server.js](/Users/jiwen/PycharmProjects/freecad-assembler/server.js)
    - 做了文件名安全校验（只允许 `basename`，只允许 `.step/.stp`）
    - 文件不存在返回 `404`
    - 通过 `res.download(...)` 返回附件下载头
  - 前端新增下载按钮（在 step view 右上角）
    位置：[StepViewer.vue](/Users/jiwen/PycharmProjects/freecad-assembler/src/components/StepViewer.vue)
    - 按当前已加载模型 `currentFileName` 生成下载 URL
    - 点击直接触发下载
    - 没有可下载模型时按钮禁用
  - 样式新增按钮定位
    位置：[styles.css](/Users/jiwen/PycharmProjects/freecad-assembler/src/styles.css)
  验证结果：
  - 下载接口已验证返回附件头：
    - `status: 200`
    - `content-disposition: attachment; filename="...step"`
  - 页面按钮已验证存在，且在真实桌面浏览器里可用（非禁用）。
  - 我已重启了本地 `dev` 服务以确保后端改动生效。
## 2026-04-02T15:02:31+08:00 · Codex session `019d4444-54fb-7b71-883a-e691fb60688b`
- completion: `task_complete`
- session_start: `2026-03-31T22:20:22+08:00`
- last_event: `2026-04-02T15:02:31+08:00`
- cwd: `/Users/jiwen/PycharmProjects/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/03/31/rollout-2026-03-31T22-20-22-019d4444-54fb-7b71-883a-e691fb60688b.jsonl`
- summary:
  已按 `harness/WORKFLOW.MD` 完成这个需求，功能已生效。
  实现内容：
  - 后端新增自动清理逻辑（1 天保留）：
    - 清理目录：
    - `models/step` 下生成的 `.step/.stp`
    - `scripts/freecad` 下生成的 `.py`
    - 清理条件：
    - 文件名匹配生成命名（`_*14位时间戳*`），且 `mtime > 24h`
    - 保护文件不删：
    - `_generated_freecad_runner.py`
    - `build_laser_gantry.py`
  - 执行时机：
    - 服务启动时执行一次
    - 每次生成 STEP 前再执行一次
  修改文件：
  - [server.js](/Users/jiwen/PycharmProjects/freecad-assembler/server.js)
  - [harness/QA.MD](/Users/jiwen/PycharmProjects/freecad-assembler/harness/QA.MD)
  QA 实测：
  - 我创建了两个 2 天前的测试文件：
    - `models/step/test_cleanup_20240101000000.step`
    - `scripts/freecad/test_cleanup_20240101000000.py`
  - 重启服务后，两者都被自动删除。
  - 保护文件 `scripts/freecad/_generated_freecad_runner.py` 仍在。
  Git：
  - 已提交：`5131be5`
  - 提交信息：`feat(cleanup): auto-delete generated STEP and python files older than 1 day`
## 2026-03-31T17:19:10+08:00 · Codex session `019d4285-501c-7800-9b10-c991123d7a8e`
- completion: `task_complete`
- session_start: `2026-03-31T14:12:06+08:00`
- last_event: `2026-03-31T17:19:10+08:00`
- cwd: `/Users/jiwen/PycharmProjects/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/03/31/rollout-2026-03-31T14-12-06-019d4285-501c-7800-9b10-c991123d7a8e.jsonl`
- summary:
  已完成，提交是 `d5a18a7 Generate and preview FreeCAD STEP models`，当前 `git status` 干净。
  核心改动在 [server.js](/Users/jiwen/PycharmProjects/freecad-assembler/server.js) 和 [StepViewer.vue](/Users/jiwen/PycharmProjects/freecad-assembler/src/components/StepViewer.vue)。`/api/freecad/generate` 现在不再只是返回代码，而是会：
  1. 调用 LLM 生成 FreeCAD Python 装配脚本。
  2. 把脚本落到 `scripts/freecad/`。
  3. 用本地 `FreeCADCmd` 执行脚本并统一导出 `FCStd` 和 `STEP`。
  4. 把新生成的 STEP 文件信息返回前端。
  前端在点击“生成 FreeCAD 代码”后，会自动刷新模型列表并直接加载新生成的 STEP，所以用户输入 query 后会直接在 StepViewer 里看到模型。
  文档也更新了，在 [LLM-MODELS.MD](/Users/jiwen/PycharmProjects/freecad-assembler/harness/LLM-MODELS.MD) 说明了新的返回结构、`FREECAD_CMD` 配置，以及“生成脚本 -> 本地 FreeCAD 导出 -> 页面预览”的链路。
  QA 做了三层验证：
  - `npm run build` 通过。
  - 用真实 `FreeCADCmd` 验证了导出链路能生成 STEP/FCStd。
  - 用本地 OpenAI-compatible mock + Playwright 做了端到端验证：页面输入需求并点击生成后，状态变成 `当前模型: generated_query_sample_20260331090614.step`，说明“query -> /api/freecad/generate -> FreeCAD 导出 -> StepViewer 自动加载”已经打通。
  补充一点：本机默认 `qwen3-vl:8b` 推理很慢，这不是链路问题。现在代码路径已经接好，只要 `harness/LLM_model` 指向的 OpenAI-compatible 模型能正常响应，页面就会走完整流程。
## 2026-03-31T13:46:30+08:00 · Codex session `019d3a15-59eb-7dc0-a28e-3364df12b9be`
- completion: `task_complete`
- session_start: `2026-03-29T22:52:51+08:00`
- last_event: `2026-03-31T13:46:30+08:00`
- cwd: `/Users/jiwen/PycharmProjects/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/03/29/rollout-2026-03-29T22-52-51-019d3a15-59eb-7dc0-a28e-3364df12b9be.jsonl`
- summary:
  已经完成。
  我先修改了 [harness/WORKFLOW.MD](/Users/jiwen/PycharmProjects/freecad-assembler/harness/WORKFLOW.MD)，把流程收紧成强约束版本，明确了：
  - 按 `DEVELOPER.MD` 开发
  - 按 `QA.MD` 验证，失败就回到开发
  - QA 通过后必须 `git add` + `git commit`
  - 最终回复前必须检查 `git status`
  然后我按这个新流程执行了最后一步，把这次改动提交了。
  提交信息：
  - `494b01f` `Refine workflow rules and align chat plan output`
  当前工作区已经是干净的，`git status` 无未提交变更。
## 2026-03-27T23:25:14+08:00 · Codex session `019d2e16-1a64-7472-868b-e4dc87c2d1d4`
- completion: `task_complete`
- session_start: `2026-03-27T14:58:13+08:00`
- last_event: `2026-03-27T23:25:14+08:00`
- cwd: `/Users/jiwen/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/03/27/rollout-2026-03-27T14-58-13-019d2e16-1a64-7472-868b-e4dc87c2d1d4.jsonl`
- summary:
  我已经把模型加载后的定位改成“按当前视锥直接贴近左上角”，不是小幅偏移。修改在 [public/app.js](/Users/jiwen/freecad-assembler/public/app.js)。
  按你的要求也已经：
  - 杀掉旧进程
  - 重启最新版本到 `http://127.0.0.1:3000`
  你现在刷新再看。如果还不够贴，我下一步就直接把 `edgePadding` 再调小，让它更靠边。
## 2026-03-27T10:02:24+08:00 · Codex session `019d28ed-c2b6-7ac2-bf44-242a7cd14528`
- completion: `task_complete`
- session_start: `2026-03-26T14:56:03+08:00`
- last_event: `2026-03-27T10:02:24+08:00`
- cwd: `/Users/jiwen/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/03/26/rollout-2026-03-26T14-56-03-019d28ed-c2b6-7ac2-bf44-242a7cd14528.jsonl`
- summary:
  已经下载好了，文件在 [Foot.FCStd](/Users/jiwen/freecad-assembler/models/fcstd/Foot.FCStd)。
  我把它放到了 `models/fcstd`，因为这是现有项目里存放 FreeCAD 文档的目录。文件大小约 `55K`。
  如果你要，我下一步可以直接把这个 `Foot.FCStd` 导入到你刚才那个输送线装配里。
## 2026-03-26T10:18:50+08:00 · Codex session `019d2583-9a0f-7b63-8890-353aa328da09`
- completion: `task_complete`
- session_start: `2026-03-25T23:01:14+08:00`
- last_event: `2026-03-26T10:18:50+08:00`
- cwd: `/Users/jiwen/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/03/25/rollout-2026-03-25T23-01-14-019d2583-9a0f-7b63-8890-353aa328da09.jsonl`
- summary:
  因为这个 `circularEdge_001` 不是按 A2plus 正常 GUI 流程创建的，而是我为了让它能在 `freecadcmd` 里生成，故意绕过了 A2plus 的 GUI `ViewProvider` 和 mirror 逻辑。
  关键点有两个：
  [create_a2plus_fasteners_assembly.py](/Users/jiwen/freecad-assembler/create_a2plus_fasteners_assembly.py) 里我加了一个 `setup_proxies_headless` 补丁。这个补丁在无界面模式下只保留约束数据对象 `ConstraintObjectProxy`，但不会创建 A2plus 正常的 `ConstraintViewProviderProxy`。
  A2plus 原本在 [a2p_viewProviderProxies.py](/Users/jiwen/Library/Application%20Support/FreeCAD/Mod/A2plus/a2p_viewProviderProxies.py) 里会给约束创建 GUI proxy，还会生成一个 `_mirror` 对象，并用 `Visibility` 和 `Suppressed` 联动。你这个文件是 headless 生成的，所以这套 GUI 可见性机制没完整建立。
  结果就是：
  - `circularEdge_001` 作为“约束数据对象”是存在的
  - 但它没有正常的 A2plus 约束可视化代理
  - 所以在界面里会表现成 `invisible`，这不代表约束没生效
  从生成日志看，约束其实已经解算成功了，装配是有效的。
  如果你要“界面上也像手工建的 A2plus 约束那样正常显示”，有两个办法：
  1. 最稳妥：在 FreeCAD GUI 里删掉这个约束，重新手工建一次 `Circular Edge Constraint`
  2. 我帮你改脚本：在 GUI 模式打开文件时，补建 A2plus 的 `ViewProvider` 和 mirror，让它恢复成标准 A2plus 约束对象
  如果你要，我下一步可以直接给你写一个“修复已有 `.FCStd` 里 A2plus 约束可见性”的脚本。
## 2026-03-24T22:20:36+08:00 · Codex session `019d1b13-f242-7be1-9236-73aca38d351e`
- completion: `task_complete`
- session_start: `2026-03-23T22:23:05+08:00`
- last_event: `2026-03-24T22:20:36+08:00`
- cwd: `/Users/jiwen/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/03/23/rollout-2026-03-23T22-23-05-019d1b13-f242-7be1-9236-73aca38d351e.jsonl`
- summary:
  新版本已经单独复制成 [LaserHeadAssembly_v2.FCStd](/Users/jiwen/freecad-assembler/LaserHeadAssembly_v2.FCStd) 并打开了。这个文件里我确认包含你刚才没看到的新增件：
  - `FrontMountPlate`
  - `RearMountPlate`
  - `LeftClamp`
  - `RightClamp`
  - `BottomSaddle`
  - `RearSpine`
  - `BridgeBlock`
  也就是说，问题不是没生成，而是 FreeCAD 之前复用了旧标签页或旧视图。
  你现在看 `LaserHeadAssembly_v2.FCStd` 这一份。如果还是没看到新增结构，我下一步就不再靠“刷新原文件”，而是直接把这些新增件做得更大、更明显，或者把激光头单独和夹具做成一个更紧凑的装配，避免被其它梁和底座遮住。
## 2026-04-24T20:23:06+08:00 · Codex session `019dbf6f-3116-7e40-be39-7941908da419`
- completion: `task_complete`
- session_start: `2026-04-24T20:20:28+08:00`
- last_event: `2026-04-24T20:23:06+08:00`
- cwd: `/Users/jiwen/PycharmProjects/freecad-assembler`
- source: `/Users/jiwen/.codex/sessions/2026/04/24/rollout-2026-04-24T20-20-28-019dbf6f-3116-7e40-be39-7941908da419.jsonl`
- summary:
  - App purpose: Local FreeCAD/STEP web app that loads `.step`/`.stp` files from `models/step`, parses them in-browser, and renders them with `three.js`.
  - Main entrypoint: `server.js` starts the app server; the Vue frontend boots from `src/main.js`.
  - How to run it: `npm install` then `npm run start`, then open `http://127.0.0.1:3000`.
