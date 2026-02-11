"""Compat package shim for repository-root `AlmaGag` package.

This repository keeps source code inside `AlmaGag/` (nested directory) while
also having a repository-root `__init__.py` file. In some environments (pytest,
IDEs, runners that add `/workspace` to `sys.path`) Python resolves this root
package first, making imports like `AlmaGag.layout` fail.

We explicitly extend `__path__` to include the nested source directory so
`AlmaGag.<module>` works consistently across execution contexts.
"""

from pathlib import Path
from pkgutil import extend_path

# Namespace-compatible path extension.
__path__ = extend_path(__path__, __name__)  # type: ignore[name-defined]

_nested_src = Path(__file__).resolve().parent / "AlmaGag"
if _nested_src.is_dir():
    nested_src_str = str(_nested_src)
    if nested_src_str not in __path__:
        __path__.append(nested_src_str)
