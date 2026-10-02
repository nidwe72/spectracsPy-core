from sciens.spectracs.logic.lamp.LampStatus import LampStatus
from sciens.spectracs.logic.lamp.LampSwitch import LampSwitch


class NoLampSwitch(LampSwitch):
    # No plug: the lamp is switched by hand at the socket (D10), or there is no lamp at all (virtual device,
    # §10). Does nothing, never fails.

    def on(self, capSeconds):
        pass

    def off(self):
        pass

    def status(self):
        return LampStatus(isOn=False)

    def describe(self):
        return "no lamp plug"

    def isSwitchable(self):
        return False
