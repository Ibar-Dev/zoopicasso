from __future__ import annotations

import sys
from pathlib import Path


def ensure_project_paths() -> list[str]:
    """Adds project root paths needed by the desktop app and shared modules."""
    root = Path(__file__).resolve().parents[1]
    app_dir = Path(__file__).resolve().parent
    generar_dir = root / 'generar_para_email'

    for candidate in (root, app_dir, generar_dir):
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(0, candidate_str)

    return [str(root), str(app_dir), str(generar_dir)]
