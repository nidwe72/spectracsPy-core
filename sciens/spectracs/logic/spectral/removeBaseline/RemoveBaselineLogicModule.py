import numpy
from scipy.ndimage import minimum_filter1d, maximum_filter1d

from sciens.spectracs.logic.spectral.removeBaseline.RemoveBaselineLogicModuleParameters import RemoveBaselineLogicModuleParameters
from sciens.spectracs.logic.spectral.removeBaseline.RemoveBaselineLogicModuleResult import RemoveBaselineLogicModuleResult


class RemoveBaselineLogicModule:

    def removeBaseline(self, removeBaselineLogicModuleParameters: RemoveBaselineLogicModuleParameters):
        # Baseline / continuum removal: a morphological opening (erosion then dilation) over a window
        # wider than an emission line but narrower than the continuum estimates the background; subtracting
        # it isolates the sharp lines. Helps peak detection, especially in the dense red cluster.
        # The window is resolution-adaptive (~10% of the spectrum width). A fixed window broke the plain
        # heuristic's anchor ranking on the lower-resolution test image; ~10% keeps it correct on both
        # the Philips and Snowy spectra while still helping the predict-and-snap matcher.
        spectrum = removeBaselineLogicModuleParameters.getSpectrum()
        windowSize = removeBaselineLogicModuleParameters.getWindowSize()

        keys = list(spectrum.valuesByNanometers.keys())
        values = numpy.asarray(list(spectrum.valuesByNanometers.values()), float)
        if windowSize is None:
            windowSize = max(31, len(values) // 10)
        baseline = maximum_filter1d(minimum_filter1d(values, windowSize), windowSize)
        corrected = numpy.clip(values - baseline, 0, None)
        spectrum.valuesByNanometers = dict(zip(keys, corrected.tolist()))

        result = RemoveBaselineLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
