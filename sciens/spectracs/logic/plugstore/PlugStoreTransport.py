from typing import List, Optional, Tuple


class PlugStoreError(Exception):
    """The plug store could not complete a call (plug refused it, or the stored data is inconsistent)."""


class PlugStoreFull(PlugStoreError):
    """A large value would push the plug's free flash below the reserve (SPEC_shelly_instrument_memory.md §3.6)."""


class PlugStoreTransport:
    """The raw storage primitives of a plug, as PlugKeyValueStore needs them (SPEC_shelly_instrument_memory.md
    §4.7). Two storages: the native key-value store (small values) and script slots (large text, never started).
    Implementations: ShellyGen2PlugStoreTransport (the real plug), InMemoryPlugStoreTransport (tests)."""

    # --- native key-value store ---
    def kvsGet(self, key: str) -> Optional[str]:
        raise NotImplementedError

    def kvsSet(self, key: str, value: str):
        raise NotImplementedError

    def kvsDelete(self, key: str):
        raise NotImplementedError

    def kvsKeys(self, prefix: str) -> List[str]:
        raise NotImplementedError

    # --- script slots ---
    def scriptList(self) -> List[Tuple[int, str]]:
        """[(id, name)] of every script on the plug."""
        raise NotImplementedError

    def scriptCreate(self, name: str) -> int:
        raise NotImplementedError

    def scriptAppend(self, scriptId: int, text: str):
        raise NotImplementedError

    def scriptRead(self, scriptId: int, offset: int, length: int) -> Tuple[str, int]:
        """(data, bytesLeftAfterIt)."""
        raise NotImplementedError

    def scriptDelete(self, scriptId: int):
        raise NotImplementedError

    # --- flash ---
    def fsFree(self) -> int:
        raise NotImplementedError


class InMemoryPlugStoreTransport(PlugStoreTransport):
    """A plug in memory, with the limits measured on the real one (§7.2/§7.3): KVS values ≤ 253 JSON-escaped
    characters, 50 keys, script slots ≤ 65 535 bytes, flash shrinking as data is stored. `failAfterAppends` lets a
    test break a write in the middle (torn write)."""

    KVS_MAX_KEYS = 50
    KVS_MAX_VALUE = 253
    SLOT_MAX_BYTES = 65535

    def __init__(self, fsFree=126976):
        self.kvs = {}
        self.scripts = {}           # id -> [name, text]
        self.nextScriptId = 1
        self.freeBytes = fsFree
        self.failAfterAppends = None
        self.appends = 0

    def kvsGet(self, key):
        return self.kvs.get(key)

    def kvsSet(self, key, value):
        import json
        if len(json.dumps(value)) - 2 > self.KVS_MAX_VALUE:
            raise PlugStoreError("Invalid argument 'value': length should be less than 255!")
        if key not in self.kvs and len(self.kvs) >= self.KVS_MAX_KEYS:
            raise PlugStoreError("KVS full")
        self.kvs[key] = value

    def kvsDelete(self, key):
        self.kvs.pop(key, None)

    def kvsKeys(self, prefix):
        return sorted(k for k in self.kvs if k.startswith(prefix))

    def scriptList(self):
        return [(sid, entry[0]) for sid, entry in sorted(self.scripts.items())]

    def scriptCreate(self, name):
        sid = self.nextScriptId
        self.nextScriptId += 1
        self.scripts[sid] = [name, ""]
        return sid

    def scriptAppend(self, scriptId, text):
        self.appends += 1
        if self.failAfterAppends is not None and self.appends > self.failAfterAppends:
            raise PlugStoreError("connection lost (test)")
        entry = self.scripts[scriptId]
        if len((entry[1] + text).encode()) > self.SLOT_MAX_BYTES:
            raise PlugStoreError("Script length exceeded 65535 bytes limit!")
        entry[1] += text
        self.freeBytes -= len(text.encode())

    def scriptRead(self, scriptId, offset, length):
        data = self.scripts[scriptId][1].encode()
        piece = data[offset:offset + length]
        return piece.decode(), max(0, len(data) - offset - len(piece))

    def scriptDelete(self, scriptId):
        entry = self.scripts.pop(scriptId, None)
        if entry is not None:
            self.freeBytes += len(entry[1].encode())

    def fsFree(self):
        return self.freeBytes
