import os
from pathlib import Path


DATA_DIR = Path(os.path.expanduser("~")) / ".finance_manager"
DB_PATH = DATA_DIR / "finance.db"
THEMES_DIR = DATA_DIR / "themes"

DATA_DIR.mkdir(parents=True, exist_ok=True)
THEMES_DIR.mkdir(parents=True, exist_ok=True)
