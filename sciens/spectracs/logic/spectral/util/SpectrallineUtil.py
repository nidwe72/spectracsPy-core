from operator import attrgetter
from typing import Dict
from typing import List

import numpy as np

from sciens.base.Singleton import Singleton
from sciens.spectracs.logic.spectral.util.SpectralColorUtil import SpectralColorUtil
from sciens.spectracs.logic.spectral.util.SpectralLineMasterDataUtil import SpectralLineMasterDataUtil
from sciens.spectracs.model.databaseEntity.spectral.device.SpectralLine import SpectralLine


class SpectralLineUtil(Singleton):

    def createSpectralLinesByNames(self)->Dict[str,SpectralLine]:

        spectralLineMasterDatas=SpectralLineMasterDataUtil().getSpectralLineMasterDatasByNames()
        result = {}
        for spectralLineMasterData in spectralLineMasterDatas.values():
            spectralLine = SpectralLine()
            spectralLine.spectralLineMasterData =spectralLineMasterData
            nanometer = spectralLineMasterData.nanometer
            if nanometer>780:
                nanometer=780
            spectralLine.color = SpectralColorUtil().wavelengthToColor(nanometer)
            result[spectralLine.spectralLineMasterData.name] = spectralLine

        return result

    def getSpectralLinesByProminences(self, spectralLinesCollection: List[SpectralLine]) -> Dict[float, SpectralLine]:

        result: Dict[float, SpectralLine] = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.prominence] = spectralLine
        return result

    def sortSpectralLinesByProminences(self, spectralLinesCollection: List[SpectralLine]) -> List[SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('prominence'), reverse=True)
        return spectralLinesCollection

    def sortSpectralLinesByPixelIndices(self, spectralLinesCollection: List[SpectralLine]) -> Dict[int, SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('pixelIndex'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.pixelIndex] = spectralLine
        return result

    def sortSpectralLinesByNanometers(self, spectralLinesCollection: List[SpectralLine]) -> Dict[int, SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('spectralLineMasterData.nanometer'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.spectralLineMasterData.nanometer] = spectralLine
        return result

    def sortSpectralLinesByNames(self, spectralLinesCollection: List[SpectralLine]) -> Dict[int, SpectralLine]:
        spectralLinesCollection.sort(key=attrgetter('spectralLineMasterData.name'), reverse=False)
        result = {}
        for spectralLine in spectralLinesCollection:
            result[spectralLine.spectralLineMasterData.name] = spectralLine
        return result

    def getPixelIndices(self, spectralLinesCollection: List[SpectralLine]) -> List[int]:
        result = []
        for spectralLine in spectralLinesCollection:
            result.append(spectralLine.pixelIndex)
        return result

    def getNanometers(self, spectralLinesCollection: List[SpectralLine]) -> List[float]:
        result = []
        for spectralLine in spectralLinesCollection:
            result.append(spectralLine.spectralLineMasterData.nanometer)
        return result

    def polyfit(self,spectralLinesCollection: List[SpectralLine]):
        nanometers = self.getNanometers(spectralLinesCollection)
        pixelIndices = self.getPixelIndices(spectralLinesCollection)
        coefficients=np.polyfit(pixelIndices, nanometers,3)
        result = np.poly1d(coefficients)
        return result





