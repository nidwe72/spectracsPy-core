class VerdictLogicModuleParameters:
    # Input: the measured hue in degrees (0-360). Band edges are demo/provisional (concept §8) and
    # default to the perfect-centred demo values; pass overrides once real thresholds are calibrated.

    hue = None
    # Demo band edges sit between the playground's three reachable target hues (72 / 60 / 35).
    overRoastedBelowHue = 47.0   # hue < this -> too brown -> OVER-ROASTED
    underRoastedAboveHue = 66.0  # hue > this -> too green -> UNDER-ROASTED

    def setHue(self, hue):
        self.hue = hue

    def getHue(self):
        return self.hue

    def setOverRoastedBelowHue(self, hue):
        self.overRoastedBelowHue = hue

    def getOverRoastedBelowHue(self):
        return self.overRoastedBelowHue

    def setUnderRoastedAboveHue(self, hue):
        self.underRoastedAboveHue = hue

    def getUnderRoastedAboveHue(self):
        return self.underRoastedAboveHue
