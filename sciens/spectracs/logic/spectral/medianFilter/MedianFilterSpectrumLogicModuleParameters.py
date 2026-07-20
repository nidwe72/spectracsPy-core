class MedianFilterSpectrumLogicModuleParameters:

    spectrum = None
    # Moving-median (rank) window. Coerced to odd. Default 7 suits the flat-offset floor estimate.
    kernelSize = 7

    def setSpectrum(self, spectrum):
        self.spectrum = spectrum
        return self

    def getSpectrum(self):
        return self.spectrum

    def setKernelSize(self, kernelSize):
        self.kernelSize = kernelSize
        return self

    def getKernelSize(self):
        return self.kernelSize
