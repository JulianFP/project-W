import re
from typing import Dict, Generic, List, Optional, Tuple, TypeVar, Union

from flask import Request, json
from itsdangerous.url_safe import URLSafeTimedSerializer

from project_W.logger import get_logger

logger = get_logger("project-W")


def _encode_string_as_token(string_to_encode: str, salt: str, secret_key: str) -> str:
    ss = URLSafeTimedSerializer(secret_key, salt=salt)
    return ss.dumps(string_to_encode)


def _decode_string_from_token(
    token: str, salt: str, secret_key: str, max_age_secs: int
) -> Optional[str]:
    ss = URLSafeTimedSerializer(secret_key, salt=salt)
    try:
        decodedString = ss.loads(token, max_age=max_age_secs)
    except Exception as e:
        logger.warning(f"Invalid or expired {salt} token: {e}")
        return None
    return decodedString


def encode_activation_token(oldEmail: str, newEmail: str, secret_key: str) -> str:
    return _encode_string_as_token(
        json.dumps({"old_email": oldEmail, "new_email": newEmail}), "activate", secret_key
    )


def decode_activation_token(token: str, secret_key: str) -> Optional[Dict]:
    one_day_in_secs = 60 * 60 * 24
    decodedData = _decode_string_from_token(token, "activate", secret_key, one_day_in_secs)
    if decodedData is None:
        return None
    else:
        decodedDict = json.loads(decodedData)
        return decodedDict


def encode_password_reset_token(email: str, secret_key: str) -> str:
    return _encode_string_as_token(email, "password-reset", secret_key)


def decode_password_reset_token(token: str, secret_key: str) -> Optional[str]:
    one_hour_in_secs = 60 * 60
    return _decode_string_from_token(token, "password-reset", secret_key, one_hour_in_secs)


TKey = TypeVar("TKey")
TPrio = TypeVar("TPrio")


class AddressablePriorityQueue(Generic[TKey, TPrio]):
    """
    A max-heap priority queue that supports efficient
    lookup/removal of arbitrary elements.
    """

    _heap: List[Tuple[TKey, TPrio]]
    _key_to_index: Dict[TKey, int]

    def __init__(self):
        self._heap = []
        self._key_to_index = {}

    def _swap(self, i: int, j: int):
        self._heap[i], self._heap[j] = self._heap[j], self._heap[i]
        self._key_to_index[self._heap[i][0]] = i
        self._key_to_index[self._heap[j][0]] = j

    def _sift_up(self, index: int):
        while index > 0:
            parent_index = (index - 1) // 2
            if self._heap[parent_index][1] < self._heap[index][1]:
                self._swap(parent_index, index)
                index = parent_index
            else:
                return

    def _sift_down(self, index: int):
        left_child = 2 * index + 1
        while left_child < len(self._heap):
            right_child = left_child + 1
            if (
                right_child < len(self._heap)
                and self._heap[right_child][1] > self._heap[left_child][1]
            ):
                max_child = right_child
            else:
                max_child = left_child
            if self._heap[index][1] < self._heap[max_child][1]:
                self._swap(index, max_child)
                index = max_child
                left_child = 2 * index + 1
            else:
                return

    def push(self, key: TKey, value: TPrio):
        self._heap.append((key, value))
        self._key_to_index[key] = len(self._heap) - 1
        self._sift_up(len(self._heap) - 1)

    def pop_max(self) -> Tuple[TKey, TPrio]:
        if len(self._heap) == 0:
            raise IndexError("pop from empty heap")
        result = self._heap[0]
        self._heap[0] = self._heap[-1]
        self._heap.pop()
        del self._key_to_index[result[0]]
        self._sift_down(0)
        return result

    def peek_max(self) -> Tuple[TKey, TPrio]:
        if len(self._heap) == 0:
            raise IndexError("peek on empty heap")
        return self._heap[0]

    def __str__(self) -> str:
        return f"{self._heap}"

    def __len__(self) -> int:
        return len(self._heap)

    def __contains__(self, key: TKey) -> bool:
        return key in self._key_to_index

    def __delitem__(self, key: TKey):
        if key not in self._key_to_index:
            raise KeyError(f"key {key} not in queue")
        index = self._key_to_index[key]
        self._swap(index, len(self._heap) - 1)
        key, prio = self._heap.pop()
        del self._key_to_index[key]
        if len(self._heap) < (
            index + 1
        ):  # deleted element was at end of list (swapped with itself previously)
            return
        elif self._heap[index][1] > prio:
            self._sift_up(index)
        else:
            self._sift_down(index)


def synchronized(lock_name: str):
    def wrap(f):
        def with_lock(self, *args, **kw):
            lock = getattr(self, lock_name)
            with lock:
                return f(self, *args, **kw)

        return with_lock

    return wrap


AUTH_HEADER_PATTERN = re.compile(r"Bearer ([a-zA-Z0-9_-]+)")


def auth_token_from_req(request: Request) -> Union[Tuple[str, None], Tuple[None, str]]:
    """
    Extracts the token from the Authorization header of a request. If the header
    is missing or malformed, returns `(None, error_message)`.
    """
    auth_header = request.headers.get("Authorization")
    if auth_header is None:
        return None, "No Authorization header provided!"
    match = AUTH_HEADER_PATTERN.match(auth_header)
    if match is None:
        return None, "Invalid Authorization header!"
    return match.group(1), None


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
