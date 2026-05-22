"""Library search CLI commands."""
from __future__ import annotations

import json
import sys
from pathlib import Path


def run_search(query: str, threshold: float, top_k: int) -> int:
    from cad_asm.library import search_library

    results = search_library(query, threshold=threshold, top_k=top_k)
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0


def run_list() -> int:
    from cad_asm.library import list_library_parts

    results = list_library_parts()
    print(json.dumps(results, ensure_ascii=False, indent=2))
    return 0
