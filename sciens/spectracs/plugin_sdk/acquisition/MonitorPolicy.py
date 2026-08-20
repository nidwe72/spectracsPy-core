class MonitorPolicy:
    """The MECHANICAL knobs of a monitored acquisition (SPEC_settled_measurement.md §10.2).

    ⛔ NO thresholds, NO gate scalar, NO band edges. Those belong to the evaluator — i.e. to the plugin —
    and the stringly-typed `gateOn="valley"` of an earlier draft was removed precisely because it let the
    machinery run a decision it does not own (§10.1a-bis).

    ⛔ `maxSeconds` MAY NEVER BE None (§12.2). A nullable cap is the loophole that turns the termination
    guarantee into a comment; a plugin may RAISE it, never remove it.
    """

    # ⭐⭐⭐ THE FRAME CAP MUST BE DERIVED, NOT PINNED (SPEC_settled_measurement.md §49/F1).
    # ⛔⛔ `maxFrames = 4000` was a runaway guard — and at this camera's measured 3.23-3.34 fps it is
    # NUMERICALLY A 20-MINUTE LIMIT. A 1200 s run needs 3880-4008 frames, and run 001's own rate is already
    # OVER 4000. ⇒ with a planned duration in place the FRAME cap would fire at ~19.9 min, before the clock,
    # set `capsHit`, and finish `NEVER_SETTLED` on essentially every run. A second time cap wearing a frame
    # costume, sitting exactly where the planned duration wants to be.
    # ⭐ Deriving it costs nothing: `maxFrames` COUNTS, it does not allocate — the ring is sized by
    # `windowFrames + retention`, never by this.
    ASSUMED_MAX_FPS = 10.0            # stated, not guessed: 3x the measured 3.3 fps, so a faster camera fits

    def __init__(self, windowFrames=50, retentionFrames=None, minWindowFrames=None,
                 evaluateEveryNFrames=1, maxSeconds=1500.0, maxFrames=None, plannedSeconds=None):
        if maxSeconds is None or maxSeconds <= 0:
            raise ValueError("maxSeconds must be a positive number — see SPEC_settled_measurement.md §12.2")
        if maxFrames is None:
            maxFrames = int(maxSeconds * self.ASSUMED_MAX_FPS) + 1
        if maxFrames is None or maxFrames <= 0:
            raise ValueError("maxFrames must be a positive number — see SPEC_settled_measurement.md §12.2")
        # ⭐⭐ THE PLANNED DURATION (§34, §46/E1) — the run ends on the CLOCK, and every fill therefore gets
        # the SAME DOSE, which deletes §2.4's varying-clearing-time term from sigma_fill. It also guarantees
        # the browning limb has time to CONFIRM the minimum: run 001 outlasted its own minimum by ONE ROW.
        # ⛔ It is NOT `maxSeconds`. `maxSeconds` is the un-removable termination guarantee AND the spectrum
        # retention horizon (§27.25) — lowering it to implement the planned duration would shrink retention
        # along with the run and throw away the winner's spectrum (§43/RD1).
        if plannedSeconds is not None:
            if plannedSeconds <= 0:
                raise ValueError("plannedSeconds must be positive")
            if plannedSeconds > maxSeconds:
                raise ValueError("plannedSeconds (%s) must not exceed maxSeconds (%s) — §46/E1"
                                 % (plannedSeconds, maxSeconds))
            if plannedSeconds * self.ASSUMED_MAX_FPS >= maxFrames:
                raise ValueError(
                    "maxFrames (%d) would fire before plannedSeconds (%s) at %g fps — §49/F1"
                    % (maxFrames, plannedSeconds, self.ASSUMED_MAX_FPS))
        self.plannedSeconds = None if plannedSeconds is None else float(plannedSeconds)
        self.windowFrames = windowFrames
        self.retentionFrames = retentionFrames
        # The smallest window allowed to emit a PROVISIONAL row (display only — §14.2). Defaults to the
        # full window, i.e. no provisional rows at all.
        # ⚠ windowFrames=None (the plain-burst shape, §10.6) means "all retained frames", so the minimum
        # is one frame — not None, which would blow up the len() comparison in the engine.
        self.minWindowFrames = minWindowFrames if minWindowFrames is not None else (
            1 if windowFrames is None else windowFrames)
        self.evaluateEveryNFrames = max(1, int(evaluateEveryNFrames))
        self.maxSeconds = float(maxSeconds)          # 25 min by default (§12.2)
        self.maxFrames = int(maxFrames)

    def toDict(self):
        # Goes into the MonitorRecord: two runs made under different rules must never be compared
        # silently (§15.2).
        return {"windowFrames": self.windowFrames, "retentionFrames": self.retentionFrames,
                "minWindowFrames": self.minWindowFrames,
                "evaluateEveryNFrames": self.evaluateEveryNFrames,
                "maxSeconds": self.maxSeconds, "maxFrames": self.maxFrames,
                "plannedSeconds": self.plannedSeconds}
