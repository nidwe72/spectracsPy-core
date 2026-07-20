import copy

import numpy

from sciens.spectracs.logic.spectral.flatOffsetBaseline.FlatOffsetBaselineLogicModuleParameters import FlatOffsetBaselineLogicModuleParameters
from sciens.spectracs.logic.spectral.flatOffsetBaseline.FlatOffsetBaselineLogicModuleResult import FlatOffsetBaselineLogicModuleResult
from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModule import MedianFilterSpectrumLogicModule
from sciens.spectracs.logic.spectral.medianFilter.MedianFilterSpectrumLogicModuleParameters import MedianFilterSpectrumLogicModuleParameters


class FlatOffsetBaselineLogicModule:

    def flatOffsetBaseline(self, flatOffsetBaselineLogicModuleParameters: FlatOffsetBaselineLogicModuleParameters):
        # Flat-offset (0th-order) baseline correction: subtract a SINGLE scalar — the absorbance floor of the
        # transparent, signal-free region — so a signal-free band reads ~0. This removes the ADDITIVE baseline b
        # that A = ε·c·l + b carries (dilution / scatter / refractive-index offset); the multiplicative c·l is left
        # for ratio/chromaticity to cancel. For the ABSORBED colour an additive b is a chromaticity SHIFT, so
        # removing it is what makes the intrinsic colour dilution-robust (SPEC_capability_proof.md §7.0.1). This is
        # COLOUR-ONLY: on the small absolute band means it injects noise (oilH, §7.0.1), so the metrics use the raw
        # / de-spiked absorbance instead. DISTINCT from RemoveBaselineLogicModule (a morphological opening for
        # SHARP emission lines) — a flat offset changes only the level, not the shape.
        #
        # Floor estimator (SPEC §7.0.1 (B)): "anchorMean" = mean over a deep-red transparent window OUTSIDE every
        # metric band (default) — low variance and non-overlapping; "medianMin" = min of a median-filtered copy
        # (kept selectable). See the parameters class.
        spectrum = flatOffsetBaselineLogicModuleParameters.getSpectrum()

        keys = list(spectrum.valuesByNanometers.keys())
        values = numpy.asarray(list(spectrum.valuesByNanometers.values()), float)
        if values.size == 0:
            result = FlatOffsetBaselineLogicModuleResult()
            result.setSpectrum(spectrum)
            return result

        floor = self.__floor(spectrum, values, flatOffsetBaselineLogicModuleParameters)
        corrected = numpy.clip(values - floor, 0, None)
        spectrum.valuesByNanometers = dict(zip(keys, corrected.tolist()))

        result = FlatOffsetBaselineLogicModuleResult()
        result.setSpectrum(spectrum)
        return result

    def __floor(self, spectrum, values, parameters):
        if parameters.getFloorMode() == "medianMin":
            return self.__medianMinFloor(spectrum, parameters.getFloorMedianWindow())
        return self.__anchorMeanFloor(spectrum, values, parameters.getAnchorLoNm(), parameters.getAnchorHiNm())

    def __anchorMeanFloor(self, spectrum, values, anchorLoNm, anchorHiNm):
        # Mean of A over the transparent anchor window. Fall back to the whole-spectrum min if the window lands
        # outside the captured range (nothing to average).
        anchor = [value for nanometer, value in spectrum.valuesByNanometers.items()
                  if anchorLoNm <= nanometer <= anchorHiNm]
        if not anchor:
            return float(numpy.min(values))
        return float(numpy.mean(anchor))

    def __medianMinFloor(self, spectrum, window):
        # Median-filter a THROWAWAY copy (the LogicModule mutates in place) and take its minimum — a spike-robust
        # min for callers that pass a non-de-spiked spectrum.
        parameters = MedianFilterSpectrumLogicModuleParameters()
        parameters.setSpectrum(copy.deepcopy(spectrum))
        parameters.setKernelSize(window)
        filtered = MedianFilterSpectrumLogicModule().medianFilter(parameters).getSpectrum()
        return float(min(filtered.valuesByNanometers.values()))
