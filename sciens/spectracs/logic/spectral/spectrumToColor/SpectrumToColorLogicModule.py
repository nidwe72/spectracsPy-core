import colorsys

from PySide6.QtGui import QColor
from colour import SpectralDistribution, MSDS_CMFS, SDS_ILLUMINANTS, sd_to_XYZ, XYZ_to_xy
from rgbxy import Converter

from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModuleParameters import SpectrumToColorLogicModuleParameters
from sciens.spectracs.logic.spectral.spectrumToColor.SpectrumToColorLogicModuleResult import SpectrumToColorLogicModuleResult


class SpectrumToColorLogicModule:

    def spectrumToColor(self, spectrumToColorLogicModuleParameters: SpectrumToColorLogicModuleParameters):
        # Convert a processed spectrum ({nm: value}, expected on the 380..780 nm grid and normalized) into
        # a perceptual colour via the CIE pipeline:
        #   SpectralDistribution -> sd_to_XYZ (CIE 1931 2 deg, D65) -> XYZ_to_xy -> xy_to_rgb (rgbxy)
        #   -> rgb_to_hls (colorsys, HLS order) -> swatch via hls_to_rgb with a fixed lightness.
        spectrum = spectrumToColorLogicModuleParameters.getSpectrum()
        lightness = spectrumToColorLogicModuleParameters.getLightness()

        valuesByNanometers = spectrum.valuesByNanometers

        # Empty / unprocessed spectrum -> neutral grey swatch, no measured colour.
        if not valuesByNanometers:
            result = SpectrumToColorLogicModuleResult()
            result.setColor(QColor.fromRgbF(0.5, 0.5, 0.5))
            result.setHue(0.0)
            result.setLightness(0.0)
            result.setSaturation(0.0)
            return result

        spectralDistribution = SpectralDistribution(valuesByNanometers)
        cmfs = MSDS_CMFS["CIE 1931 2 Degree Standard Observer"]
        illuminant = SDS_ILLUMINANTS["D65"]

        xyz = sd_to_XYZ(spectralDistribution, cmfs, illuminant, method="Integration")
        xy = XYZ_to_xy(xyz)

        converter = Converter()
        rgb = converter.xy_to_rgb(xy[0], xy[1])

        red = min(1.0, max(0.0, rgb[0] / 255.0))
        green = min(1.0, max(0.0, rgb[1] / 255.0))
        blue = min(1.0, max(0.0, rgb[2] / 255.0))

        # colorsys uses HLS order: hls[0]=hue, hls[1]=lightness, hls[2]=saturation.
        hls = colorsys.rgb_to_hls(red, green, blue)
        measuredHue = hls[0] * 360.0
        measuredLightness = hls[1] * 100.0
        measuredSaturation = hls[2] * 100.0

        # Swatch: keep the measured hue + saturation, pin lightness to the requested value.
        swatchRgb = colorsys.hls_to_rgb(hls[0], lightness, hls[2])
        color = QColor.fromRgbF(swatchRgb[0], swatchRgb[1], swatchRgb[2])

        result = SpectrumToColorLogicModuleResult()
        result.setColor(color)
        result.setHue(measuredHue)
        result.setLightness(measuredLightness)
        result.setSaturation(measuredSaturation)
        return result
