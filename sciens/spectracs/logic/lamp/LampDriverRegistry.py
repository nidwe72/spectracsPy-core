from sciens.spectracs.logic.lamp.ShellyGen2Driver import ShellyGen2Driver


class LampDriverRegistry:
    # The vendors the app knows (SPEC_lamp_switch.md §4.2). Shelly Gen2 only for now (D7).

    __drivers = (ShellyGen2Driver(),)

    @staticmethod
    def drivers():
        return LampDriverRegistry.__drivers

    @staticmethod
    def byName(name):
        for driver in LampDriverRegistry.__drivers:
            if driver.name == name:
                return driver
        return None
