#!/bin/bash
set -e
cd /Users/jiwen/PycharmProjects/freecad-assembler
source .venv/bin/activate

WORKSPACE=/tmp/asm_kimi_test
rm -rf "$WORKSPACE"

echo "=== 1. init ==="
cad-asm init --task examples/simple_bracket/task.json --workspace "$WORKSPACE" --force

echo "=== 2. step base_plate ==="
cad-asm step --workspace "$WORKSPACE" || true

echo "=== review base_plate ==="
cat "$WORKSPACE/review/pending.json"

echo "=== 3. approve base_plate ==="
echo '{"decision": "approve", "reason": "base plate at origin is correct"}' > "$WORKSPACE/decisions/0001.json"

echo "=== 4. step mount_block (align_face constraint) ==="
cad-asm step --workspace "$WORKSPACE" --continue || true

echo "=== review mount_block ==="
cat "$WORKSPACE/review/pending.json"

echo "=== 5. approve mount_block ==="
echo '{"decision": "approve", "reason": "mount block correctly aligned on top of base plate"}' > "$WORKSPACE/decisions/0002.json"

echo "=== 6. step peg (align_face constraint) ==="
cad-asm step --workspace "$WORKSPACE" --continue || true

echo "=== review peg ==="
cat "$WORKSPACE/review/pending.json"

echo "=== 7. approve peg ==="
echo '{"decision": "approve", "reason": "peg correctly aligned on top of mount block"}' > "$WORKSPACE/decisions/0003.json"

echo "=== 8. continue to finish ==="
cad-asm step --workspace "$WORKSPACE" --continue || true

echo "=== 9. verify ==="
cad-asm verify --workspace "$WORKSPACE"

echo "=== 10. export ==="
cad-asm export --workspace "$WORKSPACE" --format step

echo "=== 11. check output ==="
ls -lh "$WORKSPACE/output/assembly.step"

echo "=== DONE ==="
