class LampDriver:
    # One vendor (SPEC_lamp_switch.md §4.2, D7): how to recognise its plugs on the LAN and how to talk to one.
    # Adding Tasmota later = one more subclass in LampDriverRegistry, nothing else changes.

    name = None
    mdnsServiceTypes = ()

    def probe(self, host, timeout=1.0):
        """-> LampDevice if `host` is a switchable plug of this vendor, else None. Never raises."""
        raise NotImplementedError

    def create(self, device, password=None):
        """-> LampSwitch for a probed device."""
        raise NotImplementedError

    def macFromSsid(self, ssid):
        """The MAC in this vendor's setup-mode SSID, or None if `ssid` is not one (§15.5)."""
        return None
