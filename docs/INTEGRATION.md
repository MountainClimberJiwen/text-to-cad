# 外部 Agent 使用 cad-asm 指南

> 本文档说明如何让任意外部 agent（Hermes、Claude Code、Kimi、自定义 agent等）调用 cad-asm 这个 sub-agent。

---

## 三种集成方式

| 方式 | 复杂度 | 适用场景 | 优缺点 |
|--------|--------|-----------|--------|
| **A. Shell/CLI** | ★ 最简单 | 快速测试、脚本驱动 | 无需改代码，但需要解析 stdout |
| **B. Python API** | ★★ 中等 | 同一 Python 进程内调用 | 类型安全，可直接操作状态 |
| **C. MCP 协议** | ★★★ 标准 | 跨 agent/跨语言/跨网络 | 标准化，任何 MCP client 都能发现和调用 |

---

## A. Shell/CLI 调用（最简单）

外部 agent 直接执行 shell 命令：

```python
import subprocess

# 1. 初始化
subprocess.run([
    "python", "-m", "cad_asm", "init",
    "--task", "task.json",
    "--workspace", "./ws"
], check=True)

# 2. 全自动运行
result = subprocess.run(
    ["python", "-m", "cad_asm", "run", "--workspace", "./ws", "--auto"],
    capture_output=True, text=True
)
print(result.stdout)

# 3. 导出
subprocess.run([
    "python", "-m", "cad_asm", "export",
    "--workspace", "./ws", "--format", "step"
], check=True)
```

**返回码意义：**
- `0` — 成功/完成
- `1` — 错误
- `2` — 等待 review
- `3` — 装配已完成

---

## B. Python API 调用（推荐）

如果外部 agent 也是 Python 编写的，可以直接调用 `AgentInterface`：

```python
from cad_asm.agent_interface import AgentInterface

api = AgentInterface()

# 1. 初始化 workspace
task = {
    "task_id": "demo-001",
    "parts": [
        {"id": "base", "source": {"type": "step", "path": "models/base.step"}},
        {"id": "arm", "source": {"type": "step", "path": "models/arm.step"}},
    ],
    "constraints": [
        {"type": "place_at", "part1": "base", "part2": "arm", "params": {}}
    ],
    "review_each_step": True
}
ws = api.init_task(task, "/tmp/ws")

# 2. 查询状态
status = api.status(ws)
print(status)

# 3. 执行循环
result = api.run(ws, auto=False)
if result["status"] == "in_review":
    # Agent 检查 review 信息，做出决策
    review = result["review"]
    print(f"Review: {review}")
    api.decide(ws, "approve", "looks good")
    result = api.run(ws, auto=True)

# 4. 导出
path = api.export(ws, "step")
print(f"Exported: {path}")
```

---

## C. MCP 协议调用（标准化）

MCP（Model Context Protocol）是 Anthropic 推出的标准，Claude Code、Cursor、Hermes 等都支持。

### 启动 MCP Server

```bash
python -m cad_asm.mcp_server
```

Server 读取 stdin 的 JSON-RPC 请求，返回工具列表或执行结果。

### 提供的 Tools

| Tool | 作用 |
|------|------|
| `cad_asm_init` | 初始化 workspace |
| `cad_asm_run` | 自动运行装配循环 |
| `cad_asm_step` | 执行单步 |
| `cad_asm_status` | 查询状态 |
| `cad_asm_decide` | 提交 review 决策 |
| `cad_asm_export` | 导出结果 |

### Hermes 配置示例

在 `~/.hermes/config.yaml` 中添加：

```yaml
mcp_servers:
  cad-asm:
    command: python
    args: ["-m", "cad_asm.mcp_server"]
    cwd: /opt/text-to-cad
```

Hermes 将自动发现这 6 个 tools，并在需要时调用它们。

---

## 完整工作流（Agent 视角）

```
外部 Agent
    │
    ├────────────────────────────────────────────────────────────┐
    │                                              │
    ▶ cad_asm_init(task_json, workspace)           │
    │        ↓                                     │
    │   WorkspaceState: running                    │
    │        ↓                                     │
    ▶ cad_asm_run(workspace, auto=False)           │
    │        ↓                                     │
    │   如果 status == "in_review":                 │
    │        ↓                                     │
    ▶ cad_asm_status(workspace) → 查看 review      │
    │        ↓                                     │
    │   Agent 决策（approve/reject/modify）         │
    │        ↓                                     │
    ▶ cad_asm_decide(workspace, "approve")         │
    │        ↓                                     │
    ▶ cad_asm_run(workspace, auto=True) → 继续    │
    │        ↓                                     │
    │   如果 status == "done":                     │
    │        ↓                                     │
    ▶ cad_asm_export(workspace, "step")             │
    │        ↓                                     │
    │   → /tmp/ws/outputs/assembly.step           │
    │                                              │
    └────────────────────────────────────────────────────────────┘
```

---

## 建议

- **快速试验** → 用 Shell 方式 A
- **Python agent 集成** → 用 Python API 方式 B
- **多 agent 协作/长期架构** → 用 MCP 方式 C

MCP 是最有前景的方案，因为它让 cad-asm 成为一个“可发现的工具”，而不仅仅是一个 CLI。
