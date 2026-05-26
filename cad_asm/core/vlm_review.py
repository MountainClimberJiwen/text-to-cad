"""VLM-based three-view visual review for cad-asm checkpoints.

Orchestrates:
1. Render front/top/right views via the existing check module.
2. Build a multimodal prompt with task context + base64 images.
3. Call VLM for visual judgement.
4. Parse structured verdict (pass/fail + issues + suggestions).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from cad_asm.core.state import WorkspaceState
from cad_asm.schemas.task import AssemblyTask


def _build_task_description(task: AssemblyTask) -> str:
    lines: list[str] = []
    lines.append(f"Task ID: {task.task_id}")
    if task.name:
        lines.append(f"Name: {task.name}")
    lines.append(f"Parts ({len(task.parts)}):")
    for p in task.parts:
        src = "inline shape" if p.shape else (p.source.type if p.source else "unknown")
        lines.append(f"  - {p.id}: {p.name or p.id} (source={src})")
    if task.constraints:
        lines.append(f"Constraints ({len(task.constraints)}):")
        for c in task.constraints:
            lines.append(f"  - {c.type}: {c.part1} → {c.part2}")
    return "\n".join(lines)


def _build_review_prompt(task_desc: str, extra_instructions: str | None = None) -> str:
    base = f"""你是一名资深 CAD 装配质检工程师。请根据以下装配任务描述，严格检查提供的三视图（正视图 front、俯视图 top、右视图 right）是否合理。

## 任务描述
{task_desc}

## 检查清单
1. **零件完整性**：所有声明的零件是否都在三视图中可见？是否有遗漏或多余零件？
2. **装配位置**：各零件的相对位置、方向是否符合约束要求？
3. **干涉检测**：是否有零件重叠、穿透或异常接触？
4. **比例与尺寸**：整体尺寸比例是否符合工程常识？
5. **视图一致性**：三个视图之间的投影关系是否匹配（长对正、高平齐、宽相等）？
6. **方向标定**：坐标轴方向是否正确（X-右, Y-上, Z-前）？
"""
    if extra_instructions:
        base += f"\n## 额外要求\n{extra_instructions}\n"

    base += """
## 输出格式（极其重要）

