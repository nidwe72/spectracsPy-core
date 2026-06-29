import copy

from sciens.base.Singleton import Singleton
from sciens.spectracs.model.spectral.Spectrum import Spectrum

from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModule import SmoothSpectrumLogicModule
from sciens.spectracs.logic.spectral.smoothSpectrum.SmoothSpectrumLogicModuleParameters import SmoothSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.removeBaseline.RemoveBaselineLogicModule import RemoveBaselineLogicModule
from sciens.spectracs.logic.spectral.removeBaseline.RemoveBaselineLogicModuleParameters import RemoveBaselineLogicModuleParameters
from sciens.spectracs.logic.spectral.rebinSpectrum.RebinSpectrumLogicModule import RebinSpectrumLogicModule
from sciens.spectracs.logic.spectral.rebinSpectrum.RebinSpectrumLogicModuleParameters import RebinSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.normalizeSpectrum.NormalizeSpectrumLogicModule import NormalizeSpectrumLogicModule
from sciens.spectracs.logic.spectral.normalizeSpectrum.NormalizeSpectrumLogicModuleParameters import NormalizeSpectrumLogicModuleParameters


class SpectrumUtil(Singleton):
    # Façade over the spectrum-processing chain. Each method is one operation that delegates its heavy
    # lifting to a dedicated per-operation logic module. There is no orchestrator: callers run whichever
    # steps they need, in the canonical order mean -> smooth -> removeBaseline -> rebin -> normalize.

    def removeBaseline(self, spectrum: Spectrum, windowSize: int = None, clone: bool = False):
        result = copy.deepcopy(spectrum) if clone else spectrum
        parameters = RemoveBaselineLogicModuleParameters()
        parameters.setSpectrum(result)
        parameters.setWindowSize(windowSize)
        return RemoveBaselineLogicModule().removeBaseline(parameters).getSpectrum()

    def mean(self, spectrum: Spectrum, clone: bool = False):
        result = copy.deepcopy(spectrum) if clone else spectrum
        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(result)
        return MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()

    def smooth(self, spectrum: Spectrum, clone: bool = False):
        result = copy.deepcopy(spectrum) if clone else spectrum
        parameters = SmoothSpectrumLogicModuleParameters()
        parameters.setSpectrum(result)
        return SmoothSpectrumLogicModule().smoothSpectrum(parameters).getSpectrum()

    def rebin(self, spectrum: Spectrum, clone: bool = False):
        result = copy.deepcopy(spectrum) if clone else spectrum
        parameters = RebinSpectrumLogicModuleParameters()
        parameters.setSpectrum(result)
        return RebinSpectrumLogicModule().rebinSpectrum(parameters).getSpectrum()

    def normalize(self, spectrum: Spectrum, clone: bool = False):
        result = copy.deepcopy(spectrum) if clone else spectrum
        parameters = NormalizeSpectrumLogicModuleParameters()
        parameters.setSpectrum(result)
        return NormalizeSpectrumLogicModule().normalizeSpectrum(parameters).getSpectrum()
