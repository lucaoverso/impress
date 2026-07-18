from collections import deque
from threading import Lock
from time import monotonic
from typing import Callable, Iterable

from fastapi import HTTPException, Request


RateLimitRule = tuple[str, str, int, int]

POLICIES = {
    "login": (("ip", 60, 60), ("account", 10, 300)),
    "register": (("ip", 10, 3600),),
    "password_reset": (("ip", 20, 900), ("account", 5, 900)),
}


class InMemoryRateLimiter:
    def __init__(self, clock: Callable[[], float] = monotonic):
        self._clock = clock
        self._hits: dict[tuple[str, str], tuple[deque[float], int]] = {}
        self._lock = Lock()
        self._next_cleanup = 0.0

    def allow(self, rules: Iterable[RateLimitRule]) -> bool:
        now = self._clock()
        rules = tuple(rules)

        with self._lock:
            self._cleanup(now)
            buckets = []
            for scope, key, limit, window in rules:
                bucket, _ = self._hits.setdefault((scope, key), (deque(), window))
                cutoff = now - window
                while bucket and bucket[0] <= cutoff:
                    bucket.popleft()
                if len(bucket) >= limit:
                    return False
                buckets.append(bucket)

            for bucket in buckets:
                bucket.append(now)
            return True

    def clear(self) -> None:
        with self._lock:
            self._hits.clear()
            self._next_cleanup = 0.0

    def _cleanup(self, now: float) -> None:
        if now < self._next_cleanup:
            return

        for key, (bucket, window) in list(self._hits.items()):
            cutoff = now - window
            while bucket and bucket[0] <= cutoff:
                bucket.popleft()
            if not bucket:
                del self._hits[key]
        self._next_cleanup = now + 60


# ponytail: process-local counters; use Redis or another shared store if the API gains workers.
rate_limiter = InMemoryRateLimiter()


def enforce_rate_limit(request: Request, action: str, account: str = "") -> None:
    client_ip = request.client.host if request.client else "unknown"
    account_key = str(account or "").strip().lower() or "unknown"
    rules = []
    for dimension, limit, window in POLICIES[action]:
        key = client_ip if dimension == "ip" else account_key
        rules.append((f"{action}:{dimension}", key, limit, window))

    if not rate_limiter.allow(rules):
        raise HTTPException(429, "Muitas tentativas. Tente novamente mais tarde.")
