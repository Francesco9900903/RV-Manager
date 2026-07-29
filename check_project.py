from pathlib import Path
from rv_manager.diagnostics import compile_python_files

root = Path(__file__).resolve().parent.parent
results = compile_python_files(root)

failed = [result for result in results if not result.ok]

for result in results:
    status = "OK" if result.ok else "ERRORE"
    print(f"[{status}] {result.name}: {result.detail}")

raise SystemExit(1 if failed else 0)
