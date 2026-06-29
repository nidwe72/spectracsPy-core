import numpy
import spectres

from sciens.spectracs.logic.spectral.rebinSpectrum.RebinSpectrumLogicModuleParameters import RebinSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.rebinSpectrum.RebinSpectrumLogicModuleResult import RebinSpectrumLogicModuleResult


class RebinSpectrumLogicModule:

    def rebinSpectrum(self, rebinSpectrumLogicModuleParameters: RebinSpectrumLogicModuleParameters):
        # Resample the spectrum onto a regular wavelength grid (default 380..780 nm @ 1 nm) using
        # spectres, which is flux-conserving (it integrates over bin edges) rather than a plain linear
        # interpolation. Target wavelengths outside the input range are filled with 0.0 instead of NaN,
        # so a narrow spectrum (e.g. only 400..700 nm) does not poison the downstream colour maths.
        spectrum = rebinSpectrumLogicModuleParameters.getSpectrum()
        start = rebinSpectrumLogicModuleParameters.getStart()
        stop = rebinSpectrumLogicModuleParameters.getStop()
        step = rebinSpectrumLogicModuleParameters.getStep()

        originalWavelengths = numpy.asarray(list(spectrum.valuesByNanometers.keys()), float)
        originalValues = numpy.asarray(list(spectrum.valuesByNanometers.values()), float)

        newWavelengths = numpy.arange(start, stop + 1, step)
        newValues = spectres.spectres(newWavelengths, originalWavelengths, originalValues, fill=0.0, verbose=False)

        spectrum.valuesByNanometers = dict(zip(newWavelengths.astype(int).tolist(), newValues.tolist()))

        result = RebinSpectrumLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
