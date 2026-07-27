"""
RV Manager Enterprise 2.0

Entry point modulare. La UI legacy resta temporaneamente isolata in
`legacy_app.py`, mentre i nuovi moduli vengono spostati nel package
`rv_manager`. Questo consente una migrazione progressiva senza perdere
le funzionalità già collaudate.
"""
from pathlib import Path

LEGACY_PATH = Path(__file__).with_name("legacy_app.py")
source = LEGACY_PATH.read_text(encoding="utf-8")
exec(compile(source, str(LEGACY_PATH), "exec"), globals(), globals())
