import numpy as np

from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.SpectralColor import SpectralColor

# --- gamma decode (SPEC_capture_quality.md §17) ------------------------------------------------------
# The camera delivers 8-bit sRGB-ish ENCODED pixels: v = v_linear^(1/gamma). Relative-intensity maths
# (T = S/R, and above all the CIE colour integral) wants LINEAR light, so the measurement extraction
# decodes before it reduces channels. PURE POWER LAW, deliberately not the piecewise sRGB EOTF — the
# real curve's linear toe rescales the Soret band by a SAMPLE-DEPENDENT amount and costs 24% of the
# pumpkin class separation for no colour gain (§17.5.2, measured). Do not "fix" this to the standard.
#
# Scale-PRESERVING: f(v) = 255*(v/255)^gamma keeps f(0)=0 and f(255)=255, so the saturation/dead mask
# in ImageSpectrumAcquisitionLogicModule keeps its exact meaning and plots/logs keep their DN-ish range.
# A [0,1] normalization would silently disable that mask (§17.7/14).
#
# The LUT lives at MODULE level, not on the singleton: Singleton hands out ONE instance per process,
# shared by the video and GUI threads (and by every unit test in a run), so a mutable gamma stored on
# it would be cross-thread and cross-test state (§17.7/13). Gamma is passed in, never stored.
DEFAULT_CAPTURE_GAMMA = 2.2
CAPTURE_DECODE_DESCRIPTOR = "pow%.1f" % DEFAULT_CAPTURE_GAMMA   # stamped into the report JSON (§17.6/8)

_LUT_CACHE = {}


def _gammaLut(gamma):
    # 256-entry float32 decode table. Computed in float64, stored float32: a float64 LUT would silently
    # upgrade the whole per-frame array (2x memory, and the dtype flows on into the Tukey estimator).
    lut = _LUT_CACHE.get(gamma)
    if lut is None:
        lut = ((np.arange(256, dtype=np.float64) / 255.0) ** float(gamma) * 255.0).astype(np.float32)
        _LUT_CACHE[gamma] = lut
    return lut


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

    # --- gamma decode / encode (SPEC_capture_quality.md §17) ---------------------------------------
    # Per-camera gamma SEAM (not built, §17.7/22): a per-sensor exponent belongs in SpectrometerSensorUtil
    # beside WB-Kelvin and exposure — but the extractor holds no sensor handle, so wiring it means threading
    # one through the capture path. Every camera starts at 2.2, and §17.5.1 shows a wrong exponent costs
    # colour and absolute absorbance only, never the band ratio. Build it when a second camera is measured:
    # pass the exponent into decodeGamma* and the LUT cache does the rest.

    def captureGamma(self):
        """The decode exponent in force. One place to read it from (report stamp, probes, tests)."""
        return DEFAULT_CAPTURE_GAMMA

    def captureDecodeDescriptor(self):
        """Machine-readable name of the decode model, stamped into the report JSON so a later reader can
        tell a linearized run from a pre-§17 one instead of inferring it from the date (§17.6/8)."""
        return CAPTURE_DECODE_DESCRIPTOR

    def gammaLut(self, gamma=None):
        """The 256-entry float32 decode table for `gamma` (cached). Index it with a uint8 array."""
        return _gammaLut(DEFAULT_CAPTURE_GAMMA if gamma is None else gamma)

    def decodeGammaArray(self, values, gamma=None):
        """Encoded 0..255 -> LINEAR 0..255, elementwise. A uint8 array takes the LUT fast path (exact —
        only 256 possible inputs — and it replaces the caller's astype(float32)); anything else falls back
        to the closed form so tests and off-line replays can hand in floats."""
        array = np.asarray(values)
        if array.dtype == np.uint8:
            return self.gammaLut(gamma)[array]
        exponent = DEFAULT_CAPTURE_GAMMA if gamma is None else gamma
        return (np.maximum(array, 0.0) / 255.0) ** exponent * 255.0

    def encodeGammaFraction(self, fraction, gamma=None):
        """LINEAR fraction in [0,1] -> ENCODED 0..255 — the inverse of decodeGammaArray, for the virtual
        device's image encoder. The two are inverse halves of one transform and must ship together
        (§17.7/21), else a virtual capture decodes as value^gamma (or value^(1/gamma))."""
        exponent = DEFAULT_CAPTURE_GAMMA if gamma is None else gamma
        return 255.0 * max(0.0, float(fraction)) ** (1.0 / exponent)

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

