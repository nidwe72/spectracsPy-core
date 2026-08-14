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

    def levelCrossing(self, spectrum, lo, hi, value):
        # SPEC_v_metric_integration.md §6.2/§7 — the nm inside [lo, hi] at which the curve CROSSES `value`,
        # linearly interpolated between the two bracketing samples; None when it never does.
        #
        # ⭐ WHY THIS EXISTS. The V tab draws a crosshair whose horizontal arm is the valley BAND MEAN and
        # whose vertical arm must land where the curve actually attains it — so both arms are true statements
        # at once. Marking the window's MINIMUM instead would sit on the curve but 23 % below the number the
        # metric divides (measured, §6.2): it renders fine and is silently false.
        #
        # ⚠ FIRST crossing, deliberately. Eight of fifteen archived fills cross the mean 3 or 5 times from
        # noise wiggles, all within a nanometre or two — "first" is the one deterministic choice, and the
        # measured spread of the answer across 58 runs is 522.2 +/- 1.5 nm.
        points = [(nm, v) for nm, v in self.__sorted(spectrum) if lo <= nm <= hi]
        if len(points) < 2:
            return None
        for (nmA, valueA), (nmB, valueB) in zip(points, points[1:]):
            deltaA, deltaB = valueA - value, valueB - value
            if deltaA == 0.0:
                return float(nmA)
            if deltaA * deltaB < 0.0:
                # linear interpolation between the bracketing samples — the marker sits on the crossing,
                # not on the nearer sample (a 0.15 nm grid would otherwise quantise it visibly).
                return float(nmA + (nmB - nmA) * deltaA / (deltaA - deltaB))
        # ⚠ NO SIGN CHANGE, yet the value is (essentially) inside the window's range — a FLAT window, or a
        # value that is the band MEAN of these very samples and misses exact equality by float summation
        # rounding. Both say "the curve is at that level somewhere here", so answer with the nearest sample
        # rather than None: a caller drawing a crosshair at a window's own mean must never get nothing back.
        # ⚠ The slack is needed because a mean can land a few ULPs OUTSIDE [min, max] of a constant window
        # (mean of 0.1 repeated is 0.09999999999999998) — that is arithmetic, not a missing crossing.
        # ⛔ None stays reserved for the honest case: a value genuinely outside the window's range.
        lowest, highest = min(v for _, v in points), max(v for _, v in points)
        slack = 1e-12 * max(abs(lowest), abs(highest), 1.0)
        if lowest - slack <= value <= highest + slack:
            return float(min(points, key=lambda point: abs(point[1] - value))[0])
        return None

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

    def linearBaselineCorrected(self, spectrum, windows):
        # Least-squares straight line through EVERY point falling in `windows` (a list of (lo, hi) anchor
        # windows), subtracted from the whole spectrum. Returns a NEW Spectrum; None if fewer than two
        # anchor points survive (a line needs two).
        #
        # Distinct from linearBaseline() above, which evaluates a two-anchor line AT one wavelength. This one
        # FITS across the anchor windows and CORRECTS the whole curve, so a downstream band mean reads the
        # feature above its local baseline rather than above zero.
        #
        # WHY a line and not an offset (SPEC_capture_quality.md §16.10.2): a re-seating tilt enters absorbance
        # as an offset AND a slope. A constant-anchor subtraction removes the offset; SNV removes offset and
        # scale; neither removes a slope. A two-window linear fit removes both.
        #
        # Generic: the windows are a PARAMETER — no use-case knowledge here (the plugin owns which windows).
        # They are expected DISJOINT; a point in two overlapping windows would be counted in both.
        # EACH WINDOW CARRIES EQUAL TOTAL WEIGHT, regardless of how many points fall in it. A window is ONE
        # piece of evidence about the baseline, not one per sample: an unweighted fit would let a wider window
        # silently dominate (520–540 contributes 135 points against 600–630's 212 on the bench rig, so the red
        # end would pull ~1.6x harder), and widening a window would then move the baseline as a side-effect.
        # Measured on the 25 runs of 2026-07-27 the two fits differ by ~0.5 % and change NO verdict — this is
        # for predictability under a window change, not for accuracy (SPEC_capture_quality.md §16.10.9).
        from sciens.spectracs.model.spectral.Spectrum import Spectrum
        if spectrum is None:
            return None
        points = self.__sorted(spectrum)
        anchors, weights = [], []
        for low, high in windows:
            inWindow = [(nm, value) for nm, value in points if low <= nm <= high]
            if not inWindow:
                continue
            anchors.extend(inWindow)
            weights.extend([1.0 / len(inWindow)] * len(inWindow))
        if len(anchors) < 2:
            return None
        nanometers = np.array([nm for nm, _ in anchors], dtype=np.float64)
        values = np.array([value for _, value in anchors], dtype=np.float64)
        if np.ptp(nanometers) == 0.0:                      # all anchors at one λ -> no slope is defined
            return None
        # polyfit's `w` multiplies the RESIDUAL, so it minimises sum((w*r)^2) — pass sqrt of the intended weight.
        slope, intercept = np.polyfit(nanometers, values, 1, w=np.sqrt(np.array(weights, dtype=np.float64)))
        corrected = Spectrum()
        corrected.role = spectrum.role
        corrected.sampleType = spectrum.sampleType
        corrected.valuesByNanometers = {
            nm: float(value - (slope * nm + intercept)) for nm, value in points}
        return corrected

    def fittedBaseline(self, spectrum, windows):
        # THE LINE that linearBaselineCorrected subtracts, as a Spectrum on the same keys — so a plot can draw
        # it (SPEC_soret_448_trim.md §12.2/§12.3). Derived as `spectrum - corrected`, NOT by fitting a second
        # time: a second polyfit would be a second source of truth for one line, free to drift from the one
        # the metrics actually use. None whenever the correction itself is None (fewer than two anchor points).
        #
        # ⭐ The identity this exists to make visible:
        #     mean(spectrum over band) - mean(fittedBaseline over band) == bandMean(corrected over band)
        # i.e. draw the band's mean as a bar on the plotted curve, draw this line beneath it, and the VERTICAL
        # GAP is the baselined value the verdict divides. Exact, because the correction is pointwise on the
        # same keys and a mean is linear.
        from sciens.spectracs.model.spectral.Spectrum import Spectrum
        corrected = self.linearBaselineCorrected(spectrum, windows)
        if corrected is None:
            return None
        correctedValues = corrected.valuesByNanometers
        baseline = Spectrum()
        baseline.role = spectrum.role
        baseline.sampleType = spectrum.sampleType
        baseline.valuesByNanometers = {
            nm: float(value - correctedValues[nm]) for nm, value in self.__sorted(spectrum)
            if nm in correctedValues}
        return baseline

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
