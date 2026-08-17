class FrameRing:
    """A bounded ring of RAW per-frame spectra (SPEC_settled_measurement.md §9.1a).

    ⭐ THREE SIZES, DELIBERATELY SEPARATE — conflating them is the bug §9.1a was written to prevent:
      * `windowFrames` W  — how many frames one row averages (the statistical aperture)
      * `retentionFrames` R — how many raw frames stay in RAM. Only ever W + a small margin.
      * the WINNER          — the best row's already-reduced mean spectrum, PROMOTED OUT of the ring by
                              the engine the moment it wins. ⛔ It is never fished back out of the ring:
                              by then its frames are gone, and a ring big enough to prevent that would be
                              sized by the run length instead of by the statistics.

    `windowFrames=None` means "every retained frame" — which is what turns the ring into a plain burst
    accumulator (§10.6: the burst is the degenerate monitor).
    """

    def __init__(self, windowFrames=50, retentionFrames=None):
        if windowFrames is not None and windowFrames < 1:
            raise ValueError("windowFrames must be >= 1 (or None for 'all retained')")
        self.windowFrames = windowFrames
        # Default retention: the window plus a small margin, so a window is always available whole.
        self.retentionFrames = retentionFrames if retentionFrames is not None else (
            None if windowFrames is None else windowFrames + max(5, windowFrames // 5))
        self.__frames = []          # list of (frameIndex, timestamp, {nm: value})
        self.__offered = 0          # total frames ever offered (NOT the ring length)

    def add(self, valuesByNanometers, timestamp):
        """Append one frame. Returns its 0-based GLOBAL frame index (which keeps counting after eviction)."""
        index = self.__offered
        self.__offered += 1
        self.__frames.append((index, float(timestamp), valuesByNanometers))
        if self.retentionFrames is not None and len(self.__frames) > self.retentionFrames:
            del self.__frames[0:len(self.__frames) - self.retentionFrames]
        return index

    def offeredCount(self):
        return self.__offered

    def __len__(self):
        return len(self.__frames)

    def window(self):
        """The newest `windowFrames` retained frames (or all of them when windowFrames is None)."""
        if self.windowFrames is None:
            return list(self.__frames)
        return list(self.__frames[-self.windowFrames:])

    def windowSpan(self, window=None):
        """(firstTimestamp, lastTimestamp) of a window — the engine stamps rows at the CENTRE of this."""
        window = self.window() if window is None else window
        if not window:
            return None, None
        return window[0][1], window[-1][1]

    def lastFrameIndex(self):
        return self.__frames[-1][0] if self.__frames else None
