import os
from pathlib import Path


DATA_DIR = Path(os.path.expanduser("~")) / ".finance_manager"
DB_PATH = DATA_DIR / "finance.db"
THEMES_DIR = DATA_DIR / "themes"

DATA_DIR.mkdir(parents=True, exist_ok=True)
THEMES_DIR.mkdir(parents=True, exist_ok=True)

# Banco Central do Brasil SGS API (public economic indicators). Free, no key.
# NOTE: the /ultimos/{n} endpoint caps n at 20 ("A quantidade máxima de valores
# deve ser 20"), so we query by date range instead, which has no such limit.
BCB_SGS_BASE_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{code}/dados"
    "?formato=json&dataInicial={start}&dataFinal={end}"
)
BCB_SGS_TIMEOUT_SECONDS = 15
