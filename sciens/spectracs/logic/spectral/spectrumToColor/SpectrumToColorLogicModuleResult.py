class SpectrumToColorLogicModuleResult:

    # The rendered swatch (SpectralColor) — lightness pinned to Parameters.lightness.
    color = None
    # The measured HLS values (hue in degrees 0..360; lightness/saturation in 0..100), before the
    # swatch lightness override. Available for plugins that want the raw numbers (e.g. a hue verdict).
    hue = None
    lightness = None
    saturation = None

    def setColor(self, color):
        self.color = color

    def getColor(self):
        return self.color

    def setHue(self, hue):
        self.hue = hue

    def getHue(self):
        return self.hue

    def setLightness(self, lightness):
        self.lightness = lightness

    def getLightness(self):
        return self.lightness

    def setSaturation(self, saturation):
        self.saturation = saturation

    def getSaturation(self):
        return self.saturation
