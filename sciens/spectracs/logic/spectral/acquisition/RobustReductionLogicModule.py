"""Robust reduction estimators for capture (SPEC_capture_quality.md §6, Topic 2/M2). Pure numpy — no Qt, no ORM —
so the estimators are unit-testable in isolation.

Two DIFFERENT enemies need two DIFFERENT stages (the load-bearing subtlety):
  * SPATIAL, across the ROI band rows (`tukeyBiweightPerColumn`): a hot/dead pixel is at the SAME location in
    every frame, so no temporal combine removes it — only a spatial estimator across rows does. Few-ish samples,
    so Tukey biweight (Edwin-LOCKED): robust at small N, smoothly discards an outlier that lands in the band.
  * TEMPORAL, across frames (`sigmaClippedMean`): a glitch/read-spike frame is transient — only a temporal
    estimator catches it. Many samples, so a sigma-clipped mean keeps the full √N noise benefit.

Both are NaN-aware (caller masks saturated==255 / dead==0 to NaN) and both degrade gracefully on degenerate input
(MAD==0 constant column, or an all-masked column) — see the guards inline.
"""
import warnings

import numpy as np


def _nanmedian(values, axis):
    # np.nanmedian warns "All-NaN slice encountered" for a fully-masked column/bin — that case is DELIBERATE
    # (caller/guards handle the NaN result), so silence just that expected warning to keep production logs clean.
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", category=RuntimeWarning)
        return np.nanmedian(values, axis=axis)


