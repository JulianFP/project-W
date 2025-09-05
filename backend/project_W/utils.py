import base64
import hashlib
from datetime import datetime, timedelta, timezone


def parse_version_tuple(version_tuple: tuple[int | str, ...]) -> tuple[int, int, int, int, bool]:
    assert len(version_tuple) >= 3

    is_dirty = False
    revisions = 0
    if len(version_tuple) >= 5:
        is_dirty = str(version_tuple[4]).find(".d") != -1
    if len(version_tuple) >= 4:
        revisions = int(str(version_tuple[3])[3:])

    return (
        int(version_tuple[0]),
        int(version_tuple[1]),
        int(version_tuple[2]),
        revisions,
        is_dirty,
    )


def hash_token(token: str):
    """
    We only store the hash of the token, otherwise a db leak would make
    it possible to impersonate any runner/user. We don't need to use a salted hash
    because the token is created by the server and already has sufficient entropy.
    The hash itself is stored using base64.
    """
    return (
        base64.urlsafe_b64encode(hashlib.sha256(token.encode("ascii")).digest())
        .rstrip(b"=")
        .decode("ascii")
    )


def minutes_from_now_to_datetime(minutes_from_now: int) -> datetime:
    expires_delta = timedelta(minutes=minutes_from_now)
    return datetime.now(timezone.utc) + expires_delta
