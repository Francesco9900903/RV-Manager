"""
RV Manager Enterprise 3.5
Entry point stabile con caricamento controllato della UI legacy.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

LEGACY_PATH = ROOT / "legacy_app.py"

if not LEGACY_PATH.exists():
    raise FileNotFoundError(f"File mancante: {LEGACY_PATH}")

source = LEGACY_PATH.read_text(encoding="utf-8")
compiled = compile(source, str(LEGACY_PATH), "exec")
exec(compiled, globals(), globals())
