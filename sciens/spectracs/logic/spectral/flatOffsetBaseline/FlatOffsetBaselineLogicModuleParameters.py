class FlatOffsetBaselineLogicModuleParameters:

    spectrum = None
    # Floor estimation mode (SPEC_capability_proof.md §7.0.1 (B)):
    #   "anchorMean" (DEFAULT) — the mean of A over a transparent anchor window [anchorLoNm, anchorHiNm]. Low
    #       variance (a mean, not an extreme-value min) and placed in the deep red, OUTSIDE every metric band, so
    #       it never guts a band it overlaps. Assumes the input is already de-spiked (a spike inside the window
    #       would bias the mean — the plugin de-spikes upstream).
    #   "medianMin" — the minimum of a median-filtered copy (the earlier self-robust estimator). Kept selectable
    #       for callers that pass a non-de-spiked spectrum and want the floor to reject spikes itself.
    floorMode = "anchorMean"
    anchorLoNm = 615.0
    anchorHiNm = 625.0
    floorMedianWindow = 7          # only used when floorMode == "medianMin"

    def setSpectrum(self, spectrum):
        self.spectrum = spectrum
        return self

    def getSpectrum(self):
        return self.spectrum

    def setFloorMode(self, floorMode):
        self.floorMode = floorMode
        return self

    def getFloorMode(self):
        return self.floorMode

    def setAnchorLoNm(self, anchorLoNm):
        self.anchorLoNm = anchorLoNm
        return self

    def getAnchorLoNm(self):
        return self.anchorLoNm

    def setAnchorHiNm(self, anchorHiNm):
        self.anchorHiNm = anchorHiNm
        return self

    def getAnchorHiNm(self):
        return self.anchorHiNm

    def setFloorMedianWindow(self, floorMedianWindow):
        self.floorMedianWindow = floorMedianWindow
        return self

    def getFloorMedianWindow(self):
        return self.floorMedianWindow
