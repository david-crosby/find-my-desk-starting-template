"""
Root conftest.py — adds workspace package source directories to sys.path.

This is needed because Python 3.12 skips .pth files whose names start with
an underscore, which is the naming convention used by hatchling for editable
installs. The editable install paths would not be discovered automatically.
"""
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent
_PACKAGE_SRCS = [
    _REPO_ROOT / "packages" / "core" / "src",
    _REPO_ROOT / "packages" / "backend" / "src",
    _REPO_ROOT / "packages" / "agent" / "src",
    _REPO_ROOT / "packages" / "ui_admin" / "src",
    _REPO_ROOT / "packages" / "ui_user" / "src",
]

for _src in _PACKAGE_SRCS:
    _src_str = str(_src)
    if _src_str not in sys.path:
        sys.path.insert(0, _src_str)
