class LampSwitch:
    # The lamp behind one small interface (SPEC_lamp_switch.md §4.1, D7): one implementation per vendor plus
    # NoLampSwitch. Implementations block for at most their timeout and raise LampUnreachable / LampAuthFailed;
    # they hold no state of their own — LampService owns the clocks.

    def on(self, capSeconds):
        """Switch on and arm the device-side cap (the device switches itself off after capSeconds)."""
        raise NotImplementedError

    def off(self):
        raise NotImplementedError

    def status(self):
        """-> LampStatus"""
        raise NotImplementedError

    def describe(self):
        raise NotImplementedError

    def setTimeout(self, seconds):
        """Shorten the network timeout (shutdown uses 1 s, §14.2). No-op where there is no network."""
        pass

    def applyIndicator(self):
        """Set the device's own status light the way the app wants it (once per discovery). No-op by default."""
        pass

    def isSwitchable(self):
        """False for NoLampSwitch: the app cannot switch, the user does it at the socket."""
        return True
