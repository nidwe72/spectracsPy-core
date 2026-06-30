from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleParameters import TransmissionLogicModuleParameters
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleResult import TransmissionLogicModuleResult
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class TransmissionLogicModule:
    # Transmittance T(λ) = sample(λ) / reference(λ). Dividing by the reference removes the illuminant
    # (the LED SPD), so the result is the oil's intrinsic transmittance — LED-independent (concept §3-4).

    DEFAULT_REFERENCE_FLOOR_FRACTION = 0.01

    def transmission(self, transmissionLogicModuleParameters: TransmissionLogicModuleParameters):
        reference = transmissionLogicModuleParameters.getReference()
        sample = transmissionLogicModuleParameters.getSample()

        floorFraction = transmissionLogicModuleParameters.getReferenceFloorFraction()
        if floorFraction is None:
            floorFraction = self.DEFAULT_REFERENCE_FLOOR_FRACTION

        referenceValues = reference.valuesByNanometers
        sampleValues = sample.valuesByNanometers

        # Low-reference guard: where the reference is at/below a small fraction of its peak (a dip or the
        # spectrum edge), S/R amplifies noise and is undefined at zero — so we mask those wavelengths.
        referenceMaximum = max(referenceValues.values()) if len(referenceValues) > 0 else 0.0
        floor = floorFraction * referenceMaximum

        transmittanceByNanometers = {}
        for nanometer, referenceValue in referenceValues.items():
            if nanometer not in sampleValues:
                continue
            if referenceValue <= floor:
                continue
            transmittanceByNanometers[nanometer] = sampleValues[nanometer] / referenceValue

        transmission = Spectrum()
        transmission.setValuesByNanometers(transmittanceByNanometers)

        result = TransmissionLogicModuleResult()
        result.setSpectrum(transmission)
        return result
