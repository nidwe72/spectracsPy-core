from scipy.signal import savgol_filter

from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModuleParameters import SmoothSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModuleResult import SmoothSpectrumLogicModuleResult


class SmoothSpectrumLogicModule:

    def smoothSpectrum(self, smoothSpectrumLogicModuleParameters: SmoothSpectrumLogicModuleParameters):
        # Savitzky-Golay smoothing applied seven times in sequence (window 10, polyorder 3).
        spectrum = smoothSpectrumLogicModuleParameters.getSpectrum()

        smoothedValues = savgol_filter(list(spectrum.valuesByNanometers.values()), 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)
        smoothedValues = savgol_filter(smoothedValues, 10, 3)

        smoothedValues = smoothedValues.flatten().tolist()

        spectrum.valuesByNanometers = dict(zip(list(spectrum.valuesByNanometers.keys()), smoothedValues))

        result = SmoothSpectrumLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
