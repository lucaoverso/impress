import os
from datetime import timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


def env_bool(name: str, default: bool = False) -> bool:
    fallback = "true" if default else "false"
    return os.getenv(name, fallback).strip().lower() in {"1", "true", "yes", "on"}


def app_timezone():
    name = os.getenv("APP_TIMEZONE", "America/Campo_Grande").strip()
    try:
        return ZoneInfo(name)
    except ZoneInfoNotFoundError:
        return timezone(timedelta(hours=-4))


def push_settings() -> dict:
    public_key = os.getenv("VAPID_PUBLIC_KEY", "").strip()
    private_key = os.getenv("VAPID_PRIVATE_KEY", "").strip()
    enabled = env_bool("WEB_PUSH_ENABLED") and bool(public_key and private_key)
    return {
        "enabled": enabled,
        "public_key": public_key,
        "private_key": private_key,
        "subject": os.getenv(
            "VAPID_SUBJECT", "https://sistema.eepjd.com.br"
        ).strip(),
    }
