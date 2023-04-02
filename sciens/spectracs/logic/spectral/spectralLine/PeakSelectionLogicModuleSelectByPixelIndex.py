from sciens.spectracs.logic.spectral.spectralLine.ISpectralLinesSelectionLogicModuleSelectionParameter import \
    IPeakSelectionLogicModuleSelectionParameter


class PeakSelectionLogicModuleSelectByPixelIndex(IPeakSelectionLogicModuleSelectionParameter):

    def __init__(self):
        self.__count:int = 1
        self.__reverse:bool=False

    def getCount(self):
        return self.__count

    def setCount(self, count):
        self.__count = count
        return self

    @property
    def reverse(self):
        return self.__reverse

    @reverse.setter
    def reverse(self, reverse):
        self.__reverse=reverse
