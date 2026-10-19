from sciens.spectracs.logic.lamp.LampErrors import ShellyRpcError
from sciens.spectracs.logic.lamp.ShellyHttp import ShellyHttp
from sciens.spectracs.logic.plugstore.PlugStoreTransport import PlugStoreError, PlugStoreTransport


class ShellyGen2PlugStoreTransport(PlugStoreTransport):
    """PlugStoreTransport on a real Shelly Gen2 plug (SPEC_shelly_instrument_memory.md §4.7, measured in §7.2/§7.3).
    Everything goes over POST /rpc (script pieces are too large for a GET query). Per-key KVS.Get on purpose:
    KVS.GetMany refuses any answer over 2 048 bytes on fw 1.3.3. Reads of script slots are always done in pieces
    by the store; a whole-slot GetCode of 49 KB rebooted the plug."""

    NOT_FOUND = -105            # KVS.Get on a missing key

    def __init__(self, host, password=None, timeout=10.0):
        self.http = ShellyHttp(host, password=password, timeout=timeout)

    def __call(self, method, **params):
        try:
            return self.http.post(method, **params)
        except ShellyRpcError as error:
            raise PlugStoreError("%s refused: %s" % (method, error.message)) from error

    def kvsGet(self, key):
        try:
            result = self.http.post("KVS.Get", key=key)
        except ShellyRpcError as error:
            if error.code == self.NOT_FOUND or "not found" in (error.message or "").lower():
                return None
            raise PlugStoreError("KVS.Get refused: %s" % error.message) from error
        return (result or {}).get("value")

    def kvsSet(self, key, value):
        self.__call("KVS.Set", key=key, value=value)

    def kvsDelete(self, key):
        try:
            self.http.post("KVS.Delete", key=key)
        except ShellyRpcError as error:
            if error.code != self.NOT_FOUND and "not found" not in (error.message or "").lower():
                raise PlugStoreError("KVS.Delete refused: %s" % error.message) from error

    def kvsKeys(self, prefix):
        keys = (self.__call("KVS.List", match=prefix + "*") or {}).get("keys") or {}
        return sorted(keys.keys() if isinstance(keys, dict) else keys)

    def scriptList(self):
        scripts = (self.__call("Script.List") or {}).get("scripts") or []
        return [(entry["id"], entry.get("name") or "") for entry in scripts]

    def scriptCreate(self, name):
        return self.__call("Script.Create", name=name)["id"]

    def scriptAppend(self, scriptId, text):
        self.__call("Script.PutCode", id=scriptId, code=text, append=True)

    def scriptRead(self, scriptId, offset, length):
        result = self.__call("Script.GetCode", id=scriptId, offset=offset, len=length) or {}
        return result.get("data") or "", int(result.get("left") or 0)

    def scriptDelete(self, scriptId):
        self.__call("Script.Delete", id=scriptId)

    def fsFree(self):
        return int(self.__call("Sys.GetStatus")["fs_free"])
