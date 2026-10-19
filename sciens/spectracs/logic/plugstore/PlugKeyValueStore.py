import base64
import hashlib
import json
import re
from typing import List, Optional, Union

from sciens.spectracs.logic.plugstore.PlugStoreTransport import PlugStoreError, PlugStoreFull, PlugStoreTransport


class PlugKeyValueStore:
    """One key-value interface over both storages of the plug (SPEC_shelly_instrument_memory.md §4.7, N16).

    Small values (≤ 253 JSON-escaped characters, §7.2) live in the native KVS under "spectracs_<key>". Larger
    values are base64'd into script slots "spectracs_<key>~<gen>~<n>" (never started) plus a META key
    "spectracs_m_<key>" = {t, s, n, h, g} in the native KVS. The meta key is written LAST and is the commit point:
    a write that breaks in the middle leaves the previous value valid, and orphan slots are removed on the next
    set(). Compression and signing are the caller's business; this only stores text or bytes faithfully.
    """

    PREFIX = "spectracs_"
    META = "spectracs_m_"
    NATIVE_MAX = 253                    # JSON-escaped characters (§7.2)
    SLOT_CHARS = 60000                  # < 65 535 bytes per slot (§7.3); base64 is ASCII ⇒ chars = bytes
    WRITE_PIECE = 8192                  # Script.PutCode append size
    READ_PIECE = 4096                   # ⛔ never more: a whole-slot GetCode rebooted the plug (§7.3)
    FS_RESERVE = 16 * 1024              # flash kept free for the plug's own settings (§3.6)
    KEY_PATTERN = re.compile(r"^[A-Za-z0-9_-]{1,30}$")   # 42-char KVS keys minus "spectracs_m_" (12); no dots

    def __init__(self, transport: PlugStoreTransport):
        self.transport = transport

    # --- public -----------------------------------------------------------------------------------------
    def set(self, key: str, value: Union[str, bytes], replaceInPlace: bool = False):
        """Store `value`. A large value is written atomically: the old one stays valid until the new one is read
        back, so for a moment both are on the plug. When there is no room for both (measured 2026-10-19: a 93 KB
        value cannot be rewritten in 124 KiB) and `replaceInPlace` is set, the old value is deleted FIRST — the key
        is then empty if the write breaks. Only for a caller that can simply write again (the factory tool)."""
        self.__checkKey(key)
        kind, text = ("b", base64.b64encode(value).decode()) if isinstance(value, bytes) else ("s", value)
        native = kind + ":" + text
        if len(json.dumps(native)) - 2 <= self.NATIVE_MAX:
            self.transport.kvsSet(self.PREFIX + key, native)
            self.__dropLarge(key)
            return
        # Large values are ALWAYS base64 in the slots (ASCII ⇒ bytes = characters, nothing to escape); `t` says
        # whether get() hands back bytes or decodes them to text again.
        raw = value if isinstance(value, bytes) else value.encode()
        self.__setLarge(key, kind, base64.b64encode(raw).decode(), replaceInPlace)
        self.transport.kvsDelete(self.PREFIX + key)

    def get(self, key: str) -> Optional[Union[str, bytes]]:
        self.__checkKey(key)
        meta = self.__meta(key)
        if meta is not None:
            return self.__getLarge(meta)
        native = self.transport.kvsGet(self.PREFIX + key)
        return None if native is None else self.__decode(native[:1], native[2:])

    def sha256(self, key: str) -> Optional[str]:
        """The stored text's sha256 for a large value, without reading its slots (one KVS.Get) — so a caller can
        skip a rewrite of unchanged data (§9.5). None for a small or missing value."""
        meta = self.__meta(key)
        return None if meta is None else meta["h"]

    def delete(self, key: str):
        self.__checkKey(key)
        self.__dropLarge(key)
        self.transport.kvsDelete(self.PREFIX + key)

    def keys(self) -> List[str]:
        result = set()
        for name in self.transport.kvsKeys(self.PREFIX):
            if name.startswith(self.META):
                result.add(name[len(self.META):])
            else:
                result.add(name[len(self.PREFIX):])
        return sorted(result)

    def removeOrphans(self):
        """Delete our script slots that no meta key references (left by a write that broke in the middle)."""
        referenced = set()
        for name in self.transport.kvsKeys(self.META):
            meta = self.__parseMeta(self.transport.kvsGet(name))
            if meta is not None:
                referenced.update(meta["s"])
        for scriptId, name in self.transport.scriptList():
            if name.startswith(self.PREFIX) and scriptId not in referenced:
                self.transport.scriptDelete(scriptId)

    # --- large values -----------------------------------------------------------------------------------
    def __setLarge(self, key, kind, text, replaceInPlace):
        self.removeOrphans()
        old = self.__meta(key)
        generation = (old["g"] + 1) if old else 1
        pieces = [text[i:i + self.SLOT_CHARS] for i in range(0, len(text), self.SLOT_CHARS)]
        needed = len(text) + 4096 * len(pieces)                     # flash is handed out in 4 KiB blocks
        if old is not None and replaceInPlace and self.transport.fsFree() - needed < self.FS_RESERVE:
            self.__dropLarge(key)
            old = None
        if self.transport.fsFree() - needed < self.FS_RESERVE:
            raise PlugStoreFull("%d bytes would leave less than %d KiB free on the plug"
                                % (len(text), self.FS_RESERVE // 1024))
        slots = []
        try:
            for index, piece in enumerate(pieces):
                scriptId = self.transport.scriptCreate("%s%s~%d~%d" % (self.PREFIX, key, generation, index))
                slots.append(scriptId)
                for start in range(0, len(piece), self.WRITE_PIECE):
                    self.transport.scriptAppend(scriptId, piece[start:start + self.WRITE_PIECE])
            meta = {"t": kind, "s": slots, "n": len(text), "h": hashlib.sha256(text.encode()).hexdigest(),
                    "g": generation}
            if self.__readSlots(meta) != text:                     # read back before committing
                raise PlugStoreError("read-back of %s differs from what was written" % key)
        except Exception:
            for scriptId in slots:                                  # best effort; removeOrphans catches the rest
                try:
                    self.transport.scriptDelete(scriptId)
                except Exception:
                    pass
            raise
        self.transport.kvsSet(self.META + key, json.dumps(meta, separators=(",", ":")))   # ← the commit point
        if old is not None:
            for scriptId in old["s"]:
                self.transport.scriptDelete(scriptId)

    def __getLarge(self, meta):
        text = self.__readSlots(meta)
        if len(text) != meta["n"] or hashlib.sha256(text.encode()).hexdigest() != meta["h"]:
            return None                                             # never a half value
        raw = base64.b64decode(text)
        return raw if meta["t"] == "b" else raw.decode()

    def __readSlots(self, meta):
        parts = []
        for scriptId in meta["s"]:
            offset = 0
            while True:
                data, left = self.transport.scriptRead(scriptId, offset, self.READ_PIECE)
                parts.append(data)
                offset += len(data.encode())
                if left <= 0 or not data:
                    break
        return "".join(parts)

    def __dropLarge(self, key):
        meta = self.__meta(key)
        if meta is None:
            return
        self.transport.kvsDelete(self.META + key)
        for scriptId in meta["s"]:
            self.transport.scriptDelete(scriptId)

    # --- helpers ----------------------------------------------------------------------------------------
    def __meta(self, key):
        return self.__parseMeta(self.transport.kvsGet(self.META + key))

    @staticmethod
    def __parseMeta(raw):
        if raw is None:
            return None
        try:
            meta = json.loads(raw) if isinstance(raw, str) else raw
            return meta if {"t", "s", "n", "h", "g"} <= set(meta) else None
        except (ValueError, TypeError):
            return None

    @staticmethod
    def __decode(kind, text):
        return base64.b64decode(text) if kind == "b" else text

    def __checkKey(self, key):
        if not self.KEY_PATTERN.match(key or "") or key.startswith("m_"):
            raise ValueError("plug store key %r: 1–30 of [A-Za-z0-9_-], not starting with 'm_'" % key)
