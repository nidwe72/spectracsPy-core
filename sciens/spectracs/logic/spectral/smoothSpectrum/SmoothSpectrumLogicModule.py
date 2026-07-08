from scipy.signal import savgol_filter

from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModuleParameters import SmoothSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModuleResult import SmoothSpectrumLogicModuleResult


class SmoothSpectrumLogicModule:

    def smoothSpectrum(self, smoothSpectrumLogicModuleParameters: SmoothSpectrumLogicModuleParameters):
        # Savitzky-Golay smoothing applied `passes` times in sequence (default window 10, polyorder 3,
        # 7 passes — the historical behaviour). Callers that must preserve close features (calibration
        # doublet) pass fewer passes / a smaller window (SPEC_dev_measure_bench (a)).
        spectrum = smoothSpectrumLogicModuleParameters.getSpectrum()
        passes = smoothSpectrumLogicModuleParameters.getPasses()
        window = smoothSpectrumLogicModuleParameters.getWindow()
        polyorder = smoothSpectrumLogicModuleParameters.getPolyorder()

        smoothedValues = list(spectrum.valuesByNanometers.values())
        for _ in range(passes):
            smoothedValues = savgol_filter(smoothedValues, window, polyorder)

        smoothedValues = smoothedValues.flatten().tolist() if hasattr(smoothedValues, "flatten") else list(smoothedValues)

        spectrum.valuesByNanometers = dict(zip(list(spectrum.valuesByNanometers.keys()), smoothedValues))

        result = SmoothSpectrumLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
