import numpy

from sciens.spectracs.logic.spectral.normalizeSpectrum.NormalizeSpectrumLogicModuleParameters import NormalizeSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.normalizeSpectrum.NormalizeSpectrumLogicModuleResult import NormalizeSpectrumLogicModuleResult


class NormalizeSpectrumLogicModule:

    def normalizeSpectrum(self, normalizeSpectrumLogicModuleParameters: NormalizeSpectrumLogicModuleParameters):
        # Scale all values so the maximum becomes 1.0. No-op (rather than divide-by-zero) on an empty or
        # all-zero spectrum.
        spectrum = normalizeSpectrumLogicModuleParameters.getSpectrum()

        keys = list(spectrum.valuesByNanometers.keys())
        values = numpy.asarray(list(spectrum.valuesByNanometers.values()), float)

        if values.size > 0:
            maximum = values.max()
            if maximum > 0:
                values = values / maximum
                spectrum.valuesByNanometers = dict(zip(keys, values.tolist()))

        result = NormalizeSpectrumLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
