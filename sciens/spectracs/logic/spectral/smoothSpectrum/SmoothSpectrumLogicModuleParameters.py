class SmoothSpectrumLogicModuleParameters:

    spectrum = None
    # Savitzky-Golay parameters. Defaults reproduce the historical behaviour (7 passes, window 10,
    # polyorder 3). Callers that need to preserve close features (e.g. calibration resolving the green
    # doublet) override with fewer passes / a smaller window — SPEC_dev_measure_bench (a).
    passes = 7
    window = 10
    polyorder = 3

    def setSpectrum(self, spectrum):
        self.spectrum = spectrum

    def getSpectrum(self):
        return self.spectrum

    def setPasses(self, passes):
        self.passes = passes
        return self

    def getPasses(self):
        return self.passes

    def setWindow(self, window):
        self.window = window
        return self

    def getWindow(self):
        return self.window

    def setPolyorder(self, polyorder):
        self.polyorder = polyorder
        return self

    def getPolyorder(self):
        return self.polyorder
