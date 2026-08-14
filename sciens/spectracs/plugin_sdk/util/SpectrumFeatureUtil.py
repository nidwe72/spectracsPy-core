from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.spectral.feature.SpectrumFeatureLogicModule import SpectrumFeatureLogicModule


class SpectrumFeatureUtil(Singleton):
    """Qt-free façade exposing the generic spectral-feature ops to plugins (the plugin_sdk boundary, like
    MeanOp/AbsorptionOp). Delegates to SpectrumFeatureLogicModule. A plugin COMPOSES these generic ops with
    its own band constants — there is no use-case knowledge here. SPEC_pumpkin_peak_ratio_eval.md §7."""

    def bandMean(self, spectrum, lo, hi):
        return SpectrumFeatureLogicModule().bandMean(spectrum, lo, hi)

    def peakInRange(self, spectrum, lo, hi):
        return SpectrumFeatureLogicModule().peakInRange(spectrum, lo, hi)

    def levelCrossing(self, spectrum, lo, hi, value):
        # SPEC_v_metric_integration.md §7 — the nm where the curve crosses `value` inside [lo, hi].
        # The plugin tier carries NO numpy, so this maths cannot live there (§1).
        return SpectrumFeatureLogicModule().levelCrossing(spectrum, lo, hi, value)

    def linearBaseline(self, spectrum, lam, anchorLo, anchorHi, halfWindow=5):
        return SpectrumFeatureLogicModule().linearBaseline(spectrum, lam, anchorLo, anchorHi, halfWindow)

    def linearBaselineCorrected(self, spectrum, windows):
        return SpectrumFeatureLogicModule().linearBaselineCorrected(spectrum, windows)

    def fittedBaseline(self, spectrum, windows):
        # The line linearBaselineCorrected subtracts, as a drawable Spectrum (SPEC_soret_448_trim.md §12.2).
        return SpectrumFeatureLogicModule().fittedBaseline(spectrum, windows)

    def referenceGatedBand(self, valueSpectrum, gateSpectrum, lo, hi,
                           gateFraction, valueCeiling, gatePeakLo, gatePeakHi):
        return SpectrumFeatureLogicModule().referenceGatedBand(
            valueSpectrum, gateSpectrum, lo, hi, gateFraction, valueCeiling, gatePeakLo, gatePeakHi)
