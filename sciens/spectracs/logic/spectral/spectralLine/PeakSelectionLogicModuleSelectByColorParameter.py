from sciens.spectracs.logic.spectral.spectralLine.ISpectralLinesSelectionLogicModuleSelectionParameter import \
    IPeakSelectionLogicModuleSelectionParameter
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class PeakSelectionLogicModuleSelectByColorParameter(IPeakSelectionLogicModuleSelectionParameter):
    __spectralLine: SpectralLine = None

    def getSpectralLine(self):
        return self.__spectralLine

    def setSpectralLine(self, spectralLine):
        self.__spectralLine = spectralLine
        return self
