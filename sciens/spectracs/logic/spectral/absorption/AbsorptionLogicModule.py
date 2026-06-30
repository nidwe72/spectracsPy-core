import math

from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModuleParameters import AbsorptionLogicModuleParameters
from sciens.spectracs.logic.spectral.absorption.AbsorptionLogicModuleResult import AbsorptionLogicModuleResult
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModule import TransmissionLogicModule
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleParameters import TransmissionLogicModuleParameters
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class AbsorptionLogicModule:
    # Absorbance A(λ) = -log10(sample / reference) = -log10(T) (Beer-Lambert). Built on the transmittance
    # op so the low-reference guard is shared. A is for the absorption plot/analysis; the colour comes
    # from T (concept §3).

    def absorption(self, absorptionLogicModuleParameters: AbsorptionLogicModuleParameters):
        transmissionParameters = TransmissionLogicModuleParameters()
        transmissionParameters.setReference(absorptionLogicModuleParameters.getReference())
        transmissionParameters.setSample(absorptionLogicModuleParameters.getSample())
        transmissionParameters.setReferenceFloorFraction(absorptionLogicModuleParameters.getReferenceFloorFraction())
        transmission = TransmissionLogicModule().transmission(transmissionParameters).getSpectrum()

        absorbanceByNanometers = {}
        for nanometer, transmittance in transmission.valuesByNanometers.items():
            if transmittance > 0.0:
                absorbanceByNanometers[nanometer] = -math.log10(transmittance)

        absorption = Spectrum()
        absorption.setValuesByNanometers(absorbanceByNanometers)

        result = AbsorptionLogicModuleResult()
        result.setSpectrum(absorption)
        return result
