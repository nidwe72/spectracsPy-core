import shutil
import subprocess

from sciens.spectracs.logic.lamp.LampDriverRegistry import LampDriverRegistry


class LampSetupHint:
    # Step 8b (SPEC_lamp_switch.md §15.5): notices a plug that still has to join the WLAN — the app never sets
    # one up itself (G1). Heuristic: an OPEN network whose SSID is a vendor setup SSID (Shelly: Shelly…-<MAC>).
    # A configured Shelly keeps broadcasting its own network, so an SSID whose MAC is already on the LAN is NOT
    # an unconfigured plug and is skipped.

    @staticmethod
    def unconfiguredSsids(wifiList, knownMacs=(), drivers=None):
        """Pure: `wifiList` = [(ssid, security)], `knownMacs` = MACs of plugs found on the LAN."""
        drivers = drivers if drivers is not None else LampDriverRegistry.drivers()
        known = {mac.upper().replace(":", "") for mac in knownMacs}
        hits = []
        for ssid, security in wifiList:
            if security not in ("", "--"):
                continue
            for driver in drivers:
                mac = driver.macFromSsid(ssid)
                if mac is not None and mac not in known and ssid not in hits:
                    hits.append(ssid)
        return hits

    @staticmethod
    def parseNmcli(output):
        """`nmcli -t -f SSID,SECURITY dev wifi list` -> [(ssid, security)]. -t escapes ':' in values as '\\:'."""
        rows = []
        for line in output.splitlines():
            fields, current, escaped = [], "", False
            for char in line:
                if escaped:
                    current += char
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif char == ":":
                    fields.append(current)
                    current = ""
                else:
                    current += char
            fields.append(current)
            if len(fields) >= 2 and fields[0]:
                rows.append((fields[0], fields[1]))
        return rows

    @staticmethod
    def scanWifi():
        """The PC's visible Wi-Fi networks; [] without nmcli or a Wi-Fi adapter (Linux only for now)."""
        if shutil.which("nmcli") is None:
            return []
        try:
            result = subprocess.run(["nmcli", "-t", "-f", "SSID,SECURITY", "dev", "wifi", "list"],
                                    capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.SubprocessError):
            return []
        return LampSetupHint.parseNmcli(result.stdout) if result.returncode == 0 else []

    @staticmethod
    def hintText(ssid):
        return ("Unconfigured Shelly “%s” found nearby. Connect to its Wi-Fi, open http://192.168.33.1 and add "
                "your WLAN under Settings → Wi-Fi (2.4 GHz). Then set a password and auto-off (30 min) there, "
                "and enter the password here." % ssid)
