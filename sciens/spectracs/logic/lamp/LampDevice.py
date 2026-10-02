class LampDevice:
    # A switchable plug found on the LAN (SPEC_lamp_switch.md §4.2/§5). Plain data: which driver speaks to it,
    # where it is, and its MAC — the MAC is the identity (the IP may change with DHCP).

    def __init__(self, driverName, host, mac, model=None, deviceId=None, authRequired=False):
        self.driverName = driverName
        self.host = host
        self.mac = (mac or "").upper().replace(":", "")
        self.model = model
        self.deviceId = deviceId
        self.authRequired = bool(authRequired)

    def describe(self):
        return "%s · %s · %s" % (self.model or self.driverName, self.host, self.formattedMac())

    def formattedMac(self):
        return ":".join(self.mac[i:i + 2] for i in range(0, len(self.mac), 2))

    def __eq__(self, other):
        return isinstance(other, LampDevice) and self.mac == other.mac and self.driverName == other.driverName

    def __hash__(self):
        return hash((self.driverName, self.mac))

    def __repr__(self):
        return "LampDevice(%s, %s, %s)" % (self.driverName, self.host, self.mac)
