class SpectrumToColorLogicModuleParameters:

    spectrum = None
    # Fixed lightness of the rendered swatch (0..1). The measured lightness is reported on the Result,
    # but the swatch colour pins lightness to this value (default 0.20) so weak/dark spectra still render
    # as a visible, comparable hue chip. Override per call if a plugin wants a different swatch lightness.
    lightness = 0.20

    def setSpectrum(self, spectrum):
        self.spectrum = spectrum

    def getSpectrum(self):
        return self.spectrum

    def setLightness(self, lightness):
        self.lightness = lightness

    def getLightness(self):
        return self.lightness
