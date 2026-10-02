from sciens.spectracs.logic.lamp.LampStatus import LampStatus
from sciens.spectracs.logic.lamp.LampSwitch import LampSwitch
from sciens.spectracs.logic.lamp.ShellyHttp import ShellyHttp


class ShellyGen2LampSwitch(LampSwitch):
    # Shelly Plus Plug S (and any Gen2+ device with switch:0). Semantics verified on the real plug,
    # fw 1.3.3 (SPEC_lamp_switch.md §15.3, diagnostics/lamp_plug_blink.py --timer-check):
    #   - every on carries toggle_after — an on WITHOUT it cancels a running timer
    #   - a repeated on WITH it restarts the timer; off clears it
    #   - apower reads 0 W for ~1 s after on, then the real value

    SWITCH_ID = 0

    def __init__(self, host, password=None, timeout=2.0, label="Shelly"):
        self.http = ShellyHttp(host, password, timeout)
        self.label = label

    def on(self, capSeconds):
        self.http.rpc("Switch.Set", id=self.SWITCH_ID, on=True, toggle_after=int(capSeconds))

    def off(self):
        self.http.rpc("Switch.Set", id=self.SWITCH_ID, on=False)

    def status(self):
        reply = self.http.rpc("Switch.GetStatus", id=self.SWITCH_ID) or {}
        return LampStatus(isOn=reply.get("output", False), watts=reply.get("apower"),
                          timerRunning=reply.get("timer_duration") is not None)

    # The plug's LED ring when OFF: factory red at full brightness reads as an alarm next to the rig. A very dim
    # grey instead (Edwin 2026-10-02). Only the "off" colour is sent — the device merges it, "on" stays green.
    OFF_LED = {"rgb": [20, 20, 20], "brightness": 3}

    def applyIndicator(self):
        self.http.rpc("PLUGS_UI.SetConfig",
                      config={"leds": {"colors": {"switch:%d" % self.SWITCH_ID: {"off": self.OFF_LED}}}})

    def setTimeout(self, seconds):
        self.http.timeout = seconds

    def describe(self):
        return "%s %s" % (self.label, self.http.host)
