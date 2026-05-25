# Kimi × cad-asm 集成方案

## 两个核心问题

1. **Kimi 怎么调用 cad-asm？**
2. **cad-asm 内部需不需要 LLM 能力？**

---

## 答案 1：Kimi 集成方式

Kimi 是 LLM，本身不能直接调用外部工具。需要一个 **driver 层** 负责：

```
用户自然语言 → Kimi LLM → driver 脚本 → cad-asm 执行 → 结果返回用户
```

### 方式 A：Kimi 生成 Task JSON（推荐）

用户说"组装一个带气缸和夹具的自动化工位"，Kimi 负责把这句话翻译成 `AssemblyTask` JSON：

```python
# examples/kimi_driver.py
from agentrl.llm import KimiClient
from cad_asm.agent_interface import AgentInterface

kimi = KimiClient()
api = AgentInterface()

# 1. Kimi 生成 task JSON
user_prompt = "组装一个自动化工位，底座是 300x300 的铝板，上面安装气缸和夹具"
system = """你是 CAD 装配工程师。根据用户描述生成一个符合 cad-asm 规范的 AssemblyTask JSON。
必须包含：parts、constraints、review_each_step。"""

task_json = json.loads(kimi.chat(system=system, user=user_prompt))

# 2. cad-asm 执行装配
ws = api.init_task(task_json, "/tmp/ws")
result = api.run(ws, auto=True)
path = api.export(ws, "step")
print(f"完成：{path}")
```

### 方式 B：Kimi 做 Reviewer（质量检查）

```python
# 执行一步后暂停，让 Kimi 检查
result = api.run(ws, auto=False)

if result["status"] == "in_review":
    review = result["review"]
    
    # Kimi 检查几何、干涉、拓扑
    decision = kimi.chat(
        system="你是 CAD 质量检查员。根据 review 信息决定 approve/reject/modify。",
        user=json.dumps(review, ensure_ascii=False)
    )
    
    api.decide(ws, decision.strip())
    api.run(ws, auto=True)
```

### 方式 C：Kimi Function Calling（自动工具调用）

在调用 Kimi API 时传入 tools 定义，Kimi 自动决定调用 cad-asm：

```python
tools = [
    {
        "type": "function",
        "function": {
            "name": "cad_asm_init",
            "description": "初始化装配 workspace",
            "parameters": {...}
        }
    },
    # ... 其他 5 个 tools
]

# Kimi 会自动解析用户意图，调用相应的 cad-asm 工具
response = kimi.chat_with_tools(user="组装一个自动化工位", tools=tools)
```

### 方式 D：通过 Hermes 中转（推荐长期架构）

```
用户 → Hermes → Kimi API (思考) → Hermes → cad-asm MCP Server → 执行
                ←───── 结果 ──────┘
```

在 `~/.hermes/config.yaml` 配置 MCP server：

```yaml
mcp_servers:
  cad-asm:
    command: python
    args: ["-m", "cad_asm.mcp_server"]
    cwd: /opt/text-to-cad
```

Hermes 自动发现 6 个 cad-asm 工具，调用 Kimi 时工具定义会进入 prompt，Kimi 决定用哪个。

---

## 答案 2：cad-asm 内部需不需要 LLM？

### 答案：**核心引擎不需要，但 LLM 可大幅增强体验**

| 功能 | 当前实现 | 是否需要 LLM | 说明 |
|------|---------|-------------|------|
| 几何约束求解 | build123d + OCP | ❌ 不需要 | 确定性计算，纯数学 |
| 干涉检测 | 体积交集计算 | ❌ 不需要 | 纯几何算法 |
| STEP/STL 导出 | OCP 格式转换 | ❌ 不需要 | 文件 I/O |
| **自然语言→Task** | 无 | ✅ **需要** | 用户说"放上去" → 约束 JSON |
| **错误诊断** | 无 | ✅ **需要** | 干涉了 → 怎么修？ |
| **零件搜索** | 关键词匹配 | ✅ **增强** | "气缸" → 搜索标准库 |
| **Review 决策** | 人工 | ✅ **增强** | 几何可视化 → 自动决策 |

### 建议的 LLM 增强点

```
cad-asm 核心 (无 LLM)
    │
    ├────────────────────────────────────────────────────────────┐
    │                                              │
    ▶ 【增强 1】自然语言 → Task JSON               │
    │   Kimi 将用户描述翻译为约束和零件定义        │
    │                                              │
    ▶ 【增强 2】Review 自动化                      │
    │   Kimi 检查几何报告，做出 approve/modify        │
    │                                              │
    ▶ 【增强 3】错误恢复                        │
    │   干涉/缺少零件 → Kimi 建议修复方案       │
    │                                              │
    ▶ 【增强 4】零件语义搜索                      │
    │   "我需要一个小型气缸" → 向量搜索标准库      │
    │                                              │
```

### 实际建议

- **短期**：保持 cad-asm 核心无 LLM，用 Kimi driver 脚本做增强
- **中期**：在 `cad_asm/commands/` 中添加 `llm_` 前缀的可选命令，如 `llm_generate_task`、`llm_diagnose_error`
- **长期**：把 LLM 增强点抽象成 plugin 接口，支持 Kimi/GPT/Claude 插拔

---

## 完整示例脚本

见 `examples/kimi_driver.py`：展示了 Kimi 生成 Task → cad-asm 执行 → Kimi Review → 导出的完整流程。
