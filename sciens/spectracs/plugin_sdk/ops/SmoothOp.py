import copy

from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModule import SmoothSpectrumLogicModule
from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModuleParameters import SmoothSpectrumLogicModuleParameters
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer


class SmoothOp:
    # container -> container: Savitzky-Golay smooth every spectrum. Thin, role-agnostic adapter over
    # SmoothSpectrumLogicModule. Defaults to LIGHT smoothing (1 pass / window 7 / polyorder 3) — enough to
    # suppress pixel noise while preserving the broad colour-carrying absorption envelope (SPEC_capability_
    # proof.md §7.0.1 G3); pass heavier settings via the constructor for other uses. NON-DESTRUCTIVE: each
    # spectrum is deep-copied before smoothing (same rationale as BaselineOffsetOp).

    def __init__(self, passes: int = 1, window: int = 7, polyorder: int = 3):
        self.__passes = passes
        self.__window = window
        self.__polyorder = polyorder

    def apply(self, container: SpectraContainer) -> SpectraContainer:
        result = SpectraContainer()
        for role, spectrum in container.getSpectra().items():
            clone = copy.deepcopy(spectrum)
            parameters = SmoothSpectrumLogicModuleParameters()
            parameters.setSpectrum(clone)
            parameters.setPasses(self.__passes)
            parameters.setWindow(self.__window)
            parameters.setPolyorder(self.__polyorder)
            smoothed = SmoothSpectrumLogicModule().smoothSpectrum(parameters).getSpectrum()
            result.addToSpectra(smoothed, role)
        result.addToInputs(container)
        return result
