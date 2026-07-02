from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModule import TransmissionLogicModule
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleParameters import TransmissionLogicModuleParameters
from sciens.spectracs.model.spectral.SpectraContainer import SpectraContainer
from sciens.spectracs.plugin_sdk.roles import REFERENCE, SAMPLE, TRANSMISSION


class TransmissionOp:
    # container{reference, sample} -> container{transmission}: T = sample / reference. Two-input adapter
    # over TransmissionLogicModule (SPEC_pumpkin_integration.md B.2).

    def apply(self, container: SpectraContainer) -> SpectraContainer:
        spectra = container.getSpectra()
        parameters = TransmissionLogicModuleParameters()
        parameters.setReference(spectra[REFERENCE])
        parameters.setSample(spectra[SAMPLE])
        transmission = TransmissionLogicModule().transmission(parameters).getSpectrum()
        result = SpectraContainer()
        result.addToSpectra(transmission, TRANSMISSION)
        result.addToInputs(container)
        return result
