from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def read_json(path: Path) -> Any:
    with open(path, "r") as f:
        return json.load(f)


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def stable_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def repo_cache_dir(cache_root: str | Path, repo_path: str | Path, language: str) -> Path:
    repo_abs = str(Path(repo_path).expanduser().resolve())
    return Path(cache_root) / f"{language}_{stable_hash(repo_abs)}"


def query_cache_dir(repo_dir: Path, query: str) -> Path:
    return repo_dir / "queries" / stable_hash(query)

