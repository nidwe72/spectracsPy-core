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

    # What an un-measured wavelength is assumed to be, per source kind. Both say "transparent"; they differ
    # only because one variable is the negative log of the other. See __cieXyzDense.
    __PAD_TRANSMITTANCE = 1.0
    __PAD_ABSORBANCE = 0.0

    # Below this Lab CHROMA a chromaticity is ~grey and its hue is meaningless — the L*C*h counterpart of
    # ACHROMATIC_CHROMA (SPEC_color_retrieval.md §7.13 C2, REOPENED by DOC_colour_geometry.md §12.1). Measured
    # 2026-08-24 on near-grey spectra, where this guard is the only place it ever fires: HSL chroma and C*
    # track at ratio ~0.85 (0.89 <-> 0.75), so 8.0 ports to ~7. ⛔ The ratio does NOT hold away from grey
    # (Lugitsch reads S = 100 against C* = 349) — but the guard never runs there.
    ACHROMATIC_CHROMA_LAB = 7.0

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

    # ------------------------------------------------------------------ P3: the composable polar/Lab API
    # ⭐ ADDITIVE, deliberately (DOC_colour_geometry.md §12.1). `spectrumToHsl`, `rgbFromHsl`, `chroma` and
    # `ACHROMATIC_CHROMA` all STAY: plugins ship as sealed DB blobs against the host's SDK, `SDK_VERSION`
    # is a strict-equality gate, and three sealed rows would fail to load if this surface shrank. "Retire
    # HSL" means the dev plugin stops CALLING it, not that the SDK drops it.
    #
    # The five below compose, so a caller can take a chromaticity once and ask several questions of it
    # without re-integrating the spectrum:
    #     xy = spectrumToChromaticity(spectrum, ...)
    #     directionFromWhite(xy) / purityOf(xy) / lchOf(xy) / complementOf(xy)

    # What kind of spectrum a caller is handing over. It selects ONLY the value assumed outside the
    # measured range, and it is not cosmetic: for an absorbance "un-measured = transparent" means 0, for a
    # transmittance it means 1. ⛔ Getting it wrong pads the un-measured red as OPAQUE and moves the
    # transmitted chromaticity by ~13° of theta_W — caught 2026-08-24 by the archive sweep's 4° check,
    # which is the reason this is an explicit argument and not an inferred default.
    ABSORBANCE = "absorbance"
    TRANSMITTANCE = "transmittance"

    def spectrumToChromaticity(self, spectrum, source=ABSORBANCE, ceiling=None):
        """The (x, y) chromaticity of a spectrum, or None when it is empty/all-dark.

        `source` is `ABSORBANCE` (default) or `TRANSMITTANCE` — see the constants above. Chromaticity
        itself is converter-independent; only the RENDERING of it into a display space is not."""
        clean = self.__sanitize(spectrum, ceiling)
        if clean is None:
            return None
        pad = self.__PAD_TRANSMITTANCE if source == self.TRANSMITTANCE else self.__PAD_ABSORBANCE
        xy = XYZ_to_xy(self.__cieXyzDense(clean, pad))
        return (float(xy[0]), float(xy[1]))

    def complementOf(self, xy):
        """The white-point complement: reflect through D65, `(2x_W - x, 2y_W - y)`. A point reflection, so
        it preserves the DIRECTION exactly (mirrored) and the DISTANCE exactly.

        ⚠ Nothing constrains the result to stay inside the spectrum locus. Measured over the 88-run
        archive (DOC_colour_geometry.md §4.1): outside it on 15 % of runs, and at or past the boundary of
        human vision on 70 %. Predictor: the SOURCE purity above ~77 % ⇒ the complement is not a colour.
        ⭐ Its HUE survives all of that — 3.58° from the transmitted colour it stands in for, and no worse
        where it is imaginary (§4.2). Report `directionFromWhite`; do not report its chroma."""
        return (2.0 * self.__D65_XY[0] - xy[0], 2.0 * self.__D65_XY[1] - xy[1])

    def directionFromWhite(self, xy):
        """`theta_W` — the compass bearing of a chromaticity as seen from the white point, in degrees.
        The DIRECTION of the ray whose locus intersection is the dominant wavelength.

        ⭐ Chosen over `h_ab` as the reported hue of the chromaticity-only chips (§12.3): measured against
        the transmitted colour, theta_W = 3.58 +/- 1.43 deg where h_ab = 12.09 and HSL = 9.47. Lab's hue
        depends on CHROMA by design, and these chips compare colours whose chroma differ by 4x.
        ⚠ As an ABSOLUTE readout it is near-constant on this pigment family — 246.80 +/- 0.53 deg over the
        whole archive (§3.1) — and it inherits the capture-edge confound. It is the faithful coordinate,
        not a discriminator. Nothing in the invariant family is one."""
        return math.degrees(math.atan2(xy[1] - self.__D65_XY[1], xy[0] - self.__D65_XY[0])) % 360.0

    def purityOf(self, xy):
        """Excitation purity of a chromaticity, in percent — `r_W / R_W`, the distance from white as a
        fraction of the distance to the spectrum locus on the same ray. ⛔ Returned UNCLAMPED: a value
        over 100 means the point lies outside the locus, which is exactly the test `complementOf`'s
        docstring relies on."""
        try:
            return float(excitation_purity(list(xy), self.__D65_XY)) * 100.0
        except Exception:                                 # degenerate chromaticity — treat as achromatic
            return 0.0

    def lchOf(self, xy, luminance=None):
        """`(L*, C*_ab, h_ab, (r,g,b))` for a chromaticity reconstructed at `luminance` (default the
        chips' fixed __SWATCH_Y). Lab has no gamut, so the NUMBERS are safe; the rgb is still clamped, so
        the SWATCH is not — which is why an out-of-gamut chip must be marked (§12.1).
        ⚠ `L*` is a constant (76.07) whenever the default luminance is used: it is a rendering choice, not
        a measurement. Do not print it on a chromaticity-only chip."""
        luminance = self.__SWATCH_Y if luminance is None else luminance
        xyz = xyY_to_XYZ([xy[0], xy[1], luminance])
        lightness, chroma, hue = self.__lch(xyz)
        red, green, blue = (min(1.0, max(0.0, float(channel))) for channel in XYZ_to_sRGB(xyz))
        return (lightness, chroma, hue,
                (int(round(red * 255)), int(round(green * 255)), int(round(blue * 255))))

    def isRenderable(self, xy):
        """True when a chromaticity is inside sRGB at the chips' swatch luminance — i.e. when the drawn
        swatch is the colour the numbers describe. Thin wrapper over `__inSrgbGamut` so a plugin need not
        reach for `gamutMapXy` just to ask the yes/no question (§11 D2)."""
        return self.__inSrgbGamut(xy[0], xy[1], self.__SWATCH_Y)

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
        xyz = self.__cieXyzDense(transmittance, self.__PAD_TRANSMITTANCE)
        lightness, chroma, hue = self.__lch(xyz)
        mapped = XYZ_to_sRGB(xyz, self.__D65_XY)
        red, green, blue = (min(1.0, max(0.0, float(channel))) for channel in mapped)
        return (lightness, chroma, hue, (int(round(red * 255)), int(round(green * 255)), int(round(blue * 255))))

    def __cieXyzDense(self, valuesByNanometers, padValue):
        """XYZ of a spectrum, sampled densely on the CMF grid by LINEAR interpolation, with un-measured
        wavelengths held at `padValue` — **1.0 for a transmittance** (un-measured ⇒ transparent) and
        **0.0 for an absorbance** (the same physical assumption, in the other variable).

        ⛔ Two traps this exists to avoid, both measured 2026-08-23 (SPEC_color_retrieval.md §7.10 F29 / §7.12):
        1. `SpectralDistribution.align` fills gaps by HOLDING the boundary sample — i.e. it extrapolates the
           falling flank of the 624 nm band flat across 636-780 nm, 40 % of the visible red invented from one
           point where the reference is ~33 DN. That renders Billa Clever OLIVE-GREEN where the eye says khaki
           BROWN: it **inverts the visual ordering of the two oils**.
        2. Anchoring a few sparse T = 1 points and letting `align` interpolate is worse still — its cubic
           interpolation **overshoots** across the 1 nm step onto an opaque Soret (Y = 2.61, L* = 144).
        Hence: dense, linear, explicit. ⚠ Still an assumption, and wrong at the blue end (the Soret core below
        420 nm is MORE absorbing, not less), but the CMF weight there is small under linear interpolation, and
        it is the conservative choice in the red where the discrimination lives.

        ⭐ **P1 / D5, 2026-08-24.** Until now only `spectrumToLab` came through here; every other chip went
        through `align`'s constant hold. DOC_colour_geometry.md §9.2 measured what that cost on the absorbed
        chromaticity: Billa's C* inflated 13 % (165.9 -> 144.5) and its hue moved 2.31°, with lambda_d moving
        almost 12 nm. Every chip now shares this path."""
        cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
        illuminant = SDS_ILLUMINANTS["D65"]
        wavelengths = sorted(valuesByNanometers)
        values = [valuesByNanometers[nanometer] for nanometer in wavelengths]
        dense = {}
        for nanometer in cmfs.wavelengths:
            nanometer = float(nanometer)
            if nanometer < wavelengths[0] or nanometer > wavelengths[-1]:
                dense[nanometer] = padValue                   # un-measured
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
        """XYZ of an ABSORBANCE-like spectrum. ⭐ P1/D5: was `SpectralDistribution(...).align(...)`, whose
        constant hold invents the un-measured red from one boundary sample (§7.10 F29). Now the same dense
        linear path `spectrumToLab` has used since 2026-08-23, padded with A = 0 outside the measured range.
        ⚠ This CHANGED numbers on every chromaticity chip — see DOC_colour_geometry.md §9.2."""
        return self.__cieXyzDense(valuesByNanometers, self.__PAD_ABSORBANCE)

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
