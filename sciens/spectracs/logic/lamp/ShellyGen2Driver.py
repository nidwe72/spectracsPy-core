import re

from sciens.spectracs.logic.lamp.LampDevice import LampDevice
from sciens.spectracs.logic.lamp.LampDriver import LampDriver
from sciens.spectracs.logic.lamp.LampErrors import LampUnreachable
from sciens.spectracs.logic.lamp.ShellyGen2LampSwitch import ShellyGen2LampSwitch
from sciens.spectracs.logic.lamp.ShellyHttp import ShellyHttp


class ShellyGen2Driver(LampDriver):
    # Shelly Gen2+ (SPEC_lamp_switch.md §5). `GET /shelly` answers without auth; Edwin's plug reports
    # gen=2, app="PlusPlugS", model="SNPL-00112EU". Accept gen >= 2 (the Plus Plug S Gen3 speaks the same RPC,
    # §14 R8); without a password the switch:0 component is confirmed with Switch.GetStatus, with one it cannot
    # be checked before login and is accepted.

    name = "shelly-gen2"
    mdnsServiceTypes = ("_shelly._tcp.local.",)
    SETUP_SSID = re.compile(r"^Shelly[A-Za-z0-9]*-([0-9A-Fa-f]{12})$")

    def probe(self, host, timeout=1.0):
        http = ShellyHttp(host, timeout=timeout)
        try:
            info = http.get("/shelly") or {}
        except LampUnreachable:
            return None
        if not isinstance(info, dict) or not isinstance(info.get("gen"), int) or info["gen"] < 2:
            return None
        authRequired = bool(info.get("auth_en"))
        if not authRequired:
            try:
                status = http.rpc("Switch.GetStatus", id=0)
            except LampUnreachable:
                return None
            if not isinstance(status, dict) or "output" not in status:
                return None
        return LampDevice(self.name, host, info.get("mac"), model=info.get("app") or info.get("model"),
                          deviceId=info.get("id"), authRequired=authRequired, firmware=info.get("ver"))

    def create(self, device, password=None):
        return ShellyGen2LampSwitch(device.host, password, label="Shelly %s" % (device.model or ""))

    def macFromSsid(self, ssid):
        match = self.SETUP_SSID.match(ssid or "")
        return match.group(1).upper() if match else None
