from sciens.spectracs.logic.spectral.verdict.RoastState import RoastState
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModuleParameters import VerdictLogicModuleParameters
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModuleResult import VerdictLogicModuleResult


class VerdictLogicModule:
    # Maps a measured hue to a roast-state verdict on the perfect-centred band (concept §5): hue too
    # high (too green) -> UNDER-ROASTED; too low (too brown) -> OVER-ROASTED; in between -> PERFECT.

    def verdict(self, verdictLogicModuleParameters: VerdictLogicModuleParameters):
        hue = verdictLogicModuleParameters.getHue()

        if hue is None:
            roastState = None
        elif hue < verdictLogicModuleParameters.getOverRoastedBelowHue():
            roastState = RoastState.OVER_ROASTED
        elif hue > verdictLogicModuleParameters.getUnderRoastedAboveHue():
            roastState = RoastState.UNDER_ROASTED
        else:
            roastState = RoastState.PERFECT_ROASTED

        result = VerdictLogicModuleResult()
        result.setRoastState(roastState)
        return result
