import copy

from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModule import MedianFilterSpectrumLogicModule
from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModuleParameters import MedianFilterSpectrumLogicModuleParameters
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer


class MedianFilterOp:
    # container -> container: median-filter (DE-SPIKE) every spectrum. Removes narrow instrument spikes — the lamp
    # blue-pump edge (~473 nm), registration artifacts (~607 nm), hot pixels — while leaving broad oil absorption
    # features intact (real pigment bands are 20-100 nm wide; spikes are 1-5 px), SPEC_capability_proof.md §7.0.1.
    # Thin, role-agnostic adapter over MedianFilterSpectrumLogicModule (like MeanOp / SmoothOp). Kernel default 7
    # (small: kills sub-nm spikes, preserves the ~20-30 nm Q-band). NON-DESTRUCTIVE: deep-copies before filtering.

    def __init__(self, kernelSize: int = 7):
        self.__kernelSize = kernelSize

    def apply(self, container: SpectraContainer) -> SpectraContainer:
        result = SpectraContainer()
        for role, spectrum in container.getSpectra().items():
            clone = copy.deepcopy(spectrum)
            parameters = MedianFilterSpectrumLogicModuleParameters()
            parameters.setSpectrum(clone)
            parameters.setKernelSize(self.__kernelSize)
            filtered = MedianFilterSpectrumLogicModule().medianFilter(parameters).getSpectrum()
            result.addToSpectra(filtered, role)
        result.addToInputs(container)
        return result
