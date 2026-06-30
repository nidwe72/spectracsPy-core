from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleParameters import OilSampleSynthesisLogicModuleParameters
from sciens.spectracs.logic.spectral.synthesis.OilSampleSynthesisLogicModuleResult import OilSampleSynthesisLogicModuleResult
from sciens.spectracs.logic.spectral.synthesis.SpectrumSynthesisUtil import SpectrumSynthesisUtil


class OilSampleSynthesisLogicModule:
    # Synthesises an oil SAMPLE S(λ) = R · 10^(−A_oil·roast). With a targetHue, tunes the roast so the
    # transmission colour lands on it (forward-model + verify, never invert — concept §2).

    def synthesize(self, parameters: OilSampleSynthesisLogicModuleParameters):
        util = SpectrumSynthesisUtil()
        reference = parameters.getReference()

        roast = parameters.getRoast()
        if roast is None:
            roast = util.tuneRoastForHue(reference, parameters.getTargetHue())

        sample = util.synthesizeSample(reference, roast)
        achievedHue = util.transmissionHue(reference, sample)

        result = OilSampleSynthesisLogicModuleResult()
        result.setSpectrum(sample)
        result.setRoast(roast)
        result.setAchievedHue(achievedHue)
        return result
