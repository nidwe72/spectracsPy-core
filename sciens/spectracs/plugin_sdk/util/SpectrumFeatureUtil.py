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

    def linearBaseline(self, spectrum, lam, anchorLo, anchorHi, halfWindow=5):
        return SpectrumFeatureLogicModule().linearBaseline(spectrum, lam, anchorLo, anchorHi, halfWindow)

    def referenceGatedBand(self, valueSpectrum, gateSpectrum, lo, hi,
                           gateFraction, valueCeiling, gatePeakLo, gatePeakHi):
        return SpectrumFeatureLogicModule().referenceGatedBand(
            valueSpectrum, gateSpectrum, lo, hi, gateFraction, valueCeiling, gatePeakLo, gatePeakHi)
