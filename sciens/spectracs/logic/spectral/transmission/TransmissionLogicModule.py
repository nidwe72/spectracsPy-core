from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleParameters import TransmissionLogicModuleParameters
from sciens.spectracs.logic.spectral.transmission.TransmissionLogicModuleResult import TransmissionLogicModuleResult
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class TransmissionLogicModule:
    # Transmittance T(λ) = sample(λ) / reference(λ). Dividing by the reference removes the illuminant
    # (the LED SPD), so the result is the oil's intrinsic transmittance — LED-independent (concept §3-4).

    # Low-reference floor, as a fraction of the reference PEAK. Read in LINEAR light (SPEC_capture_quality.md
    # §17): the spectra reaching here are gamma-decoded, so the historical "1% of peak" — which was 1% of a
    # gamma-ENCODED peak — is 0.01^2.2 here. Keeping the old 0.01 would silently mask every bin below
    # 0.01^(1/2.2) = 12.3% of peak DN and shorten the spectrum at both ends, where the white-LED reference is
    # weakest (§17.6/3; measured: it cut bins in 14 of 61 archived runs, up to 100 of 1520 — and restoring this
    # constant restores all 61 exactly). The guard's job is unchanged: below it, S/R amplifies noise.
    DEFAULT_REFERENCE_FLOOR_FRACTION = 6.31e-5

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
