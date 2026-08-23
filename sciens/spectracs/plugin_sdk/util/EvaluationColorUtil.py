import colorsys
import math

import numpy

from colour import (SpectralDistribution, MSDS_CMFS, SDS_ILLUMINANTS, sd_to_XYZ, XYZ_to_xy,
                    xyY_to_XYZ, XYZ_to_sRGB, XYZ_to_Lab, excitation_purity)

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

    # Pass `ceiling=EvaluationColorUtil.RELATIVE` instead of a hard number: the cap is then derived from the
    # spectrum's own 95th percentile, so it survives a change of absorbance SCALE (gamma linearization moves it
    # ~2.2x) and a host/plugin version skew. See __resolveCeiling. SPEC_capture_quality.md §17.6/7.
    RELATIVE = "relative"
    RELATIVE_CEILING_MULTIPLE = 2.0

    # D65 2° white chromaticity — the neutral point the intrinsic-perceived complement reflects through
    # (SPEC_capability_proof.md option (b) / SPEC_color_retrieval.md). Reflecting the absorbed chromaticity through
    # white — (2·white − absorbed) — is the colorimetric "other half of the light" (the mixing-to-white complement),
    # which lands ~4° from the true perceived hue on K/L/M/N vs ~34° for a naive +180° HSL hue flip.
    __D65_XY = (0.31270, 0.32900)

    # The luminance the CHROMATICITY-ONLY chips are reconstructed at. Y=1.0 pushes saturated colours far out of
    # gamut; 0.5 is a mid tone. This is NOT the sample's brightness — the five chips are dilution-invariant by
    # design (SPEC_color_retrieval.md §0/F8), and dropping Y is the mechanism (§7.10 F21).
    __SWATCH_Y = 0.5

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

    def spectrumToPurity(self, spectrum, ceiling=None):
        """SPEC_color_retrieval.md §7.12 C1 — **the replacement for the HSL `S` that pins to 100 %.**

        Excitation purity: how far the chromaticity sits from the D65 white point along the line toward the
        spectrum locus, in percent. 0 = white, 100 = a pure spectral colour. ⭐ Unlike HSL `S` it is defined by
        the *chromaticity diagram*, not by a display gamut, so a colour outside sRGB gets a real number instead
        of pinning at 100 the moment a channel clips. Dilution-invariant, exactly like `spectrumToHsl`."""
        clean = self.__sanitize(spectrum, ceiling)
        if clean is None:
            return 0.0
        x, y = self.__cieXy(clean)
        try:
            return float(excitation_purity([x, y], self.__D65_XY)) * 100.0
        except Exception:                                 # degenerate chromaticity — treat as achromatic
            return 0.0

    def spectrumToLab(self, absorbance, path=1.0, ceiling=RELATIVE):
        """SPEC_color_retrieval.md §7.12 C3 — chip 6, "as seen". Renders the ABSORBANCE at a declared **viewing
        path** (`path=k` multiplies A, so k=3 is "through 3 cm of liquid where 1 cm was measured") and **KEEPS
        the sample's own luminance**. Returns `(L*, C*, h_ab, (r,g,b))`.

        ⛔ **NOT dilution-invariant, deliberately.** §7.6: brownness IS lightness IS concentration, so a chip
        that shows "browner" cannot also be dilution-invariant. The five chips remain the invariant ones; this is
        the one you can hold against a tube. Label it as such wherever it is rendered.

        The ceiling is applied to A BEFORE the path multiplier (it exists to suppress a T→0 spike, not to cap the
        viewing thickness) and defaults to RELATIVE — an absolute cap would clip everything once k > 1 (§7.10 F24)."""
        clean = self.__sanitize(absorbance, ceiling)
        if clean is None:
            return (0.0, 0.0, 0.0, (128, 128, 128))
        scale = max(0.0, float(path))
        transmittance = {nanometer: min(1.0, 10.0 ** (-scale * value)) for nanometer, value in clean.items()}
        xyz = self.__cieXyzDense(transmittance)
        lightness, chroma, hue = self.__lch(xyz)
        mapped = XYZ_to_sRGB(xyz, self.__D65_XY)
        red, green, blue = (min(1.0, max(0.0, float(channel))) for channel in mapped)
        return (lightness, chroma, hue, (int(round(red * 255)), int(round(green * 255)), int(round(blue * 255))))

    def __cieXyzDense(self, transmittance):
        """XYZ of a TRANSMITTANCE, sampled densely on the CMF grid by LINEAR interpolation, with un-measured
        wavelengths treated as **transparent (T = 1)**.

        ⛔ Two traps this exists to avoid, both measured 2026-08-23 (SPEC_color_retrieval.md §7.10 F29 / §7.12):
        1. `SpectralDistribution.align` fills gaps by HOLDING the boundary sample — i.e. it extrapolates the
           falling flank of the 624 nm band flat across 636-780 nm, 40 % of the visible red invented from one
           point where the reference is ~33 DN. That renders Billa Clever OLIVE-GREEN where the eye says khaki
           BROWN: it **inverts the visual ordering of the two oils**.
        2. Anchoring a few sparse T = 1 points and letting `align` interpolate is worse still — its cubic
           interpolation **overshoots** across the 1 nm step onto an opaque Soret (Y = 2.61, L* = 144).
        Hence: dense, linear, explicit. ⚠ T = 1 outside the range is still an assumption — wrong at the blue end
        (the Soret core below 420 nm is MORE absorbing, not less), but the CMF weight there is small under linear
        interpolation, and it is the conservative choice in the red where the discrimination lives."""
        cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
        illuminant = SDS_ILLUMINANTS["D65"]
        wavelengths = sorted(transmittance)
        values = [transmittance[nanometer] for nanometer in wavelengths]
        dense = {}
        for nanometer in cmfs.wavelengths:
            nanometer = float(nanometer)
            if nanometer < wavelengths[0] or nanometer > wavelengths[-1]:
                dense[nanometer] = 1.0                    # un-measured ⇒ transparent
            else:
                dense[nanometer] = float(numpy.interp(nanometer, wavelengths, values))
        spectralDistribution = SpectralDistribution(dense).align(cmfs.shape)
        return sd_to_XYZ(spectralDistribution, cmfs, illuminant, method="Integration") / 100.0

    def __lch(self, xyz):
        lab = XYZ_to_Lab(xyz, self.__D65_XY)
        lightness, a, b = (float(v) for v in lab)
        return (lightness, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360.0)

    def __sanitize(self, spectrum, ceiling):
        # F9: non-finite → 0, negatives → 0 (absorbance goes negative where T>1; negatives corrupt the CIE
        # integral), optional ceiling. None if the result is empty / all-dark.
        clean = {}
        for nanometer, value in (spectrum.valuesByNanometers or {}).items():
            if value is None or not math.isfinite(value):
                value = 0.0
            value = max(0.0, float(value))
            clean[nanometer] = value
        ceiling = self.__resolveCeiling(clean, ceiling)
        if ceiling is not None:
            clean = {nanometer: min(value, ceiling) for nanometer, value in clean.items()}
        if not clean or not any(v > 0 for v in clean.values()):
            return None
        return clean

    def __resolveCeiling(self, values, ceiling):
        # RELATIVE ceiling (SPEC_capture_quality.md §17.6/7). An ABSOLUTE cap has to be re-tuned whenever the
        # absorbance SCALE moves — and gamma linearization moves it by ~2.2x. Worse, the old 3.0 lived in
        # PLUGIN code, and plugins ship as sealed versioned DB blobs (M3): a linearized host running an older
        # assigned plugin version would clamp real signal with nothing to warn about it. So the cap is derived
        # from the spectrum itself: a multiple of its 95th percentile. That is dormant on a normal spectrum
        # (A peaks ~1.3-1.6 against a p95 ~2x lower — the same dormancy the 3.0 had), scales with gamma for
        # free, and still catches what the cap exists for: a T->0 spike in a few bins dominating the CIE
        # integral. Absolute numbers still work — the existing tests pass 3.0 — but plugins should pass RELATIVE.
        if ceiling != self.RELATIVE:
            return ceiling
        positives = sorted(value for value in values.values() if value > 0.0)
        if not positives:
            return None
        index = min(len(positives) - 1, int(round(0.95 * (len(positives) - 1))))
        return self.RELATIVE_CEILING_MULTIPLE * positives[index]

    def __cieXyz(self, valuesByNanometers):
        # ⚠ SPEC_color_retrieval.md §7.10 F29: `align` extends the measured range (420-636 nm on this rig) out to
        # the CMF shape by HOLDING the boundary sample, so 636-780 nm is extrapolated from one point. Shared by
        # every path and every caller; the on-device build raises where desktop tolerates a grid mismatch.
        spectralDistribution = SpectralDistribution(valuesByNanometers)
        cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
        illuminant = SDS_ILLUMINANTS["D65"]
        spectralDistribution = spectralDistribution.align(cmfs.shape)
        return sd_to_XYZ(spectralDistribution, cmfs, illuminant, method="Integration") / 100.0

    def __cieXy(self, valuesByNanometers):
        # SPEC_color_retrieval.md §F7/§F11: CIE → chromaticity xy (drops luminance ⇒ dilution-invariant).
        xy = XYZ_to_xy(self.__cieXyz(valuesByNanometers))
        return float(xy[0]), float(xy[1])

    def __inSrgbGamut(self, x, y, luminance):
        if y <= 1e-6:
            return False
        rgb = XYZ_to_sRGB(xyY_to_XYZ([x, y, luminance]))
        return all(-1e-6 <= float(channel) <= 1.0 + 1e-6 for channel in rgb)

    def gamutMapXy(self, x, y, luminance=None):
        """Desaturate a chromaticity toward the D65 white point until it lands inside sRGB; returns
        `(x, y, reach)` where `reach` = 1.0 means nothing was needed and < 1.0 says how far out of gamut it was.

        ⛔ **Not used in the reported-number path** — see `__hslFromXy`. It moves hue by up to 45° and does not
        cure `S ≡ 100 %`. Kept because `reach` is a useful *diagnostic* ("how unrenderable is this chip"), and a
        renderer that wants a prettier out-of-gamut swatch than a per-channel clamp can opt in."""
        luminance = self.__SWATCH_Y if luminance is None else luminance
        whiteX, whiteY = self.__D65_XY
        if self.__inSrgbGamut(x, y, luminance):
            return (x, y, 1.0)
        low, high = 0.0, 1.0
        for _ in range(40):                              # bisect the mix factor toward white
            middle = 0.5 * (low + high)
            if self.__inSrgbGamut(whiteX + middle * (x - whiteX), whiteY + middle * (y - whiteY), luminance):
                low = middle
            else:
                high = middle
        return (whiteX + low * (x - whiteX), whiteY + low * (y - whiteY), low)

    def __hslFromXy(self, x, y):
        # Reconstruct at a MID luminance (§__SWATCH_Y) → sRGB → clamp → HSL.
        # ⛔ MEASURED 2026-08-23, SPEC_color_retrieval.md §7.12 C1: gamut-mapping toward white here was tried and
        # REVERTED. It shifts the reported hue by up to 45° on the badly out-of-gamut absorbed chromaticities
        # (287.5° → 252.7° on a pumpkin absorbance) — hue is the one thing the verdict and F8 depend on — and it
        # does NOT fix `S ≡ 100 %` anyway: the gamut boundary is exactly where min(r,g,b) = 0, which IS S = 100.
        # `S` pinning at 100 is intrinsic to reading HSL saturation off an out-of-gamut chromaticity, whatever the
        # rendering. The reportable colourfulness is Lab `C*` — see `spectrumToLch`, which has no gamut at all.
        rgb = XYZ_to_sRGB(xyY_to_XYZ([x, y, self.__SWATCH_Y]))
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
