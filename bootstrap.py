from pathlib import Path
import sys

def ensure_project_root(current_file: str) -> Path:
    root = Path(current_file).resolve().parent.parent
    root_str = str(root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    return root
