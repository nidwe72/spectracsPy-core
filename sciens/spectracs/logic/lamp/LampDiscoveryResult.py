class LampDiscoveryResult:
    # What a discovery run found (SPEC_lamp_switch.md §5). `chosen` is the plug asked for: the wanted device id
    # (the active instrument's serial), else the stored MAC — never just the first one (SPEC_shelly_instrument_memory
    # §11, R25); None when it is not among `devices`. `via` names the step that
    # found it ("stored" / "mdns" / "subnet") — for the log and the Settings page, not for logic.

    def __init__(self, devices=(), chosen=None, via=None):
        self.devices = list(devices)
        self.chosen = chosen
        self.via = via

    def others(self):
        return [device for device in self.devices if device != self.chosen]

    def __repr__(self):
        return "LampDiscoveryResult(chosen=%s, via=%s, devices=%s)" % (self.chosen, self.via, self.devices)
