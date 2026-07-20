import numpy
from scipy.signal import medfilt

from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModuleParameters import MedianFilterSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModuleResult import MedianFilterSpectrumLogicModuleResult


class MedianFilterSpectrumLogicModule:

    def medianFilter(self, medianFilterSpectrumLogicModuleParameters: MedianFilterSpectrumLogicModuleParameters):
        # Moving-median (rank) filter over the spectrum values. Unlike Savitzky-Golay smoothing
        # (SmoothSpectrumLogicModule, which fits a local polynomial and PRESERVES peaks), a moving median REJECTS
        # isolated outliers — a single hot/cold pixel or a narrow lamp-line spike is replaced by its neighbourhood
        # median. Used e.g. to read a noise-robust floor for the flat-offset baseline (FlatOffsetBaselineLogicModule,
        # SPEC_capability_proof.md §7.0.1 G4/RD-A). Mutates the passed spectrum in place; callers that must keep the
        # original clone first (as SpectrumUtil / the plugin_sdk ops do).
        spectrum = medianFilterSpectrumLogicModuleParameters.getSpectrum()
        kernelSize = medianFilterSpectrumLogicModuleParameters.getKernelSize()

        keys = list(spectrum.valuesByNanometers.keys())
        values = numpy.asarray(list(spectrum.valuesByNanometers.values()), float)
        if values.size == 0:
            result = MedianFilterSpectrumLogicModuleResult()
            result.setSpectrum(spectrum)
            return result

        kernel = kernelSize if kernelSize % 2 == 1 else kernelSize + 1
        if values.size >= kernel:
            filtered = medfilt(values, kernel_size=kernel)
        else:
            filtered = values
        spectrum.valuesByNanometers = dict(zip(keys, numpy.asarray(filtered, float).tolist()))

        result = MedianFilterSpectrumLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