class RobustReductionLogicModule:

    TUKEY_C = 6.0          # biweight tuning constant (c·MAD); 6·MAD ≈ 4σ cutoff — spec-locked
    TUKEY_ITERS = 2        # location refinement passes
    SIGMA_K = 3.0          # temporal clip threshold in robust sigma
    SIGMA_ITERS = 5        # max clip passes (stops early on convergence)
    DIM_FRAME_K = 3.0      # per-FRAME brightness reject threshold in robust sigma (§14.8 C1)
    MIN_FRAMES_TO_REJECT = 5   # need enough frames for a trustworthy robust brightness center
    DIM_FRAME_SCALE_FLOOR = 0.045  # floor the reject scale at 4.5% of the brightness level: a blatant dim frame
                                   # can't survive a pathologically tight clean cluster (MAD≈0), and near-identical
                                   # clean frames aren't over-rejected. So the effective reject band is ≥ K·4.5%
                                   # ≈ 13% dim in LINEAR light.
                                   # Was 2% when the frames arriving here were gamma-ENCODED (SPEC_capture_quality
                                   # §17): x^γ multiplies every small relative deviation by γ, so a 2% linear band
                                   # is only ~0.9% in camera DN and C1 would reject ~γ× more eagerly. The RATIO
                                   # constants above (TUKEY_C, SIGMA_K, DIM_FRAME_K) need no such correction —
                                   # deviation and MAD scale together — this fixed FRACTION is the one exception.
    __MAD_TO_SIGMA = 1.4826

    def tukeyBiweightPerColumn(self, band, tieWindow=None):
        """band: 2-D array (rows × columns) of intensities; **NaN marks excluded pixels** (the caller masks
        saturated / dead — saturation is a per-CHANNEL fact, so it must be masked before qGray is formed, not
        detected here). Returns a 1-D array, one robust location per column. An all-NaN column returns NaN (the
        caller supplies the fallback, e.g. the plain median).

        ⛔⛔ `MAD == 0` DOES NOT MEAN "CONSTANT COLUMN" — IT MEANS "OVER HALF THE ROWS SHARE THE MEDIAN", AND
        THAT IS THE ORDINARY CASE AT LOW SIGNAL (SPEC_capture_quality.md §16.12.17, measured 2026-08-19). The
        guard below used to read `moving = mad > 0` with the comment *"constant columns keep their median"*,
        so such a column returned ONE EXACT INTEGER CODE and the information carried by the minority rows was
        discarded. Measured on a live frame, 291 rows per column: **35 % of all columns**, 44-47 % below DN 30,
        and **0 % above DN 60** — which is exactly the boundary between a smooth blue end and a staircase in
        500-630 nm. The discarded signal is real: in those columns the plain mean sits a median of **0.45 DN**
        away from the median that was returned instead.

        ⭐ `tieWindow` is the caller's statement of **how far apart two adjacent quantisation levels are**, in
        the SAME units as `band`, per column (scalar or 1-D). When a column's MAD collapses to zero and a
        window is supplied, the location becomes the MEAN of the rows within ±`tieWindow` of the median —
        robust like the biweight (a hot pixel is far outside the window and cannot pull it), but it USES the
        dither instead of throwing it away, which is what recovers sub-quantum resolution.
        ⚠ `tieWindow=None` keeps the historical median behaviour exactly, so callers that have no notion of a
        quantum (tests, synthetic bands) are unchanged.
        ⛔ This module still knows nothing about gamma or DN — the quantum is a fact about the CAPTURE CHAIN
        and is computed by the caller that owns the decode.
        """
        band = np.asarray(band, dtype=float)
        if band.ndim != 2 or band.shape[0] == 0:
            raise ValueError("tukeyBiweightPerColumn expects a non-empty 2-D (rows × cols) band")

        median = _nanmedian(band, axis=0)                       # NaN for all-NaN columns
        mad = _nanmedian(np.abs(band - median), axis=0)
        mad = np.where(np.isnan(mad), 0.0, mad)

        location = median.copy()
        moving = mad > 0                                        # all-NaN columns keep their median (NaN)
        if tieWindow is not None:
            location = np.where(~moving, self.__tiedMean(band, median, tieWindow), location)
        for _ in range(self.TUKEY_ITERS):
            scale = np.where(moving, self.TUKEY_C * mad, np.inf)
            u = (band - location) / scale
            weight = np.where(np.abs(u) < 1, (1.0 - u * u) ** 2, 0.0)
            weight = np.where(np.isnan(weight), 0.0, weight)
            weightSum = np.sum(weight, axis=0)
            valueSum = np.nansum(weight * np.nan_to_num(band), axis=0)
            updated = np.where(weightSum > 0, valueSum / np.maximum(weightSum, 1e-12), location)
            location = np.where(moving, updated, location)

        return location

    @staticmethod
    def __tiedMean(band, median, tieWindow):
        """The MEAN of the rows within ±`tieWindow` of the column median — the MAD==0 fallback (§16.12.17).

        ⭐ Why a windowed mean and not a plain one: with 291 rows a single hot pixel at 255 against a median of
        12 shifts a plain mean by 0.84 DN, which is LARGER than the ~0.45 DN of real sub-quantum signal being
        recovered. The window is what keeps the fix from costing more than it buys.
        ⚠ Falls back to the median wherever the window admits nothing (an all-NaN column, or a degenerate
        window), so this can never make a column worse than it was."""
        window = np.abs(np.asarray(tieWindow, dtype=float))
        inside = np.abs(band - median) <= window
        inside &= ~np.isnan(band)
        count = np.sum(inside, axis=0)
        total = np.nansum(np.where(inside, band, 0.0), axis=0)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=RuntimeWarning)
            mean = np.where(count > 0, total / np.maximum(count, 1), median)
        return np.where(np.isnan(mean), median, mean)

    def sigmaClippedMean(self, stack):
        """stack: 2-D array (frames × bins), NaN allowed for missing/dropped values. Per bin: iteratively reject
        samples beyond k·σ (σ from the median absolute deviation), then average the survivors — so a glitch frame
        is dropped while the full √N benefit is kept. Tolerates N<expected (dropped frames) and a constant bin
        (σ==0 → nothing clipped)."""
        stack = np.asarray(stack, dtype=float)
        if stack.ndim != 2 or stack.shape[0] == 0:
            raise ValueError("sigmaClippedMean expects a non-empty 2-D (frames × bins) stack")
        keep = ~np.isnan(stack)
        for _ in range(self.SIGMA_ITERS):
            kept = np.where(keep, stack, np.nan)
            center = _nanmedian(kept, axis=0)
            mad = _nanmedian(np.abs(kept - center), axis=0)
            sigma = self.__MAD_TO_SIGMA * np.where(np.isnan(mad), 0.0, mad)
            threshold = np.where(sigma > 0, self.SIGMA_K * sigma, np.inf)     # σ==0 → keep all (constant bin)
            updated = keep & (np.abs(stack - center) <= threshold)
            if np.array_equal(updated, keep):
                break
            keep = updated
        counts = np.sum(keep, axis=0)
        totals = np.nansum(np.where(keep, stack, 0.0), axis=0)
        return totals / np.maximum(counts, 1)                                # all-NaN bin → 0 (count floored to 1)

    def rejectDimFrames(self, stack):
        """stack: 2-D (frames × bins). Return a 1-D boolean KEEP-mask over FRAMES.

        Drops whole frames whose GLOBAL brightness (median across bins) is a MAD-outlier vs the median frame —
        the coherent dim group an auto-exposure ramp leaves in the reference burst, which a per-BIN sigma-clip
        cannot reject (with a large-minority dim group the per-column σ inflates and the mean is dragged toward
        them). Judging on the per-frame SCALAR, and with MAD's 50% breakdown, that group is obvious and dropped
        BEFORE `sigmaClippedMean`. Symmetric (a bright flare frame is rejected too). See SPEC_capture_quality.md
        §14.8. Conservative on the edges: too few frames, a degenerate (MAD==0) brightness spread, or a mask that
        would reject everything all fall back to keep-all — the sigma-clip still runs."""
        stack = np.asarray(stack, dtype=float)
        if stack.ndim != 2 or stack.shape[0] == 0:
            raise ValueError("rejectDimFrames expects a non-empty 2-D (frames × bins) stack")
        n = stack.shape[0]
        if n < self.MIN_FRAMES_TO_REJECT:
            return np.ones(n, dtype=bool)
        brightness = _nanmedian(stack, axis=1)                               # one brightness scalar per frame
        center = _nanmedian(brightness, axis=0)
        mad = _nanmedian(np.abs(brightness - center), axis=0)
        sigma = self.__MAD_TO_SIGMA * (mad if np.isfinite(mad) else 0.0)
        # Floor the scale relative to the brightness level (see DIM_FRAME_SCALE_FLOOR). This makes a tight/identical
        # clean cluster (MAD≈0, e.g. the virtual path or a synthetic stack) keep ALL frames when there is no dim
        # group, yet still reject a blatant dim minority — without a floor, MAD==0 would either keep everything or
        # over-reject on exact equality.
        scale = max(sigma, self.DIM_FRAME_SCALE_FLOOR * abs(center))
        if not np.isfinite(scale) or scale <= 0:
            return np.ones(n, dtype=bool)                                    # center 0 / all-NaN → nothing to judge
        keep = np.abs(brightness - center) <= self.DIM_FRAME_K * scale
        keep = np.where(np.isnan(brightness), False, keep)                   # an all-NaN frame is not usable
        if not keep.any():
            return np.ones(n, dtype=bool)                                    # never reject everything
        return keep
