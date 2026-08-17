class MonitorRow:
    """One evaluated window (SPEC_settled_measurement.md §9, §10.7c).

    ⚠ `t` IS THE WINDOW CENTRE, not the moment the row appeared — a boxcar of W frames lags the truth by
    (W-1)/2 frames, which is 17-25 s at the ELP's ~1.0-1.5 fps. Stamping at the last frame would displace
    every slope, vertex and intercept systematically (§9.3). A reader who assumes `t` means "when the line
    was written" mis-times every event by half a window.

    ⚠ `values` MAY BE EMPTY. The plugin's own metric returns nothing when its floor is not met (§25/X3),
    and a plain burst has no metric at all (§10.6) — so ⛔ nothing in the engine may index into it.
    """

    def __init__(self, t, frameIndex, n, nAccepted, values=None, provisional=False, isDecisionRow=False):
        self.t = t                        # ⭐ window CENTRE, in seconds since the first offered frame
        self.frameIndex = frameIndex      # global index of the window's LAST frame
        self.n = n                        # frames in the window
        self.nAccepted = nAccepted        # ...of which survived the C1 brightness rejection
        self.values = values or {}        # the PLUGIN's scalars — opaque to the engine
        self.provisional = provisional    # ⚠ ring still filling: display only, never gated on or fitted
        self.isDecisionRow = isDecisionRow

    def get(self, key, default=None):
        return self.values.get(key, default)

    def toDict(self):
        row = {"t": self.t, "frameIndex": self.frameIndex, "n": self.n, "nAccepted": self.nAccepted,
               "provisional": self.provisional, "isDecisionRow": self.isDecisionRow}
        row.update(self.values)
        return row

    def __repr__(self):
        return "MonitorRow(t=%.1f, n=%d/%d, %s%s)" % (
            self.t, self.nAccepted, self.n, self.values, " PROVISIONAL" if self.provisional else "")
