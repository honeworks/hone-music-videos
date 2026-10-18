"""Every example in examples/ and every `python` block of the README and docs/ runs (offline, on fakes)."""

import re
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.e2e
ROOT = Path(__file__).resolve().parents[2]
EXAMPLES = sorted((ROOT / "examples").glob("*.py"))
PAGES = [ROOT / "README.md", *sorted((ROOT / "docs").glob("*.md"))]
BLOCKS = [
    pytest.param(block, id=f"{page.name}-{n}")
    for page in PAGES
    for n, block in enumerate(re.findall(r"```python\n(.*?)```", page.read_text(encoding="utf-8"), re.S), 1)
]


@pytest.mark.parametrize("example", EXAMPLES, ids=[e.name for e in EXAMPLES])
def test_the_example_runs(example: Path, tmp_path: Path) -> None:
    found = subprocess.run([sys.executable, str(example)], cwd=tmp_path, capture_output=True, text=True)
    assert found.returncode == 0, found.stderr


def test_every_example_is_listed() -> None:
    listing = (ROOT / "examples" / "README.md").read_text(encoding="utf-8")
    assert all(f"]({e.name})" in listing for e in EXAMPLES)


@pytest.mark.parametrize("block", BLOCKS)
def test_the_docs_code_runs(block: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    script = tmp_path / "block.py"
    script.write_text(block, encoding="utf-8")
    runpy.run_path(str(script))
