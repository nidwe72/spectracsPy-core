from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModule import SpectrumToColorLogicModule
from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModuleParameters import SpectrumToColorLogicModuleParameters


class EvaluationColorUtil:
    # The Qt-free boundary (SPEC_pumpkin_integration.md P-B3): wraps SpectrumToColorLogicModule (which
    # returns a QColor) and hands the plugin only PLAIN data — an (r, g, b) tuple and the hue in DEGREES
    # (0-360, the proven verdict path — never QColor.hueF()). Keeps SpectralColorUtil out of plugin_sdk.

    def spectrumToRgbAndHue(self, spectrum):
        parameters = SpectrumToColorLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        result = SpectrumToColorLogicModule().spectrumToColor(parameters)
        color = result.getColor()
        rgb = (color.red(), color.green(), color.blue())
        return rgb, result.getHue()
