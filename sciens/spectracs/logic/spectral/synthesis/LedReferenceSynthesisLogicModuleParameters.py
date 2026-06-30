class LedReferenceSynthesisLogicModuleParameters:
    # nanometers: the axis to synthesise on (None -> 380..780). ledSet: list of (name, components, weight)
    # (None -> the default Avonec-shaped set in SpectrumSynthesisUtil).

    nanometers = None
    ledSet = None

    def setNanometers(self, nanometers):
        self.nanometers = nanometers

    def getNanometers(self):
        return self.nanometers

    def setLedSet(self, ledSet):
        self.ledSet = ledSet

    def getLedSet(self):
        return self.ledSet
