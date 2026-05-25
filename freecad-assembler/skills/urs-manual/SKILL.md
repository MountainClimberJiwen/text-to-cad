---
name: urs-manual
description: URS-MANUAL 分层文档检索 skill。用于在 WORKFLOW、模块文档和 runtime 路由文档中定位答案，并按模块逐层下钻。
triggers:
  - urs-manual
  - URS-MANUAL
  - urs
  - manual
  - 模块
  - 工艺流程
  - 机构设计
  - 验证体系
  - 交货期
---

# URS Manual Skill

当问题涉及 URS 规划、模块拆解、工艺/布局/机构/验证/排期时：

1. 先看 `URS-MANUAL/WORKFLOW.MD` 获取全局边界
2. 再按模块进入 `URS-MANUAL/modules/*.md`
3. 用 `URS-MANUAL/runtime/ROUTING.md` 执行跨模块联动与下钻

输出要求：
- 优先给出对应模块结论
- 必要时给出下一层应查看的模块路径
- 不编造未在文档出现的定量参数
