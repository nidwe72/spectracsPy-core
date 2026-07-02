from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModule import AbsorptionLogicModule
from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModuleParameters import AbsorptionLogicModuleParameters
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE, ABSORPTION


class AbsorptionOp:
    # container{reference, sample} -> container{absorption}: A = -log10(sample / reference). Two-input
    # adapter over AbsorptionLogicModule (SPEC_pumpkin_integration.md B.2).

    def apply(self, container: SpectraContainer) -> SpectraContainer:
        spectra = container.getSpectra()
        parameters = AbsorptionLogicModuleParameters()
        parameters.setReference(spectra[REFERENCE])
        parameters.setSample(spectra[SAMPLE])
        absorption = AbsorptionLogicModule().absorption(parameters).getSpectrum()
        result = SpectraContainer()
        result.addToSpectra(absorption, ABSORPTION)
        result.addToInputs(container)
        return result
