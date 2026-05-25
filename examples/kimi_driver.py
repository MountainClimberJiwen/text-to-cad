#!/usr/bin/env python3
"""
Kimi × cad-asm 完整工作流示例

演示：
  1. Kimi 根据自然语言生成 AssemblyTask JSON
  2. cad-asm 初始化 workspace 并执行装配
  3. 如果暂停在 review gate，Kimi 检查并做出决策
  4. 导出最终 STEP 文件

环境变量：
  KIMI_API_KEY — 必须，在 /opt/agentrl/.env 中定义

用法：
  cd /opt/text-to-cad
  python examples/kimi_driver.py "组装一个带气缸的自动化工位"
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

# Ensure cad_asm is importable
sys.path.insert(0, str(Path(__file__).parent.parent))

from cad_asm.agent_interface import AgentInterface


class KimiClient:
    """Lightweight Kimi API client (zero pip deps)."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("KIMI_API_KEY", "")
        if not self.api_key:
            raise RuntimeError("KIMI_API_KEY not set")
        self.base_url = "https://api.moonshot.cn/v1"
        self.model = "moonshot-v1-8k"

    def chat(self, system: str, user: str, temperature: float = 0.3) -> str:
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "cad-asm-kimi-driver",
            },
            data=json.dumps({
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
                "temperature": temperature,
            }, ensure_ascii=False).encode("utf-8"),
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"]


SYSTEM_GENERATE_TASK = """你是一个熟练的 CAD 装配工程师。根据用户的自然语言描述，生成一个符合以下规范的 AssemblyTask JSON。

规范：
- task_id: 字符串，唯一标识
- parts: 数组，每个零件必须有 id、source、transform
  - source.type: "step" 或 "primitive"
  - source.path: 文件路径（相对于 workspace）
- constraints: 数组，每个约束有 type、part1、part2、params
  - type: "place_at" | "align_face" | "mate" | "offset"
- review_each_step: 布尔值，是否每步都需要 review

只输出纯 JSON，不要任何解释。
"""


SYSTEM_REVIEW = """你是 CAD 装配质量检查员。根据以下 review 信息，决定是否批准当前步骤。

可选决策：
- "approve" — 几何正确，无干涉，可以继续
- "reject" — 有严重问题，需要重新设计
- "modify" — 需要调整位置/旋转

只输出一个单词（approve/reject/modify），不要任何解释。
"""


def parse_json(text: str) -> dict:
    """Extract JSON from markdown code block or raw text."""
    import re
    # Try code block
    m = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL)
    if m:
        return json.loads(m.group(1))
    # Try raw braces
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1:
        return json.loads(text[start:end+1])
    raise ValueError("No JSON found in response")


def main(user_request: str, workspace: str = "/tmp/cad_asm_kimi_demo") -> int:
    kimi = KimiClient()
    api = AgentInterface()
    ws = Path(workspace)

    print(f"📝 用户需求: {user_request}")

    # 1. Kimi 生成 Task JSON
    print("\n🤖 Kimi 生成 AssemblyTask...")
    raw = kimi.chat(SYSTEM_GENERATE_TASK, user_request, temperature=0.3)
    task_json = parse_json(raw)
    print(f"✅ Task 生成完成: {task_json.get('task_id', 'unknown')}")
    print(json.dumps(task_json, indent=2, ensure_ascii=False))

    # 2. 初始化 workspace
    print(f"\n📦 初始化 workspace: {ws}")
    if ws.exists():
        import shutil
        shutil.rmtree(ws)
    api.init_task(task_json, ws)
    print("✅ 初始化完成")

    # 3. 执行装配（非 auto，允许 review）
    print("\n🔄 开始装配...")
    result = api.run(ws, auto=False, max_iterations=100)

    # 4. 处理 review gate
    review_count = 0
    while result["status"] == "in_review" and review_count < 10:
        review_count += 1
        review_info = result.get("review", {})
        print(f"\n⏸️ 暂停在 review gate (第 {review_count} 次)")
        print(json.dumps(review_info, indent=2, ensure_ascii=False))

        # Kimi 做出决策
        print("\n🤖 Kimi 审查中...")
        decision = kimi.chat(SYSTEM_REVIEW, json.dumps(review_info, ensure_ascii=False), temperature=0.1)
        decision = decision.strip().lower().split()[0]
        print(f"✅ Kimi 决策: {decision}")

        if decision == "reject":
            print("❌ 装配被拒绝，终止")
            return 1

        api.decide(ws, decision, reason="kimi-auto-review")

        # 继续装配
        result = api.run(ws, auto=False, max_iterations=100)

    if result["status"] == "error":
        print(f"\n❌ 装配错误: {result.get('last_error', 'unknown')}")
        return 1

    if result["status"] == "done":
        print("\n✅ 装配完成!")

    # 5. 导出
    print("\n📤 导出 STEP...")
    path = api.export(ws, "step")
    if path:
        print(f"✅ 导出成功: {path}")
    else:
        print("⚠️ 导出失败（可能环境未配置 build123d）")

    return 0


if __name__ == "__main__":
    request = sys.argv[1] if len(sys.argv) > 1 else "组装一个底座为 300x300 铝板、带气缸和夹具的自动化工位"
    sys.exit(main(request))
