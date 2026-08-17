from sciens.spectracs.plugin_sdk.acquisition.MonitorDecision import MonitorDecision
from sciens.spectracs.plugin_sdk.acquisition.MonitorOutcome import MonitorOutcome


class BurstEvaluator:
    """"No opinion; stop when the window is full" — i.e. TODAY'S PLAIN BURST (SPEC_settled_measurement.md §10.6).

    ⭐⭐ THE POINT OF THIS CLASS IS THAT THERE WAS ONLY EVER ONE THING. Grab N frames, mean them, done —
    that is a monitored acquisition whose evaluator computes no metric and whose stop rule is "the frames
    have arrived". ⇒ ONE code path in the host for every plugin; what differs is only which evaluator the
    plugin put inside its monitor. A plugin that needs no intermediate evaluation writes ⭐ nothing at all.

    ⚠ C3 (SPEC_capture_quality.md §14.8) DOES NOT TRANSLATE LITERALLY (§19/I4). The old `__runBurst` kept
    grabbing until N frames SURVIVED the C1 brightness rejection; a ring has no "top-up". So the rule is
    expressed where it now belongs — ⭐ **stop when nAccepted >= N**, not when N frames were offered.
    ⛔ A synthetic equivalence test on clean frames passes either way, which is why the test must include
    dim frames.
    """

    version = "1.0"
    valueKey = None          # ⭐ no metric at all — the row carries only the spectrum
    columns = []

    def __init__(self, targetFrames):
        self.targetFrames = int(targetFrames)

    def evaluate(self, spectrum):
        return {}            # ⭐ no metric. The Row's `values` is legitimately empty (§25/X3).

    def decide(self, rows):
        row = rows[-1]
        if row.n >= self.targetFrames and row.nAccepted >= self.targetFrames:
            return MonitorDecision(promote=True, stop=True, outcome=MonitorOutcome.COMPLETED,
                                   readAs="BURST_MEAN")
        return MonitorDecision.carryOn()

    def coach(self, rows):
        # DETERMINATE progress — this is what reproduces today's "Capturing sample frame 34 / 60" line
        # unchanged through the new path (§13.3).
        n = rows[-1].n if rows else 0
        return {"state": "capturing", "progress": ("DETERMINATE", min(1.0, n / float(self.targetFrames))),
                "fields": [("frame", "%d / %d" % (min(n, self.targetFrames), self.targetFrames))]}
