from sciens.spectracs.logic.spectral.verdict.VerdictLogicModule import VerdictLogicModule
from sciens.spectracs.logic.spectral.verdict.VerdictLogicModuleParameters import VerdictLogicModuleParameters


class VerdictOp:
    # hue (degrees) -> RoastState. Thin adapter over VerdictLogicModule (SPEC_pumpkin_integration.md B.2).
    # Returns the RoastState (a str-Enum), so .value is the plain string for a VerdictView.

    def verdict(self, hue):
        parameters = VerdictLogicModuleParameters()
        parameters.setHue(hue)
        return VerdictLogicModule().verdict(parameters).getRoastState()
