from dataclasses import dataclass
from importlib import import_module
from pathlib import Path
from typing import Iterable
import py_compile

@dataclass
class DiagnosticResult:
    name: str
    ok: bool
    detail: str

def compile_python_files(root: Path) -> list[DiagnosticResult]:
    results = []
    for file in sorted(root.rglob("*.py")):
        if "__pycache__" in file.parts:
            continue
        try:
            py_compile.compile(str(file), doraise=True)
            results.append(DiagnosticResult(str(file.relative_to(root)), True, "Compilazione OK"))
        except Exception as exc:
            results.append(DiagnosticResult(str(file.relative_to(root)), False, f"{type(exc).__name__}: {exc}"))
    return results

def check_imports(modules: Iterable[str]) -> list[DiagnosticResult]:
    results = []
    for module_name in modules:
        try:
            import_module(module_name)
            results.append(DiagnosticResult(module_name, True, "Import OK"))
        except Exception as exc:
            results.append(DiagnosticResult(module_name, False, f"{type(exc).__name__}: {exc}"))
    return results
