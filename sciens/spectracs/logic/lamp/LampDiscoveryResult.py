class LampDiscoveryResult:
    # What a discovery run found (SPEC_lamp_switch.md §5). `chosen` is the plug the app will use: the stored
    # MAC when it is among `devices`, else the first; None when nothing was found. `via` names the step that
    # found it ("stored" / "mdns" / "subnet") — for the log and the Settings page, not for logic.

    def __init__(self, devices=(), chosen=None, via=None):
        self.devices = list(devices)
        self.chosen = chosen
        self.via = via

    def others(self):
        return [device for device in self.devices if device != self.chosen]

    def __repr__(self):
        return "LampDiscoveryResult(chosen=%s, via=%s, devices=%s)" % (self.chosen, self.via, self.devices)
