import numpy

from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleResult import MeanSpectrumLogicModuleResult


class MeanSpectrumLogicModule:

    def meanSpectrum(self, meanSpectrumLogicModuleParameters: MeanSpectrumLogicModuleParameters):
        # Average the captured frames (each a {nm: value} dict) element-wise into valuesByNanometers.
        spectrum = meanSpectrumLogicModuleParameters.getSpectrum()

        capturedValuesByNanometers = spectrum.getCapturedValuesByNanometers()
        meanValues = numpy.matrix([list(each.values()) for each in capturedValuesByNanometers]).mean(axis=0).flatten().tolist().pop()

        spectrum.valuesByNanometers = dict(zip(list(spectrum.valuesByNanometers.keys()), meanValues))

        result = MeanSpectrumLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
