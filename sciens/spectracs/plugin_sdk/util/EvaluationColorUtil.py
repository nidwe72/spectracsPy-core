import colorsys
import math

from colour import (SpectralDistribution, MSDS_CMFS, SDS_ILLUMINANTS, sd_to_XYZ, XYZ_to_xy,
                    xyY_to_XYZ, XYZ_to_sRGB)

from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModule import SpectrumToColorLogicModule
from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModuleParameters import SpectrumToColorLogicModuleParameters
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class EvaluationColorUtil:
    """The Qt-free colour boundary for plugins (SPEC_pumpkin_integration.md P-B3 / SPEC_color_retrieval.md). Wraps the
    CIE pipeline and hands the plugin only PLAIN data — (r,g,b) tuples and HSL numbers, never a QColor.

    Two entry points:
      - `spectrumToRgbAndHue` — the ORIGINAL pinned-lightness swatch + hue (UNCHANGED; the pumpkin roast verdict
        depends on its hue output, so its converter must stay `rgbxy`).
      - `spectrumToHsl` + `rgbFromHsl` — the colour-chips API (§14.8/SPEC_color_retrieval): the measured H,S,L of a
        spectrum, plus a builder to render a chip at a chosen (h,s,l). Converter is SOURCE-keyed (§F7):
        transmission → `rgbxy` (perceived, verdict-compatible), absorbance → `colour.XYZ_to_sRGB` (full gamut, no
        Philips-Hue clamping)."""

    # Below this CHROMA the source is ~grey and its hue is meaningless — forcing a vivid chip would paint a
    # confident fake colour (SPEC_color_retrieval.md §F10). The plugin greys such chips. Chroma (not raw HLS
    # saturation) because HLS saturation blows up near white/black (a near-white reads S≈100% though it is ~grey);
    # chroma = (1 − |2L−1|)·S stays small there.
    ACHROMATIC_CHROMA = 8.0                # percent

    # D65 2° white chromaticity — the neutral point the intrinsic-perceived complement reflects through
    # (SPEC_capability_proof.md option (b) / SPEC_color_retrieval.md). Reflecting the absorbed chromaticity through
    # white — (2·white − absorbed) — is the colorimetric "other half of the light" (the mixing-to-white complement),
    # which lands ~4° from the true perceived hue on K/L/M/N vs ~34° for a naive +180° HSL hue flip.
    __D65_XY = (0.31270, 0.32900)

    def spectrumToRgbAndHue(self, spectrum):
        # UNCHANGED — the pumpkin verdict's hue path. Pinned-lightness swatch via rgbxy.
        parameters = SpectrumToColorLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        result = SpectrumToColorLogicModule().spectrumToColor(parameters)
        color = result.getColor()
        rgb = (color.red(), color.green(), color.blue())
        return rgb, result.getHue()

    def spectrumToHsl(self, spectrum, converter="rgbxy", ceiling=None):
        """Measured (h, s, l) of the spectrum — h in [0,360), s and l in [0,100]. `converter`: "rgbxy" for
        transmission-derived chips (verdict-compatible), "srgb" for absorbance-derived (full-gamut). `ceiling`
        caps values (use for absorbance so a T→0 spike can't dominate). F9: non-finite → 0 and negatives → 0
        (absorbance goes negative where T>1; negative "spectrum" values corrupt the CIE integral)."""
        clean = self.__sanitize(spectrum, ceiling)
        if clean is None:
            return (0.0, 0.0, 0.0)                       # empty / all-dark → achromatic (plugin greys it)

        if converter == "srgb":
            return self.__hslFromXy(*self.__cieXy(clean))
        # rgbxy: reuse the tuned module unchanged (verdict-compatible), just on the sanitized values.
        sanitized = Spectrum()
        sanitized.valuesByNanometers = clean
        parameters = SpectrumToColorLogicModuleParameters()
        parameters.setSpectrum(sanitized)
        result = SpectrumToColorLogicModule().spectrumToColor(parameters)
        return (result.getHue(), result.getSaturation(), result.getLightness())

    def complementViaWhitePoint(self, spectrum, ceiling=None):
        """The intrinsic-perceived colour as the COLORIMETRIC complement of the absorbed colour
        (SPEC_capability_proof.md option (b)): compute the absorbed chromaticity, reflect it through the D65 white
        point (`2·white − absorbed`) — the additive "mixing-to-white" opposite, i.e. the other half of the light —
        and read its HSL. Far closer to the true perceived hue than a `+180°` HSL flip (~4° vs ~34° on K/L/M/N).
        `ceiling` caps the absorbance (a T→0 spike must not dominate). Returns (h,s,l); (0,0,0) when the source is
        grey/dark (its complement is also grey — the plugin greys the chip)."""
        clean = self.__sanitize(spectrum, ceiling)
        if clean is None:
            return (0.0, 0.0, 0.0)
        x, y = self.__cieXy(clean)
        whiteX, whiteY = self.__D65_XY
        return self.__hslFromXy(2.0 * whiteX - x, 2.0 * whiteY - y)

    def __sanitize(self, spectrum, ceiling):
        # F9: non-finite → 0, negatives → 0 (absorbance goes negative where T>1; negatives corrupt the CIE
        # integral), optional ceiling. None if the result is empty / all-dark.
        clean = {}
        for nanometer, value in (spectrum.valuesByNanometers or {}).items():
            if value is None or not math.isfinite(value):
                value = 0.0
            value = max(0.0, float(value))
            if ceiling is not None:
                value = min(value, ceiling)
            clean[nanometer] = value
        if not clean or not any(v > 0 for v in clean.values()):
            return None
        return clean

    def __cieXy(self, valuesByNanometers):
        # SPEC_color_retrieval.md §F7/§F11: CIE → chromaticity xy (drops luminance ⇒ dilution-invariant).
        spectralDistribution = SpectralDistribution(valuesByNanometers)
        cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
        illuminant = SDS_ILLUMINANTS["D65"]
        spectralDistribution = spectralDistribution.align(cmfs.shape)
        xyz = sd_to_XYZ(spectralDistribution, cmfs, illuminant, method="Integration")
        xy = XYZ_to_xy(xyz)
        return float(xy[0]), float(xy[1])

    def __hslFromXy(self, x, y):
        # Reconstruct at a MID luminance (Y=0.5; Y=1 pushes saturated colours out of gamut) → sRGB (full gamut,
        # no Hue-triangle clamp) → clamp [0,1] → HSL.
        reconstructed = xyY_to_XYZ([x, y, 0.5])
        rgb = XYZ_to_sRGB(reconstructed)
        red, green, blue = (min(1.0, max(0.0, float(channel))) for channel in rgb)
        hls = colorsys.rgb_to_hls(red, green, blue)      # HLS order: [0]=h, [1]=l, [2]=s
        return (hls[0] * 360.0, hls[2] * 100.0, hls[1] * 100.0)

    def rgbFromHsl(self, hue, saturation, lightness):
        """Build a 0-255 (r,g,b) from HSL: hue in degrees (wrapped), saturation/lightness in [0,100]."""
        red, green, blue = colorsys.hls_to_rgb((hue % 360.0) / 360.0, lightness / 100.0, saturation / 100.0)
        return (int(round(red * 255)), int(round(green * 255)), int(round(blue * 255)))

    def chroma(self, saturation, lightness):
        """HSL colourfulness that behaves near white/black (SPEC_color_retrieval.md §F10): `(1 − |2L−1|)·S`, in
        percent. ~0 for grey/near-white/near-black, high only for a genuinely vivid hue."""
        return (1.0 - abs(2.0 * lightness / 100.0 - 1.0)) * saturation
