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
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModule import TransmissionLogicModule
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleParameters import TransmissionLogicModuleParameters
from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModule import AbsorptionLogicModule
from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModuleParameters import AbsorptionLogicModuleParameters


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

    def smooth(self, spectrum: Spectrum, clone: bool = False,
               passes: int = None, window: int = None, polyorder: int = None):
        result = copy.deepcopy(spectrum) if clone else spectrum
        parameters = SmoothSpectrumLogicModuleParameters()
        parameters.setSpectrum(result)
        # Only override the historical defaults when a caller explicitly asks for lighter smoothing.
        if passes is not None:
            parameters.setPasses(passes)
        if window is not None:
            parameters.setWindow(window)
        if polyorder is not None:
            parameters.setPolyorder(polyorder)
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

    def transmission(self, reference: Spectrum, sample: Spectrum, referenceFloorFraction: float = None):
        # Two-input shortcut: transmittance T = sample / reference (illuminant cancels).
        parameters = TransmissionLogicModuleParameters()
        parameters.setReference(reference)
        parameters.setSample(sample)
        parameters.setReferenceFloorFraction(referenceFloorFraction)
        return TransmissionLogicModule().transmission(parameters).getSpectrum()

    def absorption(self, reference: Spectrum, sample: Spectrum, referenceFloorFraction: float = None):
        # Two-input shortcut: absorbance A = -log10(sample / reference).
        parameters = AbsorptionLogicModuleParameters()
        parameters.setReference(reference)
        parameters.setSample(sample)
        parameters.setReferenceFloorFraction(referenceFloorFraction)
        return AbsorptionLogicModule().absorption(parameters).getSpectrum()
