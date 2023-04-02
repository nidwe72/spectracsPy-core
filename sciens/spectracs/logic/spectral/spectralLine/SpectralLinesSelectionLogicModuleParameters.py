from typing import List

from sciens.spectracs.logic.spectral.spectralLine.ISpectralLinesSelectionLogicModuleSelectionParameter import \
    IPeakSelectionLogicModuleSelectionParameter
from sciens.spectracs.logic.spectral.spectralLine.PeakSelectionLogicModuleSelectByPixelIndex import \
    PeakSelectionLogicModuleSelectByPixelIndex
from sciens.spectracs.logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleSelectByIntensity import \
    PeakSelectionLogicModuleSelectByIntensity
from sciens.spectracs.logic.spectral.spectralLine.SpectralLinesSelectionLogicModuleSelectByProminenceParameter import \
    PeakSelectionLogicModuleSelectByProminenceParameter
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine
from sciens.spectracs.model.spectral.Spectrum import Spectrum


class SpectralLinesSelectionLogicModuleParameters:
    __spectrum: Spectrum = None

    __selectionParameters: List[IPeakSelectionLogicModuleSelectionParameter] = None

    def __init__(self):
        self.setSelectionParameters([])
        pass


    def getSelectionParameters(self) -> List[IPeakSelectionLogicModuleSelectionParameter]:
        return self.__selectionParameters

    def setSelectionParameters(self, selectionParameters: List[IPeakSelectionLogicModuleSelectionParameter]):
        self.__selectionParameters = selectionParameters
        return self

    def __addToSelectionParameters(self, selectionParameter: IPeakSelectionLogicModuleSelectionParameter):
        self.__selectionParameters.append(selectionParameter)
        return self

    def addSelectByProminence(self, count: int,leftSpectralLine:SpectralLine=None,rightSpectralLine:SpectralLine=None):
        parameter = PeakSelectionLogicModuleSelectByProminenceParameter()
        parameter.count = count
        parameter.leftSpectralLine = leftSpectralLine
        parameter.rightSpectralLine = rightSpectralLine
        self.__addToSelectionParameters(parameter)
        return self

    def addSelectByPixelIndex(self, count: int,reverse:bool=False):
        parameter = PeakSelectionLogicModuleSelectByPixelIndex()
        parameter.setCount(count)
        parameter.reverse=reverse
        self.__addToSelectionParameters(parameter)
        return self

    def addSelectByIntensity(self, count: int):
        parameter = PeakSelectionLogicModuleSelectByIntensity()
        parameter.setCount(count)
        self.__addToSelectionParameters(parameter)
        return self

    def getSpectrum(self):
        return self.__spectrum

    def setSpectrum(self, spectrum):
        self.__spectrum = spectrum
        return self
