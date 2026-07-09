import numpy as np


class SpectrumFeatureLogicModule:
    """Generic, reusable spectral-feature ops on a Spectrum's {nm: value} map — NO use-case knowledge.

    Every op reads a nm WINDOW (never an exact float key — the keys are polynomial floats) and skips masked
    gaps, returning None when a band has no data (the low-level "couldn't compute" guard; the use-case
    plugin decides what that means). See SPEC_pumpkin_peak_ratio_eval.md §3, §7, §12/17-21. Pure/Qt-free."""

    def __sorted(self, spectrum):
        items = [(nm, value) for nm, value in spectrum.valuesByNanometers.items() if value is not None]
        items.sort(key=lambda pair: pair[0])
        return items

    def bandMean(self, spectrum, lo, hi):
        # Mean of the values whose nm falls in [lo, hi]; None if the window is empty (all masked / no keys).
        values = [value for nm, value in self.__sorted(spectrum) if lo <= nm <= hi]
        if not values:
            return None
        return float(np.mean(values))

    def peakInRange(self, spectrum, lo, hi):
        # (nm, value) of the local maximum in [lo, hi]; None if empty. Absorbs small calibration/peak shifts.
        points = [(nm, value) for nm, value in self.__sorted(spectrum) if lo <= nm <= hi]
        if not points:
            return None
        nm, value = max(points, key=lambda pair: pair[1])
        return (float(nm), float(value))

    def linearBaseline(self, spectrum, lam, anchorLo, anchorHi, halfWindow=5):
        # Value at `lam` on the straight line through the anchor-window means at anchorLo and anchorHi.
        aLo = self.bandMean(spectrum, anchorLo - halfWindow, anchorLo + halfWindow)
        aHi = self.bandMean(spectrum, anchorHi - halfWindow, anchorHi + halfWindow)
        if aLo is None or aHi is None:
            return None
        if anchorHi == anchorLo:
            return aLo
        fraction = (lam - anchorLo) / (anchorHi - anchorLo)
        return aLo + (aHi - aLo) * fraction

    def referenceGatedBand(self, valueSpectrum, gateSpectrum, lo, hi,
                           gateFraction, valueCeiling, gatePeakLo, gatePeakHi):
        # Mean of valueSpectrum over [lo, hi], keeping only wavelengths where the gate spectrum is healthy
        # (>= gateFraction of its peak over [gatePeakLo, gatePeakHi]) and the value is below valueCeiling.
        # Returns (mean, keptLambdas); (None, []) if nothing survives. Two-spectrum op (value + gate).
        gatePeak = self.peakInRange(gateSpectrum, gatePeakLo, gatePeakHi)
        if gatePeak is None:
            return (None, [])
        threshold = gateFraction * gatePeak[1]
        gate = dict(self.__sorted(gateSpectrum))
        keptLambdas = []
        values = []
        for nm, value in self.__sorted(valueSpectrum):
            if not (lo <= nm <= hi):
                continue
            gateValue = gate.get(nm)                       # value/gate share the nm grid (A derives from R)
            if gateValue is None or gateValue < threshold:  # trims the LED cyan dip
                continue
            if value > valueCeiling:                        # trims the saturated Soret edge
                continue
            keptLambdas.append(float(nm))
            values.append(value)
        if not values:
            return (None, [])
        return (float(np.mean(values)), keptLambdas)
