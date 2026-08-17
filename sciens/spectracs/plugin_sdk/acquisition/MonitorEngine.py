import traceback

import numpy as np

from sciens.spectracs.logic.spectral.acquisition.RobustReductionLogicModule import RobustReductionLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModule import MeanSpectrumLogicModule
from sciens.spectracs.logic.spectral.meanSpectrum.MeanSpectrumLogicModuleParameters import \
    MeanSpectrumLogicModuleParameters
from sciens.spectracs.model.spectral.Spectrum import Spectrum
from sciens.spectracs.plugin_sdk.acquisition.FrameRing import FrameRing
from sciens.spectracs.plugin_sdk.acquisition.MonitorDecision import MonitorDecision
from sciens.spectracs.plugin_sdk.acquisition.MonitorOutcome import MonitorOutcome
from sciens.spectracs.plugin_sdk.acquisition.MonitorPolicy import MonitorPolicy
from sciens.spectracs.plugin_sdk.acquisition.MonitorResult import MonitorResult
from sciens.spectracs.plugin_sdk.acquisition.MonitorRow import MonitorRow


class MonitorEngine:
    """The mechanics of a monitored acquisition — and NOTHING else (SPEC_settled_measurement.md §10).

    ⭐⭐ A PART, NOT A FRAMEWORK. It is composed by the PLUGIN (`createMonitor()` assembles it with a ring
    and its own evaluator) and merely handed to the host, which only pushes frames into it. ⛔ It does not
    know the word "plugin", it never calls back into one, and it names no wavelength: it holds an
    `evaluator` collaborator it was given, and asks it two questions.

    ⭐ PUSH API — the CALLER owns the loop and the clock:

        monitor.offer(valuesByNanometers, timestamp) -> MonitorRow | None
        monitor.result()                             -> MonitorResult

    That is what lets the diagnostics script (`while backend.read()`), the bench (its frameProvider pump),
    a unit test (synthetic timestamps — a 90-minute curve replays in milliseconds, §25/X6) and a replay
    from `.npz` all drive the SAME object. ⛔ A pull API would need three different pumps and would block
    the GUI in one of them (§10.1b).

    ⚠ SINGLE-USE (§25/X4): one monitor per capture. A reused one carries a stale ring, a latched answer
    and a reference that may no longer be the jar on the bench.
    """

    def __init__(self, evaluator, ring=None, policy=None, evaluatorId=None, evaluatorVersion=None):
        self.policy = policy or MonitorPolicy()
        self.evaluator = evaluator
        self.ring = ring or FrameRing(self.policy.windowFrames, self.policy.retentionFrames)
        self.evaluatorId = evaluatorId or type(evaluator).__name__
        self.evaluatorVersion = evaluatorVersion or getattr(evaluator, "version", None)

        self.rows = []
        self.notes = []
        self.outcome = MonitorOutcome.RUNNING
        self.__firstTimestamp = None
        self.__lastTimestamp = None
        self.__answer = None            # ⭐ LATCHED (§14.6) — the first promote wins, later rows cannot steal it
        self.__answerSpectrum = None
        self.__answerRow = None
        self.__latchedOutcome = None
        self.__clearingSeconds = None
        self.__cancelled = False
        self.__capsHit = False
        self.__error = None
        self.__lastSignature = None     # for the duplicate-frame count (§23/V1)
        self.__distinctCount = 0
        self.__finished = False

    # --- the seam -------------------------------------------------------------------------------------

    def offer(self, valuesByNanometers, timestamp):
        """Push ONE frame. Returns the row it produced, or None (still filling / not due / finished).

        ⚠ `timestamp` should come from a MONOTONIC clock (§25/X3): a 20-minute run is long enough to meet
        an NTP step, and a backwards jump makes the rate negative while a near-zero one makes it enormous
        — which would trip a re-clouding reset rather than failing loudly.
        """
        if self.__finished:
            return None
        if valuesByNanometers is None:
            return None

        if self.__firstTimestamp is None:
            # ⭐ t = 0 is the FIRST OFFERED FRAME, never the click (§23/V4): the bench pays a ~15 s
            # auto-exposure sweep that the script does not, and clearingSeconds must be comparable.
            self.__firstTimestamp = float(timestamp)
        self.__lastTimestamp = float(timestamp)

        self.__countDistinct(valuesByNanometers)
        frameIndex = self.ring.add(valuesByNanometers, timestamp)

        row = self.__evaluateIfDue(frameIndex)
        if row is not None:
            self.rows.append(row)
            self.__pruneSpectra()
            if row.isDecisionRow and not self.__finished:
                self.__applyDecision(row)
        self.__enforceCaps()
        return row

    def isFinished(self):
        return self.__finished

    def cancel(self):
        """The operator stopped it (§12.1). ⛔ The step's container is left untouched by the HOST — a
        cancelled capture is not a capture — but the trajectory so far is kept, marked, and never
        reported as a measurement."""
        self.__cancelled = True
        self.__finish(MonitorOutcome.CANCELLED)

    def stall(self):
        """Frames stopped arriving. ⭐ Only the HOST can detect this (§12.2/L3): the engine learns that
        time passed only when someone calls offer(), so a wedged camera never wakes an engine-side timer."""
        self.__finish(MonitorOutcome.STALLED)

    def result(self):
        answer = dict(self.__answer) if self.__answer else None
        return MonitorResult(
            outcome=self.outcome, rows=list(self.rows), spectrum=self.__answerSpectrum, answer=answer,
            columns=self.__columns(), policy=self.policy, evaluatorId=self.evaluatorId,
            evaluatorVersion=self.evaluatorVersion, clearingSeconds=self.__clearingSeconds,
            cancelled=self.__cancelled, capsHit=self.__capsHit,
            distinctFraction=self.distinctFraction(), notes=list(self.notes), error=self.__error)

    def distinctFraction(self):
        """Fraction of offered frames that were NOT a repeat of their predecessor (§23/V1). Measured at
        82 % on the archive, i.e. a x1.10 noise inflation — recorded per run rather than assumed."""
        offered = self.ring.offeredCount()
        return (self.__distinctCount / float(offered)) if offered else None

    # --- internals ------------------------------------------------------------------------------------

    def __countDistinct(self, valuesByNanometers):
        # Cheap signature: the values only (keys are identical across frames by construction of the cubic).
        try:
            signature = hash(tuple(valuesByNanometers.values()))
        except TypeError:
            signature = None
        if signature is None or signature != self.__lastSignature:
            self.__distinctCount += 1
        self.__lastSignature = signature

    def __evaluateIfDue(self, frameIndex):
        window = self.ring.window()
        if len(window) < self.policy.minWindowFrames:
            return None
        full = self.policy.windowFrames is None or len(window) >= self.policy.windowFrames
        # ⭐ §25/X2: a DECISION ROW is defined by the FRAME INDEX, never by "every W-th row" — otherwise
        # raising evaluateEveryNFrames (which §9.1b explicitly reserves the right to do) would silently
        # multiply the comparison span and change the noise budget nobody re-derived.
        # ⚠ windowFrames=None is the plain-burst shape (§10.6): the window IS everything captured so far,
        # so every evaluated row decides — otherwise a burst would never be asked whether it is done.
        isDecisionRow = full if self.policy.windowFrames is None else \
            (full and ((frameIndex + 1) % self.policy.windowFrames == 0))
        due = isDecisionRow or (self.ring.offeredCount() % self.policy.evaluateEveryNFrames == 0)
        if not due:
            return None

        spectrum, nAccepted = self.__reduce(window)
        firstT, lastT = self.ring.windowSpan(window)
        values = None
        try:
            values = self.evaluator.evaluate(spectrum)
        except Exception:                                   # ⛔ §25/X5 — never swallow, but keep the run's data
            self.__error = traceback.format_exc()
            self.__finish(MonitorOutcome.FAILED)
            return None
        row = MonitorRow(
            t=(firstT + lastT) / 2.0 - self.__firstTimestamp,   # ⭐ the window CENTRE (§9.3)
            frameIndex=frameIndex, n=len(window), nAccepted=nAccepted, values=values,
            provisional=not full, isDecisionRow=isDecisionRow)
        row.spectrum = spectrum                              # transient: promoted only if this row wins
        return row

    def __reduce(self, window):
        """Window frames -> ONE mean spectrum, through the app's OWN reduction (C1 rejection inside).

        ⭐ Reduce the SPECTRA first, then let the evaluator compute its metric (§9.5): `Q%` is a ratio, so
        mean(Q%) != Q%(mean spectrum), and the shipped bench number is the latter. Doing it the other way
        round would make the monitor and the bench disagree by construction."""
        frames = [values for _, _, values in window]
        spectrum = Spectrum()
        for frame in frames:
            spectrum.addToCapturedValuesByNanometers(frame)
        parameters = MeanSpectrumLogicModuleParameters()
        parameters.setSpectrum(spectrum)
        reduced = MeanSpectrumLogicModule().meanSpectrum(parameters).getSpectrum()
        return reduced, self.__survivingFrameCount(frames)

    @staticmethod
    def __survivingFrameCount(frames):
        # ⭐ §19/I3: the same computation SpectralWorkflowEngine.__survivingFrameCount did, lifted here so
        # the two paths cannot drift. C3's top-up (SPEC_capture_quality.md §14.8) counts frames that
        # SURVIVE C1, not frames offered.
        if not frames:
            return 0
        keys = list(frames[0].keys())
        stack = np.array([[frame.get(key, np.nan) for key in keys] for frame in frames], dtype=float)
        return int(np.sum(RobustReductionLogicModule().rejectDimFrames(stack)))

    # ⛔⛔ RETENTION IS SIZED IN **TIME**, NOT IN ROWS (SPEC_settled_measurement.md §27.25, M1).
    #
    # It used to be `SPECTRUM_RETAIN_DECISION_ROWS = 5`, justified as "the vertex reaches ~2 decision rows
    # back". That was true at the DIAGNOSTIC script's 3.28-minute sampling and false on the bench: at ~3.5
    # fps a decision row lands every ~17 s, so five rows is **85 seconds** of history — while jar B's `Q%`
    # minimum sits **3.27 minutes** (11.5 rows) before the gate confirms it.
    # ⇒ on every fill that actually CLEARED, the vertex winner's spectrum had already been thrown away, so
    # the run produced an answer with no spectrum, the host set no container, and the operator was told
    # "Capture failed — no frames were delivered by the camera". MEASURED: present at 0-4 rows back, gone
    # from exactly 5. It was a window sized in rows, validated at one cadence, used at an 11x finer one.
    #
    # ⭐ A DECISION ROW'S SPECTRUM NOW LIVES AS LONG AS THE RUN MAY STILL NEED IT — `maxSeconds`, the cap
    # the run cannot outlive — so no cadence change can invalidate it again. ⚠ THIS IS THE WHOLE POINT of
    # expressing it in seconds: the next person to make rows denser (5 s is already asked for) must not
    # have to re-derive a row count nobody would think to check.
    # ⚠ The cost is bounded and small: at the 25-minute cap even a 5 s cadence keeps ~300 decision rows at
    # ~30 KB each -> ~9 MB. ⛔ The 34 MB this comment used to fear is PER-FRAME spectra (~1700 of them);
    # decision rows are ~50x fewer, and §15.3's rule — no raw frames in the product — is untouched.
    NON_DECISION_RETAIN_ROWS = 2      # a provisional row is display-only; two is enough to draw from

    def __retentionSeconds(self):
        return float(self.policy.maxSeconds)

    def __pruneSpectra(self):
        # ⭐ Keep every decision row inside the retention window; drop only what the run can no longer read.
        newest = self.rows[-1].t if self.rows else 0.0
        horizon = newest - self.__retentionSeconds()
        for stale in [row for row in self.rows if row.isDecisionRow]:
            if stale.t >= horizon:
                continue
            if getattr(stale, "spectrum", None) is not None and stale is not self.__promotedRow():
                stale.spectrum = None
        for stale in [row for row in self.rows if not row.isDecisionRow][:-self.NON_DECISION_RETAIN_ROWS]:
            stale.spectrum = None

    def __promotedRow(self):
        return None if self.__answer is None else self.__answerRow

    def __applyDecision(self, row):
        try:
            decision = self.evaluator.decide(self.rows) or MonitorDecision.carryOn()
        except Exception:
            self.__error = traceback.format_exc()
            self.__finish(MonitorOutcome.FAILED)
            return
        if decision.note:
            self.notes.append("%.1fs %s" % (row.t, decision.note))
        if decision.promote and self.__answer is None:       # ⭐ THE LATCH (§14.6): the first promote wins
            # ⭐ The promoted row is not always the current one: on the was-clearing branch the answer is
            # the Q% MINIMUM, confirmed two decision rows after it happened.
            winner = decision.promoteRow if decision.promoteRow is not None else row
            value = decision.answer if decision.answer is not None else winner.get(self.__valueKey())
            self.__answer = {"valueKey": self.__valueKey(), "value": value, "t": winner.t,
                             "frameIndex": winner.frameIndex, "readAs": decision.readAs,
                             "branch": decision.branch}
            self.__answerSpectrum = getattr(winner, "spectrum", None)
            self.__answerRow = winner
            # ⭐ §2.4: the clearing time is when the fill STOPPED clearing — i.e. when the gate confirmed
            # it (this row), not when the winning window happened to sit.
            self.__clearingSeconds = row.t
            # Remembered separately from `stop`, because a DIAGNOSTIC run promotes and then keeps
            # observing for another 20 minutes (§11.9c) — the cap must still report what was settled.
            self.__latchedOutcome = decision.outcome or MonitorOutcome.COMPLETED
        if decision.stop:
            self.__finish(decision.outcome or MonitorOutcome.COMPLETED)

    def __enforceCaps(self):
        # ⭐ L2 (§12.2): ALWAYS on, and the evaluator cannot disable them. A run that cannot terminate is
        # an instrument that can hang with the lamp on the sample.
        if self.__finished:
            return
        elapsed = (self.__lastTimestamp - self.__firstTimestamp) if self.__firstTimestamp is not None else 0.0
        if elapsed >= self.policy.maxSeconds or self.ring.offeredCount() >= self.policy.maxFrames:
            self.__capsHit = True
            # ⛔ On a cap the last row is NOT the answer (§2.5). If nothing was ever promoted, there is no
            # value at all — and the operator is told which.
            self.__finish(MonitorOutcome.NEVER_SETTLED if self.__answer is None
                          else (self.__latchedOutcome or MonitorOutcome.COMPLETED))

    def __finish(self, outcome):
        if self.__finished:
            return
        self.outcome = outcome if outcome is not None else MonitorOutcome.COMPLETED
        self.__finished = True

    def __valueKey(self):
        return getattr(self.evaluator, "valueKey", None)

    def __columns(self):
        return list(getattr(self.evaluator, "columns", []) or [])
