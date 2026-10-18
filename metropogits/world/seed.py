"""ADR-024: independent SHA-256 counter streams with an explicit wire format."""

import hashlib
import unicodedata

ALGORITHM = "sha256-counter/1"


def derive(*fields: str) -> str:
    digest = hashlib.sha256()
    for field in (ALGORITHM, *fields):
        data = unicodedata.normalize("NFC", str(field)).encode("utf8")
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.digest()[:8].hex()


def draw(seed: str, counter: int = 0) -> float:
    if not isinstance(counter, int) or isinstance(counter, bool) or counter < 0:
        raise ValueError("world counter must be a nonnegative integer")
    # 53-bit mantissa; no platform-dependent random implementation.
    return (int(derive(seed, str(counter)), 16) >> 11) / (1 << 53)


def world_seed(repository_namespace: str, override: str | None = None) -> str:
    if not repository_namespace or len(repository_namespace.encode("utf8")) > 4096:
        raise ValueError("world repository namespace must contain 1..4096 UTF-8 bytes")
    if override is not None and len(override.encode("utf8")) > 4096:
        raise ValueError("world seed exceeds 4096 UTF-8 bytes")
    return (
        derive("world", repository_namespace)
        if override is None
        else derive("override", override)
    )
