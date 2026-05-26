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
4. **悬浮/飞离零件检测（重点）**：
   - 是否有零件没有任何支撑、连接或约束，悬浮在装配体主体之外？
   - 是否有零件与主体之间的间距明显过大，看起来"飞在空中"？
   - 每个零件是否至少与另一个零件有接触、配合或约束关系？
   - 如果某个零件在三个视图中都明显偏离其他零件的聚集区域，必须标记为 critical 错误
5. **孤立零件检测**：是否有零件与其他所有零件都没有任何几何关联（既不相交也不邻近）？
6. **比例与尺寸**：整体尺寸比例是否符合工程常识？
7. **视图一致性**：三个视图之间的投影关系是否匹配（长对正、高平齐、宽相等）？
8. **方向标定**：坐标轴方向是否正确（X-右, Y-上, Z-前）？
"""
    if extra_instructions:
        base += f"\n## 额外要求\n{extra_instructions}\n"

    base += """
## 输出格式

先在 reasoning 中进行分析，然后在最终答案中只输出一个 JSON 对象，不要添加其他文字。

JSON 字段：
- passed: boolean
- confidence: float (0.0-1.0)
- summary: 中文总体评价，1-2句话
- issues: [{"severity": "critical|warning|info", "description": "中文", "view": "front|top|right|all"}]
- suggestions: ["中文建议1", "中文建议2"]
"""
    return base


def _merge_views(image_paths: list[Path], labels: tuple[str, ...] = ("front", "top", "right")) -> Path:
    """Merge orthographic views into a single horizontal image with labels.

    Images are downscaled to reduce VLM upload latency.
    """
    from PIL import Image, ImageDraw, ImageFont

    MAX_HEIGHT = 600  # Downscale tall views to keep payload small

    images_raw = [Image.open(p) for p in image_paths]
    images: list[Image.Image] = []
    for img in images_raw:
        if img.height > MAX_HEIGHT:
            ratio = MAX_HEIGHT / img.height
            new_w = int(img.width * ratio)
            images.append(img.resize((new_w, MAX_HEIGHT), Image.Resampling.LANCZOS))
        else:
            images.append(img)

    max_h = max(img.height for img in images)
    total_w = sum(img.width for img in images)
    label_h = 36
    gap = 16
    total_w += gap * (len(images) - 1)

    merged = Image.new("RGB", (total_w, max_h + label_h), (255, 255, 255))
    draw = ImageDraw.Draw(merged)

    try:
        font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 22)
    except Exception:
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        except Exception:
            font = ImageFont.load_default()

    x = 0
    for idx, img in enumerate(images):
        label = labels[idx] if idx < len(labels) else f"view_{idx}"
        merged.paste(img, (x, label_h))
        bbox = draw.textbbox((0, 0), label, font=font)
        text_w = bbox[2] - bbox[0]
        text_x = x + (img.width - text_w) // 2
        draw.text((text_x, 6), label, fill=(0, 0, 0), font=font)
        x += img.width + gap

    out_path = Path(image_paths[0]).parent / "merged_views.png"
    merged.save(out_path, "PNG")
    return out_path


def _build_messages(
    prompt_text: str,
    image_paths: list[Path],
) -> list[dict[str, Any]]:
    from cad_asm.core.vlm_client import encode_image

    # Merge three views into one image to reduce VLM latency
    merged_path = _merge_views(image_paths)
    b64 = encode_image(merged_path)

    content: list[dict[str, Any]] = [
        {"type": "text", "text": prompt_text},
        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{b64}"}},
        {"type": "text", "text": "↑ 上图从左到右依次为：front（正视图）、top（俯视图）、right（右视图）"},
    ]
    return [{"role": "user", "content": content}]


def run_vlm_review(
    workspace: Path,
    *,
    out_dir: Path | None = None,
    extra_instructions: str | None = None,
    dry_run: bool = False,
    provider: str | None = None,
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
        print(f"[VLM Review] Calling VLM ({provider or 'kimi'}) for visual judgement...")
        try:
            verdict = call_vlm(
                messages,
                temperature=0.2,
                max_tokens=4096,
                provider=provider,
            )
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
