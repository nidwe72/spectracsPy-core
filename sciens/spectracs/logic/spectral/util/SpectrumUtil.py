import copy

import numpy
from scipy.signal import savgol_filter

from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class SpectrumUtil(Singleton):

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




