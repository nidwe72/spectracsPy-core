from PySide6.QtGui import QColor

from sciens.base.Singleton import Singleton


class SpectralColorUtil(Singleton):

    def wavelengthToColor(self,nm):
        """
        Converts a wavelength between 380 and 780 nm to an RGB color tuple.
        Argument:
            nm: Wavelength in nanometers.
        Returns:
            a 3-tuple (red, green, blue) of integers in the range 0-255.
        """

        if nm < 380 or nm > 780:
            raise ValueError("wavelength out of range")
        red = 0.0
        green = 0.0
        blue = 0.0
        # Calculate intensities in the different wavelength bands.
        if nm < 440:
            red = -(nm - 440.0) / (440.0 - 380.0)
            blue = 1.0
        elif nm < 490:
            green = (nm - 440.0) / (490.0 - 440.0)
            blue = 1.0
        elif nm < 510:
            green = 1.0
            blue = -(nm - 510.0) / (510.0 - 490.0)
        elif nm < 580:
            red = (nm - 510.0) / (580.0 - 510.0)
            green = 1.0
        elif nm < 645:
            red = 1.0
            green = -(nm - 645.0) / (645.0 - 580.0)
        else:
            red = 1.0
        # Let the intensity fall off near the vision limits.
        if nm < 420:
            factor = 0.3 + 0.7 * (nm - 380.0) / (420.0 - 380.0)
        elif nm < 701:
            factor = 1.0
        else:
            factor = 0.3 + 0.7 * (780.0 - nm) / (780.0 - 700.0)
        # Return the calculated values in an (R,G,B) tuple.
        result=QColor.fromRgb(self.adjustColor(red, factor), self.adjustColor(green, factor), self.adjustColor(blue, factor))
        return result

    def hueSimilarity(self, color: QColor, referenceColor: QColor) -> float:
        """Soft, interval-free colour match (SPEC_capture_quality.md §13.4): saturation-weighted cosine closeness of
        a pixel's hue to a reference hue. 1.0 = same hue & fully saturated; 0.0 when achromatic (low sat/value) or the
        hue is >=90 deg away. Reference colours come from wavelengthToColor(target_nm), so there are no hard-coded hue
        cutoffs. hue-similarity is a soft CONFIDENCE signal — it can disagree with a camera's rendering, so callers use
        channelDominance() as the robust selector."""
        import math
        if color is None or referenceColor is None:
            return 0.0
        if color.valueF() < 0.10 or color.saturationF() < 0.12:
            return 0.0
        h1, h2 = color.hueF(), referenceColor.hueF()
        if h1 < 0 or h2 < 0:
            return 0.0
        return float(color.saturationF()) * max(0.0, math.cos(math.radians((h1 - h2) * 360.0)))

    def channelDominance(self, color: QColor, kind: str) -> float:
        """Per-channel dominance — a ratio that still discriminates at LOW saturation (where hue is unreliable), so it
        is the robust colour SELECTOR (SPEC §13.4). Normalised to [0,1]. kind in {green,blue,cyan,red}."""
        if color is None:
            return 0.0
        r, g, b = color.red(), color.green(), color.blue()
        value = {"green": g - max(r, b), "blue": b - max(r, g),
                 "cyan": min(g, b) - r, "red": r - max(g, b)}.get(kind, 0.0)
        return max(0.0, value / 255.0)

    def adjustColor(self,color, factor):
        if color < 0.01:
            return 0
        max_intensity = 255
        gamma = 0.80
        rv = int(round(max_intensity * (color * factor) ** gamma))
        if rv < 0:
            return 0
        if rv > max_intensity:
            return max_intensity
        return rv

    def getColorDifference(self,color1:QColor,color2:QColor):

        # colormath pulls networkx -> bz2 (a stdlib module p4a doesn't build for the arm64 target).
        # Import lazily so the app boots without it; this delta-E path is only exercised during
        # colour comparison, not at startup or on the virtual pipeline's colour-conversion step.
        from colormath.color_objects import sRGBColor, LabColor
        from colormath.color_conversions import convert_color
        from colormath.color_diff import delta_e_cie2000

        color1_rgb = sRGBColor(color1.redF(), color1.greenF(), color1.blueF());
        color2_rgb = sRGBColor(color2.redF(), color2.greenF(), color2.blueF());
        color1_lab = convert_color(color1_rgb, LabColor);
        color2_lab = convert_color(color2_rgb, LabColor);
        delta_e = delta_e_cie2000(color1_lab, color2_lab);

        return delta_e

    def spectrumToColor(self, spectrum) -> QColor:
        """
        Evaluate a processed spectrum (on the 380-780 nm grid, normalized) into a perceptual swatch
        colour. Thin façade over SpectrumToColorLogicModule (which owns the colour/colorsys/rgbxy
        weight); imported lazily so this util stays light for its many wavelengthToColor callers.
        Returns a QColor; the measured HLS values stay on the module's Result if needed later.
        """
        from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModule import SpectrumToColorLogicModule
        from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModuleParameters import SpectrumToColorLogicModuleParameters

        parameters = SpectrumToColorLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        result = SpectrumToColorLogicModule().spectrumToColor(parameters)
        return result.getColor()

