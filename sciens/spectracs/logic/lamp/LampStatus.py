class LampStatus:
    # What a lamp switch reports (SPEC_lamp_switch.md §4.1). `watts` is None where the device has no meter;
    # `timerRunning` only says whether the device-side cap is armed — the remaining time is the APP's clock
    # (§14.2: device time is not trusted for arithmetic).

    def __init__(self, isOn, watts=None, timerRunning=False):
        self.isOn = bool(isOn)
        self.watts = watts
        self.timerRunning = bool(timerRunning)

    def __repr__(self):
        return "LampStatus(isOn=%s, watts=%s, timerRunning=%s)" % (self.isOn, self.watts, self.timerRunning)
