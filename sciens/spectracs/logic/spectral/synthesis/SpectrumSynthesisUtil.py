import numpy

from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class SpectrumSynthesisUtil(Singleton):
    # Forward, physical synthesis for the playground (concept/KB):
    #   REFERENCE  R(λ) = Σ LED SPDs (Avonec-measured-shaped Gaussians; warm-white = pump + phosphor)
    #   SAMPLE     S(λ) = R(λ) · 10^(−A_oil(λ))   with A_oil = chlorophyll/carotenoid bands + roast browning
    # The single `roast` knob monotonically rotates the transmission colour green→brown, so a 1-D search
    # lands any target hue. All synthetic — known provenance.

    DEFAULT_NANOMETERS = list(range(380, 781))

    # name, [(peakNm, fwhmNm, amplitude), ...], weight. Warm-white is bimodal (blue pump + phosphor),
    # which a single Gaussian can't represent — see KB_led_and_oil_spectra. Default set = 2× warm-white
    # (continuum) + violet/blue/green/red/deep-red + UV-A (luxpy, fills the <410 edge).
    LED_SET = [
        ("warm-white", [(448.0, 22.0, 0.30), (586.0, 110.0, 1.00)], 2.0),
        ("uv-a", [(400.0, 15.0, 1.00)], 0.5),
        ("hyper-violet", [(432.0, 18.0, 1.00)], 0.7),
        ("royal-blue", [(445.0, 20.0, 1.00)], 0.7),
        ("green", [(515.0, 30.0, 1.00)], 0.9),
        ("red", [(635.0, 22.0, 1.00)], 0.8),
        ("deep-red", [(660.0, 25.0, 1.00)], 0.7),
    ]

    # ---- reference (LED) synthesis -------------------------------------------------------------

    def synthesizeReference(self, nanometers=None, ledSet=None) -> Spectrum:
        nanometers = self.DEFAULT_NANOMETERS if nanometers is None else nanometers
        ledSet = self.LED_SET if ledSet is None else ledSet
        axis = numpy.asarray(nanometers, float)
        total = numpy.zeros_like(axis)
        for name, components, weight in ledSet:
            if name == "uv-a":
                total += weight * self.__uvaSpd(axis)
            else:
                for peak, fwhm, amplitude in components:
                    total += weight * amplitude * self.__gaussian(axis, peak, fwhm)
        spectrum = Spectrum()
        spectrum.setValuesByNanometers({self.__key(nm): float(v) for nm, v in zip(nanometers, total)})
        return spectrum

    def perLedSpectra(self, nanometers=None, ledSet=None):
        # Returns [(name, weightedSpd), ...] — the individual LED SPDs that sum to the reference.
        nanometers = self.DEFAULT_NANOMETERS if nanometers is None else nanometers
        ledSet = self.LED_SET if ledSet is None else ledSet
        axis = numpy.asarray(nanometers, float)
        spectra = []
        for name, components, weight in ledSet:
            if name == "uv-a":
                spd = weight * self.__uvaSpd(axis)
            else:
                spd = numpy.zeros_like(axis)
                for peak, fwhm, amplitude in components:
                    spd += weight * amplitude * self.__gaussian(axis, peak, fwhm)
            spectra.append((name, spd))
        return spectra

    def __gaussian(self, axis, peak, fwhm):
        sigma = fwhm / 2.3548200450309493  # FWHM -> sigma
        return numpy.exp(-0.5 * ((axis - peak) / sigma) ** 2)

    def __uvaSpd(self, axis):
        # 390-410 UV-A has no measured Avonec curve -> synthesise with luxpy (per spec); fall back to a
        # plain Gaussian if luxpy's builder is unavailable.
        try:
            import luxpy
            from luxpy.toolboxes.spdbuild import spdbuilder as _spdb  # noqa: F401
            grid = numpy.asarray([axis], float)
            spd = luxpy.toolboxes.spdbuild.gaussian_spd(peakwl=400.0, fwhm=15.0, wl=axis)
            values = numpy.asarray(spd[1], float)
            maximum = values.max()
            return values / maximum if maximum > 0 else values
        except Exception:
            return self.__gaussian(axis, 400.0, 15.0)

    # ---- oil absorbance + sample synthesis -----------------------------------------------------

    # Roasting broadens the pigment absorption toward longer wavelengths, sliding the oil's transmission
    # window (the gap between blue and red absorption) from green toward orange — so the colour rotates
    # green -> brown. roast in [0,1] moves the window centre from WINDOW_GREEN to WINDOW_BROWN nm. (The
    # window bottom is ~zero absorption = transmits; everywhere else absorbs ~OIL_ABSORBANCE_DEPTH.)
    WINDOW_GREEN_NANOMETER = 503.0
    WINDOW_BROWN_NANOMETER = 595.0
    WINDOW_WIDTH = 46.0
    OIL_ABSORBANCE_DEPTH = 2.6

    def oilAbsorbance(self, nanometers, roast: float):
        axis = numpy.asarray(nanometers, float)
        roast = float(min(1.0, max(0.0, roast)))
        windowCenter = self.WINDOW_GREEN_NANOMETER + roast * (self.WINDOW_BROWN_NANOMETER - self.WINDOW_GREEN_NANOMETER)
        transmissionWindow = self.__gaussian(axis, windowCenter, self.WINDOW_WIDTH)
        return self.OIL_ABSORBANCE_DEPTH * (1.0 - transmissionWindow)

    def synthesizeSample(self, reference: Spectrum, roast: float) -> Spectrum:
        nanometers = list(reference.valuesByNanometers.keys())
        referenceValues = numpy.asarray(list(reference.valuesByNanometers.values()), float)
        absorbance = self.oilAbsorbance(nanometers, roast)
        sampleValues = referenceValues * numpy.power(10.0, -absorbance)
        sample = Spectrum()
        sample.setValuesByNanometers({self.__key(nm): float(v) for nm, v in zip(nanometers, sampleValues)})
        return sample

    # ---- colour helper + roast tuner -----------------------------------------------------------

    def transmissionHue(self, reference: Spectrum, sample: Spectrum) -> float:
        # Hue (degrees) of the reference-normalised transmission — the verdict discriminator.
        from sciens.spectracs.logic.spectral.util.SpectrumUtil import SpectrumUtil
        from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModule import SpectrumToColorLogicModule
        from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModuleParameters import SpectrumToColorLogicModuleParameters
        transmission = SpectrumUtil().transmission(reference, sample)
        parameters = SpectrumToColorLogicModuleParameters()
        parameters.setSpectrum(transmission)
        return SpectrumToColorLogicModule().spectrumToColor(parameters).getHue()

    def tuneRoastForHue(self, reference: Spectrum, targetHue: float, lowRoast=0.0, highRoast=1.0,
                        iterations=40) -> float:
        # Bisection on roast: hue decreases monotonically as roast (browning) increases.
        for _ in range(iterations):
            midRoast = 0.5 * (lowRoast + highRoast)
            hue = self.transmissionHue(reference, self.synthesizeSample(reference, midRoast))
            if hue > targetHue:
                lowRoast = midRoast   # too green -> roast more
            else:
                highRoast = midRoast
        return 0.5 * (lowRoast + highRoast)

    def __key(self, nm):
        return int(round(nm))
