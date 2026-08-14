import os
from pathlib import Path


DATA_DIR = Path(os.path.expanduser("~")) / ".finance_manager"
DB_PATH = DATA_DIR / "finance.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
