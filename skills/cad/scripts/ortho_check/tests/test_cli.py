from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from ortho_check.cli import CheckResult, _parse_views, _resolve_source, check_source, main


class TestParseViews:
    def test_default_views(self) -> None:
        assert _parse_views("front,top,right") == ("front", "top", "right")

    def test_single_view(self) -> None:
        assert _parse_views("isometric") == ("isometric",)

    def test_invalid_view_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid views"):
            _parse_views("front,diagonal")


class TestResolveSource:
    def test_nonexistent_returns_none(self) -> None:
        assert _resolve_source("/nonexistent/path/file.py") is None


class TestCheckSourceMissingGlb:
    def test_missing_glb_reports_error(self, tmp_path: Path) -> None:
        # Create a fake source with no GLB
        from common.catalog import CadSource

        source = CadSource(
            source_ref="test/part",
            cad_ref="@cad[test/part]",
            kind="part",
            source_path=tmp_path / "part.py",
            source="generated",
            origin_path=tmp_path / "part.py",
            script_path=tmp_path / "part.py",
            step_path=tmp_path / "part.step",
        )
        out_dir = tmp_path / "out"
        result = check_source(source, out_dir=out_dir)
        assert not result.ok
        assert any("GLB not found" in e for e in result.errors)


class TestMainCLI:
    def test_missing_target(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            rc = main(["--out-dir", str(out_dir), "/nonexistent/file.py"])
            assert rc == 1

    def test_json_report_written(self, tmp_path: Path) -> None:
        out_dir = tmp_path / "out"
        report_path = tmp_path / "report.json"
        rc = main(
            [
                "--out-dir",
                str(out_dir),
                "--report",
                str(report_path),
                "--json",
                "/nonexistent/file.py",
            ]
        )
        assert rc == 1
        assert report_path.exists()
        payload = json.loads(report_path.read_text(encoding="utf-8"))
        assert payload["ok"] is False
        assert len(payload["results"]) == 1
        assert not payload["results"][0]["ok"]
