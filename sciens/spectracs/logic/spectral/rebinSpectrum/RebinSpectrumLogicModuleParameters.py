class RebinSpectrumLogicModuleParameters:

    spectrum = None
    start = 380
    stop = 780
    step = 1

    def setSpectrum(self, spectrum):
        self.spectrum = spectrum

    def getSpectrum(self):
        return self.spectrum

    def setStart(self, start):
        self.start = start

    def getStart(self):
        return self.start

    def setStop(self, stop):
        self.stop = stop

    def getStop(self):
        return self.stop

    def setStep(self, step):
        self.step = step

    def getStep(self):
        return self.step
