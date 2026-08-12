import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
BLOG_IMAGE_DIR = Path(
    os.getenv(
        "BLOG_IMAGE_DIR",
        str(BASE_DIR.parent / "sistema-impress-data" / "blog-images"),
    )
).expanduser()

BLOG_PUBLIC_HOST = os.getenv("BLOG_PUBLIC_HOST", "blog.eepjd.com.br").strip().lower()
BLOG_PUBLIC_URL = os.getenv(
    "BLOG_PUBLIC_URL", f"https://{BLOG_PUBLIC_HOST}"
).strip().rstrip("/")
