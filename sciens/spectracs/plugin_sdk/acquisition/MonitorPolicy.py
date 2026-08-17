class MonitorPolicy:
    """The MECHANICAL knobs of a monitored acquisition (SPEC_settled_measurement.md §10.2).

    ⛔ NO thresholds, NO gate scalar, NO band edges. Those belong to the evaluator — i.e. to the plugin —
    and the stringly-typed `gateOn="valley"` of an earlier draft was removed precisely because it let the
    machinery run a decision it does not own (§10.1a-bis).

    ⛔ `maxSeconds` MAY NEVER BE None (§12.2). A nullable cap is the loophole that turns the termination
    guarantee into a comment; a plugin may RAISE it, never remove it.
    """

    def __init__(self, windowFrames=50, retentionFrames=None, minWindowFrames=None,
                 evaluateEveryNFrames=1, maxSeconds=1500.0, maxFrames=4000):
        if maxSeconds is None or maxSeconds <= 0:
            raise ValueError("maxSeconds must be a positive number — see SPEC_settled_measurement.md §12.2")
        if maxFrames is None or maxFrames <= 0:
            raise ValueError("maxFrames must be a positive number — see SPEC_settled_measurement.md §12.2")
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
                "maxSeconds": self.maxSeconds, "maxFrames": self.maxFrames}