你必须分两步输出：
1. 先在 reasoning 中进行完整分析。
2. **然后在最终答案（content）中只输出一个严格合法的 JSON 对象**，不要有任何其他文字、不要加 markdown 说明、不要加 ``` 代码块标记。

content 中输出的 JSON 必须严格如下格式：

{"passed": true, "confidence": 0.95, "summary": "...", "issues": [], "suggestions": []}

字段说明：
- passed: boolean，true 表示通过，false 表示不通过
- confidence: 0.0-1.0 的置信度
- summary: 总体评价，中文，1-2句话
- issues: 问题列表，每个问题包含 severity(critical/warning/info)、description(中文)、view(front/top/right/all)
- suggestions: 修改建议列表，中文
"""
    return base


def _build_messages(
    prompt_text: str,
    image_paths: list[Path],
) -> list[dict[str, Any]]:
    from cad_asm.core.vlm_client import encode_image

    content: list[dict[str, Any]] = [{"type": "text", "text": prompt_text}]
    view_labels = ["front", "top", "right"]
    for idx, path in enumerate(image_paths):
        label = view_labels[idx] if idx < len(view_labels) else f"view_{idx}"
        b64 = encode_image(path)
        content.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
        # Insert label text after each image so the model knows which view is which
        content.append({"type": "text", "text": f"↑ 这是 {label} 视图"})
    return [{"role": "user", "content": content}]


def run_vlm_review(
    workspace: Path,
    *,
    out_dir: Path | None = None,
    extra_instructions: str | None = None,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Run the full VLM three-view review pipeline.

    Args:
        workspace: cad-asm workspace directory.
        out_dir: Where to write check images and the final review JSON.
        extra_instructions: Additional prompt text appended to the review prompt.
        dry_run: If True, skip the actual VLM call and return a mock response.

    Returns:
        Dict with keys: ok, vlm_verdict, images, checkpoint, errors.
    """
    from cad_asm.commands.check import run as run_check
    from cad_asm.core.vlm_client import call_vlm

    state_path = workspace / "state.json"
    if not state_path.exists():
        return {"ok": False, "errors": ["Workspace not initialized"], "vlm_verdict": None}

    ws = WorkspaceState.from_file(state_path)
    task = AssemblyTask.from_file(workspace / "task.json")
    checkpoint = workspace / ws.checkpoint_file if ws.checkpoint_file else None
    if not checkpoint or not checkpoint.exists():
        return {"ok": False, "errors": ["No checkpoint found"], "vlm_verdict": None}

    if out_dir is None:
        out_dir = workspace / "checks"

    # 1. Generate orthographic views
    print("[VLM Review] Generating orthographic views...")
    rc = run_check(
        workspace,
        out_dir=out_dir,
        views=("front", "top", "right"),
        width=1200,
        height=900,
    )
    if rc != 0:
        return {"ok": False, "errors": ["View generation failed"], "vlm_verdict": None}

    stem = checkpoint.stem
    image_paths = [
        out_dir / f"{stem}-front.png",
        out_dir / f"{stem}-top.png",
        out_dir / f"{stem}-right.png",
    ]
    missing = [str(p) for p in image_paths if not p.exists()]
    if missing:
        return {"ok": False, "errors": [f"Missing images: {missing}"], "vlm_verdict": None}

    # 2. Build prompt & call VLM
    task_desc = _build_task_description(task)
    prompt = _build_review_prompt(task_desc, extra_instructions=extra_instructions)
    messages = _build_messages(prompt, image_paths)

    if dry_run:
        verdict: dict[str, Any] = {
            "passed": True,
            "confidence": 1.0,
            "summary": "[dry-run] 跳过 VLM 调用",
            "issues": [],
            "suggestions": [],
        }
    else:
        print("[VLM Review] Calling VLM for visual judgement...")
        try:
            verdict = call_vlm(messages, temperature=0.2, max_tokens=4096)
        except Exception as exc:
            return {"ok": False, "errors": [f"VLM call failed: {exc}"], "vlm_verdict": None}

    # 3. Normalize verdict
    passed = bool(verdict.get("passed")) if isinstance(verdict, dict) else False
    confidence = float(verdict.get("confidence", 0.0)) if isinstance(verdict, dict) else 0.0
    summary = str(verdict.get("summary", "")) if isinstance(verdict, dict) else ""
    issues = list(verdict.get("issues", [])) if isinstance(verdict, dict) else []
    suggestions = list(verdict.get("suggestions", [])) if isinstance(verdict, dict) else []

    # 4. Persist review result
    review_result: dict[str, Any] = {
        "ok": passed,
        "vlm_verdict": {
            "passed": passed,
            "confidence": confidence,
            "summary": summary,
            "issues": issues,
            "suggestions": suggestions,
        },
        "checkpoint": str(checkpoint),
        "images": [str(p) for p in image_paths],
    }
    review_path = out_dir / "vlm_review.json"
    review_path.write_text(
        __import__("json").dumps(review_result, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    # 5. Print summary
    status = "PASS" if passed else "FAIL"
    print(f"\n[VLM Review] {status} (confidence={confidence:.2f})")
    if summary:
        print(f"  summary: {summary}")
    for issue in issues:
        sev = issue.get("severity", "info") if isinstance(issue, dict) else "info"
        desc = issue.get("description", str(issue)) if isinstance(issue, dict) else str(issue)
        view = issue.get("view", "all") if isinstance(issue, dict) else "all"
        print(f"  [{sev}] ({view}) {desc}")
    for suggestion in suggestions:
        print(f"  suggestion: {suggestion}")
    print(f"  report: {review_path}")

    return review_result
