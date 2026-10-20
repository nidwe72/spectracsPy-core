import asyncio
import hashlib
import json
import os
import re
import struct
from typing import List, Optional

from sciens.spectracs.logic.lamp.LampErrors import LampAuthFailed, LampUnreachable, ShellyRpcError


class BleShelly:
    """A Shelly seen over Bluetooth: its BLE address and the MAC its name carries (ShellyPlusPlugS-E465B8B6B4F8)."""

    def __init__(self, address, name, mac, rssi=None):
        self.address = address
        self.name = name
        self.mac = mac
        self.rssi = rssi

    def describe(self):
        return "%s  (%s dBm)" % (self.name, self.rssi) if self.rssi is not None else self.name

    def __repr__(self):
        return "BleShelly(%s, %s)" % (self.address, self.name)


class ShellyBleRpc:
    """Shelly Gen2 JSON-RPC over Bluetooth LE (SPEC_shelly_instrument_memory.md §11.5/§11.6.1, R30) — the same calls
    as over HTTP, through the GATT service `_mOS_RPC_SVC_ID_`: write the frame length (4 bytes, big-endian) to tx_ctl
    and the JSON frame to data; read the answer length from rx_ctl, then data until complete. No pairing.

    Measured on the real plugs (fw 0.13.0 and 1.3.3, 2026-10-20): a set password guards BLE exactly like HTTP (digest,
    SHA-256; only Shelly.GetDeviceInfo stays open). ⚠ BlueZ on Edwin's PC only connects WHILE a scan runs — a connect
    after the scan ends reports "device not found" — so every call connects inside the scanner.

    `bleak` is optional and imported lazily: without it `available()` is False and the UI hides "Add new plug"."""

    SERVICE = "5f6d4f53-5f52-5043-5f53-56435f49445f"
    DATA = "5f6d4f53-5f52-5043-5f64-6174615f5f5f"
    TX_CTL = "5f6d4f53-5f52-5043-5f74-785f63746c5f"
    RX_CTL = "5f6d4f53-5f52-5043-5f72-785f63746c5f"
    NAME = re.compile(r"^(Shelly[A-Za-z0-9]*)-([0-9A-Fa-f]{12})$")
    CHUNK = 200
    SCAN_SECONDS = 10.0
    CONNECT_SECONDS = 30.0

    @staticmethod
    def available() -> bool:
        try:
            import bleak  # noqa: F401
            return True
        except ImportError:
            return False

    # --- scan ---
    def scan(self, seconds: float = None) -> List[BleShelly]:
        return asyncio.run(self.__scan(seconds or self.SCAN_SECONDS))

    async def __scan(self, seconds):
        from bleak import BleakScanner
        found = await BleakScanner.discover(timeout=seconds, return_adv=True)
        result = []
        for address, (device, advertisement) in found.items():
            name = advertisement.local_name or device.name or ""
            match = self.NAME.match(name)
            if match:
                result.append(BleShelly(address, name, match.group(2).upper(), advertisement.rssi))
        return sorted(result, key=lambda shelly: -(shelly.rssi or -999))

    # --- calls ---
    def call(self, address: str, method: str, params: Optional[dict] = None, password: Optional[str] = None):
        """The `result` of one RPC, or raises LampAuthFailed (401) / ShellyRpcError / LampUnreachable."""
        try:
            answer = asyncio.run(self.__call(address, method, params, password))
        except (LampAuthFailed, ShellyRpcError):
            raise
        except Exception as error:
            raise LampUnreachable("Bluetooth %s: %s" % (address, error)) from error
        error = answer.get("error")
        if error:
            if error.get("code") == 401:
                raise LampAuthFailed("%s needs its password over Bluetooth" % address)
            raise ShellyRpcError(error.get("code"), error.get("message"))
        return answer.get("result")

    def joinWlan(self, address: str, ssid: str, wlanPassword: str, plugPassword: Optional[str] = None):
        """E10/§11.5: the plug joins `ssid` — nothing else is written."""
        return self.call(address, "WiFi.SetConfig",
                         {"config": {"sta": {"ssid": ssid, "pass": wlanPassword, "enable": True}}}, plugPassword)

    def wifiStatus(self, address: str, plugPassword: Optional[str] = None) -> dict:
        return self.call(address, "WiFi.GetStatus", None, plugPassword) or {}

    async def __call(self, address, method, params, password):
        from bleak import BleakClient, BleakScanner
        seen = asyncio.Event()
        box = {}

        def onAdvertisement(device, advertisement):
            if device.address.upper() == address.upper():
                box["device"] = device
                seen.set()

        async with BleakScanner(onAdvertisement):
            await asyncio.wait_for(seen.wait(), self.SCAN_SECONDS * 3)
            async with BleakClient(box["device"], timeout=self.CONNECT_SECONDS) as client:
                frame = {"id": 1, "src": "spectracs", "method": method}
                if params is not None:
                    frame["params"] = params
                answer = await self.__frame(client, frame)
                challenge = (answer.get("error") or {})
                if challenge.get("code") == 401 and password:
                    frame["id"] = 2
                    frame["auth"] = self.__digest(json.loads(challenge["message"]), password)
                    answer = await self.__frame(client, frame)
                return answer

    async def __frame(self, client, frame):
        raw = json.dumps(frame).encode()
        await client.write_gatt_char(self.TX_CTL, struct.pack(">I", len(raw)), response=True)
        for offset in range(0, len(raw), self.CHUNK):
            await client.write_gatt_char(self.DATA, raw[offset:offset + self.CHUNK], response=True)
        length = 0
        for _ in range(100):
            length = struct.unpack(">I", bytes(await client.read_gatt_char(self.RX_CTL)))[0]
            if length:
                break
            await asyncio.sleep(0.1)
        buffer = b""
        while len(buffer) < length:
            buffer += bytes(await client.read_gatt_char(self.DATA))
        return json.loads(buffer.decode())

    @staticmethod
    def __digest(challenge, password):
        # Shelly's JSON-RPC digest (the same as its HTTP one): SHA-256, ha2 over the fixed "dummy_method:dummy_uri".
        sha = lambda text: hashlib.sha256(text.encode()).hexdigest()
        cnonce = os.urandom(8).hex()
        ha1 = sha("admin:%s:%s" % (challenge["realm"], password))
        ha2 = sha("dummy_method:dummy_uri")
        response = sha("%s:%s:%s:%s:auth:%s" % (ha1, challenge["nonce"], challenge.get("nc", 1), cnonce, ha2))
        return {"realm": challenge["realm"], "username": "admin", "nonce": challenge["nonce"], "cnonce": cnonce,
                "response": response, "algorithm": "SHA-256"}
