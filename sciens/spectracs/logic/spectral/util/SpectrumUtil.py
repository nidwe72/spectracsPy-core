import copy

import numpy
from scipy.signal import savgol_filter
from scipy.ndimage import minimum_filter1d, maximum_filter1d

from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class SpectrumUtil(Singleton):

    def removeBaseline(self, spectrum: Spectrum, windowSize: int = None, clone: bool = False):
        # Baseline / continuum removal: a morphological opening (erosion then dilation) over a window
        # wider than an emission line but narrower than the continuum estimates the background; subtracting
        # it isolates the sharp lines. Helps peak detection, especially in the dense red cluster.
        # The window is resolution-adaptive (~10% of the spectrum width). A fixed window broke the plain
        # heuristic's anchor ranking on the lower-resolution test image; ~10% keeps it correct on both
        # the Philips and Snowy spectra while still helping the predict-and-snap matcher.
        result = spectrum
        if clone:
            result = copy.deepcopy(spectrum)
        keys = list(result.valuesByNanometers.keys())
        values = numpy.asarray(list(result.valuesByNanometers.values()), float)
        if windowSize is None:
            windowSize = max(31, len(values) // 10)
        baseline = maximum_filter1d(minimum_filter1d(values, windowSize), windowSize)
        corrected = numpy.clip(values - baseline, 0, None)
        result.valuesByNanometers = dict(zip(keys, corrected.tolist()))
        return result

    def mean(self, spectrum:Spectrum, clone:bool=False):

        result=spectrum
        if clone:
            result=copy.deepcopy(spectrum)

        capturedValuesByNanometers = spectrum.getCapturedValuesByNanometers()
        meanValues=numpy.matrix([list(each.values()) for each in capturedValuesByNanometers]).mean(axis=0).flatten().tolist().pop()

        valuesByNanometers = dict(zip(list(result.valuesByNanometers.keys()), meanValues))
        result.valuesByNanometers= valuesByNanometers

        return result

    def smooth(self, spectrum: Spectrum, clone: bool = False):

        result=spectrum
        if clone:
            result=copy.deepcopy(spectrum)

        smoothedValues = savgol_filter(list(spectrum.valuesByNanometers.values()), 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)


        smoothedValues=smoothedValues.flatten().tolist()

        valuesByNanometers = dict(zip(list(result.valuesByNanometers.keys()), smoothedValues))
        result.valuesByNanometers= valuesByNanometers

        return result




