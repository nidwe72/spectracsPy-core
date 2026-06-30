from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleParameters import LedReferenceSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.LedReferenceSynthesisLogicModuleResult import LedReferenceSynthesisLogicModuleResult
from sciens.spectracs.logic.spectral.synthesis.SpectrumSynthesisUtil import SpectrumSynthesisUtil


class LedReferenceSynthesisLogicModule:
    # Synthesises the REFERENCE spectrum R(λ) from a set of LED SPDs (the synthetic illuminant).

    def synthesize(self, parameters: LedReferenceSynthesisLogicModuleParameters):
        spectrum = SpectrumSynthesisUtil().synthesizeReference(
            nanometers=parameters.getNanometers(), ledSet=parameters.getLedSet())
        result = LedReferenceSynthesisLogicModuleResult()
        result.setSpectrum(spectrum)
        return result
