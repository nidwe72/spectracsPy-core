import numpy as np

from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.SpectralColor import SpectralColor


class SpectralColorUtil(Singleton):
    # Qt-free (S1b): returns SpectralColor and reads only the QColor-shaped accessors, so a QColor still
    # works as an argument -- which it must, because the camera hands `colorsByPixelIndices` QColors to
    # hueSimilarity/channelDominance from the app-side calibration path. See SpectralColor's docstring.

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
        result=SpectralColor.fromRgb(self.adjustColor(red, factor), self.adjustColor(green, factor), self.adjustColor(blue, factor))
        return result

    def hueSimilarity(self, color: SpectralColor, referenceColor: SpectralColor) -> float:
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

    def channelDominance(self, color: SpectralColor, kind: str) -> float:
        """Per-channel dominance — a ratio that still discriminates at LOW saturation (where hue is unreliable), so it
        is the robust colour SELECTOR (SPEC §13.4). Normalised to [0,1]. kind in {green,blue,cyan,red}."""
        if color is None:
            return 0.0
        r, g, b = color.red(), color.green(), color.blue()
        value = {"green": g - max(r, b), "blue": b - max(r, g),
                 "cyan": min(g, b) - r, "red": r - max(g, b)}.get(kind, 0.0)
        return max(0.0, value / 255.0)

    # --- pixel-intensity reductions (SPEC_capture_quality.md §15) -----------------------------------------
    # "The gray of a pixel." Lives here so it is ONE definition, not written inline across the capture code.
    # toGrayMaximum is the DEFAULT (radiometric): the brightest channel = the Bayer channel that actually saw
    # that wavelength, so blue is not suppressed. toGrayLuminance is the OLD photometric Qt-qGray weighting
    # (weights blue only 5/32 -> under-reads blue ~3x). The scalar forms take a QColor-shaped colour; the
    # *Array forms are the vectorized siblings for the per-column reduction hot loop.

    def toGrayMaximum(self, color):
        """Radiometric intensity of a pixel = the brightest channel (SPEC §15, the default)."""
        return max(color.red(), color.green(), color.blue())

    def toGrayLuminance(self, color):
        """Photometric luminance = Qt qGray weighting (11,16,5)/32 — the OLD reduction, kept for comparison."""
        return (11 * color.red() + 16 * color.green() + 5 * color.blue()) // 32

    def toGrayMean(self, color):
        """Unweighted channel mean — all channels weighted equally."""
        return (color.red() + color.green() + color.blue()) // 3

    def toGrayMaximumArray(self, r, g, b):
        """Vectorized toGrayMaximum for the per-column reduction (numpy channel arrays or scalars)."""
        return np.maximum(np.maximum(r, g), b)

    def toGrayLuminanceArray(self, r, g, b):
        """Vectorized toGrayLuminance (the old Qt-qGray weighting)."""
        return (11.0 * r + 16.0 * g + 5.0 * b) / 32.0

    def toGrayMeanArray(self, r, g, b):
        """Vectorized toGrayMean."""
        return (r + g + b) / 3.0

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

    def getColorDifference(self,color1:SpectralColor,color2:SpectralColor):

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

    def spectrumToColor(self, spectrum) -> SpectralColor:
        """
        Evaluate a processed spectrum (on the 380-780 nm grid, normalized) into a perceptual swatch
        colour. Thin façade over SpectrumToColorLogicModule (which owns the colour/colorsys/rgbxy
        weight); imported lazily so this util stays light for its many wavelengthToColor callers.
        Returns a SpectralColor; the measured HLS values stay on the module's Result if needed later.
        """
        from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModule import SpectrumToColorLogicModule
        from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModuleParameters import SpectrumToColorLogicModuleParameters

        parameters = SpectrumToColorLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        result = SpectrumToColorLogicModule().spectrumToColor(parameters)
        return result.getColor()

