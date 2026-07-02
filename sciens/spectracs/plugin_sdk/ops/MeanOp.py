from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer


class MeanOp:
    # container -> container: reduces each bag's captured frames to their mean spectrum. Thin adapter over
    # the Spectrum-based MeanSpectrumLogicModule (SPEC_pumpkin_integration.md B.2 / P-B2).

    def apply(self, container: SpectraContainer) -> SpectraContainer:
        result = SpectraContainer()
        for role, spectrum in container.getSpectra().items():
            parameters = MeanSpectrumLogicModuleParameters()
            parameters.setSpectrum(spectrum)
            meaned = MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()
            result.addToSpectra(meaned, role)
        result.addToInputs(container)
        return result
