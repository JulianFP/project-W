import re
from typing import Dict, List, Optional, Tuple, TypeVar, Generic

from flask import Request

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
        self._heap[i], self._heap[j] = \
            self._heap[j], self._heap[i]
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
            if right_child < len(self._heap) and \
                    self._heap[right_child][1] > self._heap[left_child][1]:
                max_child = right_child
            else:
                max_child = left_child
            if self._heap[index][1] < self._heap[max_child][1]:
                self._swap(index, max_child)
                index = max_child
                left_child = 2 * index + 1

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
        if self._heap[index][1] > prio:
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


def auth_token_from_req(request: Request) -> Tuple[str, None] | Tuple[None, str]:
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
