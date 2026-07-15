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
    __MAD_TO_SIGMA = 1.4826

    def tukeyBiweightPerColumn(self, band):
        """band: 2-D array (rows × columns) of intensities; **NaN marks excluded pixels** (the caller masks
        saturated / dead — saturation is a per-CHANNEL fact, so it must be masked before qGray is formed, not
        detected here). Returns a 1-D array, one robust location per column. A constant column (MAD==0) returns its
        median unchanged; an all-NaN column returns NaN (the caller supplies the fallback, e.g. the plain median)."""
        band = np.asarray(band, dtype=float)
        if band.ndim != 2 or band.shape[0] == 0:
            raise ValueError("tukeyBiweightPerColumn expects a non-empty 2-D (rows × cols) band")

        median = _nanmedian(band, axis=0)                       # NaN for all-NaN columns
        mad = _nanmedian(np.abs(band - median), axis=0)
        mad = np.where(np.isnan(mad), 0.0, mad)

        location = median.copy()
        moving = mad > 0                                        # constant / all-NaN columns keep their median
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
