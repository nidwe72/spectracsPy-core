from sciens.spectracs.logic.spectral.spectralLine.ISpectralLinesSelectionLogicModuleSelectionParameter import \
    IPeakSelectionLogicModuleSelectionParameter
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class PeakSelectionLogicModuleSelectByProminenceParameter(IPeakSelectionLogicModuleSelectionParameter):

    def __init__(self):
        self.__count:int=1
        self.__leftSpectralLine:SpectralLine = None
        self.__rightSpectralLine: SpectralLine = None

    @property
    def count(self):
        return self.__count

    @count.setter
    def count(self, count):
        self.__count = count

    @property
    def leftSpectralLine(self):
        return self.__leftSpectralLine

    @leftSpectralLine.setter
    def leftSpectralLine(self, leftSpectralLine: SpectralLine):
        self.__leftSpectralLine = leftSpectralLine

    @property
    def rightSpectralLine(self):
        return self.__rightSpectralLine

    @rightSpectralLine.setter
    def rightSpectralLine(self, rightSpectralLine):
        self.__rightSpectralLine=rightSpectralLine
