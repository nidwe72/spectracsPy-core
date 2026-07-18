import numpy as np

from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import MeanSpectrumLogicModuleParameters
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleResult import MeanSpectrumLogicModuleResult


class MeanSpectrumLogicModule:
    """Temporal reduction of the captured frames (SPEC_capture_quality.md §6, Topic 2/M2). Combines the per-frame
    {nm: value} spectra into one with a **sigma-clipped mean** per wavelength bin — a transient glitch/read-spike
    frame is rejected while the full √N noise benefit of averaging is kept. Feeds BOTH the live-display mean and
    the real processing pipeline (`MeanOp` is a thin adapter over this).

    Replaces the old plain `numpy.matrix(...).mean()` which used deprecated `numpy.matrix`, zipped the result
    against the LAST frame's keys assuming identical key ORDER across frames, and had no outlier rejection."""

    def meanSpectrum(self, meanSpectrumLogicModuleParameters: MeanSpectrumLogicModuleParameters):
        spectrum = meanSpectrumLogicModuleParameters.getSpectrum()
        frames = spectrum.getCapturedValuesByNanometers()      # list of {nm: value}, one dict per captured frame

        result = MeanSpectrumLogicModuleResult()
        if not frames:
            result.setSpectrum(spectrum)
            return result

        # Align explicitly by the nm-key set (SPEC §6 / D9): the px->nm cubic makes every frame's keys identical,
        # but align by KEY (not zip-by-position against the last frame — the old bug) and tolerate a dropped frame
        # missing a key (-> NaN, ignored by the clip) so N < expected is valid.
        keys = list(frames[0].keys())
        stack = np.array([[frame.get(key, np.nan) for key in keys] for frame in frames], dtype=float)
        robust = RobustReductionLogicModule()
        # C1 (SPEC_capture_quality.md §14.8): drop whole frames that are a GLOBAL brightness outlier (the coherent
        # dim group an auto-exposure ramp leaves in the reference burst) BEFORE the per-bin sigma-clip — the σ-clip
        # can't reject a large-minority dim group, so without this the mean is biased low → T = S/R corrupted.
        keepMask = robust.rejectDimFrames(stack)
        keptStack = stack[keepMask] if keepMask.any() else stack
        reduced = robust.sigmaClippedMean(keptStack)

        spectrum.valuesByNanometers = dict(zip(keys, [float(value) for value in reduced]))
        result.setSpectrum(spectrum)
        return result
