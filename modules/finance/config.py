import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
FINANCE_ATTACHMENT_DIR = Path(
    os.getenv(
        "FINANCE_ATTACHMENT_DIR",
        str(BASE_DIR.parent / "sistema-impress-data" / "finance-attachments"),
    )
).expanduser()
SCHOOL_NAME = os.getenv("SCHOOL_NAME", "Unidade Escolar").strip() or "Unidade Escolar"
