class OilSampleSynthesisLogicModuleParameters:
    # reference: the synthesised REFERENCE spectrum. Provide EITHER targetHue (the module tunes the roast
    # so the transmission colour lands on it) OR roast directly (in [0,1]).

    reference = None
    targetHue = None
    roast = None

    def setReference(self, reference):
        self.reference = reference

    def getReference(self):
        return self.reference

    def setTargetHue(self, targetHue):
        self.targetHue = targetHue

    def getTargetHue(self):
        return self.targetHue

    def setRoast(self, roast):
        self.roast = roast

    def getRoast(self):
        return self.roast
